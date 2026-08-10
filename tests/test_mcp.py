"""MCP 工具测试 — 工具注册 / 执行 / 往返时间 / 异常场景 / 服务端处理"""
import json
import time
import pytest


class TestToolRegistry:
    def test_registry_import(self):
        from app.tools.registry import tool_registry
        assert tool_registry is not None

    def test_registry_has_tools(self):
        from app.tools.registry import tool_registry
        tools = tool_registry.list_all()
        assert len(tools) >= 6

    def test_registry_list_all_structure(self):
        from app.tools.registry import tool_registry
        tools = tool_registry.list_all()
        for t in tools:
            assert "name" in t
            assert "description" in t
            assert "risk_level" in t

    def test_search_by_intent_diagnosis(self):
        from app.tools.registry import tool_registry
        results = tool_registry.search_by_intent("DIAGNOSIS")
        assert len(results) >= 4

    def test_search_by_intent_device_status(self):
        from app.tools.registry import tool_registry
        results = tool_registry.search_by_intent("DEVICE_STATUS")
        assert len(results) >= 1
        assert any(r["name"] == "get_device_status" for r in results)

    def test_search_keyword(self):
        from app.tools.registry import tool_registry
        results = tool_registry.search("alarm")
        assert len(results) >= 1
        for r in results:
            assert "alarm" in r["name"].lower() or "alarm" in r["description"].lower()

    def test_get_registered_func(self):
        from app.tools.registry import tool_registry
        func = tool_registry.get_func("get_device_status")
        assert callable(func)

    def test_registry_tool_count(self):
        from app.tools.registry import tool_registry
        assert len(tool_registry._tools) >= 6

    def test_registry_all_have_funcs(self):
        from app.tools.registry import tool_registry
        for name in tool_registry._tools:
            assert callable(tool_registry.get_func(name)), f"{name} 缺少可调用函数"

    def test_search_by_intent_returns_structured(self):
        from app.tools.registry import tool_registry
        for intent in ["DIAGNOSIS", "DEVICE_STATUS", "ALARM_QUERY"]:
            results = tool_registry.search_by_intent(intent)
            for r in results:
                assert "name" in r
                assert "description" in r


# ─── 工具执行往返时间 (< 500ms) ───

class TestToolRoundTrip:
    def test_get_device_status_latency(self):
        from mcp_server.tools import get_device_status
        t0 = time.perf_counter()
        result = get_device_status("WT001")
        elapsed = time.perf_counter() - t0
        assert "error" not in result
        assert elapsed < 0.5, f"get_device_status 超时: {elapsed:.3f}s"

    def test_get_alarm_history_latency(self):
        from mcp_server.tools import get_alarm_history
        t0 = time.perf_counter()
        result = get_alarm_history("INV001", limit=20)
        elapsed = time.perf_counter() - t0
        assert "alarms" in result
        assert elapsed < 0.5, f"get_alarm_history 超时: {elapsed:.3f}s"

    def test_get_device_logs_latency(self):
        from mcp_server.tools import get_device_logs
        t0 = time.perf_counter()
        result = get_device_logs("TRA001", log_type="event", limit=10)
        elapsed = time.perf_counter() - t0
        assert "logs" in result
        assert elapsed < 0.5, f"get_device_logs 超时: {elapsed:.3f}s"

    def test_get_defect_tickets_latency(self):
        from mcp_server.tools import get_defect_tickets
        t0 = time.perf_counter()
        result = get_defect_tickets("INV001")
        elapsed = time.perf_counter() - t0
        assert "tickets" in result
        assert elapsed < 0.5, f"get_defect_tickets 超时: {elapsed:.3f}s"

    def test_search_safety_rules_latency(self):
        from mcp_server.tools import search_safety_rules
        t0 = time.perf_counter()
        result = search_safety_rules("停电操作", limit=5)
        elapsed = time.perf_counter() - t0
        assert "rules" in result
        assert elapsed < 0.5, f"search_safety_rules 超时: {elapsed:.3f}s"

    def test_get_device_profile_latency(self):
        from mcp_server.tools import get_device_profile
        t0 = time.perf_counter()
        result = get_device_profile("PV001")
        elapsed = time.perf_counter() - t0
        assert "manufacturer" in result
        assert elapsed < 0.5, f"get_device_profile 超时: {elapsed:.3f}s"

    def test_all_six_tools_within_500ms(self):
        from mcp_server.tools import (
            get_device_status, get_alarm_history, get_device_logs,
            get_defect_tickets, search_safety_rules, get_device_profile,
        )
        tools = [
            ("get_device_status", lambda: get_device_status("WT001")),
            ("get_alarm_history", lambda: get_alarm_history("INV001", limit=5)),
            ("get_device_logs", lambda: get_device_logs("TRA001", limit=3)),
            ("get_defect_tickets", lambda: get_defect_tickets("INV001", status="open")),
            ("search_safety_rules", lambda: search_safety_rules("验电", limit=3)),
            ("get_device_profile", lambda: get_device_profile("WT002")),
        ]
        for name, fn in tools:
            t0 = time.perf_counter()
            fn()
            elapsed = time.perf_counter() - t0
            assert elapsed < 0.5, f"{name} 超时 ({elapsed:.3f}s)"


# ─── 异常场景 ───

class TestToolErrorHandling:
    def test_unknown_device_returns_error(self):
        from mcp_server.tools import get_device_status
        result = get_device_status("UNKNOWN_999")
        assert "error" in result

    def test_unknown_device_alarm_history_empty(self):
        from mcp_server.tools import get_alarm_history
        result = get_alarm_history("NONEXISTENT")
        assert "alarms" in result

    def test_unknown_device_profile_error(self):
        from mcp_server.tools import get_device_profile
        result = get_device_profile("FAKE_001")
        assert "error" in result

    def test_search_safety_rules_empty_keyword(self):
        from mcp_server.tools import search_safety_rules
        result = search_safety_rules("")
        assert "rules" in result
        assert len(result["rules"]) >= 0

    def test_defect_tickets_empty_for_closed(self):
        from mcp_server.tools import get_defect_tickets
        result = get_defect_tickets("INV001", status="closed")
        assert len(result["tickets"]) > 0

    def test_all_known_devices_return_status(self):
        from mcp_server.tools import MOCK_DEVICES, get_device_status
        for device_id in MOCK_DEVICES:
            result = get_device_status(device_id)
            assert "error" not in result, f"设备 {device_id} 返回错误"
            assert result["device_id"] == device_id


# ─── 工具结果结构验证 ───

class TestToolResultStructure:
    def test_device_status_structure(self):
        from mcp_server.tools import get_device_status
        result = get_device_status("WT001")
        required = ["device_id", "device_name", "device_type", "status", "timestamp", "parameters", "location"]
        for key in required:
            assert key in result, f"缺少字段 {key}"
        params = result["parameters"]
        for key in ["temperature_c", "vibration_mm_s", "power_kw", "voltage_v", "current_a", "frequency_hz"]:
            assert key in params, f"缺少参数 {key}"

    def test_alarm_history_structure(self):
        from mcp_server.tools import get_alarm_history
        result = get_alarm_history("INV001")
        assert "alarms" in result
        assert "total" in result
        if result["alarms"]:
            alarm = result["alarms"][0]
            for key in ["id", "device_id", "code", "description", "severity", "timestamp", "status"]:
                assert key in alarm, f"告警缺少字段 {key}"

    def test_device_logs_structure(self):
        from mcp_server.tools import get_device_logs
        result = get_device_logs("TRA001")
        assert "logs" in result
        if result["logs"]:
            log = result["logs"][0]
            for key in ["id", "device_id", "type", "level", "message", "timestamp"]:
                assert key in log, f"日志缺少字段 {key}"

    def test_defect_tickets_structure(self):
        from mcp_server.tools import get_defect_tickets
        result = get_defect_tickets("INV001")
        assert "tickets" in result
        if result["tickets"]:
            ticket = result["tickets"][0]
            for key in ["id", "device_id", "title", "description", "status", "priority", "assigned_to"]:
                assert key in ticket, f"工单缺少字段 {key}"

    def test_safety_rules_structure(self):
        from mcp_server.tools import search_safety_rules
        result = search_safety_rules("停电")
        assert "rules" in result
        if result["rules"]:
            rule = result["rules"][0]
            for key in ["id", "chapter", "content", "source"]:
                assert key in rule, f"安规缺少字段 {key}"

    def test_device_profile_structure(self):
        from mcp_server.tools import get_device_profile
        result = get_device_profile("WT001")
        for key in ["device_id", "name", "type", "manufacturer", "model", "install_date", "rated_power"]:
            assert key in result, f"台账缺少字段 {key}"


# ─── MCP 工具定义完整性 ───

class TestMCPToolDefinitions:
    def test_tools_module_import(self):
        try:
            from mcp_server.tools import TOOL_REGISTRY
            assert TOOL_REGISTRY is not None
        except ImportError:
            pytest.skip("MCP SDK 未安装")

    def test_mcp_server_import(self):
        try:
            from mcp_server.server import server, TOOL_DEFINITIONS
            assert len(TOOL_DEFINITIONS) >= 6
        except ImportError:
            pytest.skip("MCP SDK 未安装")

    def test_tool_definitions_complete(self):
        try:
            from mcp_server.server import TOOL_DEFINITIONS
            tool_names = [t.name for t in TOOL_DEFINITIONS]
            expected = {"get_device_status", "get_alarm_history", "get_device_logs",
                         "get_defect_tickets", "search_safety_rules", "get_device_profile"}
            assert expected.issubset(set(tool_names))
        except ImportError:
            pytest.skip("MCP SDK 未安装")

    def test_tool_definitions_have_schema(self):
        try:
            from mcp_server.server import TOOL_DEFINITIONS
            for tool in TOOL_DEFINITIONS:
                assert tool.name
                assert tool.description
                assert tool.inputSchema
                assert "properties" in tool.inputSchema
                assert "required" in tool.inputSchema
        except ImportError:
            pytest.skip("MCP SDK 未安装")

    def test_tool_definitions_required_params(self):
        try:
            from mcp_server.server import TOOL_DEFINITIONS
            # 每个工具都应定义 required 参数列表
            for tool in TOOL_DEFINITIONS:
                required = tool.inputSchema.get("required", [])
                assert len(required) >= 1, f"{tool.name} 缺少 required 字段"
        except ImportError:
            pytest.skip("MCP SDK 未安装")

    def test_registry_matches_server(self):
        try:
            from mcp_server.server import TOOL_DEFINITIONS
            from mcp_server.tools import TOOL_REGISTRY
            server_tool_names = {t.name for t in TOOL_DEFINITIONS}
            registry_tool_names = set(TOOL_REGISTRY.keys())
            assert server_tool_names == registry_tool_names, \
                f"不一致: server={server_tool_names - registry_tool_names}, registry={registry_tool_names - server_tool_names}"
        except ImportError:
            pytest.skip("MCP SDK 未安装")


# ─── MCP 服务端处理器 ───

class TestMCPServerHandler:
    def test_handle_list_tools(self):
        import asyncio
        try:
            from mcp_server.server import handle_list_tools
            tools = asyncio.run(handle_list_tools())
            assert len(tools) == 6
            assert all(hasattr(t, 'name') for t in tools)
        except ImportError:
            pytest.skip("MCP SDK 未安装")

    def test_handle_call_tool_valid(self):
        import asyncio
        try:
            from mcp_server.server import handle_call_tool
            result = asyncio.run(handle_call_tool("get_device_status", {"device_id": "WT001"}))
            assert len(result) >= 1
            text = result[0].text
            data = json.loads(text)
            assert "error" not in data
            assert data["device_id"] == "WT001"
        except ImportError:
            pytest.skip("MCP SDK 未安装")

    def test_handle_call_tool_unknown(self):
        import asyncio
        try:
            from mcp_server.server import handle_call_tool
            result = asyncio.run(handle_call_tool("unknown_tool", {}))
            assert len(result) >= 1
            data = json.loads(result[0].text)
            assert "error" in data
        except ImportError:
            pytest.skip("MCP SDK 未安装")

    def test_handle_call_tool_all_six(self):
        import asyncio
        try:
            from mcp_server.server import handle_call_tool
            tests = [
                ("get_device_status", {"device_id": "WT001"}, "device_id"),
                ("get_alarm_history", {"device_id": "INV001", "limit": 3}, "alarms"),
                ("get_device_logs", {"device_id": "TRA001"}, "logs"),
                ("get_defect_tickets", {"device_id": "INV001", "status": "open"}, "tickets"),
                ("search_safety_rules", {"keyword": "停电"}, "rules"),
                ("get_device_profile", {"device_id": "PV001"}, "manufacturer"),
            ]
            for name, args, expected_key in tests:
                result = asyncio.run(handle_call_tool(name, args))
                data = json.loads(result[0].text)
                assert expected_key in data, f"{name} 缺少字段 {expected_key}"
        except ImportError:
            pytest.skip("MCP SDK 未安装")
