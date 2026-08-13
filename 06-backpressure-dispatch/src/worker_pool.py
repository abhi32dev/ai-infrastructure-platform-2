"""Adaptive master-worker dispatcher: each dispatch cycle checks current
queue depth and sizes a ThreadPoolExecutor worker batch accordingly,
instead of running a fixed-size pool sized for peak load — same pattern as
the resume's 'Master-Worker Dispatch' / 'Adaptive Workload Orchestration'
bullets, applied to an embedding/LLM-call queue instead of an S3 batch
manifest.

Each job simulates a slow, occasionally-failing downstream call (e.g. an
embedding API). Failures retry up to MAX_ATTEMPTS, tracked in a Redis hash
keyed by job_id (so attempt count survives a worker restart), then get
routed to the DLQ.
"""

import random
import time
from concurrent.futures import ThreadPoolExecutor

from config import MIN_WORKERS, MAX_WORKERS, SCALE_DIVISOR, MAX_ATTEMPTS
from queue_client import (
    get_client, dequeue_blocking, queue_depth,
    get_attempts, increment_attempts, clear_attempts, send_to_dlq, enqueue,
)


def desired_worker_count(depth: int) -> int:
    return max(MIN_WORKERS, min(MAX_WORKERS, (depth // SCALE_DIVISOR) + 1))


def process_job(client, job: dict, simulated_latency: float = 0.05) -> str:
    """Simulated downstream call. force_fail jobs always fail (for DLQ
    demo); other jobs succeed after `simulated_latency` seconds of 'work'."""
    time.sleep(simulated_latency)
    if job.get("force_fail"):
        raise RuntimeError("simulated downstream failure")
    return f"processed job_id={job['job_id']}"


def handle_one(client, job: dict) -> str:
    job_id = job["job_id"]
    try:
        result = process_job(client, job)
        clear_attempts(client, job_id)
        return result
    except Exception as e:
        attempts = increment_attempts(client, job_id)
        if attempts >= MAX_ATTEMPTS:
            send_to_dlq(client, job, reason=f"exceeded {MAX_ATTEMPTS} attempts: {e}")
            clear_attempts(client, job_id)
            return f"DLQ job_id={job_id} after {attempts} attempts"
        enqueue(client, job)  # bounded retry: push back for a later cycle to pick up
        return f"retry-scheduled job_id={job_id} attempt={attempts}"


def run_dispatch_cycle(client, max_jobs_this_cycle: int = 1000) -> dict:
    depth = queue_depth(client)
    worker_count = desired_worker_count(depth)

    jobs = []
    for _ in range(min(depth, max_jobs_this_cycle)):
        job = dequeue_blocking(client, timeout=1)
        if job is None:
            break
        jobs.append(job)

    if not jobs:
        return {"depth_seen": depth, "worker_count": worker_count, "processed": 0, "results": []}

    with ThreadPoolExecutor(max_workers=worker_count) as pool:
        results = list(pool.map(lambda j: handle_one(client, j), jobs))

    return {
        "depth_seen": depth,
        "worker_count": worker_count,
        "processed": len(jobs),
        "results": results,
    }


def run_dispatch_loop(max_cycles: int = 20, idle_stop_after: int = 2):
    client = get_client()
    idle_cycles = 0
    for cycle_num in range(1, max_cycles + 1):
        outcome = run_dispatch_cycle(client)
        if outcome["processed"] == 0:
            idle_cycles += 1
            if idle_cycles >= idle_stop_after:
                print(f"[dispatcher] idle for {idle_cycles} cycles, stopping.")
                break
            continue
        idle_cycles = 0

        dlq_count = sum(1 for r in outcome["results"] if r.startswith("DLQ"))
        retry_count = sum(1 for r in outcome["results"] if r.startswith("retry"))
        ok_count = outcome["processed"] - dlq_count - retry_count
        print(
            f"[dispatcher] cycle {cycle_num}: queue_depth_seen={outcome['depth_seen']} "
            f"-> spun up {outcome['worker_count']} workers, processed {outcome['processed']} "
            f"(ok={ok_count}, retry_scheduled={retry_count}, sent_to_dlq={dlq_count})"
        )


if __name__ == "__main__":
    run_dispatch_loop()
