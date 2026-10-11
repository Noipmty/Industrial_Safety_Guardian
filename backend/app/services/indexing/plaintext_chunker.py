"""带重叠的递归纯文本分块。

按当前可用的最强分隔符切分（段落 -> 行 -> 句子 -> 空格 ->
硬切分），保证 chunk 不超过 ``chunk_size`` 个字符。
"""

from __future__ import annotations

from dataclasses import dataclass

SEPARATORS = ["\n\n", "\n", "。", "；", ". ", " ", ""]


@dataclass(slots=True)
class Chunk:
    """一个文本 chunk 及其字节偏移 span。"""

    text: str
    start: int
    end: int


def _hard_split(text: str, size: int) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)]


def _split_by(text: str, separator: str, size: int) -> list[str]:
    """用 ``separator`` 将 ``text`` 切分为不超过 ``size`` 的片段。"""
    if separator == "":
        return _hard_split(text, size)
    parts = text.split(separator)
    # 重新拼回分隔符，避免内容丢失。
    parts = [part + separator for part in parts[:-1]] + [parts[-1]] if len(parts) > 1 else parts

    merged: list[str] = []
    buffer = ""
    for part in parts:
        if len(part) > size:
            if buffer:
                merged.append(buffer)
                buffer = ""
            merged.extend(_split_deeper(part, size, SEPARATORS[SEPARATORS.index(separator) + 1:]))
            continue
        if len(buffer) + len(part) > size and buffer:
            merged.append(buffer)
            buffer = part
        else:
            buffer += part
    if buffer:
        merged.append(buffer)
    return [piece for piece in merged if piece.strip()]


def _split_deeper(text: str, size: int, remaining: list[str]) -> list[str]:
    if not remaining:
        return _hard_split(text, size)
    return _split_by(text, remaining[0], size)


def recursive_chunk(
    text: str,
    chunk_size: int = 512,
    overlap: int = 64,
) -> list[Chunk]:
    """递归分块 ``text``，相邻 chunk 保留 ``overlap`` 个字符的上下文。

    重叠的实现方式是把上一个 chunk 的尾部拼到下一个 chunk
    开头（当上一尾部会重复内容时进行去重）。
    """
    if not text.strip():
        return []
    pieces = [p for p in _split_by(text.strip(), SEPARATORS[0], chunk_size) if p.strip()]
    chunks: list[Chunk] = []
    cursor = 0
    for piece in pieces:
        start = text.find(piece[:32], cursor)
        start = start if start >= 0 else cursor
        if chunks and overlap > 0:
            tail = chunks[-1].text[-overlap:]
            piece = tail + piece
        chunks.append(Chunk(text=piece, start=start, end=start + len(piece)))
        cursor = max(start, start + len(piece) - overlap)
    return chunks
