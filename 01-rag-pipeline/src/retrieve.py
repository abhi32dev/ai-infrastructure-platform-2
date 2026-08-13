"""Stage 5 — Retrieval.

Given a query, embeds it with the same embedding model used at index time
and pulls the top-k nearest chunks by vector similarity from Chroma.
"""

from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

from config import CHROMA_DIR, COLLECTION_NAME, EMBED_MODEL, RETRIEVAL_K


def get_vectordb() -> Chroma:
    embeddings = OllamaEmbeddings(model=EMBED_MODEL)
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(CHROMA_DIR),
    )


def retrieve(query: str, k: int = RETRIEVAL_K):
    vectordb = get_vectordb()
    results = vectordb.similarity_search_with_score(query, k=k)
    return results  # list of (Document, distance_score)


if __name__ == "__main__":
    import sys

    query = " ".join(sys.argv[1:]) or "What happens when an EC2 receiver fails health checks?"
    results = retrieve(query)
    print(f"Query: {query}\n")
    for doc, score in results:
        print(f"[score={score:.4f}] {doc.metadata['chunk_id']}")
        print(f"  {doc.page_content[:200]}...\n")
