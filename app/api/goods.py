"""货物开单相关AI接口

提供图片搜索、交叉比对、货物识别等功能。
"""
import io
import logging

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from app.config import settings
from app.services.goods_image_clip import GoodsImageClipService
from app.services.goods_image_search import GoodsImageSearchService
from app.services.goods_cross_check import GoodsCrossCheckService
from app.services.oss_storage import OssStorageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai/goods", tags=["货物开单AI服务"])


def get_clip_service():
    if not hasattr(router.state, "clip_service"):
        router.state.clip_service = GoodsImageClipService()
    return router.state.clip_service


def get_search_service():
    if not hasattr(router.state, "search_service"):
        clip_service = get_clip_service()
        oss_service = OssStorageService()
        router.state.search_service = GoodsImageSearchService(
            db_pool=settings.DB_POOL,
            clip_service=clip_service,
            oss_service=oss_service,
        )
    return router.state.search_service


def get_cross_check_service():
    if not hasattr(router.state, "cross_check_service"):
        clip_service = get_clip_service()
        router.state.cross_check_service = GoodsCrossCheckService(
            db_pool=settings.DB_POOL,
            clip_service=clip_service,
        )
    return router.state.cross_check_service


@router.post("/search-image")
async def search_image(
    file: UploadFile = File(..., description="查询图片"),
    threshold: float = Query(0.7, ge=0.0, le=1.0, description="相似度阈值"),
    tenant_id: int = Query(None, description="租户ID"),
):
    """图片搜索货物

    上传图片，在货物图片库中搜索相似的样品照片。
    """
    try:
        image_bytes = await file.read()
        search_service = get_search_service()
        matches = await search_service.search_similar_images(
            query_image_bytes=image_bytes,
            threshold=threshold,
            top_k=5,
            tenant_id=tenant_id,
        )
        return {"success": True, "data": {"matches": matches, "total": len(matches)}}
    except Exception as e:
        logger.error("[Goods] 图片搜索失败: %s", e, exc_info=True)
        return {"success": False, "error": str(e), "data": {"matches": [], "total": 0}}


@router.post("/cross-check")
async def cross_check(
    item_id: int = Form(..., description="货物明细ID"),
    threshold: float = Query(0.75, ge=0.0, le=1.0, description="相似度阈值"),
    files: list[UploadFile] = File(..., description="加工节点图片"),
):
    """交叉比对：加工节点图片与原始样品比对

    防止错加工，确保上传的图片与原始样品一致。
    """
    try:
        clip_service = get_clip_service()
        cross_check_service = get_cross_check_service()

        results = []
        for file in files:
            image_bytes = await file.read()
            result = await cross_check_service.compare_with_original(
                query_image_bytes=image_bytes,
                item_id=item_id,
                threshold=threshold,
            )
            results.append(result)

        all_matched = all(r.get("matched", False) for r in results)
        return {
            "success": True,
            "data": {
                "matched": all_matched,
                "results": results,
            }
        }
    except Exception as e:
        logger.error("[Goods] 交叉比对失败: %s", e, exc_info=True)
        return {"success": False, "error": str(e), "data": {"matched": False, "results": []}}


@router.post("/register-features")
async def register_features(
    image_ids: list[int] = Form(..., description="图片ID列表"),
):
    """批量注册图片特征向量

    从Java端调用，将货物图片的特征向量注册到PostgreSQL pgvector。
    """
    try:
        search_service = get_search_service()

        # 从Java API获取图片记录信息（通过AI桥接端点）
        from app.services.java_client import java_post
        result = await java_post(
            "/api/v1/ai/goods-images",
            {"image_ids": image_ids}
        )

        if not result.get("success") or result.get("data", {}).get("code") != 200:
            error_msg = result.get("error", "未知错误")
            logger.warning("[RegisterFeatures] 从Java获取图片数据失败: %s", error_msg)
            return {"success": False, "error": error_msg, "data": {"registered": 0, "total": len(image_ids)}}

        image_records_raw = result["data"].get("result", [])

        image_records = []
        for img_data in image_records_raw:
            image_records.append({
                "id": img_data["id"],
                "tenant_id": img_data.get("tenant_id"),
                "order_id": img_data.get("order_id"),
                "item_id": img_data.get("item_id"),
                "node_id": img_data.get("node_id"),
                "record_id": img_data.get("record_id"),
                "image_type": img_data.get("image_type", "SAMPLE"),
                "oss_path": img_data.get("oss_path", ""),
                "image_url": img_data.get("image_url", ""),
                "thumbnail_url": img_data.get("thumbnail_url", ""),
                "file_size": img_data.get("file_size", 0),
            })

        count = await search_service.register_image_features(image_records)
        return {"success": True, "data": {"registered": count, "total": len(image_ids)}}
    except Exception as e:
        logger.error("[Goods] 注册图片特征失败: %s", e, exc_info=True)
        return {"success": False, "error": str(e), "data": {"registered": 0, "total": 0}}


@router.post("/recognize-item")
async def recognize_item(
    file: UploadFile = File(..., description="货物图片"),
):
    """AI识别货物

    使用视觉模型识别货物名称、材质、规格等信息。
    """
    try:
        from app.services.llm_factory import get_llm
        image_bytes = await file.read()

        # 将图片转为base64
        import base64
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        content_type = file.content_type or "image/jpeg"

        llm = get_llm()
        prompt = """请仔细分析这张货物图片，识别以下信息并以JSON格式返回：
{
    "itemName": "货物名称",
    "material": "材质",
    "specification": "规格型号",
    "suggestedUnit": "推荐计量单位",
    "confidence": 0.95
}

如果没有识别到某些信息，对应字段设为null。"""

        response = await llm.ainvoke([
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:{content_type};base64,{image_base64}"}},
                {"type": "text", "text": prompt}
            ]}
        ])

        import json
        try:
            result = json.loads(response.content)
        except (json.JSONDecodeError, AttributeError):
            result = {"itemName": response.content, "material": None, "specification": None,
                      "suggestedUnit": "个", "confidence": 0.5}

        return {"success": True, "data": result}
    except Exception as e:
        logger.error("[Goods] 货物识别失败: %s", e, exc_info=True)
        return {"success": False, "error": str(e), "data": {}}
