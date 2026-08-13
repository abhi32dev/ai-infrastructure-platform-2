"""Generates a synthetic feature source with MULTIPLE historical rows per
user, each at a different timestamp with different feature values — this
is deliberate: it's the only way to actually prove point-in-time
correctness (the core value proposition of a feature store) instead of
just proving 'a lookup works,' which a plain database table could do too.

Same user-facing theme as project 08's recommender: avg_rating_given,
num_ratings, account_age_days.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

DATA_PATH = Path(__file__).resolve().parent.parent / "feature_repo" / "data" / "user_features.parquet"


def generate():
    rows = []
    base_time = datetime(2026, 1, 1)

    # user 1: three snapshots over time, feature values genuinely change —
    # this is what lets the point-in-time test distinguish "value as of
    # query time" from "latest value"
    rows.append({"user_id": 1, "event_timestamp": base_time, "avg_rating_given": 3.0, "num_ratings": 5, "account_age_days": 10})
    rows.append({"user_id": 1, "event_timestamp": base_time + timedelta(days=30), "avg_rating_given": 3.5, "num_ratings": 12, "account_age_days": 40})
    rows.append({"user_id": 1, "event_timestamp": base_time + timedelta(days=60), "avg_rating_given": 4.2, "num_ratings": 25, "account_age_days": 70})

    # user 2: two snapshots
    rows.append({"user_id": 2, "event_timestamp": base_time, "avg_rating_given": 2.8, "num_ratings": 3, "account_age_days": 5})
    rows.append({"user_id": 2, "event_timestamp": base_time + timedelta(days=45), "avg_rating_given": 3.9, "num_ratings": 18, "account_age_days": 50})

    # user 3: one snapshot
    rows.append({"user_id": 3, "event_timestamp": base_time + timedelta(days=15), "avg_rating_given": 4.5, "num_ratings": 40, "account_age_days": 100})

    df = pd.DataFrame(rows)
    df["created_timestamp"] = df["event_timestamp"]  # required by Feast's file source

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(DATA_PATH)
    print(f"Wrote {len(df)} rows across {df['user_id'].nunique()} users to {DATA_PATH}")
    return df


if __name__ == "__main__":
    generate()
