"""统一权限检查服务 — 利用 JWT 透传的 permissions/roles 强化隔离

使用方式：
    from app.services.permissions import guard, require_perm, AI_PERMS
    guard(user_context, AI_PERMS.CHAT_VIEW)           # 返回 True/False
    require_perm(user_context, AI_PERMS.KB_MANAGE_ANY) # 无权限抛 HTTPException(403)
"""

from app.models.schemas import UserContext
from fastapi import HTTPException


# ── 已知权限常量（与 sys_menu.perms 对齐）──────────────────────────────
class AI_PERMS:
    """AI 功能权限标识"""
    CHAT_VIEW          = "ai:chat:view"
    WRITER_VIEW        = "ai:writer:view"
    KNOWLEDGE_VIEW     = "ai:knowledge:view"
    KNOWLEDGE_MANAGE_GLOBAL  = "ai:knowledge:manage_global"
    KNOWLEDGE_MANAGE_TENANT  = "ai:knowledge:manage_tenant"
    KNOWLEDGE_MANAGE_PERSONAL = "ai:knowledge:manage_personal"

    # 知识库管理权限联合检查集
    KB_MANAGE_ANY = {KNOWLEDGE_MANAGE_GLOBAL, KNOWLEDGE_MANAGE_TENANT, KNOWLEDGE_MANAGE_PERSONAL}


# ── 权限检查函数 ──────────────────────────────────────────────────────────

def has_perm(user_context: UserContext, perm: str) -> bool:
    """检查用户是否拥有特定权限"""
    if not user_context or not user_context.permissions:
        return False
    return perm in user_context.permissions


def has_any_perm(user_context: UserContext, perms: set) -> bool:
    """检查用户是否拥有任一权限（适用于多级权限场景）"""
    if not user_context or not user_context.permissions:
        return False
    return bool(set(user_context.permissions) & perms)


def guard(user_context: UserContext, perm: str) -> bool:
    """权限守卫：返回 True/False，不抛异常（Template/工具层使用）"""
    return has_perm(user_context, perm)


def require_perm(user_context: UserContext, perm: str, action: str = "执行此操作"):
    """权限断言：无权限时抛出 HTTPException(403)

    Args:
        user_context: 用户上下文
        perm: 权限标识
        action: 操作描述（用于错误消息）
    """
    has_permission = has_perm(user_context, perm)
    if not has_permission:
        # 记录权限检查失败的日志
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            f"权限检查失败 - 用户: {user_context.username}, "
            f"需要权限: {perm}, "
            f"用户权限: {user_context.permissions}"
        )
        raise HTTPException(
            status_code=403,
            detail=f"权限不足：需要 {perm} 才能{action}"
        )


def require_any_perm(user_context: UserContext, perms: set, action: str = "执行此操作"):
    """权限断言（多级）：无任一权限时抛出 HTTPException(403)"""
    if not has_any_perm(user_context, perms):
        raise HTTPException(
            status_code=403,
            detail=f"权限不足：需要 {' 或 '.join(sorted(perms))} 才能{action}"
        )


# ── 权限摘要（注入 System Prompt）─────────────────────────────────────────

def describe_permissions(user_context: UserContext) -> str:
    """生成用户权限和能力摘要文本，注入 System Prompt"""
    perms = user_context.permissions or []
    roles = user_context.roles or []

    parts = []

    if not perms and not roles:
        return "（无特殊权限）"

    # 角色
    if roles:
        parts.append(f"角色: {', '.join(roles)}")

    # 权限能力描述
    capabilities = []
    if AI_PERMS.KNOWLEDGE_VIEW in perms:
        capabilities.append("知识库检索")
    if has_any_perm(user_context, AI_PERMS.KB_MANAGE_ANY):
        capabilities.append("知识库管理")
    if AI_PERMS.CHAT_VIEW in perms:
        capabilities.append("业务数据查询·统计分析")
    if AI_PERMS.WRITER_VIEW in perms:
        capabilities.append("AI写作")

    if capabilities:
        parts.append(f"可用能力: {', '.join(capabilities)}")

    return " | ".join(parts)
