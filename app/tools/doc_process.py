"""对话中临时文档处理工具"""
from app.tools.base import BaseTool
from app.config import settings
from app.services.permissions import AI_PERMS


class DocProcessTool(BaseTool):
    name = "doc_process_tool"
    required_permission = AI_PERMS.CHAT_VIEW  # 文档处理需要AI对话权限
    description = """
    处理用户在对话中上传的临时文档。支持总结、合并对比、提取要点、翻译、数据分析。
    参数：
    - file_ids: 上传文件ID列表
    - operation: 操作类型（summarize/compare/extract/translate/analyze）
    - instruction: 用户详细指令
    - conversation_id: 当前会话ID（可选，用于隔离会话内文件访问）
    """

    def __init__(self, db_pool=None):
        self.db_pool = db_pool

    async def execute(
        self,
        file_ids: list[str],
        operation: str,
        instruction: str,
        conversation_id: int = None
    ) -> dict:
        """执行文档处理"""
        if not self.db_pool:
            return {"content": "文档处理服务暂未就绪", "references": []}

        try:
            # 从临时文档表读取解析后的文本（按 conversation_id 隔离访问范围）
            async with self.db_pool.acquire() as conn:
                if conversation_id:
                    rows = await conn.fetch(
                        """SELECT file_id, file_name, file_type, parsed_text, parse_status
                           FROM temp_document
                           WHERE file_id = ANY($1::varchar[])
                             AND (conversation_id = $2 OR conversation_id IS NULL)
                             AND is_deleted = FALSE""",
                        file_ids, conversation_id
                    )
                else:
                    rows = await conn.fetch(
                        """SELECT file_id, file_name, file_type, parsed_text, parse_status
                           FROM temp_document
                           WHERE file_id = ANY($1::varchar[])
                             AND is_deleted = FALSE""",
                        file_ids
                    )

            if not rows:
                return {
                    "content": "未找到指定的临时文档，可能已过期。",
                    "references": []
                }

            doc_texts = []
            references = []

            for row in rows:
                if row["parse_status"] != "completed":
                    doc_texts.append(f"文档 {row['file_name']} 解析未完成")
                    continue

                doc_texts.append(f"【{row['file_name']}】\n{row['parsed_text']}")
                references.append({
                    "source_type": "upload",
                    "source_id": row["file_id"],
                    "doc_title": row["file_name"],
                    "page_number": None
                })

            context = "\n\n".join(doc_texts)

            operation_names = {
                "summarize": "总结",
                "compare": "对比",
                "extract": "提取",
                "translate": "翻译",
                "analyze": "分析"
            }

            result = (
                f"已读取 {len(rows)} 个文档，待进行{operation_names.get(operation, operation)}操作。\n"
                f"指令: {instruction}\n\n"
                f"文档内容:\n{context}"
            )

            return {
                "content": result,
                "references": references
            }

        except Exception as e:
            return {
                "content": f"文档处理异常: {str(e)}",
                "references": []
            }
