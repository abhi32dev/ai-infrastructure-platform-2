"""Stage 1 — Ingestion.

Loads raw source documents from disk. In production this stage would pull
from S3/a document store; here it's local markdown files, but the interface
(return a list of (source_id, raw_text) tuples) is what would change, not
the pipeline downstream of it.
"""

from pathlib import Path
from config import DATA_DIR


def load_documents() -> list[tuple[str, str]]:
    docs = []
    for path in sorted(DATA_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        docs.append((path.name, text))
    return docs


if __name__ == "__main__":
    docs = load_documents()
    print(f"Ingested {len(docs)} documents:")
    for name, text in docs:
        print(f"  - {name} ({len(text)} chars)")
