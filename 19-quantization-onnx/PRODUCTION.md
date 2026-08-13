# Production Readiness — Model Quantization & ONNX Export

## Current state
Real MNIST CNN, ONNX export, dynamic INT8 quantization. Found and fixed a
real ONNX-exporter compatibility bug. Measured a counter-intuitive real
finding: 72.3% size reduction, no accuracy regression, but INT8 was
consistently 3-4x SLOWER than fp32 on this hardware. 3 tests including a
shape-sanity negative check.

## Design decisions & trade-offs

| Decision | Why | Trade-off accepted |
|---|---|---|
| Dynamic (weights-only) quantization | Simplest ONNX Runtime quantization mode, minimal dependency surface | Doesn't avoid runtime dequantization overhead for activations, which static quantization would address — explicitly flagged as the natural next step |
| Legacy TorchScript ONNX exporter (`dynamo=False`) | The newer dynamo-based exporter broke `quantize_dynamic` with a shape-inference error | Using the deprecated export path instead of the new default — will need revisiting as PyTorch phases out the legacy exporter |
| Reported the latency regression honestly | The actual finding, not the comfortable one | A less rigorous writeup could have quietly omitted the latency numbers and only reported the size win |

## What's missing for real production use
- **Static quantization with calibration data** — would likely recover
  the latency benefit dynamic quantization didn't provide here, at the
  cost of needing a representative calibration dataset
- **Hardware-specific validation** — the "INT8 was slower" finding is
  specific to this CPU without native INT8 kernels; a production
  deployment target (server CPU with VNNI, mobile NPU, GPU tensor cores)
  needs its own latency measurement, not an assumption either way
- **Larger model validation** — this demo's CNN is tiny; quantization's
  latency benefit is more likely to materialize at larger model/batch
  sizes where the compute-to-dequantization-overhead ratio favors INT8
- **Migration off the deprecated ONNX exporter** — `dynamo=False` is a
  documented stopgap, not a long-term choice

## Scaling considerations
- The core measurement methodology (compare fp32 vs. int8 on real
  accuracy/size/latency, don't assume the "obvious" tradeoff) applies at
  any model scale
- Larger models / larger batch sizes are exactly where this project's
  finding suggests re-testing before assuming INT8 helps — the
  crossover point (where INT8 becomes faster) isn't determined here

## Security & compliance considerations
- Not directly applicable to this project's scope — no user data
  handling; a production model-optimization pipeline's security concerns
  are mostly about the model-serving layer consuming these artifacts
  (project 09/17), not the export/quantization step itself

## Operational readiness
- No automated regression testing of the accuracy/latency tradeoff as
  part of a CI pipeline — a production MLOps pipeline should re-run this
  comparison automatically whenever the base model changes, similar to
  project 03's regression-gate pattern but applied to quantization
  quality instead of prompt quality
- No deployment-target-specific benchmark suite — this project measured
  one CPU; a production decision needs the same measurement across every
  actual deployment target (different CPU generations, GPU types, mobile
  hardware)
