"""AgentState — LangGraph TypedDict 状态定义

35+ 状态键，分为 Replace（覆盖）和 Append（追加）两种策略。
LangGraph 通过 Annotated[type, operator.add] 实现 Append 语义。
"""

import operator
from typing import Annotated, Any, TypedDict


class AgentState(TypedDict, total=False):
    """Agent 全局状态，在 LangGraph 节点间流转。

    所有字段都是可选的（total=False），各节点只返回自己需要更新的字段。
    """

    # ========== 输入层 ==========
    input: str                          # 用户原始输入
    cleaned_input: str                  # 清洗后的输入（去XSS、截断）
    rewritten_query: str                # LLM 改写后的查询关键词

    # ========== 会话标识 ==========
    session_id: str                     # 对话会话标识
    task_id: str                        # 诊断任务唯一标识
    user_id: str                        # 操作用户身份标识
    trace_id: str                       # 链路追踪标识

    # ========== 意图与实体 ==========
    intent: str                         # 路由意图（FAULT_DIAGNOSIS / KNOWLEDGE_QA / CHAT 等）
    confidence: float                   # 意图分类置信度 0-1
    entities: dict[str, Any]            # 提取的实体（device_type / device_id / fault_keywords）

    # ========== 计划与执行 ==========
    plan_steps: list[dict[str, Any]]    # 诊断计划步骤列表
    step_results: Annotated[list, operator.add]   # 各步骤执行结果（Append 策略）
    execution_result: str               # 当前节点执行结果文本
    current_step_index: int             # 当前执行步骤索引

    # ========== 证据链 ==========
    evidence: list[Any]                 # 证据链汇总
    evidence_score: float               # 证据充足性评分 0-1
    evidence_coverage: float            # 证据覆盖度 0-1
    evidence_warnings: list[str]        # 证据不足警告

    # ========== 诊断核心 ==========
    diagnosis_result: dict[str, Any]    # 诊断结果（根因列表 + 分析报告）
    risk_level: str                     # 风险等级（CRITICAL/HIGH/MEDIUM/LOW）
    next_action: str                    # 下一步行动指令

    # ========== 循环控制 ==========
    loop_count: int                     # 重规划次数
    review_decision: str                # 审查决定（ACCEPT / NEED_MORE）
    max_retries: int                    # 最大重试次数

    # ========== RAG / 工具 ==========
    rag_results: str                    # RAG 检索结果文本
    tool_result: str                    # 工具调用结果

    # ========== 记忆层 ==========
    memory_context: str                 # 短期记忆上下文
    skill_context: str                  # 匹配到的 Skill Prompt
    history: str                        # 对话历史（最近3轮）
    matched_skill: str                  # 匹配到的 Skill ID

    # ========== SCADA 层 ==========
    scada_data: dict[str, Any]          # SCADA 时序数据
    scada_timestamp: str                # 数据时间戳
    device_id: str                      # 设备编号

    # ========== 安全与验证 ==========
    validation_warnings: Annotated[list, operator.add]  # 验证告警列表（Append 策略）
    permission_granted: bool            # 权限是否通过
    alarm_level: str                    # 告警级别
    approval_required: bool             # 是否需要人工审批

    # ========== 最终输出 ==========
    final_response: str                 # 最终输出文本
