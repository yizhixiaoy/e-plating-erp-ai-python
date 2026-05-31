"""Excel文档解析器"""
from app.parser.base import BaseParser


class XlsxParser(BaseParser):
    name = "Excel解析器"
    supported_extensions = ["xlsx", "xls"]

    def parse(self, file_path: str) -> str:
        """解析Excel文件"""
        try:
            from openpyxl import load_workbook

            wb = load_workbook(file_path, data_only=True)
            text_parts = []

            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                sheet_text = [f"--- 工作表: {sheet_name} ---"]

                for row in ws.iter_rows(values_only=True):
                    row_text = " | ".join([
                        str(cell) if cell is not None else ""
                        for cell in row
                    ])
                    if row_text.strip().replace("|", "").strip():
                        sheet_text.append(row_text)

                if len(sheet_text) > 1:
                    text_parts.extend(sheet_text)

            wb.close()
            return "\n".join(text_parts)
        except ImportError:
            return "Excel解析器依赖未安装 (openpyxl)"
        except Exception as e:
            return f"Excel解析失败: {str(e)}"
