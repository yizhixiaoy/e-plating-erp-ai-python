"""Word文档解析器 - 结构化提取文本+表格+图片引用"""
import logging
from app.parser.base import BaseParser

logger = logging.getLogger(__name__)


class DocxParser(BaseParser):
    name = "Word解析器"
    supported_extensions = ["docx"]

    # 图片扩展名映射
    _IMAGE_EXT_MAP = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/gif": "gif",
        "image/bmp": "bmp",
        "image/tiff": "tiff",
        "image/x-emf": "emf",
        "image/x-wmf": "wmf",
    }

    def parse(self, file_path: str) -> str:
        """解析DOCX文件——提取文本、表格、图片引用

        Returns:
            结构化文本，包含：
            - 段落文本
            - 结构化表格（| 分隔的Markdown格式）
            - 图片位置标记 + alt文本描述
        """
        try:
            from docx import Document
            from docx.opc.constants import RELATIONSHIP_TYPE as RT

            doc = Document(file_path)
            text_parts = []

            # 解析文档体（段落 + 表格 + 图片）
            body_text = self._parse_body(doc)
            if body_text:
                text_parts.append(body_text)

            # 额外：统计文档图片信息
            image_info = self._extract_image_info(doc)
            if image_info:
                text_parts.append(image_info)

            return "\n\n".join(text_parts)
        except ImportError:
            return "Word解析器依赖未安装 (python-docx)"
        except Exception as e:
            logger.warning(f"DOCX解析异常: {e}")
            return f"Word解析失败: {str(e)}"

    def _parse_body(self, doc) -> str:
        """解析文档体：按顺序处理段落、表格、图片

        使用 iter_block_items 确保元素按文档顺序输出
        """
        try:
            from docx.document import Document as DocType
            from docx.oxml.ns import qn
        except ImportError:
            return ""

        text_parts = []
        # 用 iter_inner_content 或直接遍历 body 子元素
        body = doc.element.body

        for child in body:
            tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag

            if tag == 'p':
                # 段落：检测是否只含图片
                para_text = self._parse_paragraph_xml(child)
                if para_text is not None:
                    text_parts.append(para_text)
            elif tag == 'tbl':
                # 表格
                table_text = self._parse_table_xml(child)
                if table_text:
                    text_parts.append(table_text)

        return "\n\n".join(text_parts)

    def _parse_paragraph_xml(self, p_element) -> str | None:
        """解析单个段落的XML，提取文本或图片标记

        Returns:
            段落文本，纯图片段落返回 "[图片: description]"，全空返回 None
        """
        from docx.oxml.ns import qn

        text_parts = []
        image_count = 0
        image_descriptions = []

        for run in p_element.findall(qn('w:r')):
            # 检测图片
            drawings = run.findall(qn('w:drawing'))
            for drawing in drawings:
                # 查找 inline 中的 docPr
                inline = drawing.find(qn('wp:inline'))
                if inline is None:
                    # 也可能在 anchor 中
                    inline = drawing.find(qn('wp:anchor'))

                if inline is not None:
                    doc_pr = inline.find(qn('wp:docPr'))
                    if doc_pr is not None:
                        descr = doc_pr.get('descr', '')
                        name = doc_pr.get('name', '图片')
                        if descr:
                            image_descriptions.append(descr)
                        elif name and name != '图片':
                            image_descriptions.append(name)
                    else:
                        image_descriptions.append('')
                    image_count += 1

            # 提取文本
            t_element = run.find(qn('w:t'))
            if t_element is not None and t_element.text:
                text_parts.append(t_element.text)

        # 构建输出
        if image_count > 0 and not text_parts:
            # 纯图片段落
            desc_text = "; ".join(d for d in image_descriptions if d) or "无描述"
            return f"[图片: {desc_text}]"
        elif image_count > 0:
            # 图文混排段落
            desc_text = "; ".join(d for d in image_descriptions if d) or "无描述"
            text = "".join(text_parts)
            return f"{text}\n[图片: {desc_text}]"

        # 纯文本段落
        text = "".join(text_parts).strip()
        return text if text else None

    def _parse_table_xml(self, tbl_element) -> str | None:
        """解析表格XML元素为 Markdown 表格文本"""
        from docx.oxml.ns import qn

        rows = []
        for tr in tbl_element.findall(qn('w:tr')):
            cells = []
            for tc in tr.findall(qn('w:tc')):
                cell_text_parts = []
                for p in tc.findall(qn('w:p')):
                    para_text = self._parse_paragraph_xml(p)
                    if para_text:
                        cell_text_parts.append(para_text)
                cells.append(" ".join(cell_text_parts).replace("\n", " "))
            rows.append(cells)

        if not rows:
            return None

        # 跳过全空行
        cleaned = [row for row in rows if any(c for c in row)]
        if not cleaned:
            return None

        # Markdown 表格格式
        lines = ["【表格】"]
        for i, row in enumerate(cleaned):
            lines.append("| " + " | ".join(row) + " |")
            if i == 0 and len(cleaned) > 1:
                lines.append("| " + " | ".join(["---"] * len(row)) + " |")

        return "\n".join(lines)

    def _extract_image_info(self, doc) -> str:
        """提取文档中所有图片的汇总信息（数量、名称、类型）

        Returns:
            图片汇总文本，无图片时返回空字符串
        """
        try:
            from docx.opc.constants import RELATIONSHIP_TYPE as RT
        except ImportError:
            return ""

        images = []
        for rel in doc.part.rels.values():
            if rel.reltype == RT.IMAGE:
                rel_id = rel.rId
                # 获取图片名称和类型
                try:
                    image_part = rel.target_part
                    content_type = image_part.content_type
                    ext = self._IMAGE_EXT_MAP.get(content_type, "img")
                    image_name = getattr(image_part, 'partname', '')
                    if image_name:
                        image_name = str(image_name).split('/')[-1]
                    else:
                        image_name = f"image_{rel_id}.{ext}"
                    images.append({"name": image_name, "type": content_type})
                except Exception:
                    images.append({"name": f"image_{rel_id}", "type": "unknown"})

        if not images:
            return ""

        total = len(images)
        types = set(img["type"] for img in images)
        type_summary = ", ".join(sorted(types))
        return f"[文档包含 {total} 张图片，类型: {type_summary}]"

    def _parse_table(self, table) -> str:
        """解析Word表格为文本（保留用于 python-docx Table 对象兼容）"""
        rows = []
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            rows.append(" | ".join(cells))
        return "\n".join(rows)
