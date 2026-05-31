"""健康检查"""
from fastapi import APIRouter

router = APIRouter(tags=["健康检查"])


@router.get("/health")
async def health():
    """服务健康检查"""
    return {
        "status": "ok",
        "service": "ERP AI Assistant"
    }


@router.get("/api/ai/health")
async def ai_health():
    """AI服务健康检查"""
    return {
        "status": "ok",
        "components": {
            "agent": "ready",
            "llm": "configured",
            "database": "postgresql",
            "vector_store": "pgvector"
        }
    }
