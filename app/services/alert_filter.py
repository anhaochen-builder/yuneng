"""告警过滤层 — 去重 + 持续时间阈值
实际场站一个月上千条告警，90% 是瞬时越限自动复归
只有符合过滤条件的告警才触发 AI 诊断
"""
import time
import threading
from collections import defaultdict


class AlertFilter:
    def __init__(self, repeat_threshold: int = 3, repeat_window: int = 30,
                 duration_threshold: int = 60):
        self._repeat_threshold = repeat_threshold
        self._repeat_window = repeat_window
        self._duration_threshold = duration_threshold
        self._recent: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def should_diagnose(self, device_id: str, alarm_type: str) -> tuple[bool, str]:
        now = time.monotonic()
        key = f"{device_id}:{alarm_type}"

        with self._lock:
            cutoff = now - self._repeat_window
            self._recent[key] = [t for t in self._recent[key] if t > cutoff]
            self._recent[key].append(now)
            count = len(self._recent[key])

            if count < self._repeat_threshold:
                return False, f"重复次数不足 ({count}/{self._repeat_threshold})"

            if count == self._repeat_threshold:
                first = self._recent[key][0]
                duration = now - first
                if duration < self._duration_threshold:
                    return False, f"持续时间不足 ({duration:.0f}s < {self._duration_threshold}s)"

            if count > self._repeat_threshold and count % 5 == 0:
                return True, f"持续告警 ({count}次)"

            return count == self._repeat_threshold, "达到阈值"


_alert_filter = AlertFilter()


def should_trigger_diagnosis(device_id: str, alarm_type: str) -> tuple[bool, str]:
    return _alert_filter.should_diagnose(device_id, alarm_type)
