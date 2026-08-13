# Production Readiness — Distributed Training Fundamentals (DDP)

## Current state
Real `torch.distributed` DDP across 4 local CPU processes (gloo
backend). Measured exact weight synchronization (0.0 L2 distance) vs. a
diverging no-sync control (0.3655). 4 tests including a positive/negative
contrast pair proving the sync claim is real, not tautological.

## Design decisions & trade-offs

| Decision | Why | Trade-off accepted |
|---|---|---|
| gloo backend, not nccl | No GPUs available; gloo is the correct CPU-compatible collective backend, not a workaround | Doesn't prove nccl-specific behavior (GPU topology-aware collectives, NVLink utilization) |
| Multiprocessing on one machine, not multiple machines | Demonstrates the process-group protocol without needing a real cluster | Doesn't exercise real network partition/latency scenarios a multi-machine cluster faces |
| Simple MLP + synthetic data | Keeps focus on the DDP mechanics, not the model | Doesn't demonstrate DDP at the memory/communication scale where it actually matters (large models where gradient all-reduce is a real bottleneck) |

## What's missing for real production use
- **Multi-machine validation** — this proves single-machine multi-process
  DDP; a real cluster deployment needs the same code validated across
  actual network-separated nodes with real latency/bandwidth constraints
- **FSDP for large models** — explicitly out of scope (documented): DDP
  replicates the full model on every rank; models too large for one
  device's memory need FSDP's parameter sharding instead
- **Gradient compression/communication optimization** — at real scale,
  naive gradient all-reduce becomes a bandwidth bottleneck; production
  systems often use gradient compression or hierarchical all-reduce
- **Fault tolerance** — no handling for a rank dying mid-training; a real
  multi-day training run needs elastic/fault-tolerant training (e.g.,
  `torchrun` with elastic launch, checkpoint-based recovery)

## Scaling considerations
- The core finding (DDP synchronizes correctly) generalizes directly to
  real GPU clusters — only the backend name and device placement change
- At real scale (hundreds of GPUs), gradient all-reduce communication
  overhead becomes the dominant cost; this demo's 4-process CPU setup
  doesn't surface that bottleneck since the model and data are tiny

## Security & compliance considerations
- Not directly applicable to this project's scope — training
  infrastructure security (network isolation between training nodes,
  secrets management for distributed job launch) is a real concern at
  cluster scale but outside what a local demo can meaningfully
  demonstrate

## Operational readiness
- No training-job orchestration (Slurm, Kubernetes Jobs, Ray) wrapping
  this — a production distributed training job needs a scheduler
  managing node allocation, not manual `torch.multiprocessing.spawn`
- No checkpointing during training (only final weights saved) — a
  real multi-hour/day training run needs periodic checkpointing for
  fault recovery, same pattern as project 05's checkpointing but not
  applied here
