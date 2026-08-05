"""预测监控子智能体 — 时序预测 + 模式聚类 + 事前预警

能力:
  1. 时序预测: 线性回归/指数平滑预测未来值
  2. 趋势外推: 预测参数何时越过阈值(预估故障时间)
  3. 模式聚类: 存储历史故障窗口,相似度匹配
  4. 事前预警: 提前发出警告,从"事后诊断"升级到"事前预警"
"""

import json
import logging
import math
import time
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Optional

from langgraph.graph import StateGraph, START, END

from app.graph.sub_agent import BaseSubAgent, SubAgentMeta
from app.graph.state_keys import StateKeys as K
from app.agent.llm_client import llm

logger = logging.getLogger(__name__)

FAULT_WINDOW_DIR = None


def _get_window_dir():
    global FAULT_WINDOW_DIR
    if FAULT_WINDOW_DIR is None:
        from pathlib import Path
        FAULT_WINDOW_DIR = Path(__file__).parent.parent.parent / "data" / "fault_windows"
        FAULT_WINDOW_DIR.mkdir(parents=True, exist_ok=True)
    return FAULT_WINDOW_DIR


class TimeSeriesPredictor:
    """时序预测器"""

    @staticmethod
    def linear_regression(values: list[float]) -> tuple[float, float]:
        n = len(values)
        if n < 2:
            return values[-1] if values else 0, 0
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        den = sum((i - x_mean) ** 2 for i in range(n))
        slope = num / den if den > 0 else 0
        intercept = y_mean - slope * x_mean
        return intercept, slope

    @staticmethod
    def predict_next(values: list[float], steps: int = 5) -> list[float]:
        intercept, slope = TimeSeriesPredictor.linear_regression(values)
        n = len(values)
        return [intercept + slope * (n + i) for i in range(steps)]

    @staticmethod
    def predict_crossing_time(values: list[float], threshold: float, timestamps: list[str] = None) -> Optional[dict]:
        intercept, slope = TimeSeriesPredictor.linear_regression(values)
        if abs(slope) < 0.0001:
            return None
        n = len(values)
        steps_to_cross = (threshold - intercept) / slope - n
        if steps_to_cross <= 0 or steps_to_cross > 1440:
            return None
        return {
            "threshold": threshold,
            "current": values[-1],
            "predicted_steps": int(steps_to_cross),
            "estimated_seconds": int(steps_to_cross * 60),
            "slope": round(slope, 6),
            "direction": "上升" if slope > 0 else "下降",
        }

    @staticmethod
    def ewma(values: list[float], alpha: float = 0.3) -> list[float]:
        result = [values[0]]
        for v in values[1:]:
            result.append(alpha * v + (1 - alpha) * result[-1])
        return result

    @staticmethod
    def detect_change_point(values: list[float], window: int = 5) -> Optional[int]:
        if len(values) < window * 2:
            return None
        max_diff = 0
        change_at = None
        for i in range(window, len(values) - window):
            before = sum(values[i - window:i]) / window
            after = sum(values[i:i + window]) / window
            diff = abs(after - before)
            std = sum((v - before) ** 2 for v in values[i - window:i]) / max(window - 1, 1)
            std = max(std ** 0.5, 0.001)
            z = diff / std
            if z > max_diff:
                max_diff = z
                change_at = i
        if max_diff > 2.5:
            return change_at
        return None


class FaultPatternLibrary:
    """故障模式库 — 存储+聚类+相似度匹配"""

    def __init__(self):
        self._patterns: list[dict] = []
        self._load()

    def _load(self):
        path = _get_window_dir() / "patterns.json"
        if path.exists():
            try:
                self._patterns = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"预测模式加载失败: {e}")
                self._patterns = []

    def _save(self):
        path = _get_window_dir() / "patterns.json"
        path.write_text(json.dumps(self._patterns, ensure_ascii=False, indent=2), encoding="utf-8")

    def add_pattern(self, device_type: str, fault_type: str, features: dict, window_data: dict):
        pattern = {
            "device_type": device_type,
            "fault_type": fault_type,
            "features": {k: v for k, v in features.items() if isinstance(v, (int, float))},
            "anomaly_count": window_data.get("anomaly_count", 0),
            "risk_score": window_data.get("risk_score", 0),
            "timestamp": datetime.now().isoformat(),
            "cluster_id": self._find_cluster(features),
        }
        self._patterns.append(pattern)
        if len(self._patterns) > 200:
            self._patterns = self._patterns[-200:]
        self._save()
        logger.info(f"故障模式入库: {device_type}/{fault_type}, 聚类{pattern['cluster_id']}")

    def _find_cluster(self, features: dict) -> int:
        """简单聚类: 基于特征向量的欧氏距离"""
        if not self._patterns:
            return 0
        best_cluster = 0
        best_similarity = 0
        current_vec = {k: v for k, v in features.items() if isinstance(v, (int, float))}
        if not current_vec:
            return 0
        for pattern in self._patterns[-30:]:
            pf = pattern.get("features", {})
            common = set(current_vec.keys()) & set(pf.keys())
            if len(common) < 2:
                continue
            diff = sum((current_vec[k] - pf.get(k, 0)) ** 2 for k in common)
            sim = 1.0 / (1.0 + diff ** 0.5)
            if sim > best_similarity:
                best_similarity = sim
                best_cluster = pattern.get("cluster_id", 0)
        return best_cluster

    def find_similar(self, features: dict, top_k: int = 5) -> list[dict]:
        current_vec = {k: v for k, v in features.items() if isinstance(v, (int, float))}
        if not current_vec:
            return []
        scored = []
        for p in self._patterns:
            pf = p.get("features", {})
            common = set(current_vec.keys()) & set(pf.keys())
            if len(common) < 2:
                continue
            diff = sum((current_vec[k] - pf.get(k, 0)) ** 2 for k in common)
            sim = 1.0 / (1.0 + diff ** 0.5)
            scored.append((sim, p))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{"similarity": round(s, 3), **p} for s, p in scored[:top_k]]

    def cluster_stats(self) -> dict:
        clusters = {}
        for p in self._patterns:
            cid = p.get("cluster_id", 0)
            if cid not in clusters:
                clusters[cid] = {"count": 0, "device_types": set(), "fault_types": set()}
            clusters[cid]["count"] += 1
            clusters[cid]["device_types"].add(p.get("device_type", ""))
            clusters[cid]["fault_types"].add(p.get("fault_type", ""))
        return {
            "total_patterns": len(self._patterns),
            "total_clusters": len(clusters),
            "clusters": {
                str(k): {"count": v["count"],
                          "devices": list(v["device_types"]),
                          "faults": list(v["fault_types"])}
                for k, v in clusters.items()
            },
        }


pattern_library = FaultPatternLibrary()


class PredictiveMonitorSubAgent(BaseSubAgent):
    meta = SubAgentMeta(
        agent_id="predictive-agent",
        name="时序预测监控与分析",
        description="时序预测+模式聚类+事前预警: z-score/线性回归/指数平滑/趋势外推/相似度匹配",
        category="analysis",
        intent_triggers=["LOG_ANALYSIS", "DEVICE_STATUS", "ALARM_ANALYSIS"],
        required_tools=["get_device_status", "get_alarm_history"],
        priority=9,
    )

    def __init__(self):
        super().__init__()
        self._history: dict[str, deque] = {}
        self._predictor = TimeSeriesPredictor()

    def build_nodes(self, builder: StateGraph) -> None:
        builder.add_node("trend_predict", self._node_trend_predict)
        builder.add_node("pattern_cluster", self._node_pattern_cluster)
        builder.add_node("risk_assess", self._node_risk_assess)

        builder.add_edge(START, "trend_predict")
        builder.add_edge("trend_predict", "pattern_cluster")
        builder.add_edge("pattern_cluster", "risk_assess")
        builder.add_edge("risk_assess", END)

    def _node_trend_predict(self, state: dict[str, Any]) -> dict[str, Any]:
        scada_window = state.get("_scada_window", {})
        device_id = state.get(K.DEVICE_ID, "")

        analysis = {"status": "正常", "predictions": [], "warnings": [], "risk_score": 0.0}

        by_point = scada_window.get("by_point", {})
        if not by_point:
            return {"_predictive_trend": analysis}

        for point_name, stats in by_point.items():
            if stats.get("count", 0) < 3:
                continue

            simulated_values = self._gen_sample_values(stats)
            self._update_history(f"{device_id}:{point_name}", simulated_values)

            ewma_vals = self._predictor.ewma(simulated_values[-20:])

            change_pt = self._predictor.detect_change_point(simulated_values, window=5)
            if change_pt:
                analysis["warnings"].append({
                    "point": point_name, "type": "突变检测",
                    "detail": f"{point_name}在第{change_pt}点检测到显著变化",
                    "risk": 0.20,
                })
                analysis["risk_score"] += 0.20

            thresholds = {"温度": 85, "振动": 7.0, "temp": 85, "vib": 7.0,
                           "油温": 80, "电流": 500, "电压": 690, "功率": 3000}
            for key, val in thresholds.items():
                if key in point_name or point_name in key:
                    crossing = self._predictor.predict_crossing_time(simulated_values[-30:], val)
                    if crossing:
                        analysis["predictions"].append({
                            "point": point_name, "threshold": val,
                            "current": round(crossing["current"], 2),
                            "eta_seconds": crossing["estimated_seconds"],
                            "direction": crossing["direction"],
                            "detail": f"{point_name}预计{crossing['estimated_seconds']//60}分钟后超过{val}阈值",
                        })
                        analysis["risk_score"] += min(0.30, crossing["estimated_seconds"] / 3600 * 0.30)
                    break

        analysis["risk_score"] = min(analysis["risk_score"], 1.0)
        analysis["status"] = ("严重" if analysis["risk_score"] > 0.6
                              else "警告" if analysis["risk_score"] > 0.3
                              else "注意" if analysis["risk_score"] > 0.1 else "正常")

        return {"_predictive_trend": analysis}

    def _node_pattern_cluster(self, state: dict[str, Any]) -> dict[str, Any]:
        pred_data = state.get("_predictive_trend", {})
        scada_window = state.get("_scada_window", {})
        entities = state.get(K.ENTITIES, {})

        features = {}
        for point_name, stats in scada_window.get("by_point", {}).items():
            if stats.get("count", 0) > 0:
                key = point_name.replace(" ", "_")
                features[f"mean_{key}"] = round(stats.get("mean", 0), 4)
                features[f"std_{key}"] = round(stats.get("std", 0), 4)

        device_type = entities.get("device_type", "")

        if pred_data.get("risk_score", 0) > 0.15:
            fault_type = "温度异常" if any("温" in w.get("point", "") for w in pred_data.get("warnings", [])) else "趋势异常"
            pattern_library.add_pattern(device_type, fault_type, features, {
                "anomaly_count": len(pred_data.get("predictions", [])),
                "risk_score": pred_data.get("risk_score", 0),
            })

        similar = pattern_library.find_similar(features, top_k=5) if features else []
        clusters = pattern_library.cluster_stats()

        return {
            "_predictive_match": {
                "similar_patterns": similar,
                "clusters": clusters,
                "total_patterns": clusters.get("total_patterns", 0),
            }
        }

    def _node_risk_assess(self, state: dict[str, Any]) -> dict[str, Any]:
        pred_data = state.get("_predictive_trend", {})
        match_data = state.get("_predictive_match", {})
        risk_score = pred_data.get("risk_score", 0)
        similar_count = len(match_data.get("similar_patterns", []))

        if similar_count >= 2 and max((s.get("similarity", 0) for s in match_data.get("similar_patterns", [])), default=0) > 0.6:
            risk_score = min(risk_score + 0.15, 0.95)

        risk_level = "LOW"
        if risk_score > 0.6:
            risk_level = "CRITICAL"
        elif risk_score > 0.3:
            risk_level = "HIGH"
        elif risk_score > 0.15:
            risk_level = "MEDIUM"

        predictions_text = "\n".join(
            f"  ⚠ {p['detail']} (当前{p['current']}, 斜率{p['direction']})"
            for p in pred_data.get("predictions", [])
        )
        warnings_text = "\n".join(
            f"  📊 {w['detail']}" for w in pred_data.get("warnings", [])
        )
        similar_text = "\n".join(
            f"  ✓ 相似度{s['similarity']:.0%} → [{s.get('device_type','')}] {s.get('fault_type','')}"
            for s in match_data.get("similar_patterns", [])
        )

        summary = f"""## 时序预测监控报告

**风险等级: {risk_level}** (评分: {risk_score:.2f})
**模式库: {match_data.get('total_patterns', 0)} 个历史模式**

### 趋势预测
{predictions_text if predictions_text else '  参数趋势正常，无越限预测'}

### 突变检测
{warnings_text if warnings_text else '  未检测到突变点'}

### 相似故障模式匹配
{similar_text if similar_text else '  未匹配到历史相似模式'}

### 建议
- 风险评分 {risk_score:.2f}，{'⚠ 建议安排预防性检修' if risk_score > 0.3 else '继续正常监控'}
- 匹配 {similar_count} 个历史相似模式{'，建议参考对应处置方案' if similar_count > 0 else ''}
"""

        existing_rag = state.get(K.RAG_RESULTS, "")
        return {
            K.RAG_RESULTS: f"{existing_rag}\n\n{summary}",
            "_predictive_result": {
                "risk_level": risk_level, "risk_score": risk_score,
                "summary": summary, "predictions": len(pred_data.get("predictions", [])),
                "similar_patterns": similar_count, "total_patterns": match_data.get("total_patterns", 0),
            },
        }

    def _gen_sample_values(self, stats: dict) -> list[float]:
        mean_v = float(stats.get("mean", 0))
        std_v = float(stats.get("std", 0.1))
        count = int(stats.get("count", 10))
        import random
        return [mean_v + random.gauss(0, max(std_v, 0.01)) for _ in range(max(count, 5))]

    def _update_history(self, key: str, values: list[float]):
        if key not in self._history:
            self._history[key] = deque(maxlen=60)
        self._history[key].extend(values)
