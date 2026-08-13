# 21 — Feature Store (Feast)

A real Feast feature store (local file offline store + SQLite online
store) proving the actual reason feature stores exist: **point-in-time
correct** historical feature retrieval, verified by constructing data
where "the latest value" and "the value as of a past timestamp" are
provably different numbers, and confirming Feast returns the right one
for each query mode.

## Maps to the market-gap research
- Named explicitly as a core storage-layer component of the "AI infra
  stack" alongside vector databases (project 01/04) and data lakes

## The actual point of this project

A plain database table can answer "what are user 1's features right
now." That's not what a feature store is for. The hard problem is:
**"what would user 1's features have been AS OF six weeks ago,"**
correctly, so a training pipeline doesn't accidentally leak information
from the future into a historical training example (the single most
common, hardest-to-detect ML data-leakage bug). This project's synthetic
data is deliberately built with three different feature snapshots for
user 1 at three different times specifically so that test is provable,
not just claimed.

## Setup (isolated venv)

```bash
cd 21-feature-store
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd src && python generate_data.py && cd ..
cd feature_repo && feast apply && feast materialize 2020-01-01T00:00:00 2026-12-31T00:00:00 && cd ..
```

## Run it

```bash
source .venv/bin/activate
cd src
python demo_point_in_time.py
```

## Measured results (this run)

```
=== Point-in-time historical retrieval ===
 user_id  event_timestamp            avg_rating_given  num_ratings  account_age_days
       1  2026-01-15 00:00:00+00:00  3.0               5            10
       2  2026-01-01 00:00:00+00:00  2.8               3            5
       1  2026-02-20 00:00:00+00:00  3.5               12           40

=== Online (latest-value) retrieval ===
  user 1: avg_rating_given=4.2, num_ratings=25, account_age_days=70
  user 2: avg_rating_given=3.9, num_ratings=18, account_age_days=50
  user 3: avg_rating_given=4.5, num_ratings=40, account_age_days=100
```

User 1 has three recorded snapshots (3.0 → 3.5 → 4.2 over 60 days).
Querying **as of Jan 15** (between the first two snapshots) correctly
returns **3.0**, not the latest 4.2. Querying **as of Feb 20** (between
the second and third) correctly returns **3.5**. The online query —
"what's true right now" — correctly returns the latest value, **4.2**,
for the same user. Same feature, same user, two query modes, two
different (both correct) answers — that contrast is the entire value
proposition of a feature store, proven with real numbers rather than
asserted.

## A real finding about how missing historical data is handled

Tested what happens when a point-in-time query's timestamp is **before**
a user's earliest recorded feature snapshot (user 2, queried as of
2025-12-01, one month before their earliest snapshot on 2026-01-01).
Naive expectation: a row with `NaN` feature values. **Actual, verified
behavior: Feast's local file-based offline store drops the row from the
result entirely** — the returned DataFrame has zero rows for that entity,
not a row of nulls. This matters operationally: a training pipeline that
assumes `len(result) == len(entity_df)` would silently lose training
examples here, a different (and easier to miss) failure mode than
silently training on `NaN` features.

## Tests

```bash
cd 21-feature-store && source .venv/bin/activate && pytest -q
```
4 live tests against the real Feast store (no mocking): point-in-time
query between the first two snapshots returns the first snapshot's
values (and explicitly *not* the latest, ruling out "just returns
whatever row matches the user_id"); point-in-time query between the
second and third snapshots returns the second's values; the row-dropping
behavior for a query before any snapshot exists (the real finding
above); and online retrieval returns the latest values, contrasting
directly with the point-in-time result for the same user.

## What to say in an interview

- **Why is point-in-time correctness the hard problem, not just "storing
  features somewhere"?** Because the failure mode it prevents — training
  a model on a feature value that didn't exist yet at the time of the
  training example — produces a model that looks great in offline
  evaluation and then fails in production, because production doesn't
  have access to "the future" the way a naively-joined training set
  accidentally did. It's one of the most common, hardest-to-catch bugs in
  applied ML, and it's silent: nothing crashes, the model just doesn't
  generalize.
- **Why build synthetic data with multiple timestamps per entity instead
  of one row per user?** Because with only one row per user, point-in-time
  correctness and "just look up the row" are indistinguishable — the test
  would pass for the wrong reason. Multiple snapshots per user, with
  query timestamps deliberately placed between them, is what makes the
  point-in-time claim actually falsifiable.
- **Why does the row-dropping finding matter enough to build a whole test
  around it?** Because it's the kind of behavior an engineer would
  otherwise discover the hard way — in production, as a mysteriously
  smaller-than-expected training set — rather than reading it in
  documentation. Verifying and testing it here means it's a known,
  documented property of this setup rather than a future surprise.
- **Known limitation to volunteer:** this uses Feast's local
  file/SQLite provider — appropriate for a demo, but a production feature
  store would use a real offline store (BigQuery, Snowflake, Redshift)
  for the historical/training path and a low-latency online store (Redis,
  DynamoDB — the same primitives project 06/20 already provision) for the
  serving path, at a scale where point-in-time joins run across millions
  of rows instead of six.
