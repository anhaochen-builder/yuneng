"""子智能体运行器 — 在 Supervisor 主图中调度执行子智能体

每个子智能体作为一个 LangGraph 节点存在，通过 sub_agent_registry 查找和执行。
"""

import logging
from typing import Any

from app.graph.state import AgentState
from app.graph.state_keys import StateKeys as K
from app.graph.sub_agent import sub_agent_registry

logger = logging.getLogger(__name__)


async def run_sub_agent(agent_id: str, state: AgentState) -> dict[str, Any]:
    """通用的子智能体运行器

    Args:
        agent_id: 子智能体ID（在 sub_agent_registry 中注册）
        state: 当前全局 AgentState

    Returns:
        部分状态更新字典
    """
    agent = sub_agent_registry.get(agent_id)
    if not agent:
        logger.warning(f"子智能体 [{agent_id}] 未注册，跳过")
        return {}

    config = {"configurable": {"thread_id": f"{agent_id}_{state.get(K.TASK_ID, 'unknown')}"}}
    return await agent.arun(state, config)


def run_sub_agent_sync(agent_id: str, state: AgentState) -> dict[str, Any]:
    """同步版本的子智能体运行器"""
    agent = sub_agent_registry.get(agent_id)
    if not agent:
        logger.warning(f"子智能体 [{agent_id}] 未注册，跳过")
        return {}

    config = {"configurable": {"thread_id": f"{agent_id}_{state.get(K.TASK_ID, 'unknown')}"}}
    return agent.run(state, config)


# ================================================================
# 便捷包装函数（兼容旧接口）
# ================================================================

async def run_diagnosis_subgraph(state: AgentState) -> dict[str, Any]:
    """Diagnosis 子智能体运行器 — 带循环计数"""
    loop = state.get(K.LOOP_COUNT, 0) + 1
    state[K.LOOP_COUNT] = loop
    logger.info(f"  → Diagnosis 子智能体 (第{loop}次)")
    return await run_sub_agent("diagnosis-agent", state)


async def run_knowledge_qa_subgraph(state: AgentState) -> dict[str, Any]:
    """KnowledgeQA 子智能体运行器（兼容旧接口）"""
    logger.info("  → KnowledgeQA 子智能体")
    return await run_sub_agent("knowledge-qa-agent", state)


async def run_chat_subgraph(state: AgentState) -> dict[str, Any]:
    """Chat 子智能体运行器（兼容旧接口）"""
    logger.info("  → Chat 子智能体")
    return await run_sub_agent("chat-agent", state)


async def run_scada_subgraph(state: AgentState) -> dict[str, Any]:
    """SCADA 子智能体运行器"""
    logger.info("  → SCADA 子智能体")
    return await run_sub_agent("scada-agent", state)


async def run_multimodal_subgraph(state: AgentState) -> dict[str, Any]:
    """多模态子智能体运行器"""
    logger.info("  → 多模态子智能体")
    return await run_sub_agent("multimodal-agent", state)


async def run_report_subgraph(state: AgentState) -> dict[str, Any]:
    """报告生成子智能体运行器"""
    logger.info("  → 报告生成子智能体")
    return await run_sub_agent("report-agent", state)
