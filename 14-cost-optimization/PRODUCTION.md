# Production Readiness — Semantic Cache & Cost Dashboard

## Current state
Embedding-similarity response cache with a real, measured threshold-
calibration finding (0.92 guess → 0 hits; recalibrated to 0.75 from
measured data → 27% cost savings). SQLite cost ledger + HTML dashboard.
9 tests including a regression guard protecting the calibration finding.

## Design decisions & trade-offs

| Decision | Why | Trade-off accepted |
|---|---|---|
| In-memory cache (NumPy linear scan), not Chroma | Cache size bounded by session length; simpler and fast enough at this scale | Doesn't persist across process restarts; a production cache serving many users needs a persistent, larger-scale vector index |
| Threshold=0.75, calibrated from measured similarity | Real data beats guessed thresholds (proven: 0.92 guess produced zero hits) | Catches only near-identical rephrasings, not loose paraphrases — a stated, deliberate recall/precision tradeoff |
| No TTL/invalidation on cached entries | Keeps the demo focused on the caching mechanism itself | Explicitly flagged as a real gap: if underlying facts change, a cached answer to a paraphrased question keeps returning the stale answer indefinitely |

## What's missing for real production use
- **Cache invalidation on source-document change** — the single biggest
  gap: no mechanism ties a cached response's validity to whether the
  document(s) it was grounded in have since changed
- **TTL-based expiry** — cached entries live forever within a session;
  production needs at least a TTL as a coarse safety net even before
  proper invalidation exists
- **Persistent, larger-scale cache backend** — Chroma or a dedicated
  vector cache service, not an in-memory NumPy array, for a cache meant
  to survive restarts and serve many concurrent users
- **Per-user or per-tenant cache isolation** — the current cache has no
  concept of "whose" query this is; a multi-tenant deployment needs
  isolation so one user's cached answer never leaks to another user's
  differently-scoped query

## Scaling considerations
- Linear scan over in-memory embeddings is fine at tens-to-hundreds of
  cached entries; would need approximate nearest-neighbor search (the
  same Chroma/pgvector pattern from project 01) at real production cache
  sizes
- The cost ledger (SQLite) is single-writer; a production deployment with
  concurrent cache checks from multiple processes needs a proper
  database, not a local SQLite file

## Security & compliance considerations
- Cached responses may contain information from the original query's
  context — if that context included PII (project 12's concern), the
  cache itself becomes a place PII persists beyond the original request's
  lifetime, worth explicit consideration in a real deployment

## Operational readiness
- No monitoring of cache hit-rate drift over time — if query patterns
  shift, the calibrated threshold might stop being appropriate and
  nothing would surface that
- Dashboard is generated on-demand, not live/auto-refreshing — a
  production FinOps dashboard needs to reflect near-real-time spend, not
  a point-in-time snapshot regenerated manually
