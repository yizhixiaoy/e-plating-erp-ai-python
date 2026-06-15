"""任务复杂度分类器 - 判定任务类型（simple/medium/complex）"""
import json
import logging
from langchain_core.messages import SystemMessage, HumanMessage
from app.agent.state import AgentState
from app.agent.nodes import _get_llm_content, _extract_json
from app.config import settings

logger = logging.getLogger(__name__)

CLASSIFIER_PROMPT = """你是ERP智能助理的任务分类器。分析用户提问，判定任务复杂度。

分类标准：

【simple - 简单任务】无需调用工具或只需1个工具即可完成：
- 知识库问答（如"镀镍液pH值范围？"、"电镀工艺标准是什么？"）
- 简单闲聊/功能介绍（如"你好"、"系统有什么功能？"）
- 写作助手类简单请求

【medium - 中等任务】需要调用 1-2个工具，或涉及数据库查询：
- 业务数据统计查询（如"公司有多少员工？"、"上月完成了多少订单？"）
- 业务数据明细查询（如"员工名单都有谁？"、"库存中镀镍液有多少？"）
- 多表数据查询对比（如"对比上月和本月订单完成率"）
- 上传文档分析

【complex - 复杂任务】需要 3个以上工具或多方协调：
- 生成完整分析报告（需要多表查询+统计分析）
- 批量数据处理任务
- 跨模块业务操作

关键判断规则：
- 只要涉及"员工/客户/订单/产品/库存/质检"等业务数据查询 → 至少为 medium
- 只要需要调用 erp_query_tool → 至少为 medium
- 纯粹的知识库问答（不涉及具体业务数据） → simple

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
        # 防御性提取内容（兼容思考模式content为空）
        content = _get_llm_content(response)
        if not content.strip():
            logger.warning("[classifier] LLM返回空内容，默认simple")
            return {"task_complexity": "simple", "requires_confirmation": False}

        # 健壮JSON提取（兼容markdown代码块包裹/截断修复）
        result = _extract_json(content)
        if result is None:
            # _extract_json失败，尝试直接json.loads（兼容旧格式）
            result = json.loads(content)

        complexity = result.get("complexity", "simple")
        reason = result.get("reason", "")
        logger.info("[classifier] query=%r → complexity=%s, reason=%s", query[:50], complexity, reason)

        return {
            "task_complexity": complexity,
            "requires_confirmation": result.get("requires_confirmation", False)
        }
    except (json.JSONDecodeError, AttributeError) as e:
        # 默认判定为简单任务
        logger.warning("[classifier] JSON解析失败，默认simple: %s, raw=%r", e, str(response.content)[:100] if response.content else "")
        return {
            "task_complexity": "simple",
            "requires_confirmation": False
        }
