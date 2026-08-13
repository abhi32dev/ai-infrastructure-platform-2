# Production Readiness — Guardrails Layer

## Current state
Regex-based prompt-injection detection, PII redaction/leak scanning, and
rate limiting, wrapping a real Ollama call. 100% pass rate on an 8-case
red-team suite. 16 tests, the most extensive suite in the portfolio,
covering true/false positives, multi-category redaction, and rate-limiter
isolation.

## Design decisions & trade-offs

| Decision | Why | Trade-off accepted |
|---|---|---|
| Regex/heuristic detectors, not an ML classifier | Auditable (exact reason for firing), zero added latency | Known recall gap — a paraphrased or obfuscated attack not covered by the pattern list passes through undetected, explicitly acknowledged |
| Redact PII rather than block the whole request | Lets legitimate requests through with sensitive values replaced | Requires correctly identifying every PII pattern; a missed pattern leaks through unredacted |
| Output-leak check scoped to categories redacted from THAT input | Avoids false-flagging unrelated PII the model might hallucinate | Doesn't catch a model leaking a DIFFERENT category of sensitive info it wasn't explicitly given |
| Token-bucket rate limiter, in-memory | Simple, correct semantics, no external dependency | Not shared across multiple service instances — each process has its own bucket, allowing higher effective throughput than intended in a multi-instance deployment |

## What's missing for real production use
- **ML-based secondary detection** — the README states this explicitly:
  a production version would add an LLM-based check (project 02's
  pattern) for injection/PII cases regex generalizes poorly to, accepting
  the latency/cost tradeoff for higher recall
- **International PII formats** — phone/ID regex patterns assume US-style
  formats; a global deployment needs locale-aware pattern sets
- **Shared rate-limiter state** — the in-memory limiter doesn't coordinate
  across multiple service replicas; production needs a Redis-backed
  distributed rate limiter (project 06's Redis pattern)
- **Guardrail bypass logging distinct from normal request logging** — 
  blocked/flagged requests should route to a dedicated security-review
  log stream, not just the standard audit trail

## Scaling considerations
- Regex matching is O(patterns × text length) per request — negligible
  cost at any realistic request volume; this layer will never be the
  throughput bottleneck
- Rate limiter needs to move to a shared backend the moment the service
  runs more than one replica, or effective limits become
  `configured_limit × replica_count`

## Security & compliance considerations
- This project IS the security/compliance layer for the rest of the
  portfolio's LLM-calling projects — but it isn't actually wired into any
  of them; each project that calls a model directly (01, 02, 04, etc.)
  bypasses these guardrails entirely in its current form
- No security review of the regex patterns themselves for ReDoS
  (catastrophic backtracking) vulnerability — worth an explicit audit
  before production use, especially for patterns processing untrusted
  user input

## Operational readiness
- No alerting when red-team-style patterns are detected in real traffic —
  a spike in blocked injection attempts should page a security on-call,
  not just increment a counter
- No metrics export (project 13's pattern) on block/flag rates over time
  — needed to tune detection thresholds and catch detector drift
