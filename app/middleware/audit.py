"""操作审计中间件"""
import time
import asyncpg
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from app.config import settings


class AuditMiddleware(BaseHTTPMiddleware):
    """审计中间件：记录AI操作的审计日志"""

    def __init__(self, app, db_pool: asyncpg.Pool = None):
        super().__init__(app)
        self.db_pool = db_pool

    async def dispatch(self, request: Request, call_next):
        if not settings.AUDIT_ENABLED:
            return await call_next(request)

        start_time = time.time()
        response = await call_next(request)
        duration_ms = int((time.time() - start_time) * 1000)

        # 仅记录AI相关路径
        if request.url.path.startswith("/api/ai/") and self.db_pool:
            await self._log(request, response, duration_ms)

        return response

    async def _log(self, request: Request, response, duration_ms: int):
        """写入审计日志"""
        try:
            user_context = getattr(request.state, "user_context", None)
            if not user_context:
                return

            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO ai_audit_log
                       (tenant_id, user_id, action, target_type, duration_ms, ip_address, created_by, created_at, updated_at)
                       VALUES ($1, $2, $3, $4, $5, $6, $2, NOW(), NOW())""",
                    user_context.tenant_id,
                    user_context.user_id,
                    request.url.path,
                    request.method,
                    duration_ms,
                    request.client.host if request.client else ""
                )
        except Exception:
            pass  # 审计失败不影响业务
