"""A small RAG pipeline (retrieval -> context assembly -> generation),
instrumented end to end: one parent span per query, one child span per
stage, with attributes recording exactly what a real debugging session
would want to know (chunks retrieved, token counts, model used) — and the
matching Prometheus metrics recorded at the same boundaries.

Uses a tiny in-memory keyword-matched corpus instead of a full vector DB
(project 01 already covers real vector retrieval in depth) so this
project's focus stays on the observability instrumentation itself.
"""

import time
import tiktoken
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from opentelemetry.trace import Status, StatusCode

from tracing_setup import tracer
from metrics import REQUEST_LATENCY, STAGE_LATENCY, REQUESTS_TOTAL, TOKENS_TOTAL

encoder = tiktoken.get_encoding("cl100k_base")

MODEL_NAME = "llama3.2:1b"

CORPUS = [
    ("architecture", "The receiver fleet runs on Amazon EC2 with a Network Load Balancer for multi-AZ failover."),
    ("incidents", "The 2026-02-14 incident was caused by a race condition in the dedup marker write timing."),
    ("runbook", "Rollback should be triggered if error rate exceeds 2x baseline for 5 consecutive minutes."),
]


def retrieve(query: str) -> list[tuple[str, str]]:
    with tracer.start_as_current_span("retrieval") as span:
        start = time.time()
        query_words = set(query.lower().split())
        scored = [(doc_id, text, len(query_words & set(text.lower().split()))) for doc_id, text in CORPUS]
        scored.sort(key=lambda x: -x[2])
        top = [(doc_id, text) for doc_id, text, score in scored[:2] if score > 0] or [scored[0][:2]]

        elapsed = time.time() - start
        span.set_attribute("chunks_retrieved", len(top))
        span.set_attribute("retrieval.doc_ids", [d for d, _ in top])
        STAGE_LATENCY.labels(stage="retrieval").observe(elapsed)
        return top


def assemble_context(chunks: list[tuple[str, str]]) -> str:
    with tracer.start_as_current_span("context_assembly") as span:
        start = time.time()
        context = "\n".join(f"[{doc_id}] {text}" for doc_id, text in chunks)
        token_count = len(encoder.encode(context))

        elapsed = time.time() - start
        span.set_attribute("context.tokens", token_count)
        STAGE_LATENCY.labels(stage="context_assembly").observe(elapsed)
        TOKENS_TOTAL.labels(stage="context_assembly").inc(token_count)
        return context


def generate(query: str, context: str) -> str:
    with tracer.start_as_current_span("generation") as span:
        start = time.time()
        span.set_attribute("generation.model", MODEL_NAME)

        llm = ChatOllama(model=MODEL_NAME, temperature=0.1)
        response = llm.invoke([HumanMessage(content=f"Context:\n{context}\n\nQuestion: {query}")])
        text = response.content

        elapsed = time.time() - start
        output_tokens = len(encoder.encode(text))
        span.set_attribute("generation.output_tokens", output_tokens)
        span.set_attribute("generation.latency_sec", elapsed)
        STAGE_LATENCY.labels(stage="generation").observe(elapsed)
        TOKENS_TOTAL.labels(stage="generation").inc(output_tokens)
        return text


def run_traced_query(query: str) -> dict:
    overall_start = time.time()
    with tracer.start_as_current_span("rag_query") as span:
        span.set_attribute("query", query)
        try:
            chunks = retrieve(query)
            context = assemble_context(chunks)
            answer = generate(query, context)

            span.set_status(Status(StatusCode.OK))
            REQUESTS_TOTAL.labels(outcome="success").inc()
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            REQUESTS_TOTAL.labels(outcome="error").inc()
            raise
        finally:
            total_latency = time.time() - overall_start
            REQUEST_LATENCY.observe(total_latency)
            span.set_attribute("total_latency_sec", total_latency)

    return {"query": query, "answer": answer, "sources": [d for d, _ in chunks], "latency_sec": total_latency}


if __name__ == "__main__":
    result = run_traced_query("What caused the 2026-02-14 incident?")
    print("\n=== Final result ===")
    print(f"Q: {result['query']}")
    print(f"A: {result['answer'][:200]}")
    print(f"Sources: {result['sources']} | latency: {result['latency_sec']:.2f}s")
