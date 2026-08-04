"""成功案例自动入库

触发条件：用户通过 /api/feedback 反馈"准确"
执行动作：
  1. 提取诊断文本（故障描述 + 根因 + 处置方案）
  2. BGE-Large-ZH 编码为 1024 维向量
  3. 存入 ChromaDB long_term_memory 集合
  4. 附带结构化元数据（设备类型、故障类型、时间戳、置信度）
"""

import logging
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)

LONG_TERM_COLLECTION = "long_term_memory"
CASE_COLLECTION = "diagnosis_cases"


class CaseIngestionService:
    """案例自动入库服务"""

    def ingest(
        self,
        task_id: str,
        symptoms: str,
        diagnosis_text: str,
        root_cause: str,
        confidence: float,
        risk_level: str,
        device_id: str = "",
        device_type: str = "",
        user_id: str = "",
    ) -> dict[str, Any]:
        result = {
            "task_id": task_id,
            "success": False,
            "ingested_at": "",
            "note": "",
        }

        if not diagnosis_text or confidence < 0.5:
            result["note"] = "诊断置信度过低，不纳入案例库"
            return result

        meta = {
            "task_id": task_id,
            "device_id": device_id,
            "device_type": device_type,
            "fault_type": self._classify_fault(symptoms),
            "root_cause": root_cause,
            "confidence": confidence,
            "risk_level": risk_level,
            "user_id": user_id,
            "stored_at": datetime.now().isoformat(),
            "source": "user_feedback_accurate",
        }

        full_text = (
            f"故障描述: {symptoms}\n"
            f"根因诊断: {root_cause}\n"
            f"风险等级: {risk_level}\n"
            f"置信度: {confidence * 100:.0f}%\n"
            f"诊断报告: {diagnosis_text[:2000]}"
        )

        try:
            from app.memory.memory_service import get_memory
            memory = get_memory()
            count = memory.save_long_term(full_text, meta, task_id)
            result["success"] = count > 0
            result["ingested_at"] = datetime.now().isoformat()
            if result["success"]:
                logger.info(f"案例入库成功: {task_id} (置信度 {confidence:.2f})")
        except Exception as e:
            result["note"] = str(e)
            logger.warning(f"案例入库失败: {e}")

        return result

    def count_by_fault_type(self, fault_type: str) -> int:
        query = "故障类型 " + fault_type
        try:
            from app.memory.memory_service import get_memory
            memory = get_memory()
            results = memory.search_long_term(query, top_k=50, device_type=fault_type)
            return len(results)
        except Exception:
            return 0

    def get_similar_cases(self, fault_type: str, limit: int = 3) -> list[dict]:
        try:
            from app.memory.memory_service import get_memory
            memory = get_memory()
            return memory.search_long_term(fault_type, top_k=limit, device_type=fault_type)
        except Exception:
            return []

    @staticmethod
    def _classify_fault(text: str) -> str:
        text_lower = text
        if any(k in text_lower for k in ["通讯", "通信", "通讯中断", "通讯故障"]):
            return "通讯故障"
        if any(k in text_lower for k in ["温度", "高温", "过热", "过温", "IGBT"]):
            return "温度异常"
        if any(k in text_lower for k in ["振动", "摆动", "晃动"]):
            return "机械振动"
        if any(k in text_lower for k in ["电压", "电流", "功率", "过载", "过流"]):
            return "电气异常"
        if any(k in text_lower for k in ["绝缘", "泄漏", "放电"]):
            return "绝缘故障"
        if any(k in text_lower for k in ["油温", "瓦斯", "变压器"]):
            return "变压器异常"
        return "其他故障"


case_ingestion = CaseIngestionService()
