"""对话接口 - SSE流式输出，支持多轮对话历史管理"""
import json
import asyncio
import time
import traceback
import logging
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from app.models.schemas import ChatRequest
from app.services.llm_factory import create_llm
from app.services.context_manager import compress_history
from app.services.cache import get_or_set, flush_namespace, CacheNS
from app.services.permissions import require_perm, AI_PERMS, is_platform_admin
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai/chat", tags=["AI对话"])
_CONV_LIST_TTL = 120  # 会话列表缓存2分钟


# ─── 会话管理：创建/获取/更新 ─────────────────────────────

async def get_or_create_conversation(
    db_pool, tenant_id: int, user_id: int,
    conversation_id: int | None,
    is_admin: bool = False
) -> tuple[int, bool]:
    """
    获取或创建会话

    Args:
        is_admin: 平台管理员时跳过租户隔离，可跨租户访问

    Returns:
        (conversation_id, is_new)
    """
    async with db_pool.acquire() as conn:
        # 尝试获取已有会话
        if conversation_id:
            if is_admin:
                # 平台管理员：跨租户查找（仅按id查找）
                row = await conn.fetchrow(
                    """SELECT id, message_count FROM conversation
                       WHERE id = $1 AND is_deleted = FALSE""",
                    conversation_id
                )
            else:
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
        await flush_namespace(CacheNS.CONV_LIST)
        return new_id, True


async def persist_user_message(
    db_pool, conversation_id: int, tenant_id: int, user_id: int,
    query: str
) -> None:
    """仅持久化用户消息（用于plan_pending场景：plan不是正式答案，不入库）"""
    async with db_pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO conversation_message
               (conversation_id, tenant_id, role, content,
                token_count, created_by, created_at, updated_at)
               VALUES ($1, $2, 'user', $3, $4, $5, NOW(), NOW())""",
            conversation_id, tenant_id, query,
            len(query) // 2, user_id
        )
        await conn.execute(
            """UPDATE conversation
               SET message_count = message_count + 1,
                   last_message_at = NOW(),
                   updated_by = $2,
                   updated_at = NOW()
               WHERE id = $1""",
            conversation_id, user_id
        )
    await flush_namespace(CacheNS.CONV_LIST)


async def persist_messages(
    db_pool, conversation_id: int, tenant_id: int, user_id: int,
    query: str, full_response: str, references: list,
    token_usage: dict, model_name: str,
    thinking_steps: list = None,
    duration_sec: float = None,
    skip_user_message: bool = False
) -> int:
    """持久化用户消息和AI回复到conversation_message表

    Args:
        skip_user_message: True时跳过用户消息写入（用于plan确认场景，"确认执行计划"不需要落库）

    Returns:
        AI回复消息的ID
    """
    ai_message_id = None
    async with db_pool.acquire() as conn:
        if not skip_user_message:
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
                model_name, "references", token_usage, thinking_steps, duration_sec,
                created_by, created_at, updated_at)
               VALUES ($1, $2, 'assistant', $3, $4, $5, $6, $7, $8, $9, NOW(), NOW())
               RETURNING id""",
            conversation_id, tenant_id, full_response,
            model_name,
            json.dumps(references, ensure_ascii=False) if references else "[]",
            json.dumps(token_usage) if token_usage else "{}",
            json.dumps(thinking_steps or [], ensure_ascii=False),
            duration_sec,
            user_id
        )

        # 更新会话元数据
        total_new_tokens = (token_usage or {}).get("input", 0) + (token_usage or {}).get("output", 0)
        msg_count_increment = 1 if skip_user_message else 2
        await conn.execute(
            """UPDATE conversation
               SET message_count = message_count + $2,
                   total_tokens = total_tokens + $3,
                   last_message_at = NOW(),
                   updated_by = $4,
                   updated_at = NOW()
               WHERE id = $1""",
            conversation_id, msg_count_increment, total_new_tokens, user_id
        )

    await flush_namespace(CacheNS.CONV_LIST)
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


async def _generate_and_save_title(
    db_pool, conversation_id: int, first_message: str, llm
) -> str:
    """同步生成会话标题、写入数据库并返回标题文本

    使用专用非推理LLM（thinking=OFF, streaming=OFF）直接生成标题，
    避免推理模型可能返回空content的问题。
    """
    title = None
    try:
        # 创建专用标题生成LLM：低温度、无需思考和流式
        from app.services.llm_factory import create_chat_llm
        from langchain_core.messages import HumanMessage
        from app.agent.nodes import TITLE_GENERATION_PROMPT, _get_llm_content

        title_llm = create_chat_llm(
            temperature=settings.TITLE_GEN_TEMPERATURE,
            max_tokens=settings.TITLE_GEN_MAX_TOKENS,
            streaming=False,
            enable_thinking=False
        )

        prompt = TITLE_GENERATION_PROMPT.format(first_message=first_message)
        response = await title_llm.ainvoke([HumanMessage(content=prompt)])
        # 防御性提取：兼容思考模式content为空的情况
        raw_content = _get_llm_content(response)
        title = raw_content.strip() if raw_content else None

        if not title:
            logger.warning("[标题生成] LLM返回空content，使用fallback")
    except Exception as e:
        logger.warning("[标题生成] LLM调用失败: %s，使用fallback", e)

    # 使用LLM结果或fallback
    if not title:
        max_len = settings.CONVERSATION_TITLE_MAX_LENGTH
        title = first_message[:max_len] if len(first_message) > max_len else first_message

    # 截断到上限
    max_len = settings.CONVERSATION_TITLE_MAX_LENGTH
    if len(title) > max_len:
        title = title[:max_len]

    # 写入数据库
    try:
        async with db_pool.acquire() as conn:
            await conn.execute(
                """UPDATE conversation
                   SET title = $1, updated_at = NOW()
                   WHERE id = $2""",
                title, conversation_id
            )
    except Exception as e:
        logger.error("[标题生成] 数据库写入失败: %s", e)

    logger.info("[标题生成] conversation=%d title=%r", conversation_id, title)
    return title


async def auto_generate_title(
    db_pool, conversation_id: int, first_message: str, llm
):
    """异步生成会话标题（已弃用，保留兼容）"""
    await _generate_and_save_title(db_pool, conversation_id, first_message, llm)


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
    file_ids: list[str] | None = None,
    confirmed_plan: list[dict] | None = None,
    original_query: str | None = None
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
        admin_mode = is_platform_admin(user_context)
        conversation_id, is_new = await get_or_create_conversation(
            db_pool, user_context.tenant_id, user_context.user_id,
            conversation_id, is_admin=admin_mode
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

        # 确认plan时：使用原始用户问题作为query（而非"确认执行计划"），让aggregator有正确上下文
        effective_query = original_query if (confirmed_plan and original_query) else query

        initial_state: AgentState = {
            "messages": [HumanMessage(content=effective_query)],
            "query": effective_query,
            "user_context": user_context,
            "conversation_id": conversation_id,
            "kb_ids": kb_ids,
            "file_ids": file_ids,
            "task_complexity": "simple",
            "requires_confirmation": False,
            "plan_steps": confirmed_plan or [],
            "plan_confirmed": bool(confirmed_plan),
            "tool_calls_pending": [],
            "tool_results": [],
            "knowledge_context": None,
            "references": [],
            "memory_summary": memory_summary,
            "conversation_history": conversation_history,
            "final_response": None,
            "token_usage": {},
            "error": None,
            "token_expired": None
        }

        # ── 发射初始thinking事件（提示用户已开始处理）──
        yield {
            "event": "thinking",
            "data": json.dumps({"content": "收到您的问题，正在分析..."}, ensure_ascii=False)
        }

        # ── 步骤6：运行Agent图(使用 messages stream mode 获取 LLM token) ──
        config = {
            "configurable": {
                "thread_id": f"conv_{conversation_id}"
            }
        }

        full_response = ""
        references = []
        token_usage = {}
        thinking_steps = []
        step_start = time.time()
        fallback_content = ""  # 从节点更新中提取的兜底内容
        chunk_count = 0  # 统计接收的 chunk 数量
        captured_plan_steps = []  # 从planner节点输出中捕获的plan步骤

        # ── 思考内容按节点拼接缓冲区 ──
        # reasoning_content 逐chunk返回前端（实时），但落库时按节点合并为一个thinking条目
        current_thinking_buffer = ""          # 当前节点累积的推理文本
        current_thinking_start_ts = 0.0       # 当前节点首个thinking chunk的时间戳
        token_expired_detected = False        # Python→Java返回401标记

        def _flush_thinking_node():
            """将当前节点的思考缓冲区合并为一条thinking记录落库"""
            nonlocal current_thinking_buffer, current_thinking_start_ts
            if current_thinking_buffer:
                thinking_steps.append({
                    "type": "thinking",
                    "content": current_thinking_buffer,
                    "timestamp": current_thinking_start_ts
                })
                current_thinking_buffer = ""
                current_thinking_start_ts = 0.0

        # 初始thinking提示（独立条目，不属于任何节点缓冲区）
        thinking_steps.append({"type": "thinking", "content": "收到您的问题，正在分析...", "timestamp": 0.0})

        # 使用 astream + messages mode 获取 LLM token 流式输出
        async for chunk in agent_graph.astream(
            initial_state,
            config=config,
            stream_mode=["messages", "updates"],
            version="v2"
        ):
            chunk_type = chunk["type"]
            
            if chunk_type == "messages":
                # LLM token 流式输出
                message_chunk, metadata = chunk["data"]
                event_name = metadata.get("langgraph_node", "")
                event_tags = metadata.get("tags", [])
                
                # 只处理 aggregator 节点的输出
                is_aggregator = (
                    event_name == "aggregator"
                    or "aggregator" in event_tags
                    or any("aggregator" in str(t) for t in event_tags)
                )
                if not is_aggregator:
                    continue
                
                # ── 提取推理过程（reasoning_content）：每个chunk立即返回前端，但累积到节点缓冲区 ──
                if hasattr(message_chunk, "additional_kwargs"):
                    reasoning = message_chunk.additional_kwargs.get("reasoning_content", "")
                    if reasoning:
                        # 记录首个chunk的时间戳
                        if not current_thinking_buffer:
                            current_thinking_start_ts = round(time.time() - step_start, 1)
                        current_thinking_buffer += reasoning
                        # 每个chunk仍然实时返回前端（流式体验不变）
                        yield {
                            "event": "thinking",
                            "data": json.dumps({"content": reasoning}, ensure_ascii=False)
                        }
                
                # ── 提取正文内容（content）──
                if hasattr(message_chunk, "content") and message_chunk.content:
                    content = message_chunk.content
                    chunk_count += 1
                    # 正文首次到达时：flush当前节点的思考缓冲区（标志着思考阶段结束）
                    if chunk_count == 1:
                        _flush_thinking_node()
                    full_response += content
                    yield {
                        "event": "chunk",
                        "data": json.dumps({"content": content}, ensure_ascii=False)
                    }
            
            elif chunk_type == "updates":
                # 节点状态更新 - 提取工具调用、计划和引用
                for node_name, node_output in chunk["data"].items():
                    if isinstance(node_output, dict):
                        logger.info("[SSE] 节点 %s 输出keys: %s", node_name, list(node_output.keys()))
                        # 检测Token过期标记（Python→Java返回401，全局处理）
                        if node_output.get("token_expired"):
                            token_expired_detected = True

                        # 提取执行计划（planner节点输出）
                        if "plan_steps" in node_output and node_output["plan_steps"]:
                            plan_steps_data = node_output["plan_steps"]
                            captured_plan_steps = plan_steps_data  # 捕获用于plan_pending判定
                            # flush当前节点的思考缓冲区（planner开始，新的思考阶段）
                            _flush_thinking_node()
                            ts = round(time.time() - step_start, 1)
                            thinking_steps.append({
                                "type": "plan",
                                "content": f"已规划{len(plan_steps_data)}个执行步骤",
                                "timestamp": ts
                            })
                            yield {
                                "event": "plan",
                                "data": json.dumps({"steps": plan_steps_data}, ensure_ascii=False)
                            }

                        # 提取工具调用信息
                        if "tool_calls_pending" in node_output and node_output["tool_calls_pending"]:
                            # flush当前节点的思考缓冲区（工具调用开始，新的思考阶段）
                            _flush_thinking_node()
                            for tool_call in node_output["tool_calls_pending"]:
                                tool_name = tool_call.get("tool_name", "")
                                ts = round(time.time() - step_start, 1)
                                thinking_steps.append({
                                    "type": "tool_start",
                                    "content": f"调用 {tool_name}",
                                    "toolName": tool_name,
                                    "timestamp": ts
                                })
                                yield {
                                    "event": "tool_start",
                                    "data": json.dumps({
                                        "tool_name": tool_name,
                                        "tool_params": tool_call.get("tool_args", {}),
                                        "step_index": 0
                                    }, ensure_ascii=False)
                                }

                        # 提取工具执行结果 → 发射tool_end/tool_error事件
                        if "tool_results" in node_output and node_output["tool_results"]:
                            for tr in node_output["tool_results"]:
                                tool_name = tr.get("tool_name", "unknown")
                                ts = round(time.time() - step_start, 1)
                                if "error" in tr:
                                    # 工具执行失败（权限不足、异常等）
                                    error_msg = tr["error"]
                                    thinking_steps.append({
                                        "type": "tool_end",
                                        "content": f"{tool_name} 失败: {error_msg}",
                                        "toolName": tool_name,
                                        "timestamp": ts
                                    })
                                    yield {
                                        "event": "tool_error",
                                        "data": json.dumps({
                                            "tool_name": tool_name,
                                            "error_msg": error_msg,
                                            "step_index": 0
                                        }, ensure_ascii=False)
                                    }
                                else:
                                    # 工具执行成功 → 提取摘要
                                    result_data = tr.get("result", {})
                                    if isinstance(result_data, dict):
                                        summary = result_data.get("content", str(result_data))[:100]
                                    else:
                                        summary = str(result_data)[:100]
                                    thinking_steps.append({
                                        "type": "tool_end",
                                        "content": f"{tool_name}: {summary}",
                                        "toolName": tool_name,
                                        "timestamp": ts
                                    })
                                    yield {
                                        "event": "tool_end",
                                        "data": json.dumps({
                                            "tool_name": tool_name,
                                            "result_summary": summary,
                                            "step_index": 0
                                        }, ensure_ascii=False)
                                    }
                        
                        # 提取引用（去重：只发送本轮新增的引用，避免aggregator透传state导致前端重复展示）
                        if "references" in node_output and node_output["references"]:
                            refs = node_output["references"]
                            new_refs = [r for r in refs if r not in references]
                            if new_refs:
                                references.extend(new_refs)
                                yield {
                                    "event": "reference",
                                    "data": json.dumps(new_refs, ensure_ascii=False)
                                }
                        
                        # 提取 token 用量和最终响应(兜底)
                        if "token_usage" in node_output and node_output["token_usage"]:
                            token_usage = node_output["token_usage"]
                        if "final_response" in node_output and node_output["final_response"] and not full_response:
                            fallback_content = node_output["final_response"]

        # ── 步骤7：检测plan_pending（Plan是中间态，不落库） ──
        # 最后flush：确保尾部思考内容不丢失
        _flush_thinking_node()
        
        # ── 兜底：如果流式未捕获到正文，使用 on_chat_model_end / on_chain_end 的内容 ──
        if not full_response and fallback_content:
            full_response = fallback_content
            logger.warning("[SSE] 流式未捕获内容，使用兜底: len=%d, preview=%r",
                           len(full_response), full_response[:100])
            # 补发 chunk 事件，前端能立即看到内容
            yield {
                "event": "chunk",
                "data": json.dumps({"content": full_response}, ensure_ascii=False)
            }
        elif not full_response:
            logger.warning("[SSE] 流式和兜底均无内容! chunks=%d, fallback_empty=True", chunk_count)

        duration_sec = round(time.time() - start_time, 2)
        logger.info(
            "[SSE] 流式生成完成: chunks=%d, full_response_len=%d, thinking_steps=%d, duration=%.1fs",
            chunk_count, len(full_response), len(thinking_steps), duration_sec
        )

        # ── 检测plan_pending：plan不是正式答案，只通过SSE实时展示，不落库 ──
        plan_pending = False
        # 判定条件：无正文chunk + 兜底内容含"执行计划" + 从planner捕获了plan步骤且未确认
        if not chunk_count and fallback_content and "执行计划" in fallback_content and captured_plan_steps:
            plan_pending = True

        ai_message_id = None
        conversation_title = None

        if plan_pending:
            # ── Plan模式：仅保存用户消息，plan不落库 ──
            logger.info("[SSE] plan_pending=True，仅保存用户消息，plan不入库")
            await persist_user_message(
                db_pool, conversation_id, user_context.tenant_id,
                user_context.user_id, query
            )
        else:
            # ── 正常模式：保存用户消息 + AI回复 ──
            ai_message_id = await persist_messages(
                db_pool, conversation_id, user_context.tenant_id,
                user_context.user_id, query, full_response,
                references, token_usage, settings.LLM_MODEL_CHAT,
                thinking_steps=thinking_steps,
                duration_sec=duration_sec,
                skip_user_message=bool(confirmed_plan)  # plan确认时不存"确认执行计划"
            )

            # ── 步骤9：异步记忆提取 ──
            if memory_service and settings.MEM0_ENABLED:
                asyncio.create_task(
                    extract_long_term_memory(
                        memory_service, user_context.tenant_id,
                        user_context.user_id, query, full_response
                    )
                )

        # ── 步骤8：新会话同步生成标题（plan_pending 也需要生成）──
        if is_new:
            conversation_title = await _generate_and_save_title(
                db_pool, conversation_id, query, chat_llm
            )

        # ── 步骤10：如果检测到Token过期，先发token_expired事件再发done ──
        if token_expired_detected:
            yield {
                "event": "token_expired",
                "data": json.dumps({"message": "认证已过期，请重新登录"}, ensure_ascii=False)
            }

        # ── 步骤11：发射done事件 ──
        done_data = {
            "full_content": full_response,
            "token_usage": token_usage or {
                "input": len(query) // 2,
                "output": len(full_response) // 2
            },
            "conversation_id": conversation_id,
            "message_id": ai_message_id,
            "duration_sec": duration_sec,
            "thinking_steps": thinking_steps,
            "plan_pending": plan_pending
        }
        # Plan pending时：附带plan_steps数据，前端用于展示确认卡片
        if plan_pending and captured_plan_steps:
            done_data["plan_steps"] = captured_plan_steps
        if conversation_title:
            done_data["conversation_title"] = conversation_title
        
        yield {
            "event": "done",
            "data": json.dumps(done_data, ensure_ascii=False)
        }

    except Exception as e:
        logger.error("chat_stream_generator 异常: %s\n%s", e, traceback.format_exc())
        yield {
            "event": "error",
            "data": json.dumps({"message": f"处理异常: {str(e)}"}, ensure_ascii=False)
        }


# ─── 会话管理接口 ──────────────────────────────────────────

conversations_router = APIRouter(prefix="/api/ai/conversations", tags=["AI会话管理"])


@conversations_router.get("")
async def list_conversations(page_num: int = 1, page_size: int = 20, req: Request = None):
    """获取当前用户的会话列表（Redis缓存，2分钟TTL）"""
    pool = req.app.state.db_pool
    user_context = req.state.user_context

    cache_key = f"t{user_context.tenant_id}_u{user_context.user_id}_p{page_num}_s{page_size}"

    async def _fetch():
        offset = (page_num - 1) * page_size
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT id, title, session_type, message_count, total_tokens,
                          last_message_at, is_pinned, created_at, updated_at
                   FROM conversation
                   WHERE tenant_id = $1 AND user_id = $2 AND is_deleted = FALSE
                   ORDER BY is_pinned DESC, last_message_at DESC NULLS LAST
                   LIMIT $3 OFFSET $4""",
                user_context.tenant_id, user_context.user_id, page_size, offset
            )
            total = await conn.fetchval(
                """SELECT COUNT(*) FROM conversation
                   WHERE tenant_id = $1 AND user_id = $2 AND is_deleted = FALSE""",
                user_context.tenant_id, user_context.user_id
            )

        items = [dict(row) for row in rows]
        for item in items:
            for key in ("last_message_at", "created_at", "updated_at"):
                if item.get(key):
                    item[key] = item[key].isoformat()
        return {"total": total, "page_num": page_num, "page_size": page_size, "items": items}

    return await get_or_set(CacheNS.CONV_LIST, cache_key, _fetch, _CONV_LIST_TTL)


@conversations_router.get("/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: int,
    limit: int = 50,
    before_id: int = None,
    req: Request = None
):
    """获取会话历史消息（支持游标分页）

    平台管理员可跨租户查看任意会话消息。
    """
    pool = req.app.state.db_pool
    user_context = req.state.user_context
    admin_mode = is_platform_admin(user_context)

    async with pool.acquire() as conn:
        # 校验会话归属（平台管理员跳过租户校验）
        if admin_mode:
            conv = await conn.fetchrow(
                "SELECT id FROM conversation WHERE id = $1 AND is_deleted = FALSE",
                conversation_id
            )
        else:
            conv = await conn.fetchrow(
                "SELECT id FROM conversation WHERE id = $1 AND user_id = $2 AND tenant_id = $3 AND is_deleted = FALSE",
                conversation_id, user_context.user_id, user_context.tenant_id
            )
        if not conv:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="会话不存在")

        if before_id:
            rows = await conn.fetch(
                """SELECT id, role, content, model_name, tool_calls, tool_call_id,
                          tool_result, token_count, token_usage, file_ids, "references",
                          thinking_steps, duration_sec, is_streaming, created_at
                   FROM conversation_message
                   WHERE conversation_id = $1 AND is_deleted = FALSE AND id < $2
                   ORDER BY created_at DESC
                   LIMIT $3""",
                conversation_id, before_id, limit
            )
        else:
            rows = await conn.fetch(
                """SELECT id, role, content, model_name, tool_calls, tool_call_id,
                          tool_result, token_count, token_usage, file_ids, "references",
                          thinking_steps, duration_sec, is_streaming, created_at
                   FROM conversation_message
                   WHERE conversation_id = $1 AND is_deleted = FALSE
                   ORDER BY created_at DESC
                   LIMIT $2""",
                conversation_id, limit
            )

    items = []
    for row in reversed(rows):
        item = dict(row)
        if item.get("created_at"):
            item["created_at"] = item["created_at"].isoformat()
        # 解析JSON字段：asyncpg默认返回JSON字符串，需手动parse
        for field in ("references", "token_usage", "file_ids", "tool_calls", "thinking_steps"):
            if item.get(field) and isinstance(item[field], str):
                try:
                    item[field] = json.loads(item[field])
                except (json.JSONDecodeError, TypeError):
                    pass
        items.append(item)

    return {"conversation_id": conversation_id, "items": items, "has_more": len(rows) >= limit}


@conversations_router.put("/{conversation_id}")
async def rename_conversation(
    conversation_id: int,
    req: Request = None
):
    """修改会话名称

    平台管理员可跨租户修改任意会话名称。
    """
    from fastapi import HTTPException
    pool = req.app.state.db_pool
    user_context = req.state.user_context
    admin_mode = is_platform_admin(user_context)

    body = await req.json()
    title = (body.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="会话名称不能为空")
    if len(title) > 50:
        title = title[:50]

    async with pool.acquire() as conn:
        # 校验归属（平台管理员跳过租户校验）
        if admin_mode:
            exists = await conn.fetchval(
                "SELECT id FROM conversation WHERE id = $1 AND is_deleted = FALSE",
                conversation_id
            )
        else:
            exists = await conn.fetchval(
                "SELECT id FROM conversation WHERE id = $1 AND user_id = $2 AND tenant_id = $3 AND is_deleted = FALSE",
                conversation_id, user_context.user_id, user_context.tenant_id
            )
        if not exists:
            raise HTTPException(status_code=404, detail="会话不存在")

        await conn.execute(
            "UPDATE conversation SET title = $1, updated_at = NOW() WHERE id = $2",
            title, conversation_id
        )

    await flush_namespace(CacheNS.CONV_LIST)
    return {"id": conversation_id, "title": title}


@conversations_router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    req: Request = None
):
    """软删除会话

    平台管理员可跨租户删除任意会话。
    """
    from fastapi import HTTPException
    pool = req.app.state.db_pool
    user_context = req.state.user_context
    admin_mode = is_platform_admin(user_context)

    async with pool.acquire() as conn:
        # 校验归属（平台管理员跳过租户校验）
        if admin_mode:
            exists = await conn.fetchval(
                "SELECT id FROM conversation WHERE id = $1 AND is_deleted = FALSE",
                conversation_id
            )
        else:
            exists = await conn.fetchval(
                "SELECT id FROM conversation WHERE id = $1 AND user_id = $2 AND tenant_id = $3 AND is_deleted = FALSE",
                conversation_id, user_context.user_id, user_context.tenant_id
            )
        if not exists:
            raise HTTPException(status_code=404, detail="会话不存在")

        await conn.execute(
            "UPDATE conversation SET is_deleted = TRUE, updated_at = NOW() WHERE id = $1",
            conversation_id
        )

    await flush_namespace(CacheNS.CONV_LIST)
    return {"id": conversation_id, "deleted": True}


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

    # 权限守卫：认证用户需要AI对话权限
    require_perm(user_context, AI_PERMS.CHAT_VIEW, "使用AI对话")

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
            file_ids=request.file_ids,
            confirmed_plan=request.confirmed_plan,
            original_query=request.original_query
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
        logger.error("_guest_chat_stream 异常: %s\n%s", e, traceback.format_exc())
        yield {
            "event": "error",
            "data": json.dumps({"message": f"处理异常: {str(e)}"}, ensure_ascii=False)
        }
