"""诊断回放 API — /api/trace

查询诊断任务的完整执行轨迹，包含每个节点的输入/输出/耗时。
"""

import logging
import time
from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.graph.builder import get_graph

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/trace", tags=["trace"])


@router.get("/{task_id}/replay")
async def replay_trace(task_id: str):
    """回放指定诊断任务的完整执行轨迹

    利用 LangGraph Checkpointer 查询历史状态快照。
    """
    graph = get_graph()
    config = {"configurable": {"thread_id": task_id}}

    try:
        steps = []

        state_history = list(graph.get_state_history(config))
        state_history.reverse()

        prev_time: float | None = None

        for i, snapshot in enumerate(state_history):
            state = snapshot.values if hasattr(snapshot, "values") else {}

            current_ts = state.get("_checkpoint_ts", "")
            try:
                current_dt = datetime.fromisoformat(current_ts)
                current_epoch = current_dt.timestamp()
            except (ValueError, TypeError):
                current_epoch = time.time()

            elapsed_ms = 0
            if prev_time is not None:
                elapsed_ms = int((current_epoch - prev_time) * 1000)
            prev_time = current_epoch

            node_name = (
                snapshot.metadata.get("source", "unknown")
                if hasattr(snapshot, "metadata")
                else "unknown"
            )

            step_info = {
                "step": i + 1,
                "node_name": node_name,
                "elapsed_ms": elapsed_ms,
                "intent": state.get("intent", ""),
                "confidence": state.get("confidence", 0),
                "risk_level": state.get("risk_level", ""),
                "loop_count": state.get("loop_count", 0),
                "execution_result_preview": (
                    state.get("execution_result", "")[:200]
                    if state.get("execution_result")
                    else ""
                ),
            }
            steps.append(step_info)

        if not steps:
            return {
                "code": 404,
                "data": None,
                "message": f"未找到诊断任务 {task_id} 的轨迹记录",
            }

        return {
            "code": 0,
            "data": {
                "task_id": task_id,
                "total_steps": len(steps),
                "steps": steps,
            },
            "message": "success",
        }

    except Exception as e:
        logger.warning(f"轨迹回放失败: {e}")
        return {
            "code": 500,
            "data": None,
            "message": f"轨迹回放异常: {str(e)}",
        }
