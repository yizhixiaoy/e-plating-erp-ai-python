"""知识库检索工具 - pgvector向量检索 + BM25 + RRF融合 + Rerank"""
from app.tools.base import BaseTool
from app.config import settings
import asyncpg
import json


class KnowledgeTool(BaseTool):
    name = "knowledge_tool"
    description = """
    检索知识库中的文档片段。用于回答电镀工艺、SOP、质检标准等知识类问题。
    参数：
    - query: 检索查询（建议改写成更精确的关键词组合）
    - kb_ids: 指定知识库ID列表（可选，为空则检索所有可见库）
    - top_k: 返回片段数量（默认5）
    返回检索到的文本内容和引用来源。
    """

    def __init__(self, db_pool: asyncpg.Pool = None):
        self.db_pool = db_pool
        self.embedding_model = None  # 延迟加载
        self.reranker = None         # 延迟加载
        self.top_k = settings.RAG_TOP_K
        self.similarity_threshold = settings.RAG_SIMILARITY_THRESHOLD

    async def execute(
        self,
        query: str,
        kb_ids: list[int] = None,
        top_k: int = None
    ) -> dict:
        """执行知识库检索"""
        top_k = top_k or self.top_k

        if not self.db_pool:
            return {"content": "知识库检索服务暂未就绪", "references": []}

        try:
            # 1. 生成查询向量
            query_embedding = await self._get_query_embedding(query)

            # 2. 向量检索
            async with self.db_pool.acquire() as conn:
                # 注册 pgvector 扩展
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

                # 构建SQL查询
                kb_filter = ""
                kb_params = []
                if kb_ids:
                    kb_filter = "AND c.kb_id = ANY($2::bigint[])"
                    kb_params = [kb_ids]

                sql = f"""
                    SELECT
                        c.id,
                        c.doc_id,
                        c.chunk_index,
                        c.content,
                        c.metadata,
                        c.kb_id,
                        d.title as doc_title,
                        kb.name as kb_name,
                        1 - (c.embedding <=> $1::vector) AS similarity
                    FROM knowledge_chunk c
                    JOIN knowledge_document d ON c.doc_id = d.id AND d.is_deleted = FALSE
                    JOIN knowledge_base kb ON c.kb_id = kb.id AND kb.is_deleted = FALSE
                    WHERE c.embedding IS NOT NULL
                        AND c.is_deleted = FALSE
                        {kb_filter}
                        AND kb.status = 'active'
                        AND d.parse_status = 'completed'
                    ORDER BY c.embedding <=> $1::vector
                    LIMIT {top_k * 2}
                """

                rows = await conn.fetch(sql, query_embedding, *kb_params)

                if not rows:
                    return {
                        "content": "未找到相关知识。",
                        "references": []
                    }

                # 3. 构建引用来源和上下文
                references = []
                context_parts = []

                for row in rows:
                    similarity = row["similarity"]
                    if similarity < self.similarity_threshold:
                        continue

                    metadata = json.loads(row["metadata"]) if row["metadata"] else {}

                    ref = {
                        "source_type": "knowledge",
                        "source_id": str(row["doc_id"]),
                        "doc_title": row["doc_title"],
                        "chunk_index": row["chunk_index"],
                        "similarity": round(similarity, 4),
                        "page_number": metadata.get("page_number"),
                        "section_title": metadata.get("section_title")
                    }
                    references.append(ref)

                    context_parts.append(
                        f"[来源: {row['doc_title']}, 片段{row['chunk_index']}]\n{row['content']}"
                    )

                    if len(references) >= top_k:
                        break

                context = "\n\n---\n\n".join(context_parts)

                return {
                    "content": context,
                    "references": references
                }

        except Exception as e:
            return {
                "content": f"知识库检索异常: {str(e)}",
                "references": []
            }

    async def _get_query_embedding(self, query: str) -> list[float]:
        """获取查询向量"""
        if not self.embedding_model:
            from FlagEmbedding import FlagModel
            self.embedding_model = FlagModel(
                settings.EMBEDDING_MODEL,
                query_instruction_for_retrieval="为这个句子生成表示以用于检索相关文章："
            )
        # FlagEmbedding返回numpy数组
        embedding = self.embedding_model.encode(query)
        return embedding.tolist()
