"""FastAPI wrapper around the pipeline, so it can be exercised over HTTP
like a real service, not just a CLI. Run with: uvicorn app:app --reload
"""

from fastapi import FastAPI
from pydantic import BaseModel

from config import CHROMA_DIR
from embed_index import build_index
from generate import answer

app = FastAPI(title="Aegis RAG Pipeline")


class QueryRequest(BaseModel):
    question: str
    k: int | None = None


class QueryResponse(BaseModel):
    query: str
    answer: str
    sources: list[str]


@app.on_event("startup")
def ensure_index():
    if not CHROMA_DIR.exists():
        build_index()


@app.get("/health")
def health():
    return {"status": "ok", "index_ready": CHROMA_DIR.exists()}


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
    result = answer(req.question, k=req.k)
    return QueryResponse(query=result["query"], answer=result["answer"], sources=result["sources"])


@app.post("/reindex")
def reindex():
    vectordb = build_index()
    return {"status": "reindexed", "vector_count": vectordb._collection.count()}
