"""故障诊断 Agent — DeepSeek V4 Pro 驱动，输出 9 项结构化诊断报告"""

import json
import logging

from app.agent.llm_client import llm

logger = logging.getLogger(__name__)

DIAGNOSIS_PROMPT = """你是新能源场站智能诊断专家。请综合分析所有证据，生成结构化诊断报告。

你必须严格按照以下 9 项格式输出诊断报告：

## 1. 告警摘要
简要描述故障事件的关键信息。

## 2. 初步判断
基于告警信息和初步分析，给出初步判断。

## 3. 分析依据
列出支持诊断结论的所有数据和证据来源。

## 4. 可能原因（按可能性排序）
列出所有可能的原因，按可能性从高到低排序，并给出可能性评估（百分比）。

## 5. 排查步骤
给出详细的排查步骤，每步说明目的和方法。

## 6. 处理建议
给出具体的处理建议，包括是否需要降负荷、停运检修等。

## 7. 安全风险提示
列出操作过程中需要注意的安全风险，引用相关安规条款。

## 8. 是否建议派单
明确给出是否建议派单的结论，如建议派单，说明紧急程度和派单类型。

## 9. 风险自复核
对上述诊断建议进行自我审核：
- 诊断结论是否有充分的数据支撑？如有不足，明确指出
- 处理建议是否存在安全风险？如有，补充安全措施
- 是否遗漏了重要的排查步骤？如有，补充说明
- 整体风险等级评估：CRITICAL/HIGH/MEDIUM/LOW

重要规则：
- 高风险操作（停电、降负荷、紧急派单）必须标注 ⚠️ 并建议人工确认
- 严禁编造数据，只能引用工具返回的真实内容
- 涉及安全操作时，必须提示遵守现场规程
- 风险自复核必须诚实客观，发现不足时必须指出

在报告末尾输出一行 JSON：
```json
{"root_cause": "最可能的根因", "confidence": 0.8, "risk_level": "HIGH", "evidence_sufficient": true, "recommend_dispatch": true, "urgency": "紧急"}
```
"""


class DiagnosisAgent:
    """综合诊断 Agent"""

    def diagnose(self, context: str, skill_context: str = "") -> dict:
        full_input = context
        if skill_context:
            full_input += f"\n\n--- 业务场景指导 ---\n{skill_context}"
        text = llm.chat(DIAGNOSIS_PROMPT, full_input, temperature=0.1, max_tokens=8192)
        structured = self._parse_diagnosis(text)
        return {
            "report_text": text,
            **structured,
        }

    def _parse_diagnosis(self, text: str) -> dict:
        result = {"root_cause": "", "confidence": 0.5, "risk_level": "MEDIUM",
                   "evidence_sufficient": True, "recommend_dispatch": False, "urgency": "一般"}
        try:
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0]
                parsed = json.loads(json_str)
                result.update(parsed)
            elif text.strip().startswith("{"):
                parsed = json.loads(text.strip().split("\n")[-1])
                result.update(parsed)
        except (json.JSONDecodeError, IndexError):
            pass
        return result
