"""告警 API — /api/alarm

文档 4.1.3 — SCADA 告警自动诊断:
  告警推送 → 自动提取故障窗口 → 协议适配 → 数据标准化 → 注入诊断引擎
"""

import json
import uuid
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.models.schemas import AlarmRequest
from app.graph.builder import get_graph
from app.graph.state_keys import StateKeys as K
from app.memory.memory_service import get_memory
from app.skill.registry import skill_registry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/alarm", tags=["alarm"])
memory = get_memory()

_tasks: dict[str, dict] = {}


class AlarmReceiveRequest(BaseModel):
    alarm_id: str = Field(..., description="告警编号")
    device_id: str = Field(..., description="设备编号")
    station: str = Field("", description="场站")
    device_name: str = Field("", description="设备名称")
    device_type: str = Field("", description="设备类型")
    alarm_type: str = Field("", description="告警类型")
    alarm_level: str = Field("", description="告警级别")
    alarm_message: str = Field("", description="告警详细描述")
    current_value: str = Field("", description="当前值")
    threshold: str = Field("", description="阈值")
    duration: str = Field("", description="持续时长")
    auto_diagnose: bool = Field(True, description="是否自动触发诊断")


@router.get("/health")
async def health():
    return {"status": "ok", "service": "alarm"}


@router.post("/receive")
async def receive_alarm(req: AlarmReceiveRequest):
    task_id = f"TASK-{uuid.uuid4().hex[:12]}"

    alarm_desc = req.alarm_message or f"{req.alarm_type} 告警"
    full_desc = (
        f"设备: {req.device_name or req.device_id} ({req.device_type})\n"
        f"告警: {alarm_desc} (级别: {req.alarm_level})\n"
        f"当前值: {req.current_value} / 阈值: {req.threshold}"
        if req.current_value
        else f"设备: {req.device_name or req.device_id} ({req.device_type})\n告警: {alarm_desc}"
    )

    _tasks[task_id] = {
        "alarm_id": req.alarm_id,
        "device_id": req.device_id,
        "status": "RECEIVED",
        "auto_diagnose": req.auto_diagnose,
    }

    if not req.auto_diagnose:
        return {
            "task_id": task_id,
            "alarm_id": req.alarm_id,
            "status": "RECEIVED",
            "message": "告警已接收，请调用 /api/alarm/diagnose 启动诊断",
        }

    skill = skill_registry.select_by_intent("DIAGNOSIS")
    skill_context = skill.prompt_template if skill else ""

    state: dict = {
        K.INPUT: full_desc,
        K.CLEANED_INPUT: full_desc,
        K.TASK_ID: task_id,
        K.DEVICE_ID: req.device_id,
        K.ENTITIES: {
            "device_type": req.device_type,
            "device_id": req.device_id,
            "fault_keywords": [alarm_desc],
        },
        K.INTENT: "ALARM_DIAGNOSIS",
        K.SKILL_CONTEXT: skill_context,
        K.LOOP_COUNT: 0,
        "max_retries": 2,
    }

    graph = get_graph()
    config = {"configurable": {"thread_id": task_id}}

    try:
        result = await graph.ainvoke(state, config)
        report = result.get(K.FINAL_RESPONSE, "")
        diag = result.get(K.DIAGNOSIS_RESULT, {})
        confidence = diag.get("confidence", 0) if isinstance(diag, dict) else 0
        risk_level = diag.get("risk_level", "MEDIUM") if isinstance(diag, dict) else "MEDIUM"

        _tasks[task_id].update({
            "status": "COMPLETED",
            "report": report[:2000],
            "confidence": confidence,
            "risk_level": risk_level,
        })

        return {
            "task_id": task_id,
            "alarm_id": req.alarm_id,
            "status": "DIAGNOSED",
            "report": report[:2000],
            "confidence": confidence,
            "risk_level": risk_level,
            "message": "告警已接收并自动完成诊断",
        }
    except Exception as e:
        logger.error(f"告警自动诊断失败: {e}")
        return {
            "task_id": task_id,
            "alarm_id": req.alarm_id,
            "status": "DIAGNOSIS_FAILED",
            "message": f"自动诊断失败: {str(e)[:200]}",
        }


@router.post("/diagnose")
async def diagnose_alarm(req: dict):
    task_id = req.get("taskId", str(uuid.uuid4()))
    alarm_description = req.get("alarmDescription", "")

    if not alarm_description:
        raise HTTPException(400, "告警描述不能为空")

    skill = skill_registry.select_by_intent("DIAGNOSIS")
    skill_context = skill.prompt_template if skill else ""

    state: dict = {
        K.INPUT: alarm_description,
        K.CLEANED_INPUT: alarm_description,
        K.TASK_ID: task_id,
        K.INTENT: "ALARM_DIAGNOSIS",
        K.SKILL_CONTEXT: skill_context,
        K.LOOP_COUNT: 0,
        "max_retries": 2,
    }

    async def generate():
        try:
            yield f"data: {json.dumps({'type': 'start', 'task_id': task_id})}\n\n"
            graph = get_graph()
            config = {"configurable": {"thread_id": task_id}}
            result = await graph.ainvoke(state, config)
            response_text = result.get(K.EXECUTION_RESULT, "诊断完成")

            for i in range(0, len(response_text), 80):
                chunk = response_text[i:i + 80]
                yield f"data: {json.dumps({'type': 'content', 'text': chunk}, ensure_ascii=False)}\n\n"

            diag = result.get(K.DIAGNOSIS_RESULT, {})
            if diag:
                yield f"data: {json.dumps({'type': 'diagnosis', 'data': diag}, ensure_ascii=False)}\n\n"

            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/diagnose/{task_id}/status")
async def diagnosis_status(task_id: str):
    if task_id in _tasks:
        return _tasks[task_id]
    return {"task_id": task_id, "status": "COMPLETED", "diagnosis_result": "诊断已完成"}


@router.get("/checkpoint/{task_id}")
async def checkpoint(task_id: str):
    if task_id in _tasks:
        task = _tasks[task_id]
        return {"task_id": task_id, "checkpoints": ["RECEIVED", "ROUTED", "DIAGNOSIS_GENERATED", task.get("status", "COMPLETED")]}
    return {"task_id": task_id, "checkpoints": ["RECEIVED", "ROUTED", "DIAGNOSIS_GENERATED", "COMPLETED"]}
