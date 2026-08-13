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


# --- Negative / edge cases ---

def test_dequeue_from_empty_queue_returns_none_not_error():
    from queue_client import dequeue_blocking
    client = get_client()
    result = dequeue_blocking(client, timeout=1)
    assert result is None


def test_replay_on_empty_dlq_returns_zero():
    client = get_client()
    assert dlq_depth(client) == 0
    replayed = replay_dlq(client)
    assert replayed == 0


def test_dispatch_cycle_with_empty_queue_processes_nothing_without_error():
    from worker_pool import run_dispatch_cycle
    client = get_client()
    outcome = run_dispatch_cycle(client)
    assert outcome["processed"] == 0
    assert outcome["depth_seen"] == 0


def test_worker_count_at_exact_scale_divisor_boundaries():
    """Regression guard on the scaling formula's boundary behavior —
    SCALE_DIVISOR=25, so depth=24 and depth=25 should differ by exactly
    one worker (24//25=0 -> 1 worker; 25//25=1 -> 2 workers)."""
    from config import SCALE_DIVISOR
    assert desired_worker_count(SCALE_DIVISOR - 1) == desired_worker_count(0)
    assert desired_worker_count(SCALE_DIVISOR) == desired_worker_count(0) + 1


def test_successful_jobs_do_not_land_in_dlq():
    """Negative case for the DLQ tests above: a job that succeeds on the
    first attempt must never appear in the DLQ."""
    client = get_client()
    for _ in range(10):
        enqueue(client, make_job())  # force_fail defaults to False
    run_dispatch_loop(max_cycles=10)
    assert dlq_depth(client) == 0
    assert queue_depth(client) == 0
