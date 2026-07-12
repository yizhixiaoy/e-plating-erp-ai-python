"""货物图片相似度搜索服务

基于pgvector的HNSW索引，实现货物图片的相似度搜索。
"""
import logging

import aiohttp
import asyncpg

from app.services.goods_image_clip import GoodsImageClipService
from app.services.oss_storage import OssStorageService

logger = logging.getLogger(__name__)


class GoodsImageSearchService:
    """货物图片相似度搜索服务"""

    def __init__(self, db_pool: asyncpg.Pool, clip_service: GoodsImageClipService, oss_service: OssStorageService):
        self.db_pool = db_pool
        self.clip_service = clip_service
        self.oss_service = oss_service

    async def search_similar_images(
        self,
        query_image_bytes: bytes,
        threshold: float = 0.7,
        top_k: int = 5,
        tenant_id: int = None,
    ) -> list[dict]:
        """上传图片，搜索相似的货物图片

        Args:
            query_image_bytes: 查询图片的二进制数据
            threshold: 相似度阈值（默认0.7）
            top_k: 返回结果数量（默认5）
            tenant_id: 租户ID（数据隔离）

        Returns:
            匹配结果列表 [{item_id, order_no, item_name, similarity, thumbnail_url}, ...]
        """
        try:
            # 1. 提取查询图片特征向量
            query_embedding = self.clip_service.get_embedding(query_image_bytes)

            # 2. 使用pgvector HNSW搜索相似图片
            sql = """
                SELECT id, tenant_id, order_id, item_id, node_id,
                       image_type, oss_path, image_url, thumbnail_url,
                       1 - (embedding <=> $1::vector) AS similarity
                FROM goods_image_feature
                WHERE is_deleted = FALSE
                  AND image_type = 'SAMPLE'
                  AND tenant_id = $2
                ORDER BY similarity DESC
                LIMIT $3
            """

            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(sql, query_embedding, tenant_id, top_k)

            # 3. 过滤低于阈值的結果
            matches = []
            for row in rows:
                sim = float(row["similarity"])
                if sim >= threshold:
                    matches.append({
                        "id": row["id"],
                        "item_id": row["item_id"],
                        "order_id": row["order_id"],
                        "node_id": row["node_id"],
                        "image_type": row["image_type"],
                        "oss_path": row["oss_path"],
                        "image_url": row["image_url"],
                        "thumbnail_url": row["thumbnail_url"],
                        "similarity": round(sim, 4),
                    })

            # 4. 批量从Java获取业务数据（order_no, item_name）
            if matches:
                item_ids = [m["item_id"] for m in matches if m["item_id"]]
                if item_ids:
                    business_data = await self._fetch_business_data(item_ids, tenant_id)
                    for m in matches:
                        if m["item_id"] in business_data:
                            m.update(business_data[m["item_id"]])

            logger.info("[GoodsSearch] 图片搜索完成: 返回%d条匹配", len(matches))
            return matches

        except Exception as e:
            logger.error("[GoodsSearch] 图片搜索失败: %s", e, exc_info=True)
            return []

    async def _fetch_business_data(self, item_ids: list, tenant_id: int) -> dict:
        """从Java后端批量获取货物明细的业务数据

        Returns:
            {item_id: {"order_no": ..., "item_name": ..., "company_name": ...}}
        """
        try:
            from app.services.java_client import java_get
            result = await java_get(
                f"/api/v1/goods/items/business-data?item_ids={','.join(map(str, item_ids))}&tenant_id={tenant_id}"
            )
            if result.get("success") and result.get("data"):
                # Java返回格式: [{"itemId": 123, "orderNo": "GD...", "itemName": "..."}, ...]
                return {
                    item["itemId"]: {
                        "order_no": item.get("orderNo", ""),
                        "item_name": item.get("itemName", ""),
                        "company_name": item.get("companyName", ""),
                    }
                    for item in result["data"]
                }
        except Exception as e:
            logger.warning("[GoodsSearch] 获取业务数据失败: %s", e)
        return {}

    async def register_image_features(self, image_records: list[dict]) -> int:
        """将Java端goods_image表中的图片注册到PostgreSQL特征库

        Args:
            image_records: 图片记录列表 [{id, order_id, item_id, node_id, image_type, oss_path, image_url, file_size, ...}]

        Returns:
            成功注册的数量
        """
        if not image_records:
            return 0

        try:
            # 下载所有图片并提取特征
            from app.config import settings

            insert_sql = """
                INSERT INTO goods_image_feature
                    (id, tenant_id, order_id, item_id, node_id, image_type,
                     embedding, oss_path, image_url, thumbnail_url, file_size,
                     created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7::vector, $8, $9, $10, $11,
                        NOW(), NOW())
                ON CONFLICT (id) DO UPDATE SET
                    embedding = EXCLUDED.embedding,
                    oss_path = EXCLUDED.oss_path,
                    updated_at = NOW()
            """

            inserted = 0
            async with aiohttp.ClientSession() as session:
                for record in image_records:
                    try:
                        # 从OSS下载图片
                        img_bytes = await self._download_image(session, record["oss_path"])
                        if not img_bytes:
                            continue

                        # 提取特征向量
                        embedding = self.clip_service.get_embedding(img_bytes)

                        # 存入PostgreSQL
                        await self.db_pool.execute(
                            insert_sql,
                            record["id"],
                            record.get("tenant_id"),
                            record.get("order_id"),
                            record.get("item_id"),
                            record.get("node_id"),
                            record["image_type"],
                            embedding,
                            record["oss_path"],
                            record.get("image_url", ""),
                            record.get("thumbnail_url", ""),
                            record.get("file_size", 0),
                        )
                        inserted += 1

                    except Exception as e:
                        logger.warning("[GoodsSearch] 注册图片特征失败: id=%s, err=%s",
                                       record.get("id"), e)
                        continue

            logger.info("[GoodsSearch] 图片特征注册完成: 成功%d/%d", inserted, len(image_records))
            return inserted

        except Exception as e:
            logger.error("[GoodsSearch] 批量注册图片特征失败: %s", e, exc_info=True)
            return 0

    async def _download_image(self, session: aiohttp.ClientSession, oss_path: str) -> bytes:
        """从OSS下载图片"""
        try:
            # 通过Java网关下载图片
            url = self.oss_service.get_resource_url(oss_path, action="download")
            # 如果是本地调试，直接从OSS下载
            from app.config import settings
            if settings.OSS_ENABLED and settings.OSS_ENDPOINT:
                full_url = f"https://{settings.OSS_ENDPOINT}/{settings.OSS_BUCKET}/{oss_path}"
            else:
                full_url = url  # 通过Java网关

            async with session.get(full_url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    return await resp.read()
        except Exception as e:
            logger.warning("[GoodsSearch] 下载图片失败: oss_path=%s, err=%s", oss_path, e)
        return b""
