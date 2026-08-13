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


def test_half_open_success_fully_resets_failure_count():
    """Boundary check: after a successful HALF_OPEN probe, a SUBSEQUENT
    single failure should not immediately reopen the circuit — proves
    record_success() resets the consecutive-failure counter to zero, not
    just the state label."""
    cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=0.2)
    cb.record_failure()
    assert cb.state == CLOSED  # 1 failure, threshold is 2
    cb.record_failure()
    assert cb.state == OPEN  # 2nd consecutive failure trips it
    time.sleep(0.3)
    assert cb.state == HALF_OPEN
    cb.record_success()
    assert cb.state == CLOSED
    cb.record_failure()  # only 1 consecutive failure since the reset
    assert cb.state == CLOSED


def test_snapshot_reports_zero_failures_when_healthy():
    cb = CircuitBreaker()
    snap = cb.snapshot()
    assert snap["state"] == CLOSED
    assert snap["consecutive_failures"] == 0


# --- Negative / edge cases: malformed requests ---

def test_malformed_request_missing_prompt_field_returns_422():
    from starlette.testclient import TestClient
    from app import app

    client = TestClient(app)
    r = client.post("/generate", json={"not_a_prompt_field": "hi"})
    assert r.status_code == 422  # FastAPI/pydantic validation error, not a 500


def test_health_endpoint_reports_healthy_before_any_requests():
    from starlette.testclient import TestClient
    from app import app, breaker

    # fresh breaker state for this isolated check
    breaker._consecutive_failures = 0
    breaker._state = CLOSED
    breaker._opened_at = None

    client = TestClient(app)
    health = client.get("/health").json()
    assert health["healthy"] is True
    assert health["circuit_state"] == "CLOSED"


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
