"""PgVector向量存储实现 - 基于pgvector扩展"""
import asyncpg
import json
from app.vector.base import VectorStore


class PgVectorStore(VectorStore):
    """PostgreSQL + pgvector 向量存储实现

    封装pgvector的增删查操作，支持：
    - 批量插入向量及元数据
    - 余弦相似度检索（HNSW索引加速）
    - 按ID或条件批量删除
    """

    def __init__(self, db_pool: asyncpg.Pool, table: str = "knowledge_chunk"):
        self.db_pool = db_pool
        self.table = table

    async def add_vectors(
        self,
        vectors: list[list[float]],
        metadatas: list[dict],
        ids: list[str] = None
    ) -> list[str]:
        """批量添加向量到knowledge_chunk表

        Args:
            vectors: 向量列表
            metadatas: 元数据列表（需包含doc_id, kb_id, tenant_id, chunk_index, content等）
            ids: 可选ID列表（未提供时自动生成）

        Returns:
            chunk ID列表
        """
        chunk_ids = []

        async with self.db_pool.acquire() as conn:
            for i, (vector, meta) in enumerate(zip(vectors, metadatas)):
                vector_str = str(vector)
                metadata_json = json.dumps(meta.get("metadata", {}), ensure_ascii=False)

                chunk_id = await conn.fetchval(
                    f"""INSERT INTO {self.table}
                        (doc_id, kb_id, tenant_id, chunk_index, content, token_count,
                         embedding, metadata, is_deleted, created_by, updated_by, created_at, updated_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7::vector, $8::jsonb,
                                FALSE, $9, $9, NOW(), NOW())
                        RETURNING id""",
                    meta.get("doc_id"),
                    meta.get("kb_id"),
                    meta.get("tenant_id"),
                    meta.get("chunk_index", i),
                    meta.get("content", ""),
                    meta.get("token_count"),
                    vector_str,
                    metadata_json,
                    meta.get("created_by")
                )
                chunk_ids.append(str(chunk_id))

        return chunk_ids

    async def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        filter: dict = None
    ) -> list[dict]:
        """余弦相似度检索

        Args:
            query_vector: 查询向量
            top_k: 返回数量
            filter: 过滤条件（kb_id, tenant_id, doc_id等）

        Returns:
            [{"id": int, "content": str, "similarity": float, "metadata": dict}, ...]
        """
        filter_clauses = ["c.is_deleted = FALSE", "c.embedding IS NOT NULL"]
        params = [str(query_vector)]
        param_idx = 2

        if filter:
            if "kb_id" in filter:
                filter_clauses.append(f"c.kb_id = ${param_idx}")
                params.append(filter["kb_id"])
                param_idx += 1
            if "tenant_id" in filter:
                filter_clauses.append(
                    f"(kb.scope_type = 'global' OR c.tenant_id = ${param_idx})"
                )
                params.append(filter["tenant_id"])
                param_idx += 1
            if "doc_id" in filter:
                filter_clauses.append(f"c.doc_id = ${param_idx}")
                params.append(filter["doc_id"])
                param_idx += 1

        where_clause = " AND ".join(filter_clauses)

        sql = f"""
            SELECT c.id, c.doc_id, c.chunk_index, c.content, c.metadata,
                   1 - (c.embedding <=> $1::vector) AS similarity
            FROM {self.table} c
            LEFT JOIN knowledge_base kb ON c.kb_id = kb.id
            WHERE {where_clause}
            ORDER BY c.embedding <=> $1::vector
            LIMIT {top_k}
        """

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)

        return [
            {
                "id": row["id"],
                "doc_id": row["doc_id"],
                "chunk_index": row["chunk_index"],
                "content": row["content"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                "similarity": float(row["similarity"])
            }
            for row in rows
        ]

    async def delete(self, ids: list[str]):
        """按ID逻辑删除向量"""
        if not ids:
            return

        int_ids = [int(i) for i in ids]

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                f"UPDATE {self.table} SET is_deleted = TRUE, updated_at = NOW() WHERE id = ANY($1::bigint[])",
                int_ids
            )

    async def delete_by_doc(self, doc_id: int):
        """按文档ID逻辑删除所有关联向量"""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                f"UPDATE {self.table} SET is_deleted = TRUE, updated_at = NOW() WHERE doc_id = $1",
                doc_id
            )
