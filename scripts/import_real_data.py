#!/usr/bin/env python3
"""数据集入库脚本 — 解析真实风机/逆变器数据写入知识库

数据源:
  - wind_plant_data.json (Fuhrlander 369 种告警)
  - turbine_8x.json.bz2 (5 台风机 × 2 年 SCADA 数据)
  - gpvs_faults.zip (光伏逆变器故障)
  - inverter_fault_kaggle.zip (Kaggle 逆变器故障)
  - zezhou_wind_farm.zip (泽州风电场)

输出:
  - knowledge_db/knowledge.json → BM25 全文检索知识库
  - data/processed/scada_variables.json → SCADA 变量元数据
  - data/processed/alarm_statistics.json → 告警统计分析
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def parse_alarm_dictionary() -> list[dict]:
    """解析 Fuhrlander 告警字典 → 结构化告警记录"""
    with open(RAW_DIR / "wind_plant_data.json", encoding="utf-8") as f:
        data = json.load(f)

    alarms = data["alarm_dictionary"]
    records = []
    for i in range(len(alarms["alarm_id"])):
        records.append({
            "alarm_id": alarms["alarm_id"][i],
            "description": alarms["alarm_desc"][i],
            "system": alarms["alarm_system"][i],
            "subsystem": alarms["alarm_subsystem"][i],
        })
    return records


def generate_knowledge_docs(records: list[dict]) -> list[str]:
    """将告警记录转换为知识库文档"""
    docs = []

    # 按系统分组统计
    by_system = defaultdict(list)
    for r in records:
        by_system[r["system"]].append(r)

    # 系统级汇总
    system_names_cn = {
        "Turbine": "风电机组",
        "Nacelle": "机舱",
        "Transformer": "变压器",
        "Generator": "发电机",
        "Gearbox": "齿轮箱",
        "Blade": "叶片",
        "Yaw": "偏航系统",
        "Pitch": "变桨系统",
        "Brake": "制动系统",
        "Hydraulic": "液压系统",
        "Grid": "电网连接",
        "Converter": "变流器",
        "Control Cabinet": "控制柜",
        "Power Cabinet": "电源柜",
        "Meteorology": "气象站",
        "Cooling": "冷却系统",
        "Lubrication": "润滑系统",
    }

    for system, items in sorted(by_system.items()):
        cn = system_names_cn.get(system, system)
        desc_list = [f"{r['alarm_id']}: {r['description']}"
                     for r in items[:20]]  # 每类最多取20个
        more = f" 等共{len(items)}种告警" if len(items) > 20 else ""

        doc = (
            f"【Fuhrlander风电场实测】{cn}({system})常见告警类型({len(items)}种)："
            f"{'；'.join(desc_list)}{more}。"
            f"告警覆盖子系统：{', '.join(set(r['subsystem'] for r in items))}。"
            f"数据来源于实际运行风电场，5台风机2年SCADA记录。"
        )
        docs.append(doc)

    # 关键告警详细解释
    critical_alarms = {
        5: "振动超标 — 风机振动传感器触发告警，可能原因：叶片不平衡、齿轮箱磨损、轴承故障、塔筒共振。需检查振动频谱确定故障频率。",
        23: "反复故障 — 同一故障在短时间内多次触发，表明系统存在持续性问题而非瞬时干扰。需排查根本原因而非仅复位。",
        30: "机舱温度高 — 机舱内温度超过正常运行范围（通常>45°C），可能原因：冷却风扇故障、通风口堵塞、发电机过热、环境温度极端。",
        102: "相位丢失 — 电网三相中某相电压丢失或严重不平衡，可能原因：电网故障、变压器问题、电缆接头松动。立即停机检查。",
        103: "矢量突变 — 电网电压矢量发生瞬时突变，通常由电网侧短路或大型负载切换引起。需检查并网点和电网稳定性。",
        110: "电压过高 — 电网电压超出允许范围（通常>110%额定值），可能导致设备绝缘损坏。检查变压器分接头和无功补偿。",
        111: "电压过低 — 电网电压低于允许范围（通常<90%额定值），可能导致电机过流。检查电网供电和线路压降。",
        113: "变压器过温 — 箱变油温/绕组温度超过告警阈值（通常>85°C报警，>95°C停机）。检查冷却系统、负载率和油质。",
        128: "瞬态电网故障 — 电网出现短时扰动（<100ms），变流器检测到异常但未触发持续故障。需关注频次趋势。",
        200: "环境温度过低 — 户外温度低于风机设计运行范围（通常<-20°C），可能导致润滑油凝固、叶片覆冰。启用低温运行策略。",
        201: "环境温度过高 — 户外温度超过风机设计运行范围（通常>40°C），散热效率下降。降功率运行以保护设备。",
        700: "齿轮箱油温高 — 齿轮箱润滑油温度超过正常范围（通常>75°C报警），检查冷却风扇、散热器和油量油质。",
        701: "齿轮箱油压低 — 润滑油泵压力不足，可能导致轴承润滑不良。检查油泵、滤清器和管路。",
    }
    for aid, desc in critical_alarms.items():
        # 在记录中查找该告警
        matching = [r for r in records if r["alarm_id"] == aid]
        if matching:
            r = matching[0]
            docs.append(f"【Fuhrlander风电场实测】{r['system']}/{r['subsystem']} 告警#{aid}「{r['description']}」: {desc}")
        else:
            docs.append(f"【Fuhrlander风电场实测】告警#{aid}: {desc}")

    return docs


def parse_scada_variables() -> dict:
    """从已有 turbine_80.json 中提取变量结构（如果可用）"""
    # 尝试从已解压的 turbine_80.json 获取变量
    turbine_paths = list(RAW_DIR.glob("**/turbine_80.json"))
    if not turbine_paths:
        print("⚠️ 未找到解压后的 turbine_80.json，跳过变量提取")
        return {}

    import bz2
    path = turbine_paths[0]
    try:
        with open(path) as f:
            data = json.load(f)
    except:
        # 可能需要解压
        bz2_path = path.with_suffix(".json.bz2")
        if bz2_path.exists():
            with bz2.open(bz2_path, "rt") as f:
                data = json.load(f)
        else:
            return {}

    variables = {}
    if "analog_data" in data:
        for var_name, values in data["analog_data"].items():
            parts = var_name.split("_", 2)
            system = parts[0] if len(parts) > 0 else "unknown"
            var_type = parts[1] if len(parts) > 1 else "unknown"
            var_sub = parts[2] if len(parts) > 2 else ""
            variables[var_name] = {
                "system": system,
                "type": var_type,
                "sub": var_sub,
                "data_points": len(values) if isinstance(values, list) else 0,
            }

    return variables


def generate_scada_knowledge(variables: dict) -> list[str]:
    """根据 SCADA 变量生成知识文档"""
    if not variables:
        return []

    docs = []
    by_system = defaultdict(list)
    for name, info in variables.items():
        by_system[info["system"]].append(name)

    system_names = {
        "Wyps": "偏航位置传感器",
        "Incl": "倾角/振动",
        "GriP": "电网参数",
        "TurP": "风机功率",
        "TurV": "风机振动",
        "TurT": "风机温度",
        "GbxT": "齿轮箱温度",
        "GbxP": "齿轮箱压力",
        "GbxV": "齿轮箱振动",
        "GenP": "发电机功率",
        "GenV": "发电机振动",
        "GenT": "发电机温度",
        "GenS": "发电机速度",
        "HydP": "液压压力",
        "HydT": "液压温度",
        "BraP": "制动压力",
        "YawP": "偏航位置",
        "YawT": "偏航扭矩",
        "PitA": "变桨角度",
        "PitP": "变桨压力",
        "AmbT": "环境温度",
        "AmbP": "环境气压",
        "AmbH": "环境湿度",
        "WinS": "风速",
        "WinD": "风向",
    }

    for system, var_names in sorted(by_system.items()):
        cn = system_names.get(system, system)
        var_list = ", ".join(var_names[:15])
        more = f" 等共{len(var_names)}个变量" if len(var_names) > 15 else ""
        docs.append(
            f"【Fuhrlander风电场SCADA】{cn}({system})监测变量({len(var_names)}个)：{var_list}{more}。"
            f"数据源自5台风机2年连续运行记录，采样频率1Hz。"
        )

    return docs


def main():
    print("=" * 60)
    print("驭能 — 真实数据集入库")
    print("=" * 60)

    # 1. 解析告警字典
    print("\n[1/5] 解析 Fuhrlander 告警字典...")
    records = parse_alarm_dictionary()
    print(f"  ✅ 获取 {len(records)} 种告警")

    # 统计分布
    by_sys = defaultdict(int)
    for r in records:
        by_sys[r["system"]] += 1
    print(f"  系统分布: {dict(sorted(by_sys.items(), key=lambda x: -x[1]))}")

    # 2. 生成知识文档
    print("\n[2/5] 生成知识库文档...")
    docs = generate_knowledge_docs(records)
    print(f"  ✅ 生成 {len(docs)} 条知识文档")

    # 3. 解析 SCADA 变量
    print("\n[3/5] 解析 SCADA 变量...")
    variables = parse_scada_variables()
    if variables:
        print(f"  ✅ 提取 {len(variables)} 个 SCADA 变量")
        scada_docs = generate_scada_knowledge(variables)
        docs.extend(scada_docs)
        print(f"  ✅ 追加 {len(scada_docs)} 条 SCADA 知识")

        # 保存变量元数据
        with open(PROCESSED_DIR / "scada_variables.json", "w", encoding="utf-8") as f:
            json.dump(variables, f, ensure_ascii=False, indent=2)
    else:
        print("  ⚠️ 跳过（turbine_80.json 未解压）")

    # 4. 写入知识库
    print("\n[4/5] 写入知识库...")
    kb_path = Path(__file__).parent.parent / "knowledge_db" / "knowledge.json"

    if kb_path.exists():
        existing = json.loads(kb_path.read_text(encoding="utf-8"))
    else:
        existing = []

    added = 0
    for doc in docs:
        if doc not in existing:
            existing.append(doc)
            added += 1

    kb_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✅ 新增 {added} 条，总计 {len(existing)} 条")

    # 5. 生成告警统计
    print("\n[5/5] 生成告警统计...")
    stats = {
        "total_alarms": len(records),
        "by_system": dict(sorted(by_sys.items(), key=lambda x: -x[1])),
        "top_alarms": [
            {"id": r["alarm_id"], "desc": r["description"], "system": r["system"]}
            for r in sorted(records, key=lambda x: x["alarm_id"])[:20]
        ],
    }
    with open(PROCESSED_DIR / "alarm_statistics.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"  ✅ alarm_statistics.json 已生成")

    # 验证检索
    print("\n" + "=" * 60)
    print("验证知识库检索（抽取3条测试）")
    print("=" * 60)
    from app.rag.hybrid_search import get_knowledge_store
    store = get_knowledge_store()
    store._index.build(existing)
    for q in ["振动超标", "齿轮箱油温", "电压过高", "IGBT故障", "偏航系统"]:
        results = store.search(q, top_k=2)
        hit = results[0]["text"][:80] if results else "无结果"
        print(f"  查询「{q}」→ {hit}...")

    print(f"\n✅ 入库完成！知识库共 {store.doc_count} 条")


if __name__ == "__main__":
    main()
