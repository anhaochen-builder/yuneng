#!/usr/bin/env python3
"""Fuhrländer 风机数据集导入脚本

将 turbine_80~84.json.bz2 解压并导入知识库。
- 告警记录 → 知识库文档
- 模拟量数据 → SCADA 模拟参考（可选）
"""

import json
import bz2
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.rag.vector_store import add_documents
from app.rag.hybrid_search import HybridSearchService

DATASET_DIR = Path(__file__).parent.parent / "data" / "raw" / "fuhrlander" / "fuhrlander-master" / "dataset"


def load_turbine(turbine_id: int) -> dict:
    path = DATASET_DIR / f"turbine_{turbine_id}.json.bz2"
    with bz2.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def extract_alarm_docs(data: dict) -> list[str]:
    """从告警数据生成知识库文档"""
    alarms = data.get("alarms", {})
    alarm_ids = alarms.get("alarm_id", [])
    alarm_descs = alarms.get("alarm_desc", [])
    times_ini = alarms.get("date_time_ini", [])
    times_end = alarms.get("date_time_end", [])

    docs = []
    seen = set()

    for i in range(min(len(alarm_ids), 5000)):
        aid = alarm_ids[i]
        if aid in seen:
            continue
        seen.add(aid)

        desc = alarm_descs[i] if i < len(alarm_descs) else ""
        t0 = times_ini[i] if i < len(times_ini) else ""
        t1 = times_end[i] if i < len(times_end) else ""

        doc = (
            f"风机告警记录 id={aid}。"
            f"告警描述: {desc}。"
            f"开始时间: {t0}，结束时间: {t1}。"
        )
        docs.append(doc)

    return docs


def extract_analog_summary(data: dict) -> str:
    """从模拟量数据提取特征摘要"""
    analog = data.get("analog_data", {})
    lines = [f"风机 {data.get('turbine_id', '?')} 模拟量数据概要:"]
    lines.append(f"采样频率: {data.get('analog_data_frequency_seconds', '?')}秒")
    lines.append(f"记录数: {data.get('number_of_entries', '?')}")

    key_fields = [
        "wgdc_avg_TriGri_PhV", "wgdc_avg_TriGri_A",
        "wgdc_avg_TriGri_PwrAt", "wgdc_avg_WSpd",
        "wgdc_avg_GBX_Oil_Temp", "wgdc_avg_Gen_Bear_Temp",
    ]

    for field in key_fields:
        if field in analog:
            values = analog[field]
            valid = [v for v in values if v is not None]
            if valid:
                lines.append(
                    f"{field}: min={min(valid):.1f} max={max(valid):.1f} "
                    f"mean={sum(valid)/len(valid):.1f}"
                )

    return "\n".join(lines)


def main():
    print("=== Fuhrländer 数据集导入 ===")

    all_docs = []
    all_metas = []

    for turbine_id in [80, 81, 82, 83, 84]:
        path = DATASET_DIR / f"turbine_{turbine_id}.json.bz2"
        if not path.exists():
            print(f"  T{turbine_id}: 文件不存在, 跳过")
            continue

        print(f"  T{turbine_id}: 加载中...", end=" ", flush=True)
        data = load_turbine(turbine_id)

        alarm_docs = extract_alarm_docs(data)
        print(f"{len(alarm_docs)} 条告警", end="", flush=True)

        for doc in alarm_docs:
            all_docs.append(doc)
            all_metas.append({
                "source": "fuhrlander",
                "turbine_id": turbine_id,
                "type": "alarm",
            })

        # 模拟量摘要
        summary = extract_analog_summary(data)
        all_docs.append(summary)
        all_metas.append({
            "source": "fuhrlander",
            "turbine_id": turbine_id,
            "type": "analog_summary",
        })

        print(" ✅")

    print(f"\n总计: {len(all_docs)} 条文档")

    if all_docs:
        n = add_documents(
            texts=all_docs,
            metadatas=all_metas,
            collection_name="power_knowledge",
        )
        print(f"入库: {n} 条")

        searcher = HybridSearchService()
        searcher.index_keywords(all_docs)
        print(f"BM25 索引: {len(all_docs)} 条 ✅")

    print("\n=== 导入完成 ===")


if __name__ == "__main__":
    main()
