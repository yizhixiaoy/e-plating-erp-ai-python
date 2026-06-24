"""LangGraph节点实现：Planner / Executor / Aggregator"""
import inspect
import json
import logging
import re
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from app.agent.state import AgentState
from app.config import settings
from app.services.context_manager import ContextManager
from app.services.permissions import describe_permissions, is_platform_admin

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> dict | None:
    """从LLM返回文本中提取JSON对象，兼容markdown代码块包裹"""
    # 优先匹配 ```json ... ``` 或 ``` ... ``` 代码块
    m = re.search(r'```(?:json)?\s*\n?(.*?)```', text, re.DOTALL)
    if m:
        text = m.group(1).strip()
    # 提取最外层 {...}
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(text[start:end])
    return None


def _get_llm_content(response) -> str:
    """从LLM响应中提取实际内容，兼容思考模式导致content为空的情况

    Qwen3思考模式下：content为空，实际回答在additional_kwargs.reasoning_content中
    """
    content = response.content or ""
    if content.strip():
        return content
    # 兜底：检查additional_kwargs中的reasoning_content
    if hasattr(response, "additional_kwargs"):
        reasoning = response.additional_kwargs.get("reasoning_content", "")
        if reasoning:
            logger.warning("[llm] content为空，从reasoning_content兜底提取 (前100字): %r", reasoning[:100])
            return reasoning
    logger.warning("[llm] content和reasoning_content均为空，response type=%s, additional_kwargs=%s",
                   type(response).__name__,
                   getattr(response, "additional_kwargs", "N/A"))
    return ""


def _infer_tool_from_text(text: str, tools: dict, query: str) -> dict | None:
    """当LLM未返回有效JSON时，从原始文本中智能推断应调用的工具

    根据关键词匹配选择工具：
    - 涉及数据库表名/SQL → erp_query_tool
    - 涉及电镀工艺/知识 → knowledge_tool
    - 涉及统计/分析/图表 → stats_tool
    - 涉及文档处理 → doc_process_tool
    """
    text_lower = text.lower()
    # 优先匹配工具名的精确提及
    for tool_name in tools:
        if tool_name in text_lower:
            return {"tool_name": tool_name, "tool_params": _default_params(tool_name, query)}
    # 关键词推断
    erp_keywords = ["sys_", "tenant", "user", "order", "product", "sql", "table",
                    "员工", "订单", "客户", "产品", "库存", "质检", "公司", "数据库"]
    knowledge_keywords = ["知识库", "电镀", "工艺", "标准", "文档", "技术"]
    stats_keywords = ["统计", "图表", "分析", "报表", "趋势"]

    if any(kw in text_lower for kw in erp_keywords):
        return {"tool_name": "erp_query_tool", "tool_params": {"query": query}}
    if any(kw in text for kw in knowledge_keywords):
        return {"tool_name": "knowledge_tool", "tool_params": {"query": query, "kb_ids": None, "top_k": 5}}
    if any(kw in text for kw in stats_keywords):
        return {"tool_name": "stats_tool", "tool_params": {"data": ""}}
    return None


def _default_params(tool_name: str, query: str) -> dict:
    """返回工具的默认参数"""
    defaults = {
        "erp_query_tool": {"query": query},
        "knowledge_tool": {"query": query, "kb_ids": None, "top_k": 5},
        "stats_tool": {"data": ""},
        "doc_process_tool": {"file_ids": [], "operation": "analyze", "instruction": query},
    }
    return defaults.get(tool_name, {})


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
- 姓名: {nickname}
- 用户名: {username}
- 租户ID: {tenant_id}
- 用户ID: {user_id}
- 数据权限: {data_scope}
- 权限摘要: {permissions_summary}

重要安全规则：
- {tenant_rule}
- 用户的数据权限级别为 {data_scope}，不得越权
- {permissions_summary}，超出能力范围的操作应明确拒绝
"""

# 会话自动标题生成提示词
TITLE_GENERATION_PROMPT = """根据以下用户的第一条消息，生成一个简短的会话标题（不超过15个字）。
只输出标题本身，不要加引号或其他修饰。

用户消息：{first_message}
"""


async def planner_node(state: AgentState, llm, tools: dict = None) -> dict:
    """
    规划节点：为复杂任务制定执行计划

    仅 medium/complex 任务走此节点
    """
    complexity = state["task_complexity"]
    query = state["query"]
    conversation_history = state.get("conversation_history", [])
    memory_summary = state.get("memory_summary", "")

    if complexity == "simple":
        return {}

    # 构建对话历史摘要（让planner了解上下文）
    history_text = ""
    if conversation_history:
        recent = conversation_history[-settings.AGENT_PLANNER_RECENT_HISTORY:]
        history_text = "\n".join([
            f"[{m['role']}] {m['content'][:settings.AGENT_PLANNER_HISTORY_TRUNC]}" for m in recent
        ])

    # ── 获取动态数据库Schema ──
    schema_text = ""
    if tools and "erp_query_tool" in tools:
        try:
            schema_text = await tools["erp_query_tool"].get_schema_description()
        except Exception:
            pass

    planning_prompt = f"""你需要为用户问题制定执行计划。

用户问题：{query}
任务复杂度：{complexity}
"""
    if schema_text:
        planning_prompt += f"\n数据库Schema：\n{schema_text}\n"
    if history_text:
        planning_prompt += f"\n最近对话历史：\n{history_text}\n"
    if memory_summary:
        planning_prompt += f"\n用户信息：{memory_summary}\n"

    planning_prompt += """
可用的工具（严格遵守参数名，不要编造额外参数）：

1. erp_query_tool - 业务数据查询
   参数（仅限以下3个）：
   - table: string（必填，表名，从数据库Schema中选取）
   - aggregate: object（可选，{{"func": "count|sum|avg|max|min", "field": "字段名"}}）
   - filters: object（可选，{{"date_range": ["开始日期","结束日期"], "status": "...", ...}}）

2. knowledge_tool - 知识库检索
   参数（仅限以下2个）：
   - query: string（必填，改写后的检索查询）
   - top_k: int（可选，默认5，返回条数）

3. stats_tool - 统计分析（必须先有数据，不能直接查表）
   参数（仅限以下3个）：
   - operation: string（必填，trend|compare|ratio|summary）
   - data: string（必填，写空字符串""即可，系统会自动注入前序工具的结果）
   - params: object（可选，{{"group_by": "字段", "sort": "asc|desc", "top_n": 5}}）

4. doc_process_tool - 文档处理（仅当用户上传了文件时使用）
   参数（仅限以下3个）：
   - file_ids: list[string]（必填，文件ID列表，系统会自动注入）
   - operation: string（必填，summarize|compare|extract|translate|analyze）
   - instruction: string（必填，用户的详细指令）

重要规则：
- 每个step的params只能包含对应工具声明的参数，禁止添加额外字段
- stats_tool的data参数必须写空字符串""，系统会自动注入前序工具的结果，禁止写"step1_result"等占位符
- stats_tool不能直接查询数据库，它的data参数来自前序工具的结果
- 如果只需要查询数据，不需要加stats_tool步骤
- 每个工具最多调用一次，不要重复调用同一工具

请制定分步执行计划，输出JSON格式：
{{
    "steps": [
        {{"step": 1, "action": "描述", "tool": "工具名", "params": {{...仅限工具声明的参数...}}}}
    ]
}}
"""
    messages = [
        SystemMessage(content="你是任务规划助手，为ERP数据分析任务制定执行计划。"),
        HumanMessage(content=planning_prompt)
    ]

    response = await llm.ainvoke(
        messages,
        temperature=settings.PLANNER_TEMPERATURE,
        max_tokens=settings.PLANNER_MAX_TOKENS
    )

    try:
        content = _get_llm_content(response)
        result = _extract_json(content)
        if result is None:
            logger.warning("[planner] 无有效JSON: %r", content[:100] if content else "")
            return {"plan_steps": [], "plan_confirmed": False}
        steps = result.get("steps", [])
        logger.info("[planner] query=%r → %d个步骤: %s", query[:50], len(steps),
                     [s.get("tool", "?") for s in steps])
        return {"plan_steps": steps, "plan_confirmed": True}
    except (json.JSONDecodeError, AttributeError) as e:
        raw_content = _get_llm_content(response)
        logger.warning("[planner] JSON解析失败: %s, raw=%r", e, raw_content[:100] if raw_content else "")
        return {"plan_steps": [], "plan_confirmed": True}


async def _execute_single_tool(
    tool_name: str, tool_params: dict, tools: dict,
    user_context, tool_results: list, knowledge_context, references: list,
    kb_ids=None, file_ids=None, conversation_id=None,
    _inject_fn=None, _sanitize_fn=None, _merge_fn=None
) -> dict:
    """执行单个工具调用并返回结果（提取自 executor_node 的单工具分支）"""
    import inspect, re as _re

    tool = tools.get(tool_name)
    if not tool:
        return {"tool_calls_pending": [], "tool_results": [], "knowledge_context": None, "references": []}

    pending_calls = [{"tool_name": tool_name, "tool_args": tool_params}]

    # 权限检查
    if hasattr(tool, 'check_permission') and not tool.check_permission(user_context):
        return {
            "tool_calls_pending": pending_calls,
            "tool_results": [{"tool_name": tool_name, "error": "权限不足：您没有使用该工具的权限"}],
            "knowledge_context": knowledge_context,
            "references": references
        }

    # 注入上下文参数
    if _inject_fn:
        tool_params = _inject_fn(tool_name, tool_params)
    # 过滤非法参数
    if _sanitize_fn:
        tool_params = _sanitize_fn(tool, tool_params)

    # 执行工具
    try:
        tool_result = await tool.execute(**tool_params)
    except Exception as ex:
        tool_results.append({"tool_name": tool_name, "error": str(ex)})
        return {
            "tool_calls_pending": pending_calls,
            "tool_results": tool_results,
            "knowledge_context": knowledge_context,
            "references": references
        }

    new_result = {"tool_name": tool_name, "params": tool_params, "result": tool_result}
    tool_results.append(new_result)

    # Token过期检测
    if isinstance(tool_result, dict) and tool_result.get("error_code") == 401:
        return {
            "tool_calls_pending": pending_calls,
            "tool_results": tool_results,
            "knowledge_context": knowledge_context,
            "references": references,
            "token_expired": True
        }

    # 合并工具结果到知识上下文
    if _merge_fn:
        _merge_fn(tool_result)

    return {
        "tool_calls_pending": pending_calls,
        "tool_results": tool_results,
        "knowledge_context": knowledge_context,
        "references": references
    }


async def executor_node(state: AgentState, llm, tools: dict) -> dict:
    """
    执行节点：按计划或直接调用工具

    - simple任务：使用LLM判断调用哪个工具（单次调用）
    - medium/complex任务：按planner生成的plan_steps逐步执行多工具
    """
    query = state["query"]
    plan_steps = state.get("plan_steps", [])
    tool_results = state.get("tool_results", [])
    knowledge_context = state.get("knowledge_context")
    references = state.get("references", [])
    user_context = state.get("user_context")

    logger.info("[executor] query=%r, plan_steps=%d, available_tools=%s",
                query[:50], len(plan_steps), list(tools.keys()))
    kb_ids = state.get("kb_ids")
    file_ids = state.get("file_ids")
    conversation_id = state.get("conversation_id")

    def _inject_context_params(tool_name: str, tool_params: dict) -> dict:
        """注入租户隔离和请求上下文参数"""
        params = dict(tool_params)
        # knowledge_tool：注入tenant_id + kb_ids + is_platform_admin
        if tool_name == "knowledge_tool":
            if user_context:
                params.setdefault("tenant_id", user_context.tenant_id)
                params.setdefault("is_platform_admin", is_platform_admin(user_context))
            if kb_ids and not params.get("kb_ids"):
                params["kb_ids"] = kb_ids
        # doc_process_tool：注入file_ids + conversation_id
        if tool_name == "doc_process_tool":
            if file_ids and not params.get("file_ids"):
                params["file_ids"] = file_ids
            if conversation_id and not params.get("conversation_id"):
                params["conversation_id"] = conversation_id
        # erp_query_tool：注入auth_headers
        if tool_name == "erp_query_tool" and user_context:
            pass  # auth_headers已在chat.py中通过set_auth_headers注入
        return params

    def _sanitize_tool_params(tool, params: dict) -> dict:
        """过滤工具参数：只保留execute()方法声明的参数，丢弃LLM编造的未知参数"""
        sig = inspect.signature(tool.execute)
        valid_params = set(sig.parameters.keys()) - {"self"}
        sanitized = {k: v for k, v in params.items() if k in valid_params}
        dropped = set(params.keys()) - valid_params
        if dropped:
            logger.warning("[executor] 丢弃工具 %s 的非法参数: %s", tool.name, dropped)
        return sanitized

    def _merge_tool_result(tool_result: dict):
        """合并工具返回的引用和知识上下文"""
        nonlocal knowledge_context, references
        if isinstance(tool_result, dict):
            if "references" in tool_result:
                references.extend(tool_result["references"])
            if "content" in tool_result:
                if knowledge_context:
                    knowledge_context += "\n\n" + tool_result["content"]
                else:
                    knowledge_context = tool_result["content"]

    # ── 分支1：有执行计划时，按计划逐步执行多个工具 ──
    if plan_steps:
        token_expired = False
        # 收集即将调用的工具信息（供SSE stream发射tool_start事件）
        pending_calls = []
        for step in plan_steps:
            tool_name = step.get("tool")
            if tool_name and tools.get(tool_name):
                pending_calls.append({
                    "tool_name": tool_name,
                    "tool_args": step.get("params", {})
                })
        # 提前写入state，让chat_stream_generator能检测到并发射tool_start事件
        # （LangGraph updates模式在节点完成后才捕获，但总比不发射好）

        for step in plan_steps:
            tool_name = step.get("tool")
            if not tool_name:
                continue

            tool = tools.get(tool_name)
            if not tool:
                continue

            # 权限检查：工具级别守卫
            if hasattr(tool, 'check_permission') and not tool.check_permission(user_context):
                tool_results.append({
                    "tool_name": tool_name,
                    "error": "权限不足：您没有使用该工具的权限"
                })
                continue

            tool_params = _inject_context_params(tool_name, step.get("params", {}))

            # stats_tool：自动注入前序工具结果作为data参数
            # 触发条件：data为空 OR data是step引用占位符（如 "step1_result"、"step_1"）
            _data_val = tool_params.get("data", "")
            _is_placeholder = (
                not _data_val
                or _data_val == ""
                or re.match(r'^step[_\d]*[_]?result$', str(_data_val), re.IGNORECASE) is not None
            )
            if tool_name == "stats_tool" and _is_placeholder:
                logger.info("[executor] stats_tool data=%r 识别为占位符，注入前序工具结果", _data_val)
                # 从已完成的工具结果中提取最后一个成功的content作为data
                injected = False
                for prev in reversed(tool_results):
                    if "result" in prev and "error" not in prev:
                        prev_result = prev["result"]
                        if isinstance(prev_result, dict):
                            tool_params["data"] = prev_result.get("content", str(prev_result))
                        else:
                            tool_params["data"] = str(prev_result)
                        injected = True
                        break
                if not injected:
                    logger.warning("[executor] stats_tool 无前序工具结果可注入")

            tool_params = _sanitize_tool_params(tool, tool_params)

            try:
                tool_result = await tool.execute(**tool_params)
            except Exception as e:
                tool_results.append({"tool_name": tool_name, "error": str(e)})
                continue

            # 检测Token过期（Python→Java返回401）
            if isinstance(tool_result, dict) and tool_result.get("error_code") == 401:
                token_expired = True
                tool_results.append({"tool_name": tool_name, "params": tool_params, "result": tool_result})
                break

            new_result = {"tool_name": tool_name, "params": tool_params, "result": tool_result}
            tool_results.append(new_result)
            _merge_tool_result(tool_result)

        return {
            "tool_calls_pending": pending_calls,
            "tool_results": tool_results,
            "knowledge_context": knowledge_context,
            "references": references,
            "token_expired": token_expired or None
        }

    # ── 分支2：无计划时，使用LLM判断调用哪个工具（单次） ──
    tool_descriptions = "\n".join([
        f"- {name}: {tool.description}" for name, tool in tools.items()
    ])

    # ── 获取动态数据库Schema ──
    schema_text = ""
    if "erp_query_tool" in tools:
        try:
            schema_text = await tools["erp_query_tool"].get_schema_description()
        except Exception:
            pass

    schema_block = ""
    if schema_text:
        schema_block = f"\n数据库Schema：\n{schema_text}\n"

    executor_prompt = f"""根据用户问题，判断需要调用哪些工具。

用户问题：{query}

可用工具：
{tool_descriptions}
{schema_block}请决定：
1. 如果问题涉及业务数据查询（员工、订单、客户、产品、库存等），调用 erp_query_tool
2. 如果问题涉及电镀工艺、标准等知识类内容，调用 knowledge_tool
3. 如果问题涉及统计分析，调用 stats_tool
4. 如果涉及文档处理，调用 doc_process_tool
5. 如果不需调用任何工具（闲聊、系统功能介绍等），返回空

重要提示：
- 只要涉及任何业务实体（员工/用户/订单/客户/产品/物料/库存/质检），优先使用 erp_query_tool
- 表名必须从上方的"数据库Schema"中选取，不要编造表名
- 查询"有多少个XX"使用 aggregate: {{"func": "count", "field": "*"}}
- 查询"XX是谁/有哪些"直接查询明细（不设aggregate）

输出JSON：
{{
    "tool_name": "erp_query_tool",
    "tool_params": {{"table": "sys_user", "aggregate": {{"func": "count", "field": "*"}}}}
}}

或

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

    response = await llm.ainvoke(
        messages,
        temperature=settings.EXECUTOR_TOOL_SELECT_TEMP,
        max_tokens=settings.EXECUTOR_MAX_TOKENS
    )

    try:
        content = _get_llm_content(response)
        result = _extract_json(content)
        if result is None:
            # ── JSON提取失败，尝试从原始文本中智能推断工具名 ──
            logger.warning("[executor] LLM返回无有效JSON: %r", content[:200])
            inferred = _infer_tool_from_text(content, tools, query)
            if inferred:
                logger.info("[executor] 从文本推断工具: %s", inferred["tool_name"])
                result = inferred
            else:
                return {"tool_calls_pending": [], "tool_results": [], "knowledge_context": None, "references": []}

        tool_name = result.get("tool_name")
        if not tool_name:
            reason = result.get("reason", "")
            logger.info("[executor] 无需调用工具: reason=%s", reason)
            return {"tool_calls_pending": [], "tool_results": [], "knowledge_context": None, "references": []}

        tool_params = result.get("tool_params", {})
        tool = tools.get(tool_name)
        logger.info("[executor] 选择工具: %s, params=%s", tool_name, list(tool_params.keys()))

        if not tool:
            return {"tool_calls_pending": [], "tool_results": [], "knowledge_context": None, "references": []}

        # 收集即将调用的工具信息（供SSE stream发射tool_start事件）
        pending_calls = [{"tool_name": tool_name, "tool_args": tool_params}]

        # 权限检查：工具级别守卫
        if hasattr(tool, 'check_permission') and not tool.check_permission(user_context):
            return {
                "tool_calls_pending": pending_calls,
                "tool_results": [{
                    "tool_name": tool_name,
                    "error": "权限不足：您没有使用该工具的权限"
                }],
                "knowledge_context": knowledge_context,
                "references": references
            }

        # 注入上下文参数（租户隔离、kb_ids、file_ids）
        tool_params = _inject_context_params(tool_name, tool_params)
        tool_params = _sanitize_tool_params(tool, tool_params)

        # 执行工具
        tool_result = await tool.execute(**tool_params)

        new_result = {
            "tool_name": tool_name,
            "params": tool_params,
            "result": tool_result
        }
        tool_results.append(new_result)

        # 检测Token过期（Python→Java返回401）→ 不合并结果，直接通知前端
        if isinstance(tool_result, dict) and tool_result.get("error_code") == 401:
            return {
                "tool_calls_pending": pending_calls,
                "tool_results": tool_results,
                "knowledge_context": knowledge_context,
                "references": references,
                "token_expired": True
            }

        _merge_tool_result(tool_result)

        return {
            "tool_calls_pending": pending_calls,
            "tool_results": tool_results,
            "knowledge_context": knowledge_context,
            "references": references
        }

    except (json.JSONDecodeError, AttributeError) as e:
        raw_content = _get_llm_content(response)
        logger.warning("[executor] JSON解析失败: %s, raw=%r", e, raw_content[:200] if raw_content else "")
        # ── 尝试从原始文本智能推断工具名并执行 ──
        inferred = _infer_tool_from_text(raw_content, tools, query) if raw_content else None
        if inferred:
            logger.info("[executor] JSON异常后从文本推断工具: %s", inferred["tool_name"])
            return await _execute_single_tool(
                inferred["tool_name"], inferred.get("tool_params", {}),
                tools, user_context, tool_results, knowledge_context, references,
                kb_ids, file_ids, conversation_id,
                _inject_fn=_inject_context_params,
                _sanitize_fn=_sanitize_tool_params,
                _merge_fn=_merge_tool_result
            )
        return {
            "tool_calls_pending": [],
            "tool_results": [{"tool_name": "tool_selector", "error": f"工具选择JSON解析失败: {e}"}],
            "knowledge_context": None,
            "references": []
        }


async def aggregator_node(state: AgentState, llm) -> dict:
    """
    聚合节点：使用历史上下文、长期记忆、检索结果和工具结果生成最终回答

    增强功能：
    - 通过 ContextManager 管理上下文窗口，智能截断历史消息
    - 注入长期记忆摘要到 System Prompt
    - 合并知识库上下文和工具调用结果
    """
    # Token过期短路：不调用LLM，直接返回标记让前端全局处理
    if state.get("token_expired"):
        return {
            "final_response": "认证已过期，请重新登录",
            "token_usage": {"input": 0, "output": 0},
            "token_expired": True
        }

    query = state["query"]
    user_context = state["user_context"]
    knowledge_context = state.get("knowledge_context", "")
    tool_results = state.get("tool_results", [])
    references = state.get("references", [])
    memory_summary = state.get("memory_summary", "")
    conversation_history = state.get("conversation_history", [])

    # ── 构建合并后的上下文（知识库 + 工具结果） ──
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

    knowledge_context_combined = "\n\n".join(context_parts) if context_parts else None

    # ── 构建 System Prompt（含长期记忆） ──
    # 平台管理员可跨租户访问，普通用户限定本租户
    if is_platform_admin(user_context):
        tenant_rule = "当前用户为平台管理员，可跨租户访问所有数据，但仍需遵守数据权限规则"
    else:
        tenant_rule = f"用户只能查询和操作本租户（tenant_id={user_context.tenant_id}）范围内的数据"

    system_prompt = SYSTEM_PROMPT.format(
        tenant_id=user_context.tenant_id,
        user_id=user_context.user_id,
        username=user_context.username or "",
        nickname=user_context.nickname or user_context.username or "用户",
        data_scope=user_context.data_scope or "NONE",
        permissions_summary=describe_permissions(user_context),
        tenant_rule=tenant_rule
    )

    if memory_summary:
        system_prompt += f"\n\n【用户长期记忆】\n{memory_summary}"

    # ── 使用 ContextManager 组装完整消息列表 ──
    ctx_manager = ContextManager()
    messages = ctx_manager.build_messages(
        system_prompt=system_prompt,
        conversation_history=conversation_history or [],
        current_input=query,
        knowledge_context=knowledge_context_combined
    )

    # ── 转换为 LangChain 消息格式 ──
    lc_messages = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        if role == "system":
            lc_messages.append(SystemMessage(content=content))
        elif role == "user":
            lc_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            lc_messages.append(AIMessage(content=content))

    try:
        # 使用 ainvoke - LangGraph 的 messages stream mode 会捕获 token 事件
        response = await llm.ainvoke(
            lc_messages,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS
        )
    except Exception as e:
        import traceback, logging
        logger = logging.getLogger(__name__)
        logger.error("[aggregator] LLM调用失败: %s\n%s", e, traceback.format_exc())
        return {
            "final_response": f"抱歉，生成回答时出错：{str(e)}",
            "token_usage": {"input": 0, "output": 0},
            "references": references,
            "error": str(e)
        }

    final_response = _get_llm_content(response)

    # Token用量：优先使用模型返回的实际值（usage_metadata），否则估算
    token_usage = {}
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        um = response.usage_metadata
        token_usage = {
            "input": um.get("input_tokens", 0),
            "output": um.get("output_tokens", 0)
        }
    if not token_usage.get("input"):
        input_text = "\n".join(m.get("content", "") for m in messages)
        token_usage["input"] = ctx_manager._estimate_tokens(input_text)
    if not token_usage.get("output"):
        token_usage["output"] = ctx_manager._estimate_tokens(final_response)

    return {
        "final_response": final_response,
        "token_usage": token_usage,
        "references": references
    }


async def generate_conversation_title(first_message: str, llm) -> str:
    """
    根据用户首条消息自动生成会话标题

    Args:
        first_message: 用户的第一条消息
        llm: LLM客户端

    Returns:
        会话标题（不超过15字）
    """
    try:
        prompt = TITLE_GENERATION_PROMPT.format(first_message=first_message)
        response = await llm.ainvoke(
            [HumanMessage(content=prompt)],
            temperature=settings.TITLE_GEN_TEMPERATURE,
            max_tokens=settings.TITLE_GEN_MAX_TOKENS
        )
        title = _get_llm_content(response).strip()
        # 截断到上限
        max_len = settings.CONVERSATION_TITLE_MAX_LENGTH
        if len(title) > max_len:
            title = title[:max_len]
        return title
    except Exception:
        # 降级：取消息前N字作为标题
        max_len = settings.CONVERSATION_TITLE_MAX_LENGTH
        return first_message[:max_len] if len(first_message) > max_len else first_message
