"""Deterministic unit tests of the circuit breaker's state machine (no
HTTP, no Ollama needed, instant), plus a live integration test proving the
FastAPI app actually enforces it end to end against a real closed port.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from circuit_breaker import CircuitBreaker, CLOSED, OPEN, HALF_OPEN


def test_starts_closed():
    cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=5)
    assert cb.state == CLOSED
    assert cb.allow_request() is True


def test_opens_after_threshold_failures():
    cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=5)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CLOSED
    cb.record_failure()
    assert cb.state == OPEN
    assert cb.allow_request() is False


def test_success_resets_failure_count_and_closes():
    cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=5)
    cb.record_failure()
    cb.record_failure()
    cb.record_success()
    assert cb.state == CLOSED
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CLOSED  # only 2 consecutive since the reset, threshold not hit


def test_transitions_to_half_open_after_cooldown():
    cb = CircuitBreaker(failure_threshold=1, cooldown_seconds=0.2)
    cb.record_failure()
    assert cb.state == OPEN
    time.sleep(0.3)
    assert cb.state == HALF_OPEN
    assert cb.allow_request() is True


def test_half_open_failure_reopens_circuit():
    cb = CircuitBreaker(failure_threshold=1, cooldown_seconds=0.2)
    cb.record_failure()
    time.sleep(0.3)
    assert cb.state == HALF_OPEN
    cb.record_failure()
    assert cb.state == OPEN


def test_live_app_opens_circuit_on_real_connection_failure_and_fast_fails():
    from starlette.testclient import TestClient
    import config
    from app import app

    client = TestClient(app)
    config.OLLAMA_URL = "http://localhost:1"  # closed port

    for _ in range(config.FAILURE_THRESHOLD):
        client.post("/generate", json={"prompt": "hi"})

    health = client.get("/health").json()
    assert health["circuit_state"] == "OPEN"

    start = time.time()
    r = client.post("/generate", json={"prompt": "hi"})
    elapsed = time.time() - start

    assert r.status_code == 503
    assert elapsed < 1.0  # fast-fail, not a full downstream timeout
