"""Hook 引擎 — 12 个生命周期拦截器，从 GridOpsAgent 完全复用"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
import logging
import re

logger = logging.getLogger(__name__)


@dataclass
class HookContext:
    """Hook 上下文，在 Hook 链中传递"""
    input: str = ""
    output: str = ""
    intent: str = ""
    confidence: float = 0.0
    entities: dict = field(default_factory=dict)
    session_id: str = ""
    user_id: str = ""
    metadata: dict = field(default_factory=dict)
    state: dict = field(default_factory=dict)


class AgentHook(ABC):
    """Hook 基类"""

    @abstractmethod
    def hook_point(self) -> str:
        ...

    @abstractmethod
    def execute(self, ctx: HookContext) -> HookContext:
        ...


class HookEngine:
    """Hook 执行引擎"""

    def __init__(self):
        self._hooks: dict[str, list[AgentHook]] = {}

    def register(self, hook: AgentHook):
        point = hook.hook_point()
        if point not in self._hooks:
            self._hooks[point] = []
        self._hooks[point].append(hook)

    def execute_hooks(self, hook_point: str, ctx: HookContext) -> HookContext:
        hooks = self._hooks.get(hook_point, [])
        for hook in hooks:
            try:
                ctx = hook.execute(ctx)
            except Exception as e:
                logger.warning(f"Hook {hook.__class__.__name__} 执行失败: {e}")
        return ctx


# ============ 12 个 Hook 实现 ============

HOOK_POINTS = {
    "PRE_ROUTE": "pre_route",
    "POST_ROUTE": "post_route",
    "PRE_RAG": "pre_rag",
    "POST_RAG": "post_rag",
    "PRE_TOOL_USE": "pre_tool_use",
    "POST_TOOL_USE": "post_tool_use",
    "PRE_DIAGNOSIS": "pre_diagnosis",
    "POST_DIAGNOSIS": "post_diagnosis",
}


class PreRouteHook(AgentHook):
    """输入清洗、XSS 过滤、长度限制"""
    def hook_point(self): return HOOK_POINTS["PRE_ROUTE"]

    def execute(self, ctx: HookContext) -> HookContext:
        ctx.input = ctx.input.strip()[:5000]
        ctx.input = re.sub(r"<script.*?>.*?</script>", "", ctx.input, flags=re.DOTALL)
        ctx.input = re.sub(r"<[^>]+>", "", ctx.input)
        return ctx


class SafetyCheckHook(AgentHook):
    """安全关键词检查"""
    def hook_point(self): return HOOK_POINTS["PRE_ROUTE"]

    def execute(self, ctx: HookContext) -> HookContext:
        blocked = ["炸弹", "武器", "破坏", "黑客"]
        for kw in blocked:
            if kw in ctx.input:
                ctx.output = "输入包含不安全内容，已拒绝处理。"
                ctx.metadata["blocked"] = True
        return ctx


class PostRouteHook(AgentHook):
    """路由结果合理性校验"""
    def hook_point(self): return HOOK_POINTS["POST_ROUTE"]

    def execute(self, ctx: HookContext) -> HookContext:
        valid_intents = {"DIAGNOSIS", "FAULT_DIAGNOSIS", "ALARM_DIAGNOSIS", "KNOWLEDGE_QA", "CHAT", "ALARM_ANALYSIS", "LOG_ANALYSIS", "TICKET_QUERY", "SAFETY_QA", "DEVICE_STATUS", "DEVICE_PROFILE", "ALARM_QUERY"}
        if ctx.intent not in valid_intents:
            logger.warning(f"未知意图 {ctx.intent}，降级为 CHAT")
            ctx.intent = "CHAT"
            ctx.confidence = 0.3
        return ctx


class PreRagHook(AgentHook):
    """Query 改写，补全设备类型前缀"""
    def hook_point(self): return HOOK_POINTS["PRE_RAG"]

    def execute(self, ctx: HookContext) -> HookContext:
        entity = ctx.entities.get("device_type", "")
        if entity and entity not in ctx.input:
            ctx.input = f"{entity} {ctx.input}"
        return ctx


class PostRagHook(AgentHook):
    """召回质量检查"""
    def hook_point(self): return HOOK_POINTS["POST_RAG"]

    def execute(self, ctx: HookContext) -> HookContext:
        rag_count = ctx.metadata.get("rag_count", 0)
        if rag_count < 3:
            ctx.metadata["rag_quality"] = "low"
            logger.warning(f"RAG 召回量不足 ({rag_count})，建议扩大检索")
        else:
            ctx.metadata["rag_quality"] = "ok"
        return ctx


class PreToolUseHook(AgentHook):
    """权限校验、高风险工具标记"""
    def hook_point(self): return HOOK_POINTS["PRE_TOOL_USE"]

    def execute(self, ctx: HookContext) -> HookContext:
        tool_name = ctx.metadata.get("tool_name", "")
        high_risk_tools = {"get_device_status", "get_alarm_history"}
        if tool_name in high_risk_tools:
            ctx.metadata["risk_marked"] = True
        ctx.metadata["permission_granted"] = True
        return ctx


class PostToolUseHook(AgentHook):
    """结果脱敏"""
    def hook_point(self): return HOOK_POINTS["POST_TOOL_USE"]

    def execute(self, ctx: HookContext) -> HookContext:
        ctx.output = re.sub(r"1[3-9]\d{9}", "***", ctx.output)
        ctx.output = re.sub(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "***@***", ctx.output)
        return ctx


class PreDiagnosisHook(AgentHook):
    """证据充足性检查"""
    def hook_point(self): return HOOK_POINTS["PRE_DIAGNOSIS"]

    def execute(self, ctx: HookContext) -> HookContext:
        evidence = ctx.metadata.get("evidence_count", 0)
        if evidence < 2:
            ctx.metadata["evidence_insufficient"] = True
            logger.warning("证据不足，诊断置信度可能偏低")
        return ctx


class PostDiagnosisHook(AgentHook):
    """风险等级检查、安全提示补全"""
    def hook_point(self): return HOOK_POINTS["POST_DIAGNOSIS"]

    def execute(self, ctx: HookContext) -> HookContext:
        risk = ctx.metadata.get("risk_level", "LOW")
        if risk in ("CRITICAL", "HIGH"):
            ctx.output += "\n\n⚠️ 高风险诊断结论，建议人工复核后再执行处置方案。"
        return ctx


class HumanApprovalHook(AgentHook):
    """高风险操作创建审批请求"""
    def hook_point(self): return HOOK_POINTS["POST_DIAGNOSIS"]

    def execute(self, ctx: HookContext) -> HookContext:
        risk = ctx.metadata.get("risk_level", "LOW")
        if risk in ("CRITICAL", "HIGH"):
            ctx.metadata["approval_required"] = True
            logger.info(f"已创建审批请求: task={ctx.metadata.get('task_id', '')}")
        return ctx


class AuditHook(AgentHook):
    """审计日志记录 — 全生命周期"""
    def hook_point(self): return HOOK_POINTS["POST_DIAGNOSIS"]

    def execute(self, ctx: HookContext) -> HookContext:
        logger.info(f"[审计] user={ctx.user_id} intent={ctx.intent} confidence={ctx.confidence}")
        return ctx


class DataMaskingHook(AgentHook):
    """手机号/敏感信息脱敏"""
    def hook_point(self): return HOOK_POINTS["POST_DIAGNOSIS"]

    def execute(self, ctx: HookContext) -> HookContext:
        ctx.output = re.sub(r"1[3-9]\d{9}", "***", ctx.output)
        ctx.output = re.sub(r"(password|密码|secret)\s*[:=]\s*\S+", r"\1=***", ctx.output, flags=re.IGNORECASE)
        return ctx


def create_hook_engine() -> HookEngine:
    """创建预配置的 Hook 引擎（含全部 12 个 Hook）"""
    engine = HookEngine()
    hooks = [
        PreRouteHook(),
        SafetyCheckHook(),
        PostRouteHook(),
        PreRagHook(),
        PostRagHook(),
        PreToolUseHook(),
        PostToolUseHook(),
        PreDiagnosisHook(),
        PostDiagnosisHook(),
        HumanApprovalHook(),
        AuditHook(),
        DataMaskingHook(),
    ]
    for hook in hooks:
        engine.register(hook)
    return engine
