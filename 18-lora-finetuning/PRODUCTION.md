# Production Readiness — QLoRA Fine-Tuning

## Current state
Real QLoRA (verified genuine 4-bit `Linear4bit` quantization on Apple
Silicon, correcting an initial "CUDA-only" assumption from the research).
Measured 0.242% trainable parameters, 591KB adapter vs. 320MB+ base
model. 3 tests including a negative case confirming trainable parameters
stay scoped to the LoRA adapter only.

## Design decisions & trade-offs

| Decision | Why | Trade-off accepted |
|---|---|---|
| `distilgpt2` (82M params), 24 training examples | Fast, complete local training run proving the mechanism | Not enough model capacity or data to produce fluent instruction-following — explicitly stated as the expected, correctly-scoped result |
| `bnb_4bit_compute_dtype=torch.float32`, not float16 | CPU doesn't reliably support float16 compute the way a GPU does | Doesn't demonstrate the memory/speed profile of a real GPU QLoRA setup, which typically uses float16 or bfloat16 compute |
| `target_modules=["c_attn"]` only | Maximizes parameter efficiency per adapted layer for this small model | A production LoRA setup often targets more modules (all attention + MLP projections) for better task adaptation, at the cost of more trainable parameters |

## What's missing for real production use
- **A model and dataset at real scale** — 82M params / 24 examples proves
  the mechanism; production fine-tuning needs a model in the billions-of-
  parameters range and a dataset sized to the target task (hundreds to
  thousands of examples minimum)
- **Evaluation beyond before/after spot-checking** — this project shows
  qualitative generation differences; production fine-tuning needs
  quantitative evaluation (perplexity on held-out data, task-specific
  metrics, or project 02/22's evaluation-gate patterns)
- **GPU-based QLoRA validation** — confirmed 4-bit quantization works on
  CPU here; production fine-tuning at real model scale needs GPU
  execution, where compute dtype and memory-bandwidth tradeoffs differ
  from this CPU-only demo
- **Adapter merging/deployment pipeline** — the trained adapter is saved
  but not merged into a deployable model or exported for serving (project
  17's inference-serving pattern isn't connected to this project's output)

## Scaling considerations
- Training time scales with model size and dataset size; this demo's
  ~1-minute CPU training doesn't represent real fine-tuning job duration
  (hours on GPU for real model/dataset scale)
- The parameter-efficiency finding (0.242% trainable) generalizes: LoRA's
  relative parameter savings hold at any model scale, though the absolute
  adapter size grows with model size

## Security & compliance considerations
- No data provenance/licensing verification on the training examples —
  a production fine-tuning pipeline needs to verify training data doesn't
  contain sensitive information or violate licensing terms
- No differential privacy or memorization auditing — fine-tuned models
  can memorize and regurgitate training examples; production fine-tuning
  on sensitive data needs explicit memorization testing

## Operational readiness
- No experiment tracking (project 03's MLflow pattern isn't applied
  here) — a real fine-tuning pipeline should track hyperparameters,
  loss curves, and adapter versions systematically
- No automated evaluation gate before an adapter is considered ready to
  deploy — project 02/03's pattern would need to be applied to fine-tuned
  model outputs specifically
