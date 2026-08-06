"""交接班 + 数据校验 + 场站健康度 API"""
import logging
from fastapi import APIRouter, Query
from app.services.field_services import (
    generate_shift_report, get_weather_context, get_safety_checklist,
    get_maintenance_window, DEFAULT_SAFETY_RULES,
)
from app.services.data_validator import DataValidator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/field", tags=["field"])


@router.get("/shift-report")
async def shift_report():
    from app.api.alarm import _tasks as alarm_tasks
    from app.api.workorder import _load as load_orders
    from datetime import datetime

    alarm_list = [
        {"device_id": t.get("device_id", ""), "alarm_level": "HIGH",
         "alarm_message": "", "risk_level": t.get("risk_level", "MEDIUM")}
        for t in alarm_tasks.values()
    ]
    diag_list = [
        {"device_id": t.get("device_id", ""), "risk_level": t.get("risk_level", "MEDIUM"),
         "root_cause": "", "confidence": t.get("confidence", 0)}
        for t in alarm_tasks.values() if t.get("status") == "COMPLETED"
    ]
    orders = list(load_orders().values()) if callable(load_orders) else []

    report = generate_shift_report(alarm_list, diag_list, orders)
    return report


@router.get("/weather")
async def weather_context():
    import json, urllib.request
    try:
        url = "https://wttr.in/?format=j1"
        req = urllib.request.Request(url, headers={"User-Agent": "yuneng/1.0"})
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read())
        current = data.get("current_condition", [{}])[0]
        temp = current.get("temp_C", "N/A")
        humidity = current.get("humidity", "N/A")
        wind = current.get("windspeedKmph", "N/A")
        desc_en = current.get("weatherDesc", [{}])[0].get("value", "")

        trans = {
            "Partly Cloudy": "多云转晴", "Partly cloudy": "多云", "Sunny": "晴",
            "Clear": "晴", "Cloudy": "阴", "Overcast": "阴",
            "Light Rain": "小雨", "Moderate Rain": "中雨", "Heavy Rain": "大雨",
            "Mist": "雾", "Fog": "大雾", "Haze": "霾",
            "Thunderstorm": "雷暴", "Snow": "雪",
        }
        desc = trans.get(desc_en.strip(), desc_en.strip())

        alerts = []
        if any(kw in desc_en for kw in ["雷暴", "thunder", "雷雨", "storm", "Thunder"]):
            alerts.append("雷暴天气预警：需关注雷击导致的绝缘故障和线路跳闸")
            alerts.append("雷暴天气预警：需关注雷击导致的绝缘故障和线路跳闸")
        if temp != "N/A" and int(temp) < 0:
            alerts.append("低温预警：风机叶片可能覆冰，光伏组件效率下降")
        if temp != "N/A" and int(temp) > 35:
            alerts.append("高温预警：变压器/逆变器过温风险升高")
        if wind != "N/A" and int(wind) > 50:
            alerts.append("大风预警：风机可能触发超速保护")

        return {
            "temp": temp, "humidity": humidity, "wind": wind, "desc": desc,
            "alerts": alerts,
            "context": f"温度 {temp}°C, 湿度 {humidity}%, 风速 {wind}km/h, {desc}"
        }
    except Exception:
        return {"temp": "--", "humidity": "--", "wind": "--", "desc": "获取失败", "alerts": [], "context": "气象数据暂不可用"}


@router.get("/safety-checklist")
async def safety_checklist(device_type: str = Query("变压器"),
                           risk_level: str = Query("HIGH")):
    rules = get_safety_checklist(device_type, risk_level)
    return {"device_type": device_type, "risk_level": risk_level, "checklist": rules}


@router.get("/safety-rules")
async def all_safety_rules():
    return {"rules": DEFAULT_SAFETY_RULES}


@router.get("/maintenance-window")
async def maintenance_window(device_type: str = Query("变压器"),
                             risk_level: str = Query("HIGH")):
    return {"suggestion": get_maintenance_window(device_type, risk_level)}


@router.post("/validate-data")
async def validate_data(device_id: str, device_type: str,
                        point_name: str, value: float,
                        voltage: float = 0, current: float = 0, temperature: float = 0):
    params = {"电压": voltage, "电流": current, "温度": temperature}
    ok, reason = DataValidator.validate(device_id, device_type, point_name, value, params)
    return {"valid": ok, "reason": reason}


@router.get("/station-health")
async def station_health():
    devices = [
        {"name": "1号风机", "type": "风机", "status": "running", "health": 85, "alarms": 2},
        {"name": "2号风机", "type": "风机", "status": "running", "health": 92, "alarms": 0},
        {"name": "3号风机", "type": "风机", "status": "warning", "health": 68, "alarms": 5},
        {"name": "1号逆变器", "type": "逆变器", "status": "running", "health": 90, "alarms": 0},
        {"name": "2号逆变器", "type": "逆变器", "status": "fault", "health": 45, "alarms": 12},
        {"name": "3号逆变器", "type": "逆变器", "status": "running", "health": 88, "alarms": 1},
        {"name": "1号主变", "type": "变压器", "status": "running", "health": 95, "alarms": 0},
        {"name": "1号开关柜", "type": "开关柜", "status": "warning", "health": 70, "alarms": 3},
        {"name": "1号储能舱", "type": "储能", "status": "running", "health": 82, "alarms": 1},
        {"name": "2号储能舱", "type": "储能", "status": "running", "health": 91, "alarms": 0},
    ]
    type_summary = {}
    for d in devices:
        t = d["type"]
        type_summary.setdefault(t, {"total": 0, "healthy": 0, "warning": 0, "fault": 0, "avg_health": 0})
        type_summary[t]["total"] += 1
        if d["health"] >= 80:
            type_summary[t]["healthy"] += 1
        elif d["health"] >= 60:
            type_summary[t]["warning"] += 1
        else:
            type_summary[t]["fault"] += 1
        type_summary[t]["avg_health"] += d["health"]

    for t in type_summary:
        type_summary[t]["avg_health"] = round(type_summary[t]["avg_health"] / type_summary[t]["total"])

    return {"devices": devices, "type_summary": type_summary, "total": len(devices)}
