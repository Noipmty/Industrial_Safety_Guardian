"""P1 分块器单元测试（无外部服务依赖）。"""

from __future__ import annotations

from app.services.indexing.markdown_chunker import markdown_chunk
from app.services.indexing.plaintext_chunker import recursive_chunk


class TestRecursiveChunker:
    def test_respects_max_size(self):
        text = "。" * 1000  # 长的单段落内容
        chunks = recursive_chunk(text, chunk_size=200, overlap=0)
        assert chunks
        assert all(len(c.text) <= 200 for c in chunks)

    def test_overlap_present(self):
        text = "\n".join(f"line {i} " + "x" * 40 for i in range(20))
        chunks = recursive_chunk(text, chunk_size=150, overlap=30)
        assert len(chunks) > 1
        assert chunks[1].text[:30] == chunks[0].text[-30:]

    def test_no_content_loss(self):
        text = "第一段内容。\n\n第二段内容。\n\n第三段内容。"
        chunks = recursive_chunk(text, chunk_size=500, overlap=0)
        joined = "".join(c.text for c in chunks).replace("\n", "")
        assert "第一段内容" in joined and "第三段内容" in joined

    def test_empty_input(self):
        assert recursive_chunk("   \n  ") == []


class TestMarkdownChunker:
    SAMPLE = """# 安全总则
开头介绍文字。

## 3.2 动火作业
动火作业实行分级管理。

```python
# 这段代码块很长很长很长很长很长很长很长很长
print("hello")
```

### 3.2.1 审批流程
需要一级动火证。

## 第4章 有限空间
先通风、再检测、后作业。
"""

    def test_breadcrumb_paths(self):
        chunks = markdown_chunk(self.SAMPLE, chunk_size=200)
        paths = [c.breadcrumb for c in chunks]
        assert any("3.2 动火作业" in p for p in paths)
        assert any("3.2 动火作业 > 3.2.1 审批流程" in p for p in paths)

    def test_code_fence_atomic(self):
        chunks = markdown_chunk(self.SAMPLE, chunk_size=200)
        fence_chunks = [c.text for c in chunks if "```" in c.text]
        assert fence_chunks
        for text in fence_chunks:
            assert text.count("```") % 2 == 0  # 代码围栏保持成对

    def test_each_chunk_prefixed_with_breadcrumb(self):
        chunks = markdown_chunk(self.SAMPLE, chunk_size=120)
        for chunk in chunks:
            assert chunk.heading_path or "(前言)" in chunk.breadcrumb
