"""PDF解析器 - 文字型PDF和扫描件OCR"""
from app.parser.base import BaseParser


class PdfParser(BaseParser):
    name = "PDF解析器"
    supported_extensions = ["pdf"]

    def parse(self, file_path: str) -> str:
        """解析PDF文件"""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(file_path)
            text_parts = []
            for page_num, page in enumerate(doc):
                page_text = page.get_text()
                if page_text.strip():
                    text_parts.append(f"--- 第{page_num + 1}页 ---\n{page_text}")
            doc.close()

            if text_parts:
                return "\n\n".join(text_parts)
            else:
                return self._ocr_parse(file_path)
        except ImportError:
            return "PDF解析器依赖未安装 (PyMuPDF)"
        except Exception as e:
            return f"PDF解析失败: {str(e)}"

    def _ocr_parse(self, file_path: str) -> str:
        """OCR识别扫描件PDF"""
        try:
            from paddleocr import PaddleOCR
            import fitz

            ocr = PaddleOCR(use_angle_cls=True, lang="ch")
            doc = fitz.open(file_path)
            text_parts = []

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                pix = page.get_pixmap(dpi=300)
                img_path = f"/tmp/page_{page_num}.png"
                pix.save(img_path)

                result = ocr.ocr(img_path, cls=True)
                if result and result[0]:
                    page_text = "\n".join([line[1][0] for line in result[0]])
                    text_parts.append(f"--- 第{page_num + 1}页 (OCR) ---\n{page_text}")

            doc.close()
            return "\n\n".join(text_parts) if text_parts else "OCR未识别到文字"
        except ImportError:
            return "PaddleOCR依赖未安装"
        except Exception as e:
            return f"OCR识别失败: {str(e)}"
