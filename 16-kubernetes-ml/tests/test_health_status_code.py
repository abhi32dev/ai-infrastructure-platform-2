"""Deterministic unit test of the actual bug found and fixed in this
project: /health must return a non-2xx HTTP status when unhealthy, not
just a JSON body saying so — because a Kubernetes httpGet probe only
inspects the status code. Tested directly against the app code (no
cluster, no Ollama, no kubectl) so it's fast and always runnable.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from starlette.testclient import TestClient
from app import app, breaker
from circuit_breaker import CLOSED, OPEN


def reset_breaker():
    breaker._state = CLOSED
    breaker._consecutive_failures = 0
    breaker._opened_at = None


def test_health_returns_200_when_closed():
    reset_breaker()
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["healthy"] is True


def test_health_returns_503_when_open():
    """The exact regression this project's real bug fix addresses —
    before the fix, this returned 200 even though healthy=false, which
    is invisible to a Kubernetes readiness probe."""
    reset_breaker()
    breaker._state = OPEN
    import time
    breaker._opened_at = time.time()
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 503
    assert r.json()["healthy"] is False
    reset_breaker()
