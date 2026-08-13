# AI/ML Infrastructure Platform — Hands-On Portfolio

24 self-contained, hands-on projects built to demonstrate — with real
measured results, not slideware — the AI/ML infrastructure engineering
concepts referenced on a Staff/Principal AI Infrastructure resume, plus
the highest-frequency gaps found via a real job-market research pass
(NVIDIA, Tesla, Perplexity, Scale AI, Together AI postings + 2026
industry trend reports): RAG, multi-model evaluation gates, MLOps/CI
regression gating, cost-aware model routing, agent runtimes, distributed
backpressure/dispatch, statistical experimentation, recommendation
systems, resilient model serving, applied deep learning, the MCP agent
protocol, LLM guardrails, observability, cost optimization, distributed
training (DDP), Kubernetes for ML, high-performance inference serving,
QLoRA fine-tuning, quantization/ONNX, Terraform IaC, feature stores,
named LLM eval tools (Ragas/DeepEval), TensorFlow/Keras, and GPU FinOps.

See **[PROJECT_LIST.md](PROJECT_LIST.md)** for the full build tracker,
resume-claim cross-reference table, and repo conventions.

## Status

**All 24 projects complete, tested, and documented.** 175 tests total,
all passing, each suite explicitly split into positive-path,
negative/edge-case, and regression-guard categories. Every project also
has a **`PRODUCTION.md`** covering design tradeoffs, what's missing for
real production use, and scaling/security/operational readiness —
distinct from each `README.md`'s "what to say in an interview" framing.

## Projects

| # | Project | What it proves |
|---|---|---|
| 01 | [RAG-from-scratch pipeline](01-rag-pipeline/) | 7-stage RAG (ingest→chunk→embed→index→retrieve→assemble→generate), grounded refusal on out-of-corpus questions |
| 02 | [Multi-model LLM-as-judge gate](02-llm-eval-gate/) | Independent second model reviews every automation decision before it executes; v1→v2 prompt fix measured (0.33→0.83 agreement) |
| 03 | [MLflow versioning + CI regression gate](03-mlops-versioning-ci/) | Prompt/logic versions tracked in MLflow; CI blocks a measured regression |
| 04 | [Cost-aware retrieval & model router](04-cost-aware-router/) | 39.7% cost savings from routing; chunk-size/k cost-quality frontier |
| 05 | [Agent runtime (LangGraph)](05-agent-runtime/) | Checkpoint survives process restart, idempotent no-rerun, bounded retry, human-in-the-loop |
| 06 | [Backpressure-isolated ingestion + adaptive dispatch](06-backpressure-dispatch/) | Real Redis: 0.36ms enqueue latency under a 500-job burst with zero consumer; DLQ + replay |
| 07 | [A/B testing & p-value harness](07-ab-testing-harness/) | Correctly calls a 56%-looking lift "not significant" at small n; recovers a seeded 7.4% lift at scale |
| 08 | [Recommendation system](08-recommender-system/) | Matrix factorization from scratch on real MovieLens 100K, +30.19% precision@10 over baseline (p=0.0017) |
| 09 | [Local model serving harness](09-local-model-serving/) | Circuit breaker: 0.001s fast-fail vs. a 30s timeout, verified recovery |
| 10 | [Deep learning: detection & tracking](10-deep-learning-demo/) | Fine-tuned Faster R-CNN (mean IoU 0.875) on real pedestrian data; IoU multi-object tracker |
| 11 | [MCP agent-to-agent protocol](11-mcp-agent-protocol/) | Real MCP servers, tool discovery, and delegated agent-to-agent workflows |
| 12 | [Guardrails layer](12-guardrails/) | Prompt-injection detection, PII redaction, rate limiting — 100% red-team pass rate |
| 13 | [Observability](13-observability/) | OpenTelemetry tracing + Prometheus + Grafana, verified end-to-end scraping |
| 14 | [Cost optimization: caching & dashboard](14-cost-optimization/) | Semantic response cache with a real threshold-calibration story; 27% measured savings |
| 15 | [Distributed training (DDP)](15-distributed-training/) | Real torch.distributed: DDP ranks converge to exactly 0.0 weight distance vs. a diverging no-sync control |
| 16 | [Kubernetes for ML workloads](16-kubernetes-ml/) | Real kind cluster; found+fixed a real health-check bug via live outage injection |
| 17 | [High-performance inference serving](17-inference-serving/) | vLLM confirmed infeasible here (tested, not assumed) → llama.cpp; 2.09–2.27x continuous-batching speedup |
| 18 | [QLoRA fine-tuning](18-lora-finetuning/) | Verified real 4-bit quantization on Apple Silicon, correcting a "CUDA-only" assumption; 0.242% trainable params |
| 19 | [Quantization & ONNX export](19-quantization-onnx/) | Real MNIST CNN; a reproduced, counter-intuitive finding — INT8 was slower than fp32 here, not faster |
| 20 | [Terraform IaC](20-terraform-iac/) | S3/DynamoDB/SQS+DLQ against LocalStack, verified with real write/read round-trips, not just `apply` success |
| 21 | [Feature store (Feast)](21-feature-store/) | Proves point-in-time correctness with data built so "latest" and "as-of-X" provably differ |
| 22 | [Ragas & DeepEval](22-ragas-deepeval/) | Named eval-tool fluency; a real multi-hour dependency break diagnosed and pinned |
| 23 | [TensorFlow / Keras](23-tensorflow-keras/) | Direct framework comparison vs. project 19's PyTorch CNN; TFLite export, 100% prediction agreement |
| 24 | [GPU cost governance / FinOps](24-gpu-finops/) | Honest: simulated telemetry, real tested cost-governance engine — correctly isolated wasted spend to 1 of 4 instances |

## Repo conventions

- Every project is **fully isolated**: its own `.venv/`, own
  `requirements.txt`, own tests — never shares dependencies with another
  project.
- Every project runs **entirely locally**: Ollama for LLM inference,
  Docker for Redis/Prometheus/Grafana, SQLite/Chroma for storage. No
  cloud cost.
- Every project's `README.md` covers: what it does and which resume
  claim it maps to, exact setup/run commands, measured results from a
  real run, full test breakdown, and a "what to say in an interview"
  section for each non-obvious design decision.

## Quick start for any project

```bash
cd NN-project-name
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# see that project's README.md for any additional setup (Ollama models, Docker services)
pytest -q
```
