"""工具注册中心 — 工具语义检索与权限控制"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ToolInfo:
    def __init__(self, name: str, description: str, tags: list[str], risk_level: str = "LOW"):
        self.name = name
        self.description = description
        self.tags = tags
        self.risk_level = risk_level


class ToolRegistry:
    """工具注册中心"""

    def __init__(self):
        self._tools: dict[str, ToolInfo] = {}
        self._funcs: dict[str, Any] = {}

    def register(self, name: str, func, description: str, tags: list[str] = None,
                 risk_level: str = "LOW"):
        self._tools[name] = ToolInfo(name, description, tags or [], risk_level)
        self._funcs[name] = func

    def get_func(self, name: str):
        return self._funcs.get(name)

    def list_all(self) -> list[dict]:
        return [{"name": t.name, "description": t.description, "tags": t.tags,
                 "risk_level": t.risk_level} for t in self._tools.values()]

    def search(self, keyword: str) -> list[dict]:
        results = []
        for t in self._tools.values():
            if keyword.lower() in t.name.lower() or keyword.lower() in t.description.lower() \
               or any(keyword.lower() in tag.lower() for tag in t.tags):
                results.append({"name": t.name, "description": t.description, "tags": t.tags})
        return results

    def search_by_intent(self, intent: str) -> list[dict]:
        intent_tool_map = {
            "DIAGNOSIS": ["get_device_status", "get_alarm_history", "get_device_logs",
                          "get_defect_tickets", "search_safety_rules"],
            "KNOWLEDGE_QA": ["search_safety_rules"],
            "DEVICE_STATUS": ["get_device_status"],
            "DEVICE_PROFILE": ["get_device_profile"],
            "ALARM_QUERY": ["get_alarm_history"],
            "LOG_ANALYSIS": ["get_device_logs"],
            "TICKET_QUERY": ["get_defect_tickets"],
        }
        names = intent_tool_map.get(intent, [])
        return [{"name": n, "description": self._tools[n].description} for n in names if n in self._tools]


tool_registry = ToolRegistry()

from mcp_server.tools import (
    get_device_status, get_alarm_history, get_device_logs,
    get_defect_tickets, search_safety_rules, get_device_profile,
)

tool_registry.register("get_device_status", get_device_status, "查询设备实时运行状态",
                       ["设备", "状态", "实时", "参数"])
tool_registry.register("get_alarm_history", get_alarm_history, "查询设备历史告警记录",
                       ["告警", "历史", "记录"])
tool_registry.register("get_device_logs", get_device_logs, "查询设备运行日志",
                       ["日志", "运行", "操作记录"])
tool_registry.register("get_defect_tickets", get_defect_tickets, "查询设备缺陷工单",
                       ["工单", "缺陷", "检修"])
tool_registry.register("search_safety_rules", search_safety_rules, "检索电力安全规程条款",
                       ["安规", "安全", "规程"])
tool_registry.register("get_device_profile", get_device_profile, "查询设备台账信息",
                       ["台账", "设备信息", "规格"])
