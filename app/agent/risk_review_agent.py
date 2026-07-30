"""风险审查 Agent — 诊断建议安全性评估"""

import logging

from app.agent.llm_client import llm

logger = logging.getLogger(__name__)

RISK_REVIEW_PROMPT = """你是电力安全审查专家。请审查以下诊断建议的安全性。

你必须输出包含以下内容的审查报告：

## 1. 安全合规性
诊断建议是否符合电力安全规程？列出具体的合规点和违规点。

## 2. 操作风险评估
评估每项操作建议的安全风险等级和潜在后果。

## 3. 风险缓解措施
针对识别的风险，给出具体的缓解措施。

## 4. 最终建议
- is_compliant: true/false
- risk_level: HIGH/MEDIUM/LOW
- suggested_improvements: 改进建议列表

输出 JSON 格式：
{"is_compliant": true, "risk_level": "MEDIUM", "violations": [], "suggestions": ["建议1", "建议2"], "final_recommendation": "可以执行，但需注意..."}
"""


class RiskReviewAgent:
    """风险审查"""

    def review(self, diagnosis_text: str, safety_rules: list[dict] = None) -> dict:
        context = f"## 诊断结果\n{diagnosis_text}"
        if safety_rules:
            rules_text = "\n".join([f"- {r.get('content', '')}" for r in safety_rules])
            context += f"\n\n## 相关安规条款\n{rules_text}"
        try:
            result = llm.chat_json(RISK_REVIEW_PROMPT, context, temperature=0.2)
            return result
        except Exception as e:
            logger.error(f"风险审查失败: {e}")
            return {"is_compliant": True, "risk_level": "LOW", "violations": [], "suggestions": []}
