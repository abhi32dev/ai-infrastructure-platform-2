"""Three scenarios, run against the real local Redis (docker-compose up):

1. Backpressure isolation: push a large burst while NO consumer is running
   at all, and prove enqueue latency stays low regardless of how deep the
   queue gets — the producer never waits on the consumer.
2. Adaptive dispatch: run the dispatcher against a bursty multi-cycle
   producer load and show worker count scaling with observed queue depth.
3. DLQ + replay: some jobs are poisoned to always fail; after MAX_ATTEMPTS
   they land in the DLQ; replay_dlq() puts them back on the main queue and
   a final dispatch cycle drains them (still failing — proving replay
   re-attempts rather than silently discarding, even though these
   particular jobs are intentionally unrecoverable in this demo).
"""

import time

from queue_client import get_client, flush_all, enqueue, queue_depth, dlq_depth, replay_dlq
from producer import make_job, run_producer, CYCLE_VOLUMES
from worker_pool import run_dispatch_loop, run_dispatch_cycle


def scenario_backpressure_isolation():
    print("\n=== Scenario 1: backpressure isolation (no consumer running) ===")
    client = get_client()
    flush_all(client)

    latencies = []
    for i in range(500):
        job = make_job()
        latencies.append(enqueue(client, job) * 1000)

    avg = sum(latencies) / len(latencies)
    worst = max(latencies)
    print(f"Pushed 500 jobs with ZERO consumer running.")
    print(f"Avg enqueue latency: {avg:.3f}ms | worst: {worst:.3f}ms | final queue_depth={queue_depth(client)}")
    print("Producer never blocked despite queue never being drained — that's the isolation.")


def scenario_adaptive_dispatch():
    print("\n=== Scenario 2: adaptive dispatch against bursty load ===")
    client = get_client()
    flush_all(client)
    run_producer(cycles=CYCLE_VOLUMES, fail_rate=0.0)
    run_dispatch_loop(max_cycles=30)
    print(f"Final queue_depth={queue_depth(client)} (should be 0 — all jobs drained)")


def scenario_dlq_and_replay():
    print("\n=== Scenario 3: DLQ + replay ===")
    client = get_client()
    flush_all(client)

    # 30% of jobs are poisoned to always fail
    run_producer(cycles=[100], fail_rate=0.3)
    run_dispatch_loop(max_cycles=30)

    dlq_before = dlq_depth(client)
    print(f"Jobs landed in DLQ after exhausting retries: {dlq_before}")

    replayed = replay_dlq(client)
    print(f"Replayed {replayed} DLQ jobs back onto the main queue.")
    print(f"Queue depth after replay: {queue_depth(client)}")

    # Drain once more — these are still poisoned jobs, so they'll exhaust
    # retries and land back in the DLQ again, which is the correct,
    # honest outcome for an unrecoverable failure (replay retries, it
    # doesn't magically fix the underlying problem).
    run_dispatch_loop(max_cycles=30)
    print(f"DLQ depth after replay + redrain: {dlq_depth(client)} "
          f"(expected: same poisoned jobs land back here — replay proves the "
          f"recovery *mechanism* works, not that every failure is recoverable)")


if __name__ == "__main__":
    scenario_backpressure_isolation()
    scenario_adaptive_dispatch()
    scenario_dlq_and_replay()
