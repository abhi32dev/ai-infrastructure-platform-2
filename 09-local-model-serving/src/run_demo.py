"""Runs three scenarios against the app in-process (via Starlette's
TestClient, which makes real outbound HTTP calls for /generate — no mock):

1. Healthy baseline: real calls to the real local Ollama succeed.
2. Downstream failure -> circuit opens: point config.OLLAMA_URL at a
   closed port, send requests, watch the circuit trip after
   FAILURE_THRESHOLD failures and then fast-fail (503) instead of hanging.
3. Recovery: after COOLDOWN_SECONDS, restore the real Ollama URL and show
   the circuit moves to HALF_OPEN, the next request succeeds, and the
   circuit closes again.
"""

import time
from starlette.testclient import TestClient

import config
from app import app, breaker

client = TestClient(app)


def scenario_healthy_baseline():
    print("\n=== Scenario 1: healthy baseline (real Ollama) ===")
    r = client.get("/health")
    print("health:", r.json())
    r = client.post("/generate", json={"prompt": "Say OK and nothing else."})
    print("generate status:", r.status_code, "| latency:", round(r.json()["latency_sec"], 3), "s")


def scenario_downstream_failure_opens_circuit():
    print("\n=== Scenario 2: downstream failure trips the circuit ===")
    original_url = config.OLLAMA_URL
    config.OLLAMA_URL = "http://localhost:1"  # closed port, connection refused

    for i in range(1, 5):
        r = client.post("/generate", json={"prompt": "hi"})
        health = client.get("/health").json()
        print(f"  attempt {i}: status={r.status_code} circuit_state={health['circuit_state']} "
              f"consecutive_failures={health['consecutive_failures']}")

    health = client.get("/health").json()
    print(f"Circuit is now: {health['circuit_state']} (healthy={health['healthy']})")
    assert health["circuit_state"] == "OPEN"

    print("  probing again while OPEN — should fast-fail with 503, no hang:")
    start = time.time()
    r = client.post("/generate", json={"prompt": "hi"})
    print(f"  status={r.status_code} elapsed={time.time()-start:.3f}s (fast-fail, no downstream timeout wait)")

    config.OLLAMA_URL = original_url


def scenario_recovery_after_cooldown():
    print(f"\n=== Scenario 3: recovery after cooldown ({config.COOLDOWN_SECONDS}s) ===")
    print("  waiting for cooldown to elapse...")
    time.sleep(config.COOLDOWN_SECONDS + 1)

    health = client.get("/health").json()
    print(f"  circuit state after cooldown elapsed: {health['circuit_state']} (should be HALF_OPEN)")

    r = client.post("/generate", json={"prompt": "Say OK and nothing else."})
    health = client.get("/health").json()
    print(f"  probe request status={r.status_code} -> circuit now: {health['circuit_state']} (should be CLOSED)")


if __name__ == "__main__":
    scenario_healthy_baseline()
    scenario_downstream_failure_opens_circuit()
    scenario_recovery_after_cooldown()
    print("\nFinal metrics:", client.get("/metrics").json())
