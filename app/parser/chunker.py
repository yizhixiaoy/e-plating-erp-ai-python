"""混合切分引擎 - 语义感知的文档切分（含表格块保护）"""
import re
from app.config import settings


class Chunker:
    """混合切分引擎

    策略：
    1. 一级切分：按文档结构（标题/段落/表格边界）— 基于正则的标题检测 + 表格块识别
    2. 二级切分：对超长段落滑窗切分（chunk_size + overlap），表格块保持完整不分切
    """

    # 标题检测正则模式（按优先级排序）
    _HEADING_PATTERNS = [
        # Markdown ATX标题: # ## ### ...
        re.compile(r"^#{1,6}\s+"),
        # 中文数字序号：第一章/第二章... 第一/第二...
        re.compile(r"^第[一二三四五六七八九十百千万\d]+[章节条款项]"),
        # 中文序号+顿号：一、二、三、... 十二、
        re.compile(r"^[一二三四五六七八九十百千]+[、，]"),
        # 阿拉伯数字序号+点：1. 2. 3. / 1.1 1.2
        re.compile(r"^\d+(\.\d+)*[\.、，)\s]"),
        # 括号序号：(1) (2) / (一) (二) / 1) 2)
        re.compile(r"^[（(]\s*(\d+|[一二三四五六七八九十百千]+)\s*[）)]"),
        # 罗马数字序号: I. II. III.
        re.compile(r"^[IVX]+[\.、)]"),
        # 附录/附件标记: 附录A / 附件1 / §
        re.compile(r"^(附录|附件|§|Chapter|Section|Part)\s*[\w\d]*"),
    ]

    # 表格行检测：匹配 Markdown 表格行或 `|` 分隔的数据行
    _TABLE_ROW_PATTERN = re.compile(r"^\|.*\|$|^[^|]+\|[^|]+")

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None
    ):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        self.clean_min_length = settings.CHUNK_CLEAN_MIN_LENGTH
        self.clean_merge_length = settings.CHUNK_CLEAN_MERGE_LENGTH

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
        """一级切分：按文档结构分割（标题/段落/表格块）

        表格块识别策略：
        - 检测连续的 `|` 分隔行（Markdown表格 / 解析器输出的pipe分隔数据）
        - 将连续表格行合并为单一表格块，避免表格被切碎
        """
        raw_paragraphs = text.split("\n\n")
        result = []
        current_section = ""

        # 先识别表格块边界，将段落分组为 [文本段, 表格块, 文本段, ...]
        groups = self._group_paragraphs(raw_paragraphs)

        for group in groups:
            group_text = group["text"]
            is_table = group.get("is_table", False)

            # 检测标题行（仅在文本块中检测，表格块跳过）
            if not is_table and self._is_heading(group_text):
                current_section = group_text

            result.append({
                "text": group_text,
                "metadata": {
                    "section_title": current_section,
                    "block_type": "table" if is_table else "text"
                }
            })

        return result

    def _group_paragraphs(self, paragraphs: list[str]) -> list[dict]:
        """将段落列表按类型分组：[文本块, 表格块, 文本块, ...]

        表格块检测：连续2行以上含 `|` 分隔符的行 → 合并为单一块
        """
        groups = []
        current_group = []
        current_is_table = False

        def _flush():
            nonlocal current_group, current_is_table
            if current_group:
                groups.append({
                    "text": "\n".join(current_group),
                    "is_table": current_is_table
                })
            current_group = []
            current_is_table = False

        for para in paragraphs:
            para = para.strip()
            if not para:
                _flush()
                continue

            is_table_row = self._is_table_row(para)
            # 只有连续2行以上表格行才算表格块（单行 `|` 可能是分隔线）
            if current_group and current_is_table and is_table_row:
                # 继续表格块
                current_group.append(para)
            elif current_group and current_is_table and not is_table_row:
                # 表格块结束
                _flush()
                current_group.append(para)
                current_is_table = False
            elif current_group and not current_is_table and is_table_row:
                # 可能开始新表格块，先看下一行
                current_group.append(para)
                # 不立即切换，等确认连续表格行
            elif current_group and not current_is_table and not is_table_row:
                current_group.append(para)
            else:
                # 第一个元素
                current_group.append(para)

        _flush()

        # 二次处理：检查分组中是否有孤立的表格行（只有1行的假表格块）
        refined = []
        for group in groups:
            if group["is_table"]:
                lines = group["text"].split("\n")
                table_line_count = sum(1 for l in lines if self._is_table_row(l))
                if table_line_count < 2:
                    # 不足2行表格行 → 降级为普通文本块
                    group["is_table"] = False
            refined.append(group)

        return refined

    def _is_table_row(self, text: str) -> bool:
        """判断是否为表格数据行（非分隔线）

        表格数据行特征：
        - 包含多个 `|` 分隔符
        - 内容包含非空白字符（排除纯分隔线如 `| --- | --- |`）
        """
        if not text:
            return False
        # 匹配pipe分隔的行
        if not self._TABLE_ROW_PATTERN.search(text):
            return False
        # 排除纯分隔线（只含 |, -, :, 空格）
        stripped = text.replace("|", "").replace("-", "").replace(":", "").replace(" ", "")
        if not stripped:
            return False
        return True

    def _split_long_paragraphs(self, paragraphs: list[dict]) -> list[dict]:
        """二级切分：对超长段落滑窗切分，表格块保持完整不分切"""
        result = []

        for para in paragraphs:
            text = para["text"]
            metadata = para.get("metadata", {})
            is_table = metadata.get("block_type") == "table"

            # 表格块：保持完整不切分（表格结构比 chunk_size 约束更重要）
            if is_table:
                result.append(para)
            elif len(text) <= self.chunk_size:
                result.append(para)
            else:
                # 滑窗切分（仅文本块）
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
        """清理：去重、合并过短片段（阈值从config读取）"""
        cleaned = []
        for chunk in chunks:
            text = chunk["text"].strip()
            if len(text) < self.clean_min_length:
                continue
            if cleaned and len(text) < self.clean_merge_length:
                # 短片段合并到前一个
                cleaned[-1]["text"] += "\n" + text
            else:
                cleaned.append({"text": text, "metadata": chunk.get("metadata", {})})

        return cleaned

    def _is_heading(self, text: str) -> bool:
        """基于正则模式的标题检测（支持中英文混合文档结构）

        检测策略（按优先级）：
        1. 正则匹配明确标题模式（Markdown标题、序号、附录标记等）
        2. 启发式规则：短文本行 + 不以句号结尾 → 候选标题
        """
        text_stripped = text.strip()
        if not text_stripped:
            return False

        # 1. 正则模式匹配
        for pattern in self._HEADING_PATTERNS:
            if pattern.match(text_stripped):
                return True

        # 2. 启发式规则：短行且不以句末标点结尾
        if len(text_stripped) <= 50 and not text_stripped.endswith(("。", "；", "！", "？", "…")):
            return True
        return False
