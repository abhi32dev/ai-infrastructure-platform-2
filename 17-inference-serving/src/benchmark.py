"""Fires CONCURRENT_REQUESTS simultaneous completion requests at the
server and measures aggregate throughput (total tokens generated across
all requests / total wall-clock time) and per-request latency — the
exact "throughput under concurrent load, p99 latency" metric named
directly in the 2026 job-market research this project came from.

Run at --parallel 1 (no batching, effectively serial) vs --parallel 4
(continuous batching) to measure the real throughput delta.
"""

import time
import httpx
from concurrent.futures import ThreadPoolExecutor

from config import SERVER_HOST, SERVER_PORT, CONCURRENT_REQUESTS, MAX_TOKENS, PROMPT


def send_one_request(_i: int) -> dict:
    start = time.time()
    resp = httpx.post(
        f"http://{SERVER_HOST}:{SERVER_PORT}/completion",
        json={"prompt": PROMPT, "n_predict": MAX_TOKENS},
        timeout=120.0,
    )
    elapsed = time.time() - start
    data = resp.json()
    tokens_predicted = data.get("timings", {}).get("predicted_n", MAX_TOKENS)
    return {"latency_sec": elapsed, "tokens": tokens_predicted}


def run_concurrent_benchmark(n_requests: int = CONCURRENT_REQUESTS) -> dict:
    start = time.time()
    with ThreadPoolExecutor(max_workers=n_requests) as pool:
        results = list(pool.map(send_one_request, range(n_requests)))
    total_wall_time = time.time() - start

    total_tokens = sum(r["tokens"] for r in results)
    latencies = sorted(r["latency_sec"] for r in results)
    p50 = latencies[len(latencies) // 2]
    p99 = latencies[min(len(latencies) - 1, int(len(latencies) * 0.99))]

    return {
        "n_requests": n_requests,
        "total_wall_time_sec": total_wall_time,
        "total_tokens": total_tokens,
        "aggregate_tokens_per_sec": total_tokens / total_wall_time,
        "p50_latency_sec": p50,
        "p99_latency_sec": p99,
    }
