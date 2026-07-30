"""故障窗口提取器

告警触发时，以告警时刻为中心从环形缓冲区提取 ±5 分钟数据窗口。
计算统计摘要：min / max / mean / std / trend / slope
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from app.scada.base import ScadaDataPoint
from app.scada.ring_buffer import RingBuffer, get_ring_buffer

logger = logging.getLogger(__name__)


class FaultWindowExtractor:
    """故障窗口提取器"""

    def __init__(self, buffer: RingBuffer = None):
        self._buffer = buffer or get_ring_buffer()

    def extract(
        self,
        device_id: str,
        alarm_time: str,
        before_minutes: int = 5,
        after_minutes: int = 5,
    ) -> dict[str, Any]:
        """提取故障窗口数据并计算统计特征

        Returns:
            {
                alarm_time, device_id, window_duration_minutes,
                data_points: [...],
                by_point: { point_name: { values, stats, trend } },
                summary: { total_points, points_with_data }
            }
        """
        window = self._buffer.get_window(
            alarm_time, before_minutes=before_minutes, after_minutes=after_minutes
        )

        device_window = [p for p in window if p.device_id == device_id]
        if not device_window:
            device_window = window

        by_point: dict[str, list[float]] = {}
        for p in device_window:
            if p.point_name not in by_point:
                by_point[p.point_name] = []
            by_point[p.point_name].append(p.value)

        point_analysis: dict[str, dict] = {}
        for name, values in by_point.items():
            point_analysis[name] = self._analyze_point(name, values)

        return {
            "alarm_time": alarm_time,
            "device_id": device_id,
            "window_duration_minutes": before_minutes + after_minutes,
            "total_points": len(device_window),
            "by_point": point_analysis,
        }

    def _analyze_point(
        self, name: str, values: list[float]
    ) -> dict[str, Any]:
        """分析单个测点的统计特征"""
        n = len(values)
        if n == 0:
            return {"name": name, "count": 0, "min": 0, "max": 0, "mean": 0, "std": 0, "trend": "no_data"}

        min_v = min(values)
        max_v = max(values)
        mean_v = sum(values) / n

        if n > 1:
            variance = sum((v - mean_v) ** 2 for v in values) / (n - 1)
            std_v = variance ** 0.5
            first_half = values[:n // 2]
            second_half = values[n // 2:]
            first_mean = sum(first_half) / len(first_half)
            second_mean = sum(second_half) / len(second_half)

            slope = (second_mean - first_mean) / max(len(first_half), 1)
            value_range = max_v - min_v
            # 后半段 vs 前半段变化超过总范围的 3% 视为有趋势
            if value_range > 0 and abs(second_mean - first_mean) > value_range * 0.03:
                trend = "上升" if second_mean > first_mean else "下降"
            else:
                trend = "平稳"
        else:
            std_v = 0.0
            slope = 0.0
            trend = "平稳"

        return {
            "name": name,
            "count": n,
            "min": round(min_v, 4),
            "max": round(max_v, 4),
            "mean": round(mean_v, 4),
            "std": round(std_v, 4),
            "slope": round(slope, 6),
            "trend": trend,
        }

    def to_text_summary(self, analysis: dict) -> str:
        """将分析结果转为供 LLM 使用的文本摘要"""
        if not analysis.get("by_point"):
            return "无故障窗口数据"

        lines = [
            f"设备 {analysis['device_id']} 告警时刻 {analysis['alarm_time']}",
            f"时间窗口: ±5 分钟，共 {analysis['total_points']} 个数据点",
            "",
        ]
        for name, stats in analysis.get("by_point", {}).items():
            lines.append(
                f"{name}: min={stats['min']} max={stats['max']} "
                f"mean={stats['mean']} std={stats['std']} "
                f"趋势={stats['trend']} (斜率={stats.get('slope', 0):.4f})"
            )
        return "\n".join(lines)
