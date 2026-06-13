"""对话接口 - SSE流式输出，支持多轮对话历史管理"""
import json
import asyncio
import time
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from app.models.schemas import ChatRequest
from app.services.llm_factory import create_llm
from app.services.context_manager import compress_history
from app.config import settings

router = APIRouter(prefix="/api/ai/chat", tags=["AI对话"])


# ─── 会话管理：创建/获取/更新 ─────────────────────────────

async def get_or_create_conversation(
    db_pool, tenant_id: int, user_id: int,
    conversation_id: int | None
) -> tuple[int, bool]:
    """
    获取或创建会话

    Returns:
        (conversation_id, is_new)
    """
    async with db_pool.acquire() as conn:
        # 尝试获取已有会话
        if conversation_id:
            row = await conn.fetchrow(
                """SELECT id, message_count FROM conversation
                   WHERE id = $1 AND user_id = $2 AND tenant_id = $3
                     AND is_deleted = FALSE""",
                conversation_id, user_id, tenant_id
            )
            if row:
                return row["id"], False

        # 创建新会话
        new_id = await conn.fetchval(
            """INSERT INTO conversation
               (tenant_id, user_id, session_type, last_message_at,
                created_by, created_at, updated_at)
               VALUES ($1, $2, 'chat', NOW(), $2, NOW(), NOW())
               RETURNING id""",
            tenant_id, user_id
        )
        return new_id, True


async def persist_messages(
    db_pool, conversation_id: int, tenant_id: int, user_id: int,
    query: str, full_response: str, references: list,
    token_usage: dict, model_name: str
) -> int:
    """持久化用户消息和AI回复到conversation_message表

    Returns:
        AI回复消息的ID
    """
    ai_message_id = None
    async with db_pool.acquire() as conn:
        # 写入用户消息
        await conn.execute(
            """INSERT INTO conversation_message
               (conversation_id, tenant_id, role, content,
                token_count, created_by, created_at, updated_at)
               VALUES ($1, $2, 'user', $3, $4, $5, NOW(), NOW())""",
            conversation_id, tenant_id, query,
            len(query) // 2, user_id
        )

        # 写入AI回复
        ai_message_id = await conn.fetchval(
            """INSERT INTO conversation_message
               (conversation_id, tenant_id, role, content,
                model_name, references, token_usage,
                created_by, created_at, updated_at)
               VALUES ($1, $2, 'assistant', $3, $4, $5, $6, $7, NOW(), NOW())
               RETURNING id""",
            conversation_id, tenant_id, full_response,
            model_name,
            json.dumps(references, ensure_ascii=False) if references else "[]",
            json.dumps(token_usage) if token_usage else "{}",
            user_id
        )

        # 更新会话元数据
        total_new_tokens = (token_usage or {}).get("input", 0) + (token_usage or {}).get("output", 0)
        await conn.execute(
            """UPDATE conversation
               SET message_count = message_count + 2,
                   total_tokens = total_tokens + $2,
                   last_message_at = NOW(),
                   updated_by = $3,
                   updated_at = NOW()
               WHERE id = $1""",
            conversation_id, total_new_tokens, user_id
        )

    return ai_message_id


async def load_conversation_history(db_pool, conversation_id: int) -> list[dict]:
    """
    从数据库加载会话历史消息

    Returns:
        历史消息列表 [{"role": "user"|"assistant", "content": "..."}]
    """
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT role, content FROM conversation_message
               WHERE conversation_id = $1 AND is_deleted = FALSE
                 AND role IN ('user', 'assistant')
               ORDER BY created_at ASC""",
            conversation_id
        )
    return [{"role": row["role"], "content": row["content"]} for row in rows]


async def auto_generate_title(
    db_pool, conversation_id: int, first_message: str, llm
):
    """异步生成会话标题并更新到数据库"""
    try:
        from app.agent.nodes import generate_conversation_title
        title = await generate_conversation_title(first_message, llm)

        async with db_pool.acquire() as conn:
            await conn.execute(
                """UPDATE conversation
                   SET title = $1, updated_at = NOW()
                   WHERE id = $2 AND (title IS NULL OR title = '')""",
                title, conversation_id
            )
    except Exception:
        # 降级：使用消息前N字作为标题
        max_len = settings.CONVERSATION_TITLE_MAX_LENGTH
        fallback_title = first_message[:max_len] if len(first_message) > max_len else first_message
        async with db_pool.acquire() as conn:
            await conn.execute(
                """UPDATE conversation
                   SET title = $1, updated_at = NOW()
                   WHERE id = $2 AND (title IS NULL OR title = '')""",
                fallback_title, conversation_id
            )


async def extract_long_term_memory(
    memory_service, tenant_id: int, user_id: int,
    query: str, response: str
):
    """异步提取长期记忆（非阻塞）"""
    try:
        await memory_service.add_memory(
            tenant_id, user_id,
            f"用户提问: {query}\nAI回答摘要: {response[:settings.MEMORY_EXTRACT_MAX_LENGTH]}",
            memory_type="fact",
            importance=settings.MEMORY_DEFAULT_IMPORTANCE
        )
    except Exception:
        pass  # 记忆提取失败不影响主流程


# ─── SSE流式生成器（有状态多轮对话版本） ────────────────────

async def chat_stream_generator(
    query: str,
    user_context,
    conversation_id: int | None,
    agent_graph,
    db_pool,
    memory_service,
    chat_llm,
    kb_ids: list[int] | None = None,
    file_ids: list[str] | None = None
):
    """
    SSE流式生成器 - 有状态多轮对话版本

    完整流程：
    1. 获取或创建会话
    2. 加载长期记忆
    3. 加载会话历史
    4. 可选压缩过长历史
    5. 运行Agent图（传入完整上下文）
    6. 持久化消息
    7. 异步生成标题 / 提取记忆
    8. 发射done事件
    """
    start_time = time.time()

    try:
        # ── 步骤1：获取或创建会话 ──
        conversation_id, is_new = await get_or_create_conversation(
            db_pool, user_context.tenant_id, user_context.user_id,
            conversation_id
        )

        # ── 步骤2：加载长期记忆（注入System Prompt） ──
        memory_summary = ""
        if memory_service:
            memory_summary = await memory_service.summarize_memories(
                user_context.tenant_id, user_context.user_id
            )

        # ── 步骤3：加载会话历史消息 ──
        conversation_history = await load_conversation_history(db_pool, conversation_id)

        # ── 步骤4：过长历史压缩（异步，使用chat_llm） ──
        if len(conversation_history) > settings.CHAT_COMPRESS_HISTORY_THRESHOLD:
            conversation_history = await compress_history(
                conversation_history, keep_recent=settings.CHAT_COMPRESS_KEEP_RECENT, llm=chat_llm
            )

        # ── 步骤5：构建Agent输入状态 ──
        from app.agent.state import AgentState
        from langchain_core.messages import HumanMessage

        initial_state: AgentState = {
            "messages": [HumanMessage(content=query)],
            "query": query,
            "user_context": user_context,
            "conversation_id": conversation_id,
            "kb_ids": kb_ids,
            "file_ids": file_ids,
            "task_complexity": "simple",
            "requires_confirmation": False,
            "plan_steps": [],
            "tool_calls_pending": [],
            "tool_results": [],
            "knowledge_context": None,
            "references": [],
            "memory_summary": memory_summary,
            "conversation_history": conversation_history,
            "final_response": None,
            "token_usage": {},
            "error": None
        }

        # ── 发射thinking事件 ──
        yield {
            "event": "thinking",
            "data": json.dumps({"content": "收到您的问题，正在分析..."}, ensure_ascii=False)
        }

        # ── 步骤6：运行Agent图 ──
        config = {
            "configurable": {
                "thread_id": f"conv_{conversation_id}"
            }
        }

        full_response = ""
        references = []
        token_usage = {}

        async for event in agent_graph.astream_events(initial_state, config=config, version="v2"):
            event_type = event.get("event", "")
            event_name = event.get("name", "")

            if event_type == "on_tool_start":
                # 工具调用开始
                tool_input = event["data"].get("input", {})
                yield {
                    "event": "tool_start",
                    "data": json.dumps({
                        "tool_name": event_name,
                        "tool_params": tool_input,
                        "step_index": 0
                    }, ensure_ascii=False)
                }
                yield {
                    "event": "thinking",
                    "data": json.dumps({
                        "content": f"正在调用工具: {event_name}..."
                    }, ensure_ascii=False)
                }

            elif event_type == "on_tool_end":
                # 工具调用结束
                output = event["data"].get("output", {})
                result_summary = ""
                if isinstance(output, dict):
                    content_text = output.get("content", str(output))
                    result_summary = content_text[:100] if content_text else "完成"
                    # 提取引用来源
                    if "references" in output:
                        refs = output["references"]
                        if refs:
                            yield {
                                "event": "reference",
                                "data": json.dumps(refs, ensure_ascii=False)
                            }
                            references.extend(refs)
                yield {
                    "event": "tool_end",
                    "data": json.dumps({
                        "tool_name": event_name,
                        "result_summary": result_summary,
                        "step_index": 0
                    }, ensure_ascii=False)
                }

            elif event_type == "on_chat_model_stream":
                # LLM流式输出 - 仅捕获aggregator节点的最终回答
                # 使用tags精确过滤：LangGraph为每个节点添加tag标识
                # 避免捕获classifier/planner/executor节点的LLM中间输出
                event_tags = event.get("tags", [])
                is_aggregator = (
                    event_name == "aggregator"
                    or "aggregator" in event_tags
                )
                chunk = event["data"].get("chunk", {})
                if is_aggregator and hasattr(chunk, "content") and chunk.content:
                    content = chunk.content
                    full_response += content
                    yield {
                        "event": "chunk",
                        "data": json.dumps({"content": content}, ensure_ascii=False)
                    }

            elif event_type == "on_chain_end" and event_name == "aggregator":
                # Aggregator节点完成 - 提取最终token用量
                output = event["data"].get("output", {})
                if isinstance(output, dict):
                    if "token_usage" in output:
                        token_usage = output["token_usage"]
                    if "references" in output and output["references"]:
                        refs = output["references"]
                        references.extend(refs)
                        yield {
                            "event": "reference",
                            "data": json.dumps(refs, ensure_ascii=False)
                        }

        # ── 步骤7：持久化消息到数据库 ──
        ai_message_id = await persist_messages(
            db_pool, conversation_id, user_context.tenant_id,
            user_context.user_id, query, full_response,
            references, token_usage, settings.LLM_MODEL_CHAT
        )

        # ── 步骤8：异步任务（标题生成 + 记忆提取） ──
        if is_new:
            asyncio.create_task(
                auto_generate_title(db_pool, conversation_id, query, chat_llm)
            )

        if memory_service and settings.MEM0_ENABLED:
            asyncio.create_task(
                extract_long_term_memory(
                    memory_service, user_context.tenant_id,
                    user_context.user_id, query, full_response
                )
            )

        # ── 步骤9：发射done事件 ──
        duration_sec = round(time.time() - start_time, 2)
        yield {
            "event": "done",
            "data": json.dumps({
                "full_content": full_response,
                "token_usage": token_usage or {
                    "input": len(query) // 2,
                    "output": len(full_response) // 2
                },
                "conversation_id": conversation_id,
                "message_id": ai_message_id,
                "duration_sec": duration_sec
            }, ensure_ascii=False)
        }

    except Exception as e:
        yield {
            "event": "error",
            "data": json.dumps({"message": f"处理异常: {str(e)}"}, ensure_ascii=False)
        }


# ─── 对话接口入口 ──────────────────────────────────────────

@router.post("")
async def chat(request: ChatRequest, req: Request):
    """
    AI对话接口 - SSE流式输出

    接收用户问题，通过LangGraph Agent处理后流式返回结果。
    支持多轮对话：通过conversation_id关联同一会话的历史消息。

    事件类型：thinking / plan / tool_start / tool_end / chunk / reference / done / error
    """
    user_context = req.state.user_context
    auth_headers = req.state.auth_headers

    # 访客模式仅允许基础问答
    if user_context.auth_mode == "guest":
        return EventSourceResponse(
            _guest_chat_stream(request.query),
            media_type="text/event-stream"
        )

    # 从app.state获取全局依赖
    agent_graph = req.app.state.agent_graph
    db_pool = req.app.state.db_pool
    tools = req.app.state.tools
    memory_service = getattr(req.app.state, "memory_service", None)
    chat_llm = req.app.state.chat_llm

    # 注入当前请求的认证头到ErpQueryTool
    if "erp_query_tool" in tools:
        tools["erp_query_tool"].set_auth_headers(auth_headers)

    return EventSourceResponse(
        chat_stream_generator(
            query=request.query,
            user_context=user_context,
            conversation_id=request.conversation_id,
            agent_graph=agent_graph,
            db_pool=db_pool,
            memory_service=memory_service,
            chat_llm=chat_llm,
            kb_ids=request.kb_ids,
            file_ids=request.file_ids
        ),
        media_type="text/event-stream"
    )


# ─── 访客模式（无状态） ────────────────────────────────────

async def _guest_chat_stream(query: str):
    """访客模式聊天（仅基础问答，无工具调用、无历史持久化）"""
    guest_prompt = """你是电镀行业ERP系统"智镀云AI"的客服助手。当前用户尚未登录。
请：
1. 友好地介绍系统功能
2. 引导用户登录或注册
3. 回答关于系统的通用问题
4. 不能查询任何业务数据或知识库内容"""

    llm = create_llm(streaming=True)

    yield {
        "event": "thinking",
        "data": json.dumps({"content": "正在处理您的问题..."}, ensure_ascii=False)
    }

    full_response = ""
    try:
        from langchain_core.messages import SystemMessage, HumanMessage
        messages = [SystemMessage(content=guest_prompt), HumanMessage(content=query)]
        async for chunk in llm.astream(messages):
            if chunk.content:
                full_response += chunk.content
                yield {
                    "event": "chunk",
                    "data": json.dumps({"content": chunk.content}, ensure_ascii=False)
                }

        yield {
            "event": "done",
            "data": json.dumps({
                "full_content": full_response,
                "token_usage": {"input": len(query) // 2, "output": len(full_response) // 2}
            }, ensure_ascii=False)
        }
    except Exception as e:
        yield {
            "event": "error",
            "data": json.dumps({"message": f"处理异常: {str(e)}"}, ensure_ascii=False)
        }
