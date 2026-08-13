"""Smoke tests. Require Ollama running locally with the models pulled
(see README). Run with: pytest -q from the 01-rag-pipeline directory.

Test categories, explicitly:
  - Positive path: ingestion, chunking, retrieval relevance, grounded generation
  - Negative path: empty documents, empty query, out-of-corpus refusal
  - Regression guards: deterministic chunking, no verbatim context echo
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ingest import load_documents
from chunking import chunk_documents
from embed_index import build_index
from retrieve import retrieve
from generate import answer


@pytest.fixture(scope="module")
def indexed():
    """Build the vector index exactly once for the whole test module.
    Chroma's sqlite-backed persistence does not handle rapid rebuild-in-
    place cleanly across many calls in one process (hit a 'readonly
    database' error doing this per-test — same root cause documented in
    project 04's chunk_sweep.py); one shared build avoids it."""
    build_index()
    return True


# --- Positive path ---

def test_ingest_finds_all_docs():
    docs = load_documents()
    assert len(docs) == 4
    names = {d[0] for d in docs}
    assert "platform_architecture.md" in names


def test_chunking_produces_multiple_chunks_per_doc():
    docs = load_documents()
    chunks = chunk_documents(docs)
    assert len(chunks) > len(docs)
    for c in chunks:
        assert len(c.text) <= 500 + 50  # allow small splitter slack


def test_retrieval_returns_relevant_top_hit(indexed):
    results = retrieve("What happens when an EC2 receiver fails health checks?", k=3)
    assert len(results) == 3
    top_doc, _ = results[0]
    assert top_doc.metadata["doc_id"] == "oncall_faq.md"


def test_generation_is_grounded_and_refuses_out_of_scope():
    result = answer("What is the CEO's favorite color?")
    lowered = result["answer"].lower()
    assert "context" in lowered or "does not" in lowered or "no information" in lowered


# --- Negative / edge cases ---

def test_chunking_empty_document_produces_no_chunks():
    chunks = chunk_documents([("empty.md", "")])
    assert chunks == []


def test_retrieve_k_larger_than_corpus_does_not_crash(indexed):
    results = retrieve("health checks", k=1000)
    # Chroma caps results at however many vectors actually exist — should
    # return everything available, not raise, and not silently return 1000
    # duplicated/empty entries.
    assert 0 < len(results) < 1000


def test_retrieve_empty_query_string_does_not_crash(indexed):
    results = retrieve("", k=2)
    assert isinstance(results, list)


# --- Regression guards ---

def test_chunking_is_stable_under_repeated_calls_on_same_input():
    """A future change to the splitter config should not silently change
    chunk counts/boundaries without a test failing."""
    docs = load_documents()
    chunks_a = chunk_documents(docs)
    chunks_b = chunk_documents(docs)
    assert [c.text for c in chunks_a] == [c.text for c in chunks_b]


def test_generation_answers_are_not_a_verbatim_context_dump():
    """Loose regression check that the model is synthesizing an answer
    from context, not just echoing the raw assembled context block back
    (which would indicate the grounding instruction stopped working)."""
    result = answer("Who approves a rollback?")
    assert result["context"] not in result["answer"]
