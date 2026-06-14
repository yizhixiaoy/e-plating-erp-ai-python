"""对话临时文件上传接口 - 上传到OSS备份，24小时过期"""
import uuid
import hashlib
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, HTTPException, UploadFile, File
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai/files", tags=["临时文件管理"])

# 兼容前端直接调用的上传路由
upload_router = APIRouter(prefix="/api/ai/upload", tags=["临时文件上传"])


@router.post("/upload")
async def upload_temp_file(
    file: UploadFile = File(...),
    conversation_id: int = None,
    req: Request = None
):
    """对话中上传临时文件（备份到OSS，24h过期）

    流程：
    1. 文件大小校验（MAX_TEMP_FILE_SIZE=20MB）
    2. 文件类型校验
    3. 上传到OSS（ai-knowledge/temp/{tenant_id}/...）
    4. 解析文档文本（用于后续Agent读取）
    5. 写入temp_document表（含oss_path）
    6. 返回 {file_id, file_url, file_name, parse_status}
    """
    pool = req.app.state.db_pool
    user_context = req.state.user_context
    oss_service = getattr(req.app.state, "oss_service", None)

    # 读取文件内容
    file_content = await file.read()
    file_name = file.filename or "unknown"
    file_type = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "txt"
    file_size = len(file_content)

    # 1. 文件大小校验
    if file_size > settings.MAX_TEMP_FILE_SIZE:
        max_mb = settings.MAX_TEMP_FILE_SIZE // (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"文件大小超过限制（最大{max_mb}MB）"
        )

    # 2. 文件类型校验
    if file_type not in settings.ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"不支持的文件类型: {file_type}，允许: {', '.join(settings.ALLOWED_FILE_TYPES)}"
        )

    file_id = str(uuid.uuid4())
    content_type = _guess_content_type(file_type)
    file_hash = hashlib.sha256(file_content).hexdigest()
    expires_at = datetime.now() + timedelta(hours=settings.TEMP_FILE_EXPIRE_HOURS)

    # 3. 上传到OSS（OSS未启用时跳过，oss_path为空）
    oss_path = ""
    file_url = ""
    if oss_service and oss_service.enabled:
        object_name = oss_service.generate_temp_object_name(user_context.tenant_id, file_type)
        oss_path = await oss_service.upload_file(file_content, object_name, content_type)
        file_url = oss_service.get_resource_url(oss_path, file_name)
        logger.info(f"[临时文件] OSS上传成功: {oss_path}")

    # 4. 解析文档文本（用于Agent后续读取）
    parsed_text = await _parse_temp_file(file_content, file_type)
    parse_status = "completed" if parsed_text else "failed"

    # 5. 写入temp_document表
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO temp_document
               (file_id, tenant_id, user_id, conversation_id,
                file_name, file_type, file_size, file_path,
                oss_path, content_type, parsed_text, parse_status,
                is_deleted, expires_at, created_by, updated_by, created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12,
                       FALSE, $13, $14, $14, NOW(), NOW())""",
            file_id, user_context.tenant_id, user_context.user_id, conversation_id,
            file_name, file_type, file_size, oss_path or file_id,
            oss_path, content_type, parsed_text, parse_status,
            expires_at, user_context.user_id
        )

    return {
        "file_id": file_id,
        "file_name": file_name,
        "file_type": file_type,
        "file_size": file_size,
        "file_url": file_url,
        "parse_status": parse_status,
        "expires_at": expires_at.isoformat()
    }


@router.get("/{file_id}")
async def get_temp_file_info(file_id: str, req: Request):
    """获取临时文件信息（含预览URL）"""
    pool = req.app.state.db_pool
    user_context = req.state.user_context
    oss_service = getattr(req.app.state, "oss_service", None)

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT file_id, file_name, file_type, file_size, oss_path,
                      parse_status, conversation_id, expires_at, created_at
               FROM temp_document
               WHERE file_id = $1 AND is_deleted = FALSE
                 AND tenant_id = $2""",
            file_id, user_context.tenant_id
        )

    if not row:
        raise HTTPException(status_code=404, detail="文件不存在或已过期")

    if row["expires_at"] < datetime.now():
        raise HTTPException(status_code=410, detail="文件已过期")

    result = dict(row)
    # 转换时间字段
    for key in ("expires_at", "created_at"):
        if result.get(key):
            result[key] = result[key].isoformat()

    # 生成OSS预览链接
    if oss_service and result.get("oss_path"):
        result["file_url"] = oss_service.get_resource_url(
            result["oss_path"], result.get("file_name")
        )
    else:
        result["file_url"] = ""

    return result


@router.get("")
async def list_temp_files(
    conversation_id: int = None,
    req: Request = None
):
    """列出当前用户/会话的临时文件"""
    pool = req.app.state.db_pool
    user_context = req.state.user_context
    oss_service = getattr(req.app.state, "oss_service", None)

    async with pool.acquire() as conn:
        if conversation_id:
            rows = await conn.fetch(
                """SELECT file_id, file_name, file_type, file_size, oss_path,
                          parse_status, conversation_id, expires_at, created_at
                   FROM temp_document
                   WHERE conversation_id = $1 AND tenant_id = $2
                     AND is_deleted = FALSE AND expires_at > NOW()
                   ORDER BY created_at DESC""",
                conversation_id, user_context.tenant_id
            )
        else:
            rows = await conn.fetch(
                """SELECT file_id, file_name, file_type, file_size, oss_path,
                          parse_status, conversation_id, expires_at, created_at
                   FROM temp_document
                   WHERE user_id = $1 AND tenant_id = $2
                     AND is_deleted = FALSE AND expires_at > NOW()
                   ORDER BY created_at DESC LIMIT $3""",
                user_context.user_id, user_context.tenant_id, settings.TEMP_FILE_LIST_LIMIT
            )

    items = []
    for row in rows:
        item = dict(row)
        for key in ("expires_at", "created_at"):
            if item.get(key):
                item[key] = item[key].isoformat()
        # 生成OSS预览链接
        if oss_service and item.get("oss_path"):
            item["file_url"] = oss_service.get_resource_url(
                item["oss_path"], item.get("file_name")
            )
        else:
            item["file_url"] = ""
        items.append(item)

    return {"total": len(items), "items": items}


# ─── 内部辅助函数 ─────────────────────────────────────────

async def _parse_temp_file(file_content: bytes, file_type: str) -> str:
    """解析临时文件为纯文本（用于Agent后续读取）"""
    import os
    import tempfile
    import asyncio

    # 纯文本类型直接读取
    text_types = {"txt", "md", "csv", "json"}
    if file_type in text_types:
        return file_content.decode("utf-8", errors="ignore")

    # 保存到临时文件后用解析器解析
    parser_map = {
        "pdf": "app.parser.pdf_parser.PdfParser",
        "docx": "app.parser.docx_parser.DocxParser",
        "xlsx": "app.parser.xlsx_parser.XlsxParser",
        "xls": "app.parser.xlsx_parser.XlsxParser",
    }

    parser_path = parser_map.get(file_type)
    if not parser_path:
        # 不支持解析的类型，尝试作为文本
        return file_content.decode("utf-8", errors="ignore")[:settings.TEMP_FILE_PARSE_MAX_CHARS]

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=f".{file_type}", delete=False, prefix="ai_temp_"
        ) as f:
            f.write(file_content)
            tmp_path = f.name

        # 动态导入解析器
        module_path, class_name = parser_path.rsplit(".", 1)
        import importlib
        module = importlib.import_module(module_path)
        parser_class = getattr(module, class_name)
        parser = parser_class()

        text = await asyncio.to_thread(parser.parse, tmp_path)
        return text
    except Exception as e:
        logger.warning(f"[临时文件] 解析失败: {e}")
        return ""
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def _guess_content_type(file_type: str) -> str:
    """根据文件类型推断MIME类型"""
    mime_map = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "doc": "application/msword",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xls": "application/vnd.ms-excel",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "txt": "text/plain",
        "md": "text/markdown",
        "csv": "text/csv",
        "json": "application/json",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
    }
    return mime_map.get(file_type.lower(), "application/octet-stream")


# 前端直连上传入口（路径兼容）
@upload_router.post("/temp")
async def upload_temp_file_compat(
    file: UploadFile = File(...),
    conversation_id: int = None,
    req: Request = None
):
    """POST /api/ai/upload/temp — 前端直接调用的上传入口，委托到 upload_temp_file"""
    return await upload_temp_file(file=file, conversation_id=conversation_id, req=req)
