"""LLM工厂 - 支持DeepSeek/Qwen等多模型热切换

按设计文档 7.1 模型选型矩阵：
- 高性价比对话 → DeepSeek-V4-flash（create_chat_llm）
- 复杂推理       → DeepSeek-V4-pro（create_reasoning_llm）
- 智能体决策     → Qwen3.7-Max（create_agent_llm）

DeepSeek 模型使用 langchain_deepseek.ChatDeepSeek（原生支持 reasoning_content）
Qwen 模型使用 langchain_openai.ChatOpenAI（兼容 OpenAI 接口）
"""
from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from app.config import settings


def create_chat_llm(
    temperature: float = None,
    max_tokens: int = None,
    streaming: bool = False,
    enable_thinking: bool = False
) -> ChatDeepSeek:
    """创建对话模型（DeepSeek-V4-flash，高性价比对话场景）

    Args:
        temperature: 温度参数，默认使用 LLM_TEMPERATURE
        max_tokens: 最大输出Token，默认使用 LLM_MAX_TOKENS
        streaming: 是否流式输出（aggregator节点需要开启）
        enable_thinking: 是否启用深度思考模式（aggregator节点需要开启）

    Returns:
        ChatDeepSeek实例（原生支持 reasoning_content）
    """
    kwargs = {
        "model": settings.LLM_MODEL_CHAT,
        "api_key": settings.LLM_API_KEY,
        "api_base": settings.LLM_BASE_URL,
        "temperature": temperature if temperature is not None else settings.LLM_TEMPERATURE,
        "max_tokens": max_tokens or settings.LLM_MAX_TOKENS,
        "streaming": streaming,
    }
    # DeepSeek 思考模式默认开启，必须显式设置 thinking type
    # 不设置时模型仍会消耗 max_tokens 做内部推理，导致 content 为空
    kwargs["extra_body"] = {
        "thinking": {"type": "enabled" if enable_thinking else "disabled"}
    }
    return ChatDeepSeek(**kwargs)


def create_reasoning_llm(
    streaming: bool = False,
    enable_thinking: bool = True
) -> ChatDeepSeek:
    """创建推理模型（DeepSeek-V4-pro，复杂推理场景）

    Args:
        streaming: 是否流式输出
        enable_thinking: 是否启用深度思考（推理模型默认开启）

    Returns:
        ChatDeepSeek实例（原生支持 reasoning_content）
    """
    kwargs = {
        "model": settings.LLM_MODEL_REASON,
        "api_key": settings.LLM_API_KEY,
        "api_base": settings.LLM_BASE_URL,
        "temperature": settings.LLM_REASONING_TEMPERATURE,
        "max_tokens": settings.LLM_MAX_TOKENS,
        "streaming": streaming,
    }
    # DeepSeek 思考模式默认开启，必须显式设置 thinking type
    kwargs["extra_body"] = {
        "thinking": {"type": "enabled" if enable_thinking else "disabled"}
    }
    return ChatDeepSeek(**kwargs)


def create_agent_llm(
    temperature: float = None,
    max_tokens: int = None,
    streaming: bool = False,
    enable_thinking: bool = False
) -> ChatOpenAI:
    """创建智能体决策模型（Qwen3.7-Max，任务规划/分类场景）

    Qwen 通过 DashScope 兼容 OpenAI 接口调用，无需 thinking 展示。

    Args:
        temperature: 温度参数，默认使用 PLANNER_TEMPERATURE
        max_tokens: 最大输出Token
        streaming: 是否流式输出
        enable_thinking: 是否启用深度思考模式

    Returns:
        ChatOpenAI实例（Qwen 兼容 OpenAI 接口）
    """
    kwargs = {
        "model": settings.QWEN_MODEL,
        "api_key": settings.QWEN_API_KEY or settings.LLM_API_KEY,
        "base_url": settings.QWEN_BASE_URL,
        "temperature": temperature if temperature is not None else settings.PLANNER_TEMPERATURE,
        "max_tokens": max_tokens or settings.LLM_MAX_TOKENS,
        "streaming": streaming,
    }
    # Qwen 通过 enable_thinking 参数控制思考模式（默认关闭，避免 content 为空）
    kwargs["extra_body"] = {"enable_thinking": bool(enable_thinking)}
    return ChatOpenAI(**kwargs)


# 兼容旧代码的别名
create_llm = create_chat_llm
