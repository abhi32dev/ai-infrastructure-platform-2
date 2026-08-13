"""Live integration tests against the real local Redis (docker compose up
required — see README). No mocking: this project's entire point is real
queueing behavior under real concurrency.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pytest
from queue_client import get_client, flush_all, enqueue, queue_depth, dlq_depth, replay_dlq
from producer import make_job
from worker_pool import desired_worker_count, run_dispatch_loop
from config import MIN_WORKERS, MAX_WORKERS


@pytest.fixture(autouse=True)
def clean_queues():
    client = get_client()
    flush_all(client)
    yield
    flush_all(client)


def test_enqueue_latency_stays_low_under_deep_queue():
    client = get_client()
    latencies = [enqueue(client, make_job()) for _ in range(500)]
    assert max(latencies) < 0.05  # 50ms — generous bound for a local unconsumed queue
    assert queue_depth(client) == 500


def test_worker_count_scales_with_depth():
    assert desired_worker_count(0) == MIN_WORKERS
    assert desired_worker_count(1000) == MAX_WORKERS
    assert MIN_WORKERS <= desired_worker_count(50) <= MAX_WORKERS


def test_dispatch_drains_queue_fully():
    client = get_client()
    for _ in range(50):
        enqueue(client, make_job())
    run_dispatch_loop(max_cycles=10)
    assert queue_depth(client) == 0


def test_poisoned_jobs_reach_dlq_after_max_attempts():
    client = get_client()
    job = make_job()
    job["force_fail"] = True
    enqueue(client, job)
    run_dispatch_loop(max_cycles=10)
    assert queue_depth(client) == 0
    assert dlq_depth(client) == 1


def test_replay_moves_dlq_items_back_to_main_queue():
    client = get_client()
    job = make_job()
    job["force_fail"] = True
    enqueue(client, job)
    run_dispatch_loop(max_cycles=10)
    assert dlq_depth(client) == 1

    replayed = replay_dlq(client)
    assert replayed == 1
    assert dlq_depth(client) == 0
    assert queue_depth(client) == 1
