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

    if confidence < settings.confidence_threshold and loop_count <= max_retries:
        return "diagnosis"
    return "quality_gate"


def _create_checkpointer():
    try:
        import aiosqlite
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
        db_path = str(Path(settings.data_dir) / "checkpoints.db")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = aiosqlite.connect(db_path)
        saver = AsyncSqliteSaver(conn)
        logger.info(f"AsyncSqliteSaver 持久化就绪: {db_path}")
        return saver
    except (ImportError, OSError) as e:
        logger.warning(f"AsyncSqliteSaver 不可用: {e}")
    except RuntimeError as e:
        logger.warning(f"AsyncSqliteSaver 事件循环绑定失败，降级内存模式: {e}")
    return MemorySaver()


def build_graph(use_checkpointer: bool = True):
    builder = StateGraph(AgentState)

    builder.add_node("precheck", precheck_node)
    builder.add_node("context_load", context_load_node)
    builder.add_node("router", router_node)

    builder.add_node("knowledge_qa", run_knowledge_qa_subgraph)
    builder.add_node("diagnosis_parallel", diagnosis_parallel_node)
    builder.add_node("diagnosis", run_diagnosis_subgraph)
    builder.add_node("quality_gate", _quality_gate_wrapper)
    builder.add_node("chat", run_chat_subgraph)
    builder.add_node("memory_save", memory_save_node)

    builder.add_edge(START, "precheck")
    builder.add_edge("precheck", "context_load")
    builder.add_edge("context_load", "router")

    builder.add_conditional_edges(
        "router", route_by_intent,
        {"knowledge_qa": "knowledge_qa", "diagnosis_parallel": "diagnosis_parallel", "chat": "chat"},
    )

    builder.add_edge("knowledge_qa", "quality_gate")
    builder.add_edge("diagnosis_parallel", "diagnosis")
    builder.add_conditional_edges(
        "diagnosis", route_after_diagnosis,
        {"diagnosis": "diagnosis", "quality_gate": "quality_gate"},
    )
    builder.add_edge("chat", "quality_gate")
    builder.add_edge("quality_gate", "memory_save")
    builder.add_edge("memory_save", END)

    checkpointer = _create_checkpointer() if use_checkpointer else None
    compiled = builder.compile(checkpointer=checkpointer)
    logger.info(f"Graph 编译完成，节点数: {len(builder.nodes)}")
    return compiled


async def _quality_gate_wrapper(state: AgentState) -> dict[str, Any]:
    confidence = state.get(K.CONFIDENCE, 0.5)
    if confidence < 0.7:
        from app.graph.sub_agent import sub_agent_registry
        judge_agent = sub_agent_registry.get("judge-agent")
        if judge_agent:
            try:
                result = await judge_agent.arun(state)
                score = result.get("judge_score", 60)
                result[K.CONFIDENCE] = max(confidence, score / 100.0)
                return result
            except Exception as e:
                logger.warning(f"Judge Agent 评估失败: {e}")
    return {}


def get_graph():
    return build_graph()
