"""Diagnosis 子智能体 — 6 节点快速诊断流程 (优化版, 目标 < 20s)

① EntityExtract → ② AlarmRAG → ③ Diagnose → ④ Replanner → ⑤ Risk+Action → END

优化: 移除未连接的 plan_execute/executor 死代码, 移除 action_recommend LLM 调用,
      精简 prompt, 并行化实体提取, 添加超时控制。
"""

import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
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

DIAGNOSIS_TIMEOUT = 15
RAG_CACHE: dict[str, tuple[float, str]] = {}
RAG_CACHE_TTL = 30


class DiagnosisSubAgent(BaseSubAgent):
    meta = SubAgentMeta(
        agent_id="diagnosis-agent",
        name="故障诊断核心引擎(优化版)",
        description="6节点快速诊断: 实体提取→RAG检索→综合诊断→重规划→风险评估+行动建议, 目标<20s",
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
        builder.add_node("diagnose", self._node_diagnose)
        builder.add_node("replanner", self._node_replanner)
        builder.add_node("risk_action", self._node_risk_action)

        builder.add_edge(START, "entity_extract")
        builder.add_edge("entity_extract", "alarm_rag")
        builder.add_edge("alarm_rag", "diagnose")
        builder.add_edge("diagnose", "replanner")
        builder.add_conditional_edges(
            "replanner", self._route_replan,
            {"alarm_rag": "alarm_rag", "risk_action": "risk_action"},
        )
        builder.add_edge("risk_action", END)

    # ================================================================
    # ① Entity Extract — 并行提取, 加超时
    # ================================================================
    def _node_entity_extract(self, state: dict[str, Any]) -> dict[str, Any]:
        text = state.get(K.CLEANED_INPUT, state.get(K.INPUT, ""))
        t0 = time.time()

        entities = {}

        def _extract_kg():
            try:
                return kg_service.extract_entities(text)
            except Exception as e:
                logger.debug(f"KG实体提取失败: {e}")
                return {}

        def _extract_graphrag():
            try:
                return graphrag_service.extract_entities(text)
            except Exception as e:
                logger.debug(f"GraphRAG实体提取失败: {e}")
                return {}

        with ThreadPoolExecutor(max_workers=2) as pool:
            f_kg = pool.submit(_extract_kg)
            f_gr = pool.submit(_extract_graphrag)
            try:
                entities = f_kg.result(timeout=3)
            except (FuturesTimeoutError, Exception):
                pass
            try:
                gr_entities = f_gr.result(timeout=3)
                entities.update({k: v for k, v in gr_entities.items() if v and v != "未知"})
            except (FuturesTimeoutError, Exception):
                pass

        device_id = entities.get("device_id", "")
        if not device_id:
            match = re.search(r'[A-Z]+\d+', text)
            if match:
                device_id = match.group()

        logger.info(f"  ① EntityExtract({time.time()-t0:.1f}s): device={entities.get('device_type')}, id={device_id}")
        return {K.ENTITIES: entities, K.DEVICE_ID: device_id}

    # ================================================================
    # ② Alarm RAG — 带缓存的三重混合检索
    # ================================================================
    def _node_alarm_rag(self, state: dict[str, Any]) -> dict[str, Any]:
        query = state.get(K.REWRITTEN_QUERY, state.get(K.INPUT, ""))
        entities = state.get(K.ENTITIES, {})
        t0 = time.time()

        device_type = entities.get("device_type", "")
        if device_type and device_type not in query:
            query = f"{device_type} {query}"

        cache_key = f"rag:{query[:200]}"
        now = time.time()
        if cache_key in RAG_CACHE:
            cached_time, cached_text = RAG_CACHE[cache_key]
            if now - cached_time < RAG_CACHE_TTL:
                logger.info(f"  ② RAG缓存命中({time.time()-t0:.1f}s)")
                return {K.RAG_RESULTS: cached_text, K.REWRITTEN_QUERY: query}

        ctx = HookContext(input=query, entities=entities)
        ctx = hook_engine.execute_hooks(HOOK_POINTS["PRE_RAG"], ctx)

        keyword_results = hybrid_search.search(query, top_k=8, use_rerank=False)
        graph_context = kg_service.build_graph_context(query)

        rag_parts = []
        if graph_context:
            rag_parts.append(graph_context)
        rag_parts.extend([f"[参考{i+1}] {r['text'][:400]}" for i, r in enumerate(keyword_results[:5])])
        rag_text = "\n\n".join(rag_parts)

        RAG_CACHE[cache_key] = (now, rag_text)
        if len(RAG_CACHE) > 100:
            oldest = min(RAG_CACHE, key=lambda k: RAG_CACHE[k][0])
            del RAG_CACHE[oldest]

        ctx.metadata["rag_count"] = len(keyword_results)
        ctx = hook_engine.execute_hooks(HOOK_POINTS["POST_RAG"], ctx)

        logger.info(f"  ② RAG检索({time.time()-t0:.1f}s): {len(keyword_results)}条, 上下文{len(rag_text)}字")
        return {K.RAG_RESULTS: rag_text, K.REWRITTEN_QUERY: query}

    # ================================================================
    # ③ Diagnose — 精简 prompt, 单次 LLM 调用, 内嵌行动建议
    # ================================================================
    def _node_diagnose(self, state: dict[str, Any]) -> dict[str, Any]:
        input_text = state.get(K.INPUT, "")
        rag_context = state.get(K.RAG_RESULTS, "")[:2500]
        entities = state.get(K.ENTITIES, {})
        device_id = state.get(K.DEVICE_ID, "")
        multimodal = state.get("_multimodal_result", "")
        t0 = time.time()

        device_info = f"设备类型:{entities.get('device_type', '未知')}"
        if device_id:
            device_info += f" ID:{device_id}"

        context_parts = [f"故障: {input_text}", device_info]
        if rag_context:
            context_parts.append(f"知识库参考:\n{rag_context}")
        if multimodal:
            context_parts.append(f"多模态分析: {multimodal[:800]}")
        full_context = "\n\n".join(context_parts)

        prompt = """新能源场站智能诊断专家。简洁报告，全中文，禁止任何英文单词和缩写(包括IGBT/NTC等统一用中文)。

## 诊断结论 (根因+置信度+风险等级)
## 推理过程
## 可能原因(3-4个)
## 处置建议(2-4条)
## 安全提示

末尾单独一行: 置信度:X% 风险:高/中/低"""

        try:
            text = llm.chat(prompt, full_context, temperature=0.1, max_tokens=600)
        except Exception as e:
            logger.error(f"LLM诊断失败: {e}")
            return {K.EXECUTION_RESULT: "诊断服务暂时不可用，请稍后重试",
                     K.FINAL_RESPONSE: f"诊断服务暂时不可用: {str(e)[:100]}",
                     K.CONFIDENCE: 0.3, K.RISK_LEVEL: "MEDIUM"}

        import re
        conf_match = re.search(r'置信度\s*[:：]\s*(\d+)\s*%', text)
        risk_match = re.search(r'风险\s*[:：]\s*(高|中|低)', text)
        parsed = {}
        if conf_match:
            parsed["confidence"] = int(conf_match.group(1)) / 100.0
        if risk_match:
            rmap = {"高": "HIGH", "中": "MEDIUM", "低": "LOW"}
            parsed["risk_level"] = rmap.get(risk_match.group(1), "MEDIUM")

        clean_text = re.sub(r'```json\s*\{[^`]*\}\s*```', '', text)
        clean_text = re.sub(r'\{[^}]*"root_cause"[^}]*confidence[^}]*\}', '', clean_text)
        clean_text = re.sub(r'\n\s*\n\s*\n', '\n\n', clean_text).strip()

        cn_map = {"IGBT": "功率模块", "NTC": "温度传感器", "PLC": "控制器",
                   "SCADA": "监控系统", "PID": "电势衰减", "DGA": "油色谱",
                   "BMS": "电池管理", "UPS": "不间断电源"}
        for en, cn in cn_map.items():
            clean_text = clean_text.replace(en, cn)

        evidence_conf = 0.40
        if rag_context:
            evidence_conf += 0.20
        if device_id:
            evidence_conf += 0.10
        if len(text) > 600:
            evidence_conf += 0.05
        if multimodal:
            evidence_conf += 0.05
        evidence_conf = min(evidence_conf, 0.90)

        parsed_conf = parsed.get("confidence", 0.5)
        final_conf = max(parsed_conf, evidence_conf)

        elapsed = time.time() - t0
        logger.info(f"  ③ Diagnose({elapsed:.1f}s): 置信度{final_conf:.2f}, 风险{parsed.get('risk_level','MEDIUM')}")

        return {
            K.EXECUTION_RESULT: clean_text,
            K.FINAL_RESPONSE: clean_text,
            K.DIAGNOSIS_RESULT: {
                "root_causes": [{"cause": "请查看报告", "probability": final_conf,
                                  "evidence": [clean_text[:500]]}],
                "analysis": clean_text,
            },
            K.CONFIDENCE: final_conf,
            K.RISK_LEVEL: parsed.get("risk_level", "MEDIUM"),
            "_actions": [],
        }

    # ================================================================
    # ④ Replanner — 重规划判断 (最多重试2次)
    # ================================================================
    def _node_replanner(self, state: dict[str, Any]) -> dict[str, Any]:
        confidence = state.get(K.CONFIDENCE, 0.5)
        loop = state.get(K.LOOP_COUNT, 0) + 1
        max_retry = state.get("max_retries", settings.max_retries)

        if confidence < 0.5 and loop <= max_retry:
            judge_details = state.get("judge_details", {})
            hints = [f"{dim}:{d.get('comment','')[:40]}"
                     for dim, d in judge_details.items() if d.get("score", 100) < 70]
            hint = " ".join(hints) if hints else "扩大检索范围,重新推理"
            existing_rag = state.get(K.RAG_RESULTS, "")

            logger.info(f"  ④ Replanner: 置信度{confidence:.2f}<0.5, 第{loop}次重规划")
            return {
                K.LOOP_COUNT: loop, K.NEXT_ACTION: "replan",
                K.RAG_RESULTS: f"{existing_rag}\n[重规划{loop}提示] {hint}",
            }
        logger.info(f"  ④ Replanner: 通过(置信度{confidence:.2f})")
        return {K.LOOP_COUNT: loop, K.NEXT_ACTION: "continue"}

    def _route_replan(self, state: dict[str, Any]) -> str:
        return "alarm_rag" if state.get(K.NEXT_ACTION) == "replan" else "risk_action"

    # ================================================================
    # ⑤ Risk + Action — 纯规则, 无LLM调用
    # ================================================================
    def _node_risk_action(self, state: dict[str, Any]) -> dict[str, Any]:
        risk_level = state.get(K.RISK_LEVEL, "MEDIUM")
        report = state.get(K.EXECUTION_RESULT, "")
        device_type = state.get(K.ENTITIES, {}).get("device_type", "")

        impact = "单设备" if "全站" not in report else "全站"
        urgency = "紧急" if risk_level in ("CRITICAL", "HIGH") else "一般"

        actions = state.get("_actions", [])
        if not actions:
            if risk_level in ("CRITICAL", "HIGH"):
                actions = [
                    {"priority": "高", "step": "立即通知值长", "detail": f"{device_type}设备{risk_level}级风险需立即处置"},
                    {"priority": "高", "step": "执行紧急停机预案", "detail": "按场站规程执行紧急停机操作"},
                    {"priority": "中", "step": "安排现场检修", "detail": f"通知运维班组检查{device_type}设备"},
                ]
            else:
                actions = [
                    {"priority": "中", "step": "持续监控", "detail": "加强运行参数监测频率"},
                    {"priority": "低", "step": "安排计划检修", "detail": "纳入下次计划检修窗口"},
                ]

        logger.info(f"  ⑤ RiskAction: {risk_level}, 影响{impact}, 紧急度{urgency}, {len(actions)}条建议")
        return {
            K.RISK_LEVEL: risk_level,
            "_risk_impact": impact,
            "_risk_urgency": urgency,
            "_actions": actions,
        }
