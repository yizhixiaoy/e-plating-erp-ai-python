"""知识库检索工具 - pgvector向量检索 + BM25 + RRF融合 + Rerank"""
import asyncio
from app.tools.base import BaseTool
from app.config import settings
import asyncpg
import json


class KnowledgeTool(BaseTool):
    name = "knowledge_tool"
    description = """
    检索知识库中的文档片段。用于回答电镀工艺、SOP、质检标准等知识类问题。
    支持混合检索（向量+BM25）+ RRF融合 + Rerank重排序。
    参数：
    - query: 检索查询（建议改写成更精确的关键词组合）
    - kb_ids: 指定知识库ID列表（可选，为空则检索所有可见库）
    - top_k: 返回片段数量（默认5）
    - tenant_id: 租户ID（数据隔离）
    返回检索到的文本内容和引用来源。
    """

    def __init__(self, db_pool: asyncpg.Pool = None, oss_service=None):
        self.db_pool = db_pool
        self.oss_service = oss_service
        self.embedding_model = None  # 延迟加载
        self.reranker = None         # 延迟加载
        self.top_k = settings.RAG_TOP_K
        self.similarity_threshold = settings.RAG_SIMILARITY_THRESHOLD
        self.rerank_enabled = True   # Rerank总开关（模型加载失败时自动降级）

    async def execute(
        self,
        query: str,
        kb_ids: list[int] = None,
        top_k: int = None,
        tenant_id: int = None
    ) -> dict:
        """执行知识库混合检索

        完整流程：
        1. 向量检索（pgvector余弦相似度）→ 取top_k*3候选
        2. BM25检索（pg_trgm三元组匹配）→ 取top_k*3候选
        3. RRF融合（Reciprocal Rank Fusion）→ 合并排序
        4. Rerank（bge-reranker-v2-m3）→ 精排取top_k
        """
        top_k = top_k or self.top_k

        if not self.db_pool:
            return {"content": "知识库检索服务暂未就绪", "references": []}

        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

                # 构建通用过滤条件
                kb_filter, tenant_filter, base_params = self._build_filters(
                    kb_ids, tenant_id
                )

                # ── 1. 向量检索 ──
                query_embedding = await self._get_query_embedding(query)
                vector_params = [query_embedding] + base_params
                vector_sql = f"""
                    SELECT c.id, c.doc_id, c.chunk_index, c.content,
                           c.metadata, c.kb_id,
                           d.title as doc_title, d.oss_path, d.file_name,
                           kb.name as kb_name,
                           1 - (c.embedding <=> $1::vector) AS similarity
                    FROM knowledge_chunk c
                    JOIN knowledge_document d ON c.doc_id = d.id AND d.is_deleted = FALSE
                    JOIN knowledge_base kb ON c.kb_id = kb.id AND kb.is_deleted = FALSE
                    WHERE c.embedding IS NOT NULL AND c.is_deleted = FALSE
                        {kb_filter} {tenant_filter}
                        AND kb.status = 'active' AND d.parse_status = 'completed'
                    ORDER BY c.embedding <=> $1::vector
                    LIMIT {top_k * 3}
                """
                vector_rows = await conn.fetch(vector_sql, *vector_params)

                # ── 2. BM25全文检索（pg_trgm） ──
                bm25_params = [query] + base_params
                bm25_sql = f"""
                    SELECT c.id, c.doc_id, c.chunk_index, c.content,
                           c.metadata, c.kb_id,
                           d.title as doc_title, d.oss_path, d.file_name,
                           kb.name as kb_name,
                           similarity(c.content, $1) AS bm25_score
                    FROM knowledge_chunk c
                    JOIN knowledge_document d ON c.doc_id = d.id AND d.is_deleted = FALSE
                    JOIN knowledge_base kb ON c.kb_id = kb.id AND kb.is_deleted = FALSE
                    WHERE c.is_deleted = FALSE
                        {kb_filter} {tenant_filter}
                        AND kb.status = 'active' AND d.parse_status = 'completed'
                        AND c.content % $1
                    ORDER BY similarity(c.content, $1) DESC
                    LIMIT {top_k * 3}
                """
                try:
                    bm25_rows = await conn.fetch(bm25_sql, *bm25_params)
                except Exception:
                    # pg_trgm可能未启用或%操作符失败，降级仅用向量结果
                    bm25_rows = []

                # ── 3. RRF融合 ──
                fused = self._rrf_fusion(vector_rows, bm25_rows, k=60)

                if not fused:
                    return {"content": "未找到相关知识。", "references": []}

                # ── 4. Rerank精排（取前top_k*2候选重排序） ──
                candidates = fused[:top_k * 2]
                if self.rerank_enabled and len(candidates) > 1:
                    try:
                        reranked = await self._rerank(query, candidates)
                        candidates = reranked
                    except Exception:
                        pass  # Rerank失败时降级使用RRF排序结果

                # ── 5. 过滤 + 构建结果 ──
                references = []
                context_parts = []

                for item in candidates:
                    score = item.get("rrf_score", item.get("similarity", 0))
                    if score < self.similarity_threshold * 0.5:
                        continue

                    metadata = json.loads(item["metadata"]) if item.get("metadata") else {}

                    # 生成OSS预览链接（前端可直接打开预览原文件）
                    file_url = ""
                    doc_oss_path = item.get("oss_path")
                    if self.oss_service and doc_oss_path:
                        doc_filename = item.get("file_name") or item.get("doc_title")
                        file_url = self.oss_service.get_resource_url(doc_oss_path, doc_filename)

                    ref = {
                        "source_type": "knowledge",
                        "source_id": str(item["doc_id"]),
                        "doc_title": item["doc_title"],
                        "chunk_index": item["chunk_index"],
                        "similarity": round(score, 4),
                        "file_url": file_url,
                        "page_number": metadata.get("page_number"),
                        "section_title": metadata.get("section_title")
                    }
                    references.append(ref)

                    context_parts.append(
                        f"[来源: {item['doc_title']}, 片段{item['chunk_index']}]\n{item['content']}"
                    )

                    if len(references) >= top_k:
                        break

                context = "\n\n---\n\n".join(context_parts) if context_parts else "未找到相关知识。"

                return {
                    "content": context,
                    "references": references
                }

        except Exception as e:
            return {
                "content": f"知识库检索异常: {str(e)}",
                "references": []
            }

    def _build_filters(self, kb_ids: list[int] = None, tenant_id: int = None) -> tuple:
        """构建SQL过滤条件，返回 (kb_filter, tenant_filter, params)"""
        params = []
        # 参数从$2开始（$1被query或embedding占用）
        param_idx = 2

        kb_filter = ""
        if kb_ids:
            kb_filter = f"AND c.kb_id = ANY(${param_idx}::bigint[])"
            params.append(kb_ids)
            param_idx += 1

        tenant_filter = ""
        if tenant_id:
            tenant_filter = f"AND (kb.scope_type = 'global' OR kb.tenant_id = ${param_idx})"
            params.append(tenant_id)
            param_idx += 1
        else:
            tenant_filter = "AND kb.scope_type = 'global'"

        return kb_filter, tenant_filter, params

    def _rrf_fusion(self, vector_rows, bm25_rows, k: int = 60) -> list[dict]:
        """Reciprocal Rank Fusion - 融合向量和BM25检索结果

        RRF公式: score(d) = Σ 1/(k + rank_i)
        k=60 是标准推荐值，能有效平衡不同检索通道的排名差异
        """
        scores = {}  # chunk_id -> {"rrf_score": float, ...row_data}

        # 向量检索排名
        for rank, row in enumerate(vector_rows):
            cid = row["id"]
            if cid not in scores:
                scores[cid] = dict(row)
                scores[cid]["rrf_score"] = 0
            scores[cid]["rrf_score"] += 1.0 / (k + rank + 1)

        # BM25检索排名
        for rank, row in enumerate(bm25_rows):
            cid = row["id"]
            if cid not in scores:
                scores[cid] = dict(row)
                scores[cid]["rrf_score"] = 0
            scores[cid]["rrf_score"] += 1.0 / (k + rank + 1)

        # 按RRF分数降序排列
        fused = sorted(scores.values(), key=lambda x: x["rrf_score"], reverse=True)
        return fused

    async def _rerank(self, query: str, candidates: list[dict]) -> list[dict]:
        """使用bge-reranker-v2-m3对候选结果重排序"""
        if not self.reranker:
            try:
                from FlagEmbedding import FlagReranker
                # FlagReranker初始化是CPU密集操作，放入线程池
                self.reranker = await asyncio.to_thread(
                    lambda: FlagReranker(settings.RERANK_MODEL, use_fp16=True)
                )
            except ImportError:
                self.rerank_enabled = False
                return candidates

        # 构建rerank输入对：[(query, doc_content), ...]
        pairs = [(query, c["content"]) for c in candidates]

        # FlagReranker.compute_score是CPU密集操作，放入线程池避免阻塞事件循环
        rerank_scores = await asyncio.to_thread(
            lambda: self.reranker.compute_score(pairs, normalize=True)
        )

        # 将分数赋回候选
        if isinstance(rerank_scores, (list, tuple)):
            for i, score in enumerate(rerank_scores):
                candidates[i]["rrf_score"] = float(score)
        else:
            # 单条结果时返回标量
            candidates[0]["rrf_score"] = float(rerank_scores)

        # 按rerank分数降序排列
        candidates.sort(key=lambda x: x["rrf_score"], reverse=True)
        return candidates

    async def _get_query_embedding(self, query: str) -> list[float]:
        """获取查询向量"""
        if not self.embedding_model:
            from FlagEmbedding import FlagModel
            # FlagModel初始化是CPU密集操作（加载模型权重），放入线程池避免阻塞事件循环
            self.embedding_model = await asyncio.to_thread(
                lambda: FlagModel(
                    settings.EMBEDDING_MODEL,
                    query_instruction_for_retrieval="为这个句子生成表示以用于检索相关文章："
                )
            )
        # FlagEmbedding.encode是CPU密集操作，放入线程池避免阻塞事件循环
        embedding = await asyncio.to_thread(
            lambda: self.embedding_model.encode(query)
        )
        return embedding.tolist()
