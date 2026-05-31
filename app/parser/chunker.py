"""混合切分引擎 - 语义感知的文档切分"""
from app.config import settings


class Chunker:
    """混合切分引擎

    策略：
    1. 一级切分：按文档结构（标题/段落/表格边界）
    2. 二级切分：对超长段落滑窗切分（chunk_size + overlap）
    """

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None
    ):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    def split(self, text: str) -> list[dict]:
        """
        切分文档

        Args:
            text: 待切分的文档文本

        Returns:
            [{"index": 0, "content": "...", "metadata": {"section_title": "..."}}, ...]
        """
        paragraphs = self._split_by_structure(text)
        chunks = self._split_long_paragraphs(paragraphs)

        # 清理：合并过短片段、去重
        chunks = self._clean_chunks(chunks)

        # 添加序号
        result = []
        for i, chunk in enumerate(chunks):
            result.append({
                "index": i,
                "content": chunk["text"],
                "metadata": chunk.get("metadata", {})
            })

        return result

    def _split_by_structure(self, text: str) -> list[dict]:
        """一级切分：按文档结构分割"""
        paragraphs = text.split("\n\n")
        result = []
        current_section = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # 检测标题行
            if self._is_heading(para):
                current_section = para

            result.append({
                "text": para,
                "metadata": {"section_title": current_section}
            })

        return result

    def _split_long_paragraphs(self, paragraphs: list[dict]) -> list[dict]:
        """二级切分：对超长段落滑窗切分"""
        result = []

        for para in paragraphs:
            text = para["text"]
            if len(text) <= self.chunk_size:
                result.append(para)
            else:
                # 滑窗切分
                start = 0
                while start < len(text):
                    end = start + self.chunk_size
                    chunk_text = text[start:end]
                    result.append({
                        "text": chunk_text,
                        "metadata": para.get("metadata", {})
                    })
                    start += self.chunk_size - self.chunk_overlap

        return result

    def _clean_chunks(self, chunks: list[dict]) -> list[dict]:
        """清理：去重、合并过短片段"""
        cleaned = []
        for chunk in chunks:
            text = chunk["text"].strip()
            if len(text) < 10:
                continue
            if cleaned and len(text) < 50:
                # 短片段合并到前一个
                cleaned[-1]["text"] += "\n" + text
            else:
                cleaned.append({"text": text, "metadata": chunk.get("metadata", {})})

        return cleaned

    def _is_heading(self, text: str) -> bool:
        """判断是否为标题行"""
        heading_markers = ["第", "一、", "二、", "1.", "2.", "(1)", "(2)", "第一章", "第二章", "§"]
        for marker in heading_markers:
            if text.startswith(marker):
                return True
        # 短行且以粗体标记结尾（模拟）
        if len(text) <= 50 and not text.endswith("。"):
            return True
        return False
