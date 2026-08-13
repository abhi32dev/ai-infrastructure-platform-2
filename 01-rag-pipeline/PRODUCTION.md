# Production Readiness — RAG-from-Scratch Pipeline

## Current state
Every stage (ingest, chunk, embed, index, retrieve, assemble, generate)
is implemented and independently testable. Grounding is enforced via
system prompt and verified by a test that the model refuses to answer
out-of-corpus questions. 9 tests cover positive path, negative/edge
cases, and regression guards (deterministic chunking, no verbatim-context
echo).

## Design decisions & trade-offs

| Decision | Why | Trade-off accepted |
|---|---|---|
| Chroma, not a managed vector DB | Zero infra, embedded in-process, free | Not built for >~1M vectors or multi-tenant isolation; would swap to pgvector/OpenSearch at scale |
| Fixed `CHUNK_SIZE=500`/`overlap=80` | Reasonable default, documented as tunable | Not tuned per-corpus; project 04 shows the actual tuning methodology |
| System-prompt-only grounding | Simple, testable, zero extra latency | No structural guarantee against hallucination — a determined adversarial prompt could still bypass it (see project 12's guardrails for that layer) |
| Stage-by-stage functions, not a single chain call | Debuggable — inspect any stage's output in isolation | More files/boilerplate than a one-liner `RetrievalQA.from_chain_type()` |

## What's missing for real production use
- **Hybrid retrieval** (BM25 + embeddings) and **reranking** — pure
  vector similarity only; no keyword-exact-match fallback for rare terms
  embeddings handle poorly (IDs, error codes, product SKUs)
- **Incremental indexing** — `build_index()` wipes and rebuilds the whole
  collection; a production system needs upsert/delete-by-doc-id
- **Retrieval caching** — every query re-embeds and re-searches, even for
  repeated/similar questions (project 14 solves this, not wired in here)
- **Multi-tenant document isolation** — no access-control layer; anyone
  querying can retrieve any indexed document

## Scaling considerations
- At 10x corpus size: Chroma still fine, chunk count and embedding-index
  build time grow linearly — acceptable
- At 100x-1000x: Chroma's single-process model becomes the bottleneck;
  needs a managed vector store with sharding (pgvector on RDS, OpenSearch,
  Pinecone) and a separate embedding-generation pipeline (batch, not
  inline with the query path)
- Retrieval latency at scale depends on ANN index type (HNSW vs flat) —
  not configured here; Chroma's default is adequate at this corpus size
  only

## Security & compliance considerations
- No PII redaction on ingested documents — project 12's guardrails layer
  covers this pattern but isn't wired into this pipeline's ingestion path
- No audit log of who queried what — would need per-request logging with
  user identity for compliance-sensitive deployments
- Corpus documents are trusted (loaded from a local directory); a
  production ingestion path from user uploads needs the injection
  defenses project 12 demonstrates, since document content flows directly
  into the LLM context window

## Operational readiness
- No metrics/tracing wired in — project 13 demonstrates the pattern
  (OpenTelemetry spans per stage, Prometheus counters) but this project
  doesn't consume it
- No health check endpoint beyond the FastAPI `/health` in `app.py`,
  which doesn't verify Ollama/Chroma reachability, only that the process
  is up
- Rebuilding the index (`/reindex`) blocks the process during rebuild —
  no blue-green index swap, so a rebuild causes a availability gap
