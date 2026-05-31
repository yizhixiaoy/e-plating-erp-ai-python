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

    # 分类结果
    task_complexity: str                   # simple / medium / complex
    requires_confirmation: bool

    # 执行计划
    plan_steps: Optional[list[dict]]

    # 工具调用与结果
    tool_calls_pending: list[dict]
    tool_results: list[dict]

    # 知识库检索上下文
    knowledge_context: Optional[str]
    references: list[dict]

    # 响应
    final_response: Optional[str]
    token_usage: dict[str, int]

    # 错误
    error: Optional[str]
