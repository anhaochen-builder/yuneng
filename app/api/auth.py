"""认证 API — /api/auth"""
import os
import logging
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from app.utils.auth import authenticate, register_user, verify_token, get_user, TokenPayload

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)

AUTH_WHITELIST = {
    "/health", "/api/auth/login", "/api/auth/register", "/api/dashboard",
    "/docs", "/redoc", "/openapi.json", "/favicon.ico", "/assets/", "/ws/",
    "/api/skills", "/api/tools/list", "/api/tools/search",
    "/api/knowledge/health", "/api/alarm/health", "/api/scada/health",
    "/api/external/webhook/alarm", "/api/external/webhook/test", "/api/external/alarms",
    "/api/field/weather", "/api/field/safety-checklist", "/api/field/safety-rules",
    "/api/field/maintenance-window", "/api/field/shift-report", "/api/field/station-health",
}


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    password: str = Field(..., min_length=6)


class UserInfo(BaseModel):
    username: str
    role: str


async def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> UserInfo:
    if not credentials:
        raise HTTPException(401, "未登录")
    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(401, "登录已过期")
    return UserInfo(username=payload.username, role=payload.role)


def require_admin(user: UserInfo = Depends(get_current_user)) -> UserInfo:
    if user.role != "admin":
        raise HTTPException(403, "需要管理员权限")
    return user


async def auth_middleware(request: Request, call_next):
    path = request.url.path

    if not path.startswith("/api/"):
        return await call_next(request)

    if any(path == p or path.startswith(p) for p in AUTH_WHITELIST):
        return await call_next(request)

    if os.getenv("DISABLE_AUTH", "").lower() in ("1", "true", "yes"):
        request.state.user = {"username": "test", "role": "admin"}
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=401, content={"code": 401, "data": None, "message": "未登录"})

    token = auth_header[7:]
    payload = verify_token(token)
    if not payload:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=401, content={"code": 401, "data": None, "message": "登录已过期"})

    request.state.user = {"username": payload.username, "role": payload.role}
    return await call_next(request)


@router.post("/login")
async def login(req: LoginRequest):
    token = authenticate(req.username, req.password)
    if not token:
        raise HTTPException(401, "用户名或密码错误")
    user = get_user(req.username)
    return {"token": token, "user": user}


@router.post("/register")
async def register(req: RegisterRequest):
    if not register_user(req.username, req.password):
        raise HTTPException(409, "用户名已存在")
    token = authenticate(req.username, req.password)
    user = get_user(req.username)
    return {"token": token, "user": user}


@router.get("/me")
async def me(user: UserInfo = Depends(get_current_user)):
    return {"username": user.username, "role": user.role}
