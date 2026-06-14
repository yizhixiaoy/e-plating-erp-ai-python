"""Java后端HTTP客户端 - 统一管理认证、Schema缓存和401处理"""
import json
import logging
import httpx

from app.config import settings
from app.services.cache import get_or_set, CacheNS

logger = logging.getLogger(__name__)

# ── Schema缓存（Redis优先，内存降级，TTL 5分钟） ──
_SCHEMA_TTL = 300


async def get_cached_schema(auth_headers: dict = None) -> list[dict]:
    """获取可查询的数据库Schema（优先Redis缓存，降级内存缓存）

    Returns:
        [{"name": "sys_user", "label": "系统用户表", "fields": ["id", "username", ...]}, ...]
    """
    schema = await get_or_set(
        namespace=CacheNS.SCHEMA,
        key="tables",
        factory=lambda: _fetch_schema_from_java(auth_headers),
        ttl=_SCHEMA_TTL
    )
    return schema if isinstance(schema, list) else []


def build_schema_description(schema: list[dict]) -> str:
    """将Schema格式化为LLM可读的文本描述"""
    if not schema:
        return "（未能获取数据库Schema，请使用常见表名）"

    lines = ["可查询的数据库表及字段："]
    for t in schema:
        name = t.get("name", "")
        label = t.get("label", name)
        fields = t.get("fields", [])
        fields_str = ", ".join(fields[:15])
        if len(fields) > 15:
            fields_str += f", ...(共{len(fields)}个字段)"
        lines.append(f"- `{name}` ({label}): {fields_str}")
    return "\n".join(lines)


async def _fetch_schema_from_java(auth_headers: dict = None) -> list[dict]:
    """从Java端动态获取可查询的表结构（异步回源工厂）"""
    try:
        async with _build_client(auth_headers) as client:
            response = await client.get(f"{settings.JAVA_API_BASE_URL}/api/v1/ai/schema")
            if response.status_code == 200:
                tables = response.json().get("tables", [])
                logger.info("[java_client] Schema获取成功: %d张表", len(tables))
                return tables
            logger.warning("[java_client] Schema获取失败 HTTP %d: %s", response.status_code, response.text)
    except Exception as e:
        logger.warning("[java_client] Schema获取异常: %s", e)
    return []


# ── 共享HTTP客户端（统一401处理） ──

def _build_client(auth_headers: dict = None) -> httpx.AsyncClient:
    """构建带认证头的共享httpx客户端

    所有Python→Java HTTP请求统一通过此方法创建客户端，
    401错误由调用方统一处理。
    """
    headers = {
        "X-Internal-Api-Key": settings.JAVA_API_KEY,
    }
    if auth_headers:
        # 将Python内部key映射为Java InternalApiKeyFilter期望的Header名
        key_mapping = {
            "tenant_id": "X-Tenant-Id",
            "user_id": "X-User-Id",
            "data_scope": "X-Data-Scope",
            "authorization": "Authorization",
        }
        for py_key, java_header in key_mapping.items():
            if py_key in auth_headers:
                headers[java_header] = str(auth_headers[py_key])
    return httpx.AsyncClient(
        base_url=settings.JAVA_API_BASE_URL,
        timeout=settings.JAVA_API_TIMEOUT,
        headers=headers
    )


async def java_post(
    path: str,
    json_body: dict,
    auth_headers: dict = None,
    timeout: int = None
) -> dict:
    """向Java后端发起POST请求（统一入口，集中处理401）

    Args:
        path: 请求路径（如 /api/v1/ai/data-query）
        json_body: 请求体
        auth_headers: 认证头（由chat端点注入的用户上下文）
        timeout: 超时秒数（默认使用全局配置）

    Returns:
        {"success": True, "data": {...}} 或 {"success": False, "error": "..."}
    """
    t = timeout or settings.JAVA_API_TIMEOUT
    try:
        async with _build_client(auth_headers) as client:
            response = await client.post(path, json=json_body, timeout=t)

        if response.status_code == 200:
            return {"success": True, "data": response.json()}

        if response.status_code == 401:
            logger.warning("[java_client] 401 Token过期: path=%s", path)
            return {
                "success": False,
                "error": "认证已过期，请重新登录",
                "code": 401
            }

        logger.warning("[java_client] 请求失败: path=%s, HTTP %d: %s", path, response.status_code, response.text)
        return {
            "success": False,
            "error": f"请求失败(HTTP {response.status_code})",
            "code": response.status_code
        }

    except httpx.TimeoutException:
        logger.error("[java_client] 请求超时: path=%s, timeout=%ds", path, t)
        return {"success": False, "error": f"请求超时（{t}秒）", "code": 408}
    except httpx.ConnectError as e:
        logger.error("[java_client] 连接失败: path=%s, err=%s", path, e)
        return {"success": False, "error": "无法连接业务数据库服务，请稍后重试", "code": 503}
    except Exception as e:
        logger.error("[java_client] 请求异常: path=%s, err=%s", path, e)
        return {"success": False, "error": str(e), "code": 500}


async def java_get(
    path: str,
    auth_headers: dict = None,
    timeout: int = None
) -> dict:
    """向Java后端发起GET请求（统一入口）"""
    t = timeout or settings.JAVA_API_TIMEOUT
    try:
        async with _build_client(auth_headers) as client:
            response = await client.get(path, timeout=t)

        if response.status_code == 200:
            return {"success": True, "data": response.json()}

        if response.status_code == 401:
            return {"success": False, "error": "认证已过期，请重新登录", "code": 401}

        return {
            "success": False,
            "error": f"请求失败(HTTP {response.status_code})",
            "code": response.status_code
        }

    except httpx.TimeoutException:
        return {"success": False, "error": f"请求超时（{t}秒）", "code": 408}
    except httpx.ConnectError as e:
        logger.error("[java_client] 连接失败: path=%s, err=%s", path, e)
        return {"success": False, "error": "无法连接业务数据库服务", "code": 503}
    except Exception as e:
        logger.error("[java_client] 请求异常: path=%s, err=%s", path, e)
        return {"success": False, "error": str(e), "code": 500}
