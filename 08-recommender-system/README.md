# 08 — Recommendation System with Offline Evaluation

A matrix-factorization recommender built from scratch with NumPy SGD (no
scikit-surprise or other recommender library), trained and evaluated on
the real MovieLens 100K dataset against a non-personalized popularity
baseline, with the same "confirm the lift is real" statistical discipline
as project 07.

## Maps to resume claims
- "Production Recommendation Systems" (Smith Micro): personalized
  recommendation algorithms converting behavioral data into targeted
  recommendations
- "Statistically Validated Recommendation Variants": A/B comparison
  confirming the lift over baseline is real, not normal variance
- Complements the IEEE-published, "built from first principles" ML
  discipline already on the resume — this model's SGD update rule is
  implemented directly, not called from a library

## Dataset
[MovieLens 100K](https://grouplens.org/datasets/movielens/100k/) — 100,000
ratings from 943 users on 1,682 movies. Downloaded automatically into
`data/ml-100k/` (not committed to git — regenerate with the command
below). Uses the official `ua.base`/`ua.test` 80/20 split so results are
reproducible and comparable to published benchmarks.

```bash
cd 08-recommender-system/data
curl -sL -o ml-100k.zip https://files.grouplens.org/datasets/movielens/ml-100k.zip
unzip -q ml-100k.zip
```

## Setup (isolated venv)

```bash
cd 08-recommender-system
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run it

```bash
source .venv/bin/activate
cd src
python evaluate.py
```

Trains the matrix-factorization model (15 epochs, 20 latent factors),
fits the popularity baseline, then reports RMSE and a precision@10/p-value
comparison between the two.

## Measured results (real run, real data)

| Metric | Value |
|---|---|
| Test RMSE (matrix factorization) | **0.9431** |
| MF precision@10 | 0.0369 |
| Baseline precision@10 | 0.0284 |
| **Lift over baseline** | **+30.19%** |
| Users compared | 934 |
| **p-value** | **0.0017 — significant** |

An RMSE of 0.94 on MovieLens-100K is in the same range as published
baseline matrix-factorization results on this dataset (typical published
figures cluster around 0.90-0.95 for a simple SGD-MF model without bias
regularization tuning or more epochs) — a reasonable, credible result for
a from-scratch implementation, not a suspiciously perfect one.

## Tests

```bash
cd 08-recommender-system && source .venv/bin/activate && pytest -q
```
9 tests, in three categories:
- **Positive path (4):** training reduces error on synthetic data, predictions stay in [1,5], recommendations exclude already-seen items, popularity baseline respects its minimum-ratings floor
- **Negative / edge cases (4):** requesting more recommendations than items exist returns only what's available (not padded or duplicated); excluding every item returns an empty list, not an error; a baseline where NO item meets the minimum-ratings floor returns an empty ranking rather than falling back to including everything; an untrained model (random init, global_mean still 0.0) still clips predictions to [1,5]
- **Live integration (1):** training on the real MovieLens data and confirming MF beats the popularity baseline

## What to say in an interview

- **Why matrix factorization instead of simple item/user-based collaborative
  filtering (cosine similarity)?** MF learns latent factors that capture
  patterns neither raw similarity metric sees directly (e.g., a genre
  preference emerging from co-rated patterns, not explicit tags), and it's
  the same family of technique behind most production-scale recommenders
  — similarity-based CF also doesn't scale well to 1000s of items compared
  against each other per request.
- **Why compare against a popularity baseline, not just report the MF
  model's own metrics?** A model's absolute precision/RMSE means nothing
  without a comparison point. The popularity baseline is the honest "what
  would happen with zero personalization" floor — exactly the bar the
  resume's 7.4% lift was measured against at Smith Micro. Reporting only
  the MF model's numbers would be an unfalsifiable claim.
- **Why precision@k specifically, and why per-user before averaging?**
  RMSE measures rating-prediction accuracy, but a recommender's actual job
  is *ranking* — precision@10 measures "of the top 10 I'd show this user,
  how many did they actually like," which is what a real product surfaces.
  Computing it per-user first (then comparing the two per-user
  distributions with Welch's t-test) is required for the significance
  test to be valid — averaging first would throw away the variance
  information the t-test needs.
- **Known limitation to volunteer:** 20 latent factors and 15 epochs were
  chosen for a fast, complete local training run (a few minutes), not
  tuned via cross-validation — a production version would grid-search
  latent-factor count, learning rate, and regularization, and likely add
  epoch-level early stopping against a validation RMSE curve instead of a
  fixed epoch count.
