# 09 — Local Model Serving Harness

A FastAPI wrapper around Ollama with a circuit breaker gating every
inference call — the model-serving equivalent of the CONDOR platform's
"companion health-check endpoint... automatically pulls an unhealthy
instance out of rotation," scoped down to one process's connection to its
one downstream model server.

## Maps to resume claims
- "Ollama (local model serving/prototyping)"
- "prototypes changes locally with Ollama before promotion"
- Mirrors CONDOR's "Multi-AZ Fault Tolerance with Automated Failover" bullet
  at the single-service level: health checks driving automatic traffic
  routing decisions instead of manual on-call escalation

## Setup (isolated venv)

```bash
cd 09-local-model-serving
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

ollama pull llama3.2:1b
```

## Run it as a real service

```bash
source .venv/bin/activate
cd src
uvicorn app:app --reload

curl localhost:8000/health
curl -X POST localhost:8000/generate -H 'content-type: application/json' \
  -d '{"prompt": "Say hello in five words."}'
curl localhost:8000/metrics
```

## Run the circuit-breaker demo

```bash
source .venv/bin/activate
cd src
python run_demo.py
```

Three scenarios, run in-process against real Ollama + a real closed TCP
port (no mocking):

1. **Healthy baseline** — a real `/generate` call succeeds against the
   real local Ollama.
2. **Downstream failure trips the circuit** — `config.OLLAMA_URL` is
   pointed at a closed port. After `FAILURE_THRESHOLD=3` consecutive
   connection failures, the circuit opens; the next request fast-fails
   with `503` instead of waiting out a connection timeout.
3. **Recovery after cooldown** — after `COOLDOWN_SECONDS=5`, the circuit
   moves to `HALF_OPEN`; the URL is restored to the real Ollama; the next
   probe request succeeds and the circuit closes.

## Measured results (this run)

| Step | Result |
|---|---|
| Healthy call | 200, 3.23s latency |
| Failures 1-2 | 502, circuit stays CLOSED |
| Failure 3 | 502, circuit trips to OPEN |
| Request while OPEN | **503 in 0.001s** (vs. a multi-second connection timeout otherwise) |
| After cooldown, probe request | 200, circuit closes |

## Tests

```bash
cd 09-local-model-serving && source .venv/bin/activate && pytest -q
```
6 tests: 5 deterministic circuit-breaker state-machine tests (no HTTP) +
1 live integration test proving the FastAPI app enforces the breaker
end-to-end against a real closed port, with a hard assertion that the
open-circuit rejection takes under 1 second.

## What to say in an interview

- **Why does the fast-fail matter, not just "it eventually returns an
  error"?** Without the breaker, every request during an outage pays the
  full connection/read timeout (`REQUEST_TIMEOUT_SECONDS=30` here) before
  failing — under concurrent load that ties up worker threads/connections
  for the full timeout duration, potentially cascading into a broader
  outage (thread pool exhaustion) instead of a contained, fast, cheap
  failure. The measured 0.001s open-circuit rejection versus a 30s
  timeout is the entire point.
- **Why 3 consecutive failures, not 1?** A single failed request could be
  a one-off blip (packet loss, GC pause). Requiring consecutive failures
  before opening avoids tripping the breaker on noise, while still
  reacting fast to a genuine outage — the same tradeoff CONDOR's
  target-health check interval encodes (a few consecutive failed checks,
  not one, before pulling an instance from rotation).
- **Why HALF_OPEN instead of just closing immediately after the
  cooldown?** Immediately resuming full traffic to a downstream that might
  still be recovering risks re-tripping the breaker under load right as it
  comes back. A single probe request first is a much cheaper way to find
  out "is it actually back" before committing full traffic to it.
- **Known limitation to volunteer:** this breaker is process-local,
  in-memory state — if you ran multiple instances of this service behind
  a load balancer, each would trip its own breaker independently instead
  of sharing state, which is actually fine here (that's exactly what you
  want per-instance for a downstream-connection breaker) but would be the
  wrong choice for a breaker meant to represent fleet-wide consensus,
  which would need a shared store (Redis, same as project 06) instead.
