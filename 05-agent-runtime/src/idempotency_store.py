"""Stand-in for a DynamoDB TTL-keyed dedup marker (same pattern as the
resume's 'TTL-Based Idempotency' bullet), implemented as a local JSON file
so it survives process restarts, which is the whole point: if the agent
process crashes and is re-run with the same idempotency_key, it must not
re-execute the action.
"""

import json
from pathlib import Path

STORE_PATH = Path(__file__).resolve().parent.parent / "idempotency_store.json"


def _load() -> dict:
    if not STORE_PATH.exists():
        return {}
    return json.loads(STORE_PATH.read_text())


def _save(data: dict):
    STORE_PATH.write_text(json.dumps(data, indent=2))


def has_been_executed(key: str) -> bool:
    return key in _load()


def get_result(key: str):
    return _load().get(key)


def mark_executed(key: str, result: str):
    data = _load()
    data[key] = result
    _save(data)


def reset():
    """Test/demo helper — clears the store."""
    if STORE_PATH.exists():
        STORE_PATH.unlink()
