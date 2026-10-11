"""PDF 页面图像化 + 页面 hash，用于增量多模态索引。

通过 PyMuPDF（fitz）将每个 PDF 页面渲染为 PIL 图像，对页面的
文本 + 图像字节计算 SHA-256 内容 hash 以支持幂等重同步，并
提取文本描述（无需 OCR：直接使用页面文本层），在 ColQwen2
不可用时供降级的多模态编码器使用。

图像文件存放在 ``<data_dir>/pages/<doc_id>/<page>.png``，
以便 ColQwen2 编码器可用时直接取用。
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_DATA_DIR = "data/pages"


@dataclass(slots=True)
class PageImage:
    """一张渲染后的 PDF 页面及其元数据。"""

    doc_id: int
    page_num: int  # 从 0 开始
    image_path: str
    page_hash: str
    text_description: str
    width: int
    height: int


def _render_page_to_image(page: Any, dpi: int = 150) -> tuple[bytes, int, int]:
    """将 PyMuPDF 页面渲染为 PNG 字节。返回 (png_bytes, width, height)。"""
    mat = page.get_pixmap(dpi=dpi)
    png_bytes = mat.tobytes("png")
    return png_bytes, mat.width, mat.height


def _extract_text(page: Any) -> str:
    """提取页面的文本层（无需 OCR 的描述来源）。"""
    text = page.get_text("text")
    return text.strip()


def _compute_page_hash(text: str, image_bytes: bytes) -> str:
    """对文本 + 图像内容计算 SHA-256，用于幂等增量更新。"""
    h = hashlib.sha256()
    h.update(text.encode("utf-8"))
    h.update(image_bytes)
    return h.hexdigest()[:32]  # 截断为 128-bit，便于存储


def pdf_to_page_images(
    pdf_path: str,
    doc_id: int,
    data_dir: str = _DEFAULT_DATA_DIR,
    dpi: int = 150,
    max_pages: int = 0,
) -> list[PageImage]:
    """将 PDF 的所有页面渲染为图像并计算页面 hash。

    Args:
        pdf_path: PDF 文件的文件系统路径。
        doc_id: 用于目录布局的内部文档 ID。
        data_dir: 页面图像的根目录。
        dpi: 渲染分辨率（150 对 ColQwen2 是较好的平衡点）。
        max_pages: 0 表示全部页面；N 表示仅前 N 页。
    """
    import fitz  # PyMuPDF —— 惰性导入，避免无 PDF 的测试环境报错

    pages: list[PageImage] = []
    doc = fitz.open(pdf_path)
    try:
        count = len(doc) if max_pages <= 0 else min(max_pages, len(doc))
        out_dir = Path(data_dir) / str(doc_id)
        out_dir.mkdir(parents=True, exist_ok=True)
        for i in range(count):
            page = doc[i]
            text = _extract_text(page)
            png_bytes, w, h = _render_page_to_image(page, dpi=dpi)
            page_hash = _compute_page_hash(text, png_bytes)
            img_path = out_dir / f"page_{i:04d}.png"
            img_path.write_bytes(png_bytes)
            description = text[:512] if text else f"PDF page {i + 1} (no text layer)"
            pages.append(
                PageImage(
                    doc_id=doc_id,
                    page_num=i,
                    image_path=str(img_path),
                    page_hash=page_hash,
                    text_description=description,
                    width=w,
                    height=h,
                )
            )
        logger.info("Rendered %d pages from %s (doc_id=%d)", count, pdf_path, doc_id)
    finally:
        doc.close()
    return pages


def page_hash_from_text(text: str) -> str:
    """仅根据页面文本计算内容 hash（供测试 / 纯文本页面使用）。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]


def image_bytes_to_pil(png_bytes: bytes):
    """将 PNG 字节转换为 PIL Image（后续供 ColQwen2 编码器使用）。"""
    from PIL import Image

    return Image.open(io.BytesIO(png_bytes))
