"""Graph 工作流节点 — 7 个主节点"""

import logging
from typing import Any

from app.graph.state_keys import StateKeys as K
from app.graph.hooks.hooks import create_hook_engine, HookContext, HOOK_POINTS
from app.agent.router_agent import RouterAgent
from app.agent.llm_client import llm
from app.rag.hybrid_search import HybridSearchService

NODE_STATUS_MAP: dict[str, str] = {
    "precheck": "正在校验输入...",
    "context_load": "正在加载上下文记忆...",
    "router": "正在识别意图...",
    "knowledge_qa": "正在检索知识库...",
    "diagnosis": "正在执行智能诊断...",
    "diagnosis_parallel": "正在并行采集数据...",
    "quality_gate": "质量评审+报告生成...",
    "chat": "正在生成回复...",
    "safety_review": "正在进行安全审查...",
    "final_response": "正在生成诊断报告...",
    "memory_save": "正在保存会话记录...",
    "evidence_validation": "验证证据充分性...",
    "risk_action": "风险评估+行动建议生成...",
    "replanner": "诊断质量复核...",
}

logger = logging.getLogger(__name__)
hook_engine = create_hook_engine()
router_agent = RouterAgent()


def precheck_node(state: dict[str, Any]) -> dict[str, Any]:
    """PreCheck: 输入校验 + 清洗"""
    ctx = HookContext(input=state.get(K.INPUT, ""), session_id=state.get(K.SESSION_ID, ""),
                      user_id=state.get(K.USER_ID, ""))
    ctx = hook_engine.execute_hooks(HOOK_POINTS["PRE_ROUTE"], ctx)
    if ctx.metadata.get("blocked"):
        return {K.FINAL_RESPONSE: "输入包含不安全内容", K.NEXT_ACTION: "end"}
    return {K.CLEANED_INPUT: ctx.input, K.TRACE_ID: state.get(K.TRACE_ID, "")}


def context_load_node(state: dict[str, Any]) -> dict[str, Any]:
    session_id = state.get(K.SESSION_ID, "")
    task_id = state.get(K.TASK_ID, "")
    try:
        from app.memory.memory_service import get_memory
        mem = get_memory()
        mem.init_session(session_id)
        history = mem.get_session_history(session_id, n=3)
        task_ctx = mem.get_task_context(task_id) if task_id else {}
        return {
            K.HISTORY: history,
            K.MEMORY_CONTEXT: history,
            K.SKILL_CONTEXT: task_ctx.get("skill_context", state.get(K.SKILL_CONTEXT, "")),
        }
    except Exception as e:
        logger.warning(f"上下文加载失败: {e}")
        return {
            K.MEMORY_CONTEXT: state.get(K.MEMORY_CONTEXT, ""),
            K.SKILL_CONTEXT: state.get(K.SKILL_CONTEXT, ""),
            K.HISTORY: state.get(K.HISTORY, ""),
        }


def router_node(state: dict[str, Any]) -> dict[str, Any]:
    question = state.get(K.CLEANED_INPUT, state.get(K.INPUT, ""))
    existing_intent = state.get(K.INTENT, "")
    existing_confidence = state.get(K.CONFIDENCE, 0.0)
    existing_entities = state.get(K.ENTITIES) or {}

    if existing_intent and existing_confidence > 0:
        return {
            K.INTENT: existing_intent,
            K.CONFIDENCE: existing_confidence,
            K.ENTITIES: existing_entities,
        }

    result = router_agent.route(question)
    ctx = HookContext(input=question, intent=result.get("intent", "CHAT"),
                      confidence=result.get("confidence", 0.5),
                      entities=result.get("entities", {}))
    ctx = hook_engine.execute_hooks(HOOK_POINTS["POST_ROUTE"], ctx)
    return {
        K.INTENT: ctx.intent,
        K.CONFIDENCE: ctx.confidence,
        K.ENTITIES: ctx.entities,
    }


def safety_review_node(state: dict[str, Any]) -> dict[str, Any]:
    """SafetyReview: 安全审查"""
    diagnosis = state.get(K.EXECUTION_RESULT, state.get(K.FINAL_RESPONSE, ""))
    ctx = HookContext(output=diagnosis, metadata={"risk_level": state.get(K.RISK_LEVEL, "LOW")})
    ctx = hook_engine.execute_hooks(HOOK_POINTS["POST_DIAGNOSIS"], ctx)
    return {
        K.FINAL_RESPONSE: ctx.output or diagnosis,
        K.REVIEW_DECISION: ctx.metadata.get("approval_required", False),
    }


def final_response_node(state: dict[str, Any]) -> dict[str, Any]:
    """FinalResponse: 组装最终输出"""
    result = state.get(K.EXECUTION_RESULT, state.get(K.FINAL_RESPONSE, ""))
    diagnosis = state.get(K.DIAGNOSIS_RESULT, {})
    return {K.FINAL_RESPONSE: result, "output": result}


def memory_save_node(state: dict[str, Any]) -> dict[str, Any]:
    session_id = state.get(K.SESSION_ID, "")
    user_input = state.get(K.INPUT, "")
    response = state.get(K.FINAL_RESPONSE, state.get(K.EXECUTION_RESULT, ""))
    try:
        from app.memory.memory_service import get_memory
        mem = get_memory()
        mem.save_to_session(session_id, user_input, response)
        logger.info(f"保存对话记忆: session={session_id}")
    except Exception as e:
        logger.warning(f"记忆保存失败: {e}")
    return {}
