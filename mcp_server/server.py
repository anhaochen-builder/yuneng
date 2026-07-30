"""MCP 电力工具服务器 — 基于 Python MCP SDK"""

import asyncio
import json
import logging
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

from mcp_server.tools import TOOL_REGISTRY

logger = logging.getLogger(__name__)
server = Server("power-emergency-tools")

TOOL_DEFINITIONS = [
    types.Tool(
        name="get_device_status",
        description="查询新能源场站设备的实时运行状态，包括温度、振动、功率、电压、电流等关键参数",
        inputSchema={
            "type": "object",
            "properties": {"device_id": {"type": "string", "description": "设备编号，如WT001/INV001/TRA001/PV001"}},
            "required": ["device_id"],
        },
    ),
    types.Tool(
        name="get_alarm_history",
        description="查询设备的历史告警记录，支持时间范围筛选和数量限制",
        inputSchema={
            "type": "object",
            "properties": {
                "device_id": {"type": "string", "description": "设备编号"},
                "start_time": {"type": "string", "description": "开始时间 YYYY-MM-DD"},
                "end_time": {"type": "string", "description": "结束时间 YYYY-MM-DD"},
                "limit": {"type": "integer", "description": "返回记录数上限", "default": 20},
            },
            "required": ["device_id"],
        },
    ),
    types.Tool(
        name="get_device_logs",
        description="查询设备的运行日志，包括操作记录、事件记录和错误日志",
        inputSchema={
            "type": "object",
            "properties": {
                "device_id": {"type": "string", "description": "设备编号"},
                "log_type": {"type": "string", "description": "日志类型: operation/event/error", "default": "event"},
                "limit": {"type": "integer", "description": "返回记录数上限", "default": 10},
            },
            "required": ["device_id"],
        },
    ),
    types.Tool(
        name="get_defect_tickets",
        description="查询设备的缺陷工单历史，包括待处理、处理中和已关闭的工单",
        inputSchema={
            "type": "object",
            "properties": {
                "device_id": {"type": "string", "description": "设备编号"},
                "status": {"type": "string", "description": "工单状态: open/processing/closed/all", "default": "all"},
            },
            "required": ["device_id"],
        },
    ),
    types.Tool(
        name="search_safety_rules",
        description="检索电力安全操作规程条款，输入关键词返回相关安规条款",
        inputSchema={
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "搜索关键词，如'停电操作'、'验电'、'逆变器检修'"},
                "limit": {"type": "integer", "description": "返回条款数上限", "default": 5},
            },
            "required": ["keyword"],
        },
    ),
    types.Tool(
        name="get_device_profile",
        description="查询设备台账信息，包括厂家、型号、安装日期、额定功率等",
        inputSchema={
            "type": "object",
            "properties": {"device_id": {"type": "string", "description": "设备编号"}},
            "required": ["device_id"],
        },
    ),
]


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return TOOL_DEFINITIONS


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    logger.info(f"MCP 工具调用: {name}, 参数: {arguments}")
    func = TOOL_REGISTRY.get(name)
    if not func:
        return [types.TextContent(type="text", text=json.dumps({"error": f"未知工具: {name}"}, ensure_ascii=False))]

    try:
        result = func(**(arguments or {}))
        return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
    except Exception as e:
        logger.error(f"工具 {name} 执行失败: {e}")
        return [types.TextContent(type="text", text=json.dumps({"error": str(e)}, ensure_ascii=False))]


async def main():
    logger.info("MCP 电力工具服务器启动")
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="power-emergency-tools",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
