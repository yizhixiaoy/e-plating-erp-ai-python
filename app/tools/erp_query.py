"""业务数据查询工具 - 通过Java API只读访问ERP业务数据"""
from app.tools.base import BaseTool
from app.config import settings
import httpx


class ErpQueryTool(BaseTool):
    name = "erp_query_tool"
    description = """
    查询ERP业务数据。支持按表名、聚合函数和筛选条件查询。
    参数：
    - table: 表名（order/customer/inventory/quality/production）
    - aggregate: 聚合函数 {"func": "count/sum/avg", "field": "字段名"}
    - filters: 筛选条件 {"date_range": [...], "status": "..."}
    返回查询结果文本和引用来源。
    """

    def __init__(self, auth_headers: dict = None):
        self.java_api_base = settings.JAVA_API_BASE_URL
        self.api_key = settings.JAVA_API_KEY
        self.timeout = settings.JAVA_API_TIMEOUT
        self.auth_headers = auth_headers or {}

    def set_auth_headers(self, headers: dict):
        """更新认证头（每次请求前由chat端点调用）"""
        self.auth_headers = headers

    async def execute(
        self,
        table: str,
        aggregate: dict = None,
        filters: dict = None
    ) -> dict:
        """执行业务数据查询"""
        query_params = {
            "table": table,
            "aggregate": aggregate or {},
            "filters": filters or {}
        }

        table_display_names = {
            "order": "订单表",
            "customer": "客户表",
            "inventory": "库存表",
            "quality": "质检表",
            "production": "生产表"
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {
                    "X-Internal-Api-Key": self.api_key,
                    **self.auth_headers
                }
                response = await client.post(
                    f"{self.java_api_base}/api/v1/ai/data-query",
                    json=query_params,
                    headers=headers
                )

                if response.status_code == 200:
                    data = response.json()
                    content = data.get("result", {})

                    # 格式化为可读文本
                    result_text = self._format_result(table, aggregate, filters, content)

                    return {
                        "content": result_text,
                        "references": [{
                            "source_type": "database",
                            "source_id": table,
                            "doc_title": table_display_names.get(table, table),
                            "section_title": self._build_query_description(filters)
                        }]
                    }
                else:
                    return {
                        "content": f"数据查询失败: {response.text}",
                        "references": []
                    }
        except Exception as e:
            return {
                "content": f"数据查询异常: {str(e)}",
                "references": []
            }

    def _format_result(self, table: str, aggregate: dict, filters: dict, content: dict) -> str:
        """格式化查询结果为可读文本"""
        parts = [f"查询表: {table}"]

        if aggregate:
            func = aggregate.get("func", "")
            field = aggregate.get("field", "*")
            parts.append(f"聚合: {func}({field})")

        if filters:
            filter_text = ", ".join([f"{k}={v}" for k, v in filters.items()])
            parts.append(f"筛选: {filter_text}")

        parts.append(f"结果: {content}")
        return "\n".join(parts)

    def _build_query_description(self, filters: dict) -> str:
        """构建查询描述"""
        if not filters:
            return f"全表查询"
        if "date_range" in filters:
            return f"{filters.get('date_range', ['', ''])[0]} - {filters.get('date_range', ['', ''])[1]} 数据"
        return str(filters)
