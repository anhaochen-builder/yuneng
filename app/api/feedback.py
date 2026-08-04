"""反馈 API — /api/feedback

用户对诊断结果进行评价，驱动主动学习。
评价类型: accurate / partially_accurate / inaccurate
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    task_id: str = Field(..., description="诊断任务ID")
    rating: str = Field(..., description="评价: accurate / partially_accurate / inaccurate")
    comment: Optional[str] = Field(None, description="修正意见")
    corrected_root_cause: Optional[str] = Field(None, description="修正后的根因（部分准确时）")
    operator: Optional[str] = Field("system", description="操作人")


FEEDBACK_STORE: dict[str, dict] = {}


@router.post("")
async def submit_feedback(req: FeedbackRequest):
    if req.rating not in ("accurate", "partially_accurate", "inaccurate"):
        raise HTTPException(400, "rating 必须是 accurate / partially_accurate / inaccurate")

    feedback_id = str(uuid.uuid4())
    record = {
        "feedback_id": feedback_id,
        "task_id": req.task_id,
        "rating": req.rating,
        "comment": req.comment,
        "corrected_root_cause": req.corrected_root_cause,
        "operator": req.operator,
        "created_at": datetime.now().isoformat(),
    }

    FEEDBACK_STORE[feedback_id] = record
    logger.info(
        f"收到反馈: task={req.task_id} rating={req.rating} "
        f"operator={req.operator}"
    )

    if req.rating == "accurate":
        _handle_accurate(req.task_id, record)
    elif req.rating == "partially_accurate":
        _handle_partially_accurate(req.task_id, record)
    elif req.rating == "inaccurate":
        _handle_inaccurate(req.task_id, record)

    _count_total_samples()

    return {
        "code": 0,
        "data": {"feedback_id": feedback_id, "status": "RECEIVED"},
        "message": "反馈已提交",
    }


def _check_lora_threshold():
    total = _count_total_samples()
    if total >= 50:
        logger.info(f"累计{total}个标注案例 ≥ 50 → 建议运行 LoRA 微调: python scripts/lora_finetune.py")


def _count_total_samples() -> int:
    accurate = len(FEEDBACK_STORE)
    try:
        pending = sum(1 for _ in open(Path("data/pending_review.jsonl"), "r") if _.strip())
    except Exception:
        pending = 0
    try:
        negative = sum(1 for _ in open(Path("data/negative_samples.jsonl"), "r") if _.strip())
    except Exception:
        negative = 0
    return accurate + pending + negative


def _handle_accurate(task_id: str, record: dict):
    from app.learning.case_ingestion import CaseIngestionService
    from app.memory.memory_service import get_memory

    memory = get_memory()
    task_ctx = memory._tasks.get(task_id, {})
    diagnosis_text = task_ctx.get("diagnosis_text", "")

    ingestion = CaseIngestionService()
    result = ingestion.ingest(
        task_id=task_id,
        symptoms=task_ctx.get("symptoms", ""),
        diagnosis_text=diagnosis_text,
        root_cause=task_ctx.get("root_cause", ""),
        confidence=task_ctx.get("confidence", 0.5),
        risk_level=task_ctx.get("risk_level", "MEDIUM"),
        device_id=task_ctx.get("device_id", ""),
        device_type=task_ctx.get("device_type", ""),
    )

    if result.get("success"):
        logger.info(f"案例入库成功: {task_id}")

        fault_type = ingestion._classify_fault(task_ctx.get("symptoms", ""))
        count = ingestion.count_by_fault_type(fault_type)

        if count >= 3:
            from app.learning.skill_generator import skill_generator
            skill_result = skill_generator.check_and_generate(fault_type)
            if skill_result.get("generated"):
                logger.info(f"Skill自动生成: {skill_result.get('skill_id')}")

    _check_lora_threshold()


def _handle_partially_accurate(task_id: str, record: dict):
    """部分准确：记录修正信息，待人工审核"""
    logger.info(f"部分准确 → 存入待审核池: task={task_id}")
    try:
        pending_path = Path("data/pending_review.jsonl")
        pending_path.parent.mkdir(parents=True, exist_ok=True)
        with open(pending_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning(f"待审核记录失败: {e}")


def _handle_inaccurate(task_id: str, record: dict):
    """不准确：标记为负样本"""
    logger.info(f"不准确 → 标记为负样本: task={task_id}")
    try:
        negative_path = Path("data/negative_samples.jsonl")
        negative_path.parent.mkdir(parents=True, exist_ok=True)
        with open(negative_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning(f"负样本记录失败: {e}")


@router.get("/stats")
async def feedback_stats():
    """获取反馈统计"""
    total = len(FEEDBACK_STORE)
    accurate = sum(1 for r in FEEDBACK_STORE.values() if r["rating"] == "accurate")
    partial = sum(1 for r in FEEDBACK_STORE.values() if r["rating"] == "partially_accurate")
    inaccurate = sum(1 for r in FEEDBACK_STORE.values() if r["rating"] == "inaccurate")

    return {
        "code": 0,
        "data": {
            "total": total,
            "accurate": accurate,
            "partially_accurate": partial,
            "inaccurate": inaccurate,
            "accuracy_rate": round(accurate / max(total, 1), 2),
        },
        "message": "success",
    }
