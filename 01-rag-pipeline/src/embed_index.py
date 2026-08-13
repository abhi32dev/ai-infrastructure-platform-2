"""Stage 3 & 4 — Embedding + Vector Indexing.

Embeds each chunk with a local Ollama embedding model and writes it into a
persistent Chroma collection. Re-running this script wipes and rebuilds the
collection, so it's safe to iterate on chunk_size/overlap and re-index.
"""

import shutil
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

from config import CHROMA_DIR, COLLECTION_NAME, EMBED_MODEL
from ingest import load_documents
from chunking import chunk_documents


def build_index() -> Chroma:
    if CHROMA_DIR.exists():
        shutil.rmtree(CHROMA_DIR)

    docs = load_documents()
    chunks = chunk_documents(docs)

    lc_docs = [
        Document(page_content=c.text, metadata={"doc_id": c.doc_id, "chunk_id": c.chunk_id})
        for c in chunks
    ]

    embeddings = OllamaEmbeddings(model=EMBED_MODEL)
    vectordb = Chroma.from_documents(
        documents=lc_docs,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=str(CHROMA_DIR),
    )
    return vectordb


if __name__ == "__main__":
    vectordb = build_index()
    print(f"Indexed into Chroma at {CHROMA_DIR} "
          f"(collection={COLLECTION_NAME}, embed_model={EMBED_MODEL})")
    print(f"Collection now has {vectordb._collection.count()} vectors.")
