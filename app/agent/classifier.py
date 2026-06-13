"""任务复杂度分类器 - 判定任务类型（simple/medium/complex）"""
import json
from langchain_core.messages import SystemMessage, HumanMessage
from app.agent.state import AgentState
from app.config import settings

CLASSIFIER_PROMPT = """你是ERP智能助理的任务分类器。分析用户提问，判定任务复杂度。

分类标准：

【simple - 简单任务】直接调用 ≤1个工具即可完成，无需规划：
- 知识库问答（如"镀镍液pH值范围？"）
- 单表数据查询（如"上月完成了多少订单？"）
- 简单闲聊/功能介绍
- 写作助手类简单请求

【medium - 中等任务】需要调用 2-3个工具，有明确执行步骤：
- 多表数据查询对比（如"对比上月和本月订单完成率"）
- 上传文档分析
- 复杂的写作请求（需要多步生成）

【complex - 复杂任务】需要 4个以上工具或涉及多方协调：
- 生成完整分析报告（需要多表查询+统计分析+图表生成）
- 批量数据处理任务
- 跨模块业务操作

输出JSON格式：
{
    "complexity": "simple|medium|complex",
    "requires_confirmation": true|false,
    "reason": "判定理由"
}
"""


async def classify_task(state: AgentState, llm) -> dict:
    """
    分类器节点：分析用户问题，判定任务复杂度

    Returns:
        更新后的状态字段
    """
    query = state["query"]
    user_context = state.get("user_context")

    # 构建分类请求
    messages = [
        SystemMessage(content=CLASSIFIER_PROMPT),
        HumanMessage(content=f"用户({user_context.auth_mode}模式)提问：{query}")
    ]

    response = await llm.ainvoke(
        messages,
        temperature=settings.CLASSIFIER_TEMPERATURE,
        max_tokens=settings.CLASSIFIER_MAX_TOKENS
    )

    try:
        # 提取JSON
        content = response.content
        result = json.loads(content)

        return {
            "task_complexity": result.get("complexity", "simple"),
            "requires_confirmation": result.get("requires_confirmation", False)
        }
    except (json.JSONDecodeError, AttributeError):
        # 默认判定为简单任务
        return {
            "task_complexity": "simple",
            "requires_confirmation": False
        }
