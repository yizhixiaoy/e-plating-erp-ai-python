"""请求认证中间件 - 解析Java网关透传的用户上下文"""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.models.schemas import UserContext
import logging

logger = logging.getLogger(__name__)

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
        username = request.headers.get("X-Username", "")
        nickname = request.headers.get("X-Nickname", "")
        roles = [r for r in request.headers.get("X-Roles", "").split(",") if r] if request.headers.get("X-Roles") else []
        permissions = [p for p in request.headers.get("X-Permissions", "").split(",") if p] if request.headers.get("X-Permissions") else []
        data_scope = request.headers.get("X-Data-Scope", "NONE")
        auth_mode = request.headers.get("X-Auth-Mode", "guest")

        # 调试日志：记录接收到的权限
        logger.info(f"AI认证中间件 - 用户: {username}, 角色数: {len(roles)}, 权限数: {len(permissions)}")
        if permissions:
            logger.debug(f"AI认证中间件 - 权限列表: {permissions}")

        # 访客模式路径校验
        if auth_mode == "guest" and path not in GUEST_ALLOWED_PATHS:
            raise HTTPException(status_code=401, detail="请先登录后使用完整AI功能")

        # 构建用户上下文并注入到request.state
        user_context = UserContext(
            tenant_id=int(tenant_id),
            user_id=int(user_id),
            username=username,
            nickname=nickname,
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
