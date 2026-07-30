"""驭能 — FastAPI 主入口"""

import logging
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.api import chat, diagnosis, alarm, knowledge, feedback, trace, scada

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="驭能 - 新能源场站非计划停机智能诊断系统",
    description="基于 DeepSeek V4 Pro + Hermes + OpenCode 的智能诊断平台",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================================================================
# 统一异常处理
# ================================================================

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "data": None,
            "message": exc.detail or "请求错误",
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    detail = errors[0].get("msg", "参数校验失败") if errors else "参数校验失败"
    return JSONResponse(
        status_code=422,
        content={
            "code": 422,
            "data": {"errors": errors},
            "message": detail,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"未处理的异常: {exc}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "data": None,
            "message": f"服务器内部错误: {str(exc)}",
        },
    )

# ================================================================
# 路由注册
# ================================================================

app.include_router(chat.router)
app.include_router(diagnosis.router)
app.include_router(alarm.router)
app.include_router(knowledge.router)
app.include_router(feedback.router)
app.include_router(trace.router)
app.include_router(scada.router)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "yuneng",
        "version": "1.0.0",
        "model": settings.deepseek_model,
    }


@app.get("/api/tools/list")
async def list_tools():
    from app.tools.registry import tool_registry
    return tool_registry.list_all()


@app.get("/api/tools/search")
async def search_tools(keyword: str = ""):
    from app.tools.registry import tool_registry
    return tool_registry.search(keyword)


@app.get("/api/skills")
async def list_skills():
    from app.skill.registry import skill_registry
    return skill_registry.list_all()


# 静态文件（前端）
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    logger.info(f"驭能 启动: http://{settings.api_host}:{settings.api_port}")
    uvicorn.run("app.main:app", host=settings.api_host, port=settings.api_port, reload=True)
