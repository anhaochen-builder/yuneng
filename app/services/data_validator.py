"""数据前置校验层 — 跳变/冻结/合理性检测
SCADA 数据常见问题：传感器跳变、通讯冻结、单参数飙升（传感器坏）
"""
import logging
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)

_history: dict[str, list[dict]] = defaultdict(list)
MAX_HISTORY = 30


class DataValidator:
    @staticmethod
    def spike_filter(device_id: str, point_name: str, value: float,
                     max_ratio: float = 3.0) -> tuple[bool, str]:
        key = f"{device_id}:{point_name}"
        recent = _history.get(key, [])
        if not recent:
            return True, ""
        last_val = recent[-1].get("value", 0)
        if last_val == 0:
            return True, ""
        ratio = abs(value / last_val)
        if ratio > max_ratio:
            return False, f"跳变异常: {last_val:.1f} → {value:.1f} ({ratio:.1f}x, 阈值 {max_ratio}x)"
        return True, ""

    @staticmethod
    def freeze_detector(device_id: str, point_name: str, value: float) -> tuple[bool, str]:
        key = f"{device_id}:{point_name}"
        recent = _history.get(key, [])
        if len(recent) < 5:
            return True, ""
        last_values = [p.get("value") for p in recent[-5:]]
        if len(set(last_values)) == 1 and value == last_values[0]:
            return False, "数据冻结: 连续 5 分钟数值未变化"
        return True, ""

    @staticmethod
    def reasonability_check(device_id: str, device_type: str,
                            params: dict[str, float]) -> tuple[bool, str]:
        if device_type in ("逆变器", "inverter"):
            voltage = params.get("电压", params.get("voltage_v", 0))
            current = params.get("电流", params.get("current_a", 0))
            if voltage > 1000 and current < 1:
                return False, "电压超高但电流为零，疑似电压传感器故障"
            if current > 200 and voltage < 10:
                return False, "电流超大但电压为零，疑似电流传感器故障"

        if device_type in ("风机", "wind_turbine", "变压器", "transformer"):
            temp = params.get("温度", params.get("temperature_c", 0))
            if temp > 200:
                return False, "温度值 >200°C 失真，疑似传感器故障"

        return True, ""

    @staticmethod
    def validate(device_id: str, device_type: str, point_name: str,
                 value: float, params: dict[str, float]) -> tuple[bool, str]:
        ok, reason = DataValidator.spike_filter(device_id, point_name, value)
        if not ok:
            return False, reason

        ok, reason = DataValidator.freeze_detector(device_id, point_name, value)
        if not ok:
            return False, reason

        ok, reason = DataValidator.reasonability_check(device_id, device_type, params)
        if not ok:
            return False, reason

        key = f"{device_id}:{point_name}"
        _history[key].append({"value": value, "point_name": point_name})
        if len(_history[key]) > MAX_HISTORY:
            _history[key].pop(0)

        return True, "数据校验通过"
