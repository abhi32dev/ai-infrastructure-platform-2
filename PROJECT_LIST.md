# AI/ML Infrastructure Portfolio — Build Tracker

Purpose: hands-on, runnable-locally projects that map 1:1 to claims on the
Staff/Principal AI Infrastructure resume (Comcast CONDOR + Smith Micro +
IEEE/academic ML), so every resume line has a working demo behind it for
interview deep-dives. No cloud cost required — everything runs local
(Docker, Ollama, SQLite/local Postgres, LocalStack/Moto for AWS emulation).

Legend: `[ ]` not started · `[~]` in progress · `[x]` done

## Status: all 14 projects complete, tested, documented

**131 tests total across all 14 projects, all passing.** Every project's
test suite is explicitly split into three categories — check each
project's README "Tests" section for the exact breakdown:
- **Positive path** — the feature works as intended under normal input
- **Negative / edge cases** — empty input, malformed input, boundary
  values, unknown/missing IDs, zero-division-prone arithmetic — proven
  not to crash or silently misbehave
- **Regression guards** — a specific past bug, calibration finding, or
  subtle correctness property (determinism, off-by-one boundaries,
  symmetry, fail-safe direction) pinned down so a future change can't
  silently reintroduce it

Every project folder contains a `README.md` covering: what it demonstrates
and which resume claim it maps to, exact setup/run commands, measured
results from a real run (not hypothetical numbers), the full test
breakdown above, and a "what to say in an interview" section for each
non-obvious design decision.

## Phase 2: market-gap projects (15–24)

Added 2026-08-13 after a real web-search pass (not guessed) across current
Staff/Principal AI Infrastructure job postings (NVIDIA, Tesla, Perplexity,
Scale AI, Together AI) and 2026 industry hiring-trend reports, to close the
highest-frequency gaps between what's already built (01–14) and what these
postings actually ask for. Ranked by how often each theme appeared.
Sources are cited in the session this analysis came from.

- [x] **15 — Distributed training fundamentals (DDP)** (`15-distributed-training/`) — has its own `.venv/`. Real torch.distributed (gloo), 4 local ranks. Measured: DDP ranks converge to exactly 0.0 L2 weight distance; no-sync control diverges to 0.3655.
  Gap: "distributed training at scale... PyTorch DDP, FSDP" — named at
  NVIDIA, Tesla, Perplexity, Scale AI explicitly.
  Honest scope: no real multi-GPU cluster available. Demonstrates the
  actual DDP protocol (process groups, gradient all-reduce, rank sync)
  via `torch.distributed` with the `gloo` CPU backend across multiple
  local processes — the same protocol that runs unchanged on real GPUs
  with the `nccl` backend, only the backend name and device placement
  change at real scale.

- [ ] **16 — Kubernetes for ML workloads** (`16-kubernetes-ml/`)
  Gap: single most-repeated keyword across every posting searched
  ("Kubernetes internals," "GPU scheduling," named at NVIDIA/Tesla/
  Perplexity/Scale AI).
  Stack: `kind` (Kubernetes-in-Docker, already have Docker), deploying
  project 09's serving harness as a real Deployment + Service + HPA +
  liveness/readiness probes wired to its existing `/health` endpoint.

- [ ] **17 — High-performance LLM inference serving** (`17-inference-serving/`)
  Gap: "2026 primary focus is on inference: latency-per-token, throughput,
  p99 latency" — vLLM/TensorRT-LLM/SGLang/Triton named directly.
  Feasibility to verify: vLLM targets NVIDIA CUDA primarily; Apple
  Silicon support is limited/experimental. Will test directly and
  document honestly — likely substitutes llama.cpp's server (real
  continuous-batching/paged-KV-cache equivalent that runs natively on
  Apple Silicon) if vLLM itself doesn't run, benchmarked against
  project 09's Ollama baseline.

- [ ] **18 — LoRA/QLoRA fine-tuning** (`18-lora-finetuning/`)
  Gap: "the biggest shift in 2026... PEFT... QLoRA + instruction tuning
  is the practical path" — dominant, explicitly named technique.
  Feasibility to verify: QLoRA's 4-bit quantization (bitsandbytes) is
  traditionally CUDA-only. Will test on MPS/CPU and document honestly —
  likely full-precision LoRA via Hugging Face `peft` on a small causal
  LM, with the QLoRA quantization gap stated explicitly rather than
  faked.

- [ ] **19 — Model quantization & ONNX export** (`19-quantization-onnx/`)
  Gap: "model optimization" named alongside fine-tuning in postings.
  Stack: export project 10's or 18's model to ONNX, apply
  dynamic/static quantization, measure size/latency deltas.

- [ ] **20 — Terraform IaC module** (`20-terraform-iac/`)
  Gap: Terraform named in nearly every ML platform posting; resume's
  existing IaC story is AWS CDK only — a second IaC tool demonstrates
  breadth.
  Stack: Terraform against LocalStack (same free/local pattern as the
  resume's Moto/LocalStack CCPA-service testing).

- [ ] **21 — Feature store** (`21-feature-store/`)
  Gap: named explicitly as a core storage-layer component of the "AI
  infra stack" alongside vector DBs and data lakes.
  Stack: Feast, backed by local Postgres/Redis (reusing project 06's
  Redis).

- [ ] **22 — Named LLM eval tools (Ragas / DeepEval)** (`22-ragas-deepeval/`)
  Gap: projects 02/03 built a from-scratch evaluation gate (strong
  engineering signal) but don't demonstrate fluency with the specific
  named tools interviewers ask about.
  Stack: wraps project 01's RAG pipeline with both Ragas and DeepEval,
  compared side by side.

- [ ] **23 — TensorFlow / Keras project** (`23-tensorflow-keras/`)
  Gap: the user's own question — confirmed real gap. ~33% of postings
  still name TensorFlow; dominant for edge/enterprise/mobile deployment.
  Stack: a Keras model (likely a lightweight image classifier or the
  project-08-style recommender re-implemented in Keras) to show
  cross-framework fluency, not just PyTorch.

- [ ] **24 — GPU cost governance / FinOps dashboard** (`24-gpu-finops/`)
  Gap: "tracking GPU utilization... strict cost controls" named as a
  core 2026 responsibility, distinct from project 14's LLM-token cost
  focus.
  Stack: extends project 14's ledger/dashboard pattern to simulated
  GPU-hour utilization and idle-cost tracking.

---

## Build order & status

- [x] **01 — RAG-from-scratch pipeline** (`01-rag-pipeline/`) — has its own `.venv/`
  Maps to: "Applied RAG & Vector Retrieval (Self-Directed)", "7 retrieval
  stages — ingestion, chunking, embedding, vector indexing, retrieval,
  context assembly, LLM response generation"
  Stack: Python, LangChain, Chroma (local vector DB), Ollama (local LLM)

- [x] **02 — Multi-model evaluation gate (LLM-as-judge)** (`02-llm-eval-gate/`) — has its own `.venv/`
  Maps to: "Multi-Model Evaluation Gate", "Multi-Model AI Output Evaluation",
  CONDOR's "route each AI-generated decision through a second independent
  model before it acts"
  Stack: Python, two Ollama models (generator + judge), FastAPI gate service

- [x] **03 — MLflow versioning + CI regression gate** (`03-mlops-versioning-ci/`) — has its own `.venv/`. Measured: v1 prompt 0.33 agreement vs v2 0.83 agreement, gate verified to block regressions.
  Maps to: "Automation Logic Version Tracking" (MLflow), "CI-Gated Automation
  Changes" (GitHub Actions blocking regressions)
  Stack: MLflow (local tracking server), GitHub Actions, pytest

- [x] **04 — Cost-aware retrieval & model router** (`04-cost-aware-router/`) — has its own `.venv/`. Measured: 39.7% cost savings from routing, chunk_size=1000/k=4 best hit-rate-per-token.
  Maps to: "Cost-Aware Retrieval & Model Routing (Self-Directed)" — tuned
  chunk size/context length/retrieval count, routed simple queries to a
  smaller model
  Stack: Python, Ollama (small + large model), token-cost instrumentation

- [x] **05 — Agent runtime with checkpointing & idempotency** (`05-agent-runtime/`) — has its own `.venv/`. LangGraph + SQLite checkpointer; verified checkpoint-survives-restart, idempotent no-rerun, bounded retry, human-in-the-loop interrupt/resume, all with passing tests.
  Maps to: "Self-Directed Agent Runtime" — durable state, checkpoints,
  bounded retries, idempotency, failure isolation, human-in-the-loop;
  also mirrors CONDOR's "Checkpointed Self-Healing" / "Master-Worker Dispatch"
  Stack: LangGraph, SQLite checkpoint store, tool/function calling

- [x] **06 — Backpressure-isolated ingestion + adaptive dispatch** (`06-backpressure-dispatch/`) — has its own `.venv/` + docker-compose Redis. Measured: 0.36ms avg enqueue latency under 500-job burst w/ zero consumer, worker scaling 8→2 with depth, DLQ+replay verified.
  Maps to: CONDOR's "Backpressure Isolation" (SQS), "Adaptive Workload
  Orchestration" (200x volume / 265,000x payload swings), "Master-Worker
  Dispatch", "Dead-letter queue" recovery — reframed around an
  embedding/LLM-call pipeline
  Stack: Docker Redis (queue), Python worker pool, LocalStack SQS optional

- [x] **07 — A/B testing & p-value significance harness** (`07-ab-testing-harness/`) — has its own `.venv/`. Measured: synthetic recommender A/B recovers 7.4%-scale lift at p=0.00002 (n=50K/arm); live latency A/B correctly finds a 56%-looking lift NOT significant at n=8.
  Maps to: "Statistically Validated Rollouts", "A/B testing & p-value
  significance testing" (both Comcast and Smith Micro bullets)
  Stack: Python, scipy.stats, applied to LLM/prompt output quality metrics

- [x] **08 — Recommendation system with offline eval** (`08-recommender-system/`) — has its own `.venv/`. Real MovieLens 100K: RMSE 0.9431, MF beats popularity baseline by +30.19% precision@10 (p=0.0017).
  Maps to: "Production Recommendation Systems" (Smith Micro, 7.4% revenue
  lift, validated via A/B + p-value)
  Stack: Python, implicit/collaborative filtering, MovieLens dataset,
  offline holdout eval

- [x] **09 — Local model serving harness** (`09-local-model-serving/`) — has its own `.venv/`. Circuit breaker verified: opens after 3 failures, fast-fails in 0.001s (vs 30s timeout), recovers via HALF_OPEN after cooldown.
  Maps to: "Ollama (local model serving/prototyping)", "prototypes changes
  locally with Ollama before promotion"
  Stack: Ollama, FastAPI wrapper, health checks (mirrors CONDOR's
  health-check-driven failover pattern)

- [x] **10 — Deep learning / object detection demo** (`10-deep-learning-demo/`) — has its own `.venv/`. Fine-tuned Faster R-CNN on real PennFudan pedestrian data: mean IoU 0.875 on held-out set; found+fixed a real MPS NaN-loss bug (forced CPU); IoU tracker verified persistent IDs + false-positive isolation.

### Cross-cutting topics added on request (industry-standard AI platform concerns
not explicitly named on the resume, but expected knowledge at Staff level)

- [x] **11 — MCP (Model Context Protocol) agent-to-agent demo** (`11-mcp-agent-protocol/`) — has its own `.venv/`. Verified: tool discovery over stdio, coordinator hides specialist entirely, full delegated remediation trace with correct state persistence.
  What: a minimal MCP server exposing tools + an MCP client agent that
  discovers and calls them, plus a second agent-to-agent handoff (one agent
  delegates a subtask to another over MCP) — the emerging standard protocol
  for how agents expose capabilities to other agents/models, distinct from
  the ad-hoc tool-calling in project 05.
  Stack: Python `mcp` SDK, stdio/HTTP transport, LangChain MCP adapter

- [x] **12 — Guardrails layer** (`12-guardrails/`) — has its own `.venv/`. Red-team suite: 100% pass rate (8/8): 4/4 injections blocked, 2/2 PII cases correctly redacted, 2/2 benign allowed.
  What: input guardrails (prompt-injection pattern detection, PII
  detection/redaction before a query reaches a model), output guardrails
  (schema/type validation, PII leak scanning, toxicity/refusal checks), and
  rate limiting — applied in front of project 01/02's pipelines as a
  reusable middleware layer, with a red-team test suite of adversarial
  inputs that must be caught.
  Stack: Python, regex/presidio-style PII patterns, pydantic schema
  validation, a small adversarial-prompt eval set

- [x] **13 — Observability for AI systems** (`13-observability/`) — has its own `.venv/` + docker-compose (Prometheus+Grafana). Verified: Prometheus target "up", real query counts scraped, provisioned Grafana dashboard, correct span parent/child linkage.
  What: OpenTelemetry tracing across a full RAG/agent request (retrieval
  span, generation span, tool-call spans), Prometheus metrics (request
  latency, token counts, error rate, judge agreement rate pulled from
  project 02/03), and a Grafana dashboard definition — the AI-specific
  extension of the resume's existing Prometheus/Grafana/OpenTelemetry line.
  Stack: OpenTelemetry SDK, Prometheus, Grafana (Docker Compose), applied
  to project 01's RAG pipeline as the traced system

- [x] **14 — Cost optimization deep-dive: caching & dashboard** (`14-cost-optimization/`) — has its own `.venv/`. Real calibration finding (0.92 guess -> 0 hits; recalibrated to 0.75 from measured similarities). 27% cost savings measured, HTML dashboard verified rendering.
  What: extends project 04 with a semantic response cache (skip the LLM
  call entirely for a near-duplicate query), a request-level cost ledger,
  and a small dashboard visualizing spend by model/query-type over time —
  the operational layer on top of project 04's one-shot routing
  measurement.
  Stack: Python, an embedding-similarity cache (reuses project 01's Chroma
  pattern), SQLite cost ledger, a simple HTML/artifact dashboard

---

## Resume-claim → project cross-reference

| Resume phrase | Project(s) |
|---|---|
| RAG / vector retrieval / chunking & embedding | 01 |
| Multi-model evaluation / LLM-as-judge | 02 |
| MLflow config/version tracking | 03 |
| CI-gated automation changes | 03 |
| Cost-aware retrieval & model routing | 04 |
| Agentic workflows / tool calling / human-in-the-loop | 05 |
| Checkpointed self-healing / master-worker dispatch | 05, 06 |
| Backpressure isolation (SQS) | 06 |
| Adaptive workload orchestration (200x/265,000x swings) | 06 |
| Dead-letter queue / recoverable delivery | 06 |
| A/B testing & p-value significance testing | 07, 08 |
| Production recommendation systems | 08 |
| Ollama local prototyping | 01, 04, 09 |
| Deep learning / object detection (TensorFlow) | 10 |
| IEEE ML lifecycle (research→deploy) | 10 |
| MCP / agent-to-agent protocol | 11 |
| Guardrails (prompt injection, PII, output validation) | 12 |
| Evaluation sets & regression testing | 02, 03, 12 |
| Observability (tracing/metrics/dashboards) for AI systems | 13 |
| Cost optimization beyond one-shot routing (caching, ledger) | 04, 14 |

---

## Repo conventions
- Each numbered folder is a **fully isolated, self-contained** project: its
  own `.venv/` (never shared across projects), own `requirements.txt`,
  source, tests, and a short "what this demonstrates / what to say in an
  interview" section. Working on/rebuilding one project's venv never
  touches or breaks another project's venv or dependencies.
- To run any project: `cd NN-project-name && source .venv/bin/activate`
  (first time: `python3 -m venv .venv && pip install -r requirements.txt`).
- No secrets committed. `.env.example` only.
- Everything runs on a laptop. No paid cloud resources required.
- Shared local infra (Ollama models) lives outside any single project's
  venv (`ollama pull <model>` is global, not per-project) — each project's
  README lists which Ollama models it needs.
- Local git now; GitHub remote to be added once user provides GitHub ID —
  will push each project as it's completed so local and GitHub stay in sync.
