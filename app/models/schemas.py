"""数据模型定义 — 请求/响应 Schema"""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class DiagnosisRequest(BaseModel):
    """诊断请求"""
    symptoms: str = Field(..., description="故障现象描述")
    device_id: Optional[str] = Field(None, description="设备编号")
    session_id: Optional[str] = Field(None, description="会话ID")
    user_id: Optional[str] = Field("operator", description="用户ID")
    stream: bool = Field(False, description="是否流式输出")


class RootCause(BaseModel):
    """故障根因"""
    cause: str = Field(..., description="故障原因描述")
    probability: float = Field(..., description="概率 0-1")
    evidence: list[str] = Field(default_factory=list, description="支撑证据")
    confidence_level: str = Field("medium", description="置信度: high/medium/low")


class DiagnosisResult(BaseModel):
    """诊断结果"""
    root_causes: list[RootCause] = Field(default_factory=list)
    analysis: str = Field("", description="详细分析过程")
    recommendations: list[str] = Field(default_factory=list)
    confidence: float = Field(0.0)


class ActionStep(BaseModel):
    """处置步骤"""
    order: int
    action: str
    detail: str = ""
    safety_note: str = ""


class ActionPlan(BaseModel):
    """处置方案"""
    priority: str = Field("medium", description="优先级")
    steps: list[ActionStep] = Field(default_factory=list)
    tools_required: list[str] = Field(default_factory=list)
    estimated_time: str = ""
    safety_notes: list[str] = Field(default_factory=list)


class SafetyCheck(BaseModel):
    """安全审查结果"""
    is_compliant: bool = True
    violations: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    risk_level: str = Field("low", description="high/medium/low")


class DiagnosisResponse(BaseModel):
    """诊断响应"""
    task_id: str
    diagnosis: Optional[DiagnosisResult] = None
    action_plan: Optional[ActionPlan] = None
    safety_check: Optional[SafetyCheck] = None
    confidence: float = 0.0
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ChatRequest(BaseModel):
    """对话请求"""
    question: str
    session_id: Optional[str] = None
    user_id: Optional[str] = "operator"


class AlarmRequest(BaseModel):
    """告警请求"""
    alarm_id: str
    station: str = ""
    device_id: str
    device_name: str = ""
    device_type: str = ""
    alarm_type: str = ""
    alarm_level: str = ""
    current_value: str = ""
    threshold: str = ""
    duration: str = ""


class KnowledgeUploadResult(BaseModel):
    """知识库上传结果"""
    document_id: str
    filename: str
    chunk_count: int
    status: str


class MultimodalRequest(BaseModel):
    """多模态诊断请求"""
    symptoms: str = Field(..., description="故障现象描述")
    device_id: Optional[str] = Field(None, description="设备编号")
    session_id: Optional[str] = Field(None, description="会话ID")
    user_id: Optional[str] = Field("operator", description="用户ID")
    images: list[str] = Field(default_factory=list, description="Base64 编码的图像列表")
    audio_path: Optional[str] = Field(None, description="音频文件路径")
    stream: bool = Field(False, description="是否流式输出")


class DashboardProgress(BaseModel):
    """项目进度"""
    total_tasks: int = 0
    completed: int = 0
    in_progress: int = 0
    pending: int = 0
    overall_pct: float = 0.0


class DashboardPhase(BaseModel):
    """阶段进度"""
    name: str
    status: str
    tasks: list[dict] = Field(default_factory=list)
    completed_count: int = 0
    total_count: int = 0
    pct: float = 0.0


class DashboardFileStats(BaseModel):
    """文件统计"""
    total_files: int = 0
    total_lines: int = 0
    api_endpoints: int = 0
    agent_count: int = 0
    skill_count: int = 0


class DashboardResponse(BaseModel):
    """进度监控面板响应"""
    project: str = "驭能 - 新能源场站非计划停机智能诊断系统"
    update_time: str
    progress: DashboardProgress
    phases: list[DashboardPhase]
    file_stats: DashboardFileStats
    current_activity: str = ""
    data_stats: dict = Field(default_factory=dict)
    recent_actions: list[str] = Field(default_factory=list)


class GraphState(dict):
    """LangGraph 状态，包装为可序列化字典"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
