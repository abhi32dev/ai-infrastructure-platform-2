# Production Readiness — GPU Cost Governance / FinOps Dashboard

## Current state
Real, independently-tested cost-governance engine (sustained-idle
detection, per-team cost allocation, threshold alerting) against
explicitly synthetic telemetry (no real GPU cluster available). Verified
the engine correctly identified exactly the one deliberately-idle
instance and correctly left three genuinely-busy instances unflagged. 7
deterministic tests against constructed data with known correct answers.

## Design decisions & trade-offs

| Decision | Why | Trade-off accepted |
|---|---|---|
| Synthetic telemetry, explicitly labeled | No real GPU cluster to monitor; honesty over a fabricated "real" claim | The specific dollar figures aren't measurements of anything real — only the engine's correctness (against known-answer test data) is a real claim |
| Sustained-idle window (30 min), not instant threshold-crossing | Avoids false alerts on normal training-job utilization dips | A genuinely wasteful instance that's idle for 25-minute stretches repeatedly wouldn't trigger, even though it's still real waste — a tuning tradeoff |
| `KeyError` on unknown GPU type, not a default rate | A silent default would produce a cost report that looks complete while being systematically wrong | Any new GPU type added to a real fleet MUST update the rate card before this engine can process its telemetry, or every calculation involving it fails loudly |

## What's missing for real production use
- **Real telemetry source** — the single biggest gap: this needs to be
  fed real cloud-provider billing/utilization APIs (AWS Cost Explorer +
  CloudWatch GPU metrics, or equivalent) instead of a generator; the
  engine itself is decoupled from the telemetry source and wouldn't need
  to change
- **Real alerting integration** — alerts are currently just a boolean
  field in the analysis output; production needs actual paging
  (Slack/PagerDuty, the same integrations named on the resume)
- **Historical trending** — no time-series storage of past analyses; a
  real FinOps dashboard needs to show waste trends over weeks/months, not
  just a point-in-time snapshot
- **Automated remediation** — detecting idle instances is only half the
  job; a mature FinOps system can auto-terminate or auto-downsize
  confirmed-idle instances after alerting, not implemented here

## Scaling considerations
- The cost-governance logic (idle detection, allocation, alerting) is
  O(telemetry points) — trivially fast at any realistic fleet size
- Real scaling concern is the telemetry ingestion pipeline itself at a
  large fleet (thousands of GPU instances reporting utilization every few
  minutes) — not addressed here since there's no real telemetry source
  yet

## Security & compliance considerations
- Cost/utilization data by team could be considered sensitive
  (organizational spend visibility) — a real deployment needs access
  controls on who can see which team's cost breakdown
- No audit trail of who acknowledged/dismissed an alert — needed for
  accountability in a real cost-governance process

## Operational readiness
- No dashboard auto-refresh — `dashboard.py` generates a static
  snapshot; a production FinOps dashboard needs near-real-time updates
- No integration with actual instance-termination workflows — alerts are
  informational only, with no workflow connecting "alert raised" to
  "someone acted on it"
