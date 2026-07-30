"""对话 API — /api/chat"""

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.schemas import ChatRequest, DiagnosisRequest, DiagnosisResponse
from app.graph.builder import get_graph
from app.graph.state_keys import StateKeys as K
from app.memory.memory_service import MemoryService
from app.skill.registry import skill_registry

router = APIRouter(prefix="/api/chat", tags=["chat"])
memory = MemoryService()

NODE_STATUS_MAP: dict[str, str] = {
    "precheck": "正在校验输入...",
    "context_load": "正在加载上下文记忆...",
    "router": "正在识别意图...",
    "knowledge_qa": "正在检索知识库...",
    "diagnosis": "正在执行智能诊断...",
    "chat": "正在生成回复...",
    "safety_review": "正在进行安全审查...",
    "final_response": "正在生成报告...",
    "memory_save": "正在保存会话记录...",
}


def _node_status_message(node_name: str) -> str:
    return NODE_STATUS_MAP.get(node_name, f"正在处理: {node_name}")


@router.post("")
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    question = req.question.strip()
    if not question:
        raise HTTPException(400, "问题不能为空")

    memory.init_session(session_id)

    state: dict = {
        K.INPUT: question,
        K.SESSION_ID: session_id,
        K.USER_ID: req.user_id,
        K.TASK_ID: str(uuid.uuid4()),
        K.LOOP_COUNT: 0,
        "max_retries": 2,
    }

    graph = get_graph()
    config = {"configurable": {"thread_id": session_id}}
    result = await graph.ainvoke(state, config)
    answer = result.get(K.FINAL_RESPONSE, "抱歉，暂时无法处理您的问题。")

    memory.save_to_session(session_id, question, answer)
    return {"session_id": session_id, "answer": answer}


@router.post("/stream")
async def chat_stream(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    question = req.question.strip()
    if not question:
        raise HTTPException(400, "问题不能为空")

    memory.init_session(session_id)

    state: dict = {
        K.INPUT: question,
        K.SESSION_ID: session_id,
        K.USER_ID: req.user_id,
        K.TASK_ID: str(uuid.uuid4()),
        K.LOOP_COUNT: 0,
        "max_retries": 2,
    }

    async def generate():
        try:
            yield f"data: {json.dumps({'type': 'start', 'session_id': session_id})}\n\n"
            graph = get_graph()
            config = {"configurable": {"thread_id": session_id}}

            full_state: dict = {}

            async for event in graph.astream(state, config, stream_mode="updates"):
                for node_name, node_output in event.items():
                    msg = _node_status_message(node_name)
                    if msg:
                        yield f"data: {json.dumps({'type': 'status', 'message': msg, 'node': node_name})}\n\n"
                    if isinstance(node_output, dict):
                        full_state.update(node_output)

            result = full_state if full_state else state
            answer = result.get(K.FINAL_RESPONSE, "抱歉，暂时无法处理您的问题。")

            chunk_size = 50
            for i in range(0, len(answer), chunk_size):
                chunk = answer[i:i + chunk_size]
                yield f"data: {json.dumps({'type': 'content', 'text': chunk})}\n\n"

            diag = result.get(K.DIAGNOSIS_RESULT, {})
            if diag:
                yield f"data: {json.dumps({'type': 'diagnosis', 'data': diag})}\n\n"

            yield "data: [DONE]\n\n"
            memory.save_to_session(session_id, question, answer)
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/clear")
async def clear_chat(req: dict):
    session_id = req.get("sessionId", "")
    memory._sessions.pop(session_id, None)
    return {"status": "cleared"}
