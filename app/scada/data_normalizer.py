"""SCADA 数据标准化层

将不同协议的原始数据统一转换为标准格式。
三种协议输出 → 统一的 ScadaDataPoint 列表。
"""

import logging
from datetime import datetime
from typing import Any

from app.scada.base import ScadaDataPoint, ScadaReadResult

logger = logging.getLogger(__name__)

STANDARD_FIELDS = [
    "timestamp", "device_id", "point_name", "value", "unit", "quality", "protocol"
]


class DataNormalizer:
    """数据标准化器"""

    @staticmethod
    def normalize(result: ScadaReadResult) -> list[dict[str, Any]]:
        """将读取结果标准化为字典列表"""
        records = []
        for dp in result.data_points:
            records.append({
                "timestamp": dp.timestamp,
                "device_id": dp.device_id,
                "point_name": dp.point_name,
                "value": dp.value,
                "unit": dp.unit,
                "quality": dp.quality,
                "protocol": dp.protocol,
                "read_timestamp": result.read_timestamp,
            })
        return records

    @staticmethod
    def to_statistics(
        points: list[ScadaDataPoint],
    ) -> dict[str, Any]:
        """计算统计摘要"""
        if not points:
            return {"min": 0, "max": 0, "mean": 0, "std": 0, "count": 0}

        values = [p.value for p in points]
        n = len(values)
        mean = sum(values) / n

        if n > 1:
            variance = sum((v - mean) ** 2 for v in values) / (n - 1)
            std = variance ** 0.5
        else:
            std = 0.0

        return {
            "min": round(min(values), 4),
            "max": round(max(values), 4),
            "mean": round(mean, 4),
            "std": round(std, 4),
            "count": n,
        }

    @staticmethod
    def detect_anomalies(
        points: list[ScadaDataPoint],
        normal_ranges: dict[str, tuple[float, float]],
    ) -> list[dict[str, Any]]:
        """检测异常数据点"""
        anomalies = []
        for dp in points:
            if dp.point_name in normal_ranges:
                lo, hi = normal_ranges[dp.point_name]
                if dp.value < lo or dp.value > hi:
                    anomalies.append({
                        "device_id": dp.device_id,
                        "point_name": dp.point_name,
                        "value": dp.value,
                        "unit": dp.unit,
                        "normal_range": f"{lo}~{hi}",
                        "deviation": round(
                            max(lo - dp.value, dp.value - hi, 0), 4
                        ),
                        "timestamp": dp.timestamp,
                    })
        return anomalies


NORMAL_RANGES: dict[str, dict[str, tuple[float, float]]] = {
    "inverter": {
        "temperature_c":    (20.0, 75.0),
        "igbt_temp_c":      (25.0, 85.0),
        "voltage_ac_v":     (360.0, 420.0),
        "voltage_dc_v":     (600.0, 1000.0),
        "frequency_hz":      (49.8, 50.2),
        "efficiency_pct":    (90.0, 100.0),
        "insulation_mohm":   (1.0, 999.0),
    },
    "wind_turbine": {
        "temperature_c":     (10.0, 70.0),
        "vibration_mm_s":    (0.0, 3.0),
        "wind_speed_ms":     (3.0, 25.0),
        "frequency_hz":      (49.8, 50.2),
        "rotor_speed_rpm":   (6.0, 18.0),
    },
    "transformer": {
        "oil_temp_c":        (20.0, 85.0),
        "winding_temp_c":    (20.0, 95.0),
        "voltage_hv_kv":     (34.0, 36.0),
        "voltage_lv_kv":     (10.0, 10.5),
        "oil_level_pct":     (70.0, 100.0),
    },
}
