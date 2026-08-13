"""Live tests spawning real torch.distributed process groups (gloo
backend) — no mocking, since the entire point of this project is proving
actual multi-process gradient synchronization happened.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from train_ddp import train_ddp
from train_no_sync import train_no_sync
from compare_weights import max_pairwise_l2


def test_ddp_training_completes_and_reports_all_ranks():
    result = train_ddp(world_size=2, epochs=2)
    assert result["world_size"] == 2
    assert result["final_loss"] is not None
    assert result["n_shard_samples"] > 0


def test_ddp_shards_data_evenly_across_ranks():
    """Regression guard: DistributedSampler must actually partition the
    dataset (not give every rank the full set) — n_shard_samples should
    be roughly total/world_size."""
    from config import N_SAMPLES
    result = train_ddp(world_size=4, epochs=1)
    expected_shard_size = N_SAMPLES // 4
    assert abs(result["n_shard_samples"] - expected_shard_size) <= 1


def test_ddp_ranks_converge_to_identical_weights():
    """The core claim of this project, proven directly: after DDP
    training, every rank's final weights must be (numerically)
    identical, since gradients were all-reduced every step."""
    train_ddp(world_size=4, epochs=3)
    dist = max_pairwise_l2("ddp", world_size=4)
    assert dist < 1e-4


def test_no_sync_control_ranks_diverge():
    """Negative case / contrast: without DDP's synchronization, ranks
    training on disjoint shards must NOT converge to the same weights —
    proves the DDP test above is measuring something real, not a
    tautology (e.g. all ranks trivially starting and staying at the same
    initialization)."""
    train_no_sync(world_size=4, epochs=3)
    dist = max_pairwise_l2("nosync", world_size=4)
    assert dist > 0.01
