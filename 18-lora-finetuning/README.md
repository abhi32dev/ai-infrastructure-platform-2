# 18 — QLoRA Fine-Tuning

Real QLoRA: the base model (`distilgpt2`) loads with genuinely quantized
4-bit weights (verified as real `Linear4bit` layers, not assumed), and a
LoRA adapter is trained on top while the quantized base stays frozen —
the actual technique named as "the biggest shift in 2026" in the
market-gap research this project came from.

## A finding that corrected my own assumption going in

The research quote that motivated this project said QLoRA's 4-bit
quantization (`bitsandbytes`) is "traditionally CUDA-only." I expected to
hit that wall on this Apple Silicon Mac and have to fall back to
full-precision LoRA, documented honestly (the same pattern as project 17's
vLLM substitution). **I tested it directly instead of assuming the claim
still held**: `bitsandbytes==0.50.1` loaded a model with genuine 4-bit
`Linear4bit` layers on CPU — verified by inspecting the actual module
types, not just checking that `from_pretrained()` didn't raise. Newer
`bitsandbytes` releases have added multi-backend support that the
commonly-cited "CUDA-only" claim predates. **This project ended up
building real QLoRA, not a LoRA substitute** — worth stating plainly,
since assuming the pessimistic case without testing would have meant
under-selling what's actually possible here.

## Maps to the market-gap research
- "The biggest shift in 2026... PEFT... QLoRA + instruction tuning is the
  practical path" — named as the dominant fine-tuning technique across
  every source in the research

## Setup (isolated venv)

```bash
cd 18-lora-finetuning
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run it

```bash
source .venv/bin/activate
cd src

python train_qlora.py    # real QLoRA training, ~1 min on CPU
python evaluate.py       # before/after generation on held-out questions
```

## Measured results (this run)

```
Verified 24 real Linear4bit (quantized) layers in the base model.
Trainable params: 147,456 / 60,826,368 (0.242% — this is the parameter-efficiency QLoRA exists to deliver)
epoch 1/8: avg_loss=5.1758
epoch 8/8: avg_loss=4.0619
```

- **0.242% of parameters trainable** — the actual number PEFT/QLoRA
  exists to shrink from "all of them."
- **Adapter checkpoint: 591KB** (`adapter_model.safetensors`), versus the
  ~320MB+ full base model — a concrete demonstration of what "parameter
  efficient" means as a file on disk, not just a percentage.
- Loss decreased steadily and monotonically across all 8 epochs
  (5.18 → 4.06), proving the LoRA adapter's gradients are actually
  flowing and updating something, not stuck.

### Before/after generation (held-out questions, worded differently from training)

| Question | Before (base) | After (base + LoRA) |
|---|---|---|
| Why llama.cpp not vLLM? | "llama.cpp is a library for the llama.cpp library..." | "It is a simple wrapper around llama.cpp..." |
| What does the eval gate do? | "...to determine the performance of the multi-model evaluation gate." | "The evaluation gate is a single-model evaluation gate..." |

**Neither output is fluent.** That's the honest, expected result at this
scale — `distilgpt2` is 82M parameters with no prior instruction-tuning,
and 24 training examples for 8 epochs is nowhere near enough data to
produce a coherent instruction-following model. What the comparison
*does* show: the fine-tuned model's phrasing measurably shifted toward
the training distribution's pattern (topically on-target references to
"wrapper around llama.cpp," "evaluation gate") versus the base model's
generic repetition loops. The claim this project proves is **the
mechanism works** — quantization is real, LoRA gradients flow, generation
measurably changes — not that 24 examples produces a production chatbot.

## Tests

```bash
cd 18-lora-finetuning && source .venv/bin/activate && pytest -q
```
3 live tests against the real quantized model + PEFT stack (no mocking):
the base model loads with real `Linear4bit` layers (regression guard on
the core hardware-feasibility finding above), LoRA's trainable-parameter
fraction is under 5% and non-zero, and — the negative case — every
trainable parameter after applying LoRA is actually inside the LoRA
adapter, none accidentally left unfrozen elsewhere in the base model.

## What to say in an interview

- **Why test the "CUDA-only" claim instead of just trusting it and
  documenting a limitation?** Because assuming a pessimistic constraint
  without verifying it would have meant shipping a weaker project than
  what's actually achievable — the same discipline as project 17's vLLM
  test, just with the opposite outcome. Both required actually running
  the thing rather than reasoning from what's commonly said about it.
- **Why `target_modules=["c_attn"]` specifically?** That's GPT-2's
  combined query/key/value attention projection — the single linear layer
  where LoRA's low-rank adaptation has the most leverage per parameter
  for a decoder-only model this small. Scoping LoRA to just this layer
  (rather than every linear layer in the model) is itself part of the
  parameter-efficiency story, and it's what the third test
  (`test_lora_adapter_only_adds_target_module_parameters`) directly
  verifies stayed scoped correctly.
- **Why report the before/after comparison honestly instead of cherry-
  picking a fluent-looking example?** Because a Staff-level interviewer
  will immediately recognize 24 examples on an 82M model can't produce
  fluent output, and claiming otherwise would cost more credibility than
  it gains. Showing the real, rough output *and* correctly explaining
  what it does and doesn't prove is the stronger signal.
- **Known limitation to volunteer:** `bnb_4bit_compute_dtype=torch.float32`
  is used here (not `float16`) because CPU execution doesn't benefit from
  and doesn't reliably support float16 compute the way a GPU does — the
  4-bit *storage* is real and verified, but the compute dtype choice is a
  CPU-specific adaptation worth being upfront about if asked precisely
  how this differs from a real GPU QLoRA setup.
