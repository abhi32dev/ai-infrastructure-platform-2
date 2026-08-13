"""Minimal RAG pipeline, self-contained copy of project 01's approach
(own venv, own corpus — never cross-imports another project's code, per
this portfolio's isolation convention), needed here only as the system
UNDER evaluation — the actual point of this project is the two
evaluation frameworks wrapping it, not the pipeline itself.
"""

from pathlib import Path
import shutil

from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CHROMA_DIR = Path(__file__).resolve().parent.parent / "chroma_db"
EMBED_MODEL = "nomic-embed-text"
GEN_MODEL = "llama3.2:1b"

SYSTEM_PROMPT = (
    "Answer the question using ONLY the provided context. "
    "If the context does not contain the answer, say so explicitly."
)


def build_index():
    if CHROMA_DIR.exists():
        shutil.rmtree(CHROMA_DIR)
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=80)
    docs = []
    for path in sorted(DATA_DIR.glob("*.md")):
        text = path.read_text()
        for i, chunk in enumerate(splitter.split_text(text)):
            docs.append(Document(page_content=chunk, metadata={"doc_id": f"{path.name}::{i}"}))

    embeddings = OllamaEmbeddings(model=EMBED_MODEL)
    return Chroma.from_documents(docs, embeddings, collection_name="eval_docs", persist_directory=str(CHROMA_DIR))


def get_vectordb():
    embeddings = OllamaEmbeddings(model=EMBED_MODEL)
    return Chroma(collection_name="eval_docs", embedding_function=embeddings, persist_directory=str(CHROMA_DIR))


def answer_with_contexts(question: str, k: int = 4) -> dict:
    vectordb = get_vectordb()
    retrieved = vectordb.similarity_search(question, k=k)
    contexts = [d.page_content for d in retrieved]

    llm = ChatOllama(model=GEN_MODEL, temperature=0.0)
    context_block = "\n\n".join(contexts)
    response = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Context:\n{context_block}\n\nQuestion: {question}"),
    ])

    return {"question": question, "answer": response.content, "contexts": contexts}
