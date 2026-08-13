"""Simulates bursty ingestion: volume per cycle swings across a wide range
(mirroring the resume's '~200x volume range' bullet), pushing embedding/
LLM-call jobs onto the queue. Enqueue latency is measured and printed so it
can be visibly compared against consumer processing latency — the producer
should stay fast (milliseconds) no matter how backed up the queue gets.
"""

import random
import time
import uuid

from queue_client import get_client, enqueue, queue_depth

# Deliberately wide swings, same spirit as the resume's 200x volume /
# 265,000x payload-size ranges — small on the local scale of this demo,
# but the same shape of variability.
CYCLE_VOLUMES = [5, 400, 20, 600, 10]


def make_job(payload_size_hint: str = "small") -> dict:
    return {
        "job_id": str(uuid.uuid4()),
        "payload_size_hint": payload_size_hint,
        "created_at": time.time(),
    }


def run_producer(cycles: list[int] = CYCLE_VOLUMES, fail_rate: float = 0.0):
    client = get_client()
    for cycle_num, volume in enumerate(cycles, start=1):
        cycle_start = time.time()
        enqueue_latencies = []
        for _ in range(volume):
            job = make_job()
            job["force_fail"] = random.random() < fail_rate
            latency = enqueue(client, job)
            enqueue_latencies.append(latency)

        cycle_duration = time.time() - cycle_start
        avg_latency_ms = (sum(enqueue_latencies) / len(enqueue_latencies)) * 1000
        depth = queue_depth(client)
        print(
            f"[producer] cycle {cycle_num}: pushed {volume} jobs in {cycle_duration:.3f}s "
            f"(avg enqueue latency {avg_latency_ms:.2f}ms) | queue_depth now={depth}"
        )


if __name__ == "__main__":
    from queue_client import flush_all
    flush_all(get_client())
    run_producer()
