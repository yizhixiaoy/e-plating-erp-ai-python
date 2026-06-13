"""LLM工厂 - 支持DeepSeek/Qwen等多模型热切换

按设计文档 7.1 模型选型矩阵：
- 高性价比对话 → DeepSeek-V4-flash（create_chat_llm）
- 复杂推理       → DeepSeek-V4-pro（create_reasoning_llm）
- 智能体决策     → Qwen3.7-Max（create_agent_llm）
"""
from langchain_openai import ChatOpenAI
from app.config import settings


def create_chat_llm(
    temperature: float = None,
    max_tokens: int = None,
    streaming: bool = False
) -> ChatOpenAI:
    """创建对话模型（DeepSeek-V4-flash，高性价比对话场景）

    Args:
        temperature: 温度参数，默认使用 LLM_TEMPERATURE
        max_tokens: 最大输出Token，默认使用 LLM_MAX_TOKENS
        streaming: 是否流式输出

    Returns:
        ChatOpenAI实例（DeepSeek）
    """
    return ChatOpenAI(
        model=settings.LLM_MODEL_CHAT,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        temperature=temperature if temperature is not None else settings.LLM_TEMPERATURE,
        max_tokens=max_tokens or settings.LLM_MAX_TOKENS,
        streaming=streaming
    )


def create_reasoning_llm() -> ChatOpenAI:
    """创建推理模型（DeepSeek-V4-pro，复杂推理场景）"""
    return ChatOpenAI(
        model=settings.LLM_MODEL_REASON,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        temperature=settings.LLM_REASONING_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS
    )


def create_agent_llm(
    temperature: float = None,
    max_tokens: int = None,
    streaming: bool = False
) -> ChatOpenAI:
    """创建智能体决策模型（Qwen3.7-Max，任务规划/分类场景）

    Args:
        temperature: 温度参数，默认使用 PLANNER_TEMPERATURE
        max_tokens: 最大输出Token
        streaming: 是否流式输出

    Returns:
        ChatOpenAI实例（Qwen，兼容OpenAI接口）
    """
    return ChatOpenAI(
        model=settings.QWEN_MODEL,
        api_key=settings.QWEN_API_KEY or settings.LLM_API_KEY,  # 降级使用DeepSeek Key
        base_url=settings.QWEN_BASE_URL,
        temperature=temperature if temperature is not None else settings.PLANNER_TEMPERATURE,
        max_tokens=max_tokens or settings.LLM_MAX_TOKENS,
        streaming=streaming
    )


# 兼容旧代码的别名
create_llm = create_chat_llm
