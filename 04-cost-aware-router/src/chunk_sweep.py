"""Sweeps chunk_size and retrieval_k, measuring the resulting context token
count (= cost) against a deterministic retrieval-quality proxy: whether the
top-k chunks for a question contain the expected keyword. This isolates the
chunking/retrieval-count cost knob from generation cost — the same tuning
the resume's 'Cost-Aware Retrieval & Model Routing' bullet describes.

Deterministic keyword-match proxy is used instead of an LLM judge here on
purpose: it removes a second model's variance from the measurement, so the
sweep result is only a function of chunk_size/k, not judge noise.
"""

import tiktoken
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import DATA_DIR, EMBED_MODEL

encoder = tiktoken.get_encoding("cl100k_base")

EVAL_QUESTIONS = [
    {"q": "What happens when an EC2 receiver fails health checks?", "keyword": "Network Load Balancer"},
    {"q": "How is a duplicate alarm delivery prevented?", "keyword": "compare-and-swap"},
    {"q": "What must an AI-assisted automation change pass before merging?", "keyword": "evaluation gate"},
    {"q": "Who approves a rollback?", "keyword": "platform lead"},
]

CHUNK_SIZE_OPTIONS = [200, 500, 1000]
K_OPTIONS = [2, 4, 6]


def load_docs():
    docs = []
    for path in sorted(DATA_DIR.glob("*.md")):
        docs.append((path.name, path.read_text(encoding="utf-8")))
    return docs


def build_index(chunk_size: int):
    # In-memory (no persist_directory): the sweep builds and discards many
    # collections in one process, and Chroma's sqlite-backed persistence
    # doesn't handle rapid rebuild-in-place cleanly (hit a "readonly
    # database" error reusing one path across iterations). Each config's
    # index only needs to live for the duration of its own measurement.
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=min(80, chunk_size // 4),
        separators=["\n## ", "\n\n", "\n", " ", ""],
    )
    lc_docs = []
    for doc_id, text in load_docs():
        for i, piece in enumerate(splitter.split_text(text)):
            lc_docs.append(Document(page_content=piece, metadata={"doc_id": doc_id, "chunk_id": f"{doc_id}::{i}"}))

    embeddings = OllamaEmbeddings(model=EMBED_MODEL)
    return Chroma.from_documents(lc_docs, embeddings, collection_name=f"sweep_{chunk_size}")


def sweep():
    results = []
    for chunk_size in CHUNK_SIZE_OPTIONS:
        vectordb = build_index(chunk_size)
        for k in K_OPTIONS:
            hits = 0
            total_tokens = 0
            for item in EVAL_QUESTIONS:
                retrieved = vectordb.similarity_search(item["q"], k=k)
                context = "\n".join(d.page_content for d in retrieved)
                total_tokens += len(encoder.encode(context))
                if item["keyword"].lower() in context.lower():
                    hits += 1
            hit_rate = hits / len(EVAL_QUESTIONS)
            avg_tokens = total_tokens / len(EVAL_QUESTIONS)
            results.append({
                "chunk_size": chunk_size, "k": k,
                "hit_rate": hit_rate, "avg_context_tokens": round(avg_tokens, 1),
            })
    return results


if __name__ == "__main__":
    results = sweep()
    print(f"{'chunk_size':10} {'k':3} {'hit_rate':9} {'avg_context_tokens':18}")
    for r in results:
        print(f"{r['chunk_size']:10} {r['k']:3} {r['hit_rate']:9.2f} {r['avg_context_tokens']:18}")

    best = max(results, key=lambda r: (r["hit_rate"], -r["avg_context_tokens"]))
    print(f"\nBest hit_rate-per-token config: chunk_size={best['chunk_size']}, k={best['k']} "
          f"(hit_rate={best['hit_rate']:.2f}, avg_tokens={best['avg_context_tokens']})")
