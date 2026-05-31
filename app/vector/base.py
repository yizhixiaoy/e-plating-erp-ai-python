"""VectorStore抽象接口"""
from abc import ABC, abstractmethod


class VectorStore(ABC):
    """向量存储抽象接口"""

    @abstractmethod
    async def add_vectors(
        self,
        vectors: list[list[float]],
        metadatas: list[dict],
        ids: list[str] = None
    ) -> list[str]:
        """添加向量"""
        raise NotImplementedError

    @abstractmethod
    async def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        filter: dict = None
    ) -> list[dict]:
        """相似度检索"""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, ids: list[str]):
        """删除向量"""
        raise NotImplementedError
