# 06 — Backpressure-Isolated Ingestion + Adaptive Dispatch

A real (Dockerized) Redis-backed queue, an adaptive master-worker
dispatcher that sizes its worker pool to observed queue depth, and a
dead-letter-queue with replay — the CONDOR platform's core reliability
patterns, reframed around an embedding/LLM-call pipeline instead of an S3
batch manifest, and proven with real concurrency (no mocks).

## Maps to resume claims
- "Backpressure Isolation": decoupling ingestion from downstream
  processing through a queue so a slow consumer can't cause the receiver
  to drop new data
- "Adaptive Workload Orchestration" / "Master-Worker Dispatch": dynamically
  sizing batches and worker concurrency per cycle instead of provisioning
  for permanent peak capacity
- "Recoverable Event Delivery" (dead-letter queues, DLQ replay)

## Setup (isolated venv + Docker)

```bash
cd 06-backpressure-dispatch
docker compose up -d          # starts Redis on localhost:6380
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run it

```bash
source .venv/bin/activate
cd src
python run_demo.py
```

Three scenarios:

1. **Backpressure isolation** — pushes 500 jobs with **zero consumer
   running**. Proves enqueue latency stays sub-millisecond regardless of
   how deep the (never-drained) queue gets.
2. **Adaptive dispatch** — a producer emits 5 bursty cycles (5 → 400 → 20
   → 600 → 10 jobs), and the dispatcher scales its worker pool up and back
   down in response, draining the queue to zero.
3. **DLQ + replay** — 30% of jobs are poisoned to always fail. After
   `MAX_ATTEMPTS=3`, they land in the DLQ. `replay_dlq()` moves them back
   onto the main queue; a second dispatch pass picks them up (and, being
   genuinely unrecoverable, lands them back in the DLQ — the demo doesn't
   fake a happy ending here, see below).

## Measured results (this run)

| Scenario | Result |
|---|---|
| Enqueue latency, 500-job burst, no consumer | avg 0.36ms, worst 0.74ms |
| Worker scaling | depth=1035 → 8 workers, depth=35 → 2 workers |
| Full drain after bursty load | queue_depth: 0 |
| DLQ after 30%-poison run | 30/100 jobs landed in DLQ |
| Replay | 30 replayed, queue_depth=30 after replay |

## Tests

```bash
cd 06-backpressure-dispatch && source .venv/bin/activate && pytest -q
```
5 live integration tests against the real Redis instance (no mocking —
this project's whole point is real queueing/concurrency behavior):
enqueue-latency bound under a deep queue, worker-count scaling formula,
full-drain correctness, DLQ landing after max attempts, and replay
correctness.

## What to say in an interview

- **Why is "backpressure isolation" provable and not just a design
  claim?** Scenario 1 runs zero consumers at all — if the queue write
  path were coupled to consumer throughput, enqueue latency would degrade
  as the queue grew. It doesn't (0.36ms avg at depth 500), because
  `LPUSH` is O(1) regardless of list length and has no dependency on
  whether anything is reading from the other end.
- **Why `depth // SCALE_DIVISOR + 1` instead of a smarter autoscaling
  curve?** It's intentionally simple and legible — the point being
  demonstrated is *that* worker count responds to observed load
  (8 workers at depth 1035, 2 at depth 35), not a specific scaling
  algorithm. A production version would also factor in per-job processing
  latency and available compute headroom (this demo assumes uniform
  ~50ms simulated work per job), same as CONDOR's real dispatcher reacting
  to both volume *and* per-unit payload size independently.
- **Why does the DLQ replay scenario end with the jobs back in the DLQ
  instead of succeeding?** Because I intentionally poisoned those jobs to
  always fail (`force_fail=True`) — that's the honest test of what replay
  actually does: it retries, it doesn't repair. Volunteering this in an
  interview is the point: a replay mechanism's job is to give a
  transient failure another chance, not to guarantee success — for a
  truly poisoned job, replay is supposed to put it back in the DLQ, and a
  human/alert should look at *why* it's still failing, not loop replay
  forever.
- **Why Redis instead of SQS for this demo?** Zero AWS cost, runs in one
  `docker compose up -d`, and the primitives being demonstrated
  (a durable FIFO-ish queue decoupling producer from consumer, a DLQ)
  are conceptually identical — SQS is the production swap-in, same as
  project 01 noting Chroma → pgvector as the production swap for vector
  storage.
- **Known limitation to volunteer:** attempt-count tracking
  (`INFLIGHT_HASH`) has no TTL in this demo — a production version would
  expire stale attempt counters (same TTL-based idempotency pattern as
  project 05) so a job_id from days ago doesn't quietly inherit a stale
  attempt count if it's ever reused.
