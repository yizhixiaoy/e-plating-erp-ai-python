"""文档解析器基类"""
from abc import ABC, abstractmethod
from typing import BinaryIO


class BaseParser(ABC):
    """文档解析器基类"""

    name: str = ""
    supported_extensions: list[str] = []

    @abstractmethod
    def parse(self, file_path: str) -> str:
        """解析文档，返回纯文本"""
        raise NotImplementedError

    def can_parse(self, file_type: str) -> bool:
        """判断是否能解析该类型"""
        return file_type.lower() in self.supported_extensions
