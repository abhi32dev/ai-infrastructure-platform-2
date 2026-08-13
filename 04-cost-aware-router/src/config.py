from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CHROMA_DIR = Path(__file__).resolve().parent.parent / "chroma_db"

EMBED_MODEL = "nomic-embed-text"
SMALL_MODEL = "llama3.2:1b"   # cheap path
LARGE_MODEL = "qwen2.5:3b"    # expensive path, reserved for hard queries

# Illustrative $/1M-token rates, modeled loosely on published small/large
# hosted-model pricing tiers, used ONLY to translate token counts into a
# dollar-cost narrative for the interview story — Ollama itself is free/local.
SMALL_MODEL_COST_PER_1M_TOKENS = 0.15
LARGE_MODEL_COST_PER_1M_TOKENS = 2.50

COMPLEXITY_ROUTER_MODEL = SMALL_MODEL  # the small model classifies its own limits
