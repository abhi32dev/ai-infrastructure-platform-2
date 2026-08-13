# 01 — RAG-from-Scratch Pipeline

A retrieval-augmented generation pipeline built stage-by-stage (not via a
single black-box `RetrievalQA` chain) so every step is inspectable and
independently runnable. Runs entirely locally against Ollama — no API keys,
no cloud cost.

## Maps to resume claims
- "Applied RAG & Vector Retrieval (Self-Directed)" — LangChain/LlamaIndex
  orchestration, document chunking, embedding generation, retrieval over a
  vector database
- "7 retrieval stages — ingestion, chunking, embedding, vector indexing,
  retrieval, context assembly, LLM response generation"

## Architecture

```
data/*.md --> ingest.py --> chunking.py --> embed_index.py --> Chroma (chroma_db/)
                                                                    |
                                                              retrieve.py
                                                                    |
                                                              generate.py --> Ollama (llama3.2:1b)
```

Each stage lives in its own file in `src/` and can be run standalone:

| Stage | File | What it does |
|---|---|---|
| 1. Ingestion | `ingest.py` | Loads raw docs from `data/` |
| 2. Chunking | `chunking.py` | Splits docs into overlapping windows (`RecursiveCharacterTextSplitter`) |
| 3+4. Embed + Index | `embed_index.py` | Embeds chunks with `nomic-embed-text`, writes to a persistent Chroma collection |
| 5. Retrieval | `retrieve.py` | Embeds the query, does similarity search, returns top-k chunks + distance scores |
| 6+7. Context assembly + Generation | `generate.py` | Builds a grounded prompt from retrieved chunks, calls `llama3.2:1b`, forces citation of source docs |
| End-to-end | `pipeline.py` | CLI that runs the whole thing |
| Service | `app.py` | FastAPI wrapper (`/query`, `/reindex`, `/health`) |

The sample corpus (`data/*.md`) is a small fictional "Aegis platform" doc
set — architecture overview, an incident postmortem, a deployment runbook,
and an on-call FAQ — deliberately shaped like the kind of internal docs a
platform team actually has, so retrieval quality is meaningfully testable
(there are near-duplicate topics across docs, e.g. rollback appears in both
the runbook and the FAQ).

## Setup

Requires [Ollama](https://ollama.com) running locally (installed via
`brew install ollama` / `brew services start ollama` for this project).

```bash
# from ai-infra-portfolio/
source .venv/bin/activate   # shared venv for the whole portfolio
ollama pull llama3.2:1b
ollama pull nomic-embed-text
```

## Run it

```bash
cd 01-rag-pipeline/src
python pipeline.py "What happens when an EC2 receiver fails health checks?"
python pipeline.py --rebuild "some question"   # force re-index
python pipeline.py --json "some question"      # full JSON incl. assembled context

# as a service
uvicorn app:app --reload --app-dir .
curl -X POST localhost:8000/query -H 'content-type: application/json' \
  -d '{"question": "Who approves a rollback?"}'
```

## Tests

```bash
cd 01-rag-pipeline
pytest -q
```

4 smoke tests: ingestion completeness, chunk-size bound, retrieval
relevance (correct doc ranks first), and generation grounding (model
refuses to answer an out-of-corpus question instead of hallucinating).

## What to say in an interview

- **Why stage-by-stage instead of one LangChain chain call?** Debuggability
  and tunability. When retrieval quality is bad, you need to know if it's a
  chunking problem, an embedding-model problem, or a prompt problem — a
  single chain call hides which stage is at fault. This structure lets you
  print/inspect the output of any one stage in isolation (that's why each
  file has a `__main__` block).
- **Chunk size/overlap tradeoff:** smaller chunks retrieve more precisely
  but multiply the number of embedding calls and can fragment context
  across a boundary; overlap (80 chars here) exists specifically so a
  sentence that spans a chunk boundary isn't orphaned on one side. This is
  the same knob project 04 (cost-aware router) tunes against token cost.
  Currently `CHUNK_SIZE=500`, `CHUNK_OVERLAP=80` — a starting point, not a
  tuned value.
- **Grounding / anti-hallucination:** the system prompt explicitly
  instructs the model to answer only from context and say so when it
  can't — verified by `test_generation_is_grounded_and_refuses_out_of_scope`.
  This is the same discipline behind the "multi-model evaluation gate"
  bullet (project 02): don't trust a single model's output uncritically.
  In this project the model self-reports its own uncertainty; project 02
  adds a second independent model checking the first.
  There is no independent judge here yet — that's project 02.
- **Why Chroma over a managed vector DB?** Zero infra to stand up, runs
  embedded in-process, persists to local disk — right choice for a
  portfolio/demo. In production at scale you'd swap in a managed
  vector store (pgvector, OpenSearch, Pinecone); the interface
  (`retrieve.py`'s `retrieve()` function) is what stays stable across that
  swap — same separation-of-concerns instinct as the resume's ingestion
  abstraction (two independent ingestion paths behind one downstream
  queue).
- **Known limitation to volunteer if asked:** retrieval is pure vector
  similarity, no hybrid BM25+embedding and no reranking yet — that's
  explicitly called out as a follow-up (theme A, project #3 in the master
  list) if the interviewer pushes on retrieval quality at scale.
