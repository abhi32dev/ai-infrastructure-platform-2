# 16 — Kubernetes for ML Workloads

Project 09's serving harness (FastAPI + circuit breaker, wrapping Ollama)
deployed as a real Kubernetes Deployment on a local `kind` cluster — with
a Service, an HPA, and liveness/readiness probes wired to its `/health`
endpoint — exercised with real failure injection (stopping the actual
downstream Ollama process, not a mock) to prove the probes actually
remove unhealthy pods from Service rotation.

## Maps to the market-gap research
- Single most-repeated keyword across every Staff/Principal posting
  searched: "Kubernetes internals," "GPU scheduling," named directly at
  NVIDIA, Tesla, Perplexity, Scale AI
- Directly extends the resume's existing CONDOR bullet — "a companion
  health-check endpoint... automatically pulls an unhealthy instance out
  of rotation" — from an AWS NLB target-group to the Kubernetes-native
  equivalent (readiness probes + Service endpoints)

## Setup

```bash
brew install kind          # Kubernetes-in-Docker, if not already installed
cd 16-kubernetes-ml
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

ollama pull llama3.2:1b
kind create cluster --config k8s/kind-config.yaml
docker build -t model-serving:local ./app
kind load docker-image model-serving:local --name ml-serving-demo
kubectl apply -f k8s/deployment.yaml
kubectl rollout status deployment/model-serving
```

## Run it

```bash
kubectl port-forward svc/model-serving 8080:80 &
curl localhost:8080/health
curl -X POST localhost:8080/generate -H 'content-type: application/json' -d '{"prompt": "hi"}'
```

## Two real bugs found and fixed by actually running this, not just writing YAML

### 1. `/health` always returned HTTP 200 — invisible to a Kubernetes probe

Project 09's original `/health` endpoint returned `{"healthy": false, ...}`
with an always-200 status code — correct for a caller that parses the
JSON body, but **a Kubernetes `httpGet` probe only inspects the HTTP
status code**, never the body. I proved this live: stopped the real
Ollama process, drove real failing traffic through the pods until their
circuit breakers tripped, and watched `kubectl get pods` still report
`ready=true` — because the probe saw a 200 no matter what the body said.

**Fix**: `/health` now returns `503` when `healthy=false`, `200`
otherwise (`app/app.py`). Re-ran the same failure injection after the fix
— the affected pod correctly flipped to `ready=false` and was removed
from `kubectl get endpoints model-serving` within one probe interval.

### 2. `HALF_OPEN` reads as "healthy" without ever re-testing the dependency

After fixing #1, a second, subtler issue surfaced during the same live
test: once the circuit breaker's `COOLDOWN_SECONDS` elapses, it
auto-transitions `OPEN → HALF_OPEN`, and `HALF_OPEN` is treated as
healthy (`state != OPEN`) so a *single* subsequent request can probe
whether the dependency recovered. But a Kubernetes readiness probe only
calls `/health` — it never calls `/generate`, so it never actually sends
that probe request. Result: with **no real traffic flowing**, a pod
whose downstream is still down will sit in `HALF_OPEN` indefinitely,
reading as `ready=true` to Kubernetes even though it cannot actually
serve a request. Confirmed live: after tripping the breaker and stopping
Ollama, waiting past the cooldown showed `kubectl get pods` reporting
`ready=true` again while Ollama was still down.

**Not fixed in this project, documented instead** — see "known
limitation" below for why, and what the real fix looks like.

## Tests

```bash
cd 16-kubernetes-ml && source .venv/bin/activate && pytest -q
```
6 tests, in two groups:
- **Live cluster tests (4)** — skip automatically if the kind cluster
  isn't up: deployment has 2 ready replicas, Service has endpoints for
  both, HPA is configured with the correct min/max/target, and both pods
  currently report a healthy `200` (safe to run repeatedly — doesn't
  touch the real Ollama process).
- **Deterministic unit tests (2)** — the actual regression guard for bug
  #1 above, tested directly against the app code via `TestClient` with a
  manually-set breaker state (no cluster, no Ollama, fast and always
  runnable in CI): `/health` returns `200` when `CLOSED`, `503` when
  `OPEN`.

## Teardown

```bash
kind delete cluster --name ml-serving-demo
```

## What to say in an interview

- **Why does bug #1 matter beyond "the test caught it"?** Because without
  it, this deployment would have looked completely healthy in
  `kubectl get pods` through a real, ongoing outage — the exact silent
  failure mode a health-check system exists to prevent. Finding it
  required actually running the failure, not just writing correct-looking
  YAML and trusting it.
- **Why leave bug #2 unfixed instead of also patching it?** Because the
  correct fix isn't a one-line change — it requires the `/health`
  endpoint itself to perform an active check against Ollama (not just
  report the passively-observed circuit state), which changes the
  performance/complexity tradeoff of a probe that's supposed to be cheap
  and called every few seconds. Documenting the gap precisely, with the
  live reproduction that found it, is more honest and more useful in an
  interview than quietly patching it and implying the first fix was the
  whole story.
- **What's the actual production fix for #2?** Make `/health` issue a
  short-timeout (e.g. 300ms) active ping to Ollama specifically when the
  breaker is `HALF_OPEN` (not on every call, to keep the probe cheap in
  the common `CLOSED` case), and let *that* result — not just elapsed
  cooldown time — decide whether to report healthy. This turns the
  readiness probe into the HALF_OPEN recovery test itself, closing the
  gap between "no traffic flowing" and "dependency actually recovered."
- **Why readiness AND liveness, with different thresholds
  (`failureThreshold: 2` vs `5`)?** Readiness controls Service traffic
  routing — it should react fast to a degraded downstream (2 failed
  probes). Liveness controls pod *restarts* — it should be much more
  conservative (5 failed probes), because restarting a pod whose only
  problem is a temporarily-down downstream dependency doesn't fix
  anything and just adds restart churn on top of an existing outage.
- **Why `host.docker.internal` for `OLLAMA_URL`?** Same reasoning as
  project 13's Prometheus scrape config: the pod runs inside a `kind`
  node's container, and `host.docker.internal` is Docker's standard way
  for a container to reach a service running directly on the Mac host —
  the model server itself doesn't need to be containerized for this demo
  to be real.
