"""Output-side checks: the model's response is scanned before it's
returned, same 'never trust a single pass uncritically' discipline as
project 02's evaluation gate — but here checking mechanical properties
(did the model leak PII it was fed, does it contain a refusal we should
flag) rather than a second model's judgment.
"""

from pii_detector import detect_pii

REFUSAL_MARKERS = [
    "i cannot help with that",
    "i can't assist with",
    "i'm not able to help with",
]


def check_output(response_text: str, redacted_input_findings: dict) -> dict:
    output_pii = detect_pii(response_text)

    # A leak is specifically the model echoing back PII the INPUT guardrail
    # already redacted — proof the redaction didn't just hide it from the
    # model's context, it kept it out of the response too.
    leaked_categories = [cat for cat in redacted_input_findings if cat in output_pii]

    is_refusal = any(marker in response_text.lower() for marker in REFUSAL_MARKERS)

    return {
        "output_pii_found": output_pii,
        "leaked_redacted_categories": leaked_categories,
        "is_refusal": is_refusal,
        "passed": len(leaked_categories) == 0,
    }
