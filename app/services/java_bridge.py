"""Java后端API桥接客户端 - 只读调用Java后端ERP业务数据"""
import httpx
from app.config import settings


class JavaBridgeClient:
    """Java后端API客户端"""

    def __init__(self, auth_headers: dict = None):
        self.base_url = settings.JAVA_API_BASE_URL
        self.api_key = settings.JAVA_API_KEY
        self.timeout = settings.JAVA_API_TIMEOUT
        self.auth_headers = auth_headers or {}

    async def query_data(
        self,
        endpoint: str,
        params: dict = None
    ) -> dict:
        """通用数据查询"""
        params = params or {}
        headers = {
            "X-Internal-Api-Key": self.api_key,
            "X-Tenant-Id": str(self.auth_headers.get("tenant_id", "")),
            "X-User-Id": str(self.auth_headers.get("user_id", "")),
            "X-Data-Scope": self.auth_headers.get("data_scope", ""),
            "Authorization": self.auth_headers.get("authorization", ""),
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}{endpoint}",
                    json=params,
                    headers=headers
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": response.text, "status": response.status_code}
        except httpx.TimeoutException:
            return {"error": "请求超时"}
        except Exception as e:
            return {"error": str(e)}

    async def query_order_stats(self, date_range: list, status: str = None) -> dict:
        """查询订单统计"""
        filters = {"date_range": date_range}
        if status:
            filters["status"] = status
        return await self.query_data("/api/v1/ai/data-query", {
            "table": "order",
            "aggregate": {"func": "count", "field": "*"},
            "filters": filters
        })
