"""Skips cleanly if vllm isn't installed (it lives in a separate venv,
see requirements-vllm.txt) — only runs for real when invoked from
.venv-vllm, where it loads a real model and checks real output."""
import sys
import os

import pytest

pytest.importorskip("vllm")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from vllm_cpu_benchmark import run_batch, MODEL


@pytest.fixture(scope="module")
def llm():
    from vllm import LLM

    return LLM(model=MODEL, enforce_eager=True)


def test_batched_generate_returns_real_tokens(llm):
    result = run_batch(llm, ["The capital of France is", "Water boils at"])
    assert result["n_prompts"] == 2
    assert result["total_tokens"] > 0
    assert result["tokens_per_sec"] > 0


def test_batching_is_faster_than_serial(llm):
    prompts = ["Hello, my name is", "The sky is", "Two plus two equals",
               "The largest planet is", "Python is a", "The ocean is"]
    serial_tokens = 0
    import time
    start = time.perf_counter()
    for p in prompts:
        serial_tokens += run_batch(llm, [p])["total_tokens"]
    serial_elapsed = time.perf_counter() - start
    serial_tps = serial_tokens / serial_elapsed

    batched = run_batch(llm, prompts)

    assert batched["tokens_per_sec"] > serial_tps
