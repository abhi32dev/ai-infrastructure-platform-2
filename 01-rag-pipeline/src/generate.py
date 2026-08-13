"""Stage 6 & 7 — Context Assembly + Generation.

Assembles retrieved chunks into a bounded-size context block, builds a
grounded prompt that instructs the model to answer only from that context
(and say so when it can't), and calls the local Ollama model.
"""

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from config import GEN_MODEL, GEN_TEMPERATURE
from retrieve import retrieve

SYSTEM_PROMPT = (
    "You are an internal engineering assistant for the Aegis platform. "
    "Answer the question using ONLY the provided context. "
    "If the context does not contain the answer, say so explicitly instead "
    "of guessing. Cite which source document(s) you used by filename."
)


def assemble_context(retrieved) -> str:
    blocks = []
    for doc, score in retrieved:
        blocks.append(
            f"[Source: {doc.metadata['doc_id']} | chunk {doc.metadata['chunk_id']} | "
            f"distance={score:.4f}]\n{doc.page_content}"
        )
    return "\n\n---\n\n".join(blocks)


def answer(query: str, k: int | None = None) -> dict:
    retrieved = retrieve(query, k=k) if k else retrieve(query)
    context = assemble_context(retrieved)

    llm = ChatOllama(model=GEN_MODEL, temperature=GEN_TEMPERATURE)
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Context:\n{context}\n\nQuestion: {query}"),
    ]
    response = llm.invoke(messages)

    return {
        "query": query,
        "answer": response.content,
        "sources": [doc.metadata["chunk_id"] for doc, _ in retrieved],
        "context": context,
    }


if __name__ == "__main__":
    import sys
    import json

    query = " ".join(sys.argv[1:]) or "What should I do if a batch is stuck in-progress?"
    result = answer(query)
    print(f"Q: {result['query']}\n")
    print(f"A: {result['answer']}\n")
    print(f"Sources used: {result['sources']}")
