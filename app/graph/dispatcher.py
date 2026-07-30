"""意图路由分发器 — 根据 intent 分发到对应子图"""

from typing import Any
from app.graph.state_keys import StateKeys as K


class IntentDispatcher:
    """意图分发：KNOWLEDGE_QA → knowledge / DIAGNOSIS → diagnosis / 其他 → chat"""

    @staticmethod
    def dispatch(state: dict[str, Any]) -> str:
        intent = state.get(K.INTENT, "CHAT")
        if intent in ("KNOWLEDGE_QA", "SAFETY_QA", "DEVICE_STATUS", "DEVICE_PROFILE", "ALARM_QUERY"):
            return "knowledge_qa"
        elif intent in ("DIAGNOSIS", "FAULT_DIAGNOSIS", "ALARM_DIAGNOSIS", "ALARM_ANALYSIS"):
            return "diagnosis"
        elif intent in ("LOG_ANALYSIS", "TICKET_QUERY"):
            return "diagnosis"
        else:
            return "chat"
