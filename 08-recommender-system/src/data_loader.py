"""Loads the official MovieLens 100k ua.base/ua.test split — a fixed,
pre-made 80/20 train/test partition, so results are directly comparable to
published benchmarks (and to yourself across runs) instead of a fresh
random split each time.
"""

import pandas as pd
from config import TRAIN_FILE, TEST_FILE, ITEM_FILE

COLUMNS = ["user_id", "item_id", "rating", "timestamp"]


def load_ratings(path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t", names=COLUMNS, encoding="latin-1")


def load_train() -> pd.DataFrame:
    return load_ratings(TRAIN_FILE)


def load_test() -> pd.DataFrame:
    return load_ratings(TEST_FILE)


def load_item_titles() -> dict[int, str]:
    titles = {}
    with open(ITEM_FILE, encoding="latin-1") as f:
        for line in f:
            parts = line.strip().split("|")
            titles[int(parts[0])] = parts[1]
    return titles


if __name__ == "__main__":
    train = load_train()
    test = load_test()
    print(f"Train: {len(train)} ratings, {train.user_id.nunique()} users, {train.item_id.nunique()} items")
    print(f"Test:  {len(test)} ratings, {test.user_id.nunique()} users, {test.item_id.nunique()} items")
