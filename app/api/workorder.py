"""智能工单 API — /api/workorder"""
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.models.work_order import (
    WorkOrder, WorkOrderCreate, WorkOrderUpdate, WorkOrderStats,
    WorkOrderStatus, WorkOrderLevel, STATUS_TRANSITIONS, LEVEL_PRIORITY,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/workorder", tags=["workorder"])

DATA_FILE = Path(__file__).parent.parent.parent / "data" / "work_orders.json"


def _load() -> dict[str, dict]:
    if not DATA_FILE.exists():
        return {}
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: dict[str, dict]):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@router.get("")
async def list_orders(
    status: str = Query("", description="按状态筛选"),
    level: str = Query("", description="按级别筛选"),
    device_id: str = Query("", description="按设备筛选"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    data = _load()
    orders = list(data.values())

    if status:
        orders = [o for o in orders if o.get("status") == status]
    if level:
        orders = [o for o in orders if o.get("level") == level]
    if device_id:
        orders = [o for o in orders if o.get("device_id") == device_id]

    orders.sort(key=lambda o: (LEVEL_PRIORITY.get(o.get("level", "low"), 99),
                                o.get("created_at", "")), reverse=False)
    total = len(orders)
    return {
        "orders": orders[offset:offset + limit],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/stats")
async def order_stats():
    data = _load()
    orders = list(data.values())
    now = datetime.now()

    total = len(orders)
    pending = sum(1 for o in orders if o.get("status") == "pending")
    in_progress = sum(1 for o in orders if o.get("status") in ("assigned", "in_progress"))
    closed = sum(1 for o in orders if o.get("status") == "closed")
    emergency = sum(1 for o in orders if o.get("level") == "emergency")

    resolution_times = []
    for o in orders:
        if o.get("status") == "closed" and o.get("created_at"):
            try:
                created = datetime.fromisoformat(o["created_at"])
                closed_at = datetime.fromisoformat(o.get("closed_at", o.get("updated_at", o["created_at"])))
                resolution_times.append((closed_at - created).total_seconds() / 3600)
            except (ValueError, TypeError):
                pass

    avg_hours = round(sum(resolution_times) / len(resolution_times), 1) if resolution_times else 0.0

    return WorkOrderStats(
        total=total, pending=pending, in_progress=in_progress, closed=closed,
        emergency_count=emergency, avg_resolution_hours=avg_hours,
    ).model_dump()


@router.get("/{order_id}")
async def get_order(order_id: str):
    data = _load()
    if order_id not in data:
        raise HTTPException(404, "工单不存在")
    return data[order_id]


@router.post("", status_code=201)
async def create_order(req: WorkOrderCreate):
    data = _load()
    order_id = f"WO-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

    order = WorkOrder(
        order_id=order_id,
        task_id=req.task_id,
        device_id=req.device_id,
        device_name=req.device_name,
        title=req.title,
        description=req.description,
        root_cause=req.root_cause,
        investigation_steps=req.investigation_steps,
        recommendations=req.recommendations,
        safety_notes=req.safety_notes,
        level=req.level,
        status=WorkOrderStatus.PENDING,
        assignee=req.assignee,
    )
    data[order_id] = order.model_dump()
    _save(data)
    logger.info(f"工单已创建: {order_id} [{req.level.value}] {req.title[:40]}")
    return data[order_id]


@router.patch("/{order_id}")
async def update_order(order_id: str, req: WorkOrderUpdate):
    data = _load()
    if order_id not in data:
        raise HTTPException(404, "工单不存在")

    order = data[order_id]
    if req.status is not None:
        current = WorkOrderStatus(order["status"])
        if req.status not in STATUS_TRANSITIONS[current]:
            raise HTTPException(400, f"状态不能从 {current.value} 变更为 {req.status.value}")

        order["status"] = req.status.value
        if req.status == WorkOrderStatus.CLOSED:
            order["closed_at"] = datetime.now().isoformat()

    if req.assignee is not None:
        order["assignee"] = req.assignee
    if req.maintenance_notes is not None:
        order["maintenance_notes"] = req.maintenance_notes
    if req.maintenance_images is not None:
        order["maintenance_images"] = req.maintenance_images

    order["updated_at"] = datetime.now().isoformat()
    _save(data)
    logger.info(f"工单已更新: {order_id} → {order['status']}")
    return order


@router.delete("/{order_id}")
async def delete_order(order_id: str):
    data = _load()
    if order_id not in data:
        raise HTTPException(404, "工单不存在")
    del data[order_id]
    _save(data)
    return {"deleted": order_id}


def auto_create_work_order(
    task_id: str, device_id: str, device_name: str,
    report: str, root_cause: str, risk_level: str,
    steps: list[str] | None = None,
    recs: list[str] | None = None,
    safety: list[str] | None = None,
) -> str | None:
    """诊断结果触发自动创建工单，仅 CRITICAL/HIGH 自动触发"""
    risk_upper = risk_level.upper() if risk_level else "MEDIUM"
    if risk_upper not in ("CRITICAL", "HIGH"):
        return None

    level_map = {"CRITICAL": WorkOrderLevel.EMERGENCY, "HIGH": WorkOrderLevel.HIGH}
    level = level_map.get(risk_upper, WorkOrderLevel.HIGH)

    data = _load()
    order_id = f"WO-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

    order = WorkOrder(
        order_id=order_id,
        task_id=task_id,
        device_id=device_id,
        device_name=device_name,
        title=f"[自动] {device_name or device_id} {risk_upper}风险诊断工单",
        description=report[:2000] if report else "",
        root_cause=root_cause,
        investigation_steps=steps or [],
        recommendations=recs or [],
        safety_notes=safety or [],
        level=level,
        status=WorkOrderStatus.PENDING,
    )
    data[order_id] = order.model_dump()
    _save(data)
    logger.info(f"自动创建工单: {order_id} [{level.value}] {device_id}")
    return order_id
