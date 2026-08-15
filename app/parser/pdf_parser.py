"""PDF解析器 - 文字型PDF结构化提取（文本+表格），扫描件OCR降级"""
import logging
from app.parser.base import BaseParser

logger = logging.getLogger(__name__)


class PdfParser(BaseParser):
    name = "PDF解析器"
    supported_extensions = ["pdf"]

    # PyMuPDF表格查找策略：lines_strict 适合有边框线的表格
    # 对于无边框线表格，可降级为 lines 或 text
    TABLE_STRATEGIES = ["lines_strict", "lines", "text"]

    def parse(self, file_path: str) -> str:
        """解析PDF文件——提取文字+结构化表格"""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(file_path)
            text_parts = []

            for page_num, page in enumerate(doc):
                page_header = f"--- 第{page_num + 1}页 ---"

                # 1. 提取页面纯文本
                page_text = page.get_text()

                # 2. 提取结构化表格（PyMuPDF 1.23+ 支持 find_tables）
                tables_text = self._extract_tables(page)

                # 合并文本和表格
                if tables_text:
                    combined = f"{page_header}\n{page_text}\n\n【本页表格】\n{tables_text}"
                else:
                    combined = f"{page_header}\n{page_text}"

                if combined.strip() != page_header:
                    text_parts.append(combined)

            doc.close()

            if text_parts:
                return "\n\n".join(text_parts)
            else:
                return self._ocr_parse(file_path)
        except ImportError:
            return "PDF解析器依赖未安装 (PyMuPDF)"
        except Exception as e:
            logger.warning(f"PDF解析异常: {e}")
            return f"PDF解析失败: {str(e)}"

    def _extract_tables(self, page) -> str:
        """使用 PyMuPDF find_tables() 提取页面中的结构化表格

        Args:
            page: fitz.Page 对象

        Returns:
            结构化表格文本，无表格时返回空字符串
        """
        all_tables = []

        for strategy in self.TABLE_STRATEGIES:
            try:
                tables = page.find_tables(strategy=strategy)
                if tables and tables.tables:
                    for table in tables.tables:
                        table_text = self._format_table(table)
                        if table_text:
                            all_tables.append(table_text)
                    break  # 一种策略成功即停止
            except Exception:
                continue

        return "\n\n".join(all_tables) if all_tables else ""

    def _format_table(self, table) -> str:
        """将 PyMuPDF Table 对象格式化为 Markdown 表格文本

        Args:
            table: fitz.table.Table 对象（含 .extract(), .header 等属性）

        Returns:
            Markdown 格式的表格文本
        """
        try:
            rows = table.extract()  # list[list[str|None]]
        except Exception:
            return ""

        if not rows or len(rows) < 1:
            return ""

        # 清洗单元格：None→""，去除首尾空白，统一换行符
        cleaned = []
        for row in rows:
            cleaned_row = [
                str(cell).strip().replace("\n", " ") if cell else ""
                for cell in row
            ]
            # 跳过全空行
            if any(c for c in cleaned_row):
                cleaned.append(cleaned_row)

        if not cleaned:
            return ""

        # 检测表头行（通常第一行或 table.header 标记的）
        header_rows = set()
        try:
            if hasattr(table, 'header') and table.header:
                header_info = table.header
                if hasattr(header_info, 'names') and header_info.names:
                    for name in header_info.names:
                        header_rows.add(name)
        except Exception:
            pass

        # 构建 Markdown 表格
        lines = []
        for i, row in enumerate(cleaned):
            lines.append("| " + " | ".join(row) + " |")
            # 表头分隔线（第一行之后）
            if i == 0 and len(cleaned) > 1:
                lines.append("| " + " | ".join(["---"] * len(row)) + " |")

        return "\n".join(lines)

    def _ocr_parse(self, file_path: str) -> str:
        """OCR识别扫描件PDF（适配 PaddleOCR 3.x API）"""
        try:
            from paddleocr import PaddleOCR
            import fitz

            ocr = PaddleOCR(
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
            )
            doc = fitz.open(file_path)
            text_parts = []

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                pix = page.get_pixmap(dpi=300)
                img_path = f"/tmp/page_{page_num}.png"
                pix.save(img_path)

                result = ocr.predict(input=img_path)
                page_lines = []
                for res in result:
                    # PaddleOCR 3.x 结果对象：rec_texts 为识别文本列表
                    if hasattr(res, "rec_texts"):
                        page_lines.extend(res.rec_texts)
                    elif hasattr(res, "to_dict"):
                        d = res.to_dict()
                        texts = d.get("rec_texts", d.get("text", []))
                        if isinstance(texts, list):
                            page_lines.extend(texts)
                        elif isinstance(texts, str):
                            page_lines.append(texts)

                if page_lines:
                    page_text = "\n".join(page_lines)
                    text_parts.append(f"--- 第{page_num + 1}页 (OCR) ---\n{page_text}")

            doc.close()
            return "\n\n".join(text_parts) if text_parts else "OCR未识别到文字"
        except ImportError:
            return "PaddleOCR依赖未安装"
        except Exception as e:
            logger.warning(f"OCR识别异常: {e}")
            return f"OCR识别失败: {str(e)}"
