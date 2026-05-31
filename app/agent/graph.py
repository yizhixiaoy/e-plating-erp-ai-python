"""LangGraph图定义与编译"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver

from app.agent.state import AgentState
from app.agent.classifier import classify_task
from app.agent.nodes import planner_node, executor_node, aggregator_node
from app.config import settings


def build_agent_graph(chat_llm, agent_llm, tools: dict, checkpointer: PostgresSaver = None) -> StateGraph:
    """
    构建LangGraph Agent执行图

    按设计文档7.1模型选型：
    - classifier/executor/aggregator → DeepSeek-V4-flash（chat_llm）
    - planner → Qwen3.7-Max（agent_llm）

    节点流程：
    classifier → (simple?) → executor → aggregator → END
              → (medium/complex?) → planner → executor → aggregator → END
    """
    workflow = StateGraph(AgentState)

    # 注册节点：规划节点使用Qwen智能体模型
    workflow.add_node("classifier", lambda s: classify_task(s, chat_llm))
    workflow.add_node("planner", lambda s: planner_node(s, agent_llm))
    workflow.add_node("executor", lambda s: executor_node(s, chat_llm, tools))
    workflow.add_node("aggregator", lambda s: aggregator_node(s, chat_llm))

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
