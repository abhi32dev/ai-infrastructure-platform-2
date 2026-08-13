"""Real torch.distributed training: WORLD_SIZE local processes, each its
own rank, communicating over the 'gloo' backend (CPU-compatible collective
ops). Each rank trains on a distinct shard of the dataset
(DistributedSampler), and DistributedDataParallel automatically all-reduces
gradients across ranks after every backward() call — this is the exact
protocol real multi-GPU training uses; only the backend name changes to
'nccl' and devices become cuda:N instead of cpu at real scale.

Run standalone: python train_ddp.py
"""

import os
import time
from pathlib import Path

import torch
import torch.distributed as dist
import torch.multiprocessing as mp
import torch.nn as nn
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader, DistributedSampler

from config import WORLD_SIZE, BACKEND, EPOCHS, BATCH_SIZE_PER_RANK, LR
from model_and_data import SmallMLP, build_dataset

CHECKPOINT_DIR = Path(__file__).resolve().parent.parent / "checkpoints"


def setup(rank: int, world_size: int):
    os.environ.setdefault("MASTER_ADDR", "127.0.0.1")
    os.environ.setdefault("MASTER_PORT", "29511")
    dist.init_process_group(backend=BACKEND, rank=rank, world_size=world_size)


def cleanup():
    dist.destroy_process_group()


def run_worker(rank: int, world_size: int, epochs: int, result_queue):
    setup(rank, world_size)

    dataset = build_dataset()
    sampler = DistributedSampler(dataset, num_replicas=world_size, rank=rank, shuffle=True, seed=0)
    loader = DataLoader(dataset, batch_size=BATCH_SIZE_PER_RANK, sampler=sampler)

    torch.manual_seed(0)  # identical initial weights across ranks before DDP broadcast (DDP also broadcasts rank-0's weights at construction, this is belt-and-suspenders)
    model = SmallMLP()
    ddp_model = DDP(model)  # gloo backend, CPU

    optimizer = torch.optim.SGD(ddp_model.parameters(), lr=LR)
    loss_fn = nn.BCEWithLogitsLoss()

    start = time.time()
    final_loss = None
    for epoch in range(epochs):
        sampler.set_epoch(epoch)
        epoch_loss = 0.0
        n_batches = 0
        for X, y in loader:
            optimizer.zero_grad()
            logits = ddp_model(X)
            loss = loss_fn(logits, y)
            loss.backward()  # DDP all-reduces gradients across all ranks here, automatically
            optimizer.step()
            epoch_loss += loss.item()
            n_batches += 1
        final_loss = epoch_loss / n_batches

    elapsed = time.time() - start

    CHECKPOINT_DIR.mkdir(exist_ok=True)
    torch.save(ddp_model.module.state_dict(), CHECKPOINT_DIR / f"ddp_rank{rank}.pt")

    if rank == 0:
        result_queue.put({"final_loss": final_loss, "elapsed_sec": elapsed, "n_shard_samples": len(sampler)})

    cleanup()


def train_ddp(world_size: int = WORLD_SIZE, epochs: int = EPOCHS) -> dict:
    ctx = mp.get_context("spawn")
    result_queue = ctx.Queue()
    processes = []
    for rank in range(world_size):
        p = ctx.Process(target=run_worker, args=(rank, world_size, epochs, result_queue))
        p.start()
        processes.append(p)
    for p in processes:
        p.join()

    result = result_queue.get()
    result["world_size"] = world_size
    return result


if __name__ == "__main__":
    result = train_ddp()
    print(f"DDP training across {result['world_size']} ranks (gloo/CPU backend):")
    print(f"  final loss (rank 0's local batches): {result['final_loss']:.4f}")
    print(f"  samples in rank 0's shard: {result['n_shard_samples']}")
    print(f"  wall-clock time: {result['elapsed_sec']:.2f}s")
