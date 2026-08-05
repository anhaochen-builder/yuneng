"""Modbus TCP 协议适配器

支持真实连接(pymodbus)和模拟模式。
通过配置文件定义寄存器地址到测点名称的映射。
"""

import asyncio
import logging
import random
from typing import Any, Optional

from app.scada.base import (
    ProtocolAdapter, DeviceConfig, ScadaDataPoint, ScadaReadResult,
)

logger = logging.getLogger(__name__)

# 默认模拟数据模板（按设备类型）
MOCK_TEMPLATES: dict[str, dict[str, tuple[float, float, str]]] = {
    "inverter": {
        "temperature_c":       (35.0, 85.0, "°C"),
        "power_kw":           (0.0, 500.0, "kW"),
        "voltage_dc_v":       (600.0, 1000.0, "V"),
        "current_dc_a":       (0.0, 900.0, "A"),
        "voltage_ac_v":       (360.0, 420.0, "V"),
        "current_ac_a":       (0.0, 800.0, "A"),
        "frequency_hz":        (49.8, 50.2, "Hz"),
        "efficiency_pct":      (90.0, 99.0, "%"),
        "igbt_temp_c":        (35.0, 100.0, "°C"),
        "power_factor":        (0.85, 1.0, ""),
    },
    "wind_turbine": {
        "temperature_c":       (20.0, 80.0, "°C"),
        "power_kw":           (0.0, 3000.0, "kW"),
        "voltage_v":          (650.0, 720.0, "V"),
        "current_a":          (0.0, 2600.0, "A"),
        "vibration_mm_s":      (0.1, 4.5, "mm/s"),
        "wind_speed_ms":       (2.0, 30.0, "m/s"),
        "rotor_speed_rpm":     (0.0, 18.0, "rpm"),
        "generator_speed_rpm": (0.0, 1800.0, "rpm"),
        "pitch_angle_deg":     (-5.0, 90.0, "°"),
        "yaw_angle_deg":       (0.0, 360.0, "°"),
    },
    "transformer": {
        "oil_temp_c":          (40.0, 95.0, "°C"),
        "winding_temp_c":      (45.0, 105.0, "°C"),
        "voltage_hv_kv":       (34.0, 36.0, "kV"),
        "voltage_lv_kv":       (10.0, 10.5, "kV"),
        "current_hv_a":        (0.0, 200.0, "A"),
        "current_lv_a":        (0.0, 600.0, "A"),
        "power_mva":           (0.0, 10.0, "MVA"),
        "tap_position":         (1.0, 17.0, ""),
        "oil_level_pct":       (70.0, 100.0, "%"),
    },
}


class ModbusAdapter(ProtocolAdapter):
    """Modbus TCP 适配器

    配置示例:
        config = DeviceConfig(
            device_id="INV001",
            device_type="inverter",
            protocol="modbus",
            host="192.168.1.100",
            port=502,
            unit_id=1,
            points=[
                {"name": "temperature_c", "register": 40001, "type": "holding", "scale": 0.1},
                {"name": "power_kw", "register": 40003, "type": "holding", "scale": 1.0},
            ],
        )
    """

    def __init__(self, config: DeviceConfig, mock_mode: bool = False):
        super().__init__(config, mock_mode)
        self._client = None
        self._point_map = self._build_point_map()

    def _build_point_map(self) -> dict[str, dict[str, Any]]:
        """构建测点名→寄存器配置的映射"""
        mapping = {}
        for p in self.config.points:
            mapping[p["name"]] = {
                "register": p.get("register", 0),
                "type": p.get("type", "holding"),
                "scale": p.get("scale", 1.0),
                "unit": p.get("unit", ""),
                "offset": p.get("offset", 0.0),
            }
        return mapping

    # ================================================================
    # 连接管理
    # ================================================================

    async def connect(self) -> bool:
        if self.mock_mode:
            self._connected = True
            logger.info(f"[Modbus Mock] 设备 {self.config.device_id} 连接成功(模拟)")
            return True

        try:
            from pymodbus.client import AsyncModbusTcpClient

            self._client = AsyncModbusTcpClient(
                host=self.config.host,
                port=self.config.port,
                timeout=5,
            )
            connected = await self._client.connect()
            self._connected = connected
            if connected:
                logger.info(f"[Modbus] 设备 {self.config.device_id} 连接成功")
            else:
                logger.warning(f"[Modbus] 设备 {self.config.device_id} 连接失败")
            return connected

        except ImportError:
            logger.warning("pymodbus 未安装，降级为模拟模式")
            self.mock_mode = True
            self._connected = True
            return True
        except Exception as e:
            logger.error(f"[Modbus] 连接异常: {e}")
            return False

    async def disconnect(self) -> None:
        if self._client and not self.mock_mode:
            try:
                self._client.close()
            except (OSError, AttributeError):
                pass
        self._connected = False
        self._client = None

    # ================================================================
    # 数据读取
    # ================================================================

    async def read_all(self) -> ScadaReadResult:
        if not self._connected:
            return ScadaReadResult(
                device_id=self.config.device_id,
                success=False,
                error="未连接",
            )

        if self.mock_mode:
            return self._mock_read_all()

        return await self._real_read_all()

    async def read_point(self, point_name: str) -> Optional[ScadaDataPoint]:
        if point_name not in self._point_map:
            return None

        if self.mock_mode:
            return self._mock_read_point(point_name)

        try:
            cfg = self._point_map[point_name]
            raw = await self._read_register(cfg["register"], cfg["type"])
            value = raw * cfg["scale"] + cfg.get("offset", 0.0)
            return self._make_point(point_name, round(value, 2), cfg.get("unit", ""))
        except Exception as e:
            logger.debug(f"读取测点 {point_name} 失败: {e}")
            return self._make_point(point_name, 0.0, "", "bad")

    async def _read_register(self, address: int, reg_type: str) -> float:
        """读取单个寄存器"""
        if self.mock_mode or not self._client:
            return 0.0

        if reg_type == "holding":
            result = await self._client.read_holding_registers(address, 1, slave=self.config.unit_id)
        elif reg_type == "input":
            result = await self._client.read_input_registers(address, 1, slave=self.config.unit_id)
        else:
            return 0.0

        if result.isError():
            raise RuntimeError(f"寄存器读取错误: {result}")
        return float(result.registers[0])

    # ================================================================
    # 模拟模式
    # ================================================================

    def _mock_read_all(self) -> ScadaReadResult:
        """模拟批量读取"""
        template = MOCK_TEMPLATES.get(self.config.device_type, MOCK_TEMPLATES["inverter"])
        points = []

        for name, (lo, hi, unit) in template.items():
            if self._point_map and name not in self._point_map:
                continue
            value = round(random.uniform(lo, hi), 2)
            points.append(self._make_point(name, value, unit))

        return ScadaReadResult(
            device_id=self.config.device_id,
            success=True,
            data_points=points,
        )

    def _mock_read_point(self, point_name: str) -> Optional[ScadaDataPoint]:
        """模拟单点读取"""
        template = MOCK_TEMPLATES.get(self.config.device_type, MOCK_TEMPLATES["inverter"])
        if point_name not in template:
            return None

        lo, hi, unit = template[point_name]
        value = round(random.uniform(lo, hi), 2)
        return self._make_point(point_name, value, unit)

    # ================================================================
    # 真实模式
    # ================================================================

    async def _real_read_all(self) -> ScadaReadResult:
        """真实批量读取"""
        if not self._client:
            return ScadaReadResult(device_id=self.config.device_id, success=False, error="客户端未初始化")

        points = []
        try:
            for point_name in self._point_map:
                dp = await self.read_point(point_name)
                if dp:
                    points.append(dp)
            return ScadaReadResult(
                device_id=self.config.device_id,
                success=True,
                data_points=points,
            )
        except Exception as e:
            logger.error(f"批量读取失败: {e}")
            return ScadaReadResult(
                device_id=self.config.device_id,
                success=False,
                error=str(e),
            )
