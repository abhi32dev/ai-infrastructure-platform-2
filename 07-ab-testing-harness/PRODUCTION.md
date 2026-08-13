# Production Readiness — A/B Testing & p-Value Significance Harness

## Current state
Two-proportion z-test and Welch's t-test implemented and validated
against known-answer synthetic cases. Measured a real live-latency
comparison that correctly refused to call a 56%-looking lift significant
at n=8 — the intended lesson, not a bug. 9 tests covering symmetry,
negative lift, zero-variance edge cases, and 0/0-division safety.

## Design decisions & trade-offs

| Decision | Why | Trade-off accepted |
|---|---|---|
| Two-sided tests only | Standard default for "are these different" questions | A one-sided test would have more power if the direction of interest is known in advance — not implemented |
| No multiple-comparison correction | Keeps the harness simple for single-metric A/B tests | Running many simultaneous metrics/experiments without Bonferroni or FDR correction inflates the false-positive rate across the whole test suite |
| `nan` p-value on zero-variance input evaluates as "not significant" | Fail-safe direction: never claim a real effect from degenerate data | Silently swallows a genuinely edge-case input rather than raising — could mask a data-quality bug upstream |

## What's missing for real production use
- **Multiple-comparison correction** — a real experimentation platform
  running dozens of concurrent A/B tests needs FDR/Bonferroni correction;
  this harness doesn't apply any
- **Sequential testing / peeking correction** — this harness assumes a
  fixed sample size decided in advance; repeatedly checking results as
  data accumulates (common in practice) inflates false-positive rate
  without a sequential-testing correction (e.g., alpha-spending)
  addressing it
- **Sample-size/power calculation** — no pre-experiment power analysis to
  determine required sample size; a production platform would compute
  this before launching an experiment, not just analyze after
- **Automated experiment lifecycle** — no integration with a real
  experiment-assignment system (bucketing users, ramping traffic
  percentages)

## Scaling considerations
- The statistical tests themselves (`scipy.stats`) scale to arbitrarily
  large sample sizes trivially — no scaling concern in the math itself
- The real scaling concern is data collection/aggregation upstream of
  this harness, which isn't addressed here (this project starts from
  already-aggregated counts/samples)

## Security & compliance considerations
- Not directly applicable — this is a pure statistics library with no
  data storage, network calls, or user data handling in itself
- A production version integrated with real user data would need the
  same PII-handling discipline as any analytics pipeline consuming raw
  user events

## Operational readiness
- No experiment-results dashboard — results are printed to console;
  project 14's HTML-dashboard pattern isn't applied here
- No automated "stop the experiment" trigger when a clear winner emerges
  or a metric moves in a clearly harmful direction — purely an analysis
  tool, not a live experiment-management system
