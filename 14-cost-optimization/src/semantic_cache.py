"""Embedding-similarity response cache: before calling the LLM, embed the
incoming query and compare it (cosine similarity) against every previously
cached query's embedding. Above SIMILARITY_THRESHOLD, return the cached
response — skipping the LLM call entirely for a near-duplicate query,
not just an exact-string match (a plain dict cache would miss
'How do I restart an unhealthy instance?' matching a cached 'What's the
process to restart an instance that's unhealthy?').
"""

import numpy as np
from langchain_ollama import OllamaEmbeddings

from config import EMBED_MODEL, SIMILARITY_THRESHOLD

_embedder = OllamaEmbeddings(model=EMBED_MODEL)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


class SemanticCache:
    def __init__(self, threshold: float = SIMILARITY_THRESHOLD):
        self.threshold = threshold
        self._entries: list[dict] = []  # {query, embedding, response}

    def lookup(self, query: str) -> dict | None:
        if not self._entries:
            return None
        query_emb = np.array(_embedder.embed_query(query))

        best_entry, best_score = None, -1.0
        for entry in self._entries:
            score = cosine_similarity(query_emb, entry["embedding"])
            if score > best_score:
                best_entry, best_score = entry, score

        if best_score >= self.threshold:
            return {**best_entry, "similarity": best_score}
        return None

    def store(self, query: str, response: str):
        embedding = np.array(_embedder.embed_query(query))
        self._entries.append({"query": query, "embedding": embedding, "response": response})

    def size(self) -> int:
        return len(self._entries)
