"""Live tests against the real Feast feature store (local file + SQLite
online store) — no mocking, since the entire point is proving the
point-in-time join logic is actually correct, not assumed.
"""

import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from feast import FeatureStore
from demo_point_in_time import run_point_in_time_query, run_online_query

REPO_PATH = Path(__file__).resolve().parent.parent / "feature_repo"


@pytest.fixture(scope="module")
def store():
    if not (REPO_PATH / "data" / "registry.db").exists():
        pytest.skip("run `feast apply` and `feast materialize` first — see README")
    return FeatureStore(repo_path=str(REPO_PATH))


def test_point_in_time_query_before_second_snapshot_returns_first_snapshot_values(store):
    """The core claim of this project: querying user 1 at a timestamp
    between their first and second recorded snapshots must return the
    FIRST snapshot's values, not the latest — proving no future
    information leaked into a 'historical' query."""
    entity_df = pd.DataFrame({
        "user_id": [1],
        "event_timestamp": [datetime(2026, 1, 15)],  # between day-0 and day-30 snapshots
    })
    result = store.get_historical_features(
        entity_df=entity_df,
        features=["user_features:avg_rating_given", "user_features:num_ratings"],
    ).to_df()

    assert result.iloc[0]["avg_rating_given"] == pytest.approx(3.0)
    assert result.iloc[0]["num_ratings"] == 5
    # explicitly NOT the latest values (4.2, 25) — the negative case that
    # proves this isn't just returning "the row for this user_id"
    assert result.iloc[0]["avg_rating_given"] != pytest.approx(4.2)


def test_point_in_time_query_after_second_snapshot_returns_second_snapshot_values(store):
    entity_df = pd.DataFrame({
        "user_id": [1],
        "event_timestamp": [datetime(2026, 2, 20)],  # between day-30 and day-60 snapshots
    })
    result = store.get_historical_features(
        entity_df=entity_df,
        features=["user_features:avg_rating_given"],
    ).to_df()
    assert result.iloc[0]["avg_rating_given"] == pytest.approx(3.5)


def test_point_in_time_query_before_any_snapshot_drops_the_row():
    """Negative/edge case, and a real finding from building this project:
    querying a user at a timestamp BEFORE their first recorded feature
    snapshot does NOT return a row with null features (which would be
    the naive expectation) — Feast's local file-based offline store
    performs an inner-join-like point-in-time join and DROPS the row
    from the result entirely. Verified directly (see README) rather than
    assumed. This matters operationally: a training pipeline naively
    trusting entity_df's row count would silently lose examples here,
    not silently train on NaN features — a different failure mode than
    expected, worth knowing before it surprises someone in production."""
    store = FeatureStore(repo_path=str(REPO_PATH))
    entity_df = pd.DataFrame({
        "user_id": [2],
        "event_timestamp": [datetime(2025, 12, 1)],  # before user 2's earliest snapshot (2026-01-01)
    })
    result = store.get_historical_features(
        entity_df=entity_df,
        features=["user_features:avg_rating_given"],
    ).to_df()
    assert len(result) == 0


def test_online_retrieval_returns_latest_values_not_historical(store):
    """Contrast case proving the two query modes genuinely differ:
    online retrieval for user 1 must return the LATEST snapshot
    (4.2), the opposite of the point-in-time test above."""
    online = run_online_query(store)
    user1_idx = online["user_id"].index(1)
    assert online["avg_rating_given"][user1_idx] == pytest.approx(4.2, abs=0.01)
