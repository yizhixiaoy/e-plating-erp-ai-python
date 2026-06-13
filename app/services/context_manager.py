"""上下文窗口管理 - 智能管理LLM上下文窗口"""
from app.config import settings


class ContextManager:
    """管理LLM上下文窗口，智能截断历史消息"""

    def __init__(
        self,
        max_context_tokens: int = None,
        system_prompt_budget: int = None,
        output_reserve: int = None
    ):
        self.max_context_tokens = max_context_tokens or settings.MAX_CONTEXT_TOKENS
        self.system_prompt_budget = system_prompt_budget or settings.SYSTEM_PROMPT_BUDGET
        self.output_reserve = output_reserve or settings.OUTPUT_RESERVE_TOKENS
        self.history_budget = settings.HISTORY_BUDGET

    def build_messages(
        self,
        system_prompt: str,
        conversation_history: list[dict],
        current_input: str,
        knowledge_context: str = None
    ) -> list[dict]:
        """
        构建LLM请求消息列表

        Args:
            system_prompt: 系统提示
            conversation_history: 对话历史
            current_input: 当前用户输入
            knowledge_context: 知识库检索上下文

        Returns:
            消息列表 [{"role": "system"|"user"|"assistant", "content": "..."}]
        """
        messages = []

        # 1. System Prompt
        if knowledge_context:
            system_prompt = (
                f"{system_prompt}\n\n"
                f"【参考知识】请基于以下知识库内容回答用户问题，并在回答中标注引用来源：\n"
                f"{knowledge_context}"
            )
        messages.append({"role": "system", "content": system_prompt})

        # 2. 历史消息（从最近开始取，直到用完预算）
        history_messages = self._select_history(conversation_history)
        messages.extend(history_messages)

        # 3. 当前用户输入
        messages.append({"role": "user", "content": current_input})

        return messages

    def _select_history(self, history: list[dict]) -> list[dict]:
        """选择历史消息（从最近到最早，直到用完预算）"""
        selected = []
        used_tokens = 0

        for msg in reversed(history):
            msg_tokens = self._estimate_tokens(msg.get("content", ""))
            if used_tokens + msg_tokens <= self.history_budget:
                selected.insert(0, msg)
                used_tokens += msg_tokens
            else:
                break

        return selected

    def _estimate_tokens(self, text: str) -> int:
        """估算文本Token数（中文：字符数/1.5，英文：字符数/4）"""
        if not text:
            return 0
        chinese_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        other_chars = len(text) - chinese_chars
        return int(chinese_chars / 1.5 + other_chars / 4)


async def compress_history(messages: list[dict], keep_recent: int = None, llm=None) -> list[dict]:
    """
    历史压缩：超过keep_recent条的消息压缩为摘要

    Args:
        messages: 完整消息列表
        keep_recent: 保留最近N条完整消息（默认从config读取）
        llm: LLM客户端

    Returns:
        压缩后的消息列表
    """
    if keep_recent is None:
        keep_recent = settings.COMPRESS_KEEP_RECENT

    if len(messages) <= keep_recent or not llm:
        return messages

    old_messages = messages[:-keep_recent]
    recent_messages = messages[-keep_recent:]

    old_text = "\n".join([
        f"[{m.get('role', '')}] {m.get('content', '')}"
        for m in old_messages
    ])

    max_chars = settings.COMPRESS_MAX_CHARS
    summary_prompt = f"""请将以下多轮对话压缩为一段简洁的摘要，保留关键信息：

{old_text}

请输出简洁的中文摘要（{max_chars}字以内）："""

    try:
        from langchain_core.messages import HumanMessage
        response = await llm.ainvoke(
            [HumanMessage(content=summary_prompt)],
            temperature=settings.COMPRESS_TEMPERATURE,
            max_tokens=settings.COMPRESS_MAX_TOKENS
        )
        summary = response.content
    except Exception:
        summary = "历史对话摘要生成失败"

    compressed = [
        {"role": "user", "content": f"[系统自动生成的历史对话摘要] {summary}"}
    ]
    compressed.extend(recent_messages)

    return compressed
