"""Markdown 结构感知分块。

构建一棵轻量级标题树（不依赖外部 AST 库），让每个 chunk
携带其标题面包屑（如 ``第3章 > 3.2 动火作业``）。代码围栏和
表格保持原子性；超长小节退化为递归文本分块。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.services.indexing.plaintext_chunker import recursive_chunk

_HEADING_RE = re.compile(r"^(?P<level>#{1,6})\s+(?P<title>.+?)\s*$", re.MULTILINE)
_FENCE_RE = re.compile(r"^\s*```")


@dataclass(slots=True)
class MarkdownChunk:
    """结构感知的 markdown chunk。"""

    text: str
    heading_path: list[str] = field(default_factory=list)
    section: str = ""  # 一级标题文本
    start: int = 0
    end: int = 0

    @property
    def breadcrumb(self) -> str:
        """将标题路径渲染为单个字符串。"""
        return " > ".join(self.heading_path) if self.heading_path else "(前言)"


def _split_blocks(markdown: str) -> list[tuple[int, str]]:
    """将 markdown 切分为对围栏安全的块（标题处断开小节）。"""
    blocks: list[tuple[int, str]] = []
    lines = markdown.splitlines(keepends=True)
    buffer: list[str] = []
    start_offset = 0
    offset = 0
    in_fence = False
    for line in lines:
        if _FENCE_RE.match(line):
            in_fence = not in_fence
        if line.lstrip().startswith("#") and not in_fence:
            if buffer:
                blocks.append((start_offset, "".join(buffer)))
                buffer = []
            start_offset = offset
        buffer.append(line)
        offset += len(line)
    if buffer:
        blocks.append((start_offset, "".join(buffer)))
    return blocks


def _chunks_from_section(
    section_text: str,
    heading_path: list[str],
    start_offset: int,
    chunk_size: int,
) -> list[MarkdownChunk]:
    """将一个标题小节切分为一个或多个 chunk。"""
    body = section_text.strip("\n")
    if not body.strip():
        return []

    header = f"{' > '.join(heading_path)}\n\n" if heading_path else ""
    results: list[MarkdownChunk] = []

    if len(header) + len(body) <= chunk_size:
        results.append(
            MarkdownChunk(
                text=header + body,
                heading_path=list(heading_path),
                section=heading_path[0] if heading_path else "",
                start=start_offset,
                end=start_offset + len(section_text),
            )
        )
        return results

    # 超长小节：对正文递归分块，并加上面包屑前缀。
    for piece in recursive_chunk(body, chunk_size=max(chunk_size - len(header), 120)):
        results.append(
            MarkdownChunk(
                text=header + piece.text,
                heading_path=list(heading_path),
                section=heading_path[0] if heading_path else "",
                start=start_offset + piece.start,
                end=start_offset + piece.end,
            )
        )
    return results


def markdown_chunk(
    markdown: str,
    chunk_size: int = 512,
    max_heading_level: int = 3,
) -> list[MarkdownChunk]:
    """按标题结构切分 markdown。

    深于 ``max_heading_level`` 的小节保持挂在父 chunk 上，
    避免产生过度碎片化的子块。
    """
    chunks: list[MarkdownChunk] = []
    heading_stack: list[tuple[int, str]] = []
    current_start = 0

    for block_start, block in _split_blocks(markdown):
        match = _HEADING_RE.match(block.strip("\n"))
        if match and int(match.group("level").count("#")) <= max_heading_level:
            # 先输出在此标题之前累积的内容。
            if chunks or block_start > 0:
                section_text = markdown[current_start:block_start]
                path = [title for _, title in heading_stack]
                chunks.extend(
                    _chunks_from_section(section_text, path, current_start, chunk_size)
                )
            level = match.group("level").count("#")
            title = match.group("title").strip()
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, title))
            current_start = block_start
        elif match:
            # 过深标题：文本原样保留在父小节内。
            continue

    # 最后一个小节。
    section_text = markdown[current_start:]
    path = [title for _, title in heading_stack]
    chunks.extend(_chunks_from_section(section_text, path, current_start, chunk_size))

    return [chunk for chunk in chunks if chunk.text.strip()]
