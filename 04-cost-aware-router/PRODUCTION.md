# Production Readiness — Cost-Aware Retrieval & Model Router

## Current state
Complexity-based routing (SIMPLE→small model, COMPLEX→large model) with
fail-safe-to-COMPLEX on ambiguous classification. Separately, a
chunk_size/k sweep measures the retrieval cost/quality frontier. Measured
39.7% cost savings from routing; chunk_size=1000/k=4 identified as the
best hit-rate-per-token point on this corpus. 9 tests including a
regression guard on the rate card itself.

## Design decisions & trade-offs

| Decision | Why | Trade-off accepted |
|---|---|---|
| Classification via the small model itself | Classification call is cheap regardless of which model does it; avoids adding a third model | Small model's classification accuracy (5/6 on the test set) directly gates routing quality |
| Fail-safe to COMPLEX (expensive) on ambiguity | Wrongly-expensive costs cents; wrongly-cheap on a hard query costs a bad answer | Systematically over-routes to the expensive model whenever classification is uncertain, understating true savings potential |
| Illustrative $/1M-token rate card, not live pricing | Ollama has no per-token cost; the point is the routing mechanism and relative savings ratio | Absolute dollar figures aren't tied to any real provider's current rate card |

## What's missing for real production use
- **Real API cost integration** — this demo's costs are illustrative; a
  production router would pull live per-provider, per-model pricing
  (which changes over time) rather than a hardcoded rate card
- **Classification confidence scoring** — binary SIMPLE/COMPLEX with no
  confidence signal; a production router might route "uncertain" cases to
  a third, medium-cost tier rather than jumping straight to the most
  expensive option
- **Per-query chunk_size/k tuning** — the sweep found one best config for
  this corpus; a production system might need per-query-type tuning
  (short factual questions vs. long analytical ones)
- **Routing accuracy monitoring in production** — no feedback loop from
  actual user satisfaction/correction back into the classifier's accuracy

## Scaling considerations
- Classification adds one extra model call per query — at very high QPS,
  this doubles minimum latency for every query even when it correctly
  identifies SIMPLE cases; a cached/precomputed classification for
  repeated query patterns (project 14's semantic cache pattern) would
  help
- The chunk_size/k sweep is O(configs × questions) — fine for a one-time
  tuning pass on a small eval set; at production scale this tuning would
  run offline against a much larger held-out query log, not inline

## Security & compliance considerations
- No difference in data handling between the small and large model paths
  — both run locally via Ollama, so no cross-region/cross-provider data
  residency concern in this demo, but a production version routing
  between different cloud providers' APIs would need this considered
  explicitly (does the "cheap" model provider have the same compliance
  posture as the "expensive" one?)

## Operational readiness
- No cost budget circuit breaker — nothing stops the router from
  spending unboundedly if the query volume or complexity distribution
  shifts unexpectedly; a production version would want a daily/hourly
  spend cap with alerting
- No visibility into WHY a specific query was routed where — the
  classification reasoning isn't logged, making post-hoc audits of
  routing decisions difficult
