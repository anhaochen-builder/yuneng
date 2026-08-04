"""Hook 生命周期测试 — 12 个 Hook 的触发时机、输入输出变换、组合行为"""

import pytest
from app.graph.hooks.hooks import (
    HookContext, HookEngine, create_hook_engine,
    PreRouteHook, SafetyCheckHook, PostRouteHook,
    PreRagHook, PostRagHook, PreToolUseHook, PostToolUseHook,
    PreDiagnosisHook, PostDiagnosisHook, HumanApprovalHook,
    AuditHook, DataMaskingHook,
    HOOK_POINTS,
)


class TestHookContext:
    def test_default_values(self):
        ctx = HookContext()
        assert ctx.input == ""
        assert ctx.output == ""
        assert ctx.intent == ""
        assert ctx.confidence == 0.0
        assert ctx.entities == {}

    def test_full_init(self):
        ctx = HookContext(
            input="测试输入", output="测试输出",
            intent="FAULT_DIAGNOSIS", confidence=0.85,
            entities={"device_type": "逆变器", "device_id": "INV001"},
            session_id="sess_123", user_id="user_01",
            metadata={"key": "value"},
        )
        assert ctx.input == "测试输入"
        assert ctx.entities["device_type"] == "逆变器"
        assert ctx.confidence == 0.85


class TestPreRouteHook:
    def test_trim_and_truncate(self):
        hook = PreRouteHook()
        ctx = HookContext(input="  测试输入  ")
        result = hook.execute(ctx)
        assert result.input == "测试输入"

    def test_truncate_long_input(self):
        hook = PreRouteHook()
        long_input = "A" * 6000
        ctx = HookContext(input=long_input)
        result = hook.execute(ctx)
        assert len(result.input) == 5000

    def test_remove_html_tags(self):
        hook = PreRouteHook()
        ctx = HookContext(input='<div>正常内容</div><script>alert("xss")</script>')
        result = hook.execute(ctx)
        assert "<script>" not in result.input
        assert "alert" not in result.input
        assert "正常内容" in result.input

    def test_remove_nested_tags(self):
        hook = PreRouteHook()
        ctx = HookContext(input='<p><span>文本</span></p>')
        result = hook.execute(ctx)
        assert "<p>" not in result.input
        assert "<span>" not in result.input
        assert "文本" in result.input


class TestSafetyCheckHook:
    def test_normal_input(self):
        hook = SafetyCheckHook()
        ctx = HookContext(input="逆变器温度过高需要检查")
        result = hook.execute(ctx)
        assert result.output == ""
        assert not result.metadata.get("blocked")

    def test_blocked_keyword(self):
        hook = SafetyCheckHook()
        ctx = HookContext(input="如何用炸弹破坏设备")
        result = hook.execute(ctx)
        assert "拒绝" in result.output
        assert result.metadata.get("blocked") is True

    def test_blocked_keyword_hacker(self):
        hook = SafetyCheckHook()
        ctx = HookContext(input="黑客攻击手段")
        result = hook.execute(ctx)
        assert result.metadata.get("blocked") is True


class TestPostRouteHook:
    def test_valid_intent(self):
        hook = PostRouteHook()
        ctx = HookContext(intent="FAULT_DIAGNOSIS", confidence=0.95)
        result = hook.execute(ctx)
        assert result.intent == "FAULT_DIAGNOSIS"
        assert result.confidence == 0.95

    def test_invalid_intent_downgrade(self):
        hook = PostRouteHook()
        ctx = HookContext(intent="UNKNOWN_INTENT", confidence=0.9)
        result = hook.execute(ctx)
        assert result.intent == "CHAT"
        assert result.confidence == 0.3


class TestPreRagHook:
    def test_no_device_type(self):
        hook = PreRagHook()
        ctx = HookContext(input="通讯中断", entities={})
        result = hook.execute(ctx)
        assert result.input == "通讯中断"

    def test_append_device_type(self):
        hook = PreRagHook()
        ctx = HookContext(input="通讯中断", entities={"device_type": "逆变器"})
        result = hook.execute(ctx)
        assert result.input == "逆变器 通讯中断"

    def test_already_has_device_type(self):
        hook = PreRagHook()
        ctx = HookContext(input="逆变器通讯中断", entities={"device_type": "逆变器"})
        result = hook.execute(ctx)
        assert result.input == "逆变器通讯中断"


class TestPostRagHook:
    def test_low_quality(self):
        hook = PostRagHook()
        ctx = HookContext(metadata={"rag_count": 1})
        result = hook.execute(ctx)
        assert result.metadata["rag_quality"] == "low"

    def test_ok_quality(self):
        hook = PostRagHook()
        ctx = HookContext(metadata={"rag_count": 5})
        result = hook.execute(ctx)
        assert result.metadata["rag_quality"] == "ok"

    def test_exact_threshold(self):
        hook = PostRagHook()
        ctx = HookContext(metadata={"rag_count": 3})
        result = hook.execute(ctx)
        assert result.metadata["rag_quality"] == "ok"


class TestPreToolUseHook:
    def test_high_risk_tool(self):
        hook = PreToolUseHook()
        ctx = HookContext(metadata={"tool_name": "get_device_status"})
        result = hook.execute(ctx)
        assert result.metadata["risk_marked"] is True
        assert result.metadata["permission_granted"] is True

    def test_low_risk_tool(self):
        hook = PreToolUseHook()
        ctx = HookContext(metadata={"tool_name": "search_safety_rules"})
        result = hook.execute(ctx)
        assert result.metadata.get("risk_marked") is not True
        assert result.metadata["permission_granted"] is True

    def test_high_risk_alarm_history(self):
        hook = PreToolUseHook()
        ctx = HookContext(metadata={"tool_name": "get_alarm_history"})
        result = hook.execute(ctx)
        assert result.metadata["risk_marked"] is True


class TestPostToolUseHook:
    def test_mask_phone(self):
        hook = PostToolUseHook()
        ctx = HookContext(output="联系电话: 13812345678, 请联系")
        result = hook.execute(ctx)
        assert "13812345678" not in result.output
        assert "***" in result.output

    def test_mask_email(self):
        hook = PostToolUseHook()
        ctx = HookContext(output="邮箱是 admin@example.com 有问题联系")
        result = hook.execute(ctx)
        assert "admin@example.com" not in result.output
        assert "***@***" in result.output

    def test_no_sensitive_data(self):
        hook = PostToolUseHook()
        ctx = HookContext(output="温度85°C，功率500kW，正常")
        result = hook.execute(ctx)
        assert result.output == "温度85°C，功率500kW，正常"


class TestPreDiagnosisHook:
    def test_insufficient_evidence(self):
        hook = PreDiagnosisHook()
        ctx = HookContext(metadata={"evidence_count": 1})
        result = hook.execute(ctx)
        assert result.metadata["evidence_insufficient"] is True

    def test_sufficient_evidence(self):
        hook = PreDiagnosisHook()
        ctx = HookContext(metadata={"evidence_count": 3})
        result = hook.execute(ctx)
        assert result.metadata.get("evidence_insufficient") is not True

    def test_exact_threshold(self):
        hook = PreDiagnosisHook()
        ctx = HookContext(metadata={"evidence_count": 2})
        result = hook.execute(ctx)
        assert result.metadata.get("evidence_insufficient") is not True


class TestPostDiagnosisHook:
    def test_critical_risk(self):
        hook = PostDiagnosisHook()
        ctx = HookContext(output="诊断结果正常", metadata={"risk_level": "CRITICAL"})
        result = hook.execute(ctx)
        assert "高风险" in result.output
        assert "人工复核" in result.output

    def test_high_risk(self):
        hook = PostDiagnosisHook()
        ctx = HookContext(output="诊断结果正常", metadata={"risk_level": "HIGH"})
        result = hook.execute(ctx)
        assert "高风险" in result.output

    def test_low_risk_no_warning(self):
        hook = PostDiagnosisHook()
        ctx = HookContext(output="诊断结果正常", metadata={"risk_level": "LOW"})
        result = hook.execute(ctx)
        assert "高风险" not in result.output
        assert "人工复核" not in result.output

    def test_medium_risk(self):
        hook = PostDiagnosisHook()
        ctx = HookContext(output="诊断结果", metadata={"risk_level": "MEDIUM"})
        result = hook.execute(ctx)
        assert result.output == "诊断结果"


class TestHumanApprovalHook:
    def test_critical_creates_approval(self):
        hook = HumanApprovalHook()
        ctx = HookContext(metadata={"risk_level": "CRITICAL", "task_id": "TASK001"})
        result = hook.execute(ctx)
        assert result.metadata["approval_required"] is True

    def test_high_creates_approval(self):
        hook = HumanApprovalHook()
        ctx = HookContext(metadata={"risk_level": "HIGH"})
        result = hook.execute(ctx)
        assert result.metadata["approval_required"] is True

    def test_low_no_approval(self):
        hook = HumanApprovalHook()
        ctx = HookContext(metadata={"risk_level": "LOW"})
        result = hook.execute(ctx)
        assert result.metadata.get("approval_required") is not True


class TestAuditHook:
    def test_audit_executes(self):
        hook = AuditHook()
        ctx = HookContext(
            user_id="user_001", intent="FAULT_DIAGNOSIS",
            confidence=0.88,
        )
        result = hook.execute(ctx)
        assert result.user_id == "user_001"

    def test_audit_empty_context(self):
        hook = AuditHook()
        ctx = HookContext()
        result = hook.execute(ctx)
        assert result is not None


class TestDataMaskingHook:
    def test_mask_phone(self):
        hook = DataMaskingHook()
        ctx = HookContext(output="测试 13800001111 手机号")
        result = hook.execute(ctx)
        assert "13800001111" not in result.output

    def test_mask_password_inline(self):
        hook = DataMaskingHook()
        ctx = HookContext(output="password=abc123 请注意")
        result = hook.execute(ctx)
        assert "abc123" not in result.output
        assert "***" in result.output

    def test_mask_secret_key(self):
        hook = DataMaskingHook()
        ctx = HookContext(output="secret=mykey123 密钥")
        result = hook.execute(ctx)
        assert "mykey123" not in result.output

    def test_no_sensitive_data(self):
        hook = DataMaskingHook()
        ctx = HookContext(output="诊断完成，设备状态正常")
        result = hook.execute(ctx)
        assert result.output == "诊断完成，设备状态正常"


class TestHookEngine:
    def test_create_engine_has_12_hooks(self):
        engine = create_hook_engine()
        total = sum(len(v) for v in engine._hooks.values())
        assert total == 12

    def test_hook_point_distribution(self):
        engine = create_hook_engine()
        expected_points = {"pre_route", "post_route", "pre_rag", "post_rag",
                           "pre_tool_use", "post_tool_use", "pre_diagnosis",
                           "post_diagnosis"}
        assert set(engine._hooks.keys()) == expected_points

    def test_pre_route_has_two_hooks(self):
        engine = create_hook_engine()
        hooks = engine._hooks.get("pre_route", [])
        assert len(hooks) == 2

    def test_post_diagnosis_has_three_hooks(self):
        engine = create_hook_engine()
        hooks = engine._hooks.get("post_diagnosis", [])
        assert len(hooks) == 4  # PostDiagnosis + HumanApproval + Audit + DataMasking

    def test_pipeline_execution_pre_route(self):
        engine = create_hook_engine()
        ctx = HookContext(input=" <script>xss</script> 炸弹 ")
        result = engine.execute_hooks("pre_route", ctx)
        assert "xss" not in result.input.lower()
        assert "炸弹" in result.metadata.get("blocked_reason", "") or result.metadata.get("blocked") is True

    def test_pipeline_execution_post_diagnosis(self):
        engine = create_hook_engine()
        ctx = HookContext(
            output="诊断: inverter故障，联系13800000001",
            metadata={"risk_level": "CRITICAL"},
        )
        result = engine.execute_hooks("post_diagnosis", ctx)
        assert "13800000001" not in result.output
        assert "人工复核" in result.output
        assert result.metadata.get("approval_required") is True

    def test_hook_chain_does_not_crash(self):
        engine = create_hook_engine()
        for point in engine._hooks:
            ctx = HookContext(input="正常测试文本")
            result = engine.execute_hooks(point, ctx)
            assert result is not None

    def test_unknown_hook_point(self):
        engine = create_hook_engine()
        ctx = HookContext(input="测试")
        result = engine.execute_hooks("nonexistent", ctx)
        assert result is ctx  # 原样返回


class TestHookPointConstants:
    def test_all_points_defined(self):
        assert len(HOOK_POINTS) == 8
        assert HOOK_POINTS["PRE_ROUTE"] == "pre_route"
        assert HOOK_POINTS["POST_DIAGNOSIS"] == "post_diagnosis"
