# AI/ML Infrastructure Portfolio — Build Tracker

Purpose: hands-on, runnable-locally projects that map 1:1 to claims on the
Staff/Principal AI Infrastructure resume (Comcast CONDOR + Smith Micro +
IEEE/academic ML), so every resume line has a working demo behind it for
interview deep-dives. No cloud cost required — everything runs local
(Docker, Ollama, SQLite/local Postgres, LocalStack/Moto for AWS emulation).

Legend: `[ ]` not started · `[~]` in progress · `[x]` done

---

## Build order & status

- [x] **01 — RAG-from-scratch pipeline** (`01-rag-pipeline/`)
  Maps to: "Applied RAG & Vector Retrieval (Self-Directed)", "7 retrieval
  stages — ingestion, chunking, embedding, vector indexing, retrieval,
  context assembly, LLM response generation"
  Stack: Python, LangChain, Chroma (local vector DB), Ollama (local LLM)

- [ ] **02 — Multi-model evaluation gate (LLM-as-judge)** (`02-llm-eval-gate/`)
  Maps to: "Multi-Model Evaluation Gate", "Multi-Model AI Output Evaluation",
  CONDOR's "route each AI-generated decision through a second independent
  model before it acts"
  Stack: Python, two Ollama models (generator + judge), FastAPI gate service

- [ ] **03 — MLflow versioning + CI regression gate** (`03-mlops-versioning-ci/`)
  Maps to: "Automation Logic Version Tracking" (MLflow), "CI-Gated Automation
  Changes" (GitHub Actions blocking regressions)
  Stack: MLflow (local tracking server), GitHub Actions, pytest

- [ ] **04 — Cost-aware retrieval & model router** (`04-cost-aware-router/`)
  Maps to: "Cost-Aware Retrieval & Model Routing (Self-Directed)" — tuned
  chunk size/context length/retrieval count, routed simple queries to a
  smaller model
  Stack: Python, Ollama (small + large model), token-cost instrumentation

- [ ] **05 — Agent runtime with checkpointing & idempotency** (`05-agent-runtime/`)
  Maps to: "Self-Directed Agent Runtime" — durable state, checkpoints,
  bounded retries, idempotency, failure isolation, human-in-the-loop;
  also mirrors CONDOR's "Checkpointed Self-Healing" / "Master-Worker Dispatch"
  Stack: LangGraph, SQLite checkpoint store, tool/function calling

- [ ] **06 — Backpressure-isolated ingestion + adaptive dispatch** (`06-backpressure-dispatch/`)
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

---

## Repo conventions
- Each numbered folder is a **self-contained** project: own `README.md`,
  `requirements.txt`, source, tests, and a short "what this demonstrates /
  what to say in an interview" section.
- No secrets committed. `.env.example` only.
- Everything runs on a laptop. No paid cloud resources required.
- Local git now; GitHub remote to be added once user provides GitHub ID —
  will push each project as it's completed so local and GitHub stay in sync.
