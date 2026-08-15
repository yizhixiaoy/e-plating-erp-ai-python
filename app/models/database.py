"""PostgreSQL数据库连接管理"""
import asyncpg
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import BigInteger, Integer, Text, Float, Boolean, DateTime, String, func
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from pgvector.sqlalchemy import Vector

from app.config import settings


# ─── 异步引擎 ─────────────────────────────────────────
DATABASE_URL_ASYNC = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(
    DATABASE_URL_ASYNC,
    echo=settings.DEBUG,
    pool_size=settings.PG_POOL_MAX,
    max_overflow=5,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """ORM基类"""
    pass


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """获取异步数据库会话"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ─── SQLAlchemy ORM模型 ─────────────────────────────

class Conversation(Base):
    """会话表"""
    __tablename__ = "conversation"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    session_type: Mapped[str] = mapped_column(String(20), default="chat")
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, comment="逻辑删除")
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="创建人用户ID")
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="修改人用户ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ConversationMessage(Base):
    """消息表"""
    __tablename__ = "conversation_message"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, comment="user/assistant/system/tool")
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="生成该消息的模型标识")
    tool_calls: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    tool_call_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tool_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="本条消息Token总数")
    token_usage: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="Token明细 {input,output,total}")
    file_ids: Mapped[list] = mapped_column(JSONB, default=list, comment="关联的临时文件ID列表")
    references: Mapped[list] = mapped_column(JSONB, default=list, key="references")
    is_streaming: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, comment="逻辑删除")
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="创建人用户ID")
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="修改人用户ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class KnowledgeBase(Base):
    """知识库表"""
    __tablename__ = "knowledge_base"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="公共库为NULL")
    scope_type: Mapped[str] = mapped_column(String(20), default="tenant", comment="global/tenant/personal")
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding_model: Mapped[str] = mapped_column(String(50), default="bge-large-zh-v1.5")
    chunk_size: Mapped[int] = mapped_column(Integer, default=500)
    chunk_overlap: Mapped[int] = mapped_column(Integer, default=100)
    status: Mapped[str] = mapped_column(String(20), default="active")
    doc_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, comment="逻辑删除")
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="创建人用户ID")
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="修改人用户ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class KnowledgeDocument(Base):
    """文档表"""
    __tablename__ = "knowledge_document"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    kb_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tenant_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="pdf/docx/txt/md/xlsx/pptx/png/jpg")
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="字节数")
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="本地路径（保留兼容）")
    oss_path: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="OSS对象存储路径（持久备份）")
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="MIME类型")
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="文件SHA256哈希（去重/完整性校验）")
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    parse_status: Mapped[str] = mapped_column(String(20), default="pending", comment="pending/parsing/completed/failed")
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, comment="逻辑删除")
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="上传人用户ID")
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="修改人用户ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class KnowledgeChunk(Base):
    """文档片段表（含向量）"""
    __tablename__ = "knowledge_chunk"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    doc_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    kb_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024), nullable=True)
    metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, comment="逻辑删除")
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="创建人用户ID")
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="修改人用户ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class AgentKnowledgeBinding(Base):
    """Agent-知识库关联表"""
    __tablename__ = "agent_knowledge_binding"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    agent_id: Mapped[str] = mapped_column(String(50), nullable=False)
    kb_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    top_k: Mapped[int] = mapped_column(Integer, default=5)
    score_threshold: Mapped[float] = mapped_column(Float, default=0.6)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, comment="逻辑删除")
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="创建人用户ID")
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="修改人用户ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class KnowledgeBaseTag(Base):
    """知识库标签表"""
    __tablename__ = "knowledge_base_tag"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    kb_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tenant_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    tag_name: Mapped[str] = mapped_column(String(50), nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="manual", comment="manual/ai_recommended")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, comment="逻辑删除")
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="创建人用户ID")
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="修改人用户ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class UserLongTermMemory(Base):
    """用户长期记忆表"""
    __tablename__ = "user_long_term_memory"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    memory_type: Mapped[str] = mapped_column(String(50), default="fact", comment="fact/preference/pattern")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024), nullable=True)
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, comment="逻辑删除")
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="创建人用户ID")
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="修改人用户ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class TempDocument(Base):
    """临时上传文档表（24小时清理）"""
    __tablename__ = "temp_document"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    file_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    conversation_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="所属会话ID")
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, default=0)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False, comment="文件路径（兼容字段）")
    oss_path: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="OSS临时存储路径（对话文档备份）")
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="MIME类型")
    parsed_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    parse_status: Mapped[str] = mapped_column(String(20), default="pending")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, comment="逻辑删除（配合定时清理）")
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="过期时间")
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="创建人用户ID")
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="修改人用户ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class AiAuditLog(Base):
    """AI操作审计日志表"""
    __tablename__ = "ai_audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False, comment="操作类型")
    target_type: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="目标类型")
    target_id: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="目标ID")
    request_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="请求数据")
    response_summary: Mapped[str | None] = mapped_column(Text, nullable=True, comment="响应摘要")
    tool_calls: Mapped[list | None] = mapped_column(JSONB, nullable=True, comment="工具调用记录")
    token_usage: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="Token消耗")
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="耗时毫秒")
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="客户端UA")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, comment="逻辑删除")
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="创建人用户ID")
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="修改人用户ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
