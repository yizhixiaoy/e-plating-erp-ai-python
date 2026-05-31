"""LangGraph节点实现：Planner / Executor / Aggregator"""
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from app.agent.state import AgentState

SYSTEM_PROMPT = """你是电镀行业SaaS ERP系统的智能助理"智镀云AI"，服务于电镀企业的管理人员和操作人员。

你的职责：
1. 回答电镀工艺相关的技术问题（基于知识库）
2. 查询和分析ERP业务数据（订单、库存、质量、生产等）
3. 协助生成工作报告和业务文档
4. 引导用户使用系统功能

你的行为准则：
- 回答基于检索到的知识和查询到的数据，不编造信息
- 如果数据不足或无法确定，诚实告知用户
- 涉及敏感业务数据时，仅返回用户权限范围内的信息
- 使用中文回复，表达专业且友好
- 在回答中标注引用来源

用户身份信息：
- 租户ID: {tenant_id}
- 用户ID: {user_id}
- 权限范围: {data_scope}
"""


async def planner_node(state: AgentState, llm) -> dict:
    """
    规划节点：为复杂任务制定执行计划

    仅 medium/complex 任务走此节点
    """
    complexity = state["task_complexity"]
    query = state["query"]

    if complexity == "simple":
        return {}

    planning_prompt = f"""你需要为用户问题制定执行计划。

用户问题：{query}
任务复杂度：{complexity}

可用的工具：
1. erp_query_tool - 业务数据查询（表名、聚合、筛选条件）
2. stats_tool - 统计数据分析
3. knowledge_tool - 知识库检索
4. doc_process_tool - 文档处理

请制定分步执行计划，输出JSON格式：
{{
    "steps": [
        {{"step": 1, "action": "描述", "tool": "工具名", "params": {{...}}}}
    ]
}}
"""
    messages = [
        SystemMessage(content="你是任务规划助手，为ERP数据分析任务制定执行计划。"),
        HumanMessage(content=planning_prompt)
    ]

    response = await llm.ainvoke(messages, temperature=0.2, max_tokens=1000)

    try:
        import json
        content = response.content
        result = json.loads(content)
        return {"plan_steps": result.get("steps", [])}
    except (json.JSONDecodeError, AttributeError):
        return {"plan_steps": []}


async def executor_node(state: AgentState, llm, tools: dict) -> dict:
    """
    执行节点：按计划或直接调用工具

    - simple任务：直接根据用户意图调用对应工具
    - medium/complex任务：按计划逐步执行
    """
    query = state["query"]
    tool_calls_pending = state.get("tool_calls_pending", [])
    tool_results = state.get("tool_results", [])
    knowledge_context = state.get("knowledge_context")
    references = state.get("references", [])

    # 构建带工具描述的请求，让LLM决定调用哪个工具
    tool_descriptions = "\n".join([
        f"- {name}: {tool.description}" for name, tool in tools.items()
    ])

    executor_prompt = f"""根据用户问题，判断需要调用哪些工具。

用户问题：{query}

可用工具：
{tool_descriptions}

请决定：
1. 如果问题涉及知识库查询，调用 knowledge_tool
2. 如果问题涉及业务数据查询，调用 erp_query_tool
3. 如果问题涉及统计分析，调用 stats_tool
4. 如果不需调用任何工具（闲聊、功能咨询），返回空

输出JSON：
{{
    "tool_name": "knowledge_tool",
    "tool_params": {{"query": "改写后的检索查询", "kb_ids": null, "top_k": 5}}
}}

或

{{
    "tool_name": null,
    "reason": "不需要调用工具"
}}
"""
    messages = [
        SystemMessage(content="你是工具选择助手，决定调用哪个工具。"),
        HumanMessage(content=executor_prompt)
    ]

    response = await llm.ainvoke(messages, temperature=0.0, max_tokens=500)

    try:
        import json
        content = response.content
        # 提取JSON
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            result = json.loads(content[start:end])
        else:
            return {"tool_calls_pending": [], "tool_results": [], "knowledge_context": None, "references": []}

        tool_name = result.get("tool_name")
        if not tool_name:
            return {}

        tool_params = result.get("tool_params", {})
        tool = tools.get(tool_name)

        if not tool:
            return {}

        # 执行工具
        tool_result = await tool.execute(**tool_params)

        new_result = {
            "tool_name": tool_name,
            "params": tool_params,
            "result": tool_result
        }
        tool_results.append(new_result)

        # 提取引用来源和知识上下文
        if isinstance(tool_result, dict):
            if "references" in tool_result:
                references.extend(tool_result["references"])
            if "content" in tool_result:
                knowledge_context = tool_result["content"]

        return {
            "tool_results": tool_results,
            "knowledge_context": knowledge_context,
            "references": references
        }

    except (json.JSONDecodeError, AttributeError) as e:
        return {
            "tool_results": [{"error": str(e)}],
            "knowledge_context": None,
            "references": []
        }


async def aggregator_node(state: AgentState, llm) -> dict:
    """
    聚合节点：使用检索上下文和工具结果生成最终回答

    这是生成最终回答并发射 reference 事件的地方
    """
    query = state["query"]
    user_context = state["user_context"]
    knowledge_context = state.get("knowledge_context", "")
    tool_results = state.get("tool_results", [])
    references = state.get("references", [])

    # 构建完整上下文
    context_parts = []

    if knowledge_context:
        context_parts.append(f"【知识库检索结果】\n{knowledge_context}")

    if tool_results:
        for tr in tool_results:
            if "result" in tr and "error" not in tr:
                result_content = tr["result"]
                if isinstance(result_content, dict):
                    result_content = result_content.get("content", str(result_content))
                context_parts.append(f"【{tr.get('tool_name', '工具')}结果】\n{result_content}")

    full_context = "\n\n".join(context_parts) if context_parts else "无额外上下文"

    # 构建System Prompt
    system_prompt = SYSTEM_PROMPT.format(
        tenant_id=user_context.tenant_id,
        user_id=user_context.user_id,
        data_scope=user_context.data_scope or "NONE"
    )

    if full_context != "无额外上下文":
        system_prompt += f"\n\n请基于以下检索/查询结果回答用户问题，并标注引用来源：\n{full_context}"

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=query)
    ]

    response = await llm.ainvoke(messages, temperature=settings.LLM_TEMPERATURE, max_tokens=settings.LLM_MAX_TOKENS)

    final_response = response.content

    # 估算Token用量
    token_usage = {
        "input": len(system_prompt) // 2,
        "output": len(final_response) // 2
    }

    return {
        "final_response": final_response,
        "token_usage": token_usage,
        "references": references
    }


from app.config import settings
