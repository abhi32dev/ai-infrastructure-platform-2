# Production Readiness — Local Model Serving Harness

## Current state
FastAPI + Ollama with a full CLOSED/OPEN/HALF_OPEN circuit breaker,
verified against real Ollama outages. Measured 0.001s fast-fail latency
vs. a 30s timeout otherwise. 10 tests including boundary conditions on
the HALF_OPEN reset and a real malformed-request negative case.

## Design decisions & trade-offs

| Decision | Why | Trade-off accepted |
|---|---|---|
| Process-local, in-memory breaker state | Correct scope for "is MY connection to the downstream healthy" | Multiple instances behind a load balancer don't share breaker state — each trips independently, which is actually correct for this use case but wrong for a fleet-wide-consensus breaker |
| `FAILURE_THRESHOLD=3`, `COOLDOWN_SECONDS=5` | Tolerates transient blips, reacts reasonably fast to real outages | Fixed thresholds, not adaptive to traffic patterns or historical failure rates |
| HALF_OPEN allows exactly one probe request | Minimal-risk way to test recovery without committing full traffic | As found in project 16: without ACTIVE probing (not just passive traffic-triggered), a HALF_OPEN pod can look healthy indefinitely with no real traffic flowing to re-test it |

## What's missing for real production use
- **Active health probing in HALF_OPEN** — the exact gap project 16
  found and documented: `/health` doesn't itself ping Ollama, so recovery
  detection depends on real `/generate` traffic arriving during the
  HALF_OPEN window
- **Adaptive thresholds** — fixed failure count/cooldown regardless of
  traffic volume or time-of-day patterns
- **Multiple downstream models/failover** — the breaker guards one
  Ollama connection; no fallback to a secondary model/provider on
  sustained failure
- **Metrics export** — `/metrics` returns raw counters as JSON; no
  Prometheus-format `/metrics` endpoint (project 13 shows the pattern,
  not integrated here)

## Scaling considerations
- Single-process breaker state is actually the CORRECT scaling model for
  a per-instance circuit breaker — each replica in a horizontally-scaled
  deployment should independently detect its own downstream health
  (proven in project 16's real kind-cluster deployment)
- `httpx.AsyncClient` per-request (not connection-pooled across
  requests) — a high-throughput deployment would want a shared,
  connection-pooled client

## Security & compliance considerations
- No authentication on `/generate` or `/health` — any caller with
  network access can invoke the model; a production deployment needs API
  key or mTLS-based auth
- No rate limiting per caller — project 12's `TokenBucketLimiter` pattern
  isn't wired into this service
- No input validation beyond Pydantic's type checking — a production
  service should apply project 12's prompt-injection/PII guardrails
  before forwarding to the model

## Operational readiness
- No structured logging — errors/state transitions print nowhere beyond
  the JSON response body; a production service needs structured logs
  (correlation IDs, request tracing) feeding a real log aggregator
- No graceful degradation beyond "fail fast" — when the circuit is OPEN,
  the service returns 503 with no fallback response (e.g., a cached
  answer, a static "service degraded" message with reduced functionality)
