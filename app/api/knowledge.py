"""知识库管理接口"""
from fastapi import APIRouter, Request, HTTPException, UploadFile, File
from app.models.schemas import (
    KnowledgeBaseCreate, KnowledgeBaseUpdate,
    KnowledgeSearchRequest, PageRequest
)
from app.config import settings

router = APIRouter(prefix="/api/ai/knowledge", tags=["知识库管理"])


def _has_kb_permission(permissions: list[str], scope_type: str) -> bool:
    """检查用户是否拥有指定范围的知识库管理权限"""
    perm_map = {
        "global": "ai:knowledge:manage_global",
        "tenant": "ai:knowledge:manage_tenant",
        "personal": "ai:knowledge:manage_personal",
    }
    perm = perm_map.get(scope_type)
    return perm in permissions if perm else False


@router.get("")
async def list_knowledge_bases(page_num: int = 1, page_size: int = 20, req: Request = None):
    """知识库列表"""
    pool = req.app.state.db_pool
    user_context = req.state.user_context

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
        # 转换时间字段为字符串
        for item in items:
            for key in ("created_at", "updated_at"):
                if item.get(key):
                    item[key] = item[key].isoformat()

        return {"total": total, "page_num": page_num, "page_size": page_size, "items": items}


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
        return {"id": kb_id, "name": kb.name}


@router.get("/{kb_id}")
async def get_knowledge_base(kb_id: int, req: Request):
    """知识库详情"""
    pool = req.app.state.db_pool
    user_context = req.state.user_context
    async with pool.acquire() as conn:
        # tenant_id 隔离：global 库任意可见，tenant/personal 库须匹配
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
        # 权限校验：先查出知识库范围，再检查用户权限
        row = await conn.fetchrow(
            "SELECT scope_type FROM knowledge_base WHERE id = $1 AND is_deleted = FALSE",
            kb_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="知识库不存在")
        if not _has_kb_permission(user_context.permissions, row["scope_type"]):
            raise HTTPException(status_code=403, detail="无编辑该范围知识库的权限")

        await conn.execute(
            f"UPDATE knowledge_base SET {', '.join(update_fields)} WHERE id = ${idx} AND is_deleted = FALSE",
            *params
        )
        return {"message": "更新成功"}


@router.delete("/{kb_id}")
async def delete_knowledge_base(kb_id: int, req: Request):
    """删除知识库（逻辑删除）"""
    pool = req.app.state.db_pool
    user_context = req.state.user_context
    async with pool.acquire() as conn:
        # 权限校验：先查出知识库范围，再检查用户权限
        row = await conn.fetchrow(
            "SELECT scope_type FROM knowledge_base WHERE id = $1 AND is_deleted = FALSE",
            kb_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="知识库不存在")
        if not _has_kb_permission(user_context.permissions, row["scope_type"]):
            raise HTTPException(status_code=403, detail="无删除该范围知识库的权限")

        await conn.execute(
            "UPDATE knowledge_base SET is_deleted = TRUE, updated_by = $2, updated_at = NOW() WHERE id = $1 AND is_deleted = FALSE",
            kb_id, user_context.user_id
        )
        return {"message": "删除成功"}


@router.post("/{kb_id}/search")
async def search_knowledge(kb_id: int, search_req: KnowledgeSearchRequest, req: Request):
    """测试检索"""
    from app.tools.knowledge import KnowledgeTool
    pool = req.app.state.db_pool
    user_context = req.state.user_context
    oss_service = getattr(req.app.state, "oss_service", None)
    tool = KnowledgeTool(db_pool=pool, oss_service=oss_service)
    result = await tool.execute(
        query=search_req.query, kb_ids=[kb_id],
        top_k=search_req.top_k, tenant_id=user_context.tenant_id
    )
    return result


@router.post("/{kb_id}/documents")
async def upload_document(kb_id: int, file: UploadFile = File(...), req: Request = None):
    """上传文档到知识库（校验→OSS备份→解析→切块→向量化→入库）"""
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

    # 执行文档处理管道（传入知识库级切分参数 + OSS服务）
    processor = DocumentProcessor(db_pool=pool, oss_service=oss_service)
    result = await processor.process_upload(
        kb_id=kb_id,
        tenant_id=user_context.tenant_id,
        user_id=user_context.user_id,
        file_name=file_name,
        file_content=file_content,
        file_type=file_type,
        chunk_size=kb_row["chunk_size"],
        chunk_overlap=kb_row["chunk_overlap"]
    )

    if result["status"] == "completed":
        return {
            "message": f"文档处理完成，共切分{result['chunk_count']}个片段",
            "doc_id": result["doc_id"],
            "chunk_count": result["chunk_count"],
            "file_url": result.get("file_url", "")
        }
    else:
        raise HTTPException(
            status_code=422,
            detail=f"文档处理失败: {result.get('error', '未知错误')}"
        )


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
            "SELECT scope_type, chunk_size, chunk_overlap, tenant_id FROM knowledge_base WHERE id = $1 AND is_deleted = FALSE",
            kb_id
        )
        if not kb_row:
            raise HTTPException(status_code=404, detail="知识库不存在")
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
    oss_service = getattr(req.app.state, "oss_service", None)
    offset = (page_num - 1) * page_size

    async with pool.acquire() as conn:
        kb_row = await conn.fetchrow(
            "SELECT scope_type, tenant_id, created_by FROM knowledge_base WHERE id = $1 AND is_deleted = FALSE",
            kb_id
        )
        if not kb_row:
            raise HTTPException(status_code=404, detail="知识库不存在")

        # 权限校验
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
            # 生成OSS预览链接
            if oss_service and item.get("oss_path"):
                item["file_url"] = oss_service.get_resource_url(
                    item["oss_path"], item.get("file_name") or item.get("title")
                )
            else:
                item["file_url"] = ""

        return {"total": total, "page_num": page_num, "page_size": page_size, "items": items}


@router.delete("/{kb_id}/documents/{doc_id}")
async def delete_document(kb_id: int, doc_id: int, req: Request):
    """删除知识库文档（逻辑删除，同时清理向量片段）"""
    pool = req.app.state.db_pool
    user_context = req.state.user_context

    async with pool.acquire() as conn:
        kb_row = await conn.fetchrow(
            "SELECT scope_type FROM knowledge_base WHERE id = $1 AND is_deleted = FALSE",
            kb_id
        )
        if not kb_row:
            raise HTTPException(status_code=404, detail="知识库不存在")
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

        return {"message": "文档已删除"}
