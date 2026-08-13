"""Matrix factorization recommender, trained from scratch with mini-batch
SGD (no scikit-learn/surprise library) — every user and item gets a
latent-factor vector; predicted rating is their dot product plus bias
terms. This is the same 'build a model from first principles' discipline
as the resume's IEEE-published classical-ML work, applied here to the
Smith Micro-style production recommender claim.
"""

import numpy as np
import pandas as pd

from config import N_USERS, N_ITEMS, LATENT_FACTORS, LEARNING_RATE, REGULARIZATION, EPOCHS, RNG_SEED


class MatrixFactorizationRecommender:
    def __init__(self, n_users=N_USERS, n_items=N_ITEMS, n_factors=LATENT_FACTORS,
                 lr=LEARNING_RATE, reg=REGULARIZATION, seed=RNG_SEED):
        rng = np.random.default_rng(seed)
        self.n_users = n_users
        self.n_items = n_items
        self.lr = lr
        self.reg = reg

        # 1-indexed MovieLens IDs -> 0-indexed arrays
        self.P = rng.normal(scale=0.1, size=(n_users + 1, n_factors))  # user factors
        self.Q = rng.normal(scale=0.1, size=(n_items + 1, n_factors))  # item factors
        self.user_bias = np.zeros(n_users + 1)
        self.item_bias = np.zeros(n_items + 1)
        self.global_mean = 0.0

    def fit(self, train_df: pd.DataFrame, epochs=EPOCHS, verbose=True):
        self.global_mean = train_df["rating"].mean()
        rows = train_df[["user_id", "item_id", "rating"]].to_numpy()

        rng = np.random.default_rng(RNG_SEED)
        for epoch in range(1, epochs + 1):
            rng.shuffle(rows)
            sq_error_sum = 0.0
            for u, i, r in rows:
                u, i = int(u), int(i)
                pred = self._predict_raw(u, i)
                err = r - pred
                sq_error_sum += err ** 2

                # SGD update
                self.user_bias[u] += self.lr * (err - self.reg * self.user_bias[u])
                self.item_bias[i] += self.lr * (err - self.reg * self.item_bias[i])
                p_u = self.P[u].copy()
                self.P[u] += self.lr * (err * self.Q[i] - self.reg * self.P[u])
                self.Q[i] += self.lr * (err * p_u - self.reg * self.Q[i])

            if verbose:
                rmse = np.sqrt(sq_error_sum / len(rows))
                print(f"epoch {epoch}/{epochs}: train RMSE={rmse:.4f}")

    def _predict_raw(self, u: int, i: int) -> float:
        return self.global_mean + self.user_bias[u] + self.item_bias[i] + self.P[u] @ self.Q[i]

    def predict(self, user_id: int, item_id: int) -> float:
        pred = self._predict_raw(user_id, item_id)
        return float(np.clip(pred, 1, 5))

    def recommend_top_k(self, user_id: int, k: int, exclude_items: set[int]) -> list[int]:
        scores = self.global_mean + self.user_bias[user_id] + self.item_bias + self.Q @ self.P[user_id]
        ranked = np.argsort(-scores)
        recs = [int(i) for i in ranked if i not in exclude_items and 1 <= i <= self.n_items]
        return recs[:k]


if __name__ == "__main__":
    from data_loader import load_train, load_test

    train = load_train()
    model = MatrixFactorizationRecommender()
    model.fit(train, epochs=10)

    sample = train.iloc[0]
    pred = model.predict(int(sample.user_id), int(sample.item_id))
    print(f"\nSample prediction: user={sample.user_id} item={sample.item_id} "
          f"actual={sample.rating} predicted={pred:.2f}")
