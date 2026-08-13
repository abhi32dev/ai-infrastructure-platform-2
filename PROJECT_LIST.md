# AI/ML Infrastructure Portfolio — Build Tracker

Purpose: hands-on, runnable-locally projects that map 1:1 to claims on the
Staff/Principal AI Infrastructure resume (Comcast CONDOR + Smith Micro +
IEEE/academic ML), so every resume line has a working demo behind it for
interview deep-dives. No cloud cost required — everything runs local
(Docker, Ollama, SQLite/local Postgres, LocalStack/Moto for AWS emulation).

Legend: `[ ]` not started · `[~]` in progress · `[x]` done

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

- [ ] **07 — A/B testing & p-value significance harness** (`07-ab-testing-harness/`)
  Maps to: "Statistically Validated Rollouts", "A/B testing & p-value
  significance testing" (both Comcast and Smith Micro bullets)
  Stack: Python, scipy.stats, applied to LLM/prompt output quality metrics

- [ ] **08 — Recommendation system with offline eval** (`08-recommender-system/`)
  Maps to: "Production Recommendation Systems" (Smith Micro, 7.4% revenue
  lift, validated via A/B + p-value)
  Stack: Python, implicit/collaborative filtering, MovieLens dataset,
  offline holdout eval

- [ ] **09 — Local model serving harness** (`09-local-model-serving/`)
  Maps to: "Ollama (local model serving/prototyping)", "prototypes changes
  locally with Ollama before promotion"
  Stack: Ollama, FastAPI wrapper, health checks (mirrors CONDOR's
  health-check-driven failover pattern)

- [ ] **10 — Deep learning / object detection demo** (`10-deep-learning-demo/`)
  Maps to: "Applied Deep Learning, Object Detection & Tracking (Coursework)",
  IEEE publication lifecycle (research → design → train → evaluate → deploy)
  Stack: PyTorch or TensorFlow, small pretrained detector fine-tuned on a
  small dataset

### Cross-cutting topics added on request (industry-standard AI platform concerns
not explicitly named on the resume, but expected knowledge at Staff level)

- [ ] **11 — MCP (Model Context Protocol) agent-to-agent demo** (`11-mcp-agent-protocol/`)
  What: a minimal MCP server exposing tools + an MCP client agent that
  discovers and calls them, plus a second agent-to-agent handoff (one agent
  delegates a subtask to another over MCP) — the emerging standard protocol
  for how agents expose capabilities to other agents/models, distinct from
  the ad-hoc tool-calling in project 05.
  Stack: Python `mcp` SDK, stdio/HTTP transport, LangChain MCP adapter

- [ ] **12 — Guardrails layer** (`12-guardrails/`)
  What: input guardrails (prompt-injection pattern detection, PII
  detection/redaction before a query reaches a model), output guardrails
  (schema/type validation, PII leak scanning, toxicity/refusal checks), and
  rate limiting — applied in front of project 01/02's pipelines as a
  reusable middleware layer, with a red-team test suite of adversarial
  inputs that must be caught.
  Stack: Python, regex/presidio-style PII patterns, pydantic schema
  validation, a small adversarial-prompt eval set

- [ ] **13 — Observability for AI systems** (`13-observability/`)
  What: OpenTelemetry tracing across a full RAG/agent request (retrieval
  span, generation span, tool-call spans), Prometheus metrics (request
  latency, token counts, error rate, judge agreement rate pulled from
  project 02/03), and a Grafana dashboard definition — the AI-specific
  extension of the resume's existing Prometheus/Grafana/OpenTelemetry line.
  Stack: OpenTelemetry SDK, Prometheus, Grafana (Docker Compose), applied
  to project 01's RAG pipeline as the traced system

- [ ] **14 — Cost optimization deep-dive: caching & dashboard** (`14-cost-optimization/`)
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
