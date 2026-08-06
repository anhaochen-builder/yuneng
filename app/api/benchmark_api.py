"""Benchmark API — /api/benchmark

提供诊断准确率评测的 Web 界面入口：
  GET  /api/benchmark            — 查看基准案例列表和上次评测结果
  POST /api/benchmark/run        — 触发规则引擎评测
  POST /api/benchmark/run/llm    — 触发 LLM 评测（需 API Key）
  GET  /api/benchmark/result     — 获取最近一次评测报告
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/benchmark", tags=["benchmark"])

BENCHMARK_PATH = Path(__file__).parent.parent.parent / "data" / "benchmark_cases.json"
RESULT_CACHE_PATH = Path(__file__).parent.parent.parent / "data" / "benchmark_result.json"
RESULT_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)

_last_result: dict = {}
_eval_running: bool = False


class BenchmarkRunRequest(BaseModel):
    device: str = Field("", description="按设备类型筛选，空=全部")
    limit: int = Field(0, ge=0, le=100, description="限制案例数，0=全部")


def _load_cases() -> list[dict]:
    if BENCHMARK_PATH.exists():
        return json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))
    return []


def _classify_hit(predicted: str, expected: str, keywords: list[str]) -> str:
    pred_lower = predicted.lower()
    exp_lower = expected.lower()
    if exp_lower in pred_lower or any(k.lower() in pred_lower for k in keywords):
        return "exact"
    if any(w in pred_lower for w in exp_lower.split()):
        return "partial"
    return "miss"


@router.get("")
async def list_cases(device: str = Query("", description="按设备筛选")):
    cases = _load_cases()
    if device:
        cases = [c for c in cases if c["device_type"] == device]
    devices = sorted(set(c["device_type"] for c in _load_cases()))
    return {
        "total": len(cases),
        "devices": devices,
        "cases": [{"id": c["id"], "device_type": c["device_type"],
                    "device_id": c["device_id"], "symptoms": c["symptoms"][:100],
                    "expected_root_cause": c["expected_root_cause"],
                    "risk_level": c["risk_level"]} for c in cases],
        "last_result": _last_result.get("summary")
    }


@router.post("/run")
async def run_benchmark(req: BenchmarkRunRequest):
    global _last_result, _eval_running
    if _eval_running:
        raise HTTPException(409, "评测正在运行中，请稍后")

    cases = _load_cases()
    if req.device:
        cases = [c for c in cases if c["device_type"] == req.device]
    if req.limit:
        cases = cases[:req.limit]

    if not cases:
        raise HTTPException(400, "没有匹配的基准案例")

    _eval_running = True
    t_start = time.perf_counter()
    try:
        from app.agent.case_reasoner import case_reasoner
        results = []
        correct = 0
        partial = 0
        device_stats: dict = {}
        risk_stats: dict = {}

        for case in cases:
            t0 = time.perf_counter()
            result = case_reasoner.diagnose(
                symptoms=case["symptoms"],
                device_id=case.get("device_id", ""),
                device_type=case.get("device_type", ""),
            )
            elapsed = time.perf_counter() - t0
            predicted = result.get("root_cause", "")
            hit = _classify_hit(predicted, case["expected_root_cause"], case.get("keywords", []))
            if hit == "exact":
                correct += 1
            elif hit == "partial":
                partial += 1

            dev = case["device_type"]
            device_stats.setdefault(dev, {"total": 0, "correct": 0})
            device_stats[dev]["total"] += 1
            if hit in ("exact", "partial"):
                device_stats[dev]["correct"] += 1

            risk = case.get("risk_level", "MEDIUM")
            risk_stats.setdefault(risk, {"total": 0, "correct": 0})
            risk_stats[risk]["total"] += 1
            if hit in ("exact", "partial"):
                risk_stats[risk]["correct"] += 1

            results.append({
                "id": case["id"], "device": case["device_type"],
                "expected": case["expected_root_cause"],
                "predicted": predicted[:120], "hit": hit,
                "confidence": result.get("confidence", 0),
                "latency_ms": round(elapsed * 1000),
            })

        total = len(cases)
        accuracy = correct / total if total else 0
        summary = {
            "total": total,
            "exact_match": correct,
            "partial_match": partial,
            "accuracy": round(accuracy, 3),
            "combined_hit_rate": round((correct + partial) / total, 3) if total else 0,
            "avg_latency_ms": round((time.perf_counter() - t_start) * 1000 / total),
            "evaluated_at": datetime.now().isoformat(),
        }
        _last_result = {"summary": summary, "details": results,
                        "by_device": device_stats, "by_risk": risk_stats}
        RESULT_CACHE_PATH.write_text(json.dumps(_last_result, ensure_ascii=False, indent=2), encoding="utf-8")
        return _last_result
    finally:
        _eval_running = False


@router.post("/run/llm")
async def run_benchmark_llm(req: BenchmarkRunRequest):
    global _last_result, _eval_running
    if _eval_running:
        raise HTTPException(409, "评测正在运行中")

    cases = _load_cases()
    if req.device:
        cases = [c for c in cases if c["device_type"] == req.device]
    if req.limit:
        cases = cases[:req.limit]
    if not cases:
        raise HTTPException(400, "没有匹配的基准案例")

    _eval_running = True
    t_start = time.perf_counter()
    try:
        from app.agent.diagnosis_agent import DiagnosisAgent
        from app.rag.hybrid_search import get_knowledge_store
        agent = DiagnosisAgent()
        store = get_knowledge_store()
        results = []
        correct = 0

        for case in cases:
            t0 = time.perf_counter()
            rag = store.search(case["symptoms"], top_k=3)
            rag_text = "; ".join([r["text"][:200] for r in rag])
            context = f"故障描述:\n{case['symptoms']}\n\n知识库:\n{rag_text}"
            try:
                result = agent.diagnose(context)
            except Exception as e:
                result = {"report_text": f"评测异常: {e}", "confidence": 0}

            elapsed = time.perf_counter() - t0
            report = result.get("report_text", "")
            hit = "miss"
            expected = case["expected_root_cause"]
            for line in report.split("\n"):
                if any(kw in line for kw in expected[:4].split()):
                    hit = "exact" if expected.lower() in line.lower() else "partial"
                    break

            if hit == "exact":
                correct += 1
            results.append({
                "id": case["id"], "device": case["device_type"],
                "expected": expected, "hit": hit,
                "latency_ms": round(elapsed * 1000),
            })

        total = len(cases)
        summary = {
            "total": total, "exact_match": correct,
            "accuracy": round(correct / total, 3) if total else 0,
            "avg_latency_ms": round((time.perf_counter() - t_start) * 1000 / total),
            "evaluated_at": datetime.now().isoformat(),
        }
        _last_result = {"summary": summary, "details": results}
        RESULT_CACHE_PATH.write_text(json.dumps(_last_result, ensure_ascii=False, indent=2), encoding="utf-8")
        return _last_result
    finally:
        _eval_running = False


@router.get("/result")
async def get_result():
    if not _last_result:
        if RESULT_CACHE_PATH.exists():
            return json.loads(RESULT_CACHE_PATH.read_text(encoding="utf-8"))
        raise HTTPException(404, "暂无评测结果，请先运行 POST /api/benchmark/run")
    return _last_result
