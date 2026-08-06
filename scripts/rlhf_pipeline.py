"""RLHF 反馈驱动微调自动化 Pipeline

流程:
  1. 收集 feedback 数据 (accurate + inaccurate)
  2. 构造微调数据集 (正样本 + 负样本对比)
  3. 达到阈值(50条)时自动触发 LoRA 微调
  4. 模型版本管理 + A/B 测试准备

用法:
  python scripts/rlhf_pipeline.py status          # 查看数据状态
  python scripts/rlhf_pipeline.py prepare          # 准备微调数据集
  python scripts/rlhf_pipeline.py train            # 触发微调
  python scripts/rlhf_pipeline.py deploy <version> # 部署模型版本
"""

import json
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("rlhf")

DATA_DIR = Path(__file__).parent.parent / "data"
FEEDBACK_FILE = DATA_DIR / "feedback_records.jsonl"
TRAINING_DATA_DIR = DATA_DIR / "training"
VERSIONS_FILE = DATA_DIR / "model_versions.json"

TRAINING_DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_feedback() -> list[dict]:
    records = []
    if FEEDBACK_FILE.exists():
        for line in FEEDBACK_FILE.read_text(encoding="utf-8").strip().split("\n"):
            if line.strip():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records


def load_versions() -> dict:
    if VERSIONS_FILE.exists():
        return json.loads(VERSIONS_FILE.read_text(encoding="utf-8"))
    return {"versions": [], "active": None}


def save_versions(data: dict):
    VERSIONS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_status():
    records = load_feedback()
    accurate = [r for r in records if r.get("rating") == "accurate"]
    partially = [r for r in records if r.get("rating") == "partially_accurate"]
    inaccurate = [r for r in records if r.get("rating") == "inaccurate"]

    print(f"\n{'='*50}")
    print(f"  RLHF 反馈数据状态")
    print(f"{'='*50}")
    print(f"  总反馈: {len(records)}")
    print(f"  准确 (正样本): {len(accurate)}")
    print(f"  部分准确: {len(partially)}")
    print(f"  不准确 (负样本): {len(inaccurate)}")
    print(f"  微调阈值: 50 条 (还需 {max(0, 50 - len(accurate))} 条准确反馈)")
    print(f"  是否达到阈值: {'✅ 是' if len(accurate) >= 50 else '❌ 否'}")

    versions = load_versions()
    print(f"\n  模型版本:")
    for v in versions.get("versions", []):
        marker = " ← 当前" if v["id"] == versions.get("active") else ""
        print(f"    v{v['id']} | {v['samples']}样本 | {v['created_at'][:10]}{marker}")


def cmd_prepare():
    records = load_feedback()
    accurate = [r for r in records if r.get("rating") == "accurate"]
    inaccurate = [r for r in records if r.get("rating") == "inaccurate"]

    if len(accurate) < 10:
        print(f"正样本不足 ({len(accurate)} < 10)，数据准备跳过")
        return

    positive_pairs = []
    for r in accurate[:100]:
        comment = r.get("comment", "") or ""
        corrected = r.get("corrected_root_cause", "") or ""
        text = f"故障诊断任务: {r.get('task_id', '')}\n确认结果: 诊断正确"
        if comment:
            text += f"\n运维反馈: {comment}"
        if corrected:
            text += f"\n根因: {corrected}"
        positive_pairs.append({"text": text, "label": 1})

    negative_pairs = []
    for r in inaccurate[:min(50, len(inaccurate))]:
        text = f"故障诊断任务: {r.get('task_id', '')}\n确认结果: 诊断不准确"
        if r.get("corrected_root_cause"):
            text += f"\n正确根因: {r['corrected_root_cause']}"
        if r.get("comment"):
            text += f"\n运维反馈: {r['comment']}"
        negative_pairs.append({"text": text, "label": 0})

    dataset = {
        "version": datetime.now().strftime("%Y%m%d-%H%M%S"),
        "positive_samples": len(positive_pairs),
        "negative_samples": len(negative_pairs),
        "total": len(positive_pairs) + len(negative_pairs),
        "data": positive_pairs + negative_pairs,
    }

    out_path = TRAINING_DATA_DIR / f"rlhf_dataset_{dataset['version']}.json"
    out_path.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n微调数据集已生成: {out_path}")
    print(f"  正样本: {dataset['positive_samples']}")
    print(f"  负样本: {dataset['negative_samples']}")
    print(f"  总计: {dataset['total']}")


def cmd_train():
    datasets = sorted(TRAINING_DATA_DIR.glob("rlhf_dataset_*.json"))
    if not datasets:
        print("未找到微调数据集，请先运行 prepare")
        return

    latest = datasets[-1]
    data = json.loads(latest.read_text(encoding="utf-8"))
    if data["total"] < 10:
        print(f"数据量不足 ({data['total']} < 10)，训练跳过")
        return

    version_id = data["version"]
    print(f"\n使用数据集: {latest.name} ({data['total']} 条)")
    print(f"触发 LoRA 微调...")

    import subprocess
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "lora_finetune.py"),
         "--dataset", str(latest)],
        capture_output=True, text=True, timeout=600
    )

    if result.returncode == 0:
        print(f"微调完成! stdout lines: {len(result.stdout.splitlines())}")
        versions = load_versions()
        versions["versions"].append({
            "id": version_id,
            "samples": data["total"],
            "created_at": datetime.now().isoformat(),
            "dataset": latest.name,
        })
        if not versions["active"]:
            versions["active"] = version_id
        save_versions(versions)
    else:
        print(f"微调失败: {result.stderr[:500]}")


def cmd_deploy(version: str):
    versions = load_versions()
    found = any(v["id"] == version for v in versions["versions"])
    if not found:
        print(f"版本 v{version} 不存在")
        return

    versions["active"] = version
    save_versions(versions)
    print(f"已部署版本 v{version}")


def record_feedback(record: dict):
    """外部调用：记录反馈数据"""
    with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    accurate_count = sum(1 for r in load_feedback() if r.get("rating") == "accurate")
    if accurate_count >= 50:
        logger.info(f"准确反馈达到 {accurate_count} 条，建议运行: python scripts/rlhf_pipeline.py prepare && python scripts/rlhf_pipeline.py train")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RLHF 反馈驱动微调 Pipeline")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="查看数据状态")
    sub.add_parser("prepare", help="准备微调数据集")
    sub.add_parser("train", help="触发 LoRA 微调")

    deploy_parser = sub.add_parser("deploy", help="部署模型版本")
    deploy_parser.add_argument("version", help="版本号")

    args = parser.parse_args()

    if args.command == "status":
        cmd_status()
    elif args.command == "prepare":
        cmd_prepare()
    elif args.command == "train":
        cmd_train()
    elif args.command == "deploy":
        cmd_deploy(args.version)
    else:
        parser.print_help()
