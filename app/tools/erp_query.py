"""业务数据查询工具 - 通过Java API只读访问ERP业务数据"""
import logging
from app.tools.base import BaseTool
from app.config import settings
from app.services.java_client import java_post, get_cached_schema, build_schema_description
from app.services.permissions import AI_PERMS

logger = logging.getLogger(__name__)


class ErpQueryTool(BaseTool):
    name = "erp_query_tool"
    required_permission = AI_PERMS.CHAT_VIEW  # 业务数据查询需要AI对话权限
    description = """
    查询ERP业务数据。支持按表名、聚合函数和筛选条件查询。
    参数：
    - table: 表名（从可用Schema中选择，如 sys_user、biz_todo、chat_message 等）
    - aggregate: 聚合函数 {"func": "count/sum/avg/max/min", "field": "字段名"}
    - filters: 筛选条件 {"date_range": [...], "status": "..."}
    返回查询结果文本和引用来源。

    常见查询示例：
    - 查询员工总数："table": "sys_user", "aggregate": {"func": "count", "field": "*"}
    - 查询员工明细："table": "sys_user"（不含aggregate即查明细）
    - 查询待办："table": "biz_todo", "filters": {"status": "PENDING"}
    """

    def __init__(self, auth_headers: dict = None):
        self.auth_headers = auth_headers or {}

    def set_auth_headers(self, headers: dict):
        """更新认证头（每次请求前由chat端点调用）"""
        self.auth_headers = headers

    async def get_schema_description(self) -> str:
        """获取当前可用的数据库Schema描述文本（供LLM prompt注入）"""
        schema = await get_cached_schema(self.auth_headers)
        return build_schema_description(schema)

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

        logger.info("[erp_query] 查询表=%s, 聚合=%s, 筛选=%s", table, aggregate, filters)
        result = await java_post("/api/v1/ai/data-query", query_params, self.auth_headers)

        if result["success"]:
            data = result["data"]
            content = data.get("result", {})
            result_text = self._format_result(table, aggregate, filters, content)
            logger.info("[erp_query] 查询成功: table=%s, result_len=%d", table, len(result_text))
            return {
                "content": result_text,
                "references": [{
                    "source_type": "database",
                    "source_id": table,
                    "doc_title": table,
                    "section_title": self._build_query_description(filters)
                }]
            }
        else:
            logger.warning("[erp_query] 查询失败: %s", result["error"])
            resp: dict = {
                "content": result["error"],
                "references": []
            }
            # 传播401错误码，供executor_node检测并触发全局token过期处理
            if result.get("code") == 401:
                resp["error_code"] = 401
            return resp

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
            return "全表查询"
        if "date_range" in filters:
            dates = filters.get("date_range", ["", ""])
            return f"{dates[0] if len(dates) > 0 else ''} - {dates[1] if len(dates) > 1 else ''} 数据"
        return str(filters)
