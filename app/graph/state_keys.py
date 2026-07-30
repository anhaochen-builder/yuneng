"""35 个 Graph 状态键 — 从 GridOpsAgent GraphStateKeys 复用"""

from dataclasses import dataclass, field
from typing import Any, Optional


class StateKeys:
    """统一管理所有 Graph 状态键，策略: Replace 或 Append"""

    # 输入层
    INPUT = "input"
    CLEANED_INPUT = "cleaned_input"
    REWRITTEN_QUERY = "rewritten_query"

    # 会话标识
    TASK_ID = "task_id"
    SESSION_ID = "session_id"
    USER_ID = "user_id"
    TRACE_ID = "trace_id"

    # 意图与实体
    INTENT = "intent"
    CONFIDENCE = "confidence"
    ENTITIES = "entities"

    # 计划与执行
    PLAN_STEPS = "plan_steps"
    STEP_RESULTS = "step_results"
    EXECUTION_RESULT = "execution_result"
    CURRENT_STEP_INDEX = "current_step_index"
    ADDITIONAL_STEPS = "additional_steps"

    # 证据链
    EVIDENCE = "evidence"
    EVIDENCE_SCORE = "evidence_score"
    EVIDENCE_COVERAGE = "evidence_coverage"
    EVIDENCE_WARNINGS = "evidence_warnings"

    # 诊断核心
    DIAGNOSIS_RESULT = "diagnosis_result"
    RISK_LEVEL = "risk_level"
    NEXT_ACTION = "next_action"

    # 循环控制
    LOOP_COUNT = "loop_count"
    REVIEW_DECISION = "review_decision"
    REVIEW_LOOP = "review_loop"

    # RAG / 工具
    RAG_RESULTS = "rag_results"
    TOOL_RESULT = "tool_result"

    # 上下文注入
    MEMORY_CONTEXT = "memory_context"
    SKILL_CONTEXT = "skill_context"
    HISTORY = "history"
    MATCHED_SKILL = "matched_skill"

    # 设备标识
    DEVICE_ID = "device_id"

    # 安全与验证
    VALIDATION_WARNINGS = "validation_warnings"
    PERMISSION_GRANTED = "permission_granted"
    ALARM_LEVEL = "alarm_level"

    # 最终输出
    FINAL_RESPONSE = "final_response"

    # ========== 策略类型 ==========
    REPLACE_KEYS = {
        INPUT, CLEANED_INPUT, REWRITTEN_QUERY,
        TASK_ID, SESSION_ID, USER_ID, TRACE_ID,
        INTENT, CONFIDENCE, ENTITIES,
        EXECUTION_RESULT, FINAL_RESPONSE,
        LOOP_COUNT, REVIEW_DECISION, REVIEW_LOOP,
        TOOL_RESULT, RAG_RESULTS,
        MEMORY_CONTEXT, SKILL_CONTEXT, HISTORY, MATCHED_SKILL,
        PERMISSION_GRANTED, ALARM_LEVEL, DEVICE_ID,
        EVIDENCE, EVIDENCE_SCORE, EVIDENCE_COVERAGE, EVIDENCE_WARNINGS,
        RISK_LEVEL, NEXT_ACTION,
        PLAN_STEPS, DIAGNOSIS_RESULT, CURRENT_STEP_INDEX, ADDITIONAL_STEPS,
    }

    APPEND_KEYS = {
        STEP_RESULTS, VALIDATION_WARNINGS,
    }

    @classmethod
    def all_keys(cls) -> set:
        return cls.REPLACE_KEYS | cls.APPEND_KEYS

    @classmethod
    def is_append(cls, key: str) -> bool:
        return key in cls.APPEND_KEYS
