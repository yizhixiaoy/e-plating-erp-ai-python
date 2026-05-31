"""请求认证中间件 - 解析Java网关透传的用户上下文"""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.models.schemas import UserContext


GUEST_ALLOWED_PATHS = {"/api/ai/chat"}


class AuthMiddleware(BaseHTTPMiddleware):
    """认证中间件：从请求Header中提取用户上下文"""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 健康检查跳过认证
        if path in ("/health", "/api/ai/health"):
            return await call_next(request)

        # 提取用户上下文
        tenant_id = request.headers.get("X-Tenant-Id", "0")
        user_id = request.headers.get("X-User-Id", "0")
        roles = request.headers.get("X-Roles", "").split(",") if request.headers.get("X-Roles") else []
        permissions = request.headers.get("X-Permissions", "").split(",") if request.headers.get("X-Permissions") else []
        data_scope = request.headers.get("X-Data-Scope", "NONE")
        auth_mode = request.headers.get("X-Auth-Mode", "guest")

        # 访客模式路径校验
        if auth_mode == "guest" and path not in GUEST_ALLOWED_PATHS:
            raise HTTPException(status_code=401, detail="请先登录后使用完整AI功能")

        # 构建用户上下文并注入到request.state
        user_context = UserContext(
            tenant_id=int(tenant_id),
            user_id=int(user_id),
            roles=roles,
            permissions=permissions,
            data_scope=data_scope,
            auth_mode=auth_mode
        )

        request.state.user_context = user_context
        request.state.auth_headers = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "roles": ",".join(roles),
            "permissions": ",".join(permissions),
            "data_scope": data_scope,
            "authorization": request.headers.get("Authorization", "")
        }

        response = await call_next(request)
        return response
