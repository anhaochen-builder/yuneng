"""Chat 子图 — 简单对话"""

import logging
from typing import Any

from app.graph.state_keys import StateKeys as K
from app.agent.llm_client import llm

logger = logging.getLogger(__name__)


def chat_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """ChatAgent: 简单对话回复"""
    question = state.get(K.INPUT, "")
    history = state.get(K.HISTORY, "")
    skill_context = state.get(K.SKILL_CONTEXT, "")
    rag_context = state.get(K.RAG_RESULTS, "")

    system = "你是电力智能运维助手，帮助运维人员解答电力相关问题。回答简洁专业。"
    if skill_context:
        system += f"\n\n场景指导：{skill_context}"
    if rag_context:
        system += f"\n\n参考资料：{rag_context[:1000]}"

    answer = llm.chat(system, question, temperature=0.3, max_tokens=2048)
    return {K.FINAL_RESPONSE: answer, K.EXECUTION_RESULT: answer}
