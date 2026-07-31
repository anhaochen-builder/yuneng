"""进度监控面板 API — /api/dashboard

提供实时项目状态、阶段完成度、文件统计等监控数据。
"""

import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter

from app.models.schemas import (
    DashboardResponse, DashboardProgress, DashboardPhase,
    DashboardFileStats,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

BASE_DIR = Path(__file__).parent.parent.parent

# —————————————— 任务定义 ——————————————

PHASES = {
    "phase1": {
        "name": "阶段一：核心引擎加固",
        "status": "completed",
        "tasks": [
            {"id": "1.1", "name": "LangGraph StateGraph 编排引擎", "status": "completed"},
            {"id": "1.2", "name": "Judge Agent 五维度评分", "status": "completed"},
            {"id": "1.3", "name": "BGE Reranker 精排集成", "status": "completed"},
            {"id": "1.4", "name": "文档解析(PDF/DOCX/EXCEL/MD)", "status": "completed"},
            {"id": "1.5", "name": "API 层完善(反馈/追踪/异常处理)", "status": "completed"},
        ],
    },
    "phase2": {
        "name": "阶段二：数据能力建设",
        "status": "completed",
        "tasks": [
            {"id": "2.1", "name": "Modbus TCP 适配器", "status": "completed"},
            {"id": "2.2", "name": "IEC 61850 适配器", "status": "completed"},
            {"id": "2.3", "name": "OPC UA 适配器", "status": "completed"},
            {"id": "2.4", "name": "协议适配器工厂", "status": "completed"},
            {"id": "2.5", "name": "数据标准化层", "status": "completed"},
            {"id": "2.6", "name": "环形缓冲区(30分钟滚动)", "status": "completed"},
            {"id": "2.7", "name": "故障窗口提取器(±5分钟)", "status": "completed"},
            {"id": "2.8", "name": "SCADA API + 告警自动诊断", "status": "completed"},
            {"id": "2.9", "name": "知识图谱 4→48 种设备", "status": "completed"},
            {"id": "2.10", "name": "知识库初始化工具", "status": "completed"},
            {"id": "2.11", "name": "长期记忆 ChromaDB 持久化", "status": "completed"},
        ],
    },
    "phase3": {
        "name": "阶段三：进阶智能",
        "status": "completed",
        "tasks": [
            {"id": "3.0", "name": "重构核心架构：Skill→子智能体(6个BaseSubAgent, 29内部节点)", "status": "completed"},
            {"id": "3.1", "name": "图像分析(Qwen-VL-Max, 4种模式)", "status": "completed"},
            {"id": "3.2", "name": "音频分析(AST, 6种故障声音模式)", "status": "completed"},
            {"id": "3.3", "name": "Cross-Attention 融合(MultiModalSubAgent)", "status": "completed"},
            {"id": "3.4", "name": "多模态 API 端点(普通+流式)", "status": "completed"},
            {"id": "3.5", "name": "成功案例自动入库(CaseIngestion)", "status": "completed"},
            {"id": "3.6", "name": "Skill 自动生成(≥3例触发)", "status": "completed"},
            {"id": "3.7", "name": "LoRA 微调数据集生成(Alpaca JSONL)", "status": "completed"},
            {"id": "3.8", "name": "Neo4j 知识图谱(GraphRAG, 降级NetworkX)", "status": "completed"},
        ],
    },
    "phase4": {
        "name": "阶段四：后端测试与交付",
        "status": "pending",
        "tasks": [
            {"id": "4.1", "name": "单元测试(Agent/Tool/Hook)", "status": "pending"},
            {"id": "4.2", "name": "集成测试(API/Graph/MCP)", "status": "pending"},
            {"id": "4.3", "name": "Docker Compose 生产配置", "status": "pending"},
            {"id": "4.4", "name": "部署文档", "status": "pending"},
        ],
    },
}


def _count_files(base: Path) -> int:
    if not base.exists():
        return 0
    return sum(1 for f in base.rglob("*.py") if f.is_file())


def _count_lines(base: Path) -> int:
    if not base.exists():
        return 0
    total = 0
    for f in base.rglob("*.py"):
        if f.is_file():
            try:
                total += len(f.read_text(encoding="utf-8").splitlines())
            except Exception:
                pass
    return total


def _count_api_endpoints(app_dir: Path) -> int:
    count = 0
    api_dir = app_dir / "app" / "api"
    if api_dir.exists():
        for f in api_dir.rglob("*.py"):
            if f.is_file() and f.name != "__init__.py":
                try:
                    content = f.read_text(encoding="utf-8")
                    for line in content.splitlines():
                        stripped = line.strip()
                        if stripped.startswith("@router.") and ("/" in stripped or stripped.startswith(".get") or stripped.startswith(".post")):
                            count += 1
                except Exception:
                    pass
    return count


@router.get("")
async def get_dashboard():
    app_dir = BASE_DIR / "app"
    scripts_dir = BASE_DIR / "scripts"

    # 统计文件
    app_files = _count_files(app_dir)
    script_files = _count_files(scripts_dir)
    total_files = app_files + script_files

    app_lines = _count_lines(app_dir)
    script_lines = _count_lines(scripts_dir)
    total_lines = app_lines + script_lines

    api_count = _count_api_endpoints(BASE_DIR)
    skill_count = _count_skills()

    # 统计阶段
    phases_output = []
    total_completed = 0
    total_tasks = 0

    for phase_id, phase_data in PHASES.items():
        completed = sum(1 for t in phase_data["tasks"] if t["status"] == "completed")
        in_progress = sum(1 for t in phase_data["tasks"] if t["status"] == "in_progress")
        total = len(phase_data["tasks"])
        pct = round(completed / total * 100, 1) if total > 0 else 0

        phases_output.append(DashboardPhase(
            name=phase_data["name"],
            status=phase_data["status"],
            tasks=phase_data["tasks"],
            completed_count=completed,
            total_count=total,
            pct=pct,
        ))
        total_completed += completed
        total_tasks += total

    pending = total_tasks - total_completed
    in_progress_count = sum(1 for p in PHASES.values() for t in p["tasks"] if t["status"] == "in_progress")
    overall_pct = round(total_completed / total_tasks * 100, 1) if total_tasks > 0 else 0

    progress = DashboardProgress(
        total_tasks=total_tasks,
        completed=total_completed,
        in_progress=in_progress_count,
        pending=pending,
        overall_pct=overall_pct,
    )

    file_stats = DashboardFileStats(
        total_files=total_files,
        total_lines=total_lines,
        api_endpoints=api_count,
        agent_count=6,
        skill_count=skill_count,
    )

    # 数据统计
    data_stats = {"knowledge_items": 0, "cases": 0, "checkpoints": False}
    try:
        from app.rag.vector_store import get_chroma_client
        client = get_chroma_client()
        collections = client.list_collections()
        data_stats["vector_collections"] = len(collections)
        data_stats["knowledge_items"] = sum(c.count() for c in collections)
    except Exception:
        data_stats["vector_collections"] = 0

    try:
        from app.memory.memory_service import MemoryService
        mem = MemoryService()
        lt = mem.long_term_stats()
        data_stats["cases"] = lt.get("total", 0)
    except Exception:
        pass

    checkpoints_db = BASE_DIR / "data" / "checkpoints.db"
    data_stats["checkpoints"] = checkpoints_db.exists()

    return DashboardResponse(
        update_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        progress=progress,
        phases=phases_output,
        file_stats=file_stats,
        current_activity="阶段三已完成(9项) → 准备进入阶段四(测试+部署)",
        data_stats=data_stats,
        recent_actions=[
            "✅ 阶段三完成：图像分析 + 音频分析 + 多模态融合 + API",
            "✅ 学习模块：成功案例自动入库 + Skill 自动生成",
            "✅ LoRA 微调数据集生成脚本",
            "✅ GraphRAG Neo4j/NetworkX 知识图谱引擎",
            "✅ 核心架构重构：6个 BaseSubAgent 全部编译通过",
            "✅ Diagnosis(9节点) + SCADA(5节点) + MultiModal(4节点)",
            "✅ KnowledgeQA(6节点) + Report(3节点) + Chat(2节点)",
            "创建进度监控 Dashboard API",
        ],
    )


@router.get("/phases")
async def get_phases():
    return {"phases": {pid: {"name": p["name"], "status": p["status"], "task_count": len(p["tasks"])} for pid, p in PHASES.items()}}


@router.get("/phases/{phase_id}")
async def get_phase_detail(phase_id: str):
    if phase_id not in PHASES:
        return {"error": "阶段不存在", "valid_phases": list(PHASES.keys())}
    return PHASES[phase_id]


@router.get("/tasks")
async def get_tasks(status: str = ""):
    all_tasks = []
    for pid, pdata in PHASES.items():
        for t in pdata["tasks"]:
            t["phase_id"] = pid
            t["phase_name"] = pdata["name"]
            if not status or t["status"] == status:
                all_tasks.append(t)
    return {"tasks": all_tasks, "count": len(all_tasks)}


@router.get("/mode")
async def get_mode():
    try:
        from app.agent.multi_model import multi_client
        return {
            "diagnosis_mode": settings.diagnosis_mode,
            **multi_client.mode_status,
        }
    except Exception:
        return {
            "diagnosis_mode": settings.diagnosis_mode,
            "current": "unknown",
            "available": {},
        }


def _count_skills() -> int:
    try:
        from app.skill.registry import skill_registry
        return len(skill_registry.list_all())
    except Exception:
        return 0
