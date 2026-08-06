"""统一异常定义"""
from typing import Optional


class AppError(Exception):
    def __init__(self, code: int, message: str, detail: Optional[dict] = None):
        self.code = code
        self.message = message
        self.detail = detail
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, resource: str, identifier: str = ""):
        msg = f"{resource} 不存在" + (f": {identifier}" if identifier else "")
        super().__init__(404, msg)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "未登录或登录已过期"):
        super().__init__(401, message)


class ForbiddenError(AppError):
    def __init__(self, message: str = "无权限访问"):
        super().__init__(403, message)


class ValidationError(AppError):
    def __init__(self, message: str):
        super().__init__(422, message)


class ServiceUnavailableError(AppError):
    def __init__(self, service: str = ""):
        msg = f"服务暂不可用" + (f": {service}" if service else "")
        super().__init__(503, msg)
