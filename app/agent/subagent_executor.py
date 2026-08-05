"""子 Agent 并行执行器 — 4 子 Agent 并行 + 1 风险复核串行"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from app.agent.llm_client import llm

logger = logging.getLogger(__name__)

SUBAGENT_PROMPTS = {
    "regulation": """你是安规查询专家。根据故障现象检索相关安全规程条款。
请列出与当前故障相关的安全操作要求和注意事项。""",

    "metrics": """你是设备状态分析专家。根据设备实时运行数据，分析当前状态是否存在异常。
指出哪些参数偏离了正常范围。""",

    "log": """你是日志分析专家。分析设备运行日志，建立异常事件时间线。
识别关键事件的前后关联关系。""",

    "ticket": """你是工单分析专家。查询历史缺陷工单，判断当前故障是否有历史相似案例。
分析历史处理方案的参考价值。""",

    "risk_review": """你是风险审核专家。审核诊断建议的安全性、可行性和合规性。
指出潜在风险和改进建议。""",
}


@dataclass
class SubagentTask:
    name: str
    result: str = ""
    error: str = ""
    success: bool = False
    elapsed: float = 0.0


class SubagentExecutor:
    """子 Agent 并行执行器"""

    async def execute_parallel(self, names: list[str], context: str,
                               tool_results: dict[str, Any] = None) -> list[SubagentTask]:
        tasks = []
        for name in names:
            prompt = SUBAGENT_PROMPTS.get(name, "分析以下内容。")
            tasks.append(self._run_subagent(name, prompt, context, tool_results))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        output = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                output.append(SubagentTask(name=names[i], error=str(r), success=False))
            else:
                output.append(r)
        return output

    async def _run_subagent(self, name: str, system_prompt: str, context: str,
                            tool_results: dict[str, Any] = None) -> SubagentTask:
        import concurrent.futures
        start = time.time()
        try:
            user_prompt = context
            if tool_results and name in tool_results:
                user_prompt += f"\n\n工具查询结果:\n{tool_results[name]}"
            loop = asyncio.get_event_loop()
            result_text = await loop.run_in_executor(
                None, lambda: llm.chat(system_prompt, user_prompt, temperature=0.1, max_tokens=1024)
            )
            return SubagentTask(name=name, result=result_text, success=True, elapsed=time.time() - start)
        except Exception as e:
            return SubagentTask(name=name, error=str(e), success=False, elapsed=time.time() - start)
