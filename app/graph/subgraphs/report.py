"""报告生成子智能体 — 诊断报告格式化与安全审查

2 节点内部流程:
  START → SafetyReview → FormatReport → END

负责:
- 安全审查：检查诊断建议是否符合电力安全规程
- 报告格式化：将诊断结果生成标准化报告
"""

import logging
from typing import Any

from langgraph.graph import StateGraph, START, END

from app.graph.sub_agent import BaseSubAgent, SubAgentMeta
from app.graph.state_keys import StateKeys as K
from app.agent.llm_client import llm

logger = logging.getLogger(__name__)


class ReportSubAgent(BaseSubAgent):
    meta = SubAgentMeta(
        agent_id="report-agent",
        name="诊断报告生成与审核",
        description="安全合规审查 + 标准化诊断报告生成，包含安规条款引用和风险标注",
        category="report",
        intent_triggers=["DIAGNOSIS", "FAULT_DIAGNOSIS", "ALARM_DIAGNOSIS", "GENERAL_CHAT"],
        required_tools=["search_safety_rules"],
        priority=6,
    )

    def build_nodes(self, builder: StateGraph) -> None:
        builder.add_node("safety_review", self._safety_review_node)
        builder.add_node("format_report", self._format_report_node)

        builder.add_edge(START, "safety_review")
        builder.add_edge("safety_review", "format_report")
        builder.add_edge("format_report", END)

    def _safety_review_node(self, state: dict[str, Any]) -> dict[str, Any]:
        """安全审查：检查操作合规性"""
        execution_result = state.get(K.EXECUTION_RESULT, "")
        safety_warnings = []

        if not execution_result:
            return {"_safety_violations": [], "_safety_text": ""}

        safety_prompt = (
            "你是电力安全规程审查专家。请审查以下诊断报告的操作建议，"
            "检查是否存在违反电力安全规程的内容。输出JSON："
            '{"violations": [{"clause": "条款号", "description": "违规内容"}], '
            '"risk_level": "HIGH/MEDIUM/LOW", '
            '"improvements": ["改进建议1", "改进建议2"]}'
        )
        try:
            safety_result = llm.chat_json(safety_prompt, execution_result[:4000], temperature=0.1)
            violations = safety_result.get("violations", [])
            improvements = safety_result.get("improvements", [])
            risk_level = safety_result.get("risk_level", "MEDIUM")

            safety_text = "## 安全审查\n"
            if violations:
                safety_text += "\n### 违规项\n"
                for v in violations:
                    safety_text += f"- [{v.get('clause', '?')}] {v.get('description', '')}\n"
            else:
                safety_text += "\n未发现明显违规项。\n"

            if improvements:
                safety_text += "\n### 改进建议\n"
                for imp in improvements:
                    safety_text += f"- {imp}\n"

            return {
                "_safety_violations": violations,
                "_safety_text": safety_text,
                K.RISK_LEVEL: risk_level,
            }
        except Exception as e:
            logger.warning(f"安全审查失败: {e}")
            return {"_safety_violations": [], "_safety_text": f"[安全审查降级] {e}"}

    def _format_report_node(self, state: dict[str, Any]) -> dict[str, Any]:
        """报告格式化：整合诊断结果+安全审查→最终报告"""
        execution = state.get(K.EXECUTION_RESULT, "")
        safety_text = state.get("_safety_text", "")
        diag_result = state.get(K.DIAGNOSIS_RESULT, {})
        risk_level = state.get(K.RISK_LEVEL, "MEDIUM")

        root_causes = diag_result.get("root_causes", [])
        causes_text = ""
        for rc in root_causes:
            causes_text += (
                f"- {rc.get('cause', '未知')} "
                f"(概率: {rc.get('probability', 0.5) * 100:.0f}%)\n"
            )

        final_response = execution
        if safety_text and "[安全审查降级]" not in safety_text:
            final_response += f"\n\n{safety_text}"

        if not state.get(K.FINAL_RESPONSE):
            final_response = (
                f"## 诊断结论\n{causes_text}\n"
                f"## 分析过程\n{execution[:2000]}\n\n"
                f"{safety_text if '[安全审查降级]' not in safety_text else ''}"
                f"\n> 风险等级: {risk_level}"
            )

        return {
            K.FINAL_RESPONSE: final_response,
            K.RISK_LEVEL: risk_level,
        }
