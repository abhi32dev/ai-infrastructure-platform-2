"""FastAPI wrapper around Ollama with circuit-breaker-gated health checks.

/health   — reports circuit state; a load balancer's health check would
            poll this and pull the instance out of rotation while OPEN.
/generate — the actual inference call; fast-fails with 503 if the circuit
            is OPEN instead of hanging on a downstream that's known-bad.
/metrics  — simple request counters (proxy for what Prometheus/CloudWatch
            would scrape in production, see project 13 for the full
            observability treatment).
"""

import time
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import config
from config import MODEL_NAME, REQUEST_TIMEOUT_SECONDS
from circuit_breaker import CircuitBreaker, CLOSED, OPEN, HALF_OPEN

app = FastAPI(title="Local Model Serving Harness")
breaker = CircuitBreaker()

metrics = {"requests_total": 0, "requests_ok": 0, "requests_failed": 0, "requests_rejected_open_circuit": 0}


class GenerateRequest(BaseModel):
    prompt: str
    model: str | None = None


class GenerateResponse(BaseModel):
    response: str
    model: str
    latency_sec: float


@app.get("/health")
async def health():
    snapshot = breaker.snapshot()
    healthy = snapshot["state"] != OPEN
    return {
        "healthy": healthy,
        "circuit_state": snapshot["state"],
        "consecutive_failures": snapshot["consecutive_failures"],
        "model": MODEL_NAME,
    }


@app.get("/metrics")
async def get_metrics():
    return metrics


@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    metrics["requests_total"] += 1

    if not breaker.allow_request():
        metrics["requests_rejected_open_circuit"] += 1
        raise HTTPException(
            status_code=503,
            detail="circuit open: downstream model server is currently marked unhealthy",
        )

    model = req.model or MODEL_NAME
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{config.OLLAMA_URL}/api/generate",
                json={"model": model, "prompt": req.prompt, "stream": False},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        breaker.record_failure()
        metrics["requests_failed"] += 1
        raise HTTPException(status_code=502, detail=f"downstream call failed: {e}")

    breaker.record_success()
    metrics["requests_ok"] += 1
    latency = time.time() - start
    return GenerateResponse(response=data.get("response", ""), model=model, latency_sec=latency)
