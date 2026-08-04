"""API 嵌入服务 — 通义千问 DashScope 嵌入 + DeepSeek 重排序

嵌入: DashScope text-embedding-v3 (OpenAI兼容接口)
重排: DeepSeek (chat-based 评分)
降级: 无 API 时自动用本地 BCE 模型或 BM25
"""

import logging
from typing import Optional

from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)

_ds_client: Optional[OpenAI] = None
_qw_client: Optional[OpenAI] = None


def _get_deepseek() -> Optional[OpenAI]:
    global _ds_client
    if not settings.deepseek_api_key:
        return None
    if _ds_client is None:
        _ds_client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
    return _ds_client


def _get_dashscope() -> Optional[OpenAI]:
    global _qw_client
    if not settings.dashscope_api_key:
        return None
    if _qw_client is None:
        _qw_client = OpenAI(
            api_key=settings.dashscope_api_key,
            base_url=settings.qwen_base_url,
        )
    return _qw_client


def api_embed(texts: list[str]) -> Optional[list[list[float]]]:
    return None


def api_rerank_scores(query: str, documents: list[str]) -> Optional[list[float]]:
    client = _get_deepseek()
    if not client:
        return None
    try:
        scores = []
        for doc in documents:
            prompt = (
                "评估以下文档与查询的相关性，仅输出0到1之间的分数，不要解释。\n"
                f"查询: {query}\n文档: {doc[:500]}\n分数: "
            )
            resp = client.chat.completions.create(
                model=settings.deepseek_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=10,
            )
            text = resp.choices[0].message.content.strip()
            try:
                score = float(text)
                scores.append(max(0.0, min(1.0, score)))
            except ValueError:
                scores.append(0.5)
        return scores
    except Exception:
        return None


def is_api_available() -> bool:
    return bool(settings.deepseek_api_key or settings.dashscope_api_key)
