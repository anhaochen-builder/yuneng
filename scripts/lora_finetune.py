"""LoRA 微调数据集生成脚本

从长期记忆和反馈池中抽取标注案例，生成 Alpaca 格式 JSONL 训练数据。

触发条件：积累 ≥ 50 个新标注案例（正样本 + 负样本）
输出格式：{"instruction": "...", "input": "...", "output": "..."}

用法: python scripts/lora_finetune.py [--output ./data/finetune/]
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MIN_SAMPLES = 50
TRAIN_SPLIT = 0.8
VAL_SPLIT = 0.1
TEST_SPLIT = 0.1

INSTRUCTION = (
    "你是一位新能源场站智能诊断专家。请根据故障描述和设备信息，"
    "分析故障原因，提供诊断结论和处置方案。"
)


def collect_samples(min_count: int = MIN_SAMPLES) -> list[dict[str, Any]]:
    samples = []

    try:
        from app.memory.memory_service import MemoryService
        memory = MemoryService()
        results = memory.search_long_term("故障", top_k=200)
        for r in results:
            meta = r.get("metadata", {})
            samples.append({
                "text": r.get("text", ""),
                "confidence": meta.get("confidence", 0),
                "fault_type": meta.get("fault_type", ""),
                "risk_level": meta.get("risk_level", ""),
                "source": meta.get("source", "long_term_memory"),
                "task_id": meta.get("task_id", ""),
            })
    except Exception as e:
        logger.warning(f"长期记忆读取失败: {e}")

    filtered = [s for s in samples if s["confidence"] >= 0.6]
    return filtered[:min_count * 2]


def convert_to_alpaca(sample: dict) -> dict[str, str]:
    input_text = f"故障描述: {sample.get('text', '')[:2000]}"
    output_text = (
        f"故障类型: {sample.get('fault_type', '未知')}\n"
        f"风险等级: {sample.get('risk_level', 'MEDIUM')}\n"
        f"置信度: {sample.get('confidence', 0) * 100:.0f}%"
    )
    return {"instruction": INSTRUCTION, "input": input_text, "output": output_text}


def deduplicate(samples: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for s in samples:
        key = s.get("task_id", s.get("text", "")[:100])
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return unique


def validate_dataset(samples: list[dict], output_dir: Path) -> dict[str, Any]:
    stats = {"total": len(samples), "issues": []}

    if len(samples) < MIN_SAMPLES:
        stats["issues"].append(f"样本数不足（{len(samples)} < {MIN_SAMPLES}）")

    lengths = [len(json.dumps(s, ensure_ascii=False)) for s in samples]
    avg_len = sum(lengths) / len(lengths) if lengths else 0
    stats["avg_tokens_est"] = int(avg_len / 2)

    too_long = sum(1 for l in lengths if l > 8000)
    if too_long > 0:
        stats["issues"].append(f"{too_long} 条样本可能超长（> 8000 字符）")

    empty_outputs = sum(1 for s in samples if not s.get("output", "").strip())
    if empty_outputs > 0:
        stats["issues"].append(f"{empty_outputs} 条样本输出为空")

    all_rules = {s.get("risk_level", "") for s in samples}
    if len(all_rules) <= 1:
        stats["issues"].append("风险等级分布单一，可能过拟合")

    return stats


def save_dataset(samples: list[dict], output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    n = len(samples)
    i_train = int(n * TRAIN_SPLIT)
    i_val = int(n * (TRAIN_SPLIT + VAL_SPLIT))

    paths = {}
    for name, data in [
        ("train", samples[:i_train]),
        ("val", samples[i_train:i_val]),
        ("test", samples[i_val:]),
    ]:
        path = output_dir / f"{name}.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        paths[name] = path
        logger.info(f"  {name}: {len(data)} 条 → {path}")

    return paths


def generate_lora_dataset(output_dir: str = "") -> dict[str, Any]:
    base = Path(output_dir) if output_dir else Path(__file__).parent.parent / "data" / "finetune"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = base / f"lora_{timestamp}"

    logger.info(f"开始生成 LoRA 微调数据集")
    logger.info(f"输出目录: {output_dir}")

    raw = collect_samples()
    logger.info(f"收集到 {len(raw)} 条原始样本")

    raw = deduplicate(raw)
    logger.info(f"去重后 {len(raw)} 条")

    alpaca = [convert_to_alpaca(s) for s in raw]
    alpaca = [a for a in alpaca if a["output"].strip() and a["input"].strip()]
    logger.info(f"转换后 {len(alpaca)} 条 Alpaca 格式样本")

    stats = validate_dataset(alpaca, output_dir)
    paths = save_dataset(alpaca, output_dir)

    report = {
        "generated_at": datetime.now().isoformat(),
        "output_dir": str(output_dir),
        "total_samples": len(alpaca),
        "splits": {k: str(v) for k, v in paths.items()},
        "stats": stats,
        "quality": "good" if not stats["issues"] else "needs_review",
        "recommendation": (
            "可以使用该数据集进行 LoRA 微调" if not stats["issues"]
            else f"建议修复以下问题后使用: {stats['issues']}"
        ),
    }

    report_path = output_dir / "dataset_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"生成报告: {report_path}")

    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="LoRA 微调数据集生成")
    parser.add_argument("--output", type=str, default="", help="输出目录")
    parser.add_argument("--dry-run", action="store_true", help="仅统计不保存")
    args = parser.parse_args()

    report = generate_lora_dataset(args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
