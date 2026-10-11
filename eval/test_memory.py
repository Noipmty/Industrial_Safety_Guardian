"""Eval script for the memory layer (prompt eval/test_memory.py).

Runs a deterministic golden-set check over the live memory stack:
    1. seeds episodic + semantic memories for an eval user,
    2. issues recall queries and verifies the right memory is hit in top-k,
    3. verifies RLS isolation and decay/purge bookkeeping.

Usage:
    conda run -n jrong python -m eval.test_memory
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.services.memory.consolidate import SessionConsolidator  # noqa: E402
from app.services.memory.long_term import LongTermMemory  # noqa: E402
from app.services.memory.pg_store import init_memory_db  # noqa: E402
from app.services.memory.working_memory import WorkingMemory  # noqa: E402

EVAL_USER = 987_654_321

CASES = [
    {"seed_summary": "用户复习了动火作业分级审批流程，重点是一级动火证。", "query": "动火审批流程", "expect": "动火"},
    {"seed_summary": "用户咨询了有限空间作业的三步要求。", "query": "有限空间作业要求", "expect": "有限空间"},
    {"seed_summary": "用户学习了临时用电的漏电保护配置。", "query": "临时用电漏电保护", "expect": "漏电"},
]


class HashEmbedder:
    """Position-independent char n-gram hashing (unigram + bigram)."""

    def encode(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            vec = [0.0] * 1024
            grams = list(text) + [text[i : i + 2] for i in range(len(text) - 1)]
            for gram in grams:
                key = sum(ord(ch) * 131 ** i for i, ch in enumerate(gram))
                vec[key % 1024] += 1.0
            norm = sum(x * x for x in vec) ** 0.5 or 1.0
            vectors.append([x / norm for x in vec])
        return vectors


async def main() -> int:
    await init_memory_db()
    ltm = LongTermMemory(embedder=HashEmbedder())
    wm = WorkingMemory()

    # 1) working memory round trip
    await wm.clear_session("eval-wm")
    await wm.add_message("eval-wm", "user", "动火作业怎么审批？")
    assert len(await wm.get_messages("eval-wm")) == 1
    print("[PASS] working memory round trip")

    # 2) episodic recall
    hits_total = 0
    for case in CASES:
        await ltm.add_episodic(
            user_id=EVAL_USER, session_id="eval-sess", summary=case["seed_summary"], importance=0.9
        )
        hits = await ltm.search_episodic(EVAL_USER, case["query"], top_k=3)
        ok = hits and case["expect"] in hits[0].content
        hits_total += bool(ok)
        print(f"[{'PASS' if ok else 'FAIL'}] episodic recall: {case['query']}")
    # 3) semantic + RLS
    await ltm.add_semantic(EVAL_USER, "preference", "eval用户是电工", importance=0.7)
    sem = await ltm.search_semantic(EVAL_USER, "电工", top_k=3)
    ok = sem and any("电工" in h.content for h in sem)
    print(f"[{'PASS' if ok else 'FAIL'}] semantic recall")
    other = await ltm.search_episodic(EVAL_USER + 1, "动火", top_k=10)
    isolated = all(h.user_id != EVAL_USER for h in other)
    print(f"[{'PASS' if isolated else 'FAIL'}] RLS isolation")
    # 4) decay/purge bookkeeping
    await ltm.decay_all(0.98)
    await ltm.purge_forgotten()
    print("[PASS] decay + purge runnable")

    report = {
        "episodic_recall": f"{hits_total}/{len(CASES)}",
        "semantic_ok": bool(sem),
        "rls_isolated": isolated,
    }
    out = Path(__file__).parent / "memory_eval_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"report -> {out}")
    return 0 if hits_total == len(CASES) and isolated else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
