"""Mixed set of simple and complex questions used to demonstrate routing.
No ground truth needed here — the point is the routing decision and its
cost impact, not answer grading (that's covered by projects 01/02/07)."""

QUERIES = [
    {"id": "q1", "text": "What model does the receiver fleet run on — EC2 or Lambda?", "expected_tier": "simple"},
    {"id": "q2", "text": "What is the retention TTL used for the dedup marker?", "expected_tier": "simple"},
    {"id": "q3", "text": "Who approves a rollback?", "expected_tier": "simple"},
    {"id": "q4", "text": "Walk me through, step by step, why the 2026-02-14 duplicate-alarm incident happened, why the existing dedup safeguard didn't catch it, and explain how the fix specifically closes the race condition described.", "expected_tier": "complex"},
    {"id": "q5", "text": "Compare the tradeoffs between the EC2-based ingestion path and the serverless ALB+Lambda path, and explain under what failure scenario each one would independently keep the platform available.", "expected_tier": "complex"},
    {"id": "q6", "text": "Design an argument for why adaptive per-cycle batch sizing is preferable to permanently provisioning for peak capacity, accounting for both the 200x volume swings and 265,000x payload swings mentioned in the architecture doc.", "expected_tier": "complex"},
]
