"""诊断 API — /api/diagnose"""

import json
import uuid
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.schemas import DiagnosisRequest, DiagnosisResponse, DiagnosisResult, RootCause, ActionPlan, ActionStep, SafetyCheck
from app.graph.builder import get_graph
from app.graph.state_keys import StateKeys as K
from app.memory.memory_service import MemoryService
from app.skill.registry import skill_registry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/diagnose", tags=["diagnosis"])
memory = MemoryService()

NODE_STATUS_MAP: dict[str, str] = {
    "precheck": "正在校验输入...",
    "context_load": "正在加载上下文记忆...",
    "router": "正在识别意图...",
    "knowledge_qa": "正在检索知识库...",
    "diagnosis": "正在执行智能诊断...",
    "chat": "正在生成回复...",
    "safety_review": "正在进行安全审查...",
    "final_response": "正在生成诊断报告...",
    "memory_save": "正在保存会话记录...",
}


def _node_status_message(node_name: str) -> str:
    return NODE_STATUS_MAP.get(node_name, f"正在处理: {node_name}")


@router.post("")
async def diagnose(req: DiagnosisRequest):
    symptoms = req.symptoms.strip()
    if not symptoms:
        raise HTTPException(400, "故障描述不能为空")

    task_id = str(uuid.uuid4())
    session_id = req.session_id or str(uuid.uuid4())

    memory.init_session(session_id)
    memory.init_task(task_id)

    # 匹配 Skill
    skill = skill_registry.select_by_intent("DIAGNOSIS")
    skill_context = skill.prompt_template if skill else ""

    state: dict = {
        K.INPUT: symptoms,
        K.CLEANED_INPUT: symptoms,
        K.SESSION_ID: session_id,
        K.USER_ID: req.user_id or "operator",
        K.TASK_ID: task_id,
        K.INTENT: "FAULT_DIAGNOSIS",
        K.DEVICE_ID: req.device_id or "",
        K.SKILL_CONTEXT: skill_context,
        K.LOOP_COUNT: 0,
        "max_retries": 2,
    }

    graph = get_graph()
    config = {"configurable": {"thread_id": task_id}}
    result = await graph.ainvoke(state, config)

    diag_data = result.get(K.DIAGNOSIS_RESULT, {})
    root_causes = []
    for rc in diag_data.get("root_causes", []):
        root_causes.append(RootCause(
            cause=rc.get("cause", ""),
            probability=rc.get("probability", 0.5),
            evidence=rc.get("evidence", []),
        ))

    response = DiagnosisResponse(
        task_id=task_id,
        diagnosis=DiagnosisResult(
            root_causes=root_causes,
            analysis=result.get(K.EXECUTION_RESULT, ""),
            recommendations=[],
            confidence=result.get(K.CONFIDENCE, 0.5),
        ),
        confidence=result.get(K.CONFIDENCE, 0.5),
        timestamp=datetime.now().isoformat(),
    )

    memory.save_to_session(session_id, symptoms, result.get(K.EXECUTION_RESULT, ""))
    return response


@router.post("/stream")
async def diagnose_stream(req: DiagnosisRequest):
    if not req.symptoms.strip():
        raise HTTPException(400, "故障描述不能为空")

    task_id = str(uuid.uuid4())
    session_id = req.session_id or str(uuid.uuid4())

    memory.init_session(session_id)
    memory.init_task(task_id)

    skill = skill_registry.select_by_intent("DIAGNOSIS")
    skill_context = skill.prompt_template if skill else ""

    state: dict = {
        K.INPUT: req.symptoms,
        K.CLEANED_INPUT: req.symptoms,
        K.SESSION_ID: session_id,
        K.USER_ID: req.user_id or "operator",
        K.TASK_ID: task_id,
        K.INTENT: "FAULT_DIAGNOSIS",
        K.SKILL_CONTEXT: skill_context,
        K.LOOP_COUNT: 0,
        "max_retries": 2,
    }

    async def generate():
        try:
            yield f"data: {json.dumps({'type': 'start', 'task_id': task_id})}\n\n"

            graph = get_graph()
            config = {"configurable": {"thread_id": task_id}}

            full_state: dict = {}

            async for event in graph.astream(state, config, stream_mode="updates"):
                for node_name, node_output in event.items():
                    msg = _node_status_message(node_name)
                    if msg:
                        yield f"data: {json.dumps({'type': 'status', 'message': msg, 'node': node_name})}\n\n"

                    if isinstance(node_output, dict):
                        full_state.update(node_output)

            result = full_state if full_state else state

            diag_data = result.get(K.DIAGNOSIS_RESULT, {})
            if diag_data:
                yield f"data: {json.dumps({'type': 'diagnosis', 'data': {
                    'root_causes': diag_data.get('root_causes', []),
                    'confidence': result.get(K.CONFIDENCE, 0.5),
                    'risk_level': result.get(K.RISK_LEVEL, 'MEDIUM'),
                }}, ensure_ascii=False)}\n\n"

            response_text = result.get(K.EXECUTION_RESULT, result.get(K.FINAL_RESPONSE, ""))
            chunk_size = 80
            for i in range(0, len(response_text), chunk_size):
                yield f"data: {json.dumps({'type': 'content', 'text': response_text[i:i + chunk_size]}, ensure_ascii=False)}\n\n"

            yield "data: [DONE]\n\n"
            memory.save_to_session(session_id, req.symptoms, response_text)
        except Exception as e:
            logger.error(f"诊断失败: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
