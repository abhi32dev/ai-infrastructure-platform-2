"""Starts/stops llama-server as a subprocess with a configurable number of
parallel decoding slots (--parallel N). This --parallel flag is what
implements continuous batching here: N in-flight requests share GPU/CPU
compute and get interleaved token-by-token instead of running strictly
one-at-a-time — the same core idea vLLM/TensorRT-LLM/SGLang are built
around (their versions add PagedAttention-style KV-cache memory
management on top, which is the part llama.cpp does more simply).
"""

import subprocess
import time
import httpx

from config import MODEL_PATH, SERVER_PORT, SERVER_HOST


def start_server(parallel_slots: int) -> subprocess.Popen:
    proc = subprocess.Popen(
        [
            "llama-server",
            "-m", str(MODEL_PATH),
            "--host", SERVER_HOST,
            "--port", str(SERVER_PORT),
            "--parallel", str(parallel_slots),
            "-c", str(2048 * parallel_slots),  # total context budget split across slots
            "--log-disable",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _wait_for_ready(proc)
    return proc


def _wait_for_ready(proc: subprocess.Popen, timeout: float = 60.0):
    start = time.time()
    url = f"http://{SERVER_HOST}:{SERVER_PORT}/health"
    while time.time() - start < timeout:
        if proc.poll() is not None:
            raise RuntimeError("llama-server exited before becoming ready")
        try:
            r = httpx.get(url, timeout=1.0)
            if r.status_code == 200:
                return
        except httpx.RequestError:
            pass
        time.sleep(0.5)
    raise TimeoutError("llama-server did not become ready in time")


def stop_server(proc: subprocess.Popen):
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
