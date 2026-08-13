"""Prometheus metrics for the RAG pipeline — the request-level counterpart
to the per-request OpenTelemetry traces: traces answer 'what happened in
THIS request,' metrics answer 'what's the aggregate behavior over time,'
which is what an on-call dashboard and alerting actually key off.
"""

from prometheus_client import Counter, Histogram, Gauge

REQUEST_LATENCY = Histogram(
    "rag_request_latency_seconds", "End-to-end RAG query latency",
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10, 30),
)
STAGE_LATENCY = Histogram(
    "rag_stage_latency_seconds", "Per-stage latency within a RAG query",
    ["stage"], buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)
REQUESTS_TOTAL = Counter("rag_requests_total", "Total RAG queries processed", ["outcome"])
TOKENS_TOTAL = Counter("rag_tokens_total", "Total tokens consumed", ["stage"])
JUDGE_AGREEMENT_RATE = Gauge(
    "rag_judge_agreement_rate", "Most recent evaluation-gate agreement rate (from project 02/03)"
)
