# 17 — High-Performance LLM Inference Serving

Continuous-batching LLM inference, benchmarked for real: 8 concurrent
requests against the same model on the same hardware, once with
`--parallel 1` (effectively serial) and once with `--parallel 4`
(continuous batching), isolating batching as the only variable.

## Honest scope statement: why llama.cpp, not vLLM

The research this project came from named **vLLM, TensorRT-LLM, SGLang,
and Triton** as the in-demand tools. I tried vLLM first — `pip install
vllm` did not even finish resolving its dependency tree (triton,
CUDA-linked packages) in 3 minutes, because **vLLM's serving stack
targets NVIDIA CUDA**; Apple Silicon support is not a practical path.
Rather than fake it or skip the gap, I substituted **llama.cpp's
`llama-server`**, which has real native Metal/Apple-Silicon support and
implements the same core idea these tools are built around: multiple
in-flight requests sharing compute via a `--parallel N` slot count,
interleaved token-by-token instead of strictly one-at-a-time. vLLM/
TensorRT-LLM add PagedAttention-style KV-cache memory management on top
of this same core idea — the concept under test here (continuous batching
improves throughput under concurrent load) is the same; the
memory-management sophistication is what a real GPU deployment adds.

## Update (2026-08-14): the vLLM finding above is now stale — re-verified, not assumed

Re-tested `pip install vllm` on this same machine and it now succeeds
cleanly (vLLM 0.19.1), building a genuine CPU-mode wheel with no CUDA
required — a real change in vLLM's own ecosystem since this project was
first written, not a mistake in the original finding. Proven with a real
run, not just a successful install: `vllm_cpu_benchmark.py` loads
`Qwen/Qwen2.5-0.5B-Instruct` — the same model this project already
benchmarks with llama.cpp — through vLLM's actual CPU inference engine
and measures real serial-vs-batched throughput via vLLM's own
continuous-batching `LLM.generate()` API:

```
Serial:  256 tokens in 5.23s = 48.9 tok/s
Batched: 256 tokens in 2.21s = 115.8 tok/s
Batching speedup: 2.37x
```

That 2.37x is strikingly close to llama.cpp's independently-measured
2.09–2.27x below — two different engines, two different measurement
harnesses, converging on roughly the same continuous-batching speedup
magnitude, which is a meaningful cross-validation of the underlying
result, not just a coincidence to note in passing. See "Setup: vLLM CPU
benchmark" below to reproduce. The original honest-scope reasoning below
is kept as-written, unedited, because the substitution decision was
correct given what was true at the time — this update is the same
"measure, don't assume" discipline applied a second time, now that the
landscape changed.

## Maps to the market-gap research
- "2026 primary focus is on inference: latency-per-token, throughput
  under concurrent load... p99 latency" — named directly in ML platform
  engineer postings (Together AI, Scale AI)

## Setup

```bash
brew install llama.cpp
cd 17-inference-serving
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

mkdir -p models
curl -sL -o models/qwen2.5-0.5b-instruct-q4_k_m.gguf \
  "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf"
```

## Run it

```bash
source .venv/bin/activate
cd src
python run_demo.py
```

## Setup: vLLM CPU benchmark (2026 update, optional)

Separate from the llama.cpp benchmark above — kept in its own venv
because vLLM's dependency stack is heavy (torch, transformers) and
unrelated to the core llama-server benchmark.

```bash
cd 17-inference-serving
python3 -m venv .venv-vllm && source .venv-vllm/bin/activate
pip install -r requirements-vllm.txt
cd src
python vllm_cpu_benchmark.py
```

Downloads `Qwen/Qwen2.5-0.5B-Instruct` from Hugging Face on first run
(~1GB) and runs entirely on CPU — no GPU, no CUDA, no Docker.

## Measured results (clean run)

```
--- Serial (no continuous batching) (--parallel 1) ---
  8 concurrent requests, 512 total tokens generated
  wall-clock time: 2.72s
  aggregate throughput: 188.4 tokens/sec
  p50 latency: 1.74s | p99 latency: 2.71s

--- Continuous batching (--parallel 4) ---
  8 concurrent requests, 510 total tokens generated
  wall-clock time: 1.30s
  aggregate throughput: 393.0 tokens/sec
  p50 latency: 1.28s | p99 latency: 1.30s

=== Continuous batching speedup: 2.09x aggregate throughput ===
```

A second clean run measured **2.27x**. Both runs show the same pattern:
roughly **2x aggregate throughput** and p99 latency cut by more than
half, from batching alone — identical model, identical hardware, only
the serving concurrency changed.

## A real measurement-methodology finding, found while writing the tests

The first version of this project's test suite started 3–4 separate
`llama-server` processes across the file (one per test/fixture). That
version's throughput comparison was **flaky** — one run showed batched
throughput *losing* to serial (169 vs 184 tok/s) purely from run-to-run
noise, contradicting the clean demo script's consistent ~2x result.
Isolating the cause: rapid server start/stop cycling within one process
session (not the batching mechanism itself) was introducing contention —
likely residual CPU/thermal load from a just-terminated `llama-server`
process affecting the next one's timing. **Fix**: restructured the test
suite to exactly 2 sequential server lifecycles total, matching
`run_demo.py`'s pattern — stable across 3 repeated runs after the fix.
A second, related bug caught while writing an earlier draft: both
configurations bind the same `SERVER_PORT`, so an attempt to keep two
servers alive at once via separate pytest fixtures would have failed
outright with "address already in use" — caught before it ever ran.

## Tests

```bash
cd 17-inference-serving && source .venv/bin/activate && pytest -q
```
2 tests, deliberately exactly 2 server lifecycles total (see finding
above): the serial configuration's correctness (single request, 4
concurrent requests all contribute real tokens) plus recording its
throughput; the batched configuration's correctness plus the actual
regression assertion that its aggregate throughput exceeds the recorded
serial result. Stable across repeated runs after the restructuring above.

## What to say in an interview

- **Why is the vLLM-to-llama.cpp substitution the most important part of
  this project to bring up unprompted?** Because pretending vLLM ran
  here would be a lie an interviewer could catch with one follow-up
  question ("what GPU did you run it on?"). Volunteering the actual
  constraint, the concrete failure (3-minute unresolved pip install), and
  the reasoning for the substitute demonstrates the judgment that matters
  more than the specific tool name — knowing *why* vLLM exists (Paged
  Attention, CUDA kernels) well enough to pick the right stand-in.
- **Why does the flaky-test story matter as much as the 2x number?**
  Because "I measured a 2x speedup" is a much weaker claim than "I
  measured a 2x speedup, then found my own measurement methodology was
  producing an unreliable comparison, diagnosed why, and fixed the
  measurement approach itself." The second one is what separates a
  number from an engineering result.
- **What would change to reproduce this on real GPU-backed
  infrastructure?** Swap `llama-server --parallel N` for `vllm serve
  <model> --max-num-seqs N` (or TensorRT-LLM's equivalent), same
  benchmark harness, same concurrent-request methodology — the
  measurement approach (isolate batching as the only variable, use
  enough concurrent load to make the effect measurable, run clean
  isolated trials) transfers directly; only the serving engine changes.
- **Why re-check a finding you already wrote down as settled?**
  Because "settled" facts about fast-moving tooling have a shelf life —
  vLLM's Apple Silicon CPU support materially improved after this
  project's original vLLM-vs-llama.cpp decision was made and documented.
  Re-running the exact same `pip install vllm` command months later and
  getting a different, better result is itself a finding worth recording,
  not a sign the original work was wrong — the discipline is re-verifying
  periodically, not trusting a written-down conclusion indefinitely.
- **Did you also check Triton Inference Server and TensorRT-LLM the same
  way?** Yes — both remain genuinely infeasible here, for different
  reasons than vLLM's original blocker. TensorRT-LLM has no CPU or ARM
  path at all; it's CUDA-only by design, full stop. Triton *does* publish
  arm64 images, but the only ones that actually exist are built for
  NVIDIA Jetson's integrated-GPU stack (verified directly: the one
  community arm64 image found, `andreasschliebitz/tritonserver:24.08-igpu-s3`,
  targets Jetson iGPU hardware specifically) — there's no generic
  CPU-only arm64 Triton image to `docker pull` and run on a Mac. That's
  a meaningfully different situation from vLLM's, which is worth being
  able to explain precisely rather than lumping "couldn't run any of
  the CUDA-oriented tools" into one vague statement.
- **Known limitation to volunteer:** this benchmarks a 0.5B-parameter
  model on CPU — real production inference-serving decisions are made at
  7B–70B+ parameter scale on GPU, where memory bandwidth and KV-cache
  management (the part llama.cpp does more simply than vLLM's
  PagedAttention) matter far more than they do at this scale. The
  *mechanism* under test (continuous batching improves throughput under
  concurrent load) generalizes; the specific 2x number does not.
