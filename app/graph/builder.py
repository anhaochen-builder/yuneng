"""Graph Builder — 基于 LangGraph StateGraph 构建主编排图

完整流程:
START → precheck → context_load → router ─条件路由─→ knowledge_qa / diagnosis / chat
  → safety_review → final_response → memory_save → END

替代原有的 PowerEmergencyGraph 自实现图执行器。
"""

import logging
from pathlib import Path
from typing import Any, Hashable

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.graph.state import AgentState
from app.graph.state_keys import StateKeys as K
from app.graph.nodes.common_nodes import (
    precheck_node, context_load_node, router_node,
    safety_review_node, final_response_node, memory_save_node,
)
from app.graph.subgraphs.runners import (
    run_diagnosis_subgraph,
    run_knowledge_qa_subgraph,
    run_chat_subgraph,
)
from app.config import settings

logger = logging.getLogger(__name__)

# ============================================================
# 路由函数
# ============================================================

def route_by_intent(state: AgentState) -> str:
    """根据意图类型路由到对应子图

    复用 IntentDispatcher 的分发逻辑。
    """
    intent = state.get(K.INTENT, "CHAT")

    # KnowledgeQA 类意图
    if intent in ("KNOWLEDGE_QA", "SAFETY_QA", "DEVICE_STATUS",
                   "DEVICE_PROFILE", "ALARM_QUERY"):
        return "knowledge_qa"

    # Diagnosis 类意图
    if intent in ("DIAGNOSIS", "FAULT_DIAGNOSIS", "ALARM_DIAGNOSIS",
                   "ALARM_ANALYSIS", "LOG_ANALYSIS", "TICKET_QUERY"):
        return "diagnosis"

    # 默认走对话通道
    return "chat"


def route_after_diagnosis(state: AgentState) -> str:
    """诊断完成后：检查是否需要重规划

    loop_count 由 run_diagnosis_subgraph 在每次进入时递增:
    - 首次运行后 loop_count=1, 允许 ≤ max_retries(2) 时重试
    - 最多重试 2 次（共 3 次诊断），之后强制进入安全审查
    """
    confidence = state.get(K.CONFIDENCE, 0.5)
    loop_count = state.get(K.LOOP_COUNT, 0)
    max_retries = state.get("max_retries", settings.max_retries)

    if confidence < settings.confidence_threshold and loop_count <= max_retries:
        logger.info(
            f"  置信度 {confidence:.2f} < {settings.confidence_threshold}，"
            f"触发重规划 (第{loop_count}次诊断完成，最多允许{max_retries}次重试)"
        )
        return "diagnosis"
    return "safety_review"


# ============================================================
# Checkpointer 工厂
# ============================================================

def _create_checkpointer():
    """创建 Checkpointer

    优先尝试 SqliteSaver（需单独安装 langgraph-checkpoint-sqlite），
    降级使用 MemorySaver。
    """
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
        db_path = Path(settings.data_dir) / "checkpoints.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        checkpointer = SqliteSaver.from_conn_string(str(db_path))
        logger.info(f"SqliteSaver 已初始化: {db_path}")
        return checkpointer
    except ImportError:
        logger.info("SqliteSaver 不可用（未安装 langgraph-checkpoint-sqlite），使用 MemorySaver")
        return MemorySaver()
    except Exception as e:
        logger.warning(f"SqliteSaver 初始化失败 ({e})，降级使用 MemorySaver")
        return MemorySaver()


# ============================================================
# Graph 构建入口
# ============================================================

def build_graph(use_checkpointer: bool = True):
    """构建并编译 LangGraph StateGraph

    Args:
        use_checkpointer: 是否启用 Checkpointer 持久化

    Returns:
        编译后的 CompiledGraph 实例，可通过 .ainvoke(state, config) 调用
    """
    builder = StateGraph(AgentState)

    # ---- 注册主节点 ----
    builder.add_node("precheck", precheck_node)
    builder.add_node("context_load", context_load_node)
    builder.add_node("router", router_node)

    # 子图节点（async 函数，LangGraph 自动处理）
    builder.add_node("knowledge_qa", run_knowledge_qa_subgraph)
    builder.add_node("diagnosis", run_diagnosis_subgraph)
    builder.add_node("chat", run_chat_subgraph)

    builder.add_node("safety_review", safety_review_node)
    builder.add_node("final_response", final_response_node)
    builder.add_node("memory_save", memory_save_node)

    # ---- 固定边 ----
    builder.add_edge(START, "precheck")
    builder.add_edge("precheck", "context_load")
    builder.add_edge("context_load", "router")

    # ---- 条件路由: router → 三个子图 ----
    builder.add_conditional_edges(
        "router",
        route_by_intent,
        {
            "knowledge_qa": "knowledge_qa",
            "diagnosis": "diagnosis",
            "chat": "chat",
        },
    )

    # ---- 子图 → safety_review ----
    builder.add_edge("knowledge_qa", "safety_review")

    # Diagnosis 子图 → 条件判断（是否需要重规划）
    builder.add_conditional_edges(
        "diagnosis",
        route_after_diagnosis,
        {
            "diagnosis": "diagnosis",      # 重规划：回到 diagnosis 重新诊断
            "safety_review": "safety_review",  # 通过：进入安全审查
        },
    )

    builder.add_edge("chat", "safety_review")
    builder.add_edge("safety_review", "final_response")
    builder.add_edge("final_response", "memory_save")
    builder.add_edge("memory_save", END)

    # ---- 编译 ----
    checkpointer = _create_checkpointer() if use_checkpointer else None
    compiled = builder.compile(checkpointer=checkpointer)
    logger.info("Graph 编译完成，节点数: %d", len(builder.nodes))
    return compiled


# ============================================================
# 全局单例
# ============================================================

_graph_instance = None


def get_graph():
    """获取全局编译后的 Graph 实例（懒加载）"""
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = build_graph()
    return _graph_instance
