"""Smoke tests. Require Ollama running locally with the models pulled
(see README). Run with: pytest -q from the 01-rag-pipeline directory.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ingest import load_documents
from chunking import chunk_documents
from embed_index import build_index
from retrieve import retrieve
from generate import answer


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


def test_retrieval_returns_relevant_top_hit():
    build_index()
    results = retrieve("What happens when an EC2 receiver fails health checks?", k=3)
    assert len(results) == 3
    top_doc, _ = results[0]
    assert top_doc.metadata["doc_id"] == "oncall_faq.md"


def test_generation_is_grounded_and_refuses_out_of_scope():
    result = answer("What is the CEO's favorite color?")
    lowered = result["answer"].lower()
    assert "context" in lowered or "does not" in lowered or "no information" in lowered
