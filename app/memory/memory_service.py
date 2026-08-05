"""三层记忆服务 — 短期/工作/长期 + 时间衰减检索

短期: OrderedDict 内存 (会话级, 最近3轮)
工作: 任务状态字典 (任务级, 35状态键)
长期: ChromaDB 持久化 (永久级, 时间衰减)
"""

import logging
import math
from datetime import datetime, timedelta
from collections import OrderedDict
from typing import Any, Optional

logger = logging.getLogger(__name__)

LONG_TERM_COLLECTION = "long_term_memory"
DECAY_HALF_LIFE_DAYS = 180  # 半衰期: 半年


class MemoryService:
    """三层记忆管理"""

    def __init__(self):
        self._sessions: OrderedDict[str, dict] = OrderedDict()
        self._tasks: OrderedDict[str, dict] = OrderedDict()
        self._domain: dict[str, Any] = {}
        self._users: dict[str, dict] = {}

    # ================================================================
    # 短期记忆 (会话级)
    # ================================================================

    def init_session(self, session_id: str):
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "history": [],
                "created_at": datetime.now().isoformat(),
            }

    def save_to_session(self, session_id: str, user_msg: str, assistant_msg: str):
        self.init_session(session_id)
        self._sessions[session_id]["history"].append({
            "user": user_msg,
            "assistant": assistant_msg,
        })

    def get_session_history(self, session_id: str, n: int = 3) -> str:
        session = self._sessions.get(session_id, {})
        history_list = session.get("history", [])
        if not history_list:
            return ""
        return "\n".join([
            f"用户: {h.get('user', '')}\n助手: {h.get('assistant', '')}"
            for h in history_list[-n:]
        ])

    # ================================================================
    # 工作记忆 (任务级)
    # ================================================================

    def init_task(self, task_id: str, skill_context: str = ""):
        self._tasks[task_id] = {
            "skill_context": skill_context,
            "diagnosis_text": "",
            "created_at": datetime.now().isoformat(),
        }

    def save_task_diagnosis(self, task_id: str, diagnosis_text: str):
        if task_id in self._tasks:
            self._tasks[task_id]["diagnosis_text"] = diagnosis_text

    def get_task_context(self, task_id: str) -> dict:
        return self._tasks.get(task_id, {})

    # ================================================================
    # 长期记忆 (ChromaDB + 时间衰减)
    # ================================================================

    def save_long_term(
        self,
        text: str,
        metadata: dict[str, Any] = None,
        task_id: str = "",
    ) -> int:
        """将诊断案例向量化存入 ChromaDB 长期记忆"""
        try:
            from app.rag.vector_store import add_documents, is_embedding_available

            if not is_embedding_available():
                logger.debug("嵌入模型不可用，跳过长期记忆存储")
                return 0

            meta = metadata or {}
            meta.update({
                "task_id": task_id,
                "stored_at": datetime.now().isoformat(),
            })

            count = add_documents(
                texts=[text],
                metadatas=[meta],
                ids=[f"mem_{task_id}" if task_id else f"mem_{datetime.now().timestamp()}"],
                collection_name=LONG_TERM_COLLECTION,
            )
            if count > 0:
                logger.info(f"长期记忆已存储: task={task_id[:16] if task_id else 'N/A'}")

                if task_id in self._tasks:
                    self._tasks[task_id]["long_term_saved"] = True

            return count

        except Exception as e:
            logger.warning(f"长期记忆存储失败: {e}")
            return 0

    def search_long_term(
        self,
        query: str,
        top_k: int = 3,
        device_type: str = "",
    ) -> list[dict]:
        """检索长期记忆，带时间衰减加权"""
        try:
            from app.rag.vector_store import search_vector

            results = search_vector(query, collection_name=LONG_TERM_COLLECTION, top_k=top_k * 2)
            if not results:
                return []

            scored = []
            for doc in results:
                base_score = 1.0 - doc.get("distance", 0)

                meta = doc.get("metadata", {})
                stored_at = meta.get("stored_at", "")
                decay = MemoryService._time_decay(stored_at)

                bonus = 1.2 if device_type and meta.get("device_type") == device_type else 1.0
                final_score = base_score * decay * bonus
                scored.append((final_score, doc))

            scored.sort(key=lambda x: x[0], reverse=True)

            output = []
            for score, doc in scored[:top_k]:
                output.append({
                    "text": doc.get("text", ""),
                    "score": round(score, 4),
                    "metadata": doc.get("metadata", {}),
                })
            return output

        except Exception as e:
            logger.warning(f"长期记忆检索失败: {e}")
            return []

    @staticmethod
    def _time_decay(stored_at: str) -> float:
        """时间衰减: weight = 1 / (1 + days_since / half_life)

        半年前的案例权重降为原来的 50%
        """
        if not stored_at:
            return 0.5
        try:
            stored = datetime.fromisoformat(stored_at)
            days = (datetime.now() - stored).days
            return 1.0 / (1.0 + days / DECAY_HALF_LIFE_DAYS)
        except (ValueError, TypeError):
            return 0.5

    def delete_long_term(self, task_id: str) -> bool:
        """删除指定长期记忆"""
        try:
            from app.rag.vector_store import get_chroma_client
            client = get_chroma_client()
            collection = client.get_collection(LONG_TERM_COLLECTION)
            collection.delete(ids=[f"mem_{task_id}"])
            return True
        except Exception as e:
            logger.warning(f"删除长期记忆失败: {e}")
            return False

    def long_term_stats(self) -> dict:
        """长期记忆统计"""
        try:
            from app.rag.vector_store import get_chroma_client
            client = get_chroma_client()
            collection = client.get_or_create_collection(LONG_TERM_COLLECTION)
            return {"total": collection.count()}
        except (RuntimeError, ImportError) as e:
            logger.warning(f"长期记忆统计失败: {e}")
            return {"total": 0}

    # ================================================================
    # 代理上下文组装
    # ================================================================

    def build_context_for_agent(
        self, session_id: str = "", task_id: str = "", user_id: str = ""
    ) -> tuple[str, str, str]:
        session_ctx = self._sessions.get(session_id, {})
        task_ctx = self._tasks.get(task_id, {})
        user_ctx = self._users.get(user_id, {})
        domain_ctx = self._domain

        memory_parts = []
        if domain_ctx:
            memory_parts.append(
                "## 领域知识\n" + str(domain_ctx.get("knowledge", ""))[:500]
            )
        if user_ctx:
            memory_parts.append(
                "## 用户偏好\n" + str(user_ctx.get("preferences", ""))[:200]
            )

        history_text = self.get_session_history(session_id)
        skill_context = task_ctx.get("skill_context", "")
        return "\n".join(memory_parts), skill_context, history_text


_memory_instance = None


def get_memory() -> MemoryService:
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = MemoryService()
    return _memory_instance
