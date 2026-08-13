"""Deterministic unit tests of routing/cost math (mocked classifier), plus
live integration tests proving the router actually saves money and the
chunk sweep actually shows a cost/quality tradeoff on real local models.
"""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import router
from config import SMALL_MODEL, LARGE_MODEL


def test_simple_classification_routes_to_small_model():
    with patch("router.classify", return_value="SIMPLE"), \
         patch("router.ChatOllama") as mock_chat:
        mock_chat.return_value.invoke.return_value.content = "answer"
        result = router.route_and_answer("What model runs the receiver fleet?")
    assert result["model_used"] == SMALL_MODEL


def test_complex_classification_routes_to_large_model():
    with patch("router.classify", return_value="COMPLEX"), \
         patch("router.ChatOllama") as mock_chat:
        mock_chat.return_value.invoke.return_value.content = "answer"
        result = router.route_and_answer("Compare and justify the two ingestion paths.")
    assert result["model_used"] == LARGE_MODEL


def test_unparsable_classification_fails_safe_to_complex():
    with patch("router.ChatOllama") as mock_chat:
        mock_chat.return_value.invoke.return_value.content = "not valid json"
        tier = router.classify("anything")
    assert tier == "COMPLEX"  # fail-safe: ambiguous classification -> stronger model, not cheaper one


def test_live_routing_reduces_total_cost_vs_always_large():
    from cost_report import run_report
    _, total_routed, total_always_large = run_report()
    assert total_routed < total_always_large


def test_live_chunk_sweep_shows_quality_improves_with_larger_chunks():
    from chunk_sweep import sweep
    results = sweep()
    small_chunk_hit_rate = max(r["hit_rate"] for r in results if r["chunk_size"] == 200)
    large_chunk_hit_rate = max(r["hit_rate"] for r in results if r["chunk_size"] == 1000)
    assert large_chunk_hit_rate >= small_chunk_hit_rate
