"""知识库管理接口"""
from fastapi import APIRouter, Request, HTTPException, UploadFile, File
from app.models.schemas import (
    KnowledgeBaseCreate, KnowledgeBaseUpdate,
    KnowledgeSearchRequest, PageRequest
)
from app.config import settings

router = APIRouter(prefix="/api/ai/knowledge", tags=["知识库管理"])


@router.get("")
async def list_knowledge_bases(page_num: int = 1, page_size: int = 20, req: Request = None):
    """知识库列表"""
    pool = req.app.state.db_pool
    user_context = req.state.user_context

    offset = (page_num - 1) * page_size
    async with pool.acquire() as conn:
        # 获取可见知识库
        if user_context.auth_mode == "guest":
            rows = await conn.fetch(
                """SELECT * FROM knowledge_base
                   WHERE scope_type = 'public' AND status = 'active' AND is_deleted = FALSE
                   ORDER BY created_at DESC LIMIT $1 OFFSET $2""",
                page_size, offset
            )
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM knowledge_base WHERE scope_type = 'public' AND status = 'active' AND is_deleted = FALSE"
            )
        else:
            rows = await conn.fetch(
                """SELECT * FROM knowledge_base
                   WHERE is_deleted = FALSE
                     AND ((scope_type = 'public')
                      OR (scope_type = 'tenant' AND tenant_id = $3)
                      OR (scope_type = 'private' AND created_by = $4))
                   ORDER BY created_at DESC LIMIT $1 OFFSET $2""",
                page_size, offset, user_context.tenant_id, user_context.user_id
            )
            total = await conn.fetchval(
                """SELECT COUNT(*) FROM knowledge_base
                   WHERE is_deleted = FALSE
                     AND ((scope_type = 'public')
                      OR (scope_type = 'tenant' AND tenant_id = $1)
                      OR (scope_type = 'private' AND created_by = $2))""",
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

    async with pool.acquire() as conn:
        kb_id = await conn.fetchval(
            """INSERT INTO knowledge_base
               (tenant_id, scope_type, name, description, chunk_size, chunk_overlap, is_deleted, created_by, updated_by, created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5, $6, FALSE, $7, $7, NOW(), NOW())
               RETURNING id""",
            user_context.tenant_id if kb.scope_type != "public" else None,
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
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM knowledge_base WHERE id = $1 AND is_deleted = FALSE", kb_id
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
        await conn.execute(
            f"UPDATE knowledge_base SET {', '.join(update_fields)} WHERE id = ${idx}",
            *params
        )
        return {"message": "更新成功"}


@router.delete("/{kb_id}")
async def delete_knowledge_base(kb_id: int, req: Request):
    """删除知识库（逻辑删除）"""
    pool = req.app.state.db_pool
    user_context = req.state.user_context
    async with pool.acquire() as conn:
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
    tool = KnowledgeTool(db_pool=pool)
    result = await tool.execute(query=search_req.query, kb_ids=[kb_id], top_k=search_req.top_k)
    return result


@router.post("/{kb_id}/documents")
async def upload_document(kb_id: int, file: UploadFile = File(...), req: Request = None):
    """上传文档到知识库"""
    return {"message": "文档上传接口（需集成OSS/MinIO）", "kb_id": kb_id, "file_name": file.filename}


@router.post("/{kb_id}/rebuild")
async def rebuild_vectors(kb_id: int, req: Request):
    """重建知识库向量"""
    return {"message": "全量重建向量功能（需后台任务支持）", "kb_id": kb_id}
