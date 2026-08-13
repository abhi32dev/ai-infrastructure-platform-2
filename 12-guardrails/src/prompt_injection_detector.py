"""Heuristic prompt-injection detection: pattern-matches common injection
phrasings (instruction override, role-hijack, system-prompt exfiltration
attempts). Like the PII detector, deliberately simple and auditable rather
than a black-box classifier — the point of a guardrail is that you can
explain exactly why it fired.
"""

import re

INJECTION_PATTERNS = [
    re.compile(r"ignore (all |the )?(previous|prior|above) instructions", re.I),
    re.compile(r"disregard (all |the )?(previous|prior|above) (instructions|rules|prompt)", re.I),
    re.compile(r"you are now\b", re.I),
    re.compile(r"act as (if you (are|were)|a) (an?\s+)?(unrestricted|jailbroken|dan)\b", re.I),
    re.compile(r"reveal (your |the )?(system prompt|instructions)", re.I),
    re.compile(r"print (your |the )?(system prompt|initial instructions)", re.I),
    re.compile(r"pretend (you have no|there are no) (restrictions|rules|guardrails)", re.I),
    re.compile(r"\bDAN\b.*mode", re.I),
]


def detect_prompt_injection(text: str) -> list[str]:
    hits = []
    for pattern in INJECTION_PATTERNS:
        if pattern.search(text):
            hits.append(pattern.pattern)
    return hits
