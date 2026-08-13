"""Loads each rank's saved final weights and measures the max pairwise L2
distance between ranks — the actual proof, not just a claim, that DDP
synchronized every rank to an identical model while the no-sync control
diverged into world_size independent models.
"""

from pathlib import Path
from itertools import combinations

import torch

from config import WORLD_SIZE

CHECKPOINT_DIR = Path(__file__).resolve().parent.parent / "checkpoints"


def flatten_state_dict(sd: dict) -> torch.Tensor:
    return torch.cat([v.flatten() for v in sd.values()])


def max_pairwise_l2(prefix: str, world_size: int = WORLD_SIZE) -> float:
    weights = []
    for rank in range(world_size):
        sd = torch.load(CHECKPOINT_DIR / f"{prefix}_rank{rank}.pt")
        weights.append(flatten_state_dict(sd))

    max_dist = 0.0
    for i, j in combinations(range(world_size), 2):
        dist = torch.norm(weights[i] - weights[j]).item()
        max_dist = max(max_dist, dist)
    return max_dist


if __name__ == "__main__":
    ddp_dist = max_pairwise_l2("ddp")
    nosync_dist = max_pairwise_l2("nosync")

    print(f"Max pairwise L2 weight distance across {WORLD_SIZE} ranks:")
    print(f"  DDP (synchronized):     {ddp_dist:.8f}")
    print(f"  No-sync (independent):  {nosync_dist:.4f}")
    print(f"\nDDP ranks converged to {'IDENTICAL' if ddp_dist < 1e-5 else 'DIFFERENT'} weights.")
    print(f"No-sync ranks diverged into {'DIFFERENT' if nosync_dist > 0.01 else 'similar'} models "
          f"(each saw only 1/{WORLD_SIZE} of the data with no gradient sharing).")
