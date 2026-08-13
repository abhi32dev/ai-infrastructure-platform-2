# 22 — Named LLM Evaluation Tools: Ragas & DeepEval

Wraps a self-contained copy of project 01's RAG pipeline with **both**
Ragas and DeepEval — the specific tools named in the market-gap research
— run against real local Ollama models at zero API cost, alongside
projects 02/03's from-scratch evaluation gate. This project exists
because "have you used Ragas/DeepEval" is a real interview question, and
building a stronger custom evaluator (project 02) doesn't answer it.

## Maps to the market-gap research
- Ragas and DeepEval named directly as the leading open-source LLM
  evaluation frameworks in 2026 industry comparisons

## Setup — a real multi-hour dependency resolution, documented honestly

`pip install ragas deepeval` (latest versions) **does not import**:
`ragas.llms.base` unconditionally imports `ChatVertexAI` from a
`langchain_community` submodule that recent `langchain-community`
releases removed. This isn't version-specific to one ragas release —
both `ragas==0.4.3` and `ragas==0.2.15` hit it, because neither pins an
upper bound on `langchain-community`, so pip always resolves the latest
(broken, for this purpose) version. **Fix**: pinned an entire consistent
older stack (`requirements.txt`) — `ragas==0.2.15` with
`langchain-community==0.3.7`, `langchain-core==0.3.86`,
`langchain-ollama==0.2.3`, `langchain-chroma==0.1.4` — found by working
backward from the first broken import, downgrading one package,
discovering the next broken import, and repeating. Documented as the
exact version pins in `requirements.txt`, not just "install these
packages" — a naive install of this project 6 months from now would
likely hit the same wall again with newer default versions.

## Setup

```bash
cd 22-ragas-deepeval
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # exact working pins — see above

ollama pull llama3.2:1b
ollama pull qwen2.5:1.5b
ollama pull nomic-embed-text
```

## Run it

```bash
source .venv/bin/activate
cd src
python ragas_eval.py       # Ragas: faithfulness, answer_relevancy, context_precision, context_recall
python deepeval_eval.py    # DeepEval: faithfulness, answer_relevancy
python compare.py          # both, side by side
```

## Finding #1: Ragas needs LOW concurrency with a local CPU judge model

First run, Ragas' default concurrency (`max_workers` unset): 6 of 16
internal judge-model sub-calls timed out, and `context_precision` came
back `NaN` for every single question.

```
{'faithfulness': 0.2500, 'answer_relevancy': 0.4659, 'context_precision': nan, 'context_recall': 0.6167}
```

Rerun with `RunConfig(timeout=180, max_workers=2)` — same model, same
questions, only concurrency changed:

```
{'faithfulness': 0.4167, 'answer_relevancy': 0.4659, 'context_precision': 1.0000, 'context_recall': 0.6167}
```

**Why**: Ragas' default concurrency assumes a cloud judge API (OpenAI)
that handles many parallel requests fine. A local CPU-bound Ollama
model doesn't — parallel requests compete for the same CPU cores rather
than truly running in parallel, and the resulting slowdown pushes
individual calls past Ragas' per-job timeout. Lowering concurrency to
match the judge model's real capacity fixed 3 of 4 `context_precision`
failures and nearly doubled the measured `faithfulness` score by letting
calls that were timing out actually complete.

## Finding #2: DeepEval crashes hard, Ragas degrades soft — same root cause, different failure mode

With `llama3.2:1b` as DeepEval's judge model:

```
ValueError: Evaluation LLM outputted an invalid JSON. Please use a better evaluation model.
```

DeepEval's own error message is direct: `llama3.2:1b` isn't reliable
enough at producing the strict JSON its verdict-extraction step requires.
Swapping to `qwen2.5:1.5b` — the same swap project 02's README already
documented for the same underlying reason (structured-output reliability)
— fixed it completely:

```
Q: What happens when an EC2 receiver fails health checks?
  faithfulness: 1.000 (PASS)
  answer_relevancy: 0.500 (PASS)
Q: What caused the 2026-02-14 duplicate alarm incident?
  faithfulness: 0.500 (PASS)
  answer_relevancy: 1.000 (PASS)
Q: Who approves a rollback?
  faithfulness: 0.000 (FAIL)
  answer_relevancy: 0.500 (PASS)
Q: What must AI-assisted automation changes pass before merging?
  faithfulness: 0.333 (FAIL)
  answer_relevancy: 1.000 (PASS)
```

**The comparison worth making explicit**: Ragas' `context_precision`
failed *silently* (`NaN`, evaluation kept running) while DeepEval's
faithfulness metric failed *loudly* (a raised `ValueError`, evaluation
stopped) — same underlying cause (a small local model struggling with
structured output under load/complexity), two different failure
philosophies. Neither is strictly better: silent `NaN` risks an engineer
not noticing a metric quietly stopped working; a hard crash is impossible
to miss but halts the whole run. Knowing which framework does which
matters for how you'd monitor either one in CI.

## Tests

```bash
cd 22-ragas-deepeval && source .venv/bin/activate
pytest -q -m "not slow"   # fast, ~2s

# run slow tests INDIVIDUALLY, not as one -m slow selection — see the
# real finding below
pytest -q -m slow -k test_deepeval_with_unreliable_judge
pytest -q -m slow -k test_deepeval_with_reliable_judge_produces_valid_scores
pytest -q -m slow -k test_ragas_faithfulness_and_recall_are_valid_scores
```
6 tests: 3 fast/deterministic (eval dataset structure, RAG pipeline
smoke test), 3 slow/live full-framework runs, each independently
verified passing (3.6s, 26s, and 4m10s respectively).

**A real finding from building this test suite**: running all three
`slow` tests together in a single `pytest -q -m slow` invocation hung
indefinitely (40+ minutes, near-zero CPU usage, no progress) — but each
test passed reliably in 30 seconds to 4 minutes when run individually.
Root cause not fully isolated; the leading hypothesis is resource/context
buildup in the single `llama-server` process Ollama keeps resident across
many sequential heavy calls within one Python process's lifetime. Rather
than silently paper over this (e.g. quietly reducing test scope), it's
documented directly in the test file and here: run these three
individually, not as one combined `-m slow` selection, on this hardware.

Also worth stating plainly: `test_deepeval_with_unreliable_judge...`
is intentionally NOT a strict "must raise ValueError" assertion. An
earlier version asserted that and it failed on a later run — the same
`llama3.2:1b` + DeepEval combination that crashed with an invalid-JSON
error on one input succeeded cleanly on a different, simpler input. The
test now correctly asserts the real, honest property: **when it fails,
it fails loud with that specific error; when it succeeds, the score is
valid** — never a silent wrong answer either way.

## What to say in an interview

- **Why does the multi-hour dependency-pinning story matter as much as
  the eval scores?** Because "I used Ragas and DeepEval" is a much
  weaker claim than "I hit a real cross-package compatibility break, root-
  caused it to a specific unconditional import, and pinned a verified-
  working version set" — the second one is what actually happens when a
  team adopts a fast-moving open-source eval framework, and it's the more
  representative Staff-level story.
- **Why not just always use the larger judge model everywhere and avoid
  finding #2 entirely?** Because the point of this project isn't to hide
  the failure mode, it's to characterize it — knowing *which* local
  models are reliable enough for which evaluation tool, and *how* each
  tool fails when they aren't, is more valuable going into a real
  deployment decision than a report that only shows the passing
  configuration.
- **How does this compare to project 02/03's from-scratch evaluation
  gate?** Complementary, not redundant: project 02/03 proves the
  underlying LLM-as-judge *mechanism* end to end (AND-gate, MLflow
  versioning, CI regression blocking) with full control over every
  moving part; this project proves fluency with the *named, standard
  tools* an interviewer will ask about by name, including their specific
  operational rough edges.
- **Known limitation to volunteer:** Ragas and DeepEval used different
  judge models in this comparison (`llama3.2:1b` for Ragas after the
  concurrency fix, `qwen2.5:1.5b` for DeepEval after the JSON-reliability
  fix) — not a perfectly controlled apples-to-apples comparison of the
  frameworks' scoring philosophies, since the judge model itself is a
  confounding variable. A tighter comparison would hold the judge model
  fixed across both and accept Ragas' higher tolerance for that model's
  limitations as part of the actual finding.
