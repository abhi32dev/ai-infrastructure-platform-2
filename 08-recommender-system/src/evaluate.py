"""Offline evaluation: RMSE on held-out ratings, and per-user precision@k /
recall@k (relevance = actual test rating >= RELEVANCE_THRESHOLD), then a
statistical significance test (Welch's t-test, same family as project 07)
comparing the MF model's per-user precision@k against the popularity
baseline's — the same 'confirm the lift is real, not normal variance'
discipline as the resume's recommendation-system bullets.
"""

import numpy as np
from scipy import stats

from config import TOP_K, RELEVANCE_THRESHOLD
from data_loader import load_train, load_test
from matrix_factorization import MatrixFactorizationRecommender
from baseline import PopularityBaseline


def rmse(model, test_df) -> float:
    errors = []
    for row in test_df.itertuples():
        pred = model.predict(row.user_id, row.item_id)
        errors.append((pred - row.rating) ** 2)
    return float(np.sqrt(np.mean(errors)))


def precision_recall_at_k(model, train_df, test_df, k=TOP_K, threshold=RELEVANCE_THRESHOLD):
    """Returns a dict: user_id -> (precision@k, recall@k)."""
    train_items_by_user = train_df.groupby("user_id")["item_id"].apply(set).to_dict()
    relevant_by_user = (
        test_df[test_df["rating"] >= threshold]
        .groupby("user_id")["item_id"].apply(set).to_dict()
    )

    results = {}
    for user_id, relevant_items in relevant_by_user.items():
        if not relevant_items:
            continue
        seen = train_items_by_user.get(user_id, set())
        recs = model.recommend_top_k(user_id, k=k, exclude_items=seen)
        if not recs:
            continue
        hits = len(set(recs) & relevant_items)
        precision = hits / len(recs)
        recall = hits / len(relevant_items)
        results[user_id] = (precision, recall)
    return results


def compare_models(mf_results: dict, baseline_results: dict):
    common_users = set(mf_results) & set(baseline_results)
    mf_precisions = [mf_results[u][0] for u in common_users]
    baseline_precisions = [baseline_results[u][0] for u in common_users]

    t_stat, p_value = stats.ttest_ind(mf_precisions, baseline_precisions, equal_var=False)
    mf_mean = float(np.mean(mf_precisions))
    baseline_mean = float(np.mean(baseline_precisions))
    lift_pct = (mf_mean - baseline_mean) / baseline_mean * 100 if baseline_mean > 0 else float("nan")

    return {
        "n_users_compared": len(common_users),
        "mf_precision_at_k": mf_mean,
        "baseline_precision_at_k": baseline_mean,
        "lift_pct": lift_pct,
        "p_value": float(p_value),
        "significant_at_05": bool(p_value < 0.05),
    }


def run_full_evaluation():
    train = load_train()
    test = load_test()

    print("Training matrix factorization model...")
    mf_model = MatrixFactorizationRecommender()
    mf_model.fit(train, epochs=15)

    print("\nFitting popularity baseline...")
    baseline_model = PopularityBaseline()
    baseline_model.fit(train)

    print("\nComputing RMSE (matrix factorization only — baseline has no per-item prediction)...")
    mf_rmse = rmse(mf_model, test)
    print(f"MF RMSE: {mf_rmse:.4f}")

    print(f"\nComputing precision@{TOP_K} / recall@{TOP_K} per user...")
    mf_results = precision_recall_at_k(mf_model, train, test)
    baseline_results = precision_recall_at_k(baseline_model, train, test)

    comparison = compare_models(mf_results, baseline_results)

    print(f"\n=== Offline evaluation summary ===")
    print(f"RMSE (matrix factorization): {mf_rmse:.4f}")
    print(f"Users compared: {comparison['n_users_compared']}")
    print(f"MF precision@{TOP_K}:       {comparison['mf_precision_at_k']:.4f}")
    print(f"Baseline precision@{TOP_K}: {comparison['baseline_precision_at_k']:.4f}")
    print(f"Lift: {comparison['lift_pct']:+.2f}%")
    print(f"p-value: {comparison['p_value']:.6f} -> "
          f"{'SIGNIFICANT' if comparison['significant_at_05'] else 'NOT significant'} at alpha=0.05")

    return mf_rmse, comparison


if __name__ == "__main__":
    run_full_evaluation()
