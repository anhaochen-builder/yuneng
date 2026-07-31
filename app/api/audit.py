"""项目质量审计 API — /api/audit

逐项检查三阶段所有交付物：文件存在性、导入健康、架构合规、代码问题、质量评分
"""

import ast
import importlib
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from app.models.schemas import DashboardPhase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/audit", tags=["audit"])

BASE_DIR = Path(__file__).parent.parent.parent
APP_DIR = BASE_DIR / "app"

# ─── 三阶段全部交付物清单 ───

DELIVERABLES = {
    "phase1": {
        "name": "阶段一：核心引擎加固",
        "items": [
            {"file": "app/graph/state.py", "desc": "AgentState TypedDict"},
            {"file": "app/graph/builder.py", "desc": "LangGraph StateGraph + 条件路由 + Checkpointer"},
            {"file": "app/graph/subgraphs/runners.py", "desc": "3 子图 async 运行器"},
            {"file": "app/agent/judge_agent.py", "desc": "Judge Agent 五维度评分"},
            {"file": "app/rag/rerank.py", "desc": "BGE CrossEncoder Reranker"},
            {"file": "app/rag/document_parser.py", "desc": "文档解析(PDF/DOCX/EXCEL/MD)"},
            {"file": "app/api/feedback.py", "desc": "三态评价反馈"},
            {"file": "app/api/trace.py", "desc": "诊断回放 API"},
            {"file": "app/main.py", "desc": "统一异常处理 + SSE 推送"},
        ],
    },
    "phase2": {
        "name": "阶段二：数据能力建设",
        "items": [
            {"file": "app/scada/protocols/modbus_adapter.py", "desc": "Modbus TCP 适配器"},
            {"file": "app/scada/protocols/iec61850_adapter.py", "desc": "IEC 61850 适配器"},
            {"file": "app/scada/protocols/opcua_adapter.py", "desc": "OPC UA 适配器"},
            {"file": "app/scada/protocol_factory.py", "desc": "协议适配器工厂"},
            {"file": "app/scada/data_normalizer.py", "desc": "数据标准化层"},
            {"file": "app/scada/ring_buffer.py", "desc": "环形缓冲区"},
            {"file": "app/scada/window_extractor.py", "desc": "故障窗口提取器"},
            {"file": "app/api/scada.py", "desc": "SCADA API"},
            {"file": "app/rag/knowledge_graph.py", "desc": "知识图谱 48 种设备"},
            {"file": "scripts/init_knowledge.py", "desc": "知识库初始化工具"},
            {"file": "app/memory/memory_service.py", "desc": "长期记忆 ChromaDB"},
        ],
    },
    "phase3": {
        "name": "阶段三：进阶智能",
        "items": [
            {"file": "app/graph/sub_agent.py", "desc": "子智能体基类 BaseSubAgent"},
            {"file": "app/graph/sub_agent_init.py", "desc": "6 Skill → 6 SubAgent 注册"},
            {"file": "app/graph/subgraphs/diagnosis.py", "desc": "DiagnosisSubAgent (9节点)"},
            {"file": "app/graph/subgraphs/scada.py", "desc": "SCADASubAgent (5节点) **新建**"},
            {"file": "app/graph/subgraphs/multimodal.py", "desc": "MultiModalSubAgent (4节点) **新建**"},
            {"file": "app/graph/subgraphs/report.py", "desc": "ReportSubAgent (3节点) **新建**"},
            {"file": "app/graph/subgraphs/knowledge_qa.py", "desc": "KnowledgeQASubAgent (6节点)"},
            {"file": "app/graph/subgraphs/chat.py", "desc": "ChatSubAgent (2节点)"},
            {"file": "app/multimodal/image_analyzer.py", "desc": "Qwen-VL-Max 图像分析"},
            {"file": "app/multimodal/audio_analyzer.py", "desc": "AST 音频分析"},
            {"file": "app/api/diagnosis.py", "desc": "多模态诊断 API"},
            {"file": "app/learning/case_ingestion.py", "desc": "成功案例自动入库"},
            {"file": "app/learning/skill_generator.py", "desc": "Skill 自动生成"},
            {"file": "scripts/lora_finetune.py", "desc": "LoRA 微调数据集生成"},
            {"file": "app/rag/graphrag.py", "desc": "Neo4j/NetworkX 知识图谱"},
            {"file": "app/api/dashboard.py", "desc": "进度监控 Dashboard"},
        ],
    },
}

# ─── 辅助函数 ───

def _file_exists(relative_path: str) -> bool:
    return (BASE_DIR / relative_path).is_file()


def _count_lines(relative_path: str) -> int:
    path = BASE_DIR / relative_path
    if not path.is_file():
        return 0
    try:
        return len(path.read_text(encoding="utf-8").splitlines())
    except Exception:
        return 0


def _count_functions(relative_path: str) -> int:
    path = BASE_DIR / relative_path
    if not path.is_file():
        return 0
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        return sum(1 for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)))
    except Exception:
        return 0


def _count_classes(relative_path: str) -> int:
    path = BASE_DIR / relative_path
    if not path.is_file():
        return 0
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        return sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
    except Exception:
        return 0


def _check_import(module_path: str) -> dict:
    try:
        importlib.import_module(module_path)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "fail", "error": str(e)[:200]}


def _scan_dead_files() -> list[dict]:
    dead = []
    for py_file in APP_DIR.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue
        rel = str(py_file.relative_to(BASE_DIR))
        module_stem = rel.replace("/", ".").replace(".py", "")
        short = py_file.stem

        refs = []
        for other in APP_DIR.rglob("*.py"):
            if other == py_file:
                continue
            try:
                content = other.read_text(encoding="utf-8")
                if short in content or module_stem in content:
                    refs.append(str(other.relative_to(BASE_DIR)))
            except Exception:
                pass

        scripts_refs = []
        for sf in (BASE_DIR / "scripts").rglob("*.py"):
            try:
                if short in sf.read_text(encoding="utf-8") or module_stem in sf.read_text(encoding="utf-8"):
                    scripts_refs.append(str(sf.relative_to(BASE_DIR)))
            except Exception:
                pass

        all_refs = refs + scripts_refs
        if not all_refs and py_file.stat().st_size > 0:
            dead.append({
                "file": rel,
                "issue": f"无外部引用(仅自身定义)，可能是死代码",
                "severity": "warning",
            })
    return dead

def _module_short_name(module_name: str) -> str:

    return module_name.replace("/", ".").replace(".py", "")


# ─── 核心审计端点 ───

@router.get("")
async def audit_full():
    now = datetime.now().isoformat()

    phases = []
    total_exists = 0
    total_items = 0
    total_lines = 0
    all_issues = []

    for phase_id, phase_data in DELIVERABLES.items():
        items = []
        phase_exists = 0
        phase_total = len(phase_data["items"])

        for item in phase_data["items"]:
            fp = item["file"]
            exists = _file_exists(fp)
            lines = _count_lines(fp)
            funcs = _count_functions(fp)
            classes = _count_classes(fp)

            quality = "good"
            notes = []
            if not exists:
                quality = "missing"
                notes.append("文件不存在")
            elif lines < 10:
                quality = "stub"
                notes.append(f"文件过小({lines}行)，可能只有占位代码")

            if exists:
                phase_exists += 1
                total_lines += lines

            items.append({
                "file": fp,
                "desc": item["desc"],
                "exists": exists,
                "lines": lines,
                "functions": funcs,
                "classes": classes,
                "quality": quality,
                "notes": notes,
            })

        total_exists += phase_exists
        total_items += phase_total

        phases.append({
            "phase_id": phase_id,
            "name": phase_data["name"],
            "exists": phase_exists,
            "total": phase_total,
            "pct": round(phase_exists / phase_total * 100, 1) if phase_total else 0,
            "items": items,
        })

    # ─── 架构检查 ───

    skill_agent_check = _check_skill_agent_mapping()
    dead_files = _scan_dead_files()
    import_checks = _check_imports_health()

    if dead_files:
        all_issues.extend([d["issue"] for d in dead_files])

    if not skill_agent_check["all_mapped"]:
        all_issues.append(f"Skill→SubAgent 映射不完整: {skill_agent_check['unmapped_skills']}")

    for ic in import_checks:
        if ic["status"] == "fail":
            all_issues.append(f"导入失败: {ic['module']} — {ic['error'][:100]}")

    overall_pct = round(total_exists / total_items * 100, 1) if total_items else 0
    grade = "A" if overall_pct >= 95 else ("B" if overall_pct >= 85 else ("C" if overall_pct >= 70 else "D"))

    return {
        "audit_time": now,
        "project": "驭能 — 新能源场站非计划停机智能诊断系统",
        "overall": {
            "phase_count": 3,
            "total_files_checked": total_items,
            "files_exist": total_exists,
            "completion_pct": overall_pct,
            "total_lines": total_lines,
            "grade": grade,
            "issues": all_issues if all_issues else ["无重大问题"],
        },
        "phases": phases,
        "architecture": {
            "skill_agent_mapping": skill_agent_check,
        },
        "code_quality": {
            "dead_files": dead_files,
            "import_health": import_checks,
        },
    }


@router.get("/skills")
async def audit_skills():
    return _check_skill_agent_mapping()


@router.get("/files")
async def audit_files():
    dead = _scan_dead_files()
    imports = _check_imports_health()

    empty_init = []
    for init_f in APP_DIR.rglob("__init__.py"):
        try:
            if init_f.stat().st_size == 0:
                empty_init.append(str(init_f.relative_to(BASE_DIR)))
        except Exception:
            pass

    return {
        "dead_files": dead,
        "empty_init_files": empty_init,
        "import_health": imports,
    }


@router.get("/imports")
async def audit_imports():
    return {
        "checks": _check_imports_health(),
        "summary": f"{sum(1 for c in _check_imports_health() if c['status'] == 'ok')}/{len(_check_imports_health())} 模块导入正常",
    }


# ─── 检查辅助 ───

def _check_skill_agent_mapping() -> dict[str, Any]:
    try:
        from app.graph.sub_agent_init import register_all
        register_all()

        from app.skill.registry import skill_registry
        from app.graph.sub_agent import sub_agent_registry

        skills = skill_registry.list_all()
        mapped = []
        unmapped = []

        for s in skills:
            skill_id = s["skill_id"]
            agent_id = s["agent_id"]
            agent = sub_agent_registry.get(agent_id)

            if agent:
                compiled = agent.build()
                mapped.append({
                    "skill_id": skill_id,
                    "skill_name": s["name"],
                    "agent_id": agent_id,
                    "agent_name": agent.meta.name,
                    "category": agent.meta.category,
                    "internal_nodes": len(compiled.nodes),
                    "node_names": [n for n in compiled.nodes.keys() if n != "__start__"],
                    "triggers": agent.meta.intent_triggers,
                })
            else:
                unmapped.append({"skill_id": skill_id, "agent_id": agent_id})

        return {
            "total_skills": len(skills),
            "total_agents": len(sub_agent_registry),
            "all_mapped": len(unmapped) == 0,
            "mapped": mapped,
            "unmapped_skills": unmapped,
            "architecture_note": "每个 Skill 都关联了一个独立编译的 LangGraph 子智能体(CompiledGraph)，不再是 Prompt 字符串模板",
        }
    except Exception as e:
        return {"error": str(e), "all_mapped": False, "mapped": [], "unmapped_skills": []}


def _check_imports_health() -> list[dict]:
    modules = [
        "app.graph.sub_agent",
        "app.graph.sub_agent_init",
        "app.graph.builder",
        "app.graph.subgraphs.diagnosis",
        "app.graph.subgraphs.scada",
        "app.graph.subgraphs.multimodal",
        "app.graph.subgraphs.report",
        "app.graph.subgraphs.knowledge_qa",
        "app.graph.subgraphs.chat",
        "app.graph.subgraphs.runners",
        "app.multimodal.image_analyzer",
        "app.multimodal.audio_analyzer",
        "app.learning.case_ingestion",
        "app.learning.skill_generator",
        "app.rag.graphrag",
        "app.rag.hybrid_search",
        "app.rag.knowledge_graph",
        "app.rag.rerank",
        "app.rag.vector_store",
        "app.rag.document_parser",
        "app.scada.protocol_factory",
        "app.scada.ring_buffer",
        "app.scada.window_extractor",
        "app.memory.memory_service",
        "app.agent.judge_agent",
        "app.agent.diagnosis_agent",
        "app.agent.risk_review_agent",
        "app.api.diagnosis",
        "app.api.dashboard",
        "app.api.feedback",
        "app.api.trace",
        "app.api.scada",
        "app.api.alarm",
        "app.api.chat",
        "app.api.knowledge",
    ]
    results = []
    for mod in modules:
        results.append({
            "module": mod,
            **_check_import(mod),
        })
    return results
