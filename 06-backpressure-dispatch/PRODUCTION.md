# Production Readiness — Backpressure-Isolated Ingestion + Adaptive Dispatch

## Current state
Real Redis-backed queue, adaptive worker dispatch, DLQ with replay — all
verified against real concurrency (no mocking). Measured 0.36ms avg
enqueue latency under a 500-job burst with zero consumers; worker scaling
8→2 with observed depth; DLQ+replay proven correct. 10 tests including 4
negative/edge cases.

## Design decisions & trade-offs

| Decision | Why | Trade-off accepted |
|---|---|---|
| Redis, not SQS | Zero AWS cost, one `docker compose up`, same primitives (durable queue + DLQ) | Not a 1:1 API match with SQS; a real migration would need adapter code, not just a config change |
| Simple `depth // SCALE_DIVISOR + 1` scaling formula | Legible, demonstrates the scaling MECHANISM clearly | Doesn't factor in per-job processing latency or available compute headroom — a production autoscaler needs both |
| No TTL on the attempt-count hash | Keeps the demo simple | A stale attempt counter could persist indefinitely if a job_id were ever reused — needs TTL matching project 05's idempotency-store finding |

## What's missing for real production use
- **Real SQS migration path** — the Redis primitives map conceptually to
  SQS (queue + DLQ + redrive policy) but the actual client code
  (`queue_client.py`) is Redis-specific; a production cutover needs an
  abstraction layer or a rewrite against `boto3`
- **Backoff between retries** — failed jobs are immediately re-enqueued;
  no delay before the next attempt, unlike a production system's
  exponential backoff
- **Dead-letter alerting** — jobs landing in the DLQ are silent; nothing
  pages an engineer when the DLQ starts filling up
- **Multi-consumer coordination beyond a single dispatch loop** — the
  demo runs one dispatcher process; a production deployment needs
  multiple dispatcher instances coordinating (or a single elected leader)
  without double-processing

## Scaling considerations
- Demonstrated up to depth=1035 locally; Redis itself can handle vastly
  higher throughput, but `MAX_WORKERS=8` (a `ThreadPoolExecutor` cap) is
  a local-demo constant — a real deployment would tune this to actual
  available compute and might use process-based (not thread-based)
  workers for CPU-bound job types
- Single Redis instance = single point of failure; production would need
  Redis Cluster or a managed equivalent (ElastiCache) for HA

## Security & compliance considerations
- No authentication on the local Redis instance (fine for a local demo,
  never acceptable in production) — a real deployment needs Redis AUTH
  or IAM-based access (if using a managed queue service)
- Job payloads aren't encrypted at rest in Redis — sensitive job data
  would need encryption before insertion

## Operational readiness
- No dashboard/metrics on queue depth, processing rate, or DLQ size over
  time — project 13's observability pattern isn't wired into this
  project
- No graceful shutdown handling — killing the dispatcher mid-batch
  doesn't checkpoint in-flight work beyond what Redis's own message
  visibility provides
