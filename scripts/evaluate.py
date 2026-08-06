"""诊断准确率 Benchmark 评测框架

用法:
    python scripts/evaluate.py                    # 全部案例
    python scripts/evaluate.py --device 逆变器     # 按设备筛选
    python scripts/evaluate.py --limit 10         # 限制数量
    python scripts/evaluate.py --quick            # 仅规则引擎评测（秒级）
"""

import json
import sys
import time
import argparse
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
logging.basicConfig(level=logging.WARNING)

BENCHMARK_PATH = Path(__file__).parent.parent / "data" / "benchmark_cases.json"


def load_cases(path: str | None = None) -> list[dict]:
    p = Path(path) if path else BENCHMARK_PATH
    return json.loads(p.read_text(encoding="utf-8"))


def classify_hit(predicted: str, expected: str, keywords: list[str]) -> str:
    pred_lower = predicted.lower()
    exp_lower = expected.lower()
    if exp_lower in pred_lower or any(k.lower() in pred_lower for k in keywords):
        return "exact"
    if any(w in pred_lower for w in exp_lower.split()):
        return "partial"
    return "miss"


def evaluate_rule_engine(cases: list[dict]) -> dict:
    from app.agent.case_reasoner import case_reasoner
    results = []
    correct = 0
    partial = 0
    total = 0
    by_device = defaultdict(lambda: {"total": 0, "correct": 0})
    by_risk = defaultdict(lambda: {"total": 0, "correct": 0})
    latencies = []

    for case in cases:
        t0 = time.perf_counter()
        result = case_reasoner.diagnose(
            symptoms=case["symptoms"],
            device_id=case.get("device_id", ""),
            device_type=case.get("device_type", ""),
        )
        elapsed = time.perf_counter() - t0
        latencies.append(elapsed)

        predicted = result.get("root_cause", "")
        hit = classify_hit(predicted, case["expected_root_cause"], case.get("keywords", []))
        total += 1
        if hit == "exact":
            correct += 1
        elif hit == "partial":
            partial += 1

        by_device[case["device_type"]]["total"] += 1
        if hit in ("exact", "partial"):
            by_device[case["device_type"]]["correct"] += 1

        risk = case.get("risk_level", "MEDIUM")
        by_risk[risk]["total"] += 1
        if hit in ("exact", "partial"):
            by_risk[risk]["correct"] += 1

        results.append({
            "id": case["id"],
            "device": case["device_type"],
            "expected": case["expected_root_cause"],
            "predicted": predicted[:120],
            "hit": hit,
            "confidence": result.get("confidence", 0),
            "latency_ms": round(elapsed * 1000),
        })

    accuracy = correct / total if total else 0
    partial_rate = partial / total if total else 0
    return {
        "total": total,
        "exact_match": correct,
        "partial_match": partial,
        "accuracy": round(accuracy, 3),
        "partial_rate": round(partial_rate, 3),
        "combined_hit_rate": round((correct + partial) / total, 3) if total else 0,
        "avg_latency_ms": round(sum(latencies) / len(latencies) * 1000) if latencies else 0,
        "by_device": {k: {"accuracy": round(v["correct"] / v["total"], 3), **v}
                      for k, v in by_device.items()},
        "by_risk": {k: {"accuracy": round(v["correct"] / v["total"], 3), **v}
                    for k, v in by_risk.items()},
        "details": results,
    }


def evaluate_with_llm(cases: list[dict]) -> dict:
    try:
        from app.agent.diagnosis_agent import DiagnosisAgent
        from app.rag.hybrid_search import get_knowledge_store
        agent = DiagnosisAgent()
        store = get_knowledge_store()
    except Exception as e:
        return {"error": str(e), "note": "LLM评测需要完整环境和API Key"}

    results = []
    correct = 0
    partial = 0
    total = 0
    latencies = []

    for case in cases:
        t0 = time.perf_counter()
        rag = store.search(case["symptoms"], top_k=3)
        rag_text = "; ".join([r["text"][:200] for r in rag])
        context = f"故障描述:\n{case['symptoms']}\n\n知识库:\n{rag_text}"
        try:
            result = agent.diagnose(context)
        except Exception as e:
            result = {"report_text": f"评测异常: {e}", "confidence": 0, "root_cause": ""}

        elapsed = time.perf_counter() - t0
        latencies.append(elapsed)

        report = result.get("report_text", "")
        predicted = result.get("root_cause", "")

        if not predicted:
            for line in report.split("\n"):
                line_s = line.strip()
                if ("根因" in line_s and "#" not in line_s
                        and len(line_s) > 10 and "步骤" not in line_s):
                    predicted = line_s
                    break

        hit = classify_hit(predicted, case["expected_root_cause"], case.get("keywords", []))
        total += 1
        if hit == "exact":
            correct += 1
        elif hit == "partial":
            partial += 1

        results.append({
            "id": case["id"],
            "device": case["device_type"],
            "expected": case["expected_root_cause"],
            "predicted_cause_line": predicted[:200],
            "hit": hit,
            "confidence": result.get("confidence", 0),
            "latency_ms": round(elapsed * 1000),
        })
        print(f"  [{case['id']}] {hit:6s} | {case['expected_root_cause'][:40]:40s} | {predicted[:60]}")

    accuracy = correct / total if total else 0
    return {
        "total": total,
        "exact_match": correct,
        "partial_match": partial,
        "accuracy": round(accuracy, 3),
        "combined_hit_rate": round((correct + partial) / total, 3) if total else 0,
        "avg_latency_ms": round(sum(latencies) / len(latencies) * 1000) if latencies else 0,
        "details": results,
    }


def print_report(result: dict):
    print(f"\n{'='*60}")
    print(f"  诊断准确率 Benchmark")
    print(f"{'='*60}")
    print(f"  总案例: {result['total']}")
    print(f"  精确匹配: {result.get('exact_match', 0)} ({result.get('accuracy', 0):.1%})")
    print(f"  部分匹配: {result.get('partial_match', 0)} ({result.get('partial_rate', 0):.1%})")
    print(f"  综合命中率: {result.get('combined_hit_rate', 0):.1%}")
    print(f"  平均延迟: {result.get('avg_latency_ms', 0)}ms")
    print(f"\n  按设备类型:")
    for device, stats in result.get("by_device", {}).items():
        bar = "█" * int(stats["accuracy"] * 20)
        print(f"    {device:8s} │ {bar:20s} │ {stats['accuracy']:.1%} ({stats['correct']}/{stats['total']})")
    print(f"\n  按风险等级:")
    for risk, stats in result.get("by_risk", {}).items():
        bar = "█" * int(stats["accuracy"] * 20)
        print(f"    {risk:8s} │ {bar:20s} │ {stats['accuracy']:.1%} ({stats['correct']}/{stats['total']})")

    if result.get("details"):
        misses = [d for d in result["details"] if d["hit"] == "miss"]
        if misses:
            print(f"\n  未命中案例 ({len(misses)}):")
            for m in misses[:10]:
                print(f"    [{m['id']}] {m['device']}: 期望={m['expected'][:50]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="诊断准确率 Benchmark")
    parser.add_argument("--device", type=str, help="按设备类型筛选")
    parser.add_argument("--limit", type=int, help="限制案例数")
    parser.add_argument("--quick", action="store_true", help="仅规则引擎评测")
    parser.add_argument("--llm", action="store_true", help="LLM评测（需要API Key）")
    parser.add_argument("--output", type=str, help="输出JSON报告路径")
    args = parser.parse_args()

    cases = load_cases()
    if args.device:
        cases = [c for c in cases if c["device_type"] == args.device]
    if args.limit:
        cases = cases[:args.limit]

    print(f"加载 {len(cases)} 个基准案例")

    if args.llm:
        print("\n运行 LLM 诊断评测...")
        result = evaluate_with_llm(cases)
    else:
        print("\n运行规则引擎诊断评测...")
        result = evaluate_rule_engine(cases)

    if "error" in result:
        print(f"评测失败: {result['error']}")
    else:
        print_report(result)

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n报告已保存: {out_path}")
