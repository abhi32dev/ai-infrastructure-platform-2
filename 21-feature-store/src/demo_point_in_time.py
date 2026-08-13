"""Proves the actual reason feature stores exist: point-in-time-correct
historical feature retrieval. Queries user 1's features AS OF a timestamp
BEFORE their most recent update — the correct answer is the OLDER feature
value (avg_rating_given=3.0), not the latest one (4.2). A plain "SELECT
latest row" query would get this wrong and leak future information into
a training set — exactly the training/serving skew and data-leakage bugs
a feature store's point-in-time join exists to prevent.
"""

import pandas as pd
from datetime import datetime
from feast import FeatureStore

STORE_PATH = "../feature_repo" if __name__ != "__main__" else "feature_repo"


def run_point_in_time_query(store: FeatureStore) -> pd.DataFrame:
    # entity_df: "as of this timestamp, what would this training example
    # have seen for user 1's features" — deliberately set to a time
    # BETWEEN user 1's first and second recorded snapshots
    entity_df = pd.DataFrame({
        "user_id": [1, 1, 2],
        "event_timestamp": [
            datetime(2026, 1, 15),   # between user 1's day-0 and day-30 snapshots -> should get day-0 values
            datetime(2026, 2, 20),   # after user 1's day-30 snapshot, before day-60 -> should get day-30 values
            datetime(2026, 1, 1),    # exactly at user 2's first snapshot
        ],
    })

    result = store.get_historical_features(
        entity_df=entity_df,
        features=[
            "user_features:avg_rating_given",
            "user_features:num_ratings",
            "user_features:account_age_days",
        ],
    ).to_df()
    return result


def run_online_query(store: FeatureStore) -> dict:
    """The other half of a feature store's job: low-latency lookup of
    the LATEST feature values for real-time serving (not historical
    point-in-time — that's what materialize() populates)."""
    response = store.get_online_features(
        features=[
            "user_features:avg_rating_given",
            "user_features:num_ratings",
            "user_features:account_age_days",
        ],
        entity_rows=[{"user_id": 1}, {"user_id": 2}, {"user_id": 3}],
    )
    return response.to_dict()


if __name__ == "__main__":
    store = FeatureStore(repo_path="../feature_repo")

    print("=== Point-in-time historical retrieval ===")
    historical = run_point_in_time_query(store)
    print(historical.to_string(index=False))

    print("\n=== Online (latest-value) retrieval ===")
    online = run_online_query(store)
    for i, uid in enumerate(online["user_id"]):
        print(f"  user {uid}: avg_rating_given={online['avg_rating_given'][i]}, "
              f"num_ratings={online['num_ratings'][i]}, account_age_days={online['account_age_days'][i]}")
