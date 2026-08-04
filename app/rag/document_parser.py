"""文档解析器 — 支持 PDF(DOCX)/Word/Excel/TXT/Markdown

增强功能:
- PDF: 表格提取(PyMuPDF内置) + 标题层级检测(字体大小) + OCR扫描件(可选PaddleOCR)
- DOCX: 段落样式检测(H1/H2/H3) + 表格提取
- EXCEL: 多Sheet + 表头检测
- TXT/MD: 章节层级(##/###) + Markdown结构
"""

import logging
from pathlib import Path
from typing import Any, Optional
import re

logger = logging.getLogger(__name__)

FONT_H1_THRESHOLD = 18  # H1 > 18pt
FONT_H2_THRESHOLD = 15  # H2 > 15pt
FONT_H3_THRESHOLD = 13  # H3 > 13pt


def _clean_text(text: str) -> str:
    """清洗文本：移除多余空白、统一标点"""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


class DocumentParser:
    """多格式文档解析器"""

    # ================================================================
    # 公共入口
    # ================================================================

    @staticmethod
    def parse(filepath: str) -> list[dict[str, Any]]:
        """自动根据扩展名选择解析器"""
        ext = Path(filepath).suffix.lower()
        parsers = {
            ".pdf": DocumentParser.parse_pdf,
            ".docx": DocumentParser.parse_docx,
            ".xlsx": DocumentParser.parse_excel,
            ".xls": DocumentParser.parse_excel,
            ".txt": DocumentParser.parse_text,
            ".md": DocumentParser.parse_text,
        }
        parser = parsers.get(ext)
        if not parser:
            raise ValueError(f"不支持的文档格式: {ext}")
        return parser(filepath)

    # ================================================================
    # PDF 解析
    # ================================================================

    @staticmethod
    def parse_pdf(filepath: str) -> list[dict[str, Any]]:
        """PDF 解析：文本 + 表格 + 标题层级 + OCR 降级"""
        chunks: list[dict[str, Any]] = []

        try:
            import fitz
            doc = fitz.open(filepath)

            for page_num, page in enumerate(doc):
                page_num_1 = page_num + 1

                blocks = page.get_text("dict")["blocks"]

                for block in blocks:
                    if block["type"] == 0:
                        text_block = DocumentParser._parse_text_block(
                            block, filepath, page_num_1
                        )
                        chunks.extend(text_block)

                    elif block["type"] == 1:
                        img_chunk = DocumentParser._parse_image_block(
                            block, filepath, page_num_1
                        )
                        if img_chunk:
                            chunks.append(img_chunk)

                tables = page.find_tables()
                for table in tables:
                    table_chunk = DocumentParser._parse_table_block(
                        table, filepath, page_num_1
                    )
                    if table_chunk:
                        chunks.append(table_chunk)

            doc.close()

        except ImportError:
            logger.warning("PyMuPDF 未安装，使用 OCR 降级方案")
            chunks = DocumentParser._parse_pdf_ocr(filepath)

        if not chunks:
            chunks = DocumentParser._parse_pdf_fallback(filepath)

        return DocumentParser._merge_short_chunks(chunks)

    @staticmethod
    def _parse_text_block(
        block: dict, filepath: str, page_num: int
    ) -> list[dict[str, Any]]:
        """解析 PDF 文本块，检测标题层级"""
        chunks: list[dict[str, Any]] = []

        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "").strip()
                if len(text) < 5:
                    continue

                font_size = span.get("size", 12)
                font_name = span.get("font", "")
                is_bold = "Bold" in font_name or "bold" in font_name

                heading_level = _detect_heading_level(font_size, is_bold, text)

                chunks.append({
                    "text": _clean_text(text),
                    "source": filepath,
                    "page": page_num,
                    "type": "pdf",
                    "heading_level": heading_level,
                    "font_size": round(font_size, 1),
                    "is_bold": is_bold,
                })

        return chunks

    @staticmethod
    def _parse_table_block(
        table, filepath: str, page_num: int
    ) -> Optional[dict[str, Any]]:
        """解析 PDF 表格为结构化文本"""
        try:
            cells = table.extract()
            if not cells or len(cells) < 2:
                return None

            header = cells[0]
            rows_text: list[str] = []
            for row in cells[1:]:
                row_parts = [
                    f"{header[i] if i < len(header) else f'col{i}'}: {cell}"
                    for i, cell in enumerate(row)
                    if cell and str(cell).strip()
                ]
                if row_parts:
                    rows_text.append(" | ".join(row_parts))

            if not rows_text:
                return None

            return {
                "text": "\n".join(rows_text),
                "source": filepath,
                "page": page_num,
                "type": "pdf_table",
                "row_count": len(rows_text),
            }
        except Exception:
            return None

    @staticmethod
    def _parse_image_block(
        block: dict, filepath: str, page_num: int
    ) -> Optional[dict[str, Any]]:
        """提取 PDF 图片块（标记为待 OCR 处理）"""
        image_bytes = block.get("image")
        if not image_bytes:
            return None
        return {
            "text": "[图片]",
            "source": filepath,
            "page": page_num,
            "type": "pdf_image",
            "image_bytes": image_bytes,
            "needs_ocr": True,
        }

    @staticmethod
    def _parse_pdf_ocr(filepath: str) -> list[dict[str, Any]]:
        """OCR 扫描件 PDF 解析

        支持三引擎自动降级:
          1. PaddleOCR (百度,中文 >95%, 需 GPU 加速) — pip install paddlepaddle paddleocr
          2. EasyOCR (开源,中文 >90%, CPU) — pip install easyocr
          3. pytesseract (Google,中文 >80%, 需装 tesseract-ocr-chi-sim) — apt install tesseract-ocr tesseract-ocr-chi-sim && pip install pytesseract Pillow

        任一引擎可用即启用 OCR，均不可用时返回空列表(无报错)。
        """
        ocr = DocumentParser._load_ocr_engine()
        if ocr is None:
            return []

        try:
            import fitz
            doc = fitz.open(filepath)
            chunks: list[dict[str, Any]] = []

            for page_num, page in enumerate(doc):
                pix = page.get_pixmap(dpi=200)
                img_path = f"/tmp/yuneng_ocr_page_{page_num}.png"
                pix.save(img_path)

                text = DocumentParser._run_ocr(ocr, img_path)
                if text and text.strip():
                    chunks.append({
                        "text": text.strip(),
                        "source": filepath,
                        "page": page_num + 1,
                        "type": "pdf_ocr",
                    })

                Path(img_path).unlink(missing_ok=True)

            doc.close()
            logger.info(f"OCR 解析完成: {filepath} → {len(chunks)} 页")
            return chunks

        except ImportError:
            logger.info("PyMuPDF 未安装，跳过 OCR")
            return []
        except Exception as e:
            logger.warning(f"OCR 解析异常({filepath}): {e}")
            return []

    @staticmethod
    def _load_ocr_engine():
        """按优先级加载 OCR 引擎"""
        # 1. PaddleOCR
        try:
            from paddleocr import PaddleOCR
            ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
            logger.info("OCR 引擎: PaddleOCR")
            return ("paddleocr", ocr)
        except ImportError:
            pass

        # 2. EasyOCR
        try:
            import easyocr
            reader = easyocr.Reader(["ch_sim", "en"], gpu=False)
            logger.info("OCR 引擎: EasyOCR")
            return ("easyocr", reader)
        except ImportError:
            pass

        # 3. pytesseract
        try:
            import pytesseract
            from PIL import Image
            logger.info("OCR 引擎: pytesseract")
            return ("tesseract", pytesseract)
        except ImportError:
            pass

        logger.info(
            "OCR 引擎未安装（可选），跳过扫描件识别。"
            "安装其一: pip install paddleocr / pip install easyocr / "
            "apt install tesseract-ocr-chi-sim && pip install pytesseract"
        )
        return None

    @staticmethod
    def _run_ocr(engine, img_path: str) -> str:
        """统一 OCR 调用接口"""
        engine_type, ocr = engine

        if engine_type == "paddleocr":
            result = ocr.ocr(img_path, cls=True)
            if result and result[0]:
                return "\n".join(
                    line[1][0] for line in result[0] if line[1][1] > 0.5
                )
            return ""

        elif engine_type == "easyocr":
            result = ocr.readtext(img_path)
            return "\n".join(
                text for _, text, conf in result if conf > 0.5
            )

        elif engine_type == "tesseract":
            from PIL import Image
            img = Image.open(img_path)
            return ocr.image_to_string(img, lang="chi_sim+eng")

        return ""

    @staticmethod
    def _parse_pdf_fallback(filepath: str) -> list[dict[str, Any]]:
        """PyMuPDF 文本提取降级（兼容旧版）"""
        try:
            import fitz
            doc = fitz.open(filepath)
            chunks = []
            for page_num, page in enumerate(doc):
                text = page.get_text()
                paragraphs = text.split("\n\n")
                for para in paragraphs:
                    cleaned = _clean_text(para)
                    if len(cleaned) > 30:
                        chunks.append({
                            "text": cleaned,
                            "source": filepath,
                            "page": page_num + 1,
                            "type": "pdf",
                        })
            return chunks
        except ImportError:
            return []

    # ================================================================
    # DOCX 解析
    # ================================================================

    @staticmethod
    def parse_docx(filepath: str) -> list[dict[str, Any]]:
        """DOCX 解析：段落样式 + 表格 + 标题层级"""
        from docx import Document
        from docx.enum.style import WD_STYLE_TYPE

        doc = Document(filepath)
        chunks: list[dict[str, Any]] = []

        for element in doc.element.body:
            tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag

            if tag == "p":
                chunk = DocumentParser._parse_docx_paragraph(element, doc, filepath)
                if chunk:
                    chunks.append(chunk)

            elif tag == "tbl":
                table_chunk = DocumentParser._parse_docx_table(element, filepath)
                if table_chunk:
                    chunks.append(table_chunk)

        return DocumentParser._merge_short_chunks(chunks)

    @staticmethod
    def _parse_docx_paragraph(
        element, doc, filepath: str
    ) -> Optional[dict[str, Any]]:
        """解析 DOCX 段落，检测标题层级"""
        from docx.text.paragraph import Paragraph

        para = Paragraph(element, doc)
        text = para.text.strip()
        if len(text) < 5:
            return None

        style_name = para.style.name if para.style else ""
        heading_level = _detect_heading_from_style(style_name, text)

        return {
            "text": text,
            "source": filepath,
            "type": "docx",
            "heading_level": heading_level,
            "style_name": style_name,
        }

    @staticmethod
    def _parse_docx_table(element, filepath: str) -> Optional[dict[str, Any]]:
        """解析 DOCX 表格"""
        rows = element.findall(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr")
        if len(rows) < 2:
            return None

        all_rows: list[list[str]] = []
        for row in rows:
            cells = row.findall(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc")
            cell_texts = []
            for cell in cells:
                paragraphs = cell.findall(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")
                cell_text = " ".join(p.text or "" for p in paragraphs).strip()
                cell_texts.append(cell_text)
            if any(cell_texts):
                all_rows.append(cell_texts)

        if len(all_rows) < 2:
            return None

        header = all_rows[0]
        lines = []
        for row in all_rows[1:]:
            parts = [
                f"{header[i] if i < len(header) else f'col{i}'}: {cell}"
                for i, cell in enumerate(row)
                if cell
            ]
            if parts:
                lines.append(" | ".join(parts))

        return {
            "text": "\n".join(lines),
            "source": filepath,
            "type": "docx_table",
            "row_count": len(lines),
        }

    # ================================================================
    # EXCEL 解析
    # ================================================================

    @staticmethod
    def parse_excel(filepath: str) -> list[dict[str, Any]]:
        """EXCEL 解析：多 Sheet + 表头检测"""
        import pandas as pd

        xl = pd.ExcelFile(filepath)
        chunks: list[dict[str, Any]] = []

        for sheet_name in xl.sheet_names:
            df = pd.read_excel(filepath, sheet_name=sheet_name)

            if df.empty:
                continue

            columns = [str(c) for c in df.columns]

            for _, row in df.iterrows():
                parts = [
                    f"{col}: {val}"
                    for col, val in zip(columns, row)
                    if pd.notna(val) and str(val).strip()
                ]
                if parts:
                    chunks.append({
                        "text": " | ".join(parts),
                        "source": filepath,
                        "type": "excel",
                        "sheet": sheet_name,
                    })

        return chunks

    # ================================================================
    # TXT / Markdown 解析
    # ================================================================

    @staticmethod
    def parse_text(filepath: str) -> list[dict[str, Any]]:
        """TXT / Markdown 解析：章节层级 + 段落分割"""
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        ext = Path(filepath).suffix.lower()
        is_markdown = ext == ".md"

        if is_markdown:
            return DocumentParser._parse_markdown(content, filepath)
        else:
            return DocumentParser._parse_plain_text(content, filepath)

    @staticmethod
    def _parse_markdown(content: str, filepath: str) -> list[dict[str, Any]]:
        """Markdown 解析：检测 #/##/### 标题层级"""
        chunks: list[dict[str, Any]] = []
        lines = content.split("\n")
        current_heading: Optional[str] = None
        current_level: int = 0
        buffer: list[str] = []

        def flush():
            nonlocal buffer
            if buffer:
                text = "\n".join(buffer).strip()
                if len(text) > 20:
                    chunks.append({
                        "text": text,
                        "source": filepath,
                        "type": "markdown",
                        "heading": current_heading,
                        "heading_level": current_level,
                    })
                buffer = []

        for line in lines:
            match = re.match(r"^(#{1,6})\s+(.+)", line)
            if match:
                flush()
                current_level = len(match.group(1))
                current_heading = match.group(2).strip()
            else:
                stripped = line.strip()
                if stripped:
                    buffer.append(stripped)

        flush()
        return chunks

    @staticmethod
    def _parse_plain_text(content: str, filepath: str) -> list[dict[str, Any]]:
        """纯文本解析：段落分割"""
        chunks = []
        paragraphs = content.split("\n\n")
        for para in paragraphs:
            cleaned = _clean_text(para)
            if len(cleaned) > 30:
                chunks.append({
                    "text": cleaned,
                    "source": filepath,
                    "type": "text",
                })
        return chunks

    # ================================================================
    # 公共工具
    # ================================================================

    @staticmethod
    def _merge_short_chunks(
        chunks: list[dict[str, Any]], min_len: int = 100
    ) -> list[dict[str, Any]]:
        """合并过短的 chunk（保留元数据）"""
        if len(chunks) <= 1:
            return chunks

        merged: list[dict[str, Any]] = []
        buffer: list[dict[str, Any]] = []

        for chunk in chunks:
            buffer.append(chunk)
            total_len = sum(len(c.get("text", "")) for c in buffer)
            if total_len >= min_len:
                combined_text = " ".join(c["text"] for c in buffer)
                merged.append({
                    "text": combined_text,
                    "source": buffer[0]["source"],
                    "type": buffer[0]["type"],
                    "page": buffer[0].get("page"),
                    "heading_level": buffer[0].get("heading_level"),
                })
                buffer = []

        if buffer:
            combined_text = " ".join(c["text"] for c in buffer)
            merged.append({
                "text": combined_text,
                "source": buffer[0]["source"],
                "type": buffer[0]["type"],
            })

        return merged


def _detect_heading_level(font_size: float, is_bold: bool, text: str) -> int:
    """根据字体大小和格式检测标题层级

    H1 > 18pt | H2 > 15pt | H3 > 13pt | 正文 ≤ 13pt
    加粗且短文本（< 30 字）提升一级
    """
    short = len(text) < 30

    if font_size >= FONT_H1_THRESHOLD and is_bold and short:
        return 1
    if font_size >= FONT_H2_THRESHOLD and (is_bold or short):
        return 2
    if font_size >= FONT_H3_THRESHOLD and is_bold:
        return 3
    return 0


def _detect_heading_from_style(style_name: str, text: str) -> int:
    """根据 DOCX 段落样式名检测标题层级"""
    style_lower = style_name.lower()
    match = re.search(r"heading\s*(\d)", style_lower)
    if match:
        return int(match.group(1))
    for level, keyword in [(1, "title"), (2, "subtitle"), (3, "heading")]:
        if keyword in style_lower and len(text) < 60:
            return level
    return 0


def chunk_text(text: str, max_size: int = 800, overlap: int = 100) -> list[str]:
    """将长文本按大小分块（用于无法结构化的纯文本）"""
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_size, len(text))
        chunks.append(text[start:end])
        start += max_size - overlap
        if start >= len(text):
            break
    return chunks
