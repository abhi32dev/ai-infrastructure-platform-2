# 13 — Observability for AI Systems

Full OpenTelemetry tracing (one parent span per query, one child span per
pipeline stage) plus Prometheus metrics plus a provisioned Grafana
dashboard, wired around a small traced RAG pipeline — the AI-specific
extension of the resume's existing Prometheus/Grafana/OpenTelemetry line.

## Maps to the request
- "Observability" — distinct from generic infra observability already on
  the resume: this traces *inside* an AI request (retrieval span,
  context-assembly span, generation span) so a slow or wrong answer can be
  root-caused to a specific stage, not just "the request was slow."

## Architecture

```
FastAPI /query --> traced_pipeline.run_traced_query()
                      |
                      +-- span: retrieval          (+ Prometheus: rag_stage_latency_seconds{stage="retrieval"})
                      +-- span: context_assembly    (+ rag_tokens_total{stage="context_assembly"})
                      +-- span: generation           (+ rag_stage_latency_seconds{stage="generation"}, rag_tokens_total{stage="generation"})
                    parent span: rag_query          (+ rag_request_latency_seconds, rag_requests_total)

FastAPI /metrics --> scraped by Prometheus (docker-compose) --> visualized in Grafana
```

## Setup (isolated venv + Docker)

```bash
cd 13-observability
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

ollama pull llama3.2:1b
```

## Run it

**1. Start the traced app:**
```bash
source .venv/bin/activate
cd src
uvicorn app:app --port 8000
```

**2. See raw trace spans printed to console** (parent + child spans,
correct `trace_id`/`parent_id` linkage, per-stage attributes):
```bash
python traced_pipeline.py
```

**3. Start Prometheus + Grafana:**
```bash
cd ..   # back to 13-observability/
docker compose up -d
```
- Prometheus UI: http://localhost:9091 (confirm target is "up" at
  `/targets`)
- Grafana: http://localhost:3001 (anonymous admin access enabled for this
  demo only) — the "Aegis RAG Pipeline — Observability" dashboard is
  auto-provisioned with 5 panels: request latency (p50/p95), per-stage
  latency (p95), requests/min by outcome, tokens/min by stage, and a
  judge-agreement-rate gauge (wired to project 02/03's metric name).

**4. Generate traffic to see it live:**
```bash
curl -X POST localhost:8000/query -H 'content-type: application/json' \
  -d '{"query": "What caused the 2026-02-14 incident?"}'
```

## Verified this run

- Prometheus target status: **`up`** — confirmed via
  `curl localhost:9091/api/v1/targets`
- After 3 real queries, `curl localhost:9091/api/v1/query?query=rag_requests_total`
  correctly returned `outcome="success"` with value `3`
- Console trace output shows correct span hierarchy: `retrieval`,
  `context_assembly`, and `generation` all share one `trace_id` and list
  the `rag_query` span as `parent_id`

## Tests

```bash
cd 13-observability && source .venv/bin/activate && pytest -q
```
8 live tests (real pipeline, real metric registry reads), in three categories:
- **Positive path (5):** retrieval relevance, context assembly correctness, end-to-end traced query correctness, and two tests confirming Prometheus counters/histograms actually increment on real requests (reading the client library's in-memory values directly rather than parsing `/metrics` text)
- **Negative / edge cases (2):** a query with zero keyword overlap against the corpus still returns a fallback chunk instead of crashing; `assemble_context([])` returns an empty string rather than raising
- **Regression guard (1):** forcing a real exception during generation proves the `outcome="error"` metric actually increments — verified by triggering the failure, not just trusting the try/except wiring by inspection

## What to say in an interview

- **Why per-stage spans instead of one span per request?** A single span
  answers "was this request slow" — a per-stage breakdown answers "which
  *part* was slow," which is what you actually need to fix it. If
  `generation` latency dominates, that's a model/routing problem (project
  04); if `retrieval` dominates, that's an index/infra problem (project
  01/06) — same request-latency number, completely different fix.
- **Why both traces AND metrics, not just one?** They answer different
  questions at different scales. A trace is a detailed record of one
  specific request — invaluable for debugging "why was THIS query slow,"
  but useless for "what's our p95 latency this week" (you'd have to
  aggregate thousands of them by hand). A metric is a pre-aggregated
  number Prometheus can alert on and Grafana can chart cheaply. Production
  observability needs both, and OpenTelemetry's API is intentionally
  vendor-neutral so switching the trace backend later (Jaeger, Tempo,
  Grafana Cloud) doesn't touch any instrumentation code — only
  `tracing_setup.py`'s exporter config.
- **Why is the judge-agreement-rate gauge hardcoded to 0.83 instead of
  pulled live from project 02/03?** Deliberate project isolation (every
  project in this portfolio has its own venv and no cross-project runtime
  dependency, per the "keep every project fully self-contained" rule) —
  in a real single-service deployment, that gauge would be set from the
  actual MLflow-tracked latest run, exactly the number project 03 measured
  (0.83 for the v2 prompt). The dashboard panel and metric name are wired
  correctly; only the data source is stubbed for this demo.
- **Known limitation to volunteer:** the console span exporter throws a
  harmless `ValueError: I/O operation on closed file` during pytest
  teardown (the batch processor's background thread tries to flush after
  the test session closes stdout) — cosmetic, doesn't affect test results
  or span correctness, but a real deployment would use the OTLP exporter
  (already wired via the `OTLP_ENDPOINT` env var) rather than console
  output, which doesn't have this teardown-ordering issue.
