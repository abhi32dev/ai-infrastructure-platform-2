# Production Readiness — Observability Stack

## Current state
Full OpenTelemetry tracing (per-stage spans), Prometheus metrics, and a
provisioned Grafana dashboard via docker-compose. Verified end-to-end:
Prometheus target "up", real query counts scraped and queryable. 8 tests
including a forced-exception regression guard on the error-outcome metric.

## Design decisions & trade-offs

| Decision | Why | Trade-off accepted |
|---|---|---|
| Console span exporter by default, OTLP via env var | Zero-dependency demo out of the box | Console exporter has a known teardown-ordering cosmetic bug (documented); production should always use OTLP, not console |
| Prometheus pull-based scraping | Standard, matches the resume's existing Prometheus/Grafana experience | Requires the app to stay up and reachable for scraping; doesn't handle short-lived/serverless workloads well (would need Pushgateway) |
| Judge-agreement-rate gauge hardcoded, not pulled from project 02/03 | Deliberate project isolation (no cross-project runtime dependency) | The dashboard panel exists and is wired correctly, but shows a stub value, not live data — would need integration work to connect for real |
| In-memory keyword-matched corpus, not real Chroma retrieval | Keeps focus on instrumentation, not duplicating project 01's retrieval | Traced "retrieval" span doesn't reflect real vector-search latency characteristics |

## What's missing for real production use
- **Real cross-project metric integration** — the judge-agreement-rate
  gauge is a stub; a real single-service deployment would set it from
  project 03's actual latest MLflow run
- **Alerting rules** — Prometheus is scraping metrics but no Alertmanager
  rules are defined (e.g., alert if p99 latency exceeds a threshold, or
  error rate spikes)
- **Distributed tracing across service boundaries** — this traces one
  process's internal stages; a real multi-service AI pipeline (RAG
  service → guardrails service → model-serving service) needs trace
  context propagation across HTTP calls between them
- **Log correlation** — traces and metrics exist, but no structured
  logging correlated by trace ID, which is the third pillar of
  observability

## Scaling considerations
- Prometheus's pull model scales to many scrape targets easily; the
  actual scaling concern is cardinality — this demo's metrics have low
  label cardinality (stage names, outcome), but a production system
  adding per-user or per-request-ID labels would blow up Prometheus's
  memory usage
- OTLP export (once switched on from console) handles higher trace
  volume via the SDK's batching processor already configured

## Security & compliance considerations
- Grafana is configured with anonymous admin access for this demo
  ("for this demo only," explicitly flagged) — never acceptable in a real
  deployment; needs real authentication (SSO, at minimum a non-default
  admin password)
- Trace attributes include full query text — if queries contain PII, that
  PII now lives in the tracing backend too; production tracing needs the
  same redaction discipline as project 12 applied before span attributes
  are set

## Operational readiness
- No dashboard alerting thresholds configured — the Grafana dashboard
  displays data but doesn't page anyone on anomalies
- No runbook linkage from alerts to remediation steps — would need to be
  built alongside any real alerting rules
