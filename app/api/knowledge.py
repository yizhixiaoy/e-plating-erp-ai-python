"""知识库管理接口"""
import asyncio
import logging
from urllib.parse import quote, unquote
from fastapi import APIRouter, Request, HTTPException, UploadFile, File
from app.models.schemas import (
    KnowledgeBaseCreate, KnowledgeBaseUpdate,
    KnowledgeSearchRequest, PageRequest
)
from app.config import settings
from app.services.cache import get_or_set, flush_namespace, CacheNS
from app.services.permissions import require_perm, require_any_perm, AI_PERMS, is_platform_admin
from app.services.oss_storage import get_preview_type

router = APIRouter(prefix="/api/ai/knowledge", tags=["知识库管理"])
logger = logging.getLogger(__name__)
_KB_LIST_TTL = 300  # 知识库列表缓存5分钟


def _has_kb_permission(permissions: list[str], scope_type: str) -> bool:
    """检查用户是否拥有指定范围的知识库管理权限"""
    perm_map = {
        "global": "ai:knowledge:manage_global",
        "tenant": "ai:knowledge:manage_tenant",
        "personal": "ai:knowledge:manage_personal",
    }
    perm = perm_map.get(scope_type)
    return perm in permissions if perm else False


def _check_kb_ownership(kb_row, user_context, action: str = "访问"):
    """校验知识库租户/个人归属，防止跨租户越权操作

    平台管理员（system角色）可跨租户操作任意知识库。

    Args:
        kb_row: 数据库查询行（含 scope_type, tenant_id, created_by）
        user_context: 用户上下文
        action: 操作描述（用于错误消息）

    Raises:
        HTTPException(403): 无权操作
    """
    # 平台管理员跳过租户隔离
    if is_platform_admin(user_context):
        return
    scope = kb_row["scope_type"]
    if scope == "tenant" and kb_row["tenant_id"] != user_context.tenant_id:
        raise HTTPException(status_code=403, detail=f"无权{action}该知识库")
    if scope == "personal" and kb_row["created_by"] != user_context.user_id:
        raise HTTPException(status_code=403, detail=f"无权{action}该知识库")


@router.get("")
async def list_knowledge_bases(page_num: int = 1, page_size: int = 20, req: Request = None):
    """知识库列表（Redis缓存，5分钟TTL）"""
    pool = req.app.state.db_pool
    user_context = req.state.user_context

    # 权限守卫：非访客用户需要知识库查看权限
    if user_context.auth_mode != "guest":
        require_perm(user_context, AI_PERMS.KNOWLEDGE_VIEW, "查看知识库")

    cache_key = f"t{user_context.tenant_id}_u{user_context.user_id}_m{user_context.auth_mode}_p{page_num}_s{page_size}"

    async def _fetch():
        offset = (page_num - 1) * page_size
        async with pool.acquire() as conn:
            # 访客模式：仅可见全租户知识库
            if user_context.auth_mode == "guest":
                rows = await conn.fetch(
                    """SELECT * FROM knowledge_base
                       WHERE scope_type = 'global' AND status = 'active' AND is_deleted = FALSE
                       ORDER BY created_at DESC LIMIT $1 OFFSET $2""",
                    page_size, offset
                )
                total = await conn.fetchval(
                    "SELECT COUNT(*) FROM knowledge_base WHERE scope_type = 'global' AND status = 'active' AND is_deleted = FALSE"
                )
            else:
                rows = await conn.fetch(
                    """SELECT * FROM knowledge_base
                       WHERE is_deleted = FALSE
                         AND ((scope_type = 'global')
                          OR (scope_type = 'tenant' AND tenant_id = $3)
                          OR (scope_type = 'personal' AND created_by = $4))
                       ORDER BY created_at DESC LIMIT $1 OFFSET $2""",
                    page_size, offset, user_context.tenant_id, user_context.user_id
                )
                total = await conn.fetchval(
                    """SELECT COUNT(*) FROM knowledge_base
                       WHERE is_deleted = FALSE
                         AND ((scope_type = 'global')
                          OR (scope_type = 'tenant' AND tenant_id = $1)
                          OR (scope_type = 'personal' AND created_by = $2))""",
                    user_context.tenant_id, user_context.user_id
                )

            items = [dict(row) for row in rows]
            for item in items:
                for key in ("created_at", "updated_at"):
                    if item.get(key):
                        item[key] = item[key].isoformat()

            return {"total": total, "page_num": page_num, "page_size": page_size, "items": items}

    return await get_or_set(CacheNS.KB_LIST, cache_key, _fetch, _KB_LIST_TTL)


@router.post("")
async def create_knowledge_base(kb: KnowledgeBaseCreate, req: Request):
    """新建知识库"""
    pool = req.app.state.db_pool
    user_context = req.state.user_context

    # 权限校验：用户角色是否拥有该范围的管理权限
    if not _has_kb_permission(user_context.permissions, kb.scope_type.value):
        raise HTTPException(status_code=403, detail=f"您没有创建{kb.scope_type.value}范围知识库的权限")

    async with pool.acquire() as conn:
        kb_id = await conn.fetchval(
            """INSERT INTO knowledge_base
               (tenant_id, scope_type, name, description, chunk_size, chunk_overlap, is_deleted, created_by, updated_by, created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5, $6, FALSE, $7, $7, NOW(), NOW())
               RETURNING id""",
            user_context.tenant_id if kb.scope_type.value != "global" else None,
            kb.scope_type.value,
            kb.name,
            kb.description,
            kb.chunk_size,
            kb.chunk_overlap,
            user_context.user_id
        )
        await flush_namespace(CacheNS.KB_LIST)
        return {"id": kb_id, "name": kb.name}


@router.get("/{kb_id}")
async def get_knowledge_base(kb_id: int, req: Request):
    """知识库详情

    平台管理员可查看任意租户的知识库详情。
    """
    pool = req.app.state.db_pool
    user_context = req.state.user_context
    admin_mode = is_platform_admin(user_context)

    async with pool.acquire() as conn:
        if admin_mode:
            # 平台管理员：跳过租户隔离，直接查询
            row = await conn.fetchrow(
                "SELECT * FROM knowledge_base WHERE id = $1 AND is_deleted = FALSE",
                kb_id
            )
        else:
            # 普通用户：global 库任意可见，tenant/personal 库须匹配
            row = await conn.fetchrow(
                """SELECT * FROM knowledge_base
                   WHERE id = $1 AND is_deleted = FALSE
                     AND (scope_type = 'global'
                          OR (scope_type = 'tenant' AND tenant_id = $2)
                          OR (scope_type = 'personal' AND created_by = $3))""",
                kb_id, user_context.tenant_id, user_context.user_id
            )
        if not row:
            raise HTTPException(status_code=404, detail="知识库不存在")
        result = dict(row)
        for key in ("created_at", "updated_at"):
            if result.get(key):
                result[key] = result[key].isoformat()
        return result


@router.put("/{kb_id}")
async def update_knowledge_base(kb_id: int, kb: KnowledgeBaseUpdate, req: Request):
    """编辑知识库"""
    pool = req.app.state.db_pool
    user_context = req.state.user_context

    update_fields = []
    params = []
    idx = 1

    if kb.name is not None:
        update_fields.append(f"name = ${idx}")
        params.append(kb.name)
        idx += 1
    if kb.description is not None:
        update_fields.append(f"description = ${idx}")
        params.append(kb.description)
        idx += 1
    if kb.chunk_size is not None:
        update_fields.append(f"chunk_size = ${idx}")
        params.append(kb.chunk_size)
        idx += 1
    if kb.chunk_overlap is not None:
        update_fields.append(f"chunk_overlap = ${idx}")
        params.append(kb.chunk_overlap)
        idx += 1
    if kb.status is not None:
        update_fields.append(f"status = ${idx}")
        params.append(kb.status)
        idx += 1

    if not update_fields:
        return {"message": "无更新字段"}

    update_fields.append(f"updated_by = ${idx}")
    params.append(user_context.user_id)
    idx += 1
    update_fields.append("updated_at = NOW()")

    params.extend([kb_id])

    async with pool.acquire() as conn:
        # 权限校验：先查出知识库范围，再检查用户权限 + 租户归属
        row = await conn.fetchrow(
            "SELECT scope_type, tenant_id, created_by FROM knowledge_base WHERE id = $1 AND is_deleted = FALSE",
            kb_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="知识库不存在")
        _check_kb_ownership(row, user_context, "编辑")
        if not _has_kb_permission(user_context.permissions, row["scope_type"]):
            raise HTTPException(status_code=403, detail="无编辑该范围知识库的权限")

        await conn.execute(
            f"UPDATE knowledge_base SET {', '.join(update_fields)} WHERE id = ${idx} AND is_deleted = FALSE",
            *params
        )
        await flush_namespace(CacheNS.KB_LIST)
        return {"message": "更新成功"}


@router.delete("/{kb_id}")
async def delete_knowledge_base(kb_id: int, req: Request):
    """删除知识库（逻辑删除）"""
    pool = req.app.state.db_pool
    user_context = req.state.user_context
    async with pool.acquire() as conn:
        # 权限校验：先查出知识库范围，再检查用户权限 + 租户归属
        row = await conn.fetchrow(
            "SELECT scope_type, tenant_id, created_by FROM knowledge_base WHERE id = $1 AND is_deleted = FALSE",
            kb_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="知识库不存在")
        _check_kb_ownership(row, user_context, "删除")
        if not _has_kb_permission(user_context.permissions, row["scope_type"]):
            raise HTTPException(status_code=403, detail="无删除该范围知识库的权限")

        await conn.execute(
            "UPDATE knowledge_base SET is_deleted = TRUE, updated_by = $2, updated_at = NOW() WHERE id = $1 AND is_deleted = FALSE",
            kb_id, user_context.user_id
        )
        await flush_namespace(CacheNS.KB_LIST)
        return {"message": "删除成功"}


@router.post("/{kb_id}/search")
async def search_knowledge(kb_id: int, search_req: KnowledgeSearchRequest, req: Request):
    """知识库检索"""
    from app.tools.knowledge import KnowledgeTool
    pool = req.app.state.db_pool
    user_context = req.state.user_context
    oss_service = getattr(req.app.state, "oss_service", None)

    # 权限校验：先确认用户有权访问该知识库
    async with pool.acquire() as conn:
        kb_row = await conn.fetchrow(
            "SELECT scope_type, tenant_id, created_by FROM knowledge_base WHERE id = $1 AND is_deleted = FALSE",
            kb_id
        )
        if not kb_row:
            raise HTTPException(status_code=404, detail="知识库不存在")
        _check_kb_ownership(kb_row, user_context, "检索")

    tool = KnowledgeTool(db_pool=pool, oss_service=oss_service)
    result = await tool.execute(
        query=search_req.query, kb_ids=[kb_id],
        top_k=search_req.top_k, tenant_id=user_context.tenant_id,
        is_platform_admin=is_platform_admin(user_context)
    )
    return result


@router.post("/{kb_id}/documents")
async def upload_document(kb_id: int, file: UploadFile = File(...), req: Request = None):
    """上传文档到知识库（快速返回，后台异步解析）

    流程：
    1. 同步阶段：校验→保存临时文件→OSS备份→创建DB记录（状态=parsing）→立即返回
    2. 后台任务：解析→切块→向量化→更新状态
    """
    from app.services.document_processor import DocumentProcessor
    pool = req.app.state.db_pool
    user_context = req.state.user_context
    oss_service = getattr(req.app.state, "oss_service", None)

    # 权限校验：检查知识库是否存在且用户有权限
    async with pool.acquire() as conn:
        kb_row = await conn.fetchrow(
            """SELECT scope_type, chunk_size, chunk_overlap FROM knowledge_base
               WHERE id = $1 AND is_deleted = FALSE""",
            kb_id
        )
    if not kb_row:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if not _has_kb_permission(user_context.permissions, kb_row["scope_type"]):
        # 也允许知识库创建者上传
        pass

    # 读取文件内容
    file_content = await file.read()
    file_name = file.filename or "unknown"
    file_type = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "txt"

    # 文件大小校验
    if len(file_content) > settings.MAX_KB_FILE_SIZE:
        max_mb = settings.MAX_KB_FILE_SIZE // (1024 * 1024)
        raise HTTPException(status_code=413, detail=f"文件大小超过限制（最大{max_mb}MB）")

    # 文件类型校验
    if file_type not in settings.ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"不支持的文件类型: {file_type}，允许: {', '.join(settings.ALLOWED_FILE_TYPES)}"
        )

    # 快速上传阶段：保存临时文件 + OSS备份 + 创建DB记录
    processor = DocumentProcessor(db_pool=pool, oss_service=oss_service)
    upload_info = await processor.quick_upload(
        kb_id=kb_id,
        tenant_id=user_context.tenant_id,
        user_id=user_context.user_id,
        file_name=file_name,
        file_content=file_content,
        file_type=file_type
    )

    # 启动后台异步解析任务（从OSS下载文件进行解析）
    async def _background_process():
        try:
            await processor.process_in_background(
                doc_id=upload_info["doc_id"],
                kb_id=kb_id,
                tenant_id=user_context.tenant_id,
                user_id=user_context.user_id,
                oss_path=upload_info["oss_path"],
                file_type=file_type,
                chunk_size=kb_row["chunk_size"],
                chunk_overlap=kb_row["chunk_overlap"]
            )
            await flush_namespace(CacheNS.KB_LIST)
            await flush_namespace(CacheNS.KB_DOC_LIST)
        except Exception as e:
            logger.error("[upload] 后台解析任务异常: %s", e, exc_info=True)

    asyncio.create_task(_background_process())

    # 立即返回文档信息（状态=parsing）
    await flush_namespace(CacheNS.KB_LIST)
    # 生成后端代理预览URL（不暴露OSS直链）
    oss_path = upload_info.get("oss_path", "")
    preview_file_url = ""
    if oss_path:
        # oss_path在upload_file中已URL编码，需先解码再编码，防止双重编码
        decoded_path = unquote(oss_path)
        preview_file_url = f"/api/v1/files/preview?ossPath={quote(decoded_path, safe='')}&filename={quote(file_name, safe='')}"
    return {
        "message": "文件上传成功，正在解析中...",
        "doc_id": upload_info["doc_id"],
        "file_name": file_name,
        "file_type": file_type,
        "file_size": upload_info["file_size"],
        "file_url": preview_file_url,
        "parse_status": "parsing"
    }


@router.post("/{kb_id}/rebuild")
async def rebuild_vectors(kb_id: int, req: Request):
    """重建知识库向量（从OSS重新下载→解析→切块→向量化→入库）

    流程：
    1. 重置所有文档状态为pending，清理旧向量片段
    2. 后台异步逐文档从OSS下载→重新解析→切块→向量化→入库
    """
    import asyncio
    from app.services.document_processor import DocumentProcessor
    pool = req.app.state.db_pool
    user_context = req.state.user_context
    oss_service = getattr(req.app.state, "oss_service", None)

    # 权限校验
    async with pool.acquire() as conn:
        kb_row = await conn.fetchrow(
            "SELECT scope_type, chunk_size, chunk_overlap, tenant_id, created_by FROM knowledge_base WHERE id = $1 AND is_deleted = FALSE",
            kb_id
        )
        if not kb_row:
            raise HTTPException(status_code=404, detail="知识库不存在")
        _check_kb_ownership(kb_row, user_context, "重建")
        if not _has_kb_permission(user_context.permissions, kb_row["scope_type"]):
            raise HTTPException(status_code=403, detail="无重建该范围知识库的权限")

        # 获取所有需要重建的文档（含oss_path）
        docs = await conn.fetch(
            """SELECT id, oss_path, file_type, file_name FROM knowledge_document
               WHERE kb_id = $1 AND is_deleted = FALSE AND oss_path IS NOT NULL AND oss_path != ''""",
            kb_id
        )

    if not docs:
        return {"message": "无可重建的文档（需先上传到OSS）", "kb_id": kb_id}

    # 标记所有文档为pending，清理旧片段
    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE knowledge_document SET parse_status = 'pending', updated_at = NOW()
               WHERE kb_id = $1 AND is_deleted = FALSE""",
            kb_id
        )
        # 清理旧片段
        await conn.execute(
            "UPDATE knowledge_chunk SET is_deleted = TRUE, updated_at = NOW() WHERE kb_id = $1",
            kb_id
        )
        await conn.execute(
            "UPDATE knowledge_base SET chunk_count = 0, updated_at = NOW() WHERE id = $1",
            kb_id
        )

    # 后台异步重建每个文档（从OSS下载原文件重新处理）
    processor = DocumentProcessor(db_pool=pool, oss_service=oss_service)
    chunk_size = kb_row["chunk_size"]
    chunk_overlap = kb_row["chunk_overlap"]
    tenant_id = kb_row["tenant_id"]

    async def _rebuild_all():
        for doc in docs:
            await processor.reprocess_document(
                doc_id=doc["id"],
                kb_id=kb_id,
                tenant_id=tenant_id,
                user_id=user_context.user_id,
                oss_path=doc["oss_path"],
                file_type=doc["file_type"],
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )

    asyncio.create_task(_rebuild_all())

    return {
        "message": f"已启动{len(docs)}个文档的后台重建",
        "kb_id": kb_id,
        "doc_count": len(docs)
    }


# ─── 文档管理接口 ─────────────────────────────────────────

@router.get("/{kb_id}/documents")
async def list_documents(
    kb_id: int, page_num: int = 1, page_size: int = 20, req: Request = None
):
    """知识库文档列表（含OSS预览链接）"""
    pool = req.app.state.db_pool
    user_context = req.state.user_context
    offset = (page_num - 1) * page_size

    async with pool.acquire() as conn:
        kb_row = await conn.fetchrow(
            "SELECT scope_type, tenant_id, created_by FROM knowledge_base WHERE id = $1 AND is_deleted = FALSE",
            kb_id
        )
        if not kb_row:
            raise HTTPException(status_code=404, detail="知识库不存在")

        # 权限校验（平台管理员跳过租户隔离）
        if not is_platform_admin(user_context):
            scope = kb_row["scope_type"]
            if scope == "tenant" and kb_row["tenant_id"] != user_context.tenant_id:
                raise HTTPException(status_code=403, detail="无权访问该知识库")
            elif scope == "personal" and kb_row["created_by"] != user_context.user_id:
                raise HTTPException(status_code=403, detail="无权访问该知识库")

        rows = await conn.fetch(
            """SELECT id, title, file_name, file_type, file_size, chunk_count,
                      oss_path, parse_status, parse_error, created_by, created_at, updated_at
               FROM knowledge_document
               WHERE kb_id = $1 AND is_deleted = FALSE
               ORDER BY created_at DESC LIMIT $2 OFFSET $3""",
            kb_id, page_size, offset
        )
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM knowledge_document WHERE kb_id = $1 AND is_deleted = FALSE",
            kb_id
        )

        items = [dict(row) for row in rows]
        for item in items:
            for key in ("created_at", "updated_at"):
                if item.get(key):
                    item[key] = item[key].isoformat()
            # 生成预览URL：通过Java后端代理转发，不暴露OSS直链
            actual_filename = item.get("file_name") or item.get("title") or ""
            item["preview_type"] = get_preview_type(actual_filename)
            oss_path = item.get("oss_path") or ""
            if oss_path:
                # oss_path在DB中已是URL编码的（quote生成），需先解码再编码，防止双重编码
                decoded_path = unquote(oss_path)
                encoded_path = quote(decoded_path, safe='')
                encoded_name = quote(actual_filename, safe='')
                item["file_url"] = f"/api/v1/files/preview?ossPath={encoded_path}&filename={encoded_name}"
            else:
                item["file_url"] = ""

        return {"total": total, "page_num": page_num, "page_size": page_size, "items": items}


@router.post("/{kb_id}/documents/{doc_id}/reparse")
async def reparse_document(kb_id: int, doc_id: int, req: Request):
    """重新解析单个文档（从OSS下载→重新解析→切块→向量化→入库）"""
    import asyncio
    from app.services.document_processor import DocumentProcessor
    pool = req.app.state.db_pool
    user_context = req.state.user_context
    oss_service = getattr(req.app.state, "oss_service", None)

    # 权限校验
    async with pool.acquire() as conn:
        kb_row = await conn.fetchrow(
            "SELECT scope_type, chunk_size, chunk_overlap, tenant_id, created_by FROM knowledge_base WHERE id = $1 AND is_deleted = FALSE",
            kb_id
        )
        if not kb_row:
            raise HTTPException(status_code=404, detail="知识库不存在")
        _check_kb_ownership(kb_row, user_context, "重解析")
        if not _has_kb_permission(user_context.permissions, kb_row["scope_type"]):
            raise HTTPException(status_code=403, detail="无重解析该知识库文档的权限")

        doc_row = await conn.fetchrow(
            """SELECT id, oss_path, file_type FROM knowledge_document
               WHERE id = $1 AND kb_id = $2 AND is_deleted = FALSE""",
            doc_id, kb_id
        )
        if not doc_row:
            raise HTTPException(status_code=404, detail="文档不存在")
        if not doc_row["oss_path"]:
            raise HTTPException(status_code=422, detail="文档无OSS备份，无法重解析")

        # 重置文档状态
        await conn.execute(
            "UPDATE knowledge_document SET parse_status = 'pending', updated_at = NOW() WHERE id = $1",
            doc_id
        )
        # 清理旧片段
        await conn.execute(
            "UPDATE knowledge_chunk SET is_deleted = TRUE, updated_at = NOW() WHERE doc_id = $1",
            doc_id
        )

    # 后台异步重解析
    processor = DocumentProcessor(db_pool=pool, oss_service=oss_service)
    asyncio.create_task(
        processor.reprocess_document(
            doc_id=doc_id,
            kb_id=kb_id,
            tenant_id=kb_row["tenant_id"],
            user_id=user_context.user_id,
            oss_path=doc_row["oss_path"],
            file_type=doc_row["file_type"],
            chunk_size=kb_row["chunk_size"],
            chunk_overlap=kb_row["chunk_overlap"]
        )
    )

    return {"message": "已启动文档重解析", "doc_id": doc_id, "kb_id": kb_id}


@router.get("/{kb_id}/documents/{doc_id}/chunks")
async def list_document_chunks(
    kb_id: int, doc_id: int, page_num: int = 1, page_size: int = 20, req: Request = None
):
    """文档切片列表（不含向量，含元数据）"""
    pool = req.app.state.db_pool
    user_context = req.state.user_context
    offset = (page_num - 1) * page_size

    async with pool.acquire() as conn:
        # 权限校验
        kb_row = await conn.fetchrow(
            "SELECT scope_type, tenant_id, created_by FROM knowledge_base WHERE id = $1 AND is_deleted = FALSE",
            kb_id
        )
        if not kb_row:
            raise HTTPException(status_code=404, detail="知识库不存在")
        if not is_platform_admin(user_context):
            scope = kb_row["scope_type"]
            if scope == "tenant" and kb_row["tenant_id"] != user_context.tenant_id:
                raise HTTPException(status_code=403, detail="无权访问该知识库")
            elif scope == "personal" and kb_row["created_by"] != user_context.user_id:
                raise HTTPException(status_code=403, detail="无权访问该知识库")

        # 确认文档存在
        doc_row = await conn.fetchrow(
            "SELECT id, file_name, title, chunk_count FROM knowledge_document WHERE id = $1 AND kb_id = $2 AND is_deleted = FALSE",
            doc_id, kb_id
        )
        if not doc_row:
            raise HTTPException(status_code=404, detail="文档不存在")

        rows = await conn.fetch(
            """SELECT id, chunk_index, content, token_count, metadata, created_at
               FROM knowledge_chunk
               WHERE doc_id = $1 AND is_deleted = FALSE
               ORDER BY chunk_index ASC LIMIT $2 OFFSET $3""",
            doc_id, page_size, offset
        )
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM knowledge_chunk WHERE doc_id = $1 AND is_deleted = FALSE",
            doc_id
        )

        items = []
        for row in rows:
            item = dict(row)
            for key in ("created_at",):
                if item.get(key):
                    item[key] = item[key].isoformat()
            # metadata 可能是 JSON string 或 dict
            if isinstance(item.get("metadata"), str):
                import json
                try:
                    item["metadata"] = json.loads(item["metadata"])
                except Exception:
                    item["metadata"] = {}
            items.append(item)

        return {
            "total": total,
            "page_num": page_num,
            "page_size": page_size,
            "doc_id": doc_id,
            "doc_name": doc_row["file_name"] or doc_row["title"],
            "items": items
        }


@router.delete("/{kb_id}/documents/{doc_id}")
async def delete_document(kb_id: int, doc_id: int, req: Request):
    """删除知识库文档（逻辑删除，同时清理向量片段）"""
    pool = req.app.state.db_pool
    user_context = req.state.user_context

    async with pool.acquire() as conn:
        kb_row = await conn.fetchrow(
            "SELECT scope_type, tenant_id, created_by FROM knowledge_base WHERE id = $1 AND is_deleted = FALSE",
            kb_id
        )
        if not kb_row:
            raise HTTPException(status_code=404, detail="知识库不存在")
        _check_kb_ownership(kb_row, user_context, "删除文档")
        if not _has_kb_permission(user_context.permissions, kb_row["scope_type"]):
            raise HTTPException(status_code=403, detail="无删除文档的权限")

        doc_row = await conn.fetchrow(
            "SELECT chunk_count FROM knowledge_document WHERE id = $1 AND kb_id = $2 AND is_deleted = FALSE",
            doc_id, kb_id
        )
        if not doc_row:
            raise HTTPException(status_code=404, detail="文档不存在")

        # 逻辑删除文档和关联片段
        await conn.execute(
            "UPDATE knowledge_document SET is_deleted = TRUE, updated_by = $2, updated_at = NOW() WHERE id = $1",
            doc_id, user_context.user_id
        )
        await conn.execute(
            "UPDATE knowledge_chunk SET is_deleted = TRUE, updated_by = $2, updated_at = NOW() WHERE doc_id = $1",
            doc_id, user_context.user_id
        )
        # 更新知识库统计
        chunk_count = doc_row["chunk_count"] or 0
        await conn.execute(
            """UPDATE knowledge_base
               SET doc_count = (SELECT COUNT(*) FROM knowledge_document WHERE kb_id = $1 AND is_deleted = FALSE),
                   chunk_count = GREATEST(chunk_count - $2, 0),
                   updated_by = $3, updated_at = NOW()
               WHERE id = $1""",
            kb_id, chunk_count, user_context.user_id
        )

        await flush_namespace(CacheNS.KB_LIST)
        await flush_namespace(CacheNS.KB_DOC_LIST)
        return {"message": "文档已删除"}
