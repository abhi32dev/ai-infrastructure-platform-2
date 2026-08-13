"""Stage 2 — Chunking.

Splits each document into overlapping windows small enough to embed
meaningfully and retrieve precisely. Overlap prevents a sentence that
straddles a chunk boundary from losing context on either side.

Chunk size is a real cost/quality knob: smaller chunks -> more precise
retrieval but more chunks -> more embedding calls and more tokens spent on
context assembly. See project 04 for how this gets tuned against cost.
"""

from dataclasses import dataclass
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import CHUNK_SIZE, CHUNK_OVERLAP


@dataclass
class Chunk:
    doc_id: str
    chunk_id: str
    text: str


def chunk_documents(docs: list[tuple[str, str]]) -> list[Chunk]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n## ", "\n\n", "\n", " ", ""],
    )
    chunks: list[Chunk] = []
    for doc_id, text in docs:
        pieces = splitter.split_text(text)
        for i, piece in enumerate(pieces):
            chunks.append(Chunk(doc_id=doc_id, chunk_id=f"{doc_id}::{i}", text=piece))
    return chunks


if __name__ == "__main__":
    from ingest import load_documents

    docs = load_documents()
    chunks = chunk_documents(docs)
    print(f"Produced {len(chunks)} chunks from {len(docs)} documents "
          f"(chunk_size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")
    for c in chunks[:3]:
        print(f"\n--- {c.chunk_id} ---\n{c.text[:200]}...")
