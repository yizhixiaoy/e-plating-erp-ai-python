"""货物交叉比对服务

用于各加工节点上传图片时，与原始样品图片进行相似度对比，防止错加工。
"""
import logging
import asyncpg

from app.services.goods_image_clip import GoodsImageClipService

logger = logging.getLogger(__name__)


class GoodsCrossCheckService:
    """加工节点图片与原始样品的交叉比对服务"""

    def __init__(self, db_pool: asyncpg.Pool, clip_service: GoodsImageClipService):
        self.db_pool = db_pool
        self.clip_service = clip_service

    async def compare_with_original(
        self,
        query_image_bytes: bytes,
        item_id: int,
        threshold: float = 0.75,
    ) -> dict:
        """比较加工节点图片与原始样品图片的相似度

        Args:
            query_image_bytes: 加工节点上传的图片
            item_id: 货物明细ID
            threshold: 相似度阈值（默认0.75）

        Returns:
            {"matched": bool, "similarity": float, "message": str}
        """
        try:
            # 1. 获取该货物的所有SAMPLE类型图片特征
            sql = """
                SELECT embedding FROM goods_image_feature
                WHERE item_id = $1
                  AND image_type = 'SAMPLE'
                  AND is_deleted = FALSE
                ORDER BY created_at DESC
                LIMIT 1
            """

            row = await self.db_pool.fetchrow(sql, item_id)
            if not row:
                return {
                    "matched": False,
                    "similarity": 0.0,
                    "message": "未找到该货物的原始样品图片"
                }

            # 2. 提取查询图片特征
            query_embedding = self.clip_service.get_embedding(query_image_bytes)

            # 3. 计算相似度
            original_embedding = row["embedding"]
            similarity = self.clip_service.cosine_similarity(query_embedding, original_embedding)

            matched = similarity >= threshold

            message = (
                f"图片匹配{'成功' if matched else '失败'}，相似度: {similarity:.4f}"
                f"{' (超过阈值)' if matched else ' (低于阈值)'}"
            )

            logger.info("[CrossCheck] item_id=%d, similarity=%.4f, matched=%s",
                        item_id, similarity, matched)

            return {
                "matched": matched,
                "similarity": round(similarity, 4),
                "message": message,
            }

        except Exception as e:
            logger.error("[CrossCheck] 交叉比对失败: item_id=%d, err=%s", item_id, e, exc_info=True)
            return {
                "matched": False,
                "similarity": 0.0,
                "message": f"交叉比对异常: {str(e)}"
            }

    async def validate_processing(
        self,
        node_id: int,
        item_id: int,
        image_urls: list[str],
        threshold: float = 0.75,
    ) -> dict:
        """加工前验证：确认上传的图片与原始样品一致

        Args:
            node_id: 加工节点ID
            item_id: 货物明细ID
            image_urls: 加工节点上传的图片URL列表
            threshold: 相似度阈值

        Returns:
            {"valid": bool, "results": [...]}
        """
        results = []
        all_valid = True

        for url in image_urls:
            # 简化实现：实际需要从OSS下载图片
            results.append({
                "url": url,
                "matched": False,
                "similarity": 0.0,
                "message": "待实现图片下载和比对"
            })
            all_valid = False

        return {
            "valid": all_valid,
            "node_id": node_id,
            "item_id": item_id,
            "results": results,
        }
