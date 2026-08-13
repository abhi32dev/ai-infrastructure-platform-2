# Production Readiness — Feature Store (Feast)

## Current state
Real Feast (local file offline store + SQLite online store). Proved
point-in-time correctness with deliberately-designed diverging snapshot
data. Found and documented a real behavior (queries before any snapshot
drop the row entirely, rather than returning nulls). 4 tests directly
verifying the point-in-time join logic.

## Design decisions & trade-offs

| Decision | Why | Trade-off accepted |
|---|---|---|
| Local file + SQLite provider | Zero infra, appropriate for demonstrating the point-in-time mechanism | Not representative of production offline-store query performance (BigQuery/Snowflake/Redshift) at real data volumes |
| Synthetic data with multiple timestamps per entity | The ONLY way to make point-in-time correctness provable rather than just claimed | Small (6-row) dataset — doesn't exercise the offline store's performance characteristics at scale |
| Documented the row-dropping behavior rather than "fixing" it | It's Feast's actual, verified behavior — not a bug in this project's code | A production pipeline using this exact setup needs to explicitly handle the row-dropping case (e.g., verify `len(result) == len(entity_df)` and alert on mismatch) |

## What's missing for real production use
- **Real offline store** — BigQuery/Snowflake/Redshift for historical
  queries at real training-data volume; the local file store doesn't
  scale past a demo dataset
- **Real online store for low-latency serving** — SQLite is fine for a
  demo; production online serving needs Redis or DynamoDB (the same
  primitives project 06/20 already provision) for sub-10ms lookups at
  request-serving scale
- **Feature freshness monitoring** — no alerting if `materialize()`
  hasn't run recently, which would silently serve stale online features
- **Feature versioning/lineage** — no tracking of which feature
  definition version was used to train a given model, needed for full
  reproducibility

## Scaling considerations
- Point-in-time joins get expensive at scale (join complexity grows with
  both entity count and feature history depth) — real deployments need
  the join pushed down into a scalable data warehouse (BigQuery/Snowflake),
  not computed in a local Python process
- Online store lookups need to stay low-latency under production request
  volume — SQLite's single-writer model doesn't support this; Redis/
  DynamoDB do

## Security & compliance considerations
- No access control on which teams/services can read which features —
  a production feature store often needs per-feature-view authorization,
  especially for features derived from sensitive user data
- No data lineage/audit trail connecting a feature value back to its
  source data for compliance/debugging purposes

## Operational readiness
- No monitoring of `materialize()` job success/failure — a production
  feature store needs alerting if the batch job populating the online
  store fails or falls behind schedule
- No feature-value distribution monitoring (drift detection) — features
  can silently change distribution over time in ways that degrade
  downstream model quality without any error being raised
