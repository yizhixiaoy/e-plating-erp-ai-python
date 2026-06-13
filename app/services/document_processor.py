"""文档处理管道 - 上传→OSS备份→解析→切块→向量化→入库"""
import os
import json
import uuid
import asyncio
import hashlib
import tempfile
import logging
from datetime import datetime
from app.config import settings
from app.parser.chunker import Chunker
from app.services.embedding import embedding_service

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """文档处理管道

    完整流程：
    1. 保存文件到本地临时目录（用于解析）
    2. 上传到OSS/MinIO持久备份（可选，OSS未启用时跳过）
    3. 根据文件类型选择解析器（PDF/DOCX/XLSX/TXT/MD）
    4. 使用Chunker切分为文档片段
    5. 使用EmbeddingService批量向量化
    6. 写入knowledge_document + knowledge_chunk表（含oss_path）
    7. 更新knowledge_base统计计数
    8. 清理本地临时文件
    """

    # 文件类型→解析器映射
    PARSER_MAP = {
        "pdf": "app.parser.pdf_parser.PdfParser",
        "docx": "app.parser.docx_parser.DocxParser",
        "xlsx": "app.parser.xlsx_parser.XlsxParser",
        "xls": "app.parser.xlsx_parser.XlsxParser",
    }

    # 纯文本类型（无需专门解析器）
    TEXT_TYPES = {"txt", "md", "csv", "json"}

    def __init__(self, db_pool, oss_service=None):
        self.db_pool = db_pool
        self.oss_service = oss_service
        self.upload_dir = os.path.join(tempfile.gettempdir(), "ai_knowledge_uploads")
        os.makedirs(self.upload_dir, exist_ok=True)

    async def process_upload(
        self,
        kb_id: int,
        tenant_id: int,
        user_id: int,
        file_name: str,
        file_content: bytes,
        file_type: str = None,
        chunk_size: int = None,
        chunk_overlap: int = None
    ) -> dict:
        """处理文档上传的完整管道

        Args:
            kb_id: 知识库ID
            tenant_id: 租户ID
            user_id: 上传用户ID
            file_name: 文件名
            file_content: 文件二进制内容
            file_type: 文件类型（从扩展名推断）
            chunk_size: 切块大小（字符数），默认使用知识库配置或全局配置
            chunk_overlap: 重叠字符数，默认使用知识库配置或全局配置

        Returns:
            {"doc_id": int, "chunk_count": int, "oss_path": str, "file_url": str,
             "status": "completed"|"failed", "error": str|None}
        """
        if not file_type:
            file_type = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "txt"

        file_size = len(file_content)
        content_type = self._guess_content_type(file_type)
        file_hash = hashlib.sha256(file_content).hexdigest()

        # 1. 保存文件到本地临时目录（用于解析，处理完即清理）
        file_id = str(uuid.uuid4())
        local_path = os.path.join(self.upload_dir, f"{file_id}.{file_type}")
        with open(local_path, "wb") as f:
            f.write(file_content)

        # 2. 上传到OSS持久备份（OSS未启用时跳过，oss_path为空）
        oss_path = ""
        file_url = ""
        if self.oss_service and self.oss_service.enabled:
            object_name = self.oss_service.generate_kb_object_name(kb_id, file_type)
            oss_path = await self.oss_service.upload_file(file_content, object_name, content_type)
            file_url = self.oss_service.get_resource_url(oss_path, file_name)

        # 3. 创建文档记录（状态=parsing，含oss_path）
        doc_id = await self._create_document_record(
            kb_id, tenant_id, user_id, file_name,
            file_type, file_size, oss_path, content_type, file_hash
        )

        try:
            # 4. 解析文档（从本地临时文件读取）
            text = await self._parse_document(local_path, file_type)
            if not text or text.startswith("解析失败") or "依赖未安装" in text:
                await self._update_document_status(doc_id, "failed", text)
                return {"doc_id": doc_id, "chunk_count": 0, "oss_path": oss_path,
                        "file_url": file_url, "status": "failed", "error": text}

            # 5. 切块（使用知识库级参数，未指定则使用全局默认值）
            chunker = Chunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            chunks = chunker.split(text)

            if not chunks:
                await self._update_document_status(doc_id, "failed", "文档内容为空或无法切分")
                return {"doc_id": doc_id, "chunk_count": 0, "oss_path": oss_path,
                        "file_url": file_url, "status": "failed", "error": "内容为空"}

            # 6. 批量向量化
            chunk_texts = [c["content"] for c in chunks]
            embeddings = await asyncio.to_thread(embedding_service.encode, chunk_texts)

            # 7. 写入knowledge_chunk表
            chunk_count = await self._insert_chunks(
                doc_id, kb_id, tenant_id, user_id, chunks, embeddings
            )

            # 8. 更新文档状态 + 知识库统计
            await self._update_document_status(doc_id, "completed", chunk_count=chunk_count)
            await self._update_kb_stats(kb_id, chunk_count)

            return {
                "doc_id": doc_id, "chunk_count": chunk_count,
                "oss_path": oss_path, "file_url": file_url,
                "status": "completed", "error": None
            }

        except Exception as e:
            await self._update_document_status(doc_id, "failed", str(e))
            return {"doc_id": doc_id, "chunk_count": 0, "oss_path": oss_path,
                    "file_url": file_url, "status": "failed", "error": str(e)}
        finally:
            # 清理本地临时文件（OSS已持久化备份）
            try:
                os.remove(local_path)
            except OSError:
                pass

    async def _parse_document(self, file_path: str, file_type: str) -> str:
        """解析文档为纯文本"""
        # 纯文本类型直接读取
        if file_type in self.TEXT_TYPES:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

        # 使用对应解析器
        parser_path = self.PARSER_MAP.get(file_type)
        if not parser_path:
            return f"不支持的文件类型: {file_type}"

        # 动态导入解析器
        module_path, class_name = parser_path.rsplit(".", 1)
        import importlib
        module = importlib.import_module(module_path)
        parser_class = getattr(module, class_name)
        parser = parser_class()

        # 解析（同步操作，放入线程池）
        text = await asyncio.to_thread(parser.parse, file_path)
        return text

    async def _create_document_record(
        self, kb_id, tenant_id, user_id,
        file_name, file_type, file_size,
        oss_path, content_type, file_hash
    ) -> int:
        """创建knowledge_document记录（含OSS路径）"""
        async with self.db_pool.acquire() as conn:
            return await conn.fetchval(
                """INSERT INTO knowledge_document
                   (kb_id, tenant_id, title, file_name, file_type, file_size,
                    oss_path, content_type, file_hash,
                    chunk_count, parse_status, is_deleted, created_by, updated_by, created_at, updated_at)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 0, 'parsing', FALSE, $10, $10, NOW(), NOW())
                   RETURNING id""",
                kb_id, tenant_id, file_name, file_name, file_type,
                file_size, oss_path, content_type, file_hash, user_id
            )

    async def _update_document_status(
        self, doc_id: int, status: str, error: str = None, chunk_count: int = 0
    ):
        """更新文档解析状态"""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """UPDATE knowledge_document
                   SET parse_status = $2, parse_error = $3, chunk_count = $4,
                       updated_at = NOW()
                   WHERE id = $1""",
                doc_id, status, error, chunk_count
            )

    async def _insert_chunks(
        self, doc_id, kb_id, tenant_id, user_id,
        chunks: list[dict], embeddings: list[list[float]]
    ) -> int:
        """批量插入文档片段（含向量）"""
        async with self.db_pool.acquire() as conn:
            count = 0
            for chunk, embedding in zip(chunks, embeddings):
                metadata = chunk.get("metadata", {})
                await conn.execute(
                    """INSERT INTO knowledge_chunk
                       (doc_id, kb_id, tenant_id, chunk_index, content, token_count,
                        embedding, metadata, is_deleted, created_by, updated_by, created_at, updated_at)
                       VALUES ($1, $2, $3, $4, $5, $6, $7::vector, $8::jsonb, FALSE, $9, $9, NOW(), NOW())""",
                    doc_id, kb_id, tenant_id,
                    chunk["index"], chunk["content"],
                    len(chunk["content"]) // 2,  # 粗略估算token
                    str(embedding),  # asyncpg需要字符串格式的vector
                    json.dumps(metadata, ensure_ascii=False),
                    user_id
                )
                count += 1
            return count

    async def _update_kb_stats(self, kb_id: int, new_chunks: int):
        """更新知识库文档数和片段数统计"""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """UPDATE knowledge_base
                   SET doc_count = (SELECT COUNT(*) FROM knowledge_document WHERE kb_id = $1 AND is_deleted = FALSE),
                       chunk_count = chunk_count + $2,
                       updated_at = NOW()
                   WHERE id = $1""",
                kb_id, new_chunks
            )

    async def reprocess_document(
        self, doc_id: int, kb_id: int, tenant_id: int, user_id: int,
        oss_path: str, file_type: str,
        chunk_size: int = None, chunk_overlap: int = None
    ) -> dict:
        """重新处理单个文档（用于重建向量场景）

        从OSS下载原文件 → 解析 → 切块 → 向量化 → 入库

        Args:
            doc_id: 文档ID
            kb_id: 知识库ID
            tenant_id: 租户ID
            user_id: 用户ID
            oss_path: OSS存储路径
            file_type: 文件类型
            chunk_size: 切块大小
            chunk_overlap: 重叠字符数

        Returns:
            {"doc_id": int, "chunk_count": int, "status": str}
        """
        local_path = None
        try:
            # 1. 从OSS下载文件到本地临时目录
            if not oss_path or not self.oss_service or not self.oss_service.enabled:
                await self._update_document_status(doc_id, "failed", "OSS未启用或oss_path为空，无法重建")
                return {"doc_id": doc_id, "chunk_count": 0, "status": "failed"}

            file_content = await self.oss_service.download_file(oss_path)

            # 保存到临时文件（解析器需要文件路径）
            local_path = os.path.join(self.upload_dir, f"rebuild_{doc_id}.{file_type}")
            with open(local_path, "wb") as f:
                f.write(file_content)

            # 2. 解析文档
            text = await self._parse_document(local_path, file_type)
            if not text or text.startswith("解析失败") or "依赖未安装" in text:
                await self._update_document_status(doc_id, "failed", text)
                return {"doc_id": doc_id, "chunk_count": 0, "status": "failed"}

            # 3. 切块
            chunker = Chunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            chunks = chunker.split(text)
            if not chunks:
                await self._update_document_status(doc_id, "failed", "文档内容为空或无法切分")
                return {"doc_id": doc_id, "chunk_count": 0, "status": "failed"}

            # 4. 批量向量化
            chunk_texts = [c["content"] for c in chunks]
            embeddings = await asyncio.to_thread(embedding_service.encode, chunk_texts)

            # 5. 写入knowledge_chunk表
            chunk_count = await self._insert_chunks(
                doc_id, kb_id, tenant_id, user_id, chunks, embeddings
            )

            # 6. 更新文档状态 + 知识库统计
            await self._update_document_status(doc_id, "completed", chunk_count=chunk_count)
            await self._update_kb_stats(kb_id, chunk_count)

            return {"doc_id": doc_id, "chunk_count": chunk_count, "status": "completed"}

        except Exception as e:
            await self._update_document_status(doc_id, "failed", str(e))
            return {"doc_id": doc_id, "chunk_count": 0, "status": "failed"}
        finally:
            # 清理临时文件
            if local_path:
                try:
                    os.remove(local_path)
                except OSError:
                    pass

    @staticmethod
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
