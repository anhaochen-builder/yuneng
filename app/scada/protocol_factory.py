"""SCADA 协议适配器工厂

根据设备类型自动选择对应的工业协议适配器。
设备→协议映射:
  - inverter / meter / plc → Modbus TCP
  - protection_relay / ied / merging_unit → IEC 61850
  - scada_host / dcs / plc_advanced → OPC UA
"""

import logging
from typing import Optional

from app.scada.base import ProtocolAdapter, DeviceConfig
from app.scada.protocols.modbus_adapter import ModbusAdapter
from app.scada.protocols.iec61850_adapter import Iec61850Adapter
from app.scada.protocols.opcua_adapter import OpcuaAdapter

logger = logging.getLogger(__name__)

DEVICE_PROTOCOL_MAP: dict[str, str] = {
    "inverter":       "modbus",
    "meter":          "modbus",
    "plc":            "modbus",
    "environment":    "modbus",
    "protection_relay": "iec61850",
    "ied":            "iec61850",
    "merging_unit":   "iec61850",
    "fault_recorder":  "iec61850",
    "circuit_breaker": "iec61850",
    "transformer":    "iec61850",
    "scada_host":     "opcua",
    "dcs":            "opcua",
    "power_predict":   "opcua",
    "wind_turbine":   "modbus",
    "photovoltaic":   "modbus",
    "battery":        "modbus",
    "svc":            "modbus",
    "svc_static":     "modbus",
}


class ProtocolFactory:
    """协议适配器工厂：按设备类型自动创建适配器"""

    @staticmethod
    def resolve_protocol(device_type: str) -> str:
        return DEVICE_PROTOCOL_MAP.get(device_type, "modbus")

    @staticmethod
    def create(config: DeviceConfig, mock_mode: bool = False) -> Optional[ProtocolAdapter]:
        protocol = config.protocol or ProtocolFactory.resolve_protocol(config.device_type)

        adapters = {
            "modbus":    lambda: ModbusAdapter(config, mock_mode),
            "iec61850":  lambda: Iec61850Adapter(config, mock_mode),
            "opcua":     lambda: OpcuaAdapter(config, mock_mode),
        }

        factory = adapters.get(protocol)
        if factory:
            adapter = factory()
            logger.info(
                f"创建适配器: {config.device_id} → {protocol} "
                f"({'模拟' if mock_mode else '真实'}模式)"
            )
            return adapter

        logger.warning(f"不支持的协议: {protocol}")
        return None

    @staticmethod
    def create_adapters(
        configs: list[DeviceConfig], mock_mode: bool = False
    ) -> dict[str, ProtocolAdapter]:
        adapters: dict[str, ProtocolAdapter] = {}
        for cfg in configs:
            adapter = ProtocolFactory.create(cfg, mock_mode)
            if adapter:
                adapters[cfg.device_id] = adapter
        return adapters
