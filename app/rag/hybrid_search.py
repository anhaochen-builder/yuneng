"""Hybrid Search — 向量 + BM25 关键词融合检索"""

import logging
import math
from collections import defaultdict

from app.rag.vector_store import search_vector

logger = logging.getLogger(__name__)

POWER_KEYWORDS = [
    "电压", "电流", "功率", "频率", "温度", "振动", "故障", "告警",
    "逆变器", "风机", "变压器", "断路器", "保护", "接地", "短路", "过载",
    "通讯中断", "绝缘", "IGBT", "PLC", "SCADA", "齿轮箱", "叶片", "偏航",
    "变桨", "直流侧", "交流侧", "并网", "脱网", "低电压穿越", "高电压穿越",
    "AGC", "AVC", "无功补偿", "有功功率", "箱变", "集电线路", "SVG",
]


class BM25KeywordSearch:
    """简易 BM25 关键词检索"""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents: list[str] = []
        self.doc_len: list[int] = []
        self.avg_dl: float = 0
        self.term_freq: dict[str, int] = defaultdict(int)
        self.doc_freq: dict[str, int] = defaultdict(int)

    def index(self, documents: list[str]):
        self.documents = documents
        self.doc_len = [len(doc) for doc in documents]
        self.avg_dl = sum(self.doc_len) / max(len(self.doc_len), 1)
        self.term_freq.clear()
        self.doc_freq.clear()
        for doc in documents:
            terms = set(self._tokenize(doc))
            for term in terms:
                self.doc_freq[term] += 1

    def _tokenize(self, text: str) -> list[str]:
        tokens = []
        for kw in POWER_KEYWORDS:
            if kw in text:
                tokens.append(kw)
        for char in text:
            if "\u4e00" <= char <= "\u9fff":
                tokens.append(char)
        return tokens

    def search(self, query: str, top_k: int = 10) -> list[tuple[int, float]]:
        query_terms = self._tokenize(query)
        if not query_terms:
            return []
        scores = []
        n = len(self.documents)
        for i, doc in enumerate(self.documents):
            score = 0.0
            for term in query_terms:
                if term not in self.doc_freq:
                    continue
                tf = doc.count(term)
                df = self.doc_freq[term]
                idf = math.log((n - df + 0.5) / (df + 0.5) + 1)
                dl = self.doc_len[i]
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * dl / max(self.avg_dl, 1))
                score += idf * numerator / max(denominator, 0.1)
            if score > 0:
                scores.append((i, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


class HybridSearchService:
    """向量 + 关键词混合检索"""

    def __init__(self):
        self.bm25 = BM25KeywordSearch()
        self._indexed_docs: list[str] = []

    def _rrf_fusion(self, vector_results: list[dict], keyword_results: list[tuple[int, float]],
                    vector_weight: float = 1.0, keyword_weight: float = 1.0, k: int = 60) -> list[dict]:
        """RRF 融合算法"""
        scores: dict[str, float] = {}
        doc_map: dict[str, dict] = {}
        for rank, doc in enumerate(vector_results):
            doc_id = doc["id"]
            scores[doc_id] = scores.get(doc_id, 0) + vector_weight / (rank + k)
            doc_map[doc_id] = doc
        for rank, (doc_idx, _) in enumerate(keyword_results):
            doc_id = f"keyword_{doc_idx}"
            scores[doc_id] = scores.get(doc_id, 0) + keyword_weight / (rank + k)
            if doc_idx < len(self._indexed_docs):
                doc_map[doc_id] = {
                    "id": doc_id,
                    "text": self._indexed_docs[doc_idx],
                    "metadata": {"source": "keyword"},
                    "distance": 0,
                }
        sorted_ids = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        results = []
        for doc_id, score in sorted_ids:
            if doc_id in doc_map:
                doc = doc_map[doc_id]
                doc["rrf_score"] = score
                results.append(doc)
        return results

    def search(self, query: str, top_k: int = 10, use_reranker: bool = True) -> list[dict]:
        """混合检索 + 可选精排

        Args:
            query: 查询文本
            top_k: 最终返回数量
            use_reranker: 是否使用 BGE Reranker 精排
        """
        vector_results = search_vector(query, top_k=max(top_k * 2, 20))
        keyword_results = self.bm25.search(query, top_k=max(top_k * 2, 20))

        if not vector_results and not keyword_results:
            return []

        fused = self._rrf_fusion(vector_results, keyword_results)

        if not use_reranker:
            return fused[:top_k]

        from app.rag.rerank import BGECrossEncoderReranker
        reranker_top_k = min(top_k, len(fused))
        return BGECrossEncoderReranker.rerank(query, fused, top_k=reranker_top_k)

    def index_keywords(self, documents: list[str]):
        self._indexed_docs = documents
        self.bm25.index(documents)
