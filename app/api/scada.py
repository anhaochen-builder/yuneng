"""SCADA API — /api/scada

设备连接配置、数据查询、协议管理。
"""

import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.scada.base import DeviceConfig, ScadaReadResult
from app.scada.protocol_factory import ProtocolFactory
from app.scada.ring_buffer import get_ring_buffer
from app.scada.window_extractor import FaultWindowExtractor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/scada", tags=["scada"])

_adapter_registry: dict[str, Any] = {}
_buffer = get_ring_buffer()


class ScadaConnectRequest(BaseModel):
    device_id: str = Field(..., description="设备编号")
    device_type: str = Field(..., description="设备类型")
    protocol: Optional[str] = Field(None, description="协议: modbus/iec61850/opcua，留空自动选择")
    host: str = Field("127.0.0.1", description="主机地址")
    port: int = Field(502, description="端口")
    unit_id: int = Field(1, description="从站地址(Modbus)")
    points: list[dict] = Field(default_factory=list, description="测点配置")
    mock_mode: bool = Field(True, description="模拟模式")


@router.get("/health")
async def health():
    return {"status": "ok", "service": "scada", "connected_devices": len(_adapter_registry)}


@router.post("/connect")
async def connect(req: ScadaConnectRequest):
    config = DeviceConfig(
        device_id=req.device_id,
        device_type=req.device_type,
        protocol=req.protocol or "",
        host=req.host,
        port=req.port,
        unit_id=req.unit_id,
        points=req.points,
    )
    adapter = ProtocolFactory.create(config, mock_mode=req.mock_mode)
    if adapter is None:
        raise HTTPException(400, f"不支持的协议: {req.protocol}")

    ok = await adapter.connect()
    if not ok:
        raise HTTPException(500, "连接失败")

    _adapter_registry[req.device_id] = adapter
    logger.info(f"SCADA 设备已连接: {req.device_id} ({req.device_type})")
    return {
        "code": 0,
        "data": {"device_id": req.device_id, "protocol": adapter.config.protocol, "mock_mode": req.mock_mode},
        "message": f"设备 {req.device_id} 连接成功",
    }


@router.post("/disconnect/{device_id}")
async def disconnect(device_id: str):
    adapter = _adapter_registry.pop(device_id, None)
    if adapter:
        await adapter.disconnect()
        return {"code": 0, "message": f"设备 {device_id} 已断开"}
    raise HTTPException(404, f"设备 {device_id} 未连接")


@router.get("/data/{device_id}")
async def read_data(device_id: str, point: Optional[str] = None):
    adapter = _adapter_registry.get(device_id)
    if adapter is None:
        raise HTTPException(404, f"设备 {device_id} 未连接，请先调用 /api/scada/connect")

    if point:
        dp = await adapter.read_point(point)
        if dp is None:
            raise HTTPException(404, f"测点 {point} 不存在")
        return {"code": 0, "data": dp.to_dict(), "message": "success"}

    result: ScadaReadResult = await adapter.read_all()
    records = [dp.to_dict() for dp in result.data_points]

    _buffer.push_batch(result.data_points)

    return {
        "code": 0,
        "data": {
            "device_id": device_id,
            "count": len(records),
            "points": records[:20],
        },
        "message": "success",
    }


@router.get("/data/{device_id}/window")
async def read_window(
    device_id: str,
    alarm_time: Optional[str] = None,
    before_minutes: int = 5,
    after_minutes: int = 5,
):
    from datetime import datetime
    center = alarm_time or datetime.now().isoformat()

    extractor = FaultWindowExtractor(_buffer)
    analysis = extractor.extract(device_id, center, before_minutes, after_minutes)

    return {
        "code": 0,
        "data": {
            "analysis": analysis,
            "text_summary": extractor.to_text_summary(analysis),
        },
        "message": "success",
    }


@router.get("/buffer/stats")
async def buffer_stats():
    return {"code": 0, "data": _buffer.stats, "message": "success"}


@router.get("/devices")
async def list_devices():
    devices = []
    for device_id, adapter in _adapter_registry.items():
        devices.append({
            "device_id": device_id,
            "protocol": adapter.config.protocol,
            "connected": adapter.connected,
            "mock_mode": adapter.mock_mode,
        })
    return {"code": 0, "data": devices, "message": "success"}
