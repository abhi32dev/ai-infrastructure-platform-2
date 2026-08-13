# 14 — Cost Optimization: Semantic Caching, Cost Ledger & Dashboard

Extends project 04's one-shot routing measurement with the operational
layer: a semantic (embedding-similarity) response cache that skips the
LLM call entirely for near-duplicate queries, a durable SQLite cost
ledger, and a self-contained HTML dashboard generated from it.

## Maps to the request
- "Cost optimization" as an ongoing operational concern, not just a
  one-time routing decision (project 04) — caching, a persistent spend
  ledger, and a visual dashboard

## Setup (isolated venv)

```bash
cd 14-cost-optimization
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

ollama pull llama3.2:1b
ollama pull nomic-embed-text
```

## Run it

```bash
source .venv/bin/activate
cd src

python run_demo.py    # 8-query stream with paraphrased near-duplicates
python dashboard.py   # generates ../dashboard.html from the ledger
```
Open `dashboard.html` directly in a browser — no server needed.

## A real calibration finding, not a guessed threshold

My first pass used `SIMILARITY_THRESHOLD = 0.92` (a plausible-sounding
guess) and got **zero cache hits** across 3 paraphrased query pairs that
should obviously match. Rather than silently lowering the threshold until
something worked, I measured actual cosine similarities from
`nomic-embed-text` directly:

| Pair | Cosine similarity |
|---|---|
| Close paraphrase ("fails health check" vs "fails its health check") | **0.790** |
| Looser paraphrase ("EC2 receiver fails" vs "load balancer handle unhealthy") | 0.567 |
| Unrelated query | 0.474 |

`nomic-embed-text`'s raw query-embedding similarities run much lower than
a naive intuition would suggest — 0.92 was never achievable for this
model on short sentences. Recalibrated to `0.75`: sits just below the
close-paraphrase score with margin above the unrelated-query score. This
is a **stated, deliberate tradeoff**: it catches near-identical
rephrasings, not loose paraphrases — a higher-recall cache would need a
lower threshold at the cost of more false-positive cache hits (returning
a stale/wrong cached answer for a genuinely different question).

## Measured results (this run, 8-query stream)

| | |
|---|---|
| Total requests | 8 |
| Cache hits | **2** (both close paraphrases, correctly matched) |
| Cache hit rate | 25.0% |
| Actual cost | $0.000299 |
| Would-be cost (no cache) | $0.000410 |
| **Savings** | **27.0%** |

The 2 hits correctly matched their close paraphrase ("failed health
check" ↔ "instance fails its health check", similarity 0.790; "who
approves a rollback" ↔ "who signs off on rolling back", similarity 0.788)
— the 2 looser paraphrases in the stream correctly stayed cache misses,
exactly the calibrated behavior above.

## Tests

```bash
cd 14-cost-optimization && source .venv/bin/activate && pytest -q
```
5 tests: cosine-similarity math (identical/orthogonal vectors), ledger
summary arithmetic (hit rate, savings) including the empty-ledger edge
case (no division-by-zero), and one live test proving the real embedding
model hits on a close paraphrase and correctly misses on an unrelated
query at the calibrated threshold.

## What to say in an interview

- **The threshold-calibration story is the actual point of this
  project.** Anyone can hardcode `0.92` and claim a cache "works" — actually
  measuring real similarity scores, discovering the guess was wrong (zero
  hits), and recalibrating from data rather than intuition is the
  difference between a demo that looks right and one that's actually
  been validated. This is the same instinct as project 03's MLflow
  regression baseline: don't trust a number until you've measured it.
- **Why log the "would-be cost" even on a cache hit, when nothing was
  actually spent?** Because the entire point of the dashboard is showing
  the *counterfactual* — what this session would have cost without
  caching — and that number only exists if it's computed and stored at
  the moment of the hit, not reconstructed later.
- **Why store embeddings in memory instead of a real vector DB (project
  01's Chroma)?** Cache size here is bounded by session length (tens to
  low hundreds of entries) — a linear scan over in-memory NumPy arrays is
  simpler and fast enough at that scale. A production cache serving many
  concurrent users with a much larger cache population would want
  project 01's Chroma-backed approach instead, for the same reasons
  argued there (persistence, approximate-nearest-neighbor search at
  scale).
- **Known limitation to volunteer:** a stale-cache problem exists — if
  the underlying facts change (e.g., the runbook's rollback threshold
  changes from 2x to 3x), a cached answer to a paraphrased question about
  it would keep returning the old, now-wrong answer indefinitely. This
  demo has no TTL or invalidation-on-source-change mechanism; a
  production version would need one, likely keyed to the same
  document-version tracking project 03's MLflow layer already
  demonstrates for prompt/logic versions.
