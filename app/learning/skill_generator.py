"""Skill 自动生成引擎

触发条件：同一故障模式在长期记忆中累积出现 ≥ 3 次
执行动作：
  1. LLM 分析 3 个相似案例的共性特征
  2. 提炼为标准化 Skill（Prompt 模板 + 诊断流程 + 关键检查点）
  3. 注册到 SkillRegistry
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from app.agent.llm_client import llm

logger = logging.getLogger(__name__)

SKILL_TEMPLATE = {
    "skill_id": "",
    "name": "",
    "category": "diagnosis",
    "intent_triggers": ["DIAGNOSIS", "FAULT_DIAGNOSIS"],
    "prompt_template": "",
    "tools": [],
    "generated_from_cases": [],
    "created_at": "",
    "usage_count": 0,
}

SKILL_GENERATION_PROMPT = """你是新能源场站故障诊断专家。根据以下 3 个相似案例，提炼一个标准化的诊断 Skill。

分析要求：
1. 提取 3 个案例的共性故障特征
2. 总结标准化的诊断流程（步骤 1 → 步骤 2 → ...）
3. 列出关键检查点和常见根因
4. 输出 JSON 格式

输出格式：
{
  "skill_name": "Skill 名称（如：逆变器IGBT过热诊断）",
  "fault_pattern": "核心故障模式描述",
  "diagnosis_steps": ["步骤1: ...", "步骤2: ..."],
  "key_checkpoints": ["检查点1", "检查点2"],
  "common_root_causes": [{"cause": "根因1", "probability": 0.3, "evidence": "证据"}],
  "recommended_actions": ["行动1", "行动2"],
  "safety_notes": ["安全注意事项"]
}
"""

SKILLS_DIR = Path(__file__).parent.parent.parent / "skills"
SKILLS_DIR.mkdir(parents=True, exist_ok=True)


class SkillGenerator:
    """Skill 自动生成引擎"""

    def __init__(self):
        self._generated_skills: dict[str, dict] = {}
        self._load_saved_skills()

    def check_and_generate(self, fault_type: str) -> dict[str, Any]:
        from app.learning.case_ingestion import CaseIngestionService

        ingestion = CaseIngestionService()
        similar = ingestion.get_similar_cases(fault_type, limit=5)

        if len(similar) < 3:
            return {
                "generated": False,
                "reason": f"同模式案例不足（当前 {len(similar)} 个，需要 ≥ 3 个）",
                "current_count": len(similar),
            }

        case_texts = [c.get("text", "") for c in similar[:3]]
        fault_types = [c.get("metadata", {}).get("fault_type", "") for c in similar[:3]]
        if len(set(fault_types)) <= 1:
            return {
                "generated": False,
                "reason": "案例故障类型不够多样化",
                "current_count": len(similar),
            }

        skill_data = self._generate_skill(case_texts, fault_type)
        if not skill_data:
            return {"generated": False, "reason": "LLM 生成失败"}

        skill_id = f"auto-{fault_type.replace(' ', '-').lower()}-{datetime.now().strftime('%Y%m%d')}"
        skill_data["skill_id"] = skill_id
        skill_data["generated_from_cases"] = [c.get("metadata", {}).get("task_id", "") for c in similar[:3]]
        skill_data["created_at"] = datetime.now().isoformat()

        self._generated_skills[skill_id] = skill_data
        self._save_skill(skill_id, skill_data)

        try:
            from app.skill.registry import Skill, skill_registry
            from app.graph.sub_agent import sub_agent_registry
            from app.graph.subgraphs.diagnosis import DiagnosisSubAgent

            existing_skill = skill_registry.get(skill_id)
            if not existing_skill:
                diagnosis_agent = sub_agent_registry.get("diagnosis-agent") or DiagnosisSubAgent()
                new_skill = Skill(
                    skill_id=skill_id,
                    name=skill_data.get("skill_name", f"自动生成: {fault_type}"),
                    description=skill_data.get("fault_pattern", ""),
                    category="diagnosis",
                    intent_triggers=["DIAGNOSIS", "FAULT_DIAGNOSIS"],
                    sub_agent=diagnosis_agent,
                    tools=skill_data.get("recommended_actions", []),
                )
                skill_registry.register(new_skill)
                logger.info(f"Skill 已注册: {skill_id}")
        except Exception as e:
            logger.warning(f"Skill 注册失败: {e}")

        return {
            "generated": True,
            "skill_id": skill_id,
            "skill_name": skill_data.get("skill_name", ""),
            "fault_pattern": skill_data.get("fault_pattern", ""),
            "case_count": len(similar),
        }

    def _generate_skill(self, case_texts: list[str], fault_type: str) -> dict:
        cases_text = ""
        for i, text in enumerate(case_texts):
            cases_text += f"\n### 案例 {i + 1}\n{text[:1500]}\n"

        prompt = SKILL_GENERATION_PROMPT + f"\n\n故障类型: {fault_type}\n{cases_text}"
        try:
            return llm.chat_json("你是新能源场站故障诊断 Skill 生成专家。输出 JSON 格式。", prompt, temperature=0.2)
        except Exception as e:
            logger.error(f"Skill 生成失败: {e}")
            return {}

    def _save_skill(self, skill_id: str, data: dict):
        path = SKILLS_DIR / f"{skill_id}.json"
        try:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Skill 持久化失败: {e}")

    def _load_saved_skills(self):
        if not SKILLS_DIR.exists():
            return
        for f in SKILLS_DIR.glob("auto-*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                self._generated_skills[data.get("skill_id", f.stem)] = data
            except Exception:
                pass

    def list_generated(self) -> list[dict]:
        return [
            {"skill_id": k, "name": v.get("skill_name", k), "created_at": v.get("created_at", "")}
            for k, v in self._generated_skills.items()
        ]


skill_generator = SkillGenerator()
