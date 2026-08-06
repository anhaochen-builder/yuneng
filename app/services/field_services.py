"""交接班报告生成 + 气象数据解析"""
import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


def generate_shift_report(alarms: list[dict], diagnoses: list[dict],
                          workorders: list[dict], shift_start: str = "") -> dict:
    now = datetime.now()
    if not shift_start:
        shift_start_dt = now.replace(hour=8 if now.hour < 20 else 20, minute=0, second=0)
    else:
        shift_start_dt = datetime.fromisoformat(shift_start)

    total_alarms = len(alarms)
    total_diagnoses = len(diagnoses)
    critical = sum(1 for d in diagnoses if d.get("risk_level", "") in ("CRITICAL", "HIGH"))
    pending_orders = sum(1 for w in workorders if w.get("status") not in ("closed", "cancelled"))

    summary_lines = [
        f"交班时间: {now.strftime('%Y-%m-%d %H:%M')}",
        f"本班时段: {shift_start_dt.strftime('%H:%M')} — {now.strftime('%H:%M')}",
        f"本班告警: {total_alarms} 条",
        f"触发诊断: {total_diagnoses} 次",
        f"高危诊断: {critical} 条",
        f"待处理工单: {pending_orders} 单",
    ]

    if critical > 0:
        summary_lines.append("\n⚠️ 高危事项（需下一班重点关注）:")
        for d in diagnoses:
            if d.get("risk_level") in ("CRITICAL", "HIGH"):
                summary_lines.append(
                    f"  - [{d.get('device_id', '?')}] {d.get('root_cause', '?')[:60]} "
                    f"(置信度 {d.get('confidence', 0):.0%})"
                )

    if alarms:
        summary_lines.append(f"\n📋 告警明细 (最近 20 条):")
        for a in alarms[-20:]:
            summary_lines.append(
                f"  [{a.get('alarm_level', '?')}] {a.get('device_id', '?')} "
                f"{a.get('alarm_message', '?')[:60]}"
            )

    return {
        "shift_start": shift_start_dt.isoformat(),
        "shift_end": now.isoformat(),
        "summary": "\n".join(summary_lines),
        "stats": {
            "total_alarms": total_alarms,
            "total_diagnoses": total_diagnoses,
            "critical": critical,
            "pending_orders": pending_orders,
        },
    }


WEATHER_CACHE: dict = {}
WEATHER_CACHE_TIME = 0.0


def get_weather_context(location: str = "") -> str:
    global WEATHER_CACHE, WEATHER_CACHE_TIME
    import time as _time

    if WEATHER_CACHE and _time.time() - WEATHER_CACHE_TIME < 1800:
        return WEATHER_CACHE.get("context", "")

    ctx_parts = []
    try:
        import urllib.request, json
        url = "https://wttr.in/?format=j1"
        req = urllib.request.Request(url, headers={"User-Agent": "yuneng/1.0"})
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read())
        current = data.get("current_condition", [{}])[0]
        temp = current.get("temp_C", "N/A")
        humidity = current.get("humidity", "N/A")
        wind = current.get("windspeedKmph", "N/A")
        desc = current.get("weatherDesc", [{}])[0].get("value", "")

        ctx_parts.append(f"气象数据: 温度 {temp}°C, 湿度 {humidity}%, 风速 {wind}km/h, {desc}")

        if any(kw in desc for kw in ["雷暴", "thunder", "雷雨", "storm"]):
            ctx_parts.append("⚠️ 雷暴天气预警：需关注雷击导致的绝缘故障和线路跳闸")
        if temp and temp != "N/A" and int(temp) < 0:
            ctx_parts.append("⚠️ 低温预警：风机叶片可能覆冰，光伏组件效率下降")
        if temp and temp != "N/A" and int(temp) > 35:
            ctx_parts.append("⚠️ 高温预警：变压器/逆变器过温风险升高，散热系统需重点检查")
        if wind and wind != "N/A" and int(wind) > 50:
            ctx_parts.append("⚠️ 大风预警：风机可能触发超速保护，注意偏航系统状态")

        WEATHER_CACHE["context"] = "\n".join(ctx_parts)
        WEATHER_CACHE_TIME = _time.time()

    except Exception as e:
        logger.debug(f"气象数据获取失败: {e}")

    return WEATHER_CACHE.get("context", "")


DEFAULT_SAFETY_RULES: dict[str, list[str]] = {
    "逆变器": [
        "⚠️ 必须断开直流侧和交流侧开关，确认设备已停电",
        "⚠️ 必须经验电器验电，确认无电压后方可接近",
        "⚠️ 逆变器内部电容需等待 5 分钟放电完毕",
        "⚠️ 作业时必须一人操作一人监护",
    ],
    "变压器": [
        "⚠️ 必须断开高低压侧断路器并挂牌",
        "⚠️ 必须经验电器验电后挂设接地线",
        "⚠️ 进入变压器室必须检测 SF6/O2 浓度",
        "⚠️ 严禁单人操作，必须设专人监护",
    ],
    "风机": [
        "⚠️ 必须停机并锁定叶轮，禁止在叶片旋转时靠近",
        "⚠️ 攀爬塔筒必须系双钩安全带",
        "⚠️ 机舱内作业注意防雷，雷雨天气禁止登塔",
        "⚠️ 必须执行工作票制度，严禁无票作业",
    ],
    "光伏组件": [
        "⚠️ 光伏组串带电，严禁带电插拔 MC4 接头",
        "⚠️ 必须断开汇流箱开关后操作",
        "⚠️ 雨天禁止户外光伏组件检修",
        "⚠️ 高空作业必须系安全带",
    ],
    "储能电池": [
        "⚠️ 必须关闭电池管理系统 BMS 输出",
        "⚠️ 作业前检测可燃气体和氢气浓度",
        "⚠️ 严禁金属工具同时接触正负极",
        "⚠️ 必须佩戴绝缘手套和防护面罩",
    ],
    "开关柜": [
        "⚠️ 必须确认断路器在分闸位置并挂牌",
        "⚠️ 必须经验电器验电后合接地刀闸",
        "⚠️ SF6 气体泄漏时禁止进入开关柜室",
        "⚠️ 柜内作业必须先通风 15 分钟",
    ],
}


def get_safety_checklist(device_type: str, risk_level: str) -> list[str]:
    rules = DEFAULT_SAFETY_RULES.get(device_type, DEFAULT_SAFETY_RULES.get("变压器", []))
    if risk_level in ("CRITICAL", "HIGH"):
        rules = ["🚨 高风险作业：必须经值长批准后执行"] + rules
    return rules


def get_maintenance_window(device_type: str, risk_level: str) -> str:
    now = datetime.now()
    off_peak_start = now.replace(hour=2, minute=0)

    if off_peak_start < now:
        off_peak_start += timedelta(days=1)

    if risk_level == "CRITICAL":
        return "🚨 建议立即安排停电检修，不得延误"
    elif risk_level == "HIGH":
        return (
            f"建议在 {off_peak_start.strftime('%m月%d日')} 凌晨 2:00-5:00 "
            f"低谷时段安排停电检修，预计时长 2 小时"
        )
    else:
        return "建议结合下次计划检修一并处理，暂不影响运行"
