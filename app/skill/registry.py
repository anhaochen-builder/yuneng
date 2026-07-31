"""Skill 注册与子智能体管理

每个 Skill 对应一个子智能体（BaseSubAgent），不再仅仅是 Prompt 模板。
Skill 注册时自动关联对应的子智能体实例。

Supervisor 通过意图匹配找到对应子智能体，调度执行。
"""

import logging
from typing import Optional

from app.graph.sub_agent import BaseSubAgent, SubAgentRegistry, sub_agent_registry

logger = logging.getLogger(__name__)


class Skill:
    """技能定义 — 关联一个子智能体"""

    def __init__(
        self,
        skill_id: str,
        name: str,
        description: str,
        category: str,
        intent_triggers: list[str],
        sub_agent: BaseSubAgent,
        tools: list[str] = None,
    ):
        self.skill_id = skill_id
        self.name = name
        self.description = description
        self.category = category
        self.intent_triggers = intent_triggers
        self.sub_agent = sub_agent  # 关联的子智能体实例
        self.tools = tools or []

    @property
    def prompt_template(self) -> str:
        """兼容旧接口：返回子智能体的描述作为 prompt"""
        return f"## {self.name}\n{self.description}"


class SkillRegistry:
    """技能注册中心 — Skill → SubAgent 映射管理"""

    def __init__(self):
        self._skills: dict[str, Skill] = {}
        self._intent_map: dict[str, list[str]] = {}

    def register(self, skill: Skill):
        """注册技能并关联子智能体"""
        self._skills[skill.skill_id] = skill

        sub_agent_registry.register(skill.sub_agent)

        for intent in skill.intent_triggers:
            if intent not in self._intent_map:
                self._intent_map[intent] = []
            if skill.skill_id not in self._intent_map[intent]:
                self._intent_map[intent].append(skill.skill_id)

        logger.info(
            f"注册 Skill: {skill.skill_id} ({skill.name}) "
            f"→ 子智能体: {skill.sub_agent.meta.agent_id}"
        )

    def get(self, skill_id: str) -> Optional[Skill]:
        return self._skills.get(skill_id)

    def select_by_intent(self, intent: str) -> Optional[Skill]:
        """根据意图匹配 Skill（返回优先级最高的）"""
        skill_ids = self._intent_map.get(intent, [])
        if not skill_ids:
            return None
        return self._skills.get(skill_ids[0])

    def get_sub_agent(self, skill_id: str) -> Optional[BaseSubAgent]:
        skill = self.get(skill_id)
        return skill.sub_agent if skill else None

    def list_all(self) -> list[dict]:
        return [
            {
                "skill_id": s.skill_id,
                "name": s.name,
                "description": s.description,
                "category": s.category,
                "triggers": s.intent_triggers,
                "agent_id": s.sub_agent.meta.agent_id,
            }
            for s in self._skills.values()
        ]

    def list_agents(self) -> list[dict]:
        """列出所有已注册的子智能体"""
        return sub_agent_registry.list_all()


skill_registry = SkillRegistry()
