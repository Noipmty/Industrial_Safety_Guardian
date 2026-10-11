"""RAGAS evaluation runner for 工安卫士.

Usage:
    python run_ragas.py --api-url http://localhost:8000
    python run_ragas.py --api-url http://localhost:8000 --check-baseline
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import httpx


@dataclass
class EvalResult:
    """Single question evaluation result."""

    query_id: str
    query: str
    ground_truth: str
    answer: str
    sources: list[dict] = field(default_factory=list)
    faithfulness: float = 0.0
    context_recall: float = 0.0
    answer_relevancy: float = 0.0
    error: str | None = None


async def call_api(
    client: httpx.AsyncClient,
    api_url: str,
    query: str,
    user_position: str,
) -> dict:
    """Call chat API and return response."""
    resp = await client.post(
        f"{api_url}/api/v1/chat",
        json={
            "session_id": None,
            "message": query,
            "user_id": 1,
            "stream": False,
        },
        headers={"X-User-Position": user_position},
        timeout=60.0,
    )
    resp.raise_for_status()
    return resp.json()


def compute_ragas_metrics(result: EvalResult) -> EvalResult:
    """Compute RAGAS metrics locally (simplified for P0).

    Full RAGAS integration requires langchain + ragas package.
    In P0 we compute simplified proxies:
    - faithfulness: answer is grounded in sources (keyword overlap)
    - context_recall: ground truth keywords appear in sources
    - answer_relevancy: answer keywords overlap with query
    """
    if result.error:
        return result

    # Context recall: how many ground_truth keywords appear in sources
    gt_words = set(result.ground_truth.replace("，", " ").replace("。", " ").split())
    source_text = " ".join(s.get("text", "") for s in result.sources)
    source_words = set(source_text.replace("，", " ").replace("。", " ").split())
    if gt_words:
        recalled = len(gt_words & source_words)
        result.context_recall = round(recalled / len(gt_words), 4)
    else:
        result.context_recall = 0.0

    # Faithfulness: answer keywords appear in sources
    answer_words = set(result.answer.replace("，", " ").replace("。", " ").split())
    if answer_words:
        grounded = len(answer_words & source_words)
        result.faithfulness = round(grounded / len(answer_words), 4)
    else:
        result.faithfulness = 0.0

    # Answer relevancy: query keywords appear in answer
    query_words = set(result.query.replace("？", " ").replace("，", " ").split())
    if query_words:
        relevant = len(query_words & answer_words)
        result.answer_relevancy = round(relevant / len(query_words), 4)
    else:
        result.answer_relevancy = 0.0

    return result


def check_baseline(results: list[EvalResult], baseline_path: Path) -> bool:
    """Check if metrics meet baseline thresholds."""
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    avg_faith = sum(r.faithfulness for r in results) / len(results)
    avg_recall = sum(r.context_recall for r in results) / len(results)
    avg_relevancy = sum(r.answer_relevancy for r in results) / len(results)

    faith_threshold = baseline.get("faithfulness", 0.70)
    recall_threshold = baseline.get("context_recall", 0.65)
    relevancy_threshold = baseline.get("answer_relevancy", 0.72)

    passed = True
    if avg_faith < faith_threshold - 0.05:
        print(f"FAIL: faithfulness {avg_faith:.4f} < baseline {faith_threshold}")
        passed = False
    if avg_recall < recall_threshold - 0.05:
        print(f"FAIL: context_recall {avg_recall:.4f} < baseline {recall_threshold}")
        passed = False
    if avg_relevancy < relevancy_threshold - 0.05:
        print(f"FAIL: answer_relevancy {avg_relevancy:.4f} < baseline {relevancy_threshold}")
        passed = False

    return passed


async def main() -> int:
    parser = argparse.ArgumentParser(description="RAGAS evaluation runner")
    parser.add_argument("--api-url", default="http://localhost:8000", help="Backend API URL")
    parser.add_argument(
        "--queries-file",
        default=None,
        help="Path to queries.json (default: same dir as this script)",
    )
    parser.add_argument("--output", default=None, help="Output results file path")
    parser.add_argument("--check-baseline", action="store_true", help="Fail if below baseline")
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    queries_path = Path(args.queries_file) if args.queries_file else script_dir / "queries.json"
    baseline_path = script_dir / "baseline.json"
    output_path = Path(args.output) if args.output else script_dir / "results.json"

    queries = json.loads(queries_path.read_text(encoding="utf-8"))
    print(f"Loaded {len(queries)} golden set queries")

    results: list[EvalResult] = []
    async with httpx.AsyncClient() as client:
        for q in queries:
            result = EvalResult(
                query_id=q["id"],
                query=q["query"],
                ground_truth=q["ground_truth"],
                answer="",
            )
            try:
                resp = await call_api(client, args.api_url, q["query"], q.get("user_position", "司钻"))
                result.answer = resp.get("response", "")
                result.sources = resp.get("sources", [])
            except Exception as exc:
                result.error = str(exc)
                print(f"  {q['id']}: ERROR - {exc}")

            result = compute_ragas_metrics(result)
            status = "OK" if not result.error else "ERR"
            print(
                f"  {q['id']}: [{status}] "
                f"faith={result.faithfulness:.3f} "
                f"recall={result.context_recall:.3f} "
                f"relevancy={result.answer_relevancy:.3f}"
            )
            results.append(result)

    avg_faith = sum(r.faithfulness for r in results) / len(results)
    avg_recall = sum(r.context_recall for r in results) / len(results)
    avg_relevancy = sum(r.answer_relevancy for r in results) / len(results)

    print("\n=== Summary ===")
    print(f"Total queries: {len(results)}")
    print(f"Avg faithfulness:   {avg_faith:.4f}")
    print(f"Avg context_recall: {avg_recall:.4f}")
    print(f"Avg answer_relevancy: {avg_relevancy:.4f}")

    output_data = {
        "total_queries": len(results),
        "avg_faithfulness": round(avg_faith, 4),
        "avg_context_recall": round(avg_recall, 4),
        "avg_answer_relevancy": round(avg_relevancy, 4),
        "results": [
            {
                "query_id": r.query_id,
                "query": r.query,
                "ground_truth": r.ground_truth,
                "answer": r.answer,
                "faithfulness": r.faithfulness,
                "context_recall": r.context_recall,
                "answer_relevancy": r.answer_relevancy,
                "error": r.error,
            }
            for r in results
        ],
    }
    output_path.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResults written to {output_path}")

    if args.check_baseline:
        if not check_baseline(results, baseline_path):
            print("\nEVAL GATE FAILED: metrics below baseline threshold")
            return 1
        print("\nEVAL GATE PASSED")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
