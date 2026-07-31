"""Chat 子智能体 — 通用对话

1 节点内部流程:
  START → ChatNode → END
"""

import logging
from typing import Any

from langgraph.graph import StateGraph, START, END

from app.graph.sub_agent import BaseSubAgent, SubAgentMeta
from app.graph.state_keys import StateKeys as K
from app.agent.llm_client import llm

logger = logging.getLogger(__name__)

CHAT_PROMPT = (
    "你是驭能智能诊断系统的对话助手。你是新能源场站的运维专家，"
    "可以回答关于设备故障、安全规程、系统使用等问题。"
    "如果是故障诊断，请引导用户提供详细的故障现象和设备信息。"
)


class ChatSubAgent(BaseSubAgent):
    meta = SubAgentMeta(
        agent_id="chat-agent",
        name="通用对话助手",
        description="处理用户日常咨询、系统使用指导等非诊断场景的对话",
        category="diagnosis",
        intent_triggers=["CHAT", "GENERAL_CHAT"],
        required_tools=[],
        priority=5,
    )

    def build_nodes(self, builder: StateGraph) -> None:
        builder.add_node("chat", self._chat_node)
        builder.add_edge(START, "chat")
        builder.add_edge("chat", END)

    def _chat_node(self, state: dict[str, Any]) -> dict[str, Any]:
        question = state.get(K.INPUT, "")
        history = state.get(K.HISTORY, "")
        skill_context = state.get(K.SKILL_CONTEXT, "")
        rag_context = state.get(K.RAG_RESULTS, "")

        prompt = CHAT_PROMPT
        if skill_context:
            prompt += f"\n\n场景指导：{skill_context}"
        if rag_context:
            prompt += f"\n\n参考资料：{rag_context[:1000]}"

        try:
            answer = llm.chat(prompt, question, temperature=0.5, max_tokens=2048)
        except Exception as e:
            logger.error(f"Chat 对话失败: {e}")
            answer = f"抱歉，系统遇到了问题: {e}\n请稍后重试或联系运维人员。"

        return {
            K.FINAL_RESPONSE: answer,
            K.EXECUTION_RESULT: answer,
            K.INTENT: "CHAT",
        }
