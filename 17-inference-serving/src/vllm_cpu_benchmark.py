"""Real vLLM CPU-mode benchmark on Apple Silicon.

This is a follow-up to this project's original 'honest scope' finding
(vLLM couldn't even resolve its dependency tree on this machine). As of
vLLM 0.19.1 (2026), `pip install vllm` succeeds on macOS arm64 and builds
a genuine CPU inference wheel — no CUDA required. This script proves that
directly: it loads a real model and measures real serial-vs-batched
throughput, the same underlying question project 17's llama.cpp benchmark
answers, using vLLM's own continuous-batching engine instead.

Methodology note: this uses vLLM's offline `LLM.generate()` API with a
list of N prompts in one call (which vLLM internally continuous-batches),
rather than firing N concurrent HTTP requests at `vllm serve` the way
benchmark.py does against llama-server. That's a different measurement
harness, not a different underlying mechanism — noted explicitly rather
than presented as an apples-to-apples repeat of the llama.cpp benchmark.
"""
import time

MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
PROMPTS = [
    "What happens when an EC2 receiver fails its health check?",
    "Explain what a circuit breaker does in distributed systems.",
    "What is the difference between readiness and liveness probes?",
    "Why would a retry loop need a maximum attempt count?",
    "What does idempotency mean for a distributed job queue?",
    "Explain point-in-time correctness for a feature store.",
    "What is the purpose of a dead-letter queue?",
    "Why does continuous batching improve inference throughput?",
]


def run_batch(llm, prompts: list[str], max_tokens: int = 32):
    from vllm import SamplingParams

    params = SamplingParams(max_tokens=max_tokens, temperature=0)
    start = time.perf_counter()
    outputs = llm.generate(prompts, params, use_tqdm=False)
    elapsed = time.perf_counter() - start
    total_tokens = sum(len(o.outputs[0].token_ids) for o in outputs)
    return {
        "n_prompts": len(prompts),
        "elapsed_sec": elapsed,
        "total_tokens": total_tokens,
        "tokens_per_sec": total_tokens / elapsed if elapsed > 0 else 0.0,
    }


def main():
    from vllm import LLM

    print(f"Loading {MODEL} on CPU (vLLM offline engine)...")
    llm = LLM(model=MODEL, enforce_eager=True)

    print("\n--- Serial-equivalent: 1 prompt per generate() call, 8 calls ---")
    serial_total_tokens = 0
    serial_start = time.perf_counter()
    for p in PROMPTS:
        result = run_batch(llm, [p])
        serial_total_tokens += result["total_tokens"]
    serial_elapsed = time.perf_counter() - serial_start
    serial_tps = serial_total_tokens / serial_elapsed

    print(f"Serial: {serial_total_tokens} tokens in {serial_elapsed:.2f}s "
          f"= {serial_tps:.1f} tok/s")

    print("\n--- Batched: all 8 prompts in one generate() call ---")
    batched = run_batch(llm, PROMPTS)
    print(f"Batched: {batched['total_tokens']} tokens in "
          f"{batched['elapsed_sec']:.2f}s = {batched['tokens_per_sec']:.1f} tok/s")

    speedup = batched["tokens_per_sec"] / serial_tps if serial_tps > 0 else 0.0
    print(f"\nBatching speedup: {speedup:.2f}x")

    return {
        "serial_tokens_per_sec": serial_tps,
        "batched_tokens_per_sec": batched["tokens_per_sec"],
        "speedup": speedup,
    }


if __name__ == "__main__":
    main()
