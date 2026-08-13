"""SQLite-backed cost ledger: one row per request, recording whether it
was a cache hit and what it would have cost either way — durable so the
dashboard can be regenerated from history without re-running any queries.
"""

import sqlite3
import time
from pathlib import Path

from config import LEDGER_DB

SCHEMA = """
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL,
    query TEXT,
    cache_hit INTEGER,
    similarity REAL,
    tokens INTEGER,
    actual_cost_usd REAL,
    would_be_cost_usd REAL
)
"""


def get_connection(db_path: Path = LEDGER_DB) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute(SCHEMA)
    return conn


def log_request(conn, query: str, cache_hit: bool, similarity: float | None,
                 tokens: int, actual_cost: float, would_be_cost: float):
    conn.execute(
        "INSERT INTO requests (timestamp, query, cache_hit, similarity, tokens, actual_cost_usd, would_be_cost_usd) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (time.time(), query, int(cache_hit), similarity, tokens, actual_cost, would_be_cost),
    )
    conn.commit()


def summary(conn) -> dict:
    row = conn.execute(
        "SELECT COUNT(*), SUM(cache_hit), SUM(actual_cost_usd), SUM(would_be_cost_usd) FROM requests"
    ).fetchone()
    total, hits, actual_cost, would_be_cost = row
    hits = hits or 0
    actual_cost = actual_cost or 0.0
    would_be_cost = would_be_cost or 0.0
    return {
        "total_requests": total or 0,
        "cache_hits": hits,
        "cache_hit_rate": (hits / total) if total else 0.0,
        "actual_cost_usd": actual_cost,
        "would_be_cost_usd": would_be_cost,
        "savings_usd": would_be_cost - actual_cost,
        "savings_pct": ((would_be_cost - actual_cost) / would_be_cost * 100) if would_be_cost else 0.0,
    }


def reset(db_path: Path = LEDGER_DB):
    if db_path.exists():
        db_path.unlink()
