"""环形缓冲区 — 定长循环队列

滚动存储最近 30 分钟全量 SCADA 时序数据。
容量: 180 万条 (1000 测点 × 60 秒 × 30 分钟)
新数据到达时最旧数据自动被覆盖。
"""

import threading
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Optional

from app.scada.base import ScadaDataPoint


class RingBuffer:
    """线程安全的环形缓冲区

    容量计算:
      1000 测点 × 每秒 1 次采样 × 60 秒 × 30 分钟 = 1,800,000 条
    """

    def __init__(self, capacity: int = 1_800_000):
        self._capacity = capacity
        self._buffer: deque[ScadaDataPoint] = deque(maxlen=capacity)
        self._lock = threading.Lock()
        self._total_written: int = 0
        self._total_overwritten: int = 0

    def push(self, point: ScadaDataPoint) -> None:
        """写入单个数据点"""
        with self._lock:
            if len(self._buffer) >= self._capacity:
                self._total_overwritten += 1
            self._buffer.append(point)
            self._total_written += 1

    def push_batch(self, points: list[ScadaDataPoint]) -> int:
        """批量写入"""
        with self._lock:
            for point in points:
                if len(self._buffer) >= self._capacity:
                    self._total_overwritten += 1
                self._buffer.append(point)
            self._total_written += len(points)
        return len(points)

    def get_window(
        self, center_time: str, before_minutes: int = 5, after_minutes: int = 5
    ) -> list[ScadaDataPoint]:
        """提取以 center_time 为中心的 ±N 分钟故障窗口

        Args:
            center_time: ISO 8601 格式告警时刻
            before_minutes: 告警前窗口（分钟）
            after_minutes: 告警后窗口（分钟）

        Returns:
            窗口内的数据点列表（按时间排序）
        """
        try:
            center = datetime.fromisoformat(center_time)
        except (ValueError, TypeError):
            center = datetime.now()

        start = center - timedelta(minutes=before_minutes)
        end = center + timedelta(minutes=after_minutes)

        with self._lock:
            window = [
                p for p in self._buffer
                if start <= datetime.fromisoformat(p.timestamp) <= end
            ]
        return window

    def get_recent(self, seconds: int = 60) -> list[ScadaDataPoint]:
        """获取最近 N 秒的数据"""
        cutoff = datetime.now() - timedelta(seconds=seconds)
        with self._lock:
            return [
                p for p in self._buffer
                if datetime.fromisoformat(p.timestamp) >= cutoff
            ]

    def query(
        self,
        device_id: Optional[str] = None,
        point_name: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
    ) -> list[ScadaDataPoint]:
        """灵活查询"""
        with self._lock:
            results = list(self._buffer)

        if device_id:
            results = [p for p in results if p.device_id == device_id]
        if point_name:
            results = [p for p in results if p.point_name == point_name]
        if start_time:
            t0 = datetime.fromisoformat(start_time)
            results = [p for p in results if datetime.fromisoformat(p.timestamp) >= t0]
        if end_time:
            t1 = datetime.fromisoformat(end_time)
            results = [p for p in results if datetime.fromisoformat(p.timestamp) <= t1]

        return results[-limit:]

    @property
    def size(self) -> int:
        return len(self._buffer)

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "size": len(self._buffer),
                "capacity": self._capacity,
                "usage_pct": round(len(self._buffer) / self._capacity * 100, 2),
                "total_written": self._total_written,
                "total_overwritten": self._total_overwritten,
            }

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()
            self._total_written = 0
            self._total_overwritten = 0


# 全局单例
_ring_buffer: Optional[RingBuffer] = None


def get_ring_buffer(capacity: int = 1_800_000) -> RingBuffer:
    global _ring_buffer
    if _ring_buffer is None:
        _ring_buffer = RingBuffer(capacity)
    return _ring_buffer
