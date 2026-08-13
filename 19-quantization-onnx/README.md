# 19 — Model Quantization & ONNX Export

A small CNN trained on real MNIST, exported to ONNX, then dynamically
quantized to INT8 — measuring file size, accuracy, and latency for both,
rather than assuming quantization is a strict win on every axis.

## Maps to the market-gap research
- "Model optimization" named directly alongside fine-tuning in the
  research as a 2026 in-demand skill, distinct from project 18's
  parameter-efficient *training* — this is post-training *deployment*
  optimization

## Setup (isolated venv)

```bash
cd 19-quantization-onnx
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run it

```bash
source .venv/bin/activate
cd src
python train_and_export.py   # trains, exports fp32 ONNX, quantizes to int8, compares
```

## A real ONNX-exporter compatibility bug hit and fixed

PyTorch's newer "dynamo"-based ONNX exporter (the new default) produced a
graph that broke `onnxruntime`'s `quantize_dynamic` with a shape-inference
error (`Inferred shape and existing shape differ in dimension 0: (784) vs
(64)`). Diagnosed by switching to the legacy TorchScript-based exporter
(`dynamo=False`) — same model, same weights, a more conventional graph
structure that `onnxruntime`'s quantization tooling handles correctly.
Documented in `train_and_export.py` at the exact line, not silently
worked around.

## Measured results (this run, reproduced across repeated evaluations)

| | fp32 ONNX | INT8 ONNX (dynamic quantization) |
|---|---|---|
| File size | 210,076 bytes | 58,248 bytes |
| Accuracy | 0.863 | 0.866 |
| Avg batch latency | 0.32–0.43ms | 1.27–1.41ms |

**Size: −72.3%. Accuracy: no meaningful regression (actually +0.003, well
within noise for a 2-epoch training run). Latency: INT8 was consistently
3–4x *slower*, not faster** — verified by re-running the evaluation twice
more to rule out a one-off warmup artifact; the pattern held every time.

## Why INT8 was slower here — the actual finding of this project

Dynamic quantization stores weights as INT8 but **dequantizes them back
to float at inference time** before the actual matrix multiply, unless
the runtime has a dedicated INT8 compute kernel path for the operation
and hardware in use. For a model this small (a few hundred KB, three
linear/conv layers), the dequantization overhead on this CPU exceeded
whatever compute savings INT8 arithmetic would otherwise provide.
**Quantization's size and (usually) accuracy benefits are close to
unconditional; its latency benefit is not — it depends on model size,
batch size, and whether the target runtime/hardware has real INT8
execution kernels for the ops involved** (server-grade CPUs with VNNI,
mobile NPUs, and GPU INT8 tensor cores are where the latency win shows up
reliably). This is genuinely useful to know and say out loud rather than
assuming "quantized = faster."

## Tests

```bash
cd 19-quantization-onnx && source .venv/bin/activate && pytest -q
```
3 live tests (run `train_and_export.py` first to produce the ONNX
files — tests skip cleanly otherwise): INT8 file size is substantially
smaller (not just marginally), INT8 accuracy doesn't regress by more
than 5 points, and both models produce correctly-shaped (10-class) output
for every sample — a shape-sanity/negative check that the export or
quantization process didn't silently truncate or malform the output.

## What to say in an interview

- **Why report the latency regression instead of quietly only mentioning
  the size win?** Because "quantization made it 72% smaller AND faster"
  would have been a comfortable but false claim on this specific hardware
  and model size — I measured it, found the opposite, verified it wasn't
  noise, and understood *why* before writing it up. That's a stronger
  signal than a clean number that doesn't survive a follow-up question
  about the underlying mechanism.
- **When would INT8 actually be faster here?** At larger batch sizes and
  larger models, where the compute-to-dequantization-overhead ratio
  flips — and on hardware with native INT8 kernels (server CPUs with
  VNNI/AVX-512-VNNI, most mobile NPUs, GPU tensor cores), where the
  runtime doesn't need to dequantize at all before the matmul.
- **Why does the size reduction still matter even without a latency
  win?** Model size drives deployment cost independent of inference
  speed — smaller binaries ship faster to edge devices, use less disk/
  memory footprint in a container, and reduce cold-start pull time in
  serverless/edge deployments. Size and latency are separate axes; this
  project's result is exactly why they need to be measured separately,
  not assumed to move together.
- **Known limitation to volunteer:** this used dynamic (weights-only)
  quantization, the simplest ONNX Runtime quantization mode. Static
  quantization (calibrating activation ranges on a representative
  dataset) typically recovers more of the latency benefit by avoiding
  runtime dequantization for activations too — not exercised here to keep
  the project's dependency surface and calibration-data requirements
  minimal, but the natural next step if latency were the actual
  deployment goal for this specific model.
