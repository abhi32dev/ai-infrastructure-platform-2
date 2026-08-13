# 04 — Cost-Aware Retrieval & Model Router

Two independent cost knobs, both measured with real numbers on real local
models, not simulated:

1. **Model routing** — a cheap classification call decides whether a query
   is SIMPLE (routes to a small, fast model) or COMPLEX (routes to a
   larger model), instead of sending every query to the expensive model.
2. **Chunk-size / retrieval-k sweep** — measures how retrieval quality and
   context token cost trade off as chunking and `k` change.

## Maps to resume claims
- "Cost-Aware Retrieval & Model Routing (Self-Directed)": tuned chunk
  size/prompt/context length/retrieval count to reduce token usage per
  query; applied model routing — simpler queries to a smaller/cheaper
  model, harder cases to a larger model

## Setup (isolated venv)

```bash
cd 04-cost-aware-router
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

ollama pull llama3.2:1b     # cheap path
ollama pull qwen2.5:3b      # expensive path
ollama pull nomic-embed-text
```

## Run it

```bash
source .venv/bin/activate
cd src

python router.py         # classify + route all 6 sample queries
python cost_report.py    # $ cost: cost-aware routing vs "always use the large model"
python chunk_sweep.py    # chunk_size x k grid: hit_rate vs avg_context_tokens
```

## Measured results

**Routing** (6 mixed simple/complex queries): classification accuracy
5/6 against hand-labeled expected tier. Cost comparison using an
illustrative $/1M-token rate card (small model $0.15/1M, large model
$2.50/1M — modeled on real small-vs-large hosted-model pricing tiers,
since Ollama itself is free/local):

| | Total cost (6 queries) |
|---|---|
| Cost-aware routing | $0.003867 |
| Always route to large model | $0.006410 |
| **Savings** | **39.7%** |

**Chunk-size / k sweep** (4 questions, deterministic keyword-match quality
proxy, real Chroma + Ollama embeddings):

| chunk_size | k | hit_rate | avg_context_tokens |
|---|---|---|---|
| 200 | 2 | 0.50 | 69.8 |
| 200 | 4 | 0.75 | 140.2 |
| 500 | 4 | 0.75 | 309.0 |
| 1000 | 4 | **1.00** | 623.2 |
| 1000 | 6 | 1.00 | 988.0 |

`chunk_size=1000, k=4` is the best hit-rate-per-token point on this small
corpus — going from `k=4` to `k=6` at the same chunk size adds ~365 tokens
per query for zero quality gain, a pure cost regression worth catching.

## Tests

```bash
cd 04-cost-aware-router && source .venv/bin/activate && pytest -q
```
5 tests: 3 deterministic (mocked classifier — routing logic and fail-safe
behavior), 2 live integration tests proving routing actually reduces cost
and larger chunks actually improve hit rate on this corpus.

## What to say in an interview

- **Why classify with the small model itself instead of a separate
  classifier?** The classification call is cheap regardless of which
  model does it (short prompt, short JSON output), so there's no cost
  reason to add a third model. Using the small model keeps the number of
  models in the system minimal — one fewer thing to version, evaluate, and
  keep available.
- **Fail-safe direction matters:** an unparsable/ambiguous classification
  routes to the *larger* model, not the cheaper one (see
  `test_unparsable_classification_fails_safe_to_complex`). The cost of
  a wrongly-expensive answer is a few cents; the cost of a wrongly-cheap
  answer on a genuinely hard query is a bad answer reaching the user. Same
  asymmetric-risk reasoning as project 02's AND-gate.
- **Why `k=4` and not `k=6` at large chunk size, even though hit_rate is
  tied at 1.00?** More retrieved context isn't free even when it doesn't
  hurt quality — every extra chunk is tokens paid for on every single
  query at production volume. Tuning against a hit_rate-per-token metric
  (not hit_rate alone) is what catches this; optimizing quality alone
  would have missed a 58% token increase for zero benefit.
- **Known limitation to volunteer:** the routing classification accuracy
  (5/6) has the same small-model-noise issue seen in project 02 — a 6-item
  hand-labeled set is enough to demonstrate the mechanism and catch a
  fail-safe direction bug, not to certify accuracy at scale. The
  dollar-cost figures are illustrative (mapped from a real small-vs-large
  pricing tier ratio) since local Ollama inference itself has no per-token
  API cost — the point being demonstrated is the *routing mechanism* and
  the *relative* savings ratio, which holds regardless of which specific
  rate card you plug in.
