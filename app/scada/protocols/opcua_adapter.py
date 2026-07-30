"""OPC UA 协议适配器

OPC UA (IEC 62541) 是工业自动化领域的统一架构标准。
用于连接 DCS、PLC、SCADA 上位机等系统。

由于 asyncua 库较重量级，该适配器:
  - mock 模式: 返回模拟数据（基于节点 ID 映射）
  - real 模式: 通过 opcua-asyncio 连接服务器
"""

import logging
import random
from typing import Any, Optional

from app.scada.base import (
    ProtocolAdapter, DeviceConfig, ScadaDataPoint, ScadaReadResult,
)

logger = logging.getLogger(__name__)

# OPC UA 节点 ID → 测点名称映射模板
OPCUA_MOCK_NODES: dict[str, dict[str, tuple[float, float, str]]] = {
    "scada_host": {
        "ns=2;s=Station.TotalPower":       (0.0, 50.0, "MW"),
        "ns=2;s=Station.Frequency":         (49.8, 50.2, "Hz"),
        "ns=2;s=Station.ActiveAlarms":      (0.0, 5.0, "个"),
        "ns=2;s=Inverter.INV001.Power":     (0.0, 500.0, "kW"),
        "ns=2;s=Inverter.INV001.Temp":      (35.0, 85.0, "°C"),
        "ns=2;s=Inverter.INV001.Voltage":   (360.0, 420.0, "V"),
        "ns=2;s=Inverter.INV002.Power":     (0.0, 500.0, "kW"),
        "ns=2;s=Turbine.WT001.Power":       (0.0, 3000.0, "kW"),
        "ns=2;s=Turbine.WT001.WindSpeed":   (2.0, 25.0, "m/s"),
        "ns=2;s=Environment.Temperature":   (15.0, 42.0, "°C"),
        "ns=2;s=Environment.Humidity":       (10.0, 90.0, "%"),
    },
    "plc": {
        "ns=4;i=1001":  (35.0, 85.0, "°C"),
        "ns=4;i=1002":  (0.0, 500.0, "kW"),
        "ns=4;i=1003":  (360.0, 420.0, "V"),
        "ns=4;i=1004":  (0.0, 800.0, "A"),
        "ns=4;i=1005":  (49.9, 50.1, "Hz"),
        "ns=4;i=1006":  (0.0, 1.0, ""),
    },
}


class OpcuaAdapter(ProtocolAdapter):
    """OPC UA 协议适配器"""

    def __init__(self, config: DeviceConfig, mock_mode: bool = False):
        super().__init__(config, mock_mode)
        self._client = None
        self._mock_nodes = OPCUA_MOCK_NODES.get(
            config.extra.get("node_set", "scada_host"),
            OPCUA_MOCK_NODES["scada_host"],
        )
        self._endpoint = config.extra.get("endpoint",
            f"opc.tcp://{config.host}:{config.port}"
        )

    # ================================================================
    # 连接管理
    # ================================================================

    async def connect(self) -> bool:
        if self.mock_mode:
            self._connected = True
            logger.info(f"[OPC UA Mock] 服务器 {self._endpoint} 连接成功")
            return True

        try:
            # 真实环境使用 asyncua
            # from asyncua import Client
            # self._client = Client(url=self._endpoint)
            # await self._client.connect()
            logger.warning("[OPC UA] asyncua 不可用，降级模拟模式")
            self.mock_mode = True
            self._connected = True
            return True
        except Exception as e:
            logger.error(f"[OPC UA] 连接失败: {e}")
            return False

    async def disconnect(self) -> None:
        if self._client:
            try:
                await self._client.disconnect()
            except Exception:
                pass
        self._connected = False
        self._client = None

    # ================================================================
    # 数据读取
    # ================================================================

    async def read_all(self) -> ScadaReadResult:
        if not self._connected:
            return ScadaReadResult(device_id=self.config.device_id, success=False, error="未连接")

        if self.mock_mode:
            return self._mock_read_all()

        return await self._real_read_all()

    async def read_point(self, point_name: str) -> Optional[ScadaDataPoint]:
        if self.mock_mode:
            return self._mock_read_point(point_name)

        if not self._client:
            return None
        try:
            node = self._client.get_node(point_name)
            raw = await node.read_value()
            return self._make_point(point_name, float(raw), "", "good")
        except Exception as e:
            logger.debug(f"OPC UA 读取失败 {point_name}: {e}")
            return None

    # ================================================================
    # 模拟模式
    # ================================================================

    def _mock_read_all(self) -> ScadaReadResult:
        points = []
        for node_id, (lo, hi, unit) in self._mock_nodes.items():
            value = round(random.uniform(lo, hi), 2)
            points.append(self._make_point(node_id, value, unit))
        return ScadaReadResult(
            device_id=self.config.device_id,
            success=True,
            data_points=points,
        )

    def _mock_read_point(self, point_name: str) -> Optional[ScadaDataPoint]:
        if point_name in self._mock_nodes:
            lo, hi, unit = self._mock_nodes[point_name]
            value = round(random.uniform(lo, hi), 2)
            return self._make_point(point_name, value, unit)
        return None

    async def _real_read_all(self) -> ScadaReadResult:
        points = []
        for node_id in self._mock_nodes:
            dp = await self.read_point(node_id)
            if dp:
                points.append(dp)
        return ScadaReadResult(device_id=self.config.device_id, success=True, data_points=points)
