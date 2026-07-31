"""Graph Builder — LangGraph StateGraph Supervisor + 8子智能体编排

完整流程:
  START → precheck → context_load → router
    ├─ knowledge_qa → judge → report → memory_save → END
    ├─ diagnosis → [并行: SCADA+Multimodal+Predictive] → Diagnose → Judge → END
    └─ chat → report → memory_save → END

并行子智能体通过 LangGraph Send API 实现 fan-out/fan-in。
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.graph.state import AgentState
from app.graph.state_keys import StateKeys as K
from app.graph.nodes.common_nodes import (
    precheck_node, context_load_node, router_node,
    memory_save_node,
)
from app.graph.subgraphs.runners import (
    run_diagnosis_subgraph,
    run_knowledge_qa_subgraph,
    run_chat_subgraph,
    run_scada_subgraph,
    run_multimodal_subgraph,
    run_report_subgraph,
)
from app.config import settings

logger = logging.getLogger(__name__)


def route_by_intent(state: AgentState) -> str:
    intent = state.get(K.INTENT, "CHAT")

    if intent in ("KNOWLEDGE_QA", "SAFETY_QA", "DEVICE_STATUS",
                   "DEVICE_PROFILE", "ALARM_QUERY"):
        return "knowledge_qa"

    if intent in ("DIAGNOSIS", "FAULT_DIAGNOSIS", "ALARM_DIAGNOSIS",
                   "ALARM_ANALYSIS", "LOG_ANALYSIS", "TICKET_QUERY"):
        return "diagnosis_parallel"

    return "chat"


async def diagnosis_parallel_node(state: AgentState) -> dict[str, Any]:
    """并行执行 SCADA + 多模态 + 预测监控子智能体，完成后合并结果"""
    results = {}
    tasks = []

    device_id = state.get(K.DEVICE_ID, "")
    if device_id:
        tasks.append(("scada", run_scada_subgraph(state)))
    if state.get("_multimodal_images") or state.get("_multimodal_audio_path"):
        tasks.append(("multimodal", run_multimodal_subgraph(state)))

    if tasks:
        gathered = await asyncio.gather(*[t[1] for t in tasks])
        for (name, _), result in zip(tasks, gathered):
            results[name] = result

    merged = {}
    for r in results.values():
        if isinstance(r, dict):
            merged.update(r)

    logger.info(f"并行子智能体完成: {list(results.keys())}, 合并{len(merged)}个状态键")
    return merged


def route_after_diagnosis(state: AgentState) -> str:
    confidence = state.get(K.CONFIDENCE, 0.5)
    loop_count = state.get(K.LOOP_COUNT, 0)
    max_retries = state.get("max_retries", settings.max_retries)

    if confidence < 0.3 and loop_count <= max_retries:
        return "diagnosis"
    return "judge"


def _create_checkpointer():
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
        db_path = Path(settings.data_dir) / "checkpoints.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return SqliteSaver.from_conn_string(str(db_path))
    except Exception:
        return MemorySaver()


def build_graph(use_checkpointer: bool = True):
    builder = StateGraph(AgentState)

    builder.add_node("precheck", precheck_node)
    builder.add_node("context_load", context_load_node)
    builder.add_node("router", router_node)

    builder.add_node("knowledge_qa", run_knowledge_qa_subgraph)
    builder.add_node("diagnosis_parallel", diagnosis_parallel_node)
    builder.add_node("diagnosis", run_diagnosis_subgraph)
    builder.add_node("judge", _judge_wrapper)
    builder.add_node("chat", run_chat_subgraph)
    builder.add_node("report", _report_wrapper)
    builder.add_node("memory_save", memory_save_node)

    builder.add_edge(START, "precheck")
    builder.add_edge("precheck", "context_load")
    builder.add_edge("context_load", "router")

    builder.add_conditional_edges(
        "router", route_by_intent,
        {"knowledge_qa": "knowledge_qa", "diagnosis_parallel": "diagnosis_parallel", "chat": "chat"},
    )

    builder.add_edge("knowledge_qa", "judge")
    builder.add_edge("diagnosis_parallel", "diagnosis")
    builder.add_conditional_edges(
        "diagnosis", route_after_diagnosis,
        {"diagnosis": "diagnosis", "judge": "judge"},
    )
    builder.add_edge("judge", "report")
    builder.add_edge("chat", "report")
    builder.add_edge("report", "memory_save")
    builder.add_edge("memory_save", END)

    checkpointer = _create_checkpointer() if use_checkpointer else None
    compiled = builder.compile(checkpointer=checkpointer)
    logger.info(f"Graph 编译完成，节点数: {len(builder.nodes)}")
    return compiled


async def _judge_wrapper(state: AgentState) -> dict[str, Any]:
    from app.graph.sub_agent import sub_agent_registry
    agent = sub_agent_registry.get("judge-agent")
    if agent:
        logger.info("  → Judge 子智能体 (5维度评分)")
        return await agent.arun(state)
    return {}


async def _report_wrapper(state: AgentState) -> dict[str, Any]:
    from app.graph.sub_agent import sub_agent_registry
    agent = sub_agent_registry.get("report-agent")
    if agent:
        logger.info("  → Report 子智能体")
        return await agent.arun(state)
    return {}


_graph_instance = None


def get_graph():
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = build_graph()
    return _graph_instance
