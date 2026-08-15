"""写作助手接口 - SSE流式输出"""
import json
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from app.models.schemas import WriterRequest
from app.services.llm_factory import create_llm
from app.services.writer import WriterService
from app.services.permissions import require_perm, AI_PERMS, is_platform_admin
from app.config import settings

router = APIRouter(prefix="/api/ai/write", tags=["AI写作"])


async def writer_stream_generator(prompt_data: dict):
    """写作助手SSE流式生成器"""
    from langchain_core.messages import SystemMessage, HumanMessage

    messages = [
        SystemMessage(content=prompt_data["system_prompt"]),
        HumanMessage(content=prompt_data["user_prompt"])
    ]

    llm = create_llm(streaming=True, temperature=settings.LLM_WRITER_TEMPERATURE)

    yield {
        "event": "thinking",
        "data": json.dumps({
            "content": f"正在生成{prompt_data['template_name']}..."
        }, ensure_ascii=False)
    }

    full_response = ""
    try:
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
                "token_usage": {"input": len(prompt_data["user_prompt"]) // 2, "output": len(full_response) // 2}
            }, ensure_ascii=False)
        }
    except Exception as e:
        yield {
            "event": "error",
            "data": json.dumps({"message": f"生成异常: {str(e)}"}, ensure_ascii=False)
        }


@router.post("")
async def write(request: WriterRequest, req: Request):
    """AI写作接口"""
    user_context = req.state.user_context

    # 权限守卫
    require_perm(user_context, AI_PERMS.WRITER_VIEW, "使用AI写作")

    pool = req.app.state.db_pool
    oss_service = getattr(req.app.state, "oss_service", None)

    # 如果指定了参考文档ID，从知识库检索相关内容作为写作素材
    knowledge_context = ""
    if request.ref_doc_ids:
        from app.tools.knowledge import KnowledgeTool
        tool = KnowledgeTool(db_pool=pool, oss_service=oss_service)
        # 使用写作主题作为检索query，从指定文档所在知识库检索
        result = await tool.execute(
            query=request.topic,
            kb_ids=None,  # 从所有可见库检索
            top_k=settings.RAG_TOP_K,
            tenant_id=user_context.tenant_id,
            is_platform_admin=is_platform_admin(user_context)
        )
        if result.get("content") and result["content"] != "未找到相关知识。":
            knowledge_context = result["content"]

    prompt_data = WriterService.build_prompt(request, knowledge_context=knowledge_context)

    return EventSourceResponse(
        writer_stream_generator(prompt_data),
        media_type="text/event-stream"
    )


@router.get("/templates")
async def get_templates():
    """获取可用的写作模板列表"""
    return [
        {"type": "report", "name": "工作报告", "icon": "📊", "description": "周报/月报/项目报告", "example": ""},
        {"type": "notice", "name": "通知公告", "icon": "📢", "description": "内部通知/行政公告", "example": ""},
        {"type": "summary", "name": "工作总结", "icon": "📝", "description": "个人/部门工作总结", "example": ""},
        {"type": "contract", "name": "合同草稿", "icon": "📋", "description": "标准合同文本", "example": ""},
        {"type": "custom", "name": "自定义", "icon": "✏️", "description": "自由输入写作主题", "example": ""},
    ]
