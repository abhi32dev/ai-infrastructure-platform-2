"""Non-personalized popularity baseline: recommend the globally
highest-average-rated items (with a minimum rating-count floor to avoid
one 5-star rating from a single user topping the list). Every real
recommender project needs this — it's the bar a personalized model has to
clear to justify its existence, same as the resume's 7.4% lift being
measured *against* whatever the platform already did.
"""

import pandas as pd

MIN_RATINGS = 20


class PopularityBaseline:
    def fit(self, train_df: pd.DataFrame):
        stats = train_df.groupby("item_id")["rating"].agg(["mean", "count"])
        stats = stats[stats["count"] >= MIN_RATINGS]
        self.ranked_items = stats.sort_values("mean", ascending=False).index.tolist()
        self.global_mean = train_df["rating"].mean()

    def predict(self, user_id: int, item_id: int) -> float:
        return self.global_mean  # baseline has no per-item prediction beyond ranking

    def recommend_top_k(self, user_id: int, k: int, exclude_items: set[int]) -> list[int]:
        recs = [i for i in self.ranked_items if i not in exclude_items]
        return recs[:k]
