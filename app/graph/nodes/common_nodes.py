"""Graph 工作流节点 — 7 个主节点"""

import logging
from typing import Any

from app.graph.state_keys import StateKeys as K
from app.graph.hooks.hooks import create_hook_engine, HookContext, HOOK_POINTS
from app.agent.router_agent import RouterAgent
from app.agent.llm_client import llm
from app.rag.hybrid_search import HybridSearchService

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
    """ContextLoad: 加载 Memory + Skill + 历史"""
    memory_context = state.get(K.MEMORY_CONTEXT, "")
    skill_context = state.get(K.SKILL_CONTEXT, "")
    history = state.get(K.HISTORY, "")
    return {
        K.MEMORY_CONTEXT: memory_context,
        K.SKILL_CONTEXT: skill_context,
        K.HISTORY: history,
    }


def router_node(state: dict[str, Any]) -> dict[str, Any]:
    """Router: 意图识别"""
    question = state.get(K.CLEANED_INPUT, state.get(K.INPUT, ""))
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
    """MemorySave: 保存对话记忆"""
    logger.info(f"保存对话记忆: session={state.get(K.SESSION_ID, '')}")
    return {}
