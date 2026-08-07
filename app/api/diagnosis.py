"""诊断 API — /api/diagnose + /api/diagnose/multimodal"""

import json
import uuid
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.schemas import DiagnosisRequest, DiagnosisResponse, DiagnosisResult, RootCause, ActionPlan, ActionStep, SafetyCheck, MultimodalRequest
from app.graph.builder import get_graph
from app.graph.state_keys import StateKeys as K
from app.memory.memory_service import get_memory
from app.skill.registry import skill_registry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/diagnose", tags=["diagnosis"])
memory = get_memory()

from app.graph.nodes.common_nodes import NODE_STATUS_MAP


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
        "max_retries": 1,
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

    analysis_text = (
        result.get(K.FINAL_RESPONSE, "")
        or result.get(K.EXECUTION_RESULT, "")
        or "诊断完成，请查看详细报告"
    )

    response = DiagnosisResponse(
        task_id=task_id,
        diagnosis=DiagnosisResult(
            root_causes=root_causes,
            analysis=analysis_text,
            recommendations=[],
            confidence=result.get(K.CONFIDENCE, 0.5),
        ),
        confidence=result.get(K.CONFIDENCE, 0.5),
        timestamp=datetime.now().isoformat(),
    )

    memory.save_to_session(session_id, symptoms, analysis_text)

    _trigger_work_order(task_id, req.device_id or "", diag_data, analysis_text)

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
        "max_retries": 1,
    }

    async def generate():
        def sse(data: dict) -> str:
            return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

        try:
            yield sse({'type': 'start', 'data': {'task_id': task_id}})

            from app.agent.llm_provider import hybrid_llm
            current_mode = hybrid_llm.current_mode

            if current_mode in ("rule-engine", "qwen-local"):
                yield sse({'type': 'status', 'data': {'message': '离线模式：启动案例推理引擎...', 'node': 'offline_diagnosis'}})
                try:
                    from app.agent.case_reasoner import case_reasoner
                    offline_result = case_reasoner.diagnose(req.symptoms, req.device_id or "")
                    yield sse({'type': 'diagnosis', 'data': {
                        'root_causes': [{'cause': offline_result['root_cause'], 'probability': offline_result['confidence']}],
                        'confidence': offline_result['confidence'],
                        'risk_level': offline_result['risk_level'],
                    }})
                    report_text = offline_result['report_text']
                    for i in range(0, len(report_text), 200):
                        yield sse({'type': 'content', 'data': {'text': report_text[i:i + 200]}})
                    yield "data: [DONE]\n\n"
                    memory.save_to_session(session_id, req.symptoms, report_text)
                    return
                except Exception as e:
                    yield sse({'type': 'status', 'data': {'message': f'离线引擎异常: {e}'}})

            yield sse({'type': 'status', 'data': {'message': '正在提取实体...', 'node': 'entity_extract'}})

            import re
            entities = {}
            try:
                from app.rag.knowledge_graph import KnowledgeGraphService
                kg = KnowledgeGraphService()
                entities = kg.extract_entities(req.symptoms)
            except Exception:
                pass

            device_id = entities.get("device_id", "") or req.device_id or ""
            if not device_id:
                match = re.search(r'[A-Z]+\d+', req.symptoms)
                if match:
                    device_id = match.group()
            device_type = entities.get("device_type", "")

            yield sse({'type': 'status', 'data': {'message': '正在检索知识库...', 'node': 'alarm_rag'}})

            query = req.symptoms
            if device_type and device_type not in query:
                query = f"{device_type} {query}"

            from app.graph.subgraphs.diagnosis import hybrid_search, kg_service
            keyword_results = hybrid_search.search(query, top_k=8, use_rerank=False)
            graph_context = kg_service.build_graph_context(query)

            rag_parts = []
            if graph_context:
                rag_parts.append(graph_context)
            rag_parts.extend([f"[参考{i+1}] {r['text'][:400]}" for i, r in enumerate(keyword_results[:5])])
            rag_text = "\n\n".join(rag_parts)

            yield sse({'type': 'status', 'data': {'message': 'DeepSeek正在深度推理...', 'node': 'diagnose'}})

            device_info = f"设备类型:{device_type or '未知'}"
            if device_id:
                device_info += f" ID:{device_id}"
            context_parts = [f"故障: {req.symptoms}", device_info]
            if rag_text:
                context_parts.append(f"知识库参考:\n{rag_text}")
            full_context = "\n\n".join(context_parts)

            prompt = """新能源场站智能诊断专家。简洁报告，全中文，禁止任何英文单词和缩写(包括IGBT/NTC等统一用中文)。

## 诊断结论 (根因+置信度+风险等级)
## 推理过程
## 可能原因(3-4个)
## 处置建议(2-4条)
## 安全提示

末尾单独一行: 置信度:X% 风险:高/中/低"""

            from app.agent.llm_client import llm
            full_text = ""
            buffer = ""
            try:
                for chunk in llm.stream(prompt, full_context, temperature=0.1):
                    full_text += chunk
                    buffer += chunk
                    if len(buffer) >= 20 or '\n' in buffer:
                        yield sse({'type': 'content', 'data': {'text': buffer}})
                        buffer = ""
                if buffer:
                    yield sse({'type': 'content', 'data': {'text': buffer}})
            except Exception as e:
                logger.error(f"流式LLM失败: {e}, 降级同步")
                full_text = llm.chat(prompt, full_context, temperature=0.1, max_tokens=350)
                yield sse({'type': 'content', 'data': {'text': full_text}})

            import re as _re
            conf_match = _re.search(r'置信度\s*[:：]\s*(\d+)\s*%', full_text)
            risk_match = _re.search(r'风险\s*[:：]\s*(高|中|低)', full_text)
            parsed = {}
            if conf_match:
                parsed["confidence"] = int(conf_match.group(1)) / 100.0
            if risk_match:
                rmap = {"高": "HIGH", "中": "MEDIUM", "低": "LOW"}
                parsed["risk_level"] = rmap.get(risk_match.group(1), "MEDIUM")

            confidence = max(parsed.get("confidence", 0.5), 0.5) if rag_text else parsed.get("confidence", 0.5)

            yield sse({'type': 'diagnosis', 'data': {
                'root_causes': [{'cause': parsed.get('root_cause', ''), 'probability': confidence,
                                 'confidence_level': 'high' if confidence > 0.8 else 'medium'}],
                'confidence': confidence,
                'risk_level': parsed.get('risk_level', 'MEDIUM'),
            }})
            yield "data: [DONE]\n\n"
            memory.save_to_session(session_id, req.symptoms, full_text)

        except Exception as e:
            logger.error(f"诊断失败: {e}")
            yield sse({'type': 'error', 'data': {'message': str(e)}})

    return StreamingResponse(generate(), media_type="text/event-stream")


MULTIMODAL_NODE_MAP = {
    **NODE_STATUS_MAP,
    "image_analysis": "正在分析设备图像...",
    "audio_analysis": "正在分析设备声音...",
    "multimodal_fusion": "正在融合多模态信息...",
}


@router.post("/multimodal")
async def diagnose_multimodal(req: MultimodalRequest):
    symptoms = req.symptoms.strip()
    if not symptoms:
        raise HTTPException(400, "故障描述不能为空")
    if not req.images and not req.audio_path:
        raise HTTPException(400, "至少需要提供图像或音频数据")

    task_id = str(uuid.uuid4())
    session_id = req.session_id or str(uuid.uuid4())

    memory.init_session(session_id)
    memory.init_task(task_id)

    skill = skill_registry.select_by_intent("DIAGNOSIS")
    skill_context = skill.prompt_template if skill else ""

    multimodal_text = ""
    image_results = []
    audio_result = {}

    if req.images:
        try:
            from app.multimodal.image_analyzer import image_analyzer
            for img_b64 in req.images:
                result = image_analyzer.analyze(img_b64, "auto", req.device_id or "", symptoms)
                image_results.append(result)
                multimodal_text += image_analyzer.to_text_summary(result) + "\n\n"
        except Exception as e:
            logger.warning(f"图像分析失败: {e}")

    if req.audio_path:
        try:
            from app.multimodal.audio_analyzer import audio_analyzer
            audio_result = audio_analyzer.analyze(req.audio_path, "")
            multimodal_text += audio_analyzer.to_text_summary(audio_result) + "\n\n"
        except Exception as e:
            logger.warning(f"音频分析失败: {e}")

    if multimodal_text:
        try:
            from app.graph.sub_agent import sub_agent_registry
            fusion_agent = sub_agent_registry.get("multimodal-agent")
            if fusion_agent:
                fusion_state = {
                    K.INPUT: symptoms,
                    K.DEVICE_ID: req.device_id or "",
                    K.EXECUTION_RESULT: multimodal_text,
                    K.EVIDENCE_SCORE: 0.5,
                    "_image_text": multimodal_text if req.images else "",
                    "_audio_text": multimodal_text if req.audio_path else "",
                }
                fusion_result = await fusion_agent.build().ainvoke(fusion_state)
                multimodal_text = fusion_result.get(K.EXECUTION_RESULT, multimodal_text)
        except Exception as e:
            logger.warning(f"多模态融合失败: {e}")

    enriched_input = symptoms
    if multimodal_text:
        enriched_input = f"{symptoms}\n\n[多模态分析结果]\n{multimodal_text}"

    state: dict = {
        K.INPUT: enriched_input,
        K.CLEANED_INPUT: enriched_input,
        K.SESSION_ID: session_id,
        K.USER_ID: req.user_id or "operator",
        K.TASK_ID: task_id,
        K.INTENT: "FAULT_DIAGNOSIS",
        K.DEVICE_ID: req.device_id or "",
        K.SKILL_CONTEXT: skill_context,
        K.LOOP_COUNT: 0,
        K.EVIDENCE_SCORE: 0.8 if multimodal_text else 0.5,
        K.EVIDENCE: multimodal_text,
        "_multimodal_images": req.images,
        "_multimodal_audio_path": req.audio_path or "",
        "_image_analysis": image_results,
        "_audio_analysis": audio_result,
        "_image_text": multimodal_text if req.images else "",
        "_audio_text": multimodal_text if req.audio_path else "",
        "max_retries": 1,
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

    _trigger_work_order(task_id, req.device_id or "", diag_data, result.get(K.EXECUTION_RESULT, ""))

    return response


@router.post("/multimodal/stream")
async def diagnose_multimodal_stream(req: MultimodalRequest):
    if not req.symptoms.strip():
        raise HTTPException(400, "故障描述不能为空")

    task_id = str(uuid.uuid4())
    session_id = req.session_id or str(uuid.uuid4())

    memory.init_session(session_id)
    memory.init_task(task_id)

    skill = skill_registry.select_by_intent("DIAGNOSIS")
    skill_context = skill.prompt_template if skill else ""

    async def generate():
        def sse(data: dict) -> str:
            return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

        try:
            yield sse({'type': 'start', 'data': {'task_id': task_id}})

            multimodal_text = ""

            if req.images:
                yield sse({'type': 'status', 'data': {'message': '正在分析设备图像...', 'node': 'image_analysis'}})
                try:
                    from app.multimodal.image_analyzer import image_analyzer
                    for idx, img_b64 in enumerate(req.images):
                        result = image_analyzer.analyze(img_b64, "auto", req.device_id or "", req.symptoms)
                        multimodal_text += image_analyzer.to_text_summary(result) + "\n\n"
                    yield sse({'type': 'status', 'data': {'message': f'图像分析完成({len(req.images)}张)', 'node': 'image_analysis'}})
                except Exception as e:
                    yield sse({'type': 'status', 'data': {'message': f'图像分析失败: {e}'}})

            if req.audio_path:
                yield sse({'type': 'status', 'data': {'message': '正在分析设备声音...', 'node': 'audio_analysis'}})
                try:
                    from app.multimodal.audio_analyzer import audio_analyzer
                    audio_result = audio_analyzer.analyze(req.audio_path)
                    multimodal_text += audio_analyzer.to_text_summary(audio_result) + "\n\n"
                    yield sse({'type': 'status', 'data': {'message': '音频分析完成', 'node': 'audio_analysis'}})
                except Exception as e:
                    yield sse({'type': 'status', 'data': {'message': f'音频分析失败: {e}'}})

            enriched_input = req.symptoms
            if multimodal_text:
                enriched_input = f"{req.symptoms}\n\n[多模态分析结果]\n{multimodal_text}"

            from app.agent.llm_provider import hybrid_llm
            if hybrid_llm.current_mode in ("rule-engine", "qwen-local"):
                yield sse({'type': 'status', 'data': {'message': '离线模式：启动案例推理引擎...'}})
                try:
                    from app.agent.case_reasoner import case_reasoner
                    offline_result = case_reasoner.diagnose(enriched_input, req.device_id or "")
                    yield sse({'type': 'diagnosis', 'data': {
                        'root_causes': [{'cause': offline_result['root_cause'], 'probability': offline_result['confidence']}],
                        'confidence': offline_result['confidence'], 'risk_level': offline_result['risk_level'],
                    }})
                    report_text = offline_result['report_text']
                    for i in range(0, len(report_text), 200):
                        yield sse({'type': 'content', 'data': {'text': report_text[i:i + 200]}})
                    yield "data: [DONE]\n\n"
                    memory.save_to_session(session_id, req.symptoms, report_text)
                    return
                except Exception as e:
                    yield sse({'type': 'status', 'data': {'message': f'离线引擎不可用: {e}'}})

            state: dict = {
                K.INPUT: enriched_input,
                K.CLEANED_INPUT: enriched_input,
                K.SESSION_ID: session_id,
                K.USER_ID: req.user_id or "operator",
                K.TASK_ID: task_id,
                K.INTENT: "FAULT_DIAGNOSIS",
                K.DEVICE_ID: req.device_id or "",
                K.SKILL_CONTEXT: skill_context,
                K.LOOP_COUNT: 0,
                K.EVIDENCE_SCORE: 0.8 if multimodal_text else 0.5,
                K.EVIDENCE: multimodal_text,
                "_multimodal_images": req.images,
                "_multimodal_audio_path": req.audio_path or "",
                "_image_text": multimodal_text if req.images else "",
                "_audio_text": multimodal_text if req.audio_path else "",
                "max_retries": 1,
            }

            graph = get_graph()
            config = {"configurable": {"thread_id": task_id}}
            full_state: dict = {}

            async for event in graph.astream(state, config, stream_mode="updates"):
                for node_name, node_output in event.items():
                    msg = MULTIMODAL_NODE_MAP.get(node_name, _node_status_message(node_name))
                    if msg:
                        yield sse({'type': 'status', 'data': {'message': msg, 'node': node_name}})
                    if isinstance(node_output, dict):
                        full_state.update(node_output)

            result = full_state if full_state else state

            diag_data = result.get(K.DIAGNOSIS_RESULT, {})
            if diag_data:
                yield sse({'type': 'diagnosis', 'data': {
                    'root_causes': diag_data.get('root_causes', []),
                    'confidence': result.get(K.CONFIDENCE, 0.5),
                    'risk_level': result.get(K.RISK_LEVEL, 'MEDIUM'),
                }})

            response_text = result.get(K.EXECUTION_RESULT, result.get(K.FINAL_RESPONSE, ""))
            for i in range(0, len(response_text), 200):
                yield sse({'type': 'content', 'data': {'text': response_text[i:i + 200]}})

            yield "data: [DONE]\n\n"
            memory.save_to_session(session_id, req.symptoms, response_text)
        except Exception as e:
            logger.error(f"多模态诊断失败: {e}")
            yield sse({'type': 'error', 'data': {'message': str(e)}})

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/history")
async def diagnose_history(session_id: str = "", limit: int = 10):
    sessions = []
    for sid, data in memory._sessions.items():
        if session_id and sid != session_id:
            continue
        for h in data.get("history", []):
            sessions.append({
                "session_id": sid,
                "user": h.get("user", ""),
                "assistant": h.get("assistant", "")[:2000],
            })
    return {"history": sessions[-limit:], "total": len(sessions)}


@router.get("/report/{task_id}")
async def get_report(task_id: str):
    for sid, data in memory._sessions.items():
        for h in data.get("history", []):
            if task_id in h.get("user", "") or task_id in h.get("assistant", ""):
                return {"task_id": task_id, "report": h.get("assistant", ""), "query": h.get("user", "")}
    for tid, data in memory._tasks.items():
        if tid == task_id:
            return {"task_id": task_id, "report": data.get("diagnosis_text", ""), "found": True}
    return {"task_id": task_id, "report": "", "found": False}


def _trigger_work_order(task_id: str, device_id: str, diag_data: dict, report: str):
    if not device_id:
        return
    risk_level = diag_data.get("risk_level", "MEDIUM") if isinstance(diag_data, dict) else "MEDIUM"
    if risk_level not in ("CRITICAL", "HIGH"):
        return
    try:
        from app.api.workorder import auto_create_work_order
        root_causes = diag_data.get("root_causes", []) if isinstance(diag_data, dict) else []
        root_cause = root_causes[0].get("cause", "") if root_causes else diag_data.get("root_cause", "")
        auto_create_work_order(
            task_id=task_id, device_id=device_id, device_name=device_id,
            report=report, root_cause=root_cause, risk_level=risk_level,
        )
    except Exception as e:
        logger.warning(f"自动创建工单失败: {e}")
