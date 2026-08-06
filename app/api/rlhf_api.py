"""RLHF Pipeline API — /api/rlhf

反馈驱动微调自动化管线的 Web 管理入口：
  GET  /api/rlhf/status        — 查看反馈数据和模型版本状态
  POST /api/rlhf/prepare       — 准备微调数据集
  POST /api/rlhf/train         — 触发 LoRA 微调
  POST /api/rlhf/deploy        — 部署指定模型版本
  POST /api/rlhf/feedback      — 手动添加反馈记录
"""

import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rlhf", tags=["rlhf"])

DATA_DIR = Path(__file__).parent.parent.parent / "data"
FEEDBACK_FILE = DATA_DIR / "feedback_records.jsonl"
VERSIONS_FILE = DATA_DIR / "model_versions.json"

FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)


class DeployRequest(BaseModel):
    version: str = Field(..., description="要部署的版本号")


class FeedbackRecord(BaseModel):
    task_id: str = Field(..., description="诊断任务ID")
    rating: str = Field(..., description="accurate / partially_accurate / inaccurate")
    comment: str = Field("")
    corrected_root_cause: str = Field("")
    operator: str = Field("system")


def _load_feedback() -> list[dict]:
    if not FEEDBACK_FILE.exists():
        return []
    records = []
    for line in FEEDBACK_FILE.read_text(encoding="utf-8").strip().split("\n"):
        if line.strip():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return records


def _load_versions() -> dict:
    if VERSIONS_FILE.exists():
        return json.loads(VERSIONS_FILE.read_text(encoding="utf-8"))
    return {"versions": [], "active": None}


def _save_versions(data: dict):
    VERSIONS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _record_feedback(record: dict):
    with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


@router.get("/status")
async def status():
    records = _load_feedback()
    accurate = [r for r in records if r.get("rating") == "accurate"]
    partially = [r for r in records if r.get("rating") == "partially_accurate"]
    inaccurate = [r for r in records if r.get("rating") == "inaccurate"]

    recent = sorted(records, key=lambda r: r.get("created_at", ""), reverse=True)[:20]

    datasets = sorted((Path(__file__).parent.parent.parent / "data" / "training").glob("rlhf_dataset_*.json"))
    dataset_info = []
    for d in datasets[-5:]:
        try:
            info = json.loads(d.read_text(encoding="utf-8"))
            dataset_info.append({"name": d.name, "total": info.get("total", 0),
                                 "positive": info.get("positive_samples", 0),
                                 "negative": info.get("negative_samples", 0)})
        except (json.JSONDecodeError, KeyError):
            pass

    versions = _load_versions()

    return {
        "feedback": {
            "total": len(records),
            "accurate": len(accurate),
            "partially_accurate": len(partially),
            "inaccurate": len(inaccurate),
            "threshold": 50,
            "remaining": max(0, 50 - len(accurate)),
            "ready": len(accurate) >= 50,
        },
        "datasets": dataset_info,
        "model_versions": versions,
        "recent_feedback": recent,
    }


@router.post("/prepare")
async def prepare_dataset():
    records = _load_feedback()
    accurate = [r for r in records if r.get("rating") == "accurate"]
    inaccurate = [r for r in records if r.get("rating") == "inaccurate"]

    if len(accurate) < 10:
        raise HTTPException(400, f"正样本不足 ({len(accurate)} < 10)")

    positive_pairs = []
    for r in accurate[:100]:
        text = f"故障诊断任务: {r.get('task_id', '')}\n确认结果: 诊断正确"
        if r.get("comment"):
            text += f"\n运维反馈: {r['comment']}"
        if r.get("corrected_root_cause"):
            text += f"\n根因: {r['corrected_root_cause']}"
        positive_pairs.append({"text": text, "label": 1})

    negative_pairs = []
    for r in inaccurate[:min(50, len(inaccurate))]:
        text = f"故障诊断任务: {r.get('task_id', '')}\n确认结果: 诊断不准确"
        if r.get("corrected_root_cause"):
            text += f"\n正确根因: {r['corrected_root_cause']}"
        if r.get("comment"):
            text += f"\n运维反馈: {r['comment']}"
        negative_pairs.append({"text": text, "label": 0})

    version = datetime.now().strftime("%Y%m%d-%H%M%S")
    dataset = {
        "version": version,
        "positive_samples": len(positive_pairs),
        "negative_samples": len(negative_pairs),
        "total": len(positive_pairs) + len(negative_pairs),
        "data": positive_pairs + negative_pairs,
    }

    out_dir = DATA_DIR / "training"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"rlhf_dataset_{version}.json"
    out_path.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"RLHF数据集已生成: {out_path} ({dataset['total']}条)")

    return {
        "version": version,
        "path": str(out_path),
        "positive_samples": dataset["positive_samples"],
        "negative_samples": dataset["negative_samples"],
        "total": dataset["total"],
    }


@router.post("/train")
async def train_model():
    datasets = sorted((DATA_DIR / "training").glob("rlhf_dataset_*.json"))
    if not datasets:
        raise HTTPException(400, "未找到微调数据集，请先运行 POST /api/rlhf/prepare")

    latest = datasets[-1]
    data = json.loads(latest.read_text(encoding="utf-8"))
    if data["total"] < 10:
        raise HTTPException(400, f"数据量不足 ({data['total']} < 10)")

    logger.info(f"触发LoRA微调: {latest.name} ({data['total']}条)")
    try:
        train_script = Path(__file__).parent.parent.parent / "scripts" / "lora_finetune.py"
        result = subprocess.run(
            [sys.executable, str(train_script), "--dataset", str(latest)],
            capture_output=True, text=True, timeout=600, cwd=str(Path(__file__).parent.parent.parent)
        )

        if result.returncode != 0:
            raise HTTPException(500, f"微调失败: {result.stderr[:500]}")

        version_id = data["version"]
        versions = _load_versions()
        versions["versions"].append({
            "id": version_id,
            "samples": data["total"],
            "created_at": datetime.now().isoformat(),
            "dataset": latest.name,
        })
        if not versions["active"]:
            versions["active"] = version_id
        _save_versions(versions)

        return {
            "status": "completed",
            "version": version_id,
            "samples": data["total"],
            "output": result.stdout[:2000] if result.stdout else "(空)"
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "微调超时")


@router.post("/deploy")
async def deploy_version(req: DeployRequest):
    versions = _load_versions()
    found = any(v["id"] == req.version for v in versions["versions"])
    if not found:
        raise HTTPException(404, f"版本 v{req.version} 不存在")

    versions["active"] = req.version
    _save_versions(versions)
    logger.info(f"已部署模型版本 v{req.version}")

    return {"status": "deployed", "active": req.version}


@router.post("/feedback")
async def add_feedback(req: FeedbackRecord):
    record = {
        "feedback_id": f"FB{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "task_id": req.task_id,
        "rating": req.rating,
        "comment": req.comment,
        "corrected_root_cause": req.corrected_root_cause,
        "operator": req.operator,
        "created_at": datetime.now().isoformat(),
    }
    _record_feedback(record)
    accurate_count = sum(1 for r in _load_feedback() if r.get("rating") == "accurate")
    return {
        "recorded": True,
        "feedback_id": record["feedback_id"],
        "total_accurate": accurate_count,
        "ready_for_training": accurate_count >= 50,
    }
