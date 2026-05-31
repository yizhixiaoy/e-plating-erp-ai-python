"""写作助手接口 - SSE流式输出"""
import json
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from app.models.schemas import WriterRequest
from app.services.llm_factory import create_llm
from app.services.writer import WriterService

router = APIRouter(prefix="/api/ai/write", tags=["AI写作"])


async def writer_stream_generator(prompt_data: dict):
    """写作助手SSE流式生成器"""
    from langchain_core.messages import SystemMessage, HumanMessage

    messages = [
        SystemMessage(content=prompt_data["system_prompt"]),
        HumanMessage(content=prompt_data["user_prompt"])
    ]

    llm = create_llm(streaming=True, temperature=0.7)

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
    prompt_data = WriterService.build_prompt(request)

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
