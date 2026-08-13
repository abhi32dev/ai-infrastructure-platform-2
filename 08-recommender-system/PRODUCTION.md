# Production Readiness — Matrix-Factorization Recommender

## Current state
SGD matrix factorization built from scratch (no library), evaluated on
real MovieLens 100K against a popularity baseline. Measured RMSE 0.9431,
+30.19% precision@10 over baseline (p=0.0017). 9 tests covering training
convergence, prediction clipping, and edge cases (over-request, all-
excluded, empty-floor baseline).

## Design decisions & trade-offs

| Decision | Why | Trade-off accepted |
|---|---|---|
| From-scratch SGD, not a library (Surprise, implicit) | Demonstrates understanding of the underlying algorithm | Not as optimized/battle-tested as a mature library; a real production system would likely use one |
| 20 latent factors, 15 epochs, fixed hyperparameters | Fast, complete local training run | Not tuned via cross-validation — a production model would grid-search these |
| Popularity baseline, not a second personalized model | Establishes the honest "zero personalization" floor | Doesn't compare against alternative personalized approaches (item-based CF, neural CF) that a production choice would also need to beat |

## What's missing for real production use
- **Hyperparameter tuning via cross-validation** — current settings are
  reasonable defaults, not tuned; a production model needs a proper
  train/validation/test split with grid or Bayesian search
- **Cold-start handling** — no explicit strategy for brand-new
  users/items with no rating history; the current model would predict
  near the global mean for them, which is suboptimal
- **Online/incremental updates** — the model is trained in one batch pass;
  production recommenders typically need incremental updates as new
  ratings arrive, without full retraining
- **Diversity/serendipity in ranking** — precision@10 alone can produce
  narrow, filter-bubble-y recommendations; a production ranker often adds
  diversity re-ranking on top of the raw predicted scores

## Scaling considerations
- MovieLens 100K (943 users × 1682 items) trains in minutes on a laptop;
  a production catalog (millions of items/users) needs distributed
  training (Spark ALS, or a deep learning approach with mini-batch
  training on GPU) — this from-scratch NumPy implementation would not
  scale directly
- Serving `recommend_top_k` computes a full dot product against every
  item for a user — fine at 1682 items, would need approximate nearest-
  neighbor search (FAISS, ScaNN) at real catalog scale

## Security & compliance considerations
- Rating data is inherently sensitive user behavioral data — a
  production deployment needs the same PII/data-governance discipline as
  any user-behavior pipeline, not addressed in this local-CSV-based demo
- No differential privacy or user-level data deletion support — a real
  system needs to support "delete my data" requests, which requires
  retraining or a model architecture that supports targeted unlearning

## Operational readiness
- No monitoring of recommendation quality drift over time — a production
  system needs ongoing offline eval (this project's methodology) run on
  a schedule against fresh held-out data, plus online A/B testing
  (project 07's harness) to catch model staleness
- No fallback path if the model service is unavailable — a production
  recommender needs a cached/precomputed fallback (e.g., last-known-good
  recommendations or the popularity baseline itself) for availability
