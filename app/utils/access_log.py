"""请求日志审计中间件"""
import time
import logging
from fastapi import Request
from fastapi.responses import Response

logger = logging.getLogger("access")


async def access_log_middleware(request: Request, call_next):
    t0 = time.perf_counter()
    response: Response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - t0) * 1000)

    client_ip = request.client.host if request.client else "-"
    method = request.method
    path = request.url.path
    status = response.status_code

    logger.info(
        f"{client_ip} {method} {path} {status} {elapsed_ms}ms"
    )
    return response
