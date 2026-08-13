"""Tunable knobs for the pipeline, isolated so cost/quality tradeoffs are
one place to look — this is the same set of knobs referenced by the
'cost-aware retrieval' resume claim (project 04 tunes these against cost)."""

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CHROMA_DIR = Path(__file__).resolve().parent.parent / "chroma_db"

# Stage 2: chunking
CHUNK_SIZE = 500        # characters per chunk
CHUNK_OVERLAP = 80      # characters shared between adjacent chunks

# Stage 3: embedding
EMBED_MODEL = "nomic-embed-text"

# Stage 4/5: retrieval
RETRIEVAL_K = 4          # how many chunks to pull per query
COLLECTION_NAME = "aegis_docs"

# Stage 6: generation
GEN_MODEL = "llama3.2:1b"
GEN_TEMPERATURE = 0.1
