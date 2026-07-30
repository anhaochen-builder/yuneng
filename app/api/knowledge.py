"""知识库 API — /api/knowledge"""

import logging
import uuid
from pathlib import Path
from tempfile import SpooledTemporaryFile

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from app.models.schemas import KnowledgeUploadResult
from app.rag.document_parser import DocumentParser
from app.rag.vector_store import add_documents

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form("通用"),
    description: str = Form(""),
    tags: str = Form(""),
):
    ext = Path(file.filename).suffix.lower()
    if ext not in (".pdf", ".docx", ".xlsx", ".xls", ".txt", ".md"):
        raise HTTPException(400, f"不支持的格式: {ext}")

    content = await file.read()
    temp_path = Path("/tmp") / f"{uuid.uuid4()}{ext}"
    with open(temp_path, "wb") as f:
        f.write(content)

    try:
        chunks = DocumentParser.parse(str(temp_path))
        if not chunks:
            raise HTTPException(400, "文档无法解析或内容为空")

        texts = [c["text"] for c in chunks]
        metadatas = [{
            "source": file.filename,
            "page": c.get("page", 0),
            "type": c.get("type", ext),
            "document_type": document_type,
            "tags": tags,
        } for c in chunks]

        count = add_documents(texts, metadatas)
        logger.info(f"文档入库: {file.filename}, {count} 个分块")

        temp_path.unlink(missing_ok=True)
        return KnowledgeUploadResult(
            document_id=str(uuid.uuid4()),
            filename=file.filename,
            chunk_count=count,
            status="INDEXED",
        )
    except Exception as e:
        temp_path.unlink(missing_ok=True)
        raise HTTPException(500, f"文档处理失败: {str(e)}")


@router.post("/search/test")
async def search_test(req: dict):
    from app.rag.hybrid_search import HybridSearchService
    query = req.get("query", "")
    top_k = req.get("topK", 5)

    searcher = HybridSearchService()
    results = searcher.search(query, top_k=top_k)
    return {
        "query": query,
        "total": len(results),
        "results": [{"text": r["text"][:500], "score": r.get("rrf_score", 0)} for r in results],
    }


@router.get("/health")
async def health():
    return {"status": "ok", "service": "knowledge-base"}
