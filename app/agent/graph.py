"""LangGraph图定义与编译"""
from langgraph.graph import StateGraph, END

from app.agent.state import AgentState
from app.agent.classifier import classify_task
from app.agent.nodes import planner_node, executor_node, aggregator_node
from app.config import settings


def build_agent_graph(chat_llm, agent_llm, tools: dict, checkpointer=None):
    """
    构建LangGraph Agent执行图

    按设计文档7.1模型选型：
    - classifier/executor/aggregator → DeepSeek-V4-flash（chat_llm）
    - planner → Qwen3.7-Max（agent_llm）

    节点流程：
    classifier → (simple?) → executor → aggregator → END
              → (medium/complex?) → planner → executor → aggregator → END

    Thinking/Streaming 按节点控制：
    - classifier: thinking=OFF, streaming=OFF（快速分类）
    - planner:    thinking=OFF, streaming=OFF（内部规划）
    - executor:   thinking=OFF, streaming=OFF（工具选择+执行）
    - aggregator: thinking=ON,  streaming=ON （最终回答，实时展示推理过程）

    Args:
        chat_llm: 高性价比对话模型（DeepSeek-V4-flash）
        agent_llm: 智能体决策模型（Qwen-Max）
        tools: 工具字典
        checkpointer: AsyncPostgresSaver实例，为None时不启用状态持久化
    """
    workflow = StateGraph(AgentState)

    # ── 为 aggregator 创建独立的 streaming + thinking LLM ──
    # thinking 模式必须用 deepseek-v4-pro（flash 不支持 thinking）
    # 非 thinking 模式用 deepseek-v4-flash（高性价比）
    if settings.AGGREGATOR_THINKING:
        from app.services.llm_factory import create_reasoning_llm
        aggregator_llm = create_reasoning_llm(
            streaming=settings.AGGREGATOR_STREAMING,
            enable_thinking=True
        )
        print(f"[Agent] aggregator 使用推理模型: {settings.LLM_MODEL_REASON} (thinking=ON, streaming=ON)")
    else:
        from app.services.llm_factory import create_chat_llm
        aggregator_llm = create_chat_llm(
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            streaming=settings.AGGREGATOR_STREAMING,
            enable_thinking=False
        )
        print(f"[Agent] aggregator 使用对话模型: {settings.LLM_MODEL_CHAT} (thinking=OFF, streaming={'ON' if settings.AGGREGATOR_STREAMING else 'OFF'})")

    # 注册节点
    async def _classify(s):
        return await classify_task(s, chat_llm)

    async def _planner(s):
        return await planner_node(s, agent_llm, tools)

    async def _executor(s):
        return await executor_node(s, chat_llm, tools)

    async def _aggregator(s):
        return await aggregator_node(s, aggregator_llm)

    workflow.add_node("classifier", _classify)
    workflow.add_node("planner", _planner)
    workflow.add_node("executor", _executor)
    workflow.add_node("aggregator", _aggregator)

    # 设置入口
    workflow.set_entry_point("classifier")

    # 条件路由：根据复杂度决定下一步
    def route_by_complexity(state: AgentState) -> str:
        complexity = state.get("task_complexity", "simple")
        if complexity == "simple":
            return "executor"
        else:
            return "planner"

    workflow.add_conditional_edges(
        "classifier",
        route_by_complexity,
        {
            "executor": "executor",
            "planner": "planner"
        }
    )

    # planner → executor
    workflow.add_edge("planner", "executor")

    # executor → aggregator
    workflow.add_edge("executor", "aggregator")

    # aggregator → END
    workflow.add_edge("aggregator", END)

    # 编译图
    if checkpointer:
        graph = workflow.compile(checkpointer=checkpointer)
    else:
        graph = workflow.compile()

    return graph
