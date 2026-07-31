"""KnowledgeQA 子智能体 — 知识库问答引擎

5 节点内部流程:
  START → QueryRewrite → RAGRetrieve → Rerank → Answer → Review → END

负责基于知识库和安规库回答运维人员的知识性问题。
"""

import logging
from typing import Any

from langgraph.graph import StateGraph, START, END

from app.graph.sub_agent import BaseSubAgent, SubAgentMeta
from app.graph.state_keys import StateKeys as K
from app.agent.llm_client import llm
from app.rag.hybrid_search import HybridSearchService
from app.rag.knowledge_graph import KnowledgeGraphService
from app.graph.hooks.hooks import create_hook_engine, HookContext, HOOK_POINTS

logger = logging.getLogger(__name__)

hybrid_search = HybridSearchService()
kg_service = KnowledgeGraphService()
hook_engine = create_hook_engine()


class KnowledgeQASubAgent(BaseSubAgent):
    meta = SubAgentMeta(
        agent_id="knowledge-qa-agent",
        name="知识库问答专家",
        description="基于新能源场站知识库、安全规程和历史案例提供精准知识问答",
        category="diagnosis",
        intent_triggers=[
            "KNOWLEDGE_QA", "SAFETY_QA", "DEVICE_STATUS",
            "DEVICE_PROFILE", "ALARM_QUERY",
        ],
        required_tools=["search_safety_rules"],
        priority=9,
    )

    def build_nodes(self, builder: StateGraph) -> None:
        builder.add_node("query_rewrite", self._query_rewrite_node)
        builder.add_node("rag_retrieve", self._rag_retrieve_node)
        builder.add_node("rerank", self._rerank_node)
        builder.add_node("answer", self._answer_node)
        builder.add_node("review", self._review_node)

        builder.add_edge(START, "query_rewrite")
        builder.add_edge("query_rewrite", "rag_retrieve")
        builder.add_edge("rag_retrieve", "rerank")
        builder.add_edge("rerank", "answer")
        builder.add_edge("answer", "review")

        builder.add_conditional_edges(
            "review",
            self._review_router,
            {"retry": "rag_retrieve", "accept": END},
        )

    def _query_rewrite_node(self, state: dict[str, Any]) -> dict[str, Any]:
        query = state.get(K.CLEANED_INPUT, state.get(K.INPUT, ""))
        entities = state.get(K.ENTITIES, {})
        device_type = entities.get("device_type", "")
        if device_type and device_type not in query:
            query = f"{device_type} {query}"
        try:
            rewritten = llm.chat(
                "你是查询改写专家。将用户问题改写为更适合检索的关键词查询，保留核心语义。直接输出改写后的查询文本。",
                query, temperature=0.1, max_tokens=256,
            )
            return {K.REWRITTEN_QUERY: rewritten.strip() or query}
        except Exception:
            return {K.REWRITTEN_QUERY: query}

    def _rag_retrieve_node(self, state: dict[str, Any]) -> dict[str, Any]:
        query = state.get(K.REWRITTEN_QUERY, state.get(K.INPUT, ""))
        ctx = HookContext(input=query, entities=state.get(K.ENTITIES, {}))
        ctx = hook_engine.execute_hooks(HOOK_POINTS["PRE_RAG"], ctx)

        results = hybrid_search.search(ctx.input or query, top_k=10)
        graph_context = kg_service.build_graph_context(query)

        rag_parts = []
        if graph_context:
            rag_parts.append(graph_context)
        rag_parts.extend([f"[参考{i+1}] {r['text'][:500]}" for i, r in enumerate(results[:5])])
        rag_text = "\n\n".join(rag_parts)

        ctx.metadata["rag_count"] = len(results)
        ctx = hook_engine.execute_hooks(HOOK_POINTS["POST_RAG"], ctx)
        return {K.RAG_RESULTS: rag_text, K.EXECUTION_RESULT: rag_text}

    def _rerank_node(self, state: dict[str, Any]) -> dict[str, Any]:
        return {}

    def _answer_node(self, state: dict[str, Any]) -> dict[str, Any]:
        question = state.get(K.INPUT, "")
        rag_context = state.get(K.RAG_RESULTS, "")
        skill_context = state.get(K.SKILL_CONTEXT, "")

        prompt = (
            "你是电力智能运维知识问答专家。请根据参考资料准确回答用户问题。\n\n"
            f"参考资料：\n{rag_context}\n\n"
            f'{"业务场景指导：" + skill_context if skill_context else ""}\n\n'
            "重要规则：\n"
            "- 优先使用参考资料中的信息回答\n"
            "- 如果参考资料不充分，可以结合电力领域常识补充\n"
            "- 在回答末尾列出引用的资料来源\n"
            "- 涉及安全操作时，必须提示遵守现场规程"
        )
        answer = llm.chat(prompt, question, temperature=0.3, max_tokens=2048)
        return {K.FINAL_RESPONSE: answer, K.EXECUTION_RESULT: answer}

    def _review_node(self, state: dict[str, Any]) -> dict[str, Any]:
        answer = state.get(K.FINAL_RESPONSE, "")
        loop = state.get(K.LOOP_COUNT, 0) + 1
        if len(answer) < 50:
            return {K.LOOP_COUNT: loop, K.REVIEW_DECISION: "NEED_MORE"}
        return {K.LOOP_COUNT: loop, K.REVIEW_DECISION: "ACCEPT"}

    def _review_router(self, state: dict[str, Any]) -> str:
        decision = state.get(K.REVIEW_DECISION, "ACCEPT")
        loop = state.get(K.LOOP_COUNT, 0)
        if decision == "NEED_MORE" and loop < 2:
            return "retry"
        return "accept"
