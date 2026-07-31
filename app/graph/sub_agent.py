"""子智能体基类 — 每个 Skill 对应一个标准 LangGraph 子图

设计原则：
1. 每个子智能体是一个独立的 CompiledGraph（子图），可被 Supervisor 调度
2. 子智能体有独立的内部状态和节点链
3. 接口统一：build() 构建子图，arun(state) 异步执行
4. 支持并行调度：多个子智能体可并行执行
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph

from app.graph.state import AgentState

logger = logging.getLogger(__name__)


@dataclass
class SubAgentMeta:
    """子智能体元信息"""
    agent_id: str
    name: str
    description: str
    category: str  # diagnosis / analysis / review / multimodal / report
    intent_triggers: list[str] = field(default_factory=list)
    required_tools: list[str] = field(default_factory=list)
    priority: int = 5  # 1-10，越高越优先调度


class BaseSubAgent(ABC):
    """子智能体基类

    每个子智能体 = 元信息 + 内部 StateGraph（子图）

    使用方式：
        class MySubAgent(BaseSubAgent):
            meta = SubAgentMeta(agent_id="my-agent", name="我的智能体", ...)

            def build_nodes(self, builder: StateGraph):
                builder.add_node("step1", self.step1)
                builder.add_node("step2", self.step2)
                builder.add_edge(START, "step1")
                builder.add_edge("step1", "step2")
                builder.add_edge("step2", END)
    """

    meta: SubAgentMeta

    def __init__(self):
        self._subgraph: Optional[CompiledStateGraph] = None

    # ================================================================
    # 子图构建
    # ================================================================

    def build(self) -> CompiledStateGraph:
        """构建并编译子图（懒加载）"""
        if self._subgraph is not None:
            return self._subgraph

        builder = StateGraph(AgentState)
        self.build_nodes(builder)
        self._subgraph = builder.compile()
        logger.info(f"子智能体 [{self.meta.agent_id}] 已编译，节点数: {len(builder.nodes)}")
        return self._subgraph

    @abstractmethod
    def build_nodes(self, builder: StateGraph) -> None:
        """子类实现：向 builder 添加节点和边"""
        ...

    # ================================================================
    # 标准执行接口
    # ================================================================

    async def arun(self, state: AgentState, config: dict = None) -> dict[str, Any]:
        """异步执行子智能体

        Args:
            state: 当前全局状态
            config: LangGraph 配置（含 thread_id 等）

        Returns:
            部分状态更新字典，key→value 将合并到全局 AgentState
        """
        subgraph = self.build()
        cfg = config or {"configurable": {"thread_id": self.meta.agent_id}}
        try:
            result = await subgraph.ainvoke(state, cfg)
            updates = {k: v for k, v in result.items() if k != "__start__" and result.get(k) != state.get(k)}
            return updates
        except Exception as e:
            logger.error(f"子智能体 [{self.meta.agent_id}] 执行失败: {e}")
            return {"_error": str(e)}

    def run(self, state: AgentState, config: dict = None) -> dict[str, Any]:
        """同步执行子智能体"""
        subgraph = self.build()
        cfg = config or {"configurable": {"thread_id": self.meta.agent_id}}
        try:
            result = subgraph.invoke(state, cfg)
            updates = {k: v for k, v in result.items() if k != "__start__" and result.get(k) != state.get(k)}
            return updates
        except Exception as e:
            logger.error(f"子智能体 [{self.meta.agent_id}] 执行失败: {e}")
            return {"_error": str(e)}

    # ================================================================
    # 辅助方法
    # ================================================================

    def can_handle(self, intent: str) -> bool:
        """判断是否能处理给定意图"""
        return intent in self.meta.intent_triggers

    @property
    def compiled_graph(self) -> CompiledStateGraph:
        return self.build()

    def __repr__(self):
        return f"SubAgent({self.meta.agent_id}, category={self.meta.category})"


# ================================================================
# 子智能体注册中心
# ================================================================

class SubAgentRegistry:
    """子智能体注册中心 — 所有子智能体的统一入口"""

    def __init__(self):
        self._agents: dict[str, BaseSubAgent] = {}

    def register(self, agent: BaseSubAgent):
        if agent.meta.agent_id in self._agents:
            logger.warning(f"子智能体 [{agent.meta.agent_id}] 已存在，将覆盖")
        self._agents[agent.meta.agent_id] = agent
        logger.info(f"注册子智能体: {agent.meta.agent_id} ({agent.meta.name})")

    def get(self, agent_id: str) -> Optional[BaseSubAgent]:
        return self._agents.get(agent_id)

    def find_by_intent(self, intent: str) -> list[BaseSubAgent]:
        """根据意图查找可处理的子智能体（按优先级排序）"""
        matches = [a for a in self._agents.values() if a.can_handle(intent)]
        matches.sort(key=lambda a: a.meta.priority, reverse=True)
        return matches

    def list_all(self) -> list[dict]:
        return [
            {
                "agent_id": a.meta.agent_id,
                "name": a.meta.name,
                "description": a.meta.description,
                "category": a.meta.category,
                "triggers": a.meta.intent_triggers,
                "tools": a.meta.required_tools,
            }
            for a in self._agents.values()
        ]

    def __len__(self):
        return len(self._agents)


sub_agent_registry = SubAgentRegistry()
