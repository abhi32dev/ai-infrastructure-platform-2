"""Runs the concurrent-load benchmark twice against the SAME model on the
SAME hardware — once with --parallel 1 (no continuous batching) and once
with --parallel 4 (continuous batching) — isolating batching as the only
variable, so the throughput delta is attributable to the serving
architecture, not the model or hardware.
"""

from server_manager import start_server, stop_server
from benchmark import run_concurrent_benchmark
from config import CONCURRENT_REQUESTS


def run_config(parallel_slots: int) -> dict:
    print(f"\nStarting llama-server with --parallel {parallel_slots}...")
    proc = start_server(parallel_slots)
    try:
        result = run_concurrent_benchmark(CONCURRENT_REQUESTS)
        result["parallel_slots"] = parallel_slots
        return result
    finally:
        stop_server(proc)


def print_result(label: str, r: dict):
    print(f"\n--- {label} (--parallel {r['parallel_slots']}) ---")
    print(f"  {r['n_requests']} concurrent requests, {r['total_tokens']} total tokens generated")
    print(f"  wall-clock time: {r['total_wall_time_sec']:.2f}s")
    print(f"  aggregate throughput: {r['aggregate_tokens_per_sec']:.1f} tokens/sec")
    print(f"  p50 latency: {r['p50_latency_sec']:.2f}s | p99 latency: {r['p99_latency_sec']:.2f}s")


if __name__ == "__main__":
    serial = run_config(parallel_slots=1)
    print_result("Serial (no continuous batching)", serial)

    batched = run_config(parallel_slots=4)
    print_result("Continuous batching", batched)

    speedup = batched["aggregate_tokens_per_sec"] / serial["aggregate_tokens_per_sec"]
    print(f"\n=== Continuous batching speedup: {speedup:.2f}x aggregate throughput ===")
