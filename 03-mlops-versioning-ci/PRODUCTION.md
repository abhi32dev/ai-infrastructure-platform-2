# Production Readiness — MLflow Versioning + CI Regression Gate

## Current state
MLflow (SQLite-backed) tracks prompt-version runs with params/metrics/
artifacts; a regression gate compares a new run's agreement rate against
a committed baseline and exits non-zero on regression. Measured a real
v1→v2 prompt improvement (0.33→0.83 agreement). GitHub Actions workflow
committed but unexecuted (no GitHub remote at build time).

## Design decisions & trade-offs

| Decision | Why | Trade-off accepted |
|---|---|---|
| SQLite-backed MLflow, not filesystem store | Filesystem store is deprecated by newer MLflow | Single-writer; a real team needs a shared Postgres/MySQL-backed tracking server |
| Explicit `--update-baseline` flag | Baseline changes should be a deliberate, reviewed action, not automatic on every green run | An engineer can forget to update it after an intentional improvement, causing false regression alarms |
| Regression tolerance = 0.0 | Catches even small regressions | No tolerance for legitimate run-to-run noise in the metric itself — a flaky evaluation set would cause false positives |

## What's missing for real production use
- **Shared MLflow tracking server** — SQLite is single-machine; a team
  needs a centrally-hosted tracking server (Postgres backend, S3
  artifact store) so everyone's runs are visible
- **Statistical significance on the regression check** — currently a raw
  threshold comparison, not a significance test; project 07's harness
  exists but isn't integrated here, so a regression within normal noise
  could trigger a false alarm (or a real regression within noise could
  slip through)
- **Automatic rollback** — the gate blocks a merge, but doesn't provide a
  one-command rollback if a regression somehow reaches production anyway
- **Multi-metric gating** — only agreement_rate is gated; latency and
  cost regressions aren't checked even though they're tracked

## Scaling considerations
- Evaluation set of 6 scenarios runs in seconds; a production-scale set
  (hundreds of scenarios) would need the CI job's timeout budget
  increased and possibly parallelized evaluation (sharding scenarios
  across workers)
- MLflow's SQLite backend would need migration to Postgres before
  multiple CI runners could write concurrently without lock contention

## Security & compliance considerations
- No access control on who can call `--update-baseline` — in a real repo
  this should be gated by the same CODEOWNERS/branch-protection pattern
  the CI workflow already assumes exists upstream
- Prompt content (potentially containing business logic) is stored in
  MLflow's tracked artifacts — appropriate for internal tooling, would
  need access controls if the tracking server is shared beyond the
  immediate team

## Operational readiness
- CI workflow pulls a fresh Ollama model on every single run — slow and
  wasteful; a production CI setup would cache the model layer (documented
  as a known limitation already)
- No dashboard beyond MLflow's own UI (`mlflow ui`) — no Slack/PagerDuty
  integration when a regression blocks a merge
- No retry/backoff if the CI runner's Ollama installation itself fails to
  start — the workflow would just fail the whole job
