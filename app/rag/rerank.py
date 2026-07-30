"""重排序服务 — 关键词匹配精排

采用关键词重叠度 + RRF分数 + 文本长度加权排序。
不依赖任何本地模型，纯算法实现。
"""

import logging
import re

logger = logging.getLogger(__name__)


class RerankService:
    """关键词匹配精排器

    对 RRF 融合后的候选结果进行二次排序。
    """

    @staticmethod
    def rerank(query: str, results: list[dict], top_k: int = 5) -> list[dict]:
        if not results:
            return results

        scored = []
        for doc in results:
            text = doc.get("text", "")
            keyword_overlap = _compute_keyword_overlap(query, text)
            length_bonus = 0.1 if 100 < len(text) < 2000 else 0.0
            rrf_score = doc.get("rrf_score", 0)
            score = keyword_overlap * 0.5 + length_bonus + rrf_score * 0.1
            scored.append((score, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored[:top_k]]


BGECrossEncoderReranker = RerankService


def _compute_keyword_overlap(query: str, text: str) -> float:
    """计算查询与文档的关键词重叠度"""
    q_tokens = _tokenize(query)
    if not q_tokens:
        return 0.0
    d_tokens = _tokenize(text)
    overlap = len(q_tokens & d_tokens)
    return overlap / len(q_tokens)


def _tokenize(s: str) -> set[str]:
    tokens = set()
    for ch in s:
        if "\u4e00" <= ch <= "\u9fff":
            tokens.add(ch)
    for word in re.findall(r"[a-zA-Z0-9]+", s):
        tokens.add(word.lower())
    return tokens


def is_reranker_available() -> bool:
    return True


def _is_model_cached() -> bool:
    return False
