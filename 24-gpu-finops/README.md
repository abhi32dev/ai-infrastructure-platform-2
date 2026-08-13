# 24 — GPU Cost Governance / FinOps Dashboard

Extends project 14's cost-ledger/dashboard pattern from LLM-token spend
to **GPU-hour utilization and idle-cost tracking** — the distinct 2026
responsibility named in the research: "tracking GPU utilization... daily
cloud compute scaling... maintaining strict cost controls."

## Honest scope statement

**This portfolio has no real GPU cluster to monitor.** The telemetry
(`telemetry_generator.py`) is explicitly synthetic, with deliberately
designed-in patterns (a training burst followed by an idle tail — the
single most common real-world GPU waste pattern: a job finishes and
nobody terminates the instance). What's real and independently tested is
the **cost-governance engine** — sustained-idle detection, per-team cost
allocation, threshold-based alerting — proven against constructed test
data with known correct answers, the same "the mechanism is real even
though the input is synthetic" framing as project 07's seeded
recommender A/B test.

## Maps to the market-gap research
- "Supervising compute clusters by tracking GPU utilization and
  designing infrastructure frameworks... maintaining strict cost
  controls" — named as a core 2026 AI infrastructure engineer
  responsibility, distinct from project 14's LLM-token-cost focus

## Setup (isolated venv)

```bash
cd 24-gpu-finops
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run it

```bash
source .venv/bin/activate
cd src
python cost_engine.py    # analysis printed to console
python dashboard.py      # writes ../gpu_dashboard.html
```

## Measured results (this run)

```
Total spend: $70.86
Total idle (wasted) spend: $10.96 (15.5% of total)

  gpu-001 (A100, platform-ml): total=$18.36 idle=$0.0 (0.0% idle)
  gpu-002 (A100, platform-ml): total=$18.36 idle=$10.96 (59.7% idle) [ALERT]
  gpu-003 (H100, research): total=$29.88 idle=$0.0 (0.0% idle)
  gpu-004 (L4, inference-serving): total=$4.26 idle=$0.0 (0.0% idle)
```

The engine correctly identified **exactly** the one instance
(`gpu-002`) whose simulated pattern was deliberately built to go idle
after training finished, correctly left the other three (two genuinely
busy patterns, one steady-serving pattern) at 0% idle, and correctly
raised an alert only for the one instance that crossed the idle-cost
threshold — proving the detection logic works, not just that it produces
some number.

## Tests

```bash
cd 24-gpu-finops && source .venv/bin/activate && pytest -q
```
7 deterministic tests against constructed telemetry with known correct
answers (independent of the synthetic generator): a momentary dip below
the idle threshold is correctly NOT flagged (the negative case — only
*sustained* idle counts as waste, not noise); sustained low utilization
IS flagged; a fully-busy instance has zero idle cost and no alert; a
fully-idle instance triggers an alert; cost allocation sums correctly
across teams (2 instances on the same GPU type = exactly 2x one
instance's cost); different GPU types produce genuinely different
per-point costs (not a hardcoded rate); and an unknown GPU type raises
`KeyError` rather than silently defaulting to a wrong cost.

## What to say in an interview

- **Why require SUSTAINED idle, not just "utilization dropped below
  X%"?** Because real training jobs have natural utilization dips
  (data-loading stalls, checkpoint writes, distributed all-reduce
  synchronization points) that would trigger false alerts on every
  single training run if a momentary dip counted as waste. Requiring a
  sustained window (30 minutes here) is what separates real signal
  (a job finished and the instance was never torn down) from normal
  training noise — proven directly by the negative-case test.
- **Why raise `KeyError` for an unknown GPU type instead of a default
  rate?** Because a silent default (e.g., defaulting to $0 or the
  cheapest rate) would make a cost report that looks complete while
  being systematically wrong for any new GPU type added to the fleet
  without updating the rate card — a much more dangerous failure mode
  than a loud crash that gets fixed immediately.
- **Why the honest 'no real GPU cluster' framing instead of presenting
  simulated numbers as if they were real measurements?** Because a
  Staff-level interviewer evaluating this would ask "is that a real GPU
  fleet" within one follow-up question, and the honest answer needs to
  already be the answer given — the actual engineering value here is the
  cost-governance logic (provably correct against constructed test data),
  not a claim about infrastructure that doesn't exist in this portfolio.
- **Known limitation to volunteer:** a production version of this would
  need the alert to actually page/notify someone (Slack, PagerDuty — the
  same integration points named on the resume) and would need real
  cloud-provider billing/utilization APIs (AWS Cost Explorer + CloudWatch
  GPU metrics, or the equivalent) as the telemetry source instead of a
  generator — the cost-governance logic in `cost_engine.py` would not
  need to change to consume that real data, since it's already decoupled
  from where the telemetry comes from.
