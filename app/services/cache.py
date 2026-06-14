"""统一Redis缓存服务 - 支持降级到内存缓存，透明容错"""
import asyncio
import json
import logging
import time
from typing import Any, Callable, Optional

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

# ── 模块级单例 ──
_redis: aioredis.Redis | None = None
_memory_cache: dict[str, tuple[Any, float]] = {}  # key -> (value, expire_ts)


async def get_redis() -> aioredis.Redis | None:
    """获取Redis连接（延迟初始化）"""
    global _redis
    if _redis is not None:
        return _redis
    return None


async def ensure_redis():
    """确保Redis连接就绪（由main.py lifespan调用）"""
    global _redis
    if _redis is not None:
        return
    try:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await _redis.ping()
        logger.info("[cache] Redis连接成功: %s", settings.REDIS_HOST)
    except Exception as e:
        logger.warning("[cache] Redis不可用(%s)，降级为内存缓存模式", e)
        _redis = None


async def close_redis():
    """关闭Redis连接"""
    global _redis, _memory_cache
    if _redis is not None:
        await _redis.close()
        _redis = None
        logger.info("[cache] Redis连接已关闭")
    _memory_cache.clear()


# ── Cache API ──


def _build_key(namespace: str, key: str) -> str:
    """构建完整的Redis key"""
    return f"{settings.REDIS_PREFIX}{namespace}:{key}"


async def get(namespace: str, key: str, default: Any = None) -> Any:
    """从缓存获取值

    Args:
        namespace: 命名空间（如 'schema', 'kb_list', 'conversation_list'）
        key: 缓存key
        default: 缓存未命中时的默认值

    Returns:
        缓存值或default
    """
    global _memory_cache

    full_key = _build_key(namespace, key)

    # 1. 优先Redis
    redis = await get_redis()
    if redis is not None:
        try:
            cached = await redis.get(full_key)
            if cached is not None:
                return json.loads(cached)
        except Exception:
            pass

    # 2. 降级内存缓存
    entry = _memory_cache.get(full_key)
    if entry is not None:
        value, expire_ts = entry
        if time.monotonic() < expire_ts:
            return value
        del _memory_cache[full_key]

    return default


async def set(
    namespace: str,
    key: str,
    value: Any,
    ttl: int = 300
) -> bool:
    """写入缓存

    Args:
        namespace: 命名空间
        key: 缓存key
        value: 值（自动JSON序列化）
        ttl: 过期秒数，默认5分钟

    Returns:
        True表示写入成功
    """
    global _memory_cache

    full_key = _build_key(namespace, key)

    # 1. 写入Redis
    redis = await get_redis()
    if redis is not None:
        try:
            await redis.setex(full_key, ttl, json.dumps(value, ensure_ascii=False))
        except Exception:
            pass

    # 2. 同时写入内存缓存（兜底）
    _memory_cache[full_key] = (value, time.monotonic() + ttl)

    return True


async def delete(namespace: str, key: str):
    """删除缓存"""
    global _memory_cache

    full_key = _build_key(namespace, key)

    redis = await get_redis()
    if redis is not None:
        try:
            await redis.delete(full_key)
        except Exception:
            pass

    _memory_cache.pop(full_key, None)


async def get_or_set(
    namespace: str,
    key: str,
    factory: Callable[[], Any],
    ttl: int = 300
) -> Any:
    """获取缓存，未命中时调用factory回源写入

    Args:
        namespace: 命名空间
        key: 缓存key
        factory: 回源数据工厂函数（支持同步和异步）
        ttl: 过期秒数

    Returns:
        缓存值或factory返回值
    """
    cached = await get(namespace, key)
    if cached is not None:
        return cached

    # 回源获取（兼容 async def 和返回协程的普通函数如 lambda）
    if asyncio.iscoroutinefunction(factory):
        value = await factory()
    else:
        value = factory()
        if asyncio.iscoroutine(value):
            value = await value

    if value is not None:
        await set(namespace, key, value, ttl)

    return value


async def flush_namespace(namespace: str):
    """清除某个命名空间下的所有缓存

    通过Redis SCAN + DELETE实现，降级时清除内存缓存中匹配的key
    """
    global _memory_cache

    prefix = _build_key(namespace, "")

    # 1. Redis
    redis = await get_redis()
    if redis is not None:
        try:
            cursor = 0
            while True:
                cursor, keys = await redis.scan(cursor, match=f"{prefix}*", count=100)
                if keys:
                    await redis.delete(*keys)
                if cursor == 0:
                    break
        except Exception:
            pass

    # 2. 内存缓存
    expired_keys = [k for k in _memory_cache if k.startswith(prefix)]
    for k in expired_keys:
        _memory_cache.pop(k, None)


# ── 常用命名空间常量 ──

class CacheNS:
    """缓存命名空间"""
    SCHEMA = "schema"           # 数据库表结构
    KB_LIST = "kb_list"         # 知识库列表
    KB_DETAIL = "kb_detail"     # 知识库详情
    KB_DOC_LIST = "kb_doc"      # 知识库文档列表
    CONV_LIST = "conv_list"     # 会话列表
    ERP_QUERY = "erp_query"     # ERP查询结果缓存
