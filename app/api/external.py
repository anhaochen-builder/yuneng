"""外部告警自动接入 — Webhook + MQTT 双通道"""
import json
import asyncio
import logging
from datetime import datetime
from pydantic import BaseModel, Field
from fastapi import APIRouter, Request, BackgroundTasks

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/external", tags=["external"])

_last_alarms: list[dict] = []
_mqtt_client = None


class ExternalAlarm(BaseModel):
    source: str = Field("webhook", description="来源: webhook / mqtt / api")
    alarm_id: str = Field(default="", description="外部告警ID")
    device_id: str = Field(..., description="设备编号")
    device_name: str = Field(default="")
    alarm_type: str = Field(default="", description="告警类型")
    alarm_level: str = Field(default="MEDIUM", description="CRITICAL/HIGH/MEDIUM/LOW")
    alarm_message: str = Field(default="", description="告警描述")
    current_value: str = Field(default="")
    threshold: str = Field(default="")
    auto_diagnose: bool = Field(True, description="是否自动触发诊断")
    extra: dict = Field(default_factory=dict)


@router.post("/webhook/alarm")
async def receive_external_alarm(req: ExternalAlarm, background: BackgroundTasks):
    alarm_id = req.alarm_id or f"EXT-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    alarm_record = {
        "alarm_id": alarm_id,
        "device_id": req.device_id,
        "device_name": req.device_name,
        "alarm_type": req.alarm_type,
        "alarm_level": req.alarm_level,
        "alarm_message": req.alarm_message,
        "current_value": req.current_value,
        "threshold": req.threshold,
        "source": req.source,
        "received_at": datetime.now().isoformat(),
    }

    _last_alarms.append(alarm_record)
    if len(_last_alarms) > 1000:
        _last_alarms.pop(0)

    logger.info(f"外部告警接入: {alarm_id} [{req.alarm_level}] {req.device_id}")

    if req.auto_diagnose:
        background.add_task(_auto_diagnose_alarm, alarm_record)

    background.add_task(_broadcast_alarm_safe, alarm_record)

    return {"status": "received", "alarm_id": alarm_id}


async def _auto_diagnose_alarm(alarm: dict):
    try:
        from app.api.alarm import AlarmReceiveRequest
        import uuid

        req = AlarmReceiveRequest(
            alarm_id=alarm["alarm_id"],
            device_id=alarm["device_id"],
            device_name=alarm.get("device_name", ""),
            alarm_type=alarm.get("alarm_type", ""),
            alarm_level=alarm.get("alarm_level", "MEDIUM"),
            alarm_message=alarm.get("alarm_message", ""),
            current_value=alarm.get("current_value", ""),
            threshold=alarm.get("threshold", ""),
            auto_diagnose=True,
        )

        task_id = f"TASK-{uuid.uuid4().hex[:12]}"
        from app.graph.builder import get_graph
        from app.graph.state_keys import StateKeys as K
        from app.skill.registry import skill_registry

        skill = skill_registry.select_by_intent("DIAGNOSIS")
        skill_context = skill.prompt_template if skill else ""

        state = {
            K.INPUT: req.alarm_message or f"{req.alarm_type} 告警",
            K.TASK_ID: task_id,
            K.DEVICE_ID: req.device_id,
            K.INTENT: "ALARM_DIAGNOSIS",
            K.SKILL_CONTEXT: skill_context,
            K.LOOP_COUNT: 0,
            "max_retries": 2,
        }

        graph = get_graph()
        result = await graph.ainvoke(state, {"configurable": {"thread_id": task_id}})
        diag = result.get(K.DIAGNOSIS_RESULT, {})
        confidence = diag.get("confidence", 0) if isinstance(diag, dict) else 0
        risk_level = diag.get("risk_level", "MEDIUM") if isinstance(diag, dict) else "MEDIUM"

        _auto_trigger_work_order(task_id, req.device_id, risk_level,
                                  result.get(K.FINAL_RESPONSE, ""),
                                  diag.get("root_cause", "") if isinstance(diag, dict) else "")

        logger.info(f"自动诊断完成: {task_id} | 置信度: {confidence:.0%} | 风险: {risk_level}")
    except Exception as e:
        logger.error(f"自动诊断失败: {e}")


def _auto_trigger_work_order(task_id: str, device_id: str, risk_level: str,
                              report: str, root_cause: str):
    if risk_level not in ("CRITICAL", "HIGH"):
        return
    try:
        from app.api.workorder import auto_create_work_order
        auto_create_work_order(
            task_id=task_id, device_id=device_id, device_name=device_id,
            report=report, root_cause=root_cause, risk_level=risk_level,
        )
    except Exception as e:
        logger.warning(f"自动工单失败: {e}")


async def _broadcast_alarm_safe(alarm: dict):
    try:
        from app.api.websocket import broadcast_alarm
        await broadcast_alarm({
            "id": alarm.get("alarm_id", ""),
            "device_id": alarm.get("device_id", ""),
            "alarm_type": alarm.get("alarm_type", ""),
            "alarm_level": alarm.get("alarm_level", "MEDIUM"),
            "message": alarm.get("alarm_message", ""),
            "status": "active",
            "timestamp": alarm.get("received_at", ""),
        })
    except Exception:
        pass


@router.get("/webhook/test")
async def test_webhook():
    return {
        "status": "ok",
        "usage": "POST /api/external/webhook/alarm  JSON: {device_id, alarm_type, alarm_level, alarm_message, ...}",
        "example": {
            "device_id": "INV001",
            "alarm_type": "过热",
            "alarm_level": "HIGH",
            "alarm_message": "逆变器IGBT温度98°C超过阈值",
            "auto_diagnose": True,
        },
    }


@router.get("/alarms")
async def list_external_alarms(limit: int = 50):
    return {"total": len(_last_alarms), "alarms": _last_alarms[-limit:]}
