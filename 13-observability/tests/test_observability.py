"""Live tests against the real traced/instrumented pipeline (no mocking —
this project's entire point is that the instrumentation actually captures
what happened). Prometheus metric values are read directly from the
client library's registry rather than parsing the /metrics text output.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from traced_pipeline import run_traced_query, retrieve, assemble_context
from metrics import REQUESTS_TOTAL, REQUEST_LATENCY


def test_retrieval_returns_relevant_chunk_for_keyword_match():
    chunks = retrieve("What caused the incident on 2026-02-14?")
    doc_ids = [d for d, _ in chunks]
    assert "incidents" in doc_ids


def test_context_assembly_includes_all_retrieved_chunks():
    chunks = [("architecture", "text one"), ("incidents", "text two")]
    context = assemble_context(chunks)
    assert "text one" in context
    assert "text two" in context
    assert "[architecture]" in context
    assert "[incidents]" in context


def test_traced_query_returns_answer_and_sources():
    result = run_traced_query("What caused the 2026-02-14 incident?")
    assert result["answer"]
    assert "incidents" in result["sources"]
    assert result["latency_sec"] > 0


def test_metrics_increment_on_successful_query():
    before = REQUESTS_TOTAL.labels(outcome="success")._value.get()
    run_traced_query("How does the receiver fleet handle failover?")
    after = REQUESTS_TOTAL.labels(outcome="success")._value.get()
    assert after == before + 1


def test_request_latency_histogram_records_observation():
    before_count = REQUEST_LATENCY._sum.get()
    run_traced_query("When should rollback trigger?")
    after_count = REQUEST_LATENCY._sum.get()
    assert after_count > before_count


# --- Negative / edge cases ---

def test_retrieve_with_no_keyword_overlap_falls_back_gracefully():
    """Negative case: a query sharing zero words with any corpus entry
    must not return an empty result — the fallback returns the
    highest-scoring (even if score=0) entry rather than crashing or
    silently returning nothing to assemble_context."""
    chunks = retrieve("xyzzy plugh qwerty nonsense words")
    assert len(chunks) >= 1


def test_assemble_context_with_empty_chunk_list_returns_empty_string():
    context = assemble_context([])
    assert context == ""


def test_metrics_increment_on_error_outcome():
    """Regression guard: the error path (REQUESTS_TOTAL.labels(outcome=
    'error')) must actually increment when generation raises — proven by
    forcing a real exception, not just trusting the try/except wiring by
    inspection."""
    from unittest.mock import patch
    import traced_pipeline

    before = REQUESTS_TOTAL.labels(outcome="error")._value.get()

    with patch("traced_pipeline.generate", side_effect=RuntimeError("simulated downstream failure")):
        try:
            traced_pipeline.run_traced_query("this will fail during generation")
        except RuntimeError:
            pass

    after = REQUESTS_TOTAL.labels(outcome="error")._value.get()
    assert after == before + 1
