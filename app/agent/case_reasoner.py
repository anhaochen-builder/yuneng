"""案例推理引擎 — 离线精准诊断核心

不依赖外部 LLM，使用本地 BGE 嵌入 + BM25 关键词 + 知识图谱
三种检索融合 + 模板化报告生成，离线准确率目标 80%+
"""
import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DIAGNOSIS_TEMPLATE = """## 1. 告警摘要
{summary}

## 2. 初步判断
{preliminary}

## 3. 分析依据
{sources}

## 4. 可能原因
{root_causes}

## 5. 排查步骤
{investigation_steps}

## 6. 处理建议
{recommendations}

## 7. 安全风险提示
{safety_notes}

## 8. 是否建议派单
{dispatch}

## 9. 风险自复核
{self_review}"""


class CaseBasedReasoner:
    """离线案例推理诊断器"""

    def __init__(self):
        self._ready = False
        self._hybrid_search = None
        self._kg_service = None
        self._graphrag = None
        self._rule_engine = None
        self._init_components()

    def _init_components(self):
        try:
            from app.rag.hybrid_search import HybridSearchService
            self._hybrid_search = HybridSearchService()
        except Exception as e:
            logger.warning(f"混合检索引擎初始化失败: {e}")

        try:
            from app.rag.knowledge_graph import KnowledgeGraphService
            self._kg_service = KnowledgeGraphService()
        except Exception as e:
            logger.warning(f"知识图谱服务初始化失败: {e}")

        try:
            from app.rag.graphrag import graphrag_service
            self._graphrag = graphrag_service
        except Exception:
            logger.warning("GraphRAG 不可用")

        try:
            from app.agent.llm_provider import OFFLINE_RULES
            self._rule_engine = OFFLINE_RULES
        except Exception:
            self._rule_engine = {}

        self._ready = all([self._hybrid_search, self._kg_service])
        if self._ready:
            logger.info("案例推理引擎就绪 (纯离线)")

    def diagnose(self, symptoms: str, device_id: str = "",
                 device_type: str = "") -> dict[str, Any]:
        """离线诊断入口：多源检索 → 案例匹配 → 报告生成

        Returns:
            {
                "report_text": str,      # 9 项结构化报告
                "confidence": float,      # 综合置信度
                "root_cause": str,        # 根因
                "risk_level": str,        # CRITICAL/HIGH/MEDIUM/LOW
                "source": str,            # case_based / rule / fallback
                "matched_cases": int,     # 匹配到的案例数
                "evidence_summary": str,  # 证据摘要
            }
        """
        if not self._ready:
            return self._fallback_diagnosis(symptoms)

        entities = self._extract_entities(symptoms)
        device_type = device_type or entities.get("device_type", "")
        device_id = device_id or entities.get("device_id", "")

        query = symptoms
        if device_type and device_type not in query:
            query = f"{device_type} {symptoms}"

        cases = self._retrieve_cases(query, device_type)
        graph_ctx = self._get_graph_context(query, entities)
        rule_result = self._match_rules(symptoms, entities)

        if cases:
            report = self._build_report(cases, graph_ctx, rule_result, symptoms, device_id)
            report["source"] = "case_based"
            report["matched_cases"] = len(cases)
            return report

        if rule_result:
            report = self._build_from_rule(rule_result, graph_ctx, symptoms, device_id)
            report["source"] = "rule"
            return report

        return self._fallback_diagnosis(symptoms)

    def _extract_entities(self, text: str) -> dict[str, Any]:
        entities = {"device_type": "", "device_id": "", "fault_keywords": []}
        if self._kg_service:
            try:
                entities.update(self._kg_service.extract_entities(text))
            except Exception:
                pass
        if self._graphrag and not entities.get("device_type"):
            try:
                ge = self._graphrag.extract_entities(text)
                entities.update({k: v for k, v in ge.items() if v and v != "未知"})
            except Exception:
                pass

        if not entities.get("device_id"):
            match = re.search(r'[A-Z]+\d+', text)
            if match:
                entities["device_id"] = match.group()

        keywords = []
        for kw in ["过热", "通讯中断", "振动", "绝缘", "过压", "欠压", "过流",
                     "短路", "断路", "接地", "漏油", "异常声音", "温度过高", "电弧",
                     "闪络", "谐波", "三相不平衡", "功率因数", "频率异常"]:
            if kw in text:
                keywords.append(kw)
        entities["fault_keywords"] = keywords
        return entities

    def _retrieve_cases(self, query: str, device_type: str = "") -> list[dict]:
        cases = []
        if self._hybrid_search:
            try:
                results = self._hybrid_search.search(query, top_k=12)
                for r in results:
                    if r.get("text") and r["text"] not in [c["text"] for c in cases]:
                        cases.append({"text": r["text"][:2000], "score": r.get("score", 0.5),
                                       "source": r.get("metadata", {}).get("source", "bm25")})
            except Exception as e:
                logger.debug(f"混合检索失败: {e}")

        if self._kg_service and device_type:
            try:
                kg_results = self._kg_service.search_by_device_type(device_type, top_k=5)
                for r in kg_results:
                    text = r.get("text", "")
                    if text and text not in [c["text"] for c in cases]:
                        cases.append({"text": text[:2000], "score": 0.7, "source": "knowledge_graph"})
            except Exception:
                pass

        cases.sort(key=lambda c: c["score"], reverse=True)
        return cases[:8]

    def _get_graph_context(self, query: str, entities: dict) -> str:
        parts = []
        if self._kg_service:
            try:
                ctx = self._kg_service.build_graph_context(query)
                if ctx:
                    parts.append(ctx)
            except Exception:
                pass
        if self._graphrag:
            try:
                ctx = self._graphrag.build_graph_context(query)
                if ctx:
                    parts.append(ctx)
            except Exception:
                pass
        return "\n\n".join(parts)

    def _match_rules(self, symptoms: str, entities: dict) -> dict | None:
        if not self._rule_engine:
            return None
        keywords = entities.get("fault_keywords", [])
        if not keywords:
            for kw in self._rule_engine:
                if kw in symptoms:
                    keywords.append(kw)
        if not keywords:
            return None

        best = None
        best_score = 0
        for kw in keywords:
            rule = self._rule_engine.get(kw)
            if not rule:
                continue
            rule_score = sum(1 for k in rule.get("related_keywords", []) if k in symptoms) + 1
            if rule_score > best_score:
                best_score = rule_score
                best = rule

        return best

    def _build_report(self, cases: list[dict], graph_ctx: str,
                      rule_result: dict | None, symptoms: str,
                      device_id: str) -> dict[str, Any]:
        top_case = cases[0]
        main_similarity = top_case["score"]
        case_count = len(cases)
        confidence = min(0.55 + main_similarity * 0.35 + case_count * 0.02, 0.92)

        device_tag = f"[{device_id}] " if device_id else ""

        keywords = []
        for kw in ["过热", "振动", "通讯", "绝缘", "短路", "保护", "跳闸",
                     "过压", "欠压", "过流", "温度", "油温", "齿轮箱", "IGBT",
                     "变压器", "逆变器", "风机", "光伏", "组件", "电缆"]:
            if any(kw in c["text"] for c in cases):
                keywords.append(kw)

        cause_candidates = self._extract_causes(cases, keywords)
        root_causes_text = "\n".join(
            f"- [{c['type']}] {c['cause']} (参考案例:{c['ref_count']}个, 相似度:{c['avg_score']:.0%})"
            for c in cause_candidates[:4]
        )

        investigation = self._generate_investigation_steps(cases, symptoms)
        recommendations = self._generate_recommendations(cases, rule_result)
        safety = self._generate_safety_notes(cases, symptoms, rule_result)

        risk_level = "MEDIUM"
        if rule_result:
            risk_level = rule_result.get("risk_level", "MEDIUM")
        elif confidence < 0.6:
            risk_level = "HIGH"
        elif any(k in symptoms for k in ["跳闸", "保护动作", "短路", "爆炸", "着火"]):
            risk_level = "CRITICAL"

        should_dispatch = risk_level in ("CRITICAL", "HIGH")
        dispatch_text = "建议派单" if should_dispatch else "暂不建议派单，可继续观察"
        if should_dispatch:
            dispatch_text += f" ({risk_level}风险, 建议{'紧急' if risk_level == 'CRITICAL' else '一般'}派单)"

        sources_text = f"匹配到 {case_count} 个相似案例"
        if graph_ctx:
            sources_text += f", 知识图谱辅助"

        report_text = DIAGNOSIS_TEMPLATE.format(
            summary=f"{device_tag}{symptoms[:300]}",
            preliminary=f"基于 {case_count} 个相似案例的交叉比对，初步判断为 {keywords[:4]}相关故障",
            sources=sources_text,
            root_causes=root_causes_text,
            investigation_steps=investigation,
            recommendations=recommendations,
            safety_notes=safety,
            dispatch=dispatch_text,
            self_review=f"离线案例推理模式 | 案例匹配度{main_similarity:.0%} | 综合置信度{confidence:.0%} | 风险等级{risk_level}",
        )

        return {
            "report_text": report_text,
            "confidence": confidence,
            "root_cause": cause_candidates[0]["cause"] if cause_candidates else "未知",
            "risk_level": risk_level,
            "source": "case_based",
            "matched_cases": case_count,
            "evidence_summary": sources_text,
        }

    def _build_from_rule(self, rule: dict, graph_ctx: str,
                         symptoms: str, device_id: str) -> dict[str, Any]:
        device_tag = f"[{device_id}] " if device_id else ""
        confidence = rule.get("confidence", 0.6)
        risk_level = rule.get("risk_level", "MEDIUM")

        report_text = DIAGNOSIS_TEMPLATE.format(
            summary=f"{device_tag}{symptoms[:300]}",
            preliminary=f"规则引擎匹配到: {rule.get('root_cause', '')}",
            sources="离线规则引擎（基于电力行业标准模式库）",
            root_causes=f"- [主要根因] {rule.get('root_cause', '')} (置信度:{confidence:.0%})",
            investigation_steps="\n".join(rule.get("actions", [])),
            recommendations="\n".join(rule.get("recommendations", rule.get("actions", []))),
            safety_notes="\n".join(rule.get("safety_notes", ["操作前确认设备已停电并验电"])),
            dispatch=f"建议派单" if risk_level in ("CRITICAL", "HIGH") else "可继续观察",
            self_review=f"离线规则引擎 | 置信度{confidence:.0%} | 风险等级{risk_level}",
        )

        return {
            "report_text": report_text,
            "confidence": confidence,
            "root_cause": rule.get("root_cause", ""),
            "risk_level": risk_level,
            "source": "rule",
            "matched_cases": 0,
        }

    def _fallback_diagnosis(self, symptoms: str) -> dict[str, Any]:
        return {
            "report_text": f"离线诊断完成: {symptoms[:200]}\n\n建议联系运维专家或恢复网络连接获取精确诊断。",
            "confidence": 0.3,
            "root_cause": "待定",
            "risk_level": "MEDIUM",
            "source": "fallback",
            "matched_cases": 0,
        }

    def _extract_causes(self, cases: list[dict], keywords: list[str]) -> list[dict]:
        cause_map: dict[str, dict] = {}
        for case in cases:
            text = case["text"]
            for line in text.replace("；", "。").replace("，", "。").split("。"):
                line = line.strip()
                if not line or len(line) < 10:
                    continue
                for kw in keywords:
                    if kw in line:
                        key = line[:60]
                        if key not in cause_map:
                            cause_map[key] = {"cause": line[:120], "ref_count": 0, "total_score": 0}
                        cause_map[key]["ref_count"] += 1
                        cause_map[key]["total_score"] += case["score"]
                        break

        candidates = list(cause_map.values())
        for c in candidates:
            c["avg_score"] = c["total_score"] / max(c["ref_count"], 1)
        candidates.sort(key=lambda c: (c["ref_count"], c["avg_score"]), reverse=True)
        result = []
        for i, c in enumerate(candidates[:4]):
            c["type"] = "主要根因" if i == 0 else "替代可能"
            result.append(c)
        return result

    def _generate_investigation_steps(self, cases: list[dict], symptoms: str) -> str:
        steps = []
        seen = set()
        for case in cases[:4]:
            for line in case["text"].replace("；", "\n").replace("。", "\n").split("\n"):
                line = line.strip()
                if len(line) < 15 or line in seen:
                    continue
                if any(w in line for w in ["检查", "检测", "测量", "确认", "观察", "查看",
                                             "测试", "排查", "验证", "核对"]):
                    steps.append(f"{len(steps)+1}. {line}")
                    seen.add(line)
                if len(steps) >= 6:
                    break
            if len(steps) >= 6:
                break

        if not steps:
            steps = [
                "1. 检查设备外观是否有明显异常(烧焦、变形、异响)",
                "2. 检查相关接线端子是否松动或氧化",
                "3. 测量关键参数并与正常值对比",
                f"4. 参考历史案例 {cases[0]['text'][:80] if cases else ''}...",
                "5. 如无法定位，建议联系设备厂家技术支持",
            ]
        return "\n".join(steps)

    def _generate_recommendations(self, cases: list[dict],
                                   rule_result: dict | None) -> str:
        recs = []
        if rule_result:
            for a in rule_result.get("recommendations", rule_result.get("actions", []))[:3]:
                recs.append(f"- {a}")

        seen = set(recs)
        for case in cases[:3]:
            for line in case["text"].split("。"):
                line = line.strip()
                if not line or len(line) < 15 or line in seen:
                    continue
                if any(w in line for w in ["建议", "应", "需要", "必须", "立即", "进行",
                                             "更换", "清洁", "修复", "调整", "停机"]):
                    recs.append(f"- {line}")
                    seen.add(line)
                if len(recs) >= 5:
                    break
            if len(recs) >= 5:
                break

        if not recs:
            recs = ["- 建议联系运维专家进行人工诊断"]
        return "\n".join(recs[:5])

    def _generate_safety_notes(self, cases: list[dict], symptoms: str,
                                rule_result: dict | None) -> str:
        notes = []
        if rule_result and rule_result.get("safety_notes"):
            notes.extend(rule_result["safety_notes"])

        keywords = ["停电", "验电", "挂地线", "挂牌", "防护", "绝缘", "安全", "手续"]
        for case in cases[:3]:
            for line in case["text"].split("。"):
                line = line.strip()
                if any(w in line for w in keywords) and line not in notes:
                    notes.append(f"⚠️ {line}")
                    break

        if not notes:
            notes = [
                "⚠️ 操作前必须确认设备已停电并经验电器验电",
                "⚠️ 严格遵守电力安全工作规程，一人操作一人监护",
            ]
        return "\n".join(notes[:4])


case_reasoner = CaseBasedReasoner()
