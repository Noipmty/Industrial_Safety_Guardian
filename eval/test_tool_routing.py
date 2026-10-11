"""Tool-routing evaluation over the 50-question golden set.

Acceptance (prompt §P2): tool-selection accuracy >= 90%.
The router = rule classifier (query_type) + deterministic route table, so
routing accuracy equals classification accuracy against the golden labels.

Run:  cd gongan && conda run -n jrong python -m pytest eval/test_tool_routing.py -v
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
BACKEND_DIR = EVAL_DIR.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.workflows.safety_qa.nodes import TOOL_ROUTE_TABLE, classify_query_rules  # noqa: E402

QUERIES_PATH = EVAL_DIR / "queries.json"
EXPECTED_TYPES = {"factual", "relational", "visual", "structural"}


def load_golden() -> list[dict]:
    with open(QUERIES_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def test_golden_set_size():
    golden = load_golden()
    assert len(golden) >= 50
    for item in golden:
        assert item["query_type"] in EXPECTED_TYPES
        assert item["query"].strip()


def test_route_table_complete_and_never_all_tools():
    """Every query_type maps to a non-empty toolset; no type gets everything."""
    all_tools = {"hybrid_search", "sql_query", "graph_rag", "multimodal_rag"}
    for qtype in EXPECTED_TYPES:
        tools = TOOL_ROUTE_TABLE.get(qtype)
        assert tools, f"missing route for {qtype}"
        assert set(tools) < all_tools or len(all_tools) < 4


def route(query: str) -> tuple[str, list[str]]:
    """Full routing decision: classify -> plan."""
    qtype = classify_query_rules(query)
    return qtype, TOOL_ROUTE_TABLE[qtype]


def test_tool_routing_accuracy_at_least_90pct():
    golden = load_golden()
    correct = 0
    misses = []
    for item in golden:
        predicted_type, _ = route(item["query"])
        if predicted_type == item["query_type"]:
            correct += 1
        else:
            misses.append((item["id"], item["query_type"], predicted_type, item["query"]))
    accuracy = correct / len(golden)
    print(f"\n=== tool routing accuracy: {accuracy:.2%} ({correct}/{len(golden)}) ===")
    for mid, gold, pred, query in misses:
        print(f"MISS {mid}: golden={gold} predicted={pred} :: {query}")
    assert accuracy >= 0.90, f"routing accuracy {accuracy:.2%} < 90%"


def test_routing_is_deterministic():
    golden = load_golden()
    sample = golden[:5]
    first = [route(item["query"]) for item in sample]
    second = [route(item["query"]) for item in sample]
    assert first == second
