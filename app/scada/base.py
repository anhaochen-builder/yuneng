"""SCADA 协议适配器基类

定义所有工业协议适配器的统一接口。
每个适配器支持两种模式:
  - mock: 返回模拟数据（开发/测试用）
  - real: 连接真实硬件
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class ScadaDataPoint:
    """单个 SCADA 数据点"""
    timestamp: str                              # ISO 8601 时间戳
    device_id: str                              # 设备编号
    point_name: str                             # 测点名称
    value: float                                # 数值
    unit: str = ""                              # 单位
    quality: str = "good"                       # 数据质量: good / uncertain / bad
    protocol: str = ""                          # 来源协议: modbus / iec61850 / opcua

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "device_id": self.device_id,
            "point_name": self.point_name,
            "value": self.value,
            "unit": self.unit,
            "quality": self.quality,
            "protocol": self.protocol,
        }


@dataclass
class DeviceConfig:
    """设备连接配置"""
    device_id: str                              # 设备编号
    device_type: str                            # 设备类型: inverter / wind_turbine / transformer
    protocol: str                               # 协议: modbus / iec61850 / opcua
    host: str = "127.0.0.1"                    # 主机地址
    port: int = 502                             # 端口号
    unit_id: int = 1                            # Modbus 从站地址
    points: list[dict[str, Any]] = field(default_factory=list)  # 测点配置
    extra: dict[str, Any] = field(default_factory=dict)         # 协议特定参数


@dataclass
class ScadaReadResult:
    """SCADA 读取结果"""
    device_id: str
    success: bool
    data_points: list[ScadaDataPoint] = field(default_factory=list)
    error: str = ""
    read_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ProtocolAdapter(ABC):
    """协议适配器基类"""

    def __init__(self, config: DeviceConfig, mock_mode: bool = False):
        self.config = config
        self.mock_mode = mock_mode
        self._connected = False

    @abstractmethod
    async def connect(self) -> bool:
        """建立连接，返回是否成功"""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """断开连接"""
        ...

    @abstractmethod
    async def read_all(self) -> ScadaReadResult:
        """批量读取所有配置的测点"""
        ...

    @abstractmethod
    async def read_point(self, point_name: str) -> Optional[ScadaDataPoint]:
        """读取单个测点"""
        ...

    @property
    def connected(self) -> bool:
        return self._connected

    @staticmethod
    def _now_iso() -> str:
        return datetime.now().isoformat()

    def _make_point(self, point_name: str, value: float, unit: str = "",
                    quality: str = "good") -> ScadaDataPoint:
        return ScadaDataPoint(
            timestamp=self._now_iso(),
            device_id=self.config.device_id,
            point_name=point_name,
            value=value,
            unit=unit,
            quality=quality,
            protocol=self.config.protocol,
        )
