"""Judge 子智能体 — 诊断质量五维度独立评分"""

import logging
from typing import Any

from langgraph.graph import StateGraph, START, END
from app.graph.sub_agent import BaseSubAgent, SubAgentMeta
from app.graph.state_keys import StateKeys as K
from app.agent.judge_agent import JudgeAgent

logger = logging.getLogger(__name__)


class JudgeSubAgent(BaseSubAgent):
    meta = SubAgentMeta(
        agent_id="judge-agent",
        name="诊断质量评审专家",
        description="对诊断报告进行5维度量化评分(证据/逻辑/安规/操作/历史)，0-100分",
        category="review",
        intent_triggers=["DIAGNOSIS", "FAULT_DIAGNOSIS", "ALARM_DIAGNOSIS"],
        required_tools=[],
        priority=8,
    )

    def build_nodes(self, builder: StateGraph) -> None:
        builder.add_node("evaluate", self._evaluate_node)
        builder.add_edge(START, "evaluate")
        builder.add_edge("evaluate", END)

    def _evaluate_node(self, state: dict[str, Any]) -> dict[str, Any]:
        report = state.get(K.EXECUTION_RESULT, "")
        entities = state.get(K.ENTITIES, {})
        step_results = state.get(K.STEP_RESULTS, [])

        judge = JudgeAgent()
        evidence_ctx = {
            "evidence_count": len(step_results) + (1 if state.get(K.RAG_RESULTS) else 0),
            "device_type": entities.get("device_type", "未知"),
            "has_scada": bool(state.get(K.DEVICE_ID, "")),
            "has_multimodal": bool(state.get("_multimodal_result", "")),
            "retry_count": state.get(K.LOOP_COUNT, 0),
        }
        judge_result = judge.evaluate(report, evidence_ctx)

        score = judge_result.get("total_score", 60)
        logger.info(f"Judge 评分: {score}/100 ({judge_result.get('grade', 'C')})")

        return {
            "_judge_result": judge_result,
            "judge_score": score,
            "judge_details": judge_result.get("dimensions", {}),
            K.CONFIDENCE: score / 100.0,
            K.EVIDENCE_SCORE: judge_result.get("dimensions", {}).get("evidence", {}).get("score", 80) / 100.0,
            K.EVIDENCE_COVERAGE: judge_result.get("dimensions", {}).get("evidence", {}).get("score", 80) / 100.0,
        }
