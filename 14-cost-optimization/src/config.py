from pathlib import Path

EMBED_MODEL = "nomic-embed-text"
GEN_MODEL = "llama3.2:1b"

SIMILARITY_THRESHOLD = 0.92  # cosine similarity above which a cached response is reused
MODEL_COST_PER_1M_TOKENS = 0.15  # same illustrative rate as project 04, small-model tier

LEDGER_DB = Path(__file__).resolve().parent.parent / "cost_ledger.sqlite"
DASHBOARD_HTML = Path(__file__).resolve().parent.parent / "dashboard.html"
