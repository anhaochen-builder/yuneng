"""定时任务 + 设备发现 + 通知配置 API"""
import logging
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/automation", tags=["automation"])


class NotifyConfig(BaseModel):
    enabled: bool = False
    schedule: str = "daily"
    schedule_time: str = "08:00"
    dingtalk_webhook: str = ""
    wecom_webhook: str = ""
    email_smtp_host: str = ""
    email_smtp_port: int = 465
    email_user: str = ""
    email_password: str = ""
    email_receivers: list[str] = Field(default_factory=list)


@router.get("/discovery")
async def run_discovery(scan_network: bool = False):
    from app.scada.auto_discovery import run_discovery as do_discovery
    return await do_discovery(scan_network=scan_network)


@router.post("/discovery/auto-connect")
async def auto_connect_discovered():
    from app.scada.auto_discovery import discover_local_devices
    devices = await discover_local_devices()
    connected = 0
    for dev in devices:
        try:
            from app.scada.protocol_factory import ProtocolFactory
            from app.scada.base import DeviceConfig
            config = DeviceConfig(dev["device_id"], dev.get("device_type", "inverter"), dev["protocol"])
            ProtocolFactory.create(config)
            connected += 1
        except Exception as e:
            logger.warning(f"自动连接失败 {dev['device_id']}: {e}")
    return {"discovered": len(devices), "connected": connected}


@router.get("/notify/config")
async def get_notify_config():
    from app.services.scheduler import load_config
    return load_config()


@router.post("/notify/config")
async def update_notify_config(req: NotifyConfig):
    from app.services.scheduler import save_config
    cfg = req.model_dump()
    save_config(cfg)
    return {"status": "saved"}


@router.post("/notify/test")
async def test_notify(req: NotifyConfig, background: BackgroundTasks):
    from app.services.scheduler import send_dingtalk_message, send_wecom_message

    results = {}
    if req.dingtalk_webhook:
        ok = await send_dingtalk_message(req.dingtalk_webhook, "驭能通知测试", "这是一条来自驭能智能诊断平台的测试消息")
        results["dingtalk"] = "sent" if ok else "failed"
    if req.wecom_webhook:
        ok = await send_wecom_message(req.wecom_webhook, "驭能通知测试", "这是一条来自驭能智能诊断平台的测试消息")
        results["wecom"] = "sent" if ok else "failed"

    return {"results": results}


@router.post("/notify/run-now")
async def run_report_now(background: BackgroundTasks):
    background.add_task(_run_report)
    return {"status": "started"}


async def _run_report():
    from app.services.scheduler import send_daily_report
    await send_daily_report()
