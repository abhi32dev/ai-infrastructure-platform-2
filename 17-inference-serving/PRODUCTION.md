# Production Readiness — High-Performance LLM Inference Serving

## Current state
llama.cpp's `llama-server` (honest vLLM substitution, documented and
justified) with continuous batching. Measured 2.09x-2.27x throughput
speedup across clean runs; found and fixed a real test-methodology
flakiness bug (server-lifecycle contention). 2 tests, deliberately
structured as exactly 2 sequential server lifecycles.

## Design decisions & trade-offs

| Decision | Why | Trade-off accepted |
|---|---|---|
| llama.cpp, not vLLM | vLLM targets CUDA; confirmed infeasible on this Apple Silicon hardware (3-minute unresolved pip install) | The specific 2x speedup number doesn't transfer to a real vLLM/GPU deployment — the *mechanism* (continuous batching helps) generalizes, the number doesn't |
| 0.5B-parameter model | Fast enough for CPU inference in a reasonable demo time | Real production inference-serving decisions are made at 7B-70B+ scale, where memory bandwidth and KV-cache management matter far more than at this scale |
| `--parallel N` as the only variable tested | Isolates continuous batching as the cause of the measured speedup | Doesn't explore other serving-engine parameters (context length, batch size limits, quantization level) that also affect throughput |

## What's missing for real production use
- **Real GPU-backed serving engine validation** — this proves the
  continuous-batching mechanism and measurement methodology; a real
  production decision needs the same benchmark re-run against actual
  vLLM/TensorRT-LLM on real GPU hardware
- **Load testing at realistic concurrency** — 8 concurrent requests is
  enough to demonstrate the effect; production capacity planning needs
  testing at the actual expected peak concurrency, likely much higher
- **Streaming response support** — this benchmarks complete-response
  latency; most production chat/completion APIs stream tokens, which
  changes the relevant latency metric (time-to-first-token vs. total
  completion time)
- **Multi-model serving** — this serves one model; a production inference
  platform often needs to serve multiple models/model-versions from the
  same infrastructure with request routing

## Scaling considerations
- The measurement methodology (isolate the serving-concurrency variable,
  run clean trials, verify reproducibility) transfers directly to a real
  GPU deployment
- Real scaling would also need to account for KV-cache memory pressure
  under high concurrency — not a meaningful constraint at this demo's
  0.5B model scale, but the dominant scaling concern at 7B+ scale

## Security & compliance considerations
- `llama-server` binds to localhost only in this demo — a production
  deployment needs authentication, TLS, and network isolation for any
  externally-reachable inference endpoint
- No input validation/guardrails (project 12's layer) wired into this
  serving harness

## Operational readiness
- No metrics export from the serving engine itself — a production
  deployment needs per-request latency/token-count metrics feeding the
  observability stack (project 13's pattern)
- No graceful model reload/version-swap capability demonstrated — a
  production inference service needs to update the served model without
  downtime
