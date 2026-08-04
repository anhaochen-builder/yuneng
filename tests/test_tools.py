"""MCP 工具层单元测试 — 6 个核心工具，每个至少 1 个正常 + 1 个异常用例"""

import pytest
from mcp_server.tools import (
    get_device_status, get_alarm_history, get_device_logs,
    get_defect_tickets, search_safety_rules, get_device_profile,
)


class TestDeviceStatus:
    def test_valid_device(self):
        result = get_device_status("INV001")
        assert result["device_id"] == "INV001"
        assert result["device_type"] == "inverter"
        assert result["status"] in ("running", "warning", "fault", "stopped")
        params = result["parameters"]
        assert "temperature_c" in params
        assert "voltage_v" in params
        assert "current_a" in params

    def test_unknown_device(self):
        result = get_device_status("UNKNOWN999")
        assert "error" in result

    def test_wind_turbine_device(self):
        result = get_device_status("WT001")
        assert result["device_type"] == "wind_turbine"
        assert result["device_name"] == "1号风机"

    def test_all_device_types(self):
        for device_id in ("WT001", "INV001", "TRA001", "PV001"):
            result = get_device_status(device_id)
            assert "error" not in result, f"{device_id} 应存在"


class TestAlarmHistory:
    def test_valid_device(self):
        result = get_alarm_history("INV001", limit=5)
        assert result["device_id"] == "INV001"
        assert len(result["alarms"]) == 5
        assert "code" in result["alarms"][0]
        assert "severity" in result["alarms"][0]
        assert "timestamp" in result["alarms"][0]

    def test_limit_bound(self):
        result = get_alarm_history("WT001", limit=30)
        assert len(result["alarms"]) <= 12  # max 12 in mock

    def test_severity_types(self):
        result = get_alarm_history("INV001", limit=10)
        severities = {a["severity"] for a in result["alarms"]}
        assert severities.issubset({"critical", "high", "medium"})

    def test_alarm_statuses(self):
        result = get_alarm_history("INV001", limit=5)
        statuses = {a["status"] for a in result["alarms"]}
        assert statuses.issubset({"active", "cleared", "acknowledged"})


class TestDeviceLogs:
    def test_valid_device(self):
        result = get_device_logs("INV001", limit=5)
        assert result["device_id"] == "INV001"
        assert result["log_type"] == "event"
        logs = result["logs"]
        assert len(logs) == 5
        assert "level" in logs[0]
        assert "message" in logs[0]
        assert "timestamp" in logs[0]

    def test_log_levels(self):
        result = get_device_logs("WT001", limit=10)
        levels = {log["level"] for log in result["logs"]}
        assert levels.issubset({"INFO", "WARN", "ERROR"})

    def test_different_log_types(self):
        result = get_device_logs("TRA001", log_type="alarm", limit=3)
        assert result["log_type"] == "alarm"

    def test_limit_bound(self):
        result = get_device_logs("INV001", limit=100)
        assert len(result["logs"]) <= 10  # max 10 in mock


class TestDefectTickets:
    def test_valid_device(self):
        result = get_defect_tickets("INV001")
        tickets = result["tickets"]
        assert len(tickets) >= 1
        for t in tickets:
            assert "title" in t
            assert "status" in t
            assert "priority" in t

    def test_filter_by_status(self):
        result = get_defect_tickets("INV001", status="processing")
        tickets = result["tickets"]
        for t in tickets:
            assert t["status"] == "processing"

    def test_filter_by_status_closed(self):
        result = get_defect_tickets("INV001", status="closed")
        tickets = result["tickets"]
        assert len(tickets) >= 1
        assert all(t["status"] == "closed" for t in tickets)

    def test_ticket_has_assignee(self):
        result = get_defect_tickets("INV001")
        tickets = result["tickets"]
        for t in tickets:
            assert "assigned_to" in t
            assert len(t["assigned_to"]) > 0

    def test_empty_status_filter(self):
        result = get_defect_tickets("INV001", status="resolved")
        assert len(result["tickets"]) == 0


class TestSafetyRules:
    def test_search_by_keyword(self):
        result = search_safety_rules("停电", limit=3)
        assert result["keyword"] == "停电"
        assert len(result["rules"]) == 3
        assert "content" in result["rules"][0]
        assert "chapter" in result["rules"][0]
        assert "source" in result["rules"][0]

    def test_limit_bound(self):
        result = search_safety_rules("操作", limit=10)
        assert len(result["rules"]) <= 5  # max 5 rules in db
        assert result["total"] == 5

    def test_empty_keyword(self):
        result = search_safety_rules("")
        assert len(result["rules"]) == 5  # all rules returned

    def test_rules_contain_keyword(self):
        result = search_safety_rules("验电", limit=3)
        for rule in result["rules"]:
            content_plus_chapter = rule["content"] + rule["chapter"]
            assert "验电" in content_plus_chapter

    def test_rule_structure_complete(self):
        result = search_safety_rules("安全", limit=5)
        for rule in result["rules"]:
            assert all(k in rule for k in ("id", "chapter", "content", "source"))
            assert rule["id"].startswith("SAFE-")


class TestDeviceProfile:
    def test_valid_device(self):
        result = get_device_profile("INV001")
        assert result["device_id"] == "INV001"
        assert "manufacturer" in result
        assert "model" in result
        assert "install_date" in result
        assert "rated_power" in result

    def test_unknown_device(self):
        result = get_device_profile("UNKNOWN999")
        assert "error" in result

    def test_wind_turbine_profile(self):
        result = get_device_profile("WT001")
        assert result["type"] == "wind_turbine"
        assert result["capacity"] == 3.0

    def test_profile_has_operating_hours(self):
        result = get_device_profile("TRA001")
        assert "operating_hours" in result
        assert isinstance(result["operating_hours"], int)
        assert 0 < result["operating_hours"] <= 20000

    def test_last_maintenance_is_date(self):
        result = get_device_profile("PV001")
        import re
        assert re.match(r"\d{4}-\d{2}-\d{2}", result["last_maintenance"])


class TestToolRegistry:
    def test_registry_has_six_tools(self):
        from app.tools.registry import tool_registry
        all_tools = tool_registry.list_all()
        assert len(all_tools) == 6

    def test_tool_search(self):
        from app.tools.registry import tool_registry
        results = tool_registry.search("设备")
        assert len(results) >= 3

    def test_search_by_intent_diagnosis(self):
        from app.tools.registry import tool_registry
        results = tool_registry.search_by_intent("DIAGNOSIS")
        assert len(results) == 5

    def test_search_by_intent_knowledge_qa(self):
        from app.tools.registry import tool_registry
        results = tool_registry.search_by_intent("KNOWLEDGE_QA")
        assert len(results) >= 1

    def test_search_by_intent_unknown(self):
        from app.tools.registry import tool_registry
        results = tool_registry.search_by_intent("CHAT")
        assert len(results) == 0

    def test_tool_execution(self):
        from app.tools.registry import tool_registry
        func = tool_registry.get_func("get_device_status")
        assert func is not None
        result = func("INV001")
        assert "error" not in result

    def test_risk_levels(self):
        from app.tools.registry import tool_registry
        all_tools = tool_registry.list_all()
        for t in all_tools:
            assert t["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")

    def test_tool_has_tags(self):
        from app.tools.registry import tool_registry
        all_tools = tool_registry.list_all()
        for t in all_tools:
            assert len(t["tags"]) >= 1
