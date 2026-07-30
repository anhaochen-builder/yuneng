"""Skill 注册与管理 — 场景化 Prompt 注入"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class Skill:
    """技能定义"""

    def __init__(self, skill_id: str, name: str, category: str, prompt_template: str,
                 intent_triggers: list[str], tools: list[str] = None):
        self.skill_id = skill_id
        self.name = name
        self.category = category
        self.prompt_template = prompt_template
        self.intent_triggers = intent_triggers
        self.tools = tools or []


class SkillRegistry:
    """技能注册中心"""

    def __init__(self):
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill):
        self._skills[skill.skill_id] = skill
        logger.info(f"注册 Skill: {skill.skill_id} ({skill.name})")

    def get(self, skill_id: str) -> Optional[Skill]:
        return self._skills.get(skill_id)

    def select_by_intent(self, intent: str) -> Optional[Skill]:
        """根据意图匹配 Skill"""
        for skill in self._skills.values():
            if intent in skill.intent_triggers:
                return skill
        return None

    def list_all(self) -> list[dict]:
        return [
            {"skill_id": s.skill_id, "name": s.name, "category": s.category,
             "triggers": s.intent_triggers}
            for s in self._skills.values()
        ]


_default_skills = [
    Skill(
        "power-fault-diagnosis", "新能源故障诊断", "diagnosis",
        """## 新能源场站故障诊断场景

你是新能源场站故障诊断专家，请遵循以下诊断流程：

1. **症状分析**: 从描述中提取关键症状（通讯中断、温度异常、功率下降等）
2. **设备定位**: 确定故障设备类型和编号
3. **告警关联**: 分析当前告警与历史告警的关联
4. **多因子推理**: 综合考虑设备状态、运行数据、历史案例进行推理
5. **置信度评估**: 给出每个可能原因的置信度和依据
6. **处置方案**: 按优先级给出可执行的操作步骤
7. **安全审查**: 审核方案是否符合安规要求

重点关注：
- 风机：振动、温度、齿轮箱、偏航、变桨系统
- 逆变器：通讯、IGBT、直流侧、交流侧、效率
- 变压器：油温、瓦斯、差动保护、绝缘
- 光伏：组串电流、绝缘阻抗、并网功率""",
        ["DIAGNOSIS", "FAULT_DIAGNOSIS", "ALARM_DIAGNOSIS"],
        ["get_device_status", "get_alarm_history", "get_device_logs", "get_defect_tickets", "search_safety_rules"],
    ),
    Skill(
        "scada-data-analyzer", "SCADA 数据分析", "analysis",
        """## SCADA 数据分析场景

你是新能源场站 SCADA 数据分析专家，请分析设备运行数据：

1. **趋势分析**: 分析参数随时间的变化趋势
2. **异常检测**: 识别超过正常范围的数据点
3. **相关性分析**: 分析不同参数之间的相关关系
4. **统计摘要**: 输出关键统计指标（均值、标准差、分位数）""",
        ["LOG_ANALYSIS"],
        [],
    ),
    Skill(
        "report-generator", "诊断报告生成", "report",
        """## 诊断报告生成场景

你是电力诊断报告生成专家，请将诊断结果格式化为规范的诊断报告：

报告必须包含：
1. 基本信息（设备编号、诊断时间、操作人员）
2. 故障摘要（问题描述、告警级别）
3. 诊断分析（可能原因、概率、证据）
4. 处置方案（步骤、工具、预计耗时）
5. 安全审查（风险提示、安规条款引用）
6. 复核意见（诊断质量自评、补充建议）""",
        ["GENERAL_CHAT"],
        [],
    ),
]

skill_registry = SkillRegistry()
for skill in _default_skills:
    skill_registry.register(skill)
