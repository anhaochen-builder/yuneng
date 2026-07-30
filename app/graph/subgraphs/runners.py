"""子图运行器 — 将各子图逻辑封装为 LangGraph 节点兼容的 async 函数

每个子图函数签名: async def xxx(state: AgentState) -> dict[str, Any]
返回部分状态更新字典。
"""

import json
import logging
from typing import Any

from app.graph.state import AgentState
from app.graph.state_keys import StateKeys as K
from app.agent.llm_client import llm
from app.agent.diagnosis_agent import DiagnosisAgent
from app.agent.risk_review_agent import RiskReviewAgent
from app.agent.judge_agent import JudgeAgent
from app.agent.subagent_executor import SubagentExecutor
from mcp_server.tools import (
    get_device_status, get_alarm_history, get_device_logs,
    get_defect_tickets, search_safety_rules,
)

logger = logging.getLogger(__name__)


def _json_str(data) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


async def run_diagnosis_subgraph(state: AgentState) -> dict[str, Any]:
    """Diagnosis 子图运行器: EntityExtract → AlarmRAG → Executor → Diagnose → RiskReview

    从 PowerEmergencyGraph._run_diagnosis 迁移而来。
    """
    from app.graph.subgraphs.diagnosis import (
        entity_extract_node, alarm_rag_retrieve_node,
    )

    logger.info("  → Diagnosis 子图 (诊断流程)")

    entities = state.get(K.ENTITIES, {})
    device_id = entities.get("device_id", state.get(K.DEVICE_ID, ""))
    input_text = state.get(K.CLEANED_INPUT, state.get(K.INPUT, ""))
    skill_context = state.get(K.SKILL_CONTEXT, "")
    loop_count = state.get(K.LOOP_COUNT, 0) + 1  # 每次进入都会递增

    # 重试时调整策略：扩大检索范围
    is_retry = loop_count > 1
    if is_retry:
        logger.info(f"  重规划模式 (第{loop_count}次)，扩大检索范围")

    # 1. 实体提取 + RAG 检索
    entity_result = entity_extract_node(state)
    rag_result = alarm_rag_retrieve_node(state)

    # 重试时额外获取更多上下文
    if is_retry and device_id:
        try:
            alarm_data = get_alarm_history(device_id, limit=30)
            rag_context = rag_result.get(K.RAG_RESULTS, "")
            rag_result[K.RAG_RESULTS] = rag_context + f"\n\n## 扩展历史告警\n{_json_str(alarm_data)}"
        except Exception:
            pass

    # 2. 并行收集证据
    logger.info("  → 并行执行 4 个子 Agent...")
    executor = SubagentExecutor()
    subs = ["regulation", "metrics"]

    tool_data = {}
    if device_id:
        tool_data["metrics"] = _json_str(get_device_status(device_id))
        tool_data["log"] = _json_str(get_device_logs(device_id))
        tool_data["ticket"] = _json_str(get_defect_tickets(device_id))
    tool_data["regulation"] = _json_str(search_safety_rules(input_text[:50]))

    sub_results = await executor.execute_parallel(subs, input_text, tool_data)
    sub_context = ""
    for sr in sub_results:
        sub_context += f"\n## {sr.name} 分析结果\n{sr.result}\n"

    # 3. 组装上下文
    rag_context = rag_result.get(K.RAG_RESULTS, "")
    full_context = f"""## 故障描述
{input_text}

## 知识库参考
{rag_context}

## 多维度分析
{sub_context}

## 设备信息
设备ID: {device_id or '未知'}
"""

    # 4. 综合诊断
    logger.info("  → DiagnosisAgent 综合诊断...")
    diag_agent = DiagnosisAgent()
    diag_result = diag_agent.diagnose(full_context, skill_context)

    # 5. 风险审查
    logger.info("  → RiskReviewAgent 安全审查...")
    rules = search_safety_rules(diag_result.get("root_cause", ""))
    review_agent = RiskReviewAgent()
    safety_result = review_agent.review(
        diag_result.get("report_text", ""),
        rules.get("rules", []),
    )

    # 5.5 Judge 五维度质量评分
    logger.info("  → JudgeAgent 质量评估...")
    judge = JudgeAgent()
    evidence_ctx = {
        "evidence_count": len(sub_results) + (1 if rag_context else 0),
        "device_type": entities.get("device_type", "未知"),
        "has_scada": bool(device_id),
        "has_multimodal": False,
        "retry_count": loop_count - 1,
    }
    judge_result = judge.evaluate(diag_result.get("report_text", ""), evidence_ctx)
    judge_score = judge_result.get("total_score", 50)

    # 6. 组装结果
    result = {
        K.LOOP_COUNT: loop_count,
        K.CONFIDENCE: judge_score / 100.0,  # 使用 Judge 评分作为置信度
        K.EVIDENCE_SCORE: judge_result.get("dimensions", {}).get("evidence", {}).get("score", 80) / 100.0,
        K.EVIDENCE_COVERAGE: judge_result.get("dimensions", {}).get("evidence", {}).get("score", 80) / 100.0,
        K.EXECUTION_RESULT: diag_result.get("report_text", ""),
        K.DIAGNOSIS_RESULT: {
            "root_causes": [
                {
                    "cause": diag_result.get("root_cause", "未知"),
                    "probability": diag_result.get("confidence", 0.5),
                }
            ],
            "analysis": diag_result.get("report_text", ""),
        },
        K.CONFIDENCE: diag_result.get("confidence", 0.5),
        K.RISK_LEVEL: diag_result.get("risk_level", safety_result.get("risk_level", "MEDIUM")),
        K.EVIDENCE: sub_results,
        K.EVIDENCE_SCORE: 0.8,
        K.EVIDENCE_COVERAGE: 0.8,
        **entity_result,
        **rag_result,
    }
    return result


async def run_knowledge_qa_subgraph(state: AgentState) -> dict[str, Any]:
    """KnowledgeQA 子图运行器: QueryRewrite → RAG → Rerank → ReAct → Review

    从 PowerEmergencyGraph._run_knowledge_qa 迁移而来。
    """
    from app.graph.subgraphs.knowledge_qa import (
        query_rewrite_node, rag_retrieve_node, rerank_node,
        react_qa_node, answer_review_node, answer_review_dispatch,
    )

    logger.info("  → KnowledgeQA 子图")
    updates = {}

    updates.update(query_rewrite_node(state))
    updates.update(rag_retrieve_node(state))
    updates.update(rerank_node(state))
    updates.update(react_qa_node(state))

    for attempt in range(2):
        merged = {**state, **updates}
        updates.update(answer_review_node(merged))
        decision = answer_review_dispatch(merged)
        if decision == "accept":
            break
        logger.info(f"  回答质量不足，重新检索 (第{attempt + 1}次)")
        updates.update(rag_retrieve_node(merged))
        updates.update(react_qa_node(merged))

    return updates


async def run_chat_subgraph(state: AgentState) -> dict[str, Any]:
    """Chat 子图运行器: 简单 LLM 对话"""
    from app.graph.subgraphs.chat import chat_agent_node
    return chat_agent_node(state)
