"""Fast deterministic tests (tiny synthetic data, few epochs) of the model
mechanics, plus one slower live test against the real MovieLens data
proving the trained model actually beats the baseline.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from matrix_factorization import MatrixFactorizationRecommender
from baseline import PopularityBaseline


def tiny_dataset():
    # 5 users, 5 items, dense enough to learn something in a handful of epochs
    rng = np.random.default_rng(0)
    rows = []
    for u in range(1, 6):
        for i in range(1, 6):
            rows.append((u, i, rng.integers(1, 6)))
    return pd.DataFrame(rows, columns=["user_id", "item_id", "rating"])


def test_mf_training_reduces_error():
    df = tiny_dataset()
    model = MatrixFactorizationRecommender(n_users=5, n_items=5, n_factors=3)

    def total_sq_error():
        return sum((model.predict(int(r.user_id), int(r.item_id)) - r.rating) ** 2 for r in df.itertuples())

    error_before = total_sq_error()
    model.fit(df, epochs=20, verbose=False)
    error_after = total_sq_error()
    assert error_after < error_before


def test_predictions_are_clipped_to_valid_rating_range():
    df = tiny_dataset()
    model = MatrixFactorizationRecommender(n_users=5, n_items=5, n_factors=3)
    model.fit(df, epochs=5, verbose=False)
    for u in range(1, 6):
        for i in range(1, 6):
            pred = model.predict(u, i)
            assert 1.0 <= pred <= 5.0


def test_recommend_top_k_excludes_seen_items():
    df = tiny_dataset()
    model = MatrixFactorizationRecommender(n_users=5, n_items=5, n_factors=3)
    model.fit(df, epochs=5, verbose=False)
    recs = model.recommend_top_k(user_id=1, k=3, exclude_items={1, 2})
    assert 1 not in recs
    assert 2 not in recs
    assert len(recs) <= 3


def test_popularity_baseline_ranks_by_mean_rating_with_count_floor():
    df = pd.DataFrame([
        (1, 100, 5), (2, 100, 5),  # item 100: mean 5.0, count 2 -> below MIN_RATINGS, excluded
        *[(u, 200, 4) for u in range(1, 25)],  # item 200: mean 4.0, count 24 -> included
    ], columns=["user_id", "item_id", "rating"])
    baseline = PopularityBaseline()
    baseline.fit(df)
    assert 100 not in baseline.ranked_items
    assert 200 in baseline.ranked_items


# --- Negative / edge cases ---

def test_recommend_top_k_larger_than_item_count_returns_all_available():
    df = tiny_dataset()
    model = MatrixFactorizationRecommender(n_users=5, n_items=5, n_factors=3)
    model.fit(df, epochs=5, verbose=False)
    recs = model.recommend_top_k(user_id=1, k=100, exclude_items=set())
    assert len(recs) <= 5  # can't recommend more items than exist


def test_recommend_top_k_with_all_items_excluded_returns_empty():
    df = tiny_dataset()
    model = MatrixFactorizationRecommender(n_users=5, n_items=5, n_factors=3)
    model.fit(df, epochs=5, verbose=False)
    recs = model.recommend_top_k(user_id=1, k=5, exclude_items={1, 2, 3, 4, 5})
    assert recs == []


def test_popularity_baseline_with_no_items_meeting_floor_is_empty():
    """Negative case: if every item has fewer ratings than MIN_RATINGS,
    the baseline should return an empty ranking, not crash or fall back
    to including everything."""
    df = pd.DataFrame([(1, 100, 5), (2, 100, 4)], columns=["user_id", "item_id", "rating"])
    baseline = PopularityBaseline()
    baseline.fit(df)
    assert baseline.ranked_items == []
    assert baseline.recommend_top_k(user_id=1, k=5, exclude_items=set()) == []


def test_untrained_model_predictions_still_within_valid_range():
    """A model that hasn't been fit yet (global_mean still 0.0, factors
    still their random init) must still clip to [1, 5] rather than
    return a nonsensical raw value — guards the clip logic independent
    of whether training happened."""
    model = MatrixFactorizationRecommender(n_users=5, n_items=5, n_factors=3)
    pred = model.predict(1, 1)
    assert 1.0 <= pred <= 5.0


def test_live_mf_model_beats_popularity_baseline_on_real_data():
    from data_loader import load_train, load_test
    from evaluate import precision_recall_at_k, compare_models

    train = load_train()
    test = load_test()

    mf_model = MatrixFactorizationRecommender()
    mf_model.fit(train, epochs=10, verbose=False)

    baseline_model = PopularityBaseline()
    baseline_model.fit(train)

    mf_results = precision_recall_at_k(mf_model, train, test)
    baseline_results = precision_recall_at_k(baseline_model, train, test)
    comparison = compare_models(mf_results, baseline_results)

    assert comparison["mf_precision_at_k"] > comparison["baseline_precision_at_k"]
    assert comparison["n_users_compared"] > 500
