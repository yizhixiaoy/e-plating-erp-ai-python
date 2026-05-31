"""对话接口 - SSE流式输出"""
import json
import asyncio
import time
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from app.models.schemas import ChatRequest
from app.services.llm_factory import create_llm
from app.config import settings

router = APIRouter(prefix="/api/ai/chat", tags=["AI对话"])


async def chat_stream_generator(
    query: str,
    user_context,
    conversation_id: int | None,
    agent_graph,
    db_pool
):
    """SSE流式生成器"""
    start_time = time.time()

    # 构建Agent输入状态
    from app.agent.state import AgentState
    from langchain_core.messages import HumanMessage

    initial_state: AgentState = {
        "messages": [HumanMessage(content=query)],
        "query": query,
        "user_context": user_context,
        "conversation_id": conversation_id,
        "task_complexity": "simple",
        "requires_confirmation": False,
        "plan_steps": [],
        "tool_calls_pending": [],
        "tool_results": [],
        "knowledge_context": None,
        "references": [],
        "final_response": None,
        "token_usage": {},
        "error": None
    }

    try:
        # 1. 发射thinking事件 - 开始分析
        yield {
            "event": "thinking",
            "data": json.dumps({"content": "收到您的问题，正在分析..."}, ensure_ascii=False)
        }

        # 2. 运行Agent图
        config = {"configurable": {"thread_id": str(conversation_id) if conversation_id else "new"}}

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
                # LLM流式输出 - 最终回答
                chunk = event["data"].get("chunk", {})
                if hasattr(chunk, "content") and chunk.content:
                    content = chunk.content
                    if event_name == "aggregator" or event_name == "LangGraph":
                        full_response += content
                        yield {
                            "event": "chunk",
                            "data": json.dumps({"content": content}, ensure_ascii=False)
                        }

            elif event_type == "on_chain_end" and event_name == "aggregator":
                # Aggregator节点完成
                output = event["data"].get("output", {})
                if isinstance(output, dict):
                    if "references" in output and output["references"]:
                        refs = output["references"]
                        references.extend(refs)
                        yield {
                            "event": "reference",
                            "data": json.dumps(refs, ensure_ascii=False)
                        }

        # 3. 发射done事件
        duration_sec = round(time.time() - start_time, 2)
        yield {
            "event": "done",
            "data": json.dumps({
                "full_content": full_response,
                "token_usage": token_usage or {"input": len(query) // 2, "output": len(full_response) // 2},
                "conversation_id": conversation_id or 0,
                "duration_sec": duration_sec
            }, ensure_ascii=False)
        }

    except Exception as e:
        yield {
            "event": "error",
            "data": json.dumps({"message": f"处理异常: {str(e)}"}, ensure_ascii=False)
        }


@router.post("")
async def chat(request: ChatRequest, req: Request):
    """
    AI对话接口 - SSE流式输出

    接收用户问题，通过LangGraph Agent处理后流式返回结果。
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

    # 注入当前请求的认证头到ErpQueryTool
    if "erp_query_tool" in tools:
        tools["erp_query_tool"].set_auth_headers(auth_headers)

    return EventSourceResponse(
        chat_stream_generator(
            query=request.query,
            user_context=user_context,
            conversation_id=request.conversation_id,
            agent_graph=agent_graph,
            db_pool=db_pool
        ),
        media_type="text/event-stream"
    )


async def _guest_chat_stream(query: str):
    """访客模式聊天（仅基础问答，无工具调用）"""
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
