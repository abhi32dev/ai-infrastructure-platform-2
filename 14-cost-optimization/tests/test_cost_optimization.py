"""Deterministic tests of the cache math and ledger arithmetic (no LLM
calls), plus a live end-to-end test of the real semantic cache against
real embeddings.
"""

import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from semantic_cache import cosine_similarity
from cost_ledger import get_connection, log_request, summary


def test_cosine_similarity_identical_vectors_is_one():
    v = np.array([1.0, 2.0, 3.0])
    assert abs(cosine_similarity(v, v) - 1.0) < 1e-9


def test_cosine_similarity_orthogonal_vectors_is_zero():
    a = np.array([1.0, 0.0])
    b = np.array([0.0, 1.0])
    assert abs(cosine_similarity(a, b)) < 1e-9


def test_ledger_summary_computes_hit_rate_and_savings(tmp_path):
    conn = get_connection(tmp_path / "test_ledger.sqlite")
    log_request(conn, "q1", cache_hit=False, similarity=None, tokens=100, actual_cost=0.01, would_be_cost=0.01)
    log_request(conn, "q2", cache_hit=True, similarity=0.9, tokens=50, actual_cost=0.0, would_be_cost=0.005)

    stats = summary(conn)
    assert stats["total_requests"] == 2
    assert stats["cache_hits"] == 1
    assert stats["cache_hit_rate"] == 0.5
    assert abs(stats["actual_cost_usd"] - 0.01) < 1e-9
    assert abs(stats["would_be_cost_usd"] - 0.015) < 1e-9
    assert abs(stats["savings_usd"] - 0.005) < 1e-9


def test_empty_ledger_summary_has_no_division_errors(tmp_path):
    conn = get_connection(tmp_path / "empty_ledger.sqlite")
    stats = summary(conn)
    assert stats["total_requests"] == 0
    assert stats["cache_hit_rate"] == 0.0
    assert stats["savings_pct"] == 0.0


def test_live_semantic_cache_hits_on_close_paraphrase_and_misses_on_unrelated():
    from semantic_cache import SemanticCache

    cache = SemanticCache(threshold=0.75)
    cache.store("What happens when an EC2 receiver fails health checks?", "cached answer")

    close_paraphrase_hit = cache.lookup("When an instance fails its health check, what happens automatically?")
    unrelated_miss = cache.lookup("What's a good recipe for banana bread?")

    assert close_paraphrase_hit is not None
    assert close_paraphrase_hit["similarity"] >= 0.75
    assert unrelated_miss is None


# --- Negative / edge cases ---

def test_cache_lookup_on_empty_cache_returns_none():
    from semantic_cache import SemanticCache

    cache = SemanticCache(threshold=0.75)
    result = cache.lookup("any query at all")
    assert result is None


def test_ledger_summary_all_cache_hits_is_100pct_savings(tmp_path):
    conn = get_connection(tmp_path / "all_hits_ledger.sqlite")
    log_request(conn, "q1", cache_hit=True, similarity=0.9, tokens=50, actual_cost=0.0, would_be_cost=0.005)
    log_request(conn, "q2", cache_hit=True, similarity=0.85, tokens=40, actual_cost=0.0, would_be_cost=0.004)

    stats = summary(conn)
    assert stats["cache_hit_rate"] == 1.0
    assert stats["actual_cost_usd"] == 0.0
    assert stats["savings_pct"] == 100.0


def test_calibration_regression_guard_high_threshold_misses_known_paraphrase():
    """Documents and protects the real calibration finding from the
    README: at the originally-guessed threshold of 0.92, the same close
    paraphrase that hits at 0.75 must NOT hit — if someone 'fixes' the
    threshold back to a higher guessed value without re-measuring, this
    test fails and points at why."""
    from semantic_cache import SemanticCache

    cache = SemanticCache(threshold=0.92)
    cache.store("What happens when an EC2 receiver fails health checks?", "cached answer")
    result = cache.lookup("When an instance fails its health check, what happens automatically?")
    assert result is None  # measured similarity was 0.790, below 0.92


def test_cosine_similarity_opposite_vectors_is_negative_one():
    a = np.array([1.0, 0.0])
    b = np.array([-1.0, 0.0])
    assert abs(cosine_similarity(a, b) - (-1.0)) < 1e-9
