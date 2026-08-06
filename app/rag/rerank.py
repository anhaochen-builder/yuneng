"""重排序服务 — BGE CrossEncoder 精排 + 关键词匹配降级

管道: 向量检索 + BM25 → RRF融合(Top-20) → BGE Reranker精排 → Top-5
模型: BAAI/bge-reranker-v2-m3 (CrossEncoder 交叉编码)
降级: 模型不可用时自动回退到关键词匹配方案
"""

import logging
import os
import re
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

RERANK_MODEL_NAME: str = settings.rerank_model_name
_cross_encoder: Optional[object] = None
_model_load_attempted: bool = False
_model_available: bool = False


def _cached_path(model_name: str) -> str | None:
    import os as _os
    org, name = model_name.split("/")
    base = _os.path.expanduser("~/.cache/huggingface/hub")
    for entry in _os.scandir(base):
        if entry.is_dir() and entry.name.startswith(f"models--{org}--{name}"):
            snapshots = _os.path.join(entry.path, "snapshots")
            if _os.path.isdir(snapshots):
                for snap in _os.scandir(snapshots):
                    if snap.is_dir():
                        return snap.path
    return None


def _load_rerank_model():
    global _cross_encoder, _model_load_attempted, _model_available
    if _model_load_attempted:
        return
    _model_load_attempted = True
    try:
        if settings.hf_endpoint:
            os.environ.setdefault("HF_ENDPOINT", settings.hf_endpoint)
        from sentence_transformers import CrossEncoder

        model_path = _cached_path(RERANK_MODEL_NAME)
        if model_path:
            _cross_encoder = CrossEncoder(model_path, trust_remote_code=True, local_files_only=True)
        else:
            _cross_encoder = CrossEncoder(RERANK_MODEL_NAME, trust_remote_code=True)
        _cross_encoder.predict([("测试", "测试")])
        _model_available = True
        logger.info(f"BCE Reranker 模型已加载: {RERANK_MODEL_NAME}")
    except Exception as e:
        _model_available = False
        logger.warning(f"BCE Reranker 加载失败，降级关键词方案: {e}")


def is_reranker_available() -> bool:
    return _model_available


class BGECrossEncoderReranker:
    """BGE CrossEncoder 交叉编码精排器

    将查询和文档拼接后完整送入 Transformer 进行深层语义交互，
    相比双塔模型的向量检索，精度更高但速度较慢。
    """

    @staticmethod
    def rerank(query: str, results: list[dict], top_k: int = 5) -> list[dict]:
        if not results:
            return results

        _load_rerank_model()
        if _model_available:
            return _bge_rerank(query, results, top_k)

        api_reranked = _api_rerank(query, results, top_k)
        if api_reranked:
            return api_reranked

        return _keyword_rerank(query, results, top_k)


def _bge_rerank(query: str, results: list[dict], top_k: int = 5) -> list[dict]:
    texts = [r.get("text", "") for r in results]
    pairs = [(query, t) for t in texts]

    try:
        scores = _cross_encoder.predict(pairs, show_progress_bar=False)
    except Exception as e:
        logger.warning(f"BCE Reranker 推理失败，降级: {e}")
        api_result = _api_rerank(query, results, top_k)
        return api_result or _keyword_rerank(query, results, top_k)

    scored = list(zip(scores, results))
    scored.sort(key=lambda x: x[0], reverse=True)

    reranked = []
    for score, doc in scored[:top_k]:
        doc["rerank_score"] = float(score)
        reranked.append(doc)

    return reranked


def _api_rerank(query: str, results: list[dict], top_k: int = 5) -> list[dict] | None:
    try:
        from app.rag.api_embed import api_rerank_scores
        texts = [r.get("text", "") for r in results]
        scores = api_rerank_scores(query, texts)
        if not scores:
            return None
        scored = list(zip(scores, results))
        scored.sort(key=lambda x: x[0], reverse=True)
        reranked = []
        for score, doc in scored[:top_k]:
            doc["rerank_score"] = float(score)
            reranked.append(doc)
        return reranked
    except Exception as e:
        logger.debug(f"API 重排降级: {e}")
        return None


def _keyword_rerank(query: str, results: list[dict], top_k: int = 5) -> list[dict]:
    """关键词匹配降级方案"""
    scored = []
    for doc in results:
        text = doc.get("text", "")
        overlap = _compute_keyword_overlap(query, text)
        length_bonus = 0.1 if 100 < len(text) < 2000 else 0.0
        rrf_score = doc.get("rrf_score", 0)
        score = overlap * 0.5 + length_bonus + rrf_score * 0.1
        doc["rerank_score"] = round(score, 4)
        scored.append((score, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [doc for _, doc in scored[:top_k]]


def _compute_keyword_overlap(query: str, text: str) -> float:
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


# 保持向后兼容
RerankService = BGECrossEncoderReranker

_reranker_instance: Optional[BGECrossEncoderReranker] = None


def get_reranker() -> BGECrossEncoderReranker:
    global _reranker_instance
    if _reranker_instance is None:
        _reranker_instance = BGECrossEncoderReranker()
    return _reranker_instance
