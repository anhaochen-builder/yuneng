"""MCP 工具测试 — 工具注册 / 执行 / 查询"""
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


class TestMCPTools:
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
