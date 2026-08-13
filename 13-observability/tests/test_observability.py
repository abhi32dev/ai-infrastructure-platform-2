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
