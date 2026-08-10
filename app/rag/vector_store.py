"""Chroma 向量存储 — BCE 本地模型 + DeepSeek API 嵌入双模式

本地: maidalun1020/bce-embedding-base_v1 (768维, SentenceTransformer)
API:  DeepSeek API 嵌入 (openai embeddings endpoint)
降级: 纯 BM25 关键词检索
"""

import logging
import os
import threading
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings

from app.config import settings as app_settings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL_NAME: str = app_settings.embedding_model_name
_embedding_fn: Optional[object] = None
_embedding_available: bool = False
_embedding_checked: bool = False
_chroma_client = None
_chroma_lock = threading.Lock()


def _try_load_embedding():
    global _embedding_fn, _embedding_available, _embedding_checked
    if _embedding_checked:
        return
    _embedding_checked = True
    try:
        if app_settings.hf_endpoint:
            os.environ.setdefault("HF_ENDPOINT", app_settings.hf_endpoint)
        from sentence_transformers import SentenceTransformer

        cached = _cached_model_path(EMBEDDING_MODEL_NAME)
        if cached:
            _embedding_fn = SentenceTransformer(cached, device="cpu", local_files_only=True)
        else:
            _embedding_fn = SentenceTransformer(EMBEDDING_MODEL_NAME, device="cpu")
        _embedding_fn.encode(["测试"], show_progress_bar=False)
        _embedding_available = True
        logger.info(f"BCE 嵌入模型已加载: {EMBEDDING_MODEL_NAME}")
    except Exception as e:
        _embedding_available = False
        logger.warning(f"BCE 嵌入加载失败，降级: {e}")


def _cached_model_path(model_name: str) -> str | None:
    org, name = model_name.split("/")
    base = os.path.expanduser("~/.cache/huggingface/hub")
    for entry in os.scandir(base):
        if entry.is_dir() and entry.name.startswith(f"models--{org}--{name}"):
            snapshots = os.path.join(entry.path, "snapshots")
            if os.path.isdir(snapshots):
                for snap in os.scandir(snapshots):
                    if snap.is_dir():
                        return snap.path
    return None


def is_embedding_available() -> bool:
    _try_load_embedding()
    return _embedding_available


def _embed_texts(texts: list[str]) -> Optional[list[list[float]]]:
    if not _embedding_fn or not _embedding_available:
        return None
    try:
        embs = _embedding_fn.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        return embs.tolist()
    except Exception as e:
        logger.warning(f"嵌入编码失败: {e}")
        return None


def get_chroma_client() -> chromadb.PersistentClient:
    global _chroma_client
    if _chroma_client is None:
        with _chroma_lock:
            if _chroma_client is None:
                persist_dir = Path(app_settings.vector_db_path)
                persist_dir.mkdir(parents=True, exist_ok=True)
                _chroma_client = chromadb.PersistentClient(
                    path=str(persist_dir),
                    settings=Settings(anonymized_telemetry=False),
                )
    return _chroma_client


def get_collection(name: str = "power_knowledge"):
    return get_chroma_client().get_or_create_collection(name=name)


def search_vector(query: str, collection_name: str = "power_knowledge", top_k: int = 10) -> list[dict]:
    if is_embedding_available():
        local = _search_local_vector(query, collection_name, top_k)
        if local:
            return local
    return _search_api_vector(query, top_k)


def _search_local_vector(query: str, collection_name: str, top_k: int) -> list[dict]:
    query_emb = _embed_texts([query])
    if not query_emb:
        return []
    try:
        collection = get_collection(collection_name)
        results = collection.query(query_embeddings=query_emb, n_results=top_k)
        docs = []
        if results.get("ids") and len(results["ids"]) > 0:
            for i, doc_id in enumerate(results["ids"][0]):
                distance = results.get("distances", [[]])[0][i] if results.get("distances") else 0
                docs.append({
                    "id": doc_id,
                    "text": results.get("documents", [[""]])[0][i] if results.get("documents") else "",
                    "metadata": results.get("metadatas", [[{}]])[0][i] if results.get("metadatas") else {},
                    "score": round(1.0 / (1.0 + distance), 4),
                    "source": "vector",
                })
        return docs
    except Exception as e:
        logger.debug(f"本地向量检索失败: {e}")
        return []


def _search_api_vector(query: str, top_k: int) -> list[dict]:
    try:
        from app.rag.api_embed import api_embed
        from app.rag.hybrid_search import get_knowledge_store
        all_docs = get_knowledge_store().search(query, top_k=20)
        if not all_docs:
            return []
        texts = [d.get("text", "") for d in all_docs]
        query_emb = api_embed([query])
        doc_embs = api_embed(texts)
        if not query_emb or not doc_embs:
            return []
        import numpy as np
        q = np.array(query_emb[0])
        results = []
        for i, d in enumerate(all_docs):
            if i < len(doc_embs):
                sim = float(q @ np.array(doc_embs[i]).T)
                d["score"] = round(sim, 4)
                d["source"] = "api_vector"
                results.append(d)
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return results[:top_k]
    except Exception as e:
        logger.debug(f"API 嵌入降级: {e}")
        return []


def add_documents(texts: list[str], metadatas: list[dict] = None, ids: list[str] = None,
                  collection_name: str = "power_knowledge") -> int:
    if not texts:
        return 0
    if ids is None:
        ids = [f"doc_{hash(t)}_{i}" for i, t in enumerate(texts)]
    if metadatas is None:
        metadatas = [{} for _ in texts]
    embeddings = _embed_texts(texts)
    try:
        collection = get_collection(collection_name)
        if embeddings:
            collection.add(documents=texts, embeddings=embeddings, metadatas=metadatas, ids=ids)
        else:
            collection.add(documents=texts, metadatas=metadatas, ids=ids)
        logger.info(f"已向量化 {len(texts)} 条文档到 {collection_name}")
        return len(texts)
    except Exception as e:
        logger.warning(f"添加文档失败: {e}")
        return 0
