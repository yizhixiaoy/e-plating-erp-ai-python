"""Pydantic数据模型定义"""
from __future__ import annotations
from typing import Optional, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


# ─── 引用来源 ─────────────────────────────────────────────
class SourceType(str, Enum):
    KNOWLEDGE = "knowledge"
    DATABASE = "database"
    UPLOAD = "upload"


class ReferenceSource(BaseModel):
    """引用来源"""
    source_type: SourceType = Field(..., description="来源类型")
    source_id: str = Field(..., description="来源ID（文档ID/表名/文件ID）")
    doc_title: str = Field(..., description="文档标题或表名")
    chunk_index: Optional[int] = Field(None, description="片段序号（知识库场景）")
    similarity: Optional[float] = Field(None, description="相似度（0-1）")
    page_number: Optional[int] = Field(None, description="页码（PDF文档场景）")
    section_title: Optional[str] = Field(None, description="章节标题")


# ─── 对话 ─────────────────────────────────────────────────
class ChatRequest(BaseModel):
    """对话请求"""
    query: str = Field(..., min_length=1, max_length=10000, description="用户提问")
    conversation_id: Optional[int] = Field(None, description="会话ID，为空则创建新会话")
    kb_ids: Optional[list[int]] = Field(None, description="指定知识库ID列表")
    file_ids: Optional[list[str]] = Field(None, description="上传的临时文件ID列表")


class ChatResponse(BaseModel):
    """对话响应（非流式）"""
    conversation_id: int
    message_id: int
    content: str
    references: list[ReferenceSource] = Field(default_factory=list)
    token_usage: dict[str, int] = Field(default_factory=dict)


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ConversationView(BaseModel):
    """会话视图"""
    id: int
    title: Optional[str] = None
    session_type: str = "chat"
    message_count: int = 0
    last_message_at: Optional[datetime] = None
    is_pinned: bool = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MessageView(BaseModel):
    """消息视图"""
    id: int
    conversation_id: int
    role: str
    content: Optional[str] = None
    model_name: Optional[str] = None
    tool_calls: Optional[Any] = None
    references: list[ReferenceSource] = Field(default_factory=list)
    token_count: Optional[int] = None
    token_usage: Optional[dict] = None
    file_ids: list[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        protected_namespaces = ()


# ─── SSE事件 ──────────────────────────────────────────────
class SSEEventType(str, Enum):
    THINKING = "thinking"
    PLAN = "plan"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    TOOL_ERROR = "tool_error"
    CHUNK = "chunk"
    REFERENCE = "reference"
    DONE = "done"
    ERROR = "error"


class SSEThinkingData(BaseModel):
    content: str


class SSEPlanData(BaseModel):
    steps: list[dict]


class SSEToolStartData(BaseModel):
    tool_name: str
    tool_params: dict
    step_index: int = 0


class SSEToolEndData(BaseModel):
    tool_name: str
    result_summary: str
    step_index: int = 0


class SSEToolErrorData(BaseModel):
    tool_name: str
    error_msg: str
    step_index: int = 0


class SSEChunkData(BaseModel):
    content: str


class SSEReferenceData(BaseModel):
    references: list[ReferenceSource]


class SSEDoneData(BaseModel):
    full_content: str
    token_usage: dict[str, int]
    conversation_id: int
    message_id: int


class SSEErrorData(BaseModel):
    message: str


# ─── 知识库 ───────────────────────────────────────────────
class KnowledgeBaseScope(str, Enum):
    GLOBAL = "global"
    TENANT = "tenant"
    PERSONAL = "personal"


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    scope_type: KnowledgeBaseScope = KnowledgeBaseScope.TENANT
    chunk_size: int = 500
    chunk_overlap: int = 100


class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    status: Optional[str] = None


class KnowledgeBaseView(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    scope_type: str
    doc_count: int = 0
    chunk_count: int = 0
    status: str = "active"
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DocumentView(BaseModel):
    id: int
    kb_id: int
    title: str
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    chunk_count: int = 0
    parse_status: str = "pending"
    parse_error: Optional[str] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChunkView(BaseModel):
    id: int
    doc_id: int
    chunk_index: int
    content: str
    token_count: Optional[int] = None
    metadata: dict = Field(default_factory=dict)

    class Config:
        from_attributes = True


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="检索关键词")
    kb_ids: Optional[list[int]] = Field(None, description="指定知识库，为空则所有可见库")
    top_k: int = Field(5, ge=1, le=20, description="返回数量")


class KnowledgeSearchResult(BaseModel):
    chunk_id: int
    doc_id: int
    doc_title: str
    kb_name: str
    chunk_index: int
    content: str
    similarity: float
    page_number: Optional[int] = None
    section_title: Optional[str] = None


# ─── 写作助手 ─────────────────────────────────────────────
class WriterTemplate(str, Enum):
    REPORT = "report"
    NOTICE = "notice"
    SUMMARY = "summary"
    CONTRACT = "contract"
    CUSTOM = "custom"


class WriterRequest(BaseModel):
    template_type: WriterTemplate = WriterTemplate.CUSTOM
    topic: str = Field(..., min_length=1, max_length=5000)
    key_points: Optional[list[str]] = Field(None, description="关键要点")
    style: str = "formal"          # formal / concise / detailed
    word_count: int = Field(500, ge=100, le=5000)
    ref_doc_ids: Optional[list[int]] = Field(None, description="参考文档ID列表")


# ─── 上传文档 ─────────────────────────────────────────────
class TempDocumentUpload(BaseModel):
    file_id: str
    file_name: str
    file_size: int
    parse_status: str = "pending"


# ─── 用户上下文 ───────────────────────────────────────────
class UserContext(BaseModel):
    """从Java网关透传的用户上下文"""
    tenant_id: int
    user_id: int
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    data_scope: Optional[str] = None
    auth_mode: str = "authenticated"  # authenticated / guest


# ─── 分页 ────────────────────────────────────────────────
class PageRequest(BaseModel):
    page_num: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class PageResult(BaseModel):
    total: int
    page_num: int
    page_size: int
    items: list
