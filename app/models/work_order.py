"""工单数据模型"""
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class WorkOrderStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class WorkOrderLevel(str, Enum):
    EMERGENCY = "emergency"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


STATUS_TRANSITIONS: dict[WorkOrderStatus, list[WorkOrderStatus]] = {
    WorkOrderStatus.PENDING: [WorkOrderStatus.ASSIGNED, WorkOrderStatus.CANCELLED],
    WorkOrderStatus.ASSIGNED: [WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.CANCELLED],
    WorkOrderStatus.IN_PROGRESS: [WorkOrderStatus.PENDING_REVIEW, WorkOrderStatus.ASSIGNED],
    WorkOrderStatus.PENDING_REVIEW: [WorkOrderStatus.CLOSED, WorkOrderStatus.IN_PROGRESS],
    WorkOrderStatus.CLOSED: [],
    WorkOrderStatus.CANCELLED: [],
}

LEVEL_PRIORITY: dict[WorkOrderLevel, int] = {
    WorkOrderLevel.EMERGENCY: 0,
    WorkOrderLevel.HIGH: 1,
    WorkOrderLevel.MEDIUM: 2,
    WorkOrderLevel.LOW: 3,
}


class WorkOrder(BaseModel):
    order_id: str = Field(description="工单编号")
    task_id: str = Field(description="关联诊断任务ID")
    device_id: str = Field(description="设备编号")
    device_name: str = Field("", description="设备名称")
    title: str = Field(description="工单标题")
    description: str = Field(description="故障描述")
    root_cause: str = Field("", description="根因")
    investigation_steps: list[str] = Field(default_factory=list, description="排查步骤")
    recommendations: list[str] = Field(default_factory=list, description="处理建议")
    safety_notes: list[str] = Field(default_factory=list, description="安全提示")
    level: WorkOrderLevel = Field(description="紧急程度")
    status: WorkOrderStatus = Field(WorkOrderStatus.PENDING, description="工单状态")
    assignee: str = Field("", description="责任人")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="创建时间")
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="更新时间")
    closed_at: Optional[str] = Field(None, description="关闭时间")
    maintenance_notes: str = Field("", description="维修备注")
    maintenance_images: list[str] = Field(default_factory=list, description="维修照片URL")


class WorkOrderCreate(BaseModel):
    task_id: str = Field(..., description="诊断任务ID")
    device_id: str = Field(..., description="设备编号")
    device_name: str = Field("")
    title: str = Field(..., description="工单标题")
    description: str = Field(..., description="故障描述")
    root_cause: str = Field("")
    investigation_steps: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    safety_notes: list[str] = Field(default_factory=list)
    level: WorkOrderLevel = Field(WorkOrderLevel.MEDIUM)
    assignee: str = Field("")


class WorkOrderUpdate(BaseModel):
    status: Optional[WorkOrderStatus] = Field(None, description="新状态")
    assignee: Optional[str] = Field(None, description="责任人")
    maintenance_notes: Optional[str] = Field(None, description="维修备注")
    maintenance_images: Optional[list[str]] = Field(None, description="维修照片URL")


class WorkOrderStats(BaseModel):
    total: int = 0
    pending: int = 0
    in_progress: int = 0
    closed: int = 0
    emergency_count: int = 0
    avg_resolution_hours: float = 0.0
