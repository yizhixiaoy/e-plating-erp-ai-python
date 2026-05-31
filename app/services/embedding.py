"""Embedding服务 - BAAI/bge-large-zh-v1.5"""
from app.config import settings


class EmbeddingService:
    """Embedding向量化服务"""

    def __init__(self):
        self._model = None
        self.model_name = settings.EMBEDDING_MODEL
        self.dim = settings.EMBEDDING_DIM

    @property
    def model(self):
        if self._model is None:
            from FlagEmbedding import FlagModel
            self._model = FlagModel(
                self.model_name,
                query_instruction_for_retrieval="为这个句子生成表示以用于检索相关文章："
            )
        return self._model

    def encode(self, texts: list[str]) -> list[list[float]]:
        """批量生成向量"""
        embeddings = self.model.encode(texts)
        return embeddings.tolist()

    def encode_query(self, query: str) -> list[float]:
        """生成查询向量"""
        embedding = self.model.encode_queries([query])
        return embedding[0].tolist()

    def encode_documents(self, documents: list[str]) -> list[list[float]]:
        """生成文档向量"""
        embeddings = self.model.encode_corpus(documents)
        return embeddings.tolist()

    @property
    def dimension(self) -> int:
        """向量维度"""
        return self.dim


# 全局单例
embedding_service = EmbeddingService()
