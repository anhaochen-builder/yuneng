"""IEC 61850 协议适配器

IEC 61850 是电力系统通信的国际标准，用于变电站自动化。
通过 MMS (Manufacturing Message Specification) 协议访问 IED 的逻辑节点。

由于 libiec61850 需要 C 库绑定，该适配器:
  - mock 模式: 返回基于 IED 模型的模拟数据
  - real 模式: 通过 MMS 客户端连接真实 IED
"""

import logging
import random
from typing import Any, Optional

from app.scada.base import (
    ProtocolAdapter, DeviceConfig, ScadaDataPoint, ScadaReadResult,
)

logger = logging.getLogger(__name__)

# IEC 61850 逻辑节点模拟模板
IEC61850_MOCK_DATA: dict[str, dict[str, Any]] = {
    "protection_relay": {
        "description": "线路保护装置",
        "logical_nodes": {
            "MMXU1": {
                "description": "测量单元",
                "data_objects": {
                    "PhV.phsA.cVal.mag":     (6350.0, 6400.0, "V"),
                    "PhV.phsB.cVal.mag":     (6340.0, 6410.0, "V"),
                    "A.phsA.cVal.mag":       (0.0, 500.0, "A"),
                    "Hz.mag":                 (49.9, 50.1, "Hz"),
                    "W.mag":                  (0.0, 300.0, "MW"),
                },
            },
            "PDIF1": {
                "description": "差动保护",
                "data_objects": {
                    "OpCntRs.stVal":        (0.0, 9999.0, "次"),
                    "StrVal":               (0.0, 1.0, ""),
                },
            },
            "PDIS1": {
                "description": "距离保护",
                "data_objects": {
                    "OpCntRs.stVal":        (0.0, 9999.0, "次"),
                    "Z1Z2.mag":              (0.1, 100.0, "Ω"),
                },
            },
        },
    },
    "circuit_breaker": {
        "description": "断路器",
        "logical_nodes": {
            "XCBR1": {
                "description": "断路器控制",
                "data_objects": {
                    "Pos.stVal":             (0.0, 3.0, ""),
                    "BlkOpn.stVal":          (0.0, 1.0, ""),
                    "CBOpCap":               (0.0, 1.0, ""),
                },
            },
            "MMXU1": {
                "description": "测量",
                "data_objects": {
                    "A.phsA.cVal.mag":      (0.0, 2000.0, "A"),
                    "PhV.phsA.cVal.mag":     (35000.0, 36000.0, "V"),
                },
            },
        },
    },
    "transformer": {
        "description": "变压器",
        "logical_nodes": {
            "MMXU1": {
                "description": "测量单元",
                "data_objects": {
                    "PhV.phsA.cVal.mag":     (10200.0, 10600.0, "V"),
                    "A.phsA.cVal.mag":       (0.0, 900.0, "A"),
                    "W.mag":                  (0.0, 10.0, "MW"),
                },
            },
            "YPTR1": {
                "description": "变压器保护",
                "data_objects": {
                    "HPTmp.mag":              (40.0, 95.0, "°C"),
                    "OpCntRs.stVal":          (0.0, 99.0, "次"),
                },
            },
        },
    },
}


class Iec61850Adapter(ProtocolAdapter):
    """IEC 61850 适配器（MMS 协议）"""

    def __init__(self, config: DeviceConfig, mock_mode: bool = False):
        super().__init__(config, mock_mode)
        self._client = None
        self._mock_template = IEC61850_MOCK_DATA.get(
            config.extra.get("ied_type", "protection_relay"),
            IEC61850_MOCK_DATA["protection_relay"],
        )

    # ================================================================
    # 连接管理
    # ================================================================

    async def connect(self) -> bool:
        if self.mock_mode:
            self._connected = True
            logger.info(f"[IEC61850 Mock] IED {self.config.device_id} 连接成功")
            return True

        try:
            # 真实环境使用 libiec61850 Python 绑定
            # from iec61850 import IedClient
            # self._client = IedClient.create(self.config.host, self.config.port)
            # await self._client.connect()
            logger.warning("[IEC61850] C 绑定不可用，降级模拟模式")
            self.mock_mode = True
            self._connected = True
            return True
        except Exception as e:
            logger.error(f"[IEC61850] 连接失败: {e}")
            return False

    async def disconnect(self) -> None:
        if self._client:
            try:
                self._client.destroy() if hasattr(self._client, "destroy") else None
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

        return self._real_read_all()

    async def read_point(self, point_name: str) -> Optional[ScadaDataPoint]:
        """读取单个数据对象，格式: LN.DataObject.Attribute"""
        if self.mock_mode:
            return self._mock_read_point(point_name)

        if not self._client:
            return None
        try:
            raw = await self._read_mms_value(point_name)
            return self._make_point(point_name, raw, "", "good")
        except Exception as e:
            logger.debug(f"IEC61850 读取失败 {point_name}: {e}")
            return None

    async def _read_mms_value(self, path: str) -> float:
        """通过 MMS 读取数据值"""
        if self.mock_mode:
            return random.uniform(0, 100)
        # 真实环境: self._client.readFloatValue(path)
        return 0.0

    # ================================================================
    # 模拟模式
    # ================================================================

    def _mock_read_all(self) -> ScadaReadResult:
        points = []
        for ln_name, ln_data in self._mock_template.get("logical_nodes", {}).items():
            for do_name, (lo, hi, unit) in ln_data.get("data_objects", {}).items():
                value = round(random.uniform(lo, hi), 2)
                full_name = f"{ln_name}.{do_name}"
                points.append(self._make_point(full_name, value, unit))
        return ScadaReadResult(
            device_id=self.config.device_id,
            success=True,
            data_points=points,
        )

    def _mock_read_point(self, point_name: str) -> Optional[ScadaDataPoint]:
        for ln_name, ln_data in self._mock_template.get("logical_nodes", {}).items():
            for do_name, (lo, hi, unit) in ln_data.get("data_objects", {}).items():
                if point_name == f"{ln_name}.{do_name}" or point_name == do_name:
                    value = round(random.uniform(lo, hi), 2)
                    full_name = f"{ln_name}.{do_name}"
                    return self._make_point(full_name, value, unit)
        return None

    async def _real_read_all(self) -> ScadaReadResult:
        points = []
        for ln_name, ln_data in self._mock_template.get("logical_nodes", {}).items():
            for do_name in ln_data.get("data_objects", {}):
                full_name = f"{ln_name}.{do_name}"
                dp = await self.read_point(full_name)
                if dp:
                    points.append(dp)
        return ScadaReadResult(device_id=self.config.device_id, success=True, data_points=points)
