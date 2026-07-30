"""意图路由 Agent — 9 分类意图识别"""

import logging

from app.agent.llm_client import llm

logger = logging.getLogger(__name__)

ROUTER_PROMPT = """你是电力运维平台的意图识别专家。请分析用户输入，识别意图类型。

意图类型列表：
- FAULT_DIAGNOSIS: 设备故障诊断（风机/逆变器/变压器停机、异常）
- ALARM_DIAGNOSIS: 告警诊断分析
- SAFETY_QA: 安全规程问答
- DEVICE_STATUS: 设备状态查询
- DEVICE_PROFILE: 设备台账查询
- ALARM_QUERY: 告警历史查询
- LOG_ANALYSIS: 日志分析
- TICKET_QUERY: 工单查询
- GENERAL_CHAT: 通用对话

请以 JSON 格式输出：
{"intent": "意图类型", "confidence": 0.95, "entities": {"device_type": "风机/逆变器/变压器", "device_id": "设备编号"}, "reason": "判断理由"}
"""


class RouterAgent:
    """意图路由"""

    def route(self, question: str) -> dict:
        result = llm.chat_json(ROUTER_PROMPT, question, temperature=0.1)
        if not result.get("intent"):
            result["intent"] = "GENERAL_CHAT"
        return result
