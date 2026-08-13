"""Control condition: the SAME sharded-data setup as train_ddp.py, but
each process trains its local model with NO gradient synchronization
(plain nn.Module, no DDP wrapper, no all-reduce). This is what "distributed
training" would silently degrade into if DDP were mis-configured or a
process group failed to form — each worker learns its own private model
from only 1/world_size of the data. Used to prove, by contrast, that
DDP's synchronization in train_ddp.py is actually doing something.
"""

from pathlib import Path

import torch
import torch.multiprocessing as mp
import torch.nn as nn
from torch.utils.data import DataLoader

from config import WORLD_SIZE, EPOCHS, BATCH_SIZE_PER_RANK, LR
from model_and_data import SmallMLP, build_dataset

CHECKPOINT_DIR = Path(__file__).resolve().parent.parent / "checkpoints"


def run_worker_no_sync(rank: int, world_size: int, epochs: int):
    dataset = build_dataset()
    # manual sharding identical in spirit to DistributedSampler, but no
    # process group exists to coordinate or synchronize anything
    shard_indices = list(range(rank, len(dataset), world_size))
    shard = torch.utils.data.Subset(dataset, shard_indices)
    loader = DataLoader(shard, batch_size=BATCH_SIZE_PER_RANK, shuffle=True)

    torch.manual_seed(0)  # same init as DDP run, for a fair comparison
    model = SmallMLP()
    optimizer = torch.optim.SGD(model.parameters(), lr=LR)
    loss_fn = nn.BCEWithLogitsLoss()

    for epoch in range(epochs):
        for X, y in loader:
            optimizer.zero_grad()
            logits = model(X)
            loss = loss_fn(logits, y)
            loss.backward()  # NO all-reduce — gradients never leave this process
            optimizer.step()

    CHECKPOINT_DIR.mkdir(exist_ok=True)
    torch.save(model.state_dict(), CHECKPOINT_DIR / f"nosync_rank{rank}.pt")


def train_no_sync(world_size: int = WORLD_SIZE, epochs: int = EPOCHS):
    ctx = mp.get_context("spawn")
    processes = []
    for rank in range(world_size):
        p = ctx.Process(target=run_worker_no_sync, args=(rank, world_size, epochs))
        p.start()
        processes.append(p)
    for p in processes:
        p.join()


if __name__ == "__main__":
    train_no_sync()
    print(f"No-sync control training complete across {WORLD_SIZE} independent processes.")
