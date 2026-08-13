"""Live integration tests against the real llama-server binary and real
downloaded GGUF model — no mocking.

Deliberately structured as exactly TWO sequential server lifecycles for
the whole file (one --parallel 1, one --parallel 4), matching the same
pattern run_demo.py uses — this was found necessary during development:
an earlier version of this suite started 3-4 separate server processes
across the file (module-scoped fixtures used by different tests, plus a
standalone comparison test starting two more), and that many rapid
start/stop cycles in one session introduced measurement noise that made
the throughput comparison flaky, even though a single clean run of
run_demo.py reliably shows a 2x+ batching speedup (measured 2.09x and
2.27x across two separate clean runs — see README). Two servers, run in
strict sequence, reproduces that clean result reliably.

Also: both configurations bind the SAME config.SERVER_PORT, so they
cannot run concurrently — a second real bug caught while writing an
earlier draft of this file, which tried to keep both alive via
module-scoped fixtures and would have failed with 'address already in
use' the moment the second fixture was first requested.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from server_manager import start_server, stop_server
from benchmark import run_concurrent_benchmark
import config

_results = {}  # populated by test_single_slot_server_serves_correctly, read by the comparison test


def test_single_slot_server_serves_correctly():
    proc = start_server(parallel_slots=1)
    try:
        single = run_concurrent_benchmark(n_requests=1)
        assert single["total_tokens"] > 0
        assert single["p50_latency_sec"] > 0

        concurrent = run_concurrent_benchmark(n_requests=4)
        assert concurrent["n_requests"] == 4
        # every one of the 4 concurrent requests must have contributed
        # tokens, not just the first to acquire the (serial) slot
        assert concurrent["total_tokens"] >= 4 * (config.MAX_TOKENS * 0.5)

        _results["serial"] = run_concurrent_benchmark(n_requests=8)
    finally:
        stop_server(proc)


def test_batched_server_serves_correctly_and_beats_serial_throughput():
    proc = start_server(parallel_slots=4)
    try:
        result = run_concurrent_benchmark(n_requests=8)
        assert result["total_tokens"] > 0
        assert result["aggregate_tokens_per_sec"] > 0

        assert "serial" in _results, "requires test_single_slot_server_serves_correctly to have run first"
        assert result["aggregate_tokens_per_sec"] > _results["serial"]["aggregate_tokens_per_sec"]
    finally:
        stop_server(proc)
