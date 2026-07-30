"""告警 API — /api/alarm"""

import json
import uuid
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.schemas import AlarmRequest
from app.graph.builder import get_graph
from app.graph.state_keys import StateKeys as K
from app.memory.memory_service import MemoryService
from app.skill.registry import skill_registry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/alarm", tags=["alarm"])
memory = MemoryService()


@router.get("/health")
async def health():
    return {"status": "ok", "service": "alarm"}


@router.post("/receive")
async def receive_alarm(req: AlarmRequest):
    task_id = f"TASK-{uuid.uuid4().hex[:12]}"
    return {
        "task_id": task_id,
        "alarm_id": req.alarm_id,
        "status": "RECEIVED",
        "message": "告警已接收，请调用 /api/alarm/diagnose 启动诊断",
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
    return {"task_id": task_id, "status": "COMPLETED", "diagnosis_result": "诊断已完成"}


@router.get("/checkpoint/{task_id}")
async def checkpoint(task_id: str):
    return {"task_id": task_id, "checkpoints": ["RECEIVED", "ROUTED", "DIAGNOSIS_GENERATED", "COMPLETED"]}
