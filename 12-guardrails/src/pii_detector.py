"""Regex-based PII detection/redaction. Deliberately not ML-based (no
NER model) — a fast, deterministic, auditable first line of defense that
catches the common, structurally-recognizable PII patterns before a query
ever reaches a model, same idea as the resume's CCPA data-privacy
microservice ('parsed and extracted PII across 45M user records') applied
at request-time instead of batch-time.
"""

import re

PATTERNS = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "phone": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
}


def detect_pii(text: str) -> dict[str, list[str]]:
    findings = {}
    for label, pattern in PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            findings[label] = matches
    return findings


def redact_pii(text: str) -> tuple[str, dict[str, list[str]]]:
    findings = detect_pii(text)
    redacted = text
    for label, pattern in PATTERNS.items():
        redacted = pattern.sub(f"[REDACTED_{label.upper()}]", redacted)
    return redacted, findings
