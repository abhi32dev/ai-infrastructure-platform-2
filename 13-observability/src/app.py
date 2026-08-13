"""Exposes the traced pipeline over HTTP with a Prometheus /metrics
endpoint, so Prometheus (see docker-compose.yml) can scrape it on an
interval the same way it would scrape a real production service.
"""

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from traced_pipeline import run_traced_query
from metrics import JUDGE_AGREEMENT_RATE

app = FastAPI(title="Observable RAG Pipeline")


class QueryRequest(BaseModel):
    query: str


@app.post("/query")
def query(req: QueryRequest):
    return run_traced_query(req.query)


@app.get("/metrics")
def metrics():
    # Pulled from project 03's MLflow-tracked eval run in a real
    # integration; hardcoded here since this project is intentionally
    # self-contained (no cross-project runtime dependency).
    JUDGE_AGREEMENT_RATE.set(0.83)
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
def health():
    return {"status": "ok"}
