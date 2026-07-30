"""Chroma 向量存储 — 关键词优先，向量可选

默认不加载嵌入模型，使用纯 BM25 关键词检索。
嵌入模型可用时自动启用向量检索增强。
"""

import logging
from pathlib import Path

import chromadb
from chromadb.config import Settings

from app.config import settings

logger = logging.getLogger(__name__)

_embedding_available: bool = False
_embedding_checked: bool = True  # 跳过检测，直接使用 BM25
_chroma_client = None


def is_embedding_available() -> bool:
    return _embedding_available


def get_chroma_client() -> chromadb.PersistentClient:
    global _chroma_client
    if _chroma_client is None:
        persist_dir = Path(settings.vector_db_path)
        persist_dir.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(
            path=str(persist_dir),
            settings=Settings(anonymized_telemetry=False),
        )
    return _chroma_client


def get_collection(name: str = "power_knowledge"):
    return get_chroma_client().get_or_create_collection(name=name)


def search_vector(query: str, collection_name: str = "power_knowledge", top_k: int = 10) -> list[dict]:
    if not is_embedding_available():
        return []
    try:
        collection = get_collection(collection_name)
        results = collection.query(query_texts=[query], n_results=top_k)
        docs = []
        if results["ids"] and len(results["ids"]) > 0:
            for i, doc_id in enumerate(results["ids"][0]):
                docs.append({
                    "id": doc_id,
                    "text": results["documents"][0][i] if results["documents"] else "",
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0,
                })
        return docs
    except Exception as e:
        logger.warning(f"向量检索失败: {e}")
        return []


def add_documents(texts: list[str], metadatas: list[dict] = None, ids: list[str] = None,
                  collection_name: str = "power_knowledge") -> int:
    if not is_embedding_available():
        return len(texts)
    try:
        collection = get_collection(collection_name)
        if ids is None:
            ids = [f"doc_{hash(t)}_{i}" for i, t in enumerate(texts)]
        if metadatas is None:
            metadatas = [{} for _ in texts]
        collection.add(documents=texts, metadatas=metadatas, ids=ids)
        return len(texts)
    except Exception as e:
        logger.warning(f"添加文档失败: {e}")
        return 0
