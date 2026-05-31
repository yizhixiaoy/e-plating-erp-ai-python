"""工具基类"""
from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """Agent工具基类"""

    name: str = ""
    description: str = ""

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """执行工具，返回结果"""
        raise NotImplementedError

    def to_dict(self) -> dict:
        """转为字典格式供LLM理解"""
        return {
            "name": self.name,
            "description": self.description
        }
