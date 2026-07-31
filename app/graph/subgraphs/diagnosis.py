"""Diagnosis 子智能体 — 9 节点完整诊断流程

1. EntityExtract → 2. AlarmRAG → 3. Planner → 4. Executor(4并行)
→ 5. EvidenceValidation → 6. Diagnose → 7. Replanner
→ 8. RiskAssessment → 9. ActionRecommend

符合项目技术文档 3.5 节精确规格。
"""

import asyncio
import json
import logging
from typing import Any

from langgraph.graph import StateGraph, START, END

from app.graph.sub_agent import BaseSubAgent, SubAgentMeta
from app.graph.state_keys import StateKeys as K
from app.agent.llm_client import llm
from app.rag.hybrid_search import HybridSearchService
from app.rag.knowledge_graph import KnowledgeGraphService
from app.rag.graphrag import graphrag_service
from app.graph.hooks.hooks import create_hook_engine, HookContext, HOOK_POINTS
from app.config import settings

logger = logging.getLogger(__name__)

hybrid_search = HybridSearchService()
kg_service = KnowledgeGraphService()
hook_engine = create_hook_engine()


class DiagnosisSubAgent(BaseSubAgent):
    meta = SubAgentMeta(
        agent_id="diagnosis-agent",
        name="故障诊断核心引擎",
        description="9节点完整诊断流程: 实体提取→RAG检索→计划制定→并行执行→证据验证→综合诊断→重规划→风险评估→行动建议",
        category="diagnosis",
        intent_triggers=[
            "DIAGNOSIS", "FAULT_DIAGNOSIS", "ALARM_DIAGNOSIS",
            "ALARM_ANALYSIS", "LOG_ANALYSIS", "TICKET_QUERY",
        ],
        required_tools=["get_device_status", "get_alarm_history", "get_device_logs",
                         "get_defect_tickets", "search_safety_rules", "get_device_profile"],
        priority=10,
    )

    def build_nodes(self, builder: StateGraph) -> None:
        builder.add_node("entity_extract", self._node_entity_extract)
        builder.add_node("alarm_rag", self._node_alarm_rag)
        builder.add_node("planner", self._node_planner)
        builder.add_node("executor", self._node_executor)
        builder.add_node("evidence_validation", self._node_evidence_validation)
        builder.add_node("diagnose", self._node_diagnose)
        builder.add_node("replanner", self._node_replanner)
        builder.add_node("risk_assessment", self._node_risk_assessment)
        builder.add_node("action_recommend", self._node_action_recommend)

        builder.add_edge(START, "entity_extract")
        builder.add_edge("entity_extract", "alarm_rag")
        builder.add_edge("alarm_rag", "planner")
        builder.add_edge("planner", "executor")
        builder.add_edge("executor", "evidence_validation")
        builder.add_conditional_edges(
            "evidence_validation", self._route_evidence,
            {"diagnose": "diagnose", "planner": "planner"},
        )
        builder.add_edge("diagnose", "replanner")
        builder.add_conditional_edges(
            "replanner", self._route_replan,
            {"alarm_rag": "alarm_rag", "risk_assessment": "risk_assessment"},
        )
        builder.add_edge("risk_assessment", "action_recommend")
        builder.add_edge("action_recommend", END)

    # ================================================================
    # ① Entity Extract
    # ================================================================
    def _node_entity_extract(self, state: dict[str, Any]) -> dict[str, Any]:
        text = state.get(K.CLEANED_INPUT, state.get(K.INPUT, ""))
        entities = kg_service.extract_entities(text)
        graph_entities = graphrag_service.extract_entities(text)
        entities.update({k: v for k, v in graph_entities.items() if v and v != "未知"})
        logger.info(f"  ① EntityExtract: device={entities.get('device_type')}, fault={entities.get('possible_faults', [])}")

        device_id = entities.get("device_id", "")
        if not device_id:
            import re
            match = re.search(r'[A-Z]+\d+', text)
            if match:
                device_id = match.group()

        return {K.ENTITIES: entities, K.DEVICE_ID: device_id}

    # ================================================================
    # ② Alarm RAG — 三重混合检索
    # ================================================================
    def _node_alarm_rag(self, state: dict[str, Any]) -> dict[str, Any]:
        query = state.get(K.REWRITTEN_QUERY, state.get(K.INPUT, ""))
        entities = state.get(K.ENTITIES, {})

        ctx = HookContext(input=query, entities=entities)
        ctx = hook_engine.execute_hooks(HOOK_POINTS["PRE_RAG"], ctx)

        device_type = entities.get("device_type", "")
        if device_type and device_type not in query:
            query = f"{device_type} {query}"

        keyword_results = hybrid_search.search(query, top_k=10)
        graph_context = kg_service.build_graph_context(query)
        graphrag_context = graphrag_service.build_graph_context(query)

        rag_parts = []
        if graph_context:
            rag_parts.append(graph_context)
        if graphrag_context:
            rag_parts.append(graphrag_context)
        rag_parts.extend([f"[参考{i+1}] {r['text'][:400]}" for i, r in enumerate(keyword_results[:5])])
        rag_text = "\n\n".join(rag_parts)

        ctx.metadata["rag_count"] = len(keyword_results)
        ctx = hook_engine.execute_hooks(HOOK_POINTS["POST_RAG"], ctx)

        logger.info(f"  ② AlarmRAG: {len(keyword_results)}条 → RAG上下文{len(rag_text)}字")
        return {K.RAG_RESULTS: rag_text, K.REWRITTEN_QUERY: query}

    # ================================================================
    # ③ Planner — LLM 制定诊断计划
    # ================================================================
    def _node_planner(self, state: dict[str, Any]) -> dict[str, Any]:
        input_text = state.get(K.INPUT, "")
        entities = state.get(K.ENTITIES, {})
        rag_context = state.get(K.RAG_RESULTS, "")[:1500]

        prompt = f"""你是故障诊断计划专家。根据以下信息制定诊断计划。

故障描述: {input_text}
实体信息: {json.dumps(entities, ensure_ascii=False)}
知识库参考: {rag_context[:800]}

生成 JSON 格式的诊断计划步骤列表:
{{"steps":[{{"step_id":"1","type":"rag/tool/diagnosis","action":"步骤名","description":"详细说明","tool":"工具名(可选)"}}]}}"""

        try:
            plan = llm.chat_json("你输出JSON格式诊断计划。", prompt, temperature=0.1)
            steps = plan.get("steps", [{"step_id": "1", "type": "diagnosis", "action": "综合诊断", "description": "收集所有证据后执行综合诊断"}])
        except Exception:
            steps = [{"step_id": "1", "type": "diagnosis", "action": "综合诊断", "description": "执行综合故障诊断"}]

        logger.info(f"  ③ Planner: {len(steps)}个步骤")
        return {K.PLAN_STEPS: steps, K.CURRENT_STEP_INDEX: 0}

    # ================================================================
    # ④ Executor — 4并行子Agent执行
    # ================================================================
    def _node_executor(self, state: dict[str, Any]) -> dict[str, Any]:
        device_id = state.get(K.DEVICE_ID, "")
        input_text = state.get(K.INPUT, "")
        rag_context = state.get(K.RAG_RESULTS, "")

        from app.agent.subagent_executor import SubagentExecutor

        tool_data = {}
        if device_id:
            ctx = HookContext(input=input_text, entities=state.get(K.ENTITIES, {}))
            ctx = hook_engine.execute_hooks(HOOK_POINTS["PRE_TOOL_USE"], ctx)
            if not ctx.metadata.get("tool_blocked"):
                try:
                    from mcp_server.tools import (get_device_status, get_alarm_history,
                                                   get_device_logs, get_defect_tickets, search_safety_rules)
                    tool_data["metrics"] = json.dumps(get_device_status(device_id), ensure_ascii=False, default=str)[:1000]
                    tool_data["alarm"] = json.dumps(get_alarm_history(device_id, limit=10), ensure_ascii=False, default=str)[:800]
                    tool_data["log"] = json.dumps(get_device_logs(device_id, limit=20), ensure_ascii=False, default=str)[:1000]
                    tool_data["ticket"] = json.dumps(get_defect_tickets(device_id), ensure_ascii=False, default=str)[:800]
                except Exception as e:
                    logger.warning(f"MCP工具调用失败: {e}")
            ctx = hook_engine.execute_hooks(HOOK_POINTS["POST_TOOL_USE"], ctx)

        tool_data["regulation"] = ""
        try:
            from mcp_server.tools import search_safety_rules
            tool_data["regulation"] = json.dumps(search_safety_rules(input_text[:50]), ensure_ascii=False, default=str)[:800]
        except Exception:
            pass

        executor = SubagentExecutor()
        subs = ["regulation", "metrics", "log", "ticket"]
        context = f"故障: {input_text}\n知识库: {rag_context[:500]}"

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        sub_results = loop.run_until_complete(executor.execute_parallel(subs, context, tool_data))

        evidence_parts = []
        step_results = []
        for sr in sub_results:
            if sr.success:
                evidence_parts.append(f"## {sr.name} 分析\n{sr.result}")
                step_results.append(sr.result)
            else:
                evidence_parts.append(f"## {sr.name} 失败: {sr.error}")

        logger.info(f"  ④ Executor: {len([s for s in sub_results if s.success])}/{len(subs)}成功")
        return {
            K.STEP_RESULTS: step_results,
            K.EVIDENCE: "\n\n".join(evidence_parts),
        }

    # ================================================================
    # ⑤ Evidence Validation
    # ================================================================
    def _node_evidence_validation(self, state: dict[str, Any]) -> dict[str, Any]:
        step_results = state.get(K.STEP_RESULTS, [])
        rag_results = state.get(K.RAG_RESULTS, "")
        evidence_count = len(step_results) + (1 if rag_results else 0)

        ctx = HookContext(
            input=state.get(K.INPUT, ""),
            entities=state.get(K.ENTITIES, {}),
            metadata={"evidence_count": evidence_count}
        )
        ctx = hook_engine.execute_hooks(HOOK_POINTS["PRE_DIAGNOSIS"], ctx)

        warnings = []
        if evidence_count < 2:
            warnings.append("证据来源不足(<2个)，诊断置信度可能偏低")

        score = min(evidence_count * 0.25, 0.95)
        coverage = min(evidence_count * 0.2, 0.95)

        logger.info(f"  ⑤ EvidenceValidation: {evidence_count}个来源, 评分{score:.2f}, 覆盖度{coverage:.2f}")
        return {
            K.EVIDENCE_SCORE: score,
            K.EVIDENCE_COVERAGE: coverage,
            K.EVIDENCE_WARNINGS: warnings if warnings else [],
        }

    def _route_evidence(self, state: dict[str, Any]) -> str:
        score = state.get(K.EVIDENCE_SCORE, 0.5)
        return "diagnose" if score >= 0.3 else "planner"

    # ================================================================
    # ⑥ Diagnose — 综合诊断
    # ================================================================
    def _node_diagnose(self, state: dict[str, Any]) -> dict[str, Any]:
        input_text = state.get(K.INPUT, "")
        rag_context = state.get(K.RAG_RESULTS, "")
        evidence = state.get(K.EVIDENCE, "")
        skill_context = state.get(K.SKILL_CONTEXT, "")
        tool_context = state.get("_tool_context", "")
        multimodal = state.get("_multimodal_result", "")

        full_context = f"故障描述: {input_text}\n\n知识库:\n{rag_context[:2000]}\n\n多维度证据:\n{evidence[:2000]}"
        if tool_context:
            full_context += f"\n\n设备状态: {tool_context[:500]}"
        if multimodal:
            full_context += f"\n\n多模态: {multimodal[:500]}"

        unified_prompt = """你是新能源场站智能诊断专家。输出9项结构化诊断报告:

## 1. 告警摘要
## 2. 初步判断
## 3. 分析依据(只引用工具返回的真实数据)
## 4. 可能原因(按可能性排序,附百分比)
## 5. 排查步骤
## 6. 处理建议
## 7. 安全风险提示(引用安规条款编号)
## 8. 是否建议派单(标注紧急程度和派单类型)
## 9. 风险自复核(诊断是否有充分数据支撑/安全风险/遗漏项 + 风险等级CRITICAL/HIGH/MEDIUM/LOW)

规则: 高风险操作标注⚠️并建议人工确认, 严禁编造数据。

报告末尾输出JSON: {"root_cause":"根因","confidence":0.8,"risk_level":"HIGH","should_dispatch":true}"""

        try:
            from app.agent.multi_model import multi_client
            if settings.diagnosis_mode == "ensemble":
                result = multi_client.diagnose_multi(unified_prompt, full_context)
            else:
                result = multi_client.diagnose_single(unified_prompt, full_context)
            report_text = result.get("report_text", "")
            parsed = {"confidence": result.get("confidence", 0.5),
                       "root_cause": result.get("root_cause", ""),
                       "risk_level": result.get("risk_level", "MEDIUM")}
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            report_text = llm.chat(unified_prompt, full_context, temperature=0.1, max_tokens=2048)
            parsed = {"root_cause": "待定", "confidence": 0.5, "risk_level": "MEDIUM"}

        try:
            if "```json" in report_text:
                parsed.update(json.loads(report_text.split("```json")[1].split("```")[0]))
        except (json.JSONDecodeError, IndexError):
            pass

        evidence_conf = self._calc_evidence_confidence(state, report_text)
        final_conf = max(parsed.get("confidence", 0.5), evidence_conf)

        logger.info(f"  ⑥ Diagnose: 置信度{final_conf:.2f}, 风险{parsed.get('risk_level', 'MEDIUM')}")
        return {
            K.EXECUTION_RESULT: report_text,
            K.FINAL_RESPONSE: report_text,
            K.DIAGNOSIS_RESULT: {
                "root_causes": [{"cause": parsed.get("root_cause", ""), "probability": final_conf,
                                  "evidence": [report_text[:500]]}],
                "analysis": report_text,
            },
            K.CONFIDENCE: final_conf,
            K.RISK_LEVEL: parsed.get("risk_level", "MEDIUM"),
        }

    def _calc_evidence_confidence(self, state: dict, report_text: str) -> float:
        score = 0.40
        if state.get(K.RAG_RESULTS): score += 0.20
        if state.get(K.EVIDENCE): score += 0.15
        if state.get(K.DEVICE_ID): score += 0.05
        if len(report_text) > 1500: score += 0.05
        return min(score, 0.90)

    # ================================================================
    # ⑦ Replanner — 重规划判断
    # ================================================================
    def _node_replanner(self, state: dict[str, Any]) -> dict[str, Any]:
        confidence = state.get(K.CONFIDENCE, 0.5)
        loop = state.get(K.LOOP_COUNT, 0) + 1
        score = state.get("judge_score", 0)
        max_retry = state.get("max_retries", 2)

        if confidence < 0.5 and loop <= max_retry:
            judge_details = state.get("judge_details", {})
            hints = [f"{dim}: {detail.get('comment', '')[:60]}"
                     for dim, detail in judge_details.items() if detail.get("score", 100) < 70]
            hint = "  ".join(hints) if hints else "扩大检索范围重新推理"

            existing_rag = state.get(K.RAG_RESULTS, "")
            logger.info(f"  ⑦ Replanner: 置信度{confidence:.2f}<0.5, 第{loop}次重规划")

            return {
                K.LOOP_COUNT: loop,
                K.RAG_RESULTS: f"{existing_rag}\n\n[重规划{loop}] {hint}",
                K.NEXT_ACTION: "replan",
            }

        logger.info(f"  ⑦ Replanner: 通过, 进入风险评估")
        return {K.LOOP_COUNT: loop, K.NEXT_ACTION: "continue"}

    def _route_replan(self, state: dict[str, Any]) -> str:
        return "alarm_rag" if state.get(K.NEXT_ACTION) == "replan" else "risk_assessment"

    # ================================================================
    # ⑧ Risk Assessment
    # ================================================================
    def _node_risk_assessment(self, state: dict[str, Any]) -> dict[str, Any]:
        report = state.get(K.EXECUTION_RESULT, "")
        device_type = state.get(K.ENTITIES, {}).get("device_type", "")
        risk_level = state.get(K.RISK_LEVEL, "MEDIUM")

        impact = "单设备" if "全站" not in report else "全站"
        urgency = "紧急" if risk_level in ("CRITICAL", "HIGH") else "一般"

        logger.info(f"  ⑧ RiskAssessment: {risk_level}, 影响{impact}, 紧急度{urgency}")
        return {
            K.RISK_LEVEL: risk_level,
            "_risk_impact": impact,
            "_risk_urgency": urgency,
        }

    # ================================================================
    # ⑨ Action Recommend
    # ================================================================
    def _node_action_recommend(self, state: dict[str, Any]) -> dict[str, Any]:
        report = state.get(K.EXECUTION_RESULT, "")
        if not report:
            return {}

        prompt = """基于诊断报告生成具体可执行行动建议。输出JSON:
{"actions":[{"priority":"高/中/低","step":"步骤","detail":"说明","estimated_time":"预估时间","tools_needed":["工具"],"safety_note":"安全提示"}]}"""

        try:
            actions = llm.chat_json(prompt, report[:2000], temperature=0.1)
            logger.info(f"  ⑨ ActionRecommend: {len(actions.get('actions', []))}条建议")
            return {"_actions": actions.get("actions", [])}
        except Exception:
            return {"_actions": []}
