"""Diagnosis 子图 — 9 节点: EntityExtract→AlarmRAG→Plan→Execute→Validate→Diagnose→Replan→Risk→Action"""

import logging
import json
from typing import Any

from app.graph.state_keys import StateKeys as K
from app.agent.llm_client import llm
from app.rag.hybrid_search import HybridSearchService
from app.rag.knowledge_graph import KnowledgeGraphService
from app.graph.hooks.hooks import create_hook_engine, HookContext, HOOK_POINTS

logger = logging.getLogger(__name__)
hook_engine = create_hook_engine()
hybrid_search = HybridSearchService()
kg_service = KnowledgeGraphService()


def entity_extract_node(state: dict[str, Any]) -> dict[str, Any]:
    """EntityExtract: 实体提取"""
    text = state.get(K.INPUT, "")
    result = kg_service.extract_entities(text)
    return {K.ENTITIES: result}


def alarm_rag_retrieve_node(state: dict[str, Any]) -> dict[str, Any]:
    """AlarmRAG: 检索相关故障案例和规程"""
    query = state.get(K.INPUT, "")
    results = hybrid_search.search(query, top_k=10)
    graph_context = kg_service.build_graph_context(query)
    rag_text = "\n\n".join([f"[参考{i+1}] {r['text'][:500]}" for i, r in enumerate(results[:5])])
    if graph_context:
        rag_text = graph_context + "\n\n" + rag_text
    return {K.RAG_RESULTS: rag_text}


def planner_node(state: dict[str, Any]) -> dict[str, Any]:
    """Planner: 生成诊断计划步骤"""
    question = state.get(K.INPUT, "")
    entities = state.get(K.ENTITIES, {})
    rag_context = state.get(K.RAG_RESULTS, "")
    prompt = f"""你是故障诊断计划专家。根据以下信息生成诊断计划。

故障描述: {question}
实体信息: {json.dumps(entities, ensure_ascii=False)}
知识库参考: {rag_context[:1000]}

生成 JSON 格式的诊断计划步骤列表，每个步骤包含 step_id, type(rag/tool/diagnosis), action, description:
{"steps": [{"step_id": "1", "type": "rag", "action": "检索类似案例", "description": "..."}]}
"""
    plan = llm.chat_json(prompt, "", temperature=0.1)
    steps = plan.get("steps", [{"step_id": "1", "type": "diagnosis", "action": "综合诊断", "description": "执行诊断"}])
    return {K.PLAN_STEPS: steps, K.CURRENT_STEP_INDEX: 0}


# executor_node 和数据收集节点在外部工具调用后完成，此处做简化处理
def executor_node(state: dict[str, Any]) -> dict[str, Any]:
    """Executor: 执行计划步骤（简化：收集所有上下文）"""
    rag = state.get(K.RAG_RESULTS, "")
    step_results = state.get(K.STEP_RESULTS, [])
    result_text = f"## RAG 检索结果\n{rag}\n\n"
    if step_results:
        result_text += "## 步骤执行结果\n"
        for sr in step_results:
            result_text += f"- {sr}\n"
    return {K.EXECUTION_RESULT: result_text}


def evidence_validation_node(state: dict[str, Any]) -> dict[str, Any]:
    """EvidenceValidation: 证据充足性校验"""
    evidence_count = len(state.get(K.STEP_RESULTS, [])) + (1 if state.get(K.RAG_RESULTS) else 0)
    ctx = HookContext(metadata={"evidence_count": evidence_count})
    ctx = hook_engine.execute_hooks(HOOK_POINTS["PRE_DIAGNOSIS"], ctx)
    insufficient = ctx.metadata.get("evidence_insufficient", False)
    if insufficient and state.get(K.LOOP_COUNT, 0) < state.get("max_retries", 2):
        return {K.LOOP_COUNT: state.get(K.LOOP_COUNT, 0) + 1, K.EVIDENCE_SCORE: 0.5}
    return {K.EVIDENCE_SCORE: 0.8, K.EVIDENCE_COVERAGE: 0.8}


def diagnosis_node(state: dict[str, Any]) -> dict[str, Any]:
    """Diagnose: 综合诊断 — 由外部 DiagnosisAgent 驱动，此处为节点占位"""
    return {}


def replanner_node(state: dict[str, Any]) -> dict[str, Any]:
    """Replanner: 重规划判断"""
    score = state.get(K.EVIDENCE_SCORE, 0.8)
    # 置信度由外部引擎计算
    return {K.NEXT_ACTION: "continue"}


def replanner_dispatch(state: dict[str, Any]) -> str:
    next_action = state.get(K.NEXT_ACTION, "continue")
    if next_action == "replan":
        return "replan"
    return "continue"


def risk_assessment_node(state: dict[str, Any]) -> dict[str, Any]:
    """RiskAssessment: 风险评估"""
    return {}


def action_recommend_node(state: dict[str, Any]) -> dict[str, Any]:
    """ActionRecommend: 行动建议"""
    return {}
