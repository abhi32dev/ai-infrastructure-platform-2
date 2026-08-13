from pathlib import Path

EMBED_MODEL = "nomic-embed-text"
GEN_MODEL = "llama3.2:1b"

# Calibrated empirically against nomic-embed-text, not guessed: measured
# cosine similarity for a close paraphrase was 0.79, a looser paraphrase
# 0.57, and an unrelated query 0.47 (see project README). 0.75 sits just
# below the close-paraphrase score with margin above the unrelated score,
# accepting that this catches only near-identical rephrasings, not loose
# paraphrases (a real, stated tradeoff, not a bug).
SIMILARITY_THRESHOLD = 0.75
MODEL_COST_PER_1M_TOKENS = 0.15  # same illustrative rate as project 04, small-model tier

LEDGER_DB = Path(__file__).resolve().parent.parent / "cost_ledger.sqlite"
DASHBOARD_HTML = Path(__file__).resolve().parent.parent / "dashboard.html"
