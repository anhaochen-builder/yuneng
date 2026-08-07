"""驭能 — FastAPI 主入口"""

import logging
import sys
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.api import chat, diagnosis, alarm, knowledge, feedback, trace, scada, dashboard, audit, workorder
from app.api import benchmark_api, rlhf_api, auth, websocket, settings_api
from app.api import external, automation, field_api
from app.api.rate_limit import rate_limit_middleware
from app.api.auth import auth_middleware
from app.utils.access_log import access_log_middleware
from app.utils.cache import get_cache
from app.utils.circuit_breaker import get_breaker

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.graph.sub_agent_init import register_all
    from app.graph.sub_agent import sub_agent_registry
    from app.skill.registry import skill_registry
    register_all()
    logger.info(f"所有子智能体已注册: {len(sub_agent_registry._agents)} 个 SubAgent, {len(skill_registry._skills)} 个 Skill")

    import asyncio as _asyncio
    import concurrent.futures as _futures

    def _prewarm_models():
        import logging as _logging
        _log = _logging.getLogger("prewarm")
        try:
            from app.rag.vector_store import _try_load_embedding
            _log.info("预热嵌入模型...")
            _try_load_embedding()
        except Exception as e:
            _log.warning(f"嵌入模型预热跳过: {e}")
        try:
            from app.rag.rerank import _load_rerank_model
            _log.info("预热重排序模型...")
            _load_rerank_model()
        except Exception as e:
            _log.warning(f"重排序预热跳过: {e}")

    loop = _asyncio.get_event_loop()
    executor = _futures.ThreadPoolExecutor(max_workers=1)
    loop.run_in_executor(executor, _prewarm_models)
    yield


app = FastAPI(
    title="驭能 - 新能源场站非计划停机智能诊断系统",
    description="基于 DeepSeek V4 Pro + Hermes + OpenCode 的智能诊断平台",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 限流中间件 — 每 IP 每分钟最多 60 请求
app.middleware("http")(rate_limit_middleware)

# JWT 认证中间件
app.middleware("http")(auth_middleware)

# 请求日志审计中间件
app.middleware("http")(access_log_middleware)


# Access log 单独文件输出
access_logger = logging.getLogger("access")
access_logger.setLevel(logging.INFO)
if not access_logger.handlers:
    fh = logging.FileHandler(Path(__file__).parent.parent / "logs" / "access.log")
    fh.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    access_logger.addHandler(fh)


# ================================================================
# 统一响应中间件 — {code, data, message}
# ================================================================

class UnifiedResponseMiddleware(BaseHTTPMiddleware):
    """将非流式 JSON 响应统一包装为 {code: 0, data: ..., message: 'success'}"""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        content_type = response.headers.get("content-type", "")
        # 跳过非 JSON 响应: 流式/HTML/静态资源
        if isinstance(response, StreamingResponse):
            return response
        if any(t in content_type for t in ("text/event-stream", "text/html", "text/css",
                "application/javascript", "image/", "font/", "application/octet-stream")):
            return response
        if request.url.path.startswith("/assets/"):
            return response
        if request.url.path in ("/openapi.json", "/docs", "/redoc", "/favicon.ico"):
            return response

        if 200 <= response.status_code < 300:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk

            if not body:
                return JSONResponse(
                    status_code=response.status_code,
                    content={"code": 0, "data": None, "message": "success"},
                )

            try:
                import json
                data = json.loads(body)
                # 已是标准格式则透传
                if isinstance(data, dict) and "code" in data and "data" in data:
                    return JSONResponse(
                        status_code=response.status_code,
                        content=data,
                    )
                return JSONResponse(
                    status_code=response.status_code,
                    content={"code": 0, "data": data, "message": "success"},
                )
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.warning(f"响应体解析失败: {e}")
                return JSONResponse(
                    status_code=response.status_code,
                    content={"code": 0, "data": body.decode("utf-8", errors="replace"), "message": "success"},
                )

        return response


app.add_middleware(UnifiedResponseMiddleware)

# ================================================================
# 统一异常处理
# ================================================================

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404 and "text/html" in request.headers.get("accept", ""):
        index_path = Path(__file__).parent.parent / "frontend" / "dist" / "index.html"
        if index_path.exists():
            from fastapi.responses import FileResponse
            return FileResponse(index_path, media_type="text/html")
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
app.include_router(dashboard.router)
app.include_router(audit.router)
app.include_router(workorder.router)
app.include_router(benchmark_api.router)
app.include_router(rlhf_api.router)
app.include_router(auth.router)
app.include_router(websocket.router)
app.include_router(settings_api.router)
app.include_router(external.router)
app.include_router(automation.router)
app.include_router(field_api.router)


@app.get("/health")
async def health():
    llm_status = "degraded"
    try:
        from app.agent.llm_provider import hybrid_llm
        llm_status = hybrid_llm.mode_status()["current"]
    except Exception:
        llm_status = "unknown"

    cache_stats = get_cache().stats

    return {
        "status": "healthy",
        "service": "yuneng",
        "version": "1.5.0",
        "model": settings.deepseek_model,
        "llm_provider": llm_status,
        "cache": cache_stats,
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
    skills = skill_registry.list_all()
    agents = skill_registry.list_agents()
    return {
        "skills": skills,
        "sub_agents": agents,
        "architecture": "Supervisor + 子智能体模式，6 个 SubAgent 由 Supervisor 统一调度",
    }


# 静态文件（前端构建产物）
frontend_path = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    logger.info(f"驭能 启动: http://{settings.api_host}:{settings.api_port}")
    uvicorn.run("app.main:app", host=settings.api_host, port=settings.api_port, reload=True)
