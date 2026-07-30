"""MCP 电力工具 — 5个工具实现"""

import json
import random
from datetime import datetime, timedelta
from typing import Any

MOCK_DEVICES: dict[str, dict[str, Any]] = {
    "WT001": {"name": "1号风机", "type": "wind_turbine", "capacity": 3.0, "location": "A区"},
    "WT002": {"name": "2号风机", "type": "wind_turbine", "capacity": 3.0, "location": "A区"},
    "INV001": {"name": "1号逆变器", "type": "inverter", "capacity": 500, "location": "B区"},
    "INV002": {"name": "2号逆变器", "type": "inverter", "capacity": 500, "location": "B区"},
    "TRA001": {"name": "1号箱变", "type": "transformer", "capacity": 2000, "location": "C区"},
    "PV001": {"name": "1号光伏阵列", "type": "photovoltaic", "capacity": 1000, "location": "D区"},
}

MOCK_ALARMS = [
    {"code": "ALM-001", "desc": "通讯中断", "severity": "critical"},
    {"code": "ALM-002", "desc": "温度过高", "severity": "high"},
    {"code": "ALM-003", "desc": "电压异常", "severity": "medium"},
    {"code": "ALM-004", "desc": "振动超标", "severity": "high"},
    {"code": "ALM-005", "desc": "绝缘降低", "severity": "critical"},
    {"code": "ALM-006", "desc": "逆变器效率低", "severity": "medium"},
    {"code": "ALM-007", "desc": "并网异常", "severity": "high"},
    {"code": "ALM-008", "desc": "直流侧接地", "severity": "critical"},
]


def get_device_status(device_id: str) -> dict:
    """查询设备实时运行状态"""
    if device_id not in MOCK_DEVICES:
        return {"error": f"设备 {device_id} 未找到"}
    device = MOCK_DEVICES[device_id]
    return {
        "device_id": device_id,
        "device_name": device["name"],
        "device_type": device["type"],
        "status": random.choice(["running", "warning", "fault", "stopped"]),
        "timestamp": datetime.now().isoformat(),
        "parameters": {
            "temperature_c": round(random.uniform(35, 85), 1),
            "vibration_mm_s": round(random.uniform(0.1, 3.5), 2),
            "power_kw": round(random.uniform(0, device["capacity"] * 0.95), 1),
            "voltage_v": round(random.uniform(360, 420), 1),
            "current_a": round(random.uniform(50, 900), 1),
            "frequency_hz": round(random.uniform(49.8, 50.2), 2),
        },
        "location": device["location"],
    }


def get_alarm_history(device_id: str, start_time: str = None, end_time: str = None, limit: int = 20) -> dict:
    """查询设备历史告警记录"""
    alarms = []
    for i in range(min(limit, 12)):
        alarm = random.choice(MOCK_ALARMS)
        alarms.append({
            "id": f"ALM-{datetime.now().strftime('%Y%m%d')}-{i:04d}",
            "device_id": device_id,
            "code": alarm["code"],
            "description": alarm["desc"],
            "severity": alarm["severity"],
            "timestamp": (datetime.now() - timedelta(hours=random.randint(1, 720))).isoformat(),
            "status": random.choice(["active", "cleared", "acknowledged"]),
        })
    return {"device_id": device_id, "total": len(alarms), "alarms": alarms}


def get_device_logs(device_id: str, log_type: str = "event", limit: int = 10) -> dict:
    """查询设备运行日志"""
    log_messages = [
        "设备启动完成", "参数异常波动", "通讯链路恢复", "温度阈值告警",
        "例行巡检完成", "有功功率骤降", "无功补偿投入", "保护动作触发",
        "防雷器动作", "并网开关跳闸", "冷却风扇故障", "直流母线电压波动",
    ]
    log_levels = ["INFO", "WARN", "ERROR"]
    logs = []
    for i in range(min(limit, 10)):
        logs.append({
            "id": f"LOG-{i:04d}",
            "device_id": device_id,
            "type": log_type,
            "level": random.choice(log_levels),
            "message": random.choice(log_messages),
            "timestamp": (datetime.now() - timedelta(minutes=random.randint(1, 1440))).isoformat(),
        })
    return {"device_id": device_id, "log_type": log_type, "logs": logs}


def get_defect_tickets(device_id: str, status: str = "all") -> dict:
    """查询设备缺陷工单"""
    tickets = [
        {
            "id": "TK-202607001",
            "device_id": device_id,
            "title": "通讯模块异常",
            "description": "PLC通讯频繁中断，排查发现光纤接口松动",
            "status": "processing",
            "priority": "high",
            "created_at": (datetime.now() - timedelta(days=3)).isoformat(),
            "assigned_to": "张工",
        },
        {
            "id": "TK-202607002",
            "device_id": device_id,
            "title": "温度传感器偏移",
            "description": "温度传感器读数偏差较大，需校准或更换",
            "status": "open",
            "priority": "medium",
            "created_at": (datetime.now() - timedelta(days=1)).isoformat(),
            "assigned_to": "李工",
        },
        {
            "id": "TK-202606003",
            "device_id": device_id,
            "title": "IGBT模块更换",
            "description": "逆变器A相IGBT模块老化，功率下降30%",
            "status": "closed",
            "priority": "high",
            "created_at": (datetime.now() - timedelta(days=20)).isoformat(),
            "assigned_to": "王工",
        },
        {
            "id": "TK-202606004",
            "device_id": device_id,
            "title": "风机齿轮箱异响",
            "description": "巡检发现齿轮箱运行时存在异响，振动值升高",
            "status": "processing",
            "priority": "critical",
            "created_at": (datetime.now() - timedelta(days=5)).isoformat(),
            "assigned_to": "赵工",
        },
    ]
    filtered = tickets if status == "all" else [t for t in tickets if t["status"] == status]
    return {"device_id": device_id, "tickets": filtered}


def search_safety_rules(keyword: str, limit: int = 5) -> dict:
    """检索电力安规条款"""
    rules_db = [
        {
            "id": "SAFE-001",
            "chapter": "第3章 停电操作",
            "content": f"在进行{keyword}相关操作前，必须确认设备已完全停电，并悬挂'禁止合闸，有人工作'标识牌。操作人员应戴绝缘手套、穿绝缘靴。",
            "source": "国家电网电力安全工作规程（变电部分）",
        },
        {
            "id": "SAFE-002",
            "chapter": "第5章 验电与接地",
            "content": f"{keyword}操作时，必须使用相应电压等级的验电器进行验电，确认无电压后方可进行下一步操作。高压验电必须戴绝缘手套。",
            "source": "国家电网电力安全工作规程（变电部分）",
        },
        {
            "id": "SAFE-003",
            "chapter": "第8章 安全措施",
            "content": f"涉及{keyword}的作业，必须办理工作票，并指定专人监护。作业人员不得单独进入高压室。",
            "source": "国家电网电力安全工作规程（变电部分）",
        },
        {
            "id": "SAFE-004",
            "chapter": "第4章 电气操作基本要求",
            "content": f"电气操作应根据调度指令或值班负责人的命令执行。{keyword}类设备的操作需两人进行，一人操作、一人监护。",
            "source": "宁夏电网调度规程",
        },
        {
            "id": "SAFE-005",
            "chapter": "第11章 新能源场站特殊规定",
            "content": f"新能源场站的{keyword}设备停电检修，必须与调度部门确认已退出AGC/AVC控制，并在SCADA系统中挂检修牌。",
            "source": "宁夏电网调度规程",
        },
    ]
    return {"keyword": keyword, "total": len(rules_db), "rules": rules_db[:limit]}


def get_device_profile(device_id: str) -> dict:
    """查询设备台账信息"""
    if device_id not in MOCK_DEVICES:
        return {"error": f"设备 {device_id} 未找到"}
    device = MOCK_DEVICES[device_id]
    return {
        "device_id": device_id,
        **device,
        "manufacturer": "金风科技" if device["type"] == "wind_turbine" else "阳光电源",
        "model": f"{device['type'].upper()}-{random.randint(100, 999)}",
        "install_date": "2024-03-15",
        "last_maintenance": (datetime.now() - timedelta(days=random.randint(30, 180))).strftime("%Y-%m-%d"),
        "rated_power": f"{device['capacity']}MW" if device["type"] == "wind_turbine" else f"{device['capacity']}kW",
        "operating_hours": random.randint(5000, 15000),
    }


# 工具注册表
TOOL_REGISTRY: dict[str, Any] = {
    "get_device_status": get_device_status,
    "get_alarm_history": get_alarm_history,
    "get_device_logs": get_device_logs,
    "get_defect_tickets": get_defect_tickets,
    "search_safety_rules": search_safety_rules,
    "get_device_profile": get_device_profile,
}
