"""定时自动诊断 + 企业微信/钉钉通知推送"""
import json
import asyncio
import logging
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

NOTIFY_CONFIG_FILE = Path(__file__).parent.parent.parent / "data" / "notify_config.json"

DEFAULT_CONFIG = {
    "enabled": False,
    "schedule": "daily",
    "schedule_time": "08:00",
    "dingtalk_webhook": "",
    "wecom_webhook": "",
    "email_smtp_host": "",
    "email_smtp_port": 465,
    "email_user": "",
    "email_password": "",
    "email_receivers": [],
    "last_run": None,
}


def load_config() -> dict:
    if NOTIFY_CONFIG_FILE.exists():
        try:
            return json.loads(NOTIFY_CONFIG_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(cfg: dict):
    NOTIFY_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    NOTIFY_CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


async def run_daily_diagnosis() -> dict:
    from app.api.diagnosis import DiagnosisRequest
    from app.skill.registry import skill_registry
    from app.graph.builder import get_graph
    from app.graph.state_keys import StateKeys as K
    import uuid

    devices = ["WT001", "INV001", "TRA001", "PV001", "SWG001", "BAT001"]
    results = []

    for device_id in devices:
        try:
            task_id = f"DAILY-{uuid.uuid4().hex[:12]}"
            skill = skill_registry.select_by_intent("DIAGNOSIS")
            state = {
                K.INPUT: f"设备 {device_id} 日常健康检查，请综合评估运行状态",
                K.TASK_ID: task_id,
                K.DEVICE_ID: device_id,
                K.INTENT: "FAULT_DIAGNOSIS",
                K.SKILL_CONTEXT: skill.prompt_template if skill else "",
                K.LOOP_COUNT: 0,
                "max_retries": 0,
            }
            graph = get_graph()
            result = await graph.ainvoke(state, {"configurable": {"thread_id": task_id}})
            diag = result.get(K.DIAGNOSIS_RESULT, {})
            confidence = diag.get("confidence", 0) if isinstance(diag, dict) else 0
            results.append({
                "device_id": device_id,
                "confidence": confidence,
                "risk_level": diag.get("risk_level", "UNKNOWN") if isinstance(diag, dict) else "UNKNOWN",
                "status": "completed",
            })
        except Exception as e:
            results.append({"device_id": device_id, "status": "failed", "error": str(e)[:100]})

    return {"total": len(results), "results": results, "timestamp": datetime.now().isoformat()}


async def send_dingtalk_message(webhook: str, title: str, text: str) -> bool:
    try:
        payload = json.dumps({
            "msgtype": "markdown",
            "markdown": {"title": title, "text": text},
        }).encode()
        req = urllib.request.Request(webhook, data=payload, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception as e:
        logger.warning(f"钉钉通知发送失败: {e}")
        return False


async def send_wecom_message(webhook: str, title: str, text: str) -> bool:
    try:
        payload = json.dumps({
            "msgtype": "markdown",
            "markdown": {"content": f"## {title}\n{text}"},
        }).encode()
        req = urllib.request.Request(webhook, data=payload, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception as e:
        logger.warning(f"企业微信通知发送失败: {e}")
        return False


async def send_daily_report():
    cfg = load_config()
    if not cfg.get("enabled"):
        return {"status": "disabled"}

    logger.info("开始定时自动诊断...")
    result = await run_daily_diagnosis()

    abnormal = [r for r in result["results"] if r.get("risk_level") in ("CRITICAL", "HIGH")]
    report_lines = [
        f"> 诊断时间: {result['timestamp'][:16]}",
        f"> 巡检设备: {result['total']} 台",
        f"> 异常设备: {len(abnormal)} 台",
    ]
    if abnormal:
        report_lines.append("> ")
        report_lines.append("> ⚠️ 异常设备:")
        for a in abnormal:
            report_lines.append(f"> - {a['device_id']}: {a.get('risk_level', '?')} (置信度 {a.get('confidence',0):.0%})")

    report_text = "\n".join(report_lines)

    if cfg.get("dingtalk_webhook"):
        await send_dingtalk_message(cfg["dingtalk_webhook"], "驭能每日诊断报告", report_text)
    if cfg.get("wecom_webhook"):
        await send_wecom_message(cfg["wecom_webhook"], "驭能每日诊断报告", report_text)

    cfg["last_run"] = datetime.now().isoformat()
    save_config(cfg)

    return {"status": "sent", "abnormal_count": len(abnormal), "report": report_text}
