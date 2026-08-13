# 03 — MLflow Prompt/Logic Versioning + CI Regression Gate

Every version of the judge prompt (project 02's evaluation logic) is a
named file (`prompts/judge_prompt_v1.txt`, `v2.txt`, ...). Every evaluation
run against a prompt version is logged to MLflow (params: version/model/
temperature; metrics: agreement_rate/latency; artifact: full per-scenario
results). A committed `baseline_metrics.json` is the last-approved
performance, and `regression_gate.py` is what CI runs on every PR touching
prompt or automation logic — it fails the build if the new version's
agreement rate is worse than baseline.

## Maps to resume claims
- "Automation Logic Version Tracking": MLflow tracking of automation
  decision-logic versions, reproducible history, fast rollback path
- "CI-Gated Automation Changes": GitHub Actions running automated checks
  against the evaluation gate on every proposed change, blocking a
  regression from merging

## Setup (isolated venv)

```bash
cd 03-mlops-versioning-ci
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

ollama pull qwen2.5:1.5b   # same judge model as project 02
```

## Run it

```bash
source .venv/bin/activate
cd src

python eval_harness.py v1       # naive prompt — logs a run to MLflow
python eval_harness.py v2       # tuned, few-shot prompt — logs a second run

python regression_gate.py --update-baseline   # commit v2 as the approved baseline
python regression_gate.py                     # re-check current version against baseline (exit 0)
```

To see the MLflow UI and compare runs side by side:
```bash
mlflow ui --backend-store-uri sqlite:///$(pwd)/../mlflow.db
```

## Measured result (this is the actual point of the project)

| Prompt version | Agreement rate | Avg latency |
|---|---|---|
| v1 (naive, no examples) | **0.33** | 0.72s |
| v2 (few-shot, explicit criteria) | **0.83** | 0.52s |

This isn't a hypothetical — v1 is the first prompt I wrote for project 02's
judge model, and it scored so badly in testing that I rewrote it (see
project 02's README for the debugging story). v2 is that rewrite. MLflow
now holds the receipts for both, so "did this prompt change actually help"
is answered by a logged metric instead of a gut feeling.

## CI (`.github/workflows/ci.yml`)

Runs on every PR/push touching `prompts/` or `src/`: installs Ollama in the
runner, pulls the judge model, runs unit tests, then runs
`regression_gate.py` — a non-zero exit fails the check. Combined with
GitHub branch protection requiring this check + a CODEOWNERS review (same
governance pattern as the CONDOR release-governance bullet), a prompt
regression cannot reach `main` without a human explicitly approving via
`--update-baseline` first.
**Note:** this workflow file is committed and ready to run the moment this
repo is pushed to GitHub with Actions enabled — it hasn't executed on a
real GitHub runner yet since there's no remote configured.

## Tests

```bash
cd 03-mlops-versioning-ci && source .venv/bin/activate && pytest -q
```
7 tests, in three categories:
- **Positive/negative pass-fail logic (3):** no-baseline-creates-one-and-passes, regression-blocks, equal-or-better-passes
- **Boundary/edge cases (3):** agreement rate exactly at the tolerance boundary passes (not off-by-one), a tiny 0.01 regression still blocks (tolerance is 0.0, not loose), `--update-baseline` correctly overwrites an existing baseline file
- **Live integration (1):** proving `agreement_rate(v2) > agreement_rate(v1)` is a real, reproducible measurement against the actual local judge model

## What to say in an interview

- **Why block on agreement_rate specifically, not just "tests pass"?**
  Unit tests catch code bugs; they don't catch "the model quietly got
  worse at the actual judgment task." A regression here is silent —
  nothing crashes, the code runs fine, but the AI-assisted logic makes
  worse decisions. That's exactly the failure mode a fixed evaluation
  set + regression gate exists to catch, and exactly why the resume
  bullet ties CI to the evaluation gate, not just to pytest.
- **Why require an explicit `--update-baseline` step instead of
  auto-updating the baseline on every green run?** If the baseline
  silently ratchets to whatever the latest run produced, a *slow*
  regression (each change is a tiny bit worse, but never worse than the
  immediately preceding run) would never get caught. Baseline updates
  should be a deliberate, reviewed action — same instinct as requiring a
  human release manager to promote a build through QA/Stage/Prod rather
  than auto-promoting on green CI.
- **Why SQLite-backed MLflow instead of the plain filesystem store?**
  Newer MLflow versions deprecated the raw filesystem backend in favor of
  a database-backed store (I hit this directly — the filesystem backend
  threw a `MlflowException` on first run and I switched to
  `sqlite:///mlflow.db`). It's also just closer to how you'd actually run
  this in a team setting, where multiple people need to query run history
  concurrently.
- **Known limitation to volunteer:** the CI workflow pulls a fresh model
  and re-runs the full eval on every single PR, which is slow and
  redundant if only unrelated code changed. A production version would
  cache the Ollama model layer and skip the gate entirely via the `paths:`
  filter already in the workflow (only runs when `prompts/` or `src/`
  actually changed) — which this workflow already does, but a larger eval
  set would also want sharding/parallelization across scenarios.
