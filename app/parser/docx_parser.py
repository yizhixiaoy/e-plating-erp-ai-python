"""Word文档解析器"""
from app.parser.base import BaseParser


class DocxParser(BaseParser):
    name = "Word解析器"
    supported_extensions = ["docx"]

    def parse(self, file_path: str) -> str:
        """解析DOCX文件"""
        try:
            from docx import Document

            doc = Document(file_path)
            text_parts = []

            for para in doc.paragraphs:
                if para.text.strip():
                    text_parts.append(para.text)

            # 解析表格
            for table in doc.tables:
                table_text = self._parse_table(table)
                if table_text:
                    text_parts.append(table_text)

            return "\n".join(text_parts)
        except ImportError:
            return "Word解析器依赖未安装 (python-docx)"
        except Exception as e:
            return f"Word解析失败: {str(e)}"

    def _parse_table(self, table) -> str:
        """解析Word表格为文本"""
        rows = []
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            rows.append(" | ".join(cells))
        return "\n".join(rows)
