# 15 — Distributed Training Fundamentals (PyTorch DDP)

Real `torch.distributed` process groups — not a simulation, not a mock —
training a small model across 4 local CPU processes with
`DistributedDataParallel`, proving actual gradient synchronization by
directly measuring that every rank ends up with numerically identical
weights, and contrasting against a no-sync control that diverges.

## Honest scope statement

**This laptop has no multi-GPU cluster.** What's demonstrated here is the
real DDP *protocol* — process groups, `DistributedSampler` sharding,
gradient all-reduce on every `backward()` call — using the `gloo`
CPU-compatible collective backend across local processes instead of the
`nccl` GPU backend across real machines/GPUs. **The training code does
not change between the two** — swapping `BACKEND = "gloo"` for `"nccl"`
and moving tensors to `cuda:N` instead of `cpu` is the entire delta to run
this unchanged on a real multi-GPU cluster. This project proves fluency
with the mechanism, not a claim of having trained on real GPU hardware.

## Maps to the market-gap research
- "Distributed training at scale... PyTorch DDP, FSDP" — named explicitly
  at NVIDIA, Tesla, Perplexity, and Scale AI as a Staff/Principal-level
  requirement (see the job-market research this project came from)

## Setup (isolated venv)

```bash
cd 15-distributed-training
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run it

```bash
source .venv/bin/activate
cd src

python train_ddp.py          # real DDP training, 4 local processes, gloo backend
python train_no_sync.py      # control: same sharded setup, NO gradient sync
python compare_weights.py    # proves DDP ranks are identical, no-sync ranks diverged
```

## Measured results (this run)

```
DDP training across 4 ranks (gloo/CPU backend):
  final loss (rank 0's local batches): 0.6100
  samples in rank 0's shard: 1000
  wall-clock time: 0.34s

Max pairwise L2 weight distance across 4 ranks:
  DDP (synchronized):     0.00000000
  No-sync (independent):  0.3655
```

`N_SAMPLES=4000` sharded across `WORLD_SIZE=4` ranks gives exactly 1000
samples/rank — proving `DistributedSampler` actually partitioned the data
rather than giving every rank the full set. After training, DDP ranks are
**bit-for-bit identical** (L2 distance `0.0`); the no-sync control, trained
on the same disjoint shards with no gradient sharing, diverged to `0.3655`
— each process learned its own private model from only 1/4 of the data.

## Tests

```bash
cd 15-distributed-training && source .venv/bin/activate && pytest -q
```
4 live tests spawning real process groups (no mocking): DDP training
completes and reports from every rank, data is sharded evenly (not
duplicated) across ranks, DDP ranks converge to identical weights, and —
the negative/contrast case — the no-sync control's ranks provably
diverge (proving the identical-weights test above is measuring something
real, not a tautology from identical initialization).

## What to say in an interview

- **Why measure weight distance instead of just trusting DDP's
  documentation?** Because "DDP synchronizes gradients" is a claim;
  measuring `max_pairwise_l2("ddp") == 0.0` directly against a control
  that diverges is proof it actually happened in this specific run, not
  an assumption borrowed from the framework's docs. This is the same
  "prove it, don't claim it" discipline as every other project in this
  portfolio (project 06's real Redis, project 09's real closed-port
  failure).
- **Why does the no-sync control matter, not just the DDP result alone?**
  Without it, "all ranks ended up identical" could trivially be true for
  a boring reason (e.g., if the model never actually updated). The
  control proves the setup is capable of producing divergent results —
  which makes the DDP convergence result meaningful instead of vacuous.
- **Why `gloo` and not attempt to force `nccl` locally?** `nccl` requires
  actual NVIDIA GPUs with NVLink/PCIe interconnects — it isn't a CPU
  fallback option, it's GPU-specific. `gloo` is the correct, standard
  choice for CPU-only distributed training and is what PyTorch's own
  documentation recommends for this exact scenario. Claiming to use nccl
  without GPUs would have been faking it, not substituting honestly.
- **What changes at real multi-GPU scale, concretely?** Three things:
  the backend string (`"gloo"` → `"nccl"`), device placement (tensors
  and the model move to `cuda:{rank}` instead of staying on `cpu`), and
  typically `DistributedDataParallel(model, device_ids=[rank])` instead
  of the CPU-implicit `DistributedDataParallel(model)` used here. The
  process-group setup, `DistributedSampler` sharding, and the
  automatic-all-reduce-on-backward() behavior are identical.
- **Known limitation to volunteer:** this demonstrates data-parallel
  training (DDP) only. FSDP (fully-sharded data parallel — sharding the
  *model's parameters* themselves across ranks, not just the data) is a
  distinct technique for models too large to fit on one device's memory,
  and its sharding/resharding behavior genuinely benefits from GPU memory
  bandwidth in ways that don't demonstrate meaningfully on CPU — that's
  why this project scoped to DDP specifically rather than attempting a
  CPU-only FSDP demo that wouldn't show FSDP's actual value proposition.
