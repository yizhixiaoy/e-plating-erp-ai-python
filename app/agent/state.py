"""LangGraph Agent状态定义"""
from __future__ import annotations
from typing import TypedDict, Annotated, Optional, Any
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from app.models.schemas import UserContext, ReferenceSource


class AgentState(TypedDict):
    """Agent状态"""
    # 用户输入与上下文
    messages: Annotated[list[BaseMessage], add_messages]
    query: str
    user_context: UserContext
    conversation_id: Optional[int]
    kb_ids: Optional[list[int]]          # 用户指定的知识库ID列表
    file_ids: Optional[list[str]]        # 用户上传的临时文件ID列表

    # 分类结果
    task_complexity: str                   # simple / medium / complex
    requires_confirmation: bool

    # 执行计划
    plan_steps: Optional[list[dict]]
    plan_confirmed: bool                      # 用户已确认执行计划

    # 工具调用与结果
    tool_calls_pending: list[dict]
    tool_results: list[dict]

    # 知识库检索上下文
    knowledge_context: Optional[str]
    references: list[dict]

    # 多轮对话上下文
    memory_summary: Optional[str]           # 长期记忆摘要（注入System Prompt）
    conversation_history: Optional[list[dict]]  # 会话历史消息列表 [{"role": "user"|"assistant", "content": "..."}]

    # 响应
    final_response: Optional[str]
    token_usage: dict[str, int]

    # 错误
    error: Optional[str]

    # Token过期标记（Python→Java返回401时，前端全局跳转登录页）
    token_expired: Optional[bool]
