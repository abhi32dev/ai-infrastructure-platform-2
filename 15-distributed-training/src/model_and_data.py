"""Small MLP + synthetic binary-classification dataset, deliberately
simple so the point stays on the distributed-training mechanics (process
groups, gradient all-reduce, sharding), not the model architecture."""

import torch
import torch.nn as nn
from torch.utils.data import TensorDataset

from config import N_SAMPLES, N_FEATURES, RNG_SEED


class SmallMLP(nn.Module):
    def __init__(self, in_features=N_FEATURES, hidden=32):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_features, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, 1),
        )

    def forward(self, x):
        return self.net(x).squeeze(-1)


def build_dataset():
    """Same seed on every rank -> every rank sees the identical full
    dataset before sharding, which is what DistributedSampler expects."""
    g = torch.Generator().manual_seed(RNG_SEED)
    X = torch.randn(N_SAMPLES, N_FEATURES, generator=g)
    true_w = torch.randn(N_FEATURES, generator=g)
    logits = X @ true_w
    y = (logits > logits.median()).float()
    return TensorDataset(X, y)
