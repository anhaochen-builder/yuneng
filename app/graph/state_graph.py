"""主编排图 — StateGraph 工作流引擎
完整流程:
START → PreCheck → ContextLoad → Router → IntentDispatch
  → KnowledgeQA 子图 / Diagnosis 子图 / Chat 子图
  → SafetyReview → FinalResponse → MemorySave → END
"""

import logging
from typing import Any

from app.graph.state_keys import StateKeys as K
from app.graph.nodes.common_nodes import (
    precheck_node, context_load_node, router_node,
    safety_review_node, final_response_node, memory_save_node,
)
from app.graph.dispatcher import IntentDispatcher

logger = logging.getLogger(__name__)


class PowerEmergencyGraph:
    """驭能主编排图"""

    def __init__(self):
        self.nodes = {}
        self.edges = []
        self.conditional_edges = []

    def add_node(self, name: str, func):
        self.nodes[name] = func

    def add_edge(self, src: str, dst: str):
        self.edges.append((src, dst))

    def add_conditional_edge(self, src: str, router, mapping: dict[str, str]):
        self.conditional_edges.append((src, router, mapping))

    async def invoke(self, state: dict[str, Any]) -> dict[str, Any]:
        logger.info(f"Graph 启动: intent={state.get(K.INTENT, '?')}")
        current = "precheck"
        max_steps = 20
        step = 0

        while current != "__end__" and step < max_steps:
            step += 1
            if current not in self.nodes:
                logger.warning(f"未知节点: {current}")
                break

            logger.debug(f"  执行节点: {current}")
            result = self.nodes[current](state)
            if isinstance(result, dict):
                state.update(result)

            # 确定下一个节点
            next_node = None
            for src, dst in self.edges:
                if src == current:
                    next_node = dst
                    break

            if not next_node:
                for src, router, mapping in self.conditional_edges:
                    if src == current:
                        key = router(state)
                        next_node = mapping.get(key, mapping.get("default", "__end__"))
                        break

            if next_node == "knowledge_qa":
                from app.graph.subgraphs.knowledge_qa import (
                    query_rewrite_node, rag_retrieve_node, rerank_node,
                    react_qa_node, answer_review_node, answer_review_dispatch,
                )
                state = await self._run_knowledge_qa(state)
                next_node = "safety_review"
            elif next_node == "diagnosis":
                state = await self._run_diagnosis(state)
                next_node = "safety_review"
            elif next_node == "chat":
                from app.graph.subgraphs.chat import chat_agent_node
                result = chat_agent_node(state)
                state.update(result)
                next_node = "safety_review"

            current = next_node

        final_response_node(state)
        return state

    async def _run_knowledge_qa(self, state: dict[str, Any]) -> dict[str, Any]:
        from app.graph.subgraphs.knowledge_qa import (
            query_rewrite_node, rag_retrieve_node, rerank_node,
            react_qa_node, answer_review_node, answer_review_dispatch,
        )
        logger.info("  → KnowledgeQA 子图")
        state.update(query_rewrite_node(state))
        state.update(rag_retrieve_node(state))
        state.update(rerank_node(state))
        state.update(react_qa_node(state))

        for attempt in range(2):
            state.update(answer_review_node(state))
            decision = answer_review_dispatch(state)
            if decision == "accept":
                break
            logger.info(f"  回答质量不足，重新检索 (第{attempt+1}次)")
            state.update(rag_retrieve_node(state))
            state.update(react_qa_node(state))

        return state

    async def _run_diagnosis(self, state: dict[str, Any]) -> dict[str, Any]:
        from app.graph.subgraphs.diagnosis import (
            entity_extract_node, alarm_rag_retrieve_node, planner_node,
            executor_node, evidence_validation_node,
        )
        from app.agent.diagnosis_agent import DiagnosisAgent
        from app.agent.risk_review_agent import RiskReviewAgent
        from app.agent.subagent_executor import SubagentExecutor
        from mcp_server.tools import (
            get_device_status, get_alarm_history, get_device_logs,
            get_defect_tickets, search_safety_rules,
        )

        logger.info("  → Diagnosis 子图 (诊断流程)")
        entities = state.get(K.ENTITIES, {})
        device_id = entities.get("device_id", state.get("device_id", ""))
        input_text = state.get(K.CLEANED_INPUT, state.get(K.INPUT, ""))
        skill_context = state.get(K.SKILL_CONTEXT, "")

        state.update(entity_extract_node(state))
        state.update(alarm_rag_retrieve_node(state))

        # 2. 并行收集证据
        logger.info("  → 并行执行 4 个子 Agent...")
        executor = SubagentExecutor()
        subs = ["regulation", "metrics"]

        # 获取工具数据
        tool_data = {}
        if device_id:
            tool_data["metrics"] = json_str(get_device_status(device_id))
            tool_data["log"] = json_str(get_device_logs(device_id))
            tool_data["ticket"] = json_str(get_defect_tickets(device_id))
        tool_data["regulation"] = json_str(search_safety_rules(input_text[:50]))

        sub_results = await executor.execute_parallel(subs, input_text, tool_data)
        sub_context = ""
        for sr in sub_results:
            sub_context += f"\n## {sr.name} 分析结果\n{sr.result}\n"

        # 3. RAG 上下文 + 子Agent 结果
        rag_context = state.get(K.RAG_RESULTS, "")
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
        safety_result = review_agent.review(diag_result.get("report_text", ""), rules.get("rules", []))

        # 6. 组装结果
        result = {
            K.EXECUTION_RESULT: diag_result.get("report_text", ""),
            K.DIAGNOSIS_RESULT: {
                "root_causes": [
                    {"cause": diag_result.get("root_cause", "未知"), "probability": diag_result.get("confidence", 0.5)}
                ],
                "analysis": diag_result.get("report_text", ""),
            },
            K.CONFIDENCE: diag_result.get("confidence", 0.5),
            K.RISK_LEVEL: diag_result.get("risk_level", safety_result.get("risk_level", "MEDIUM")),
            K.EVIDENCE: sub_results,
        }
        state.update(result)
        return state


def json_str(data) -> str:
    import json
    return json.dumps(data, ensure_ascii=False, default=str)


def create_graph() -> PowerEmergencyGraph:
    """创建预配置的主编排图"""
    g = PowerEmergencyGraph()

    # 注册主节点
    g.add_node("precheck", precheck_node)
    g.add_node("context_load", context_load_node)
    g.add_node("router", router_node)
    g.add_node("safety_review", safety_review_node)
    g.add_node("final_response", final_response_node)
    g.add_node("memory_save", memory_save_node)
    g.add_node("__end__", lambda s: s)

    # 固定边
    g.add_edge("precheck", "context_load")
    g.add_edge("knowledge_qa", "safety_review")
    g.add_edge("diagnosis", "safety_review")
    g.add_edge("chat", "safety_review")
    g.add_edge("safety_review", "final_response")
    g.add_edge("final_response", "memory_save")
    g.add_edge("memory_save", "__end__")

    # 条件边: Router → 按意图分发
    dispatcher = IntentDispatcher()
    g.add_conditional_edge("router", dispatcher.dispatch, {
        "knowledge_qa": "knowledge_qa",
        "diagnosis": "diagnosis",
        "chat": "chat",
    })

    # ContextLoad → Router 的隐式边通过流程连续性保证
    g.add_edge("context_load", "router")

    return g
