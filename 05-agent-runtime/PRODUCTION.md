# Production Readiness — Agent Runtime (LangGraph)

## Current state
LangGraph state machine with SQLite checkpointing, idempotency (JSON
file dedup marker), bounded retry, and human-in-the-loop interrupt/resume.
8 tests including a real-file (not `:memory:`) checkpoint-survives-
restart proof and negative cases for idempotency-key isolation and
retry-boundary correctness.

## Design decisions & trade-offs

| Decision | Why | Trade-off accepted |
|---|---|---|
| Static rule for `decide_action` (not an LLM call) | Keeps the graph-mechanics tests 100% deterministic and fast | Doesn't demonstrate integrating a real judge model into the decision node — that's project 02's gate, not wired in here |
| Separate idempotency store from checkpoint DB | Different lifetimes/semantics: workflow progress vs. side-effect completion | Two datastores to keep consistent instead of one |
| No retry backoff delay | Keeps the demo's tests fast (instant retries) | Not representative of a production retry policy, which needs exponential backoff with jitter |

## What's missing for real production use
- **Real judge-model-backed decision node** — `decide_action` is a
  hardcoded set membership check (`RISKY_ACTIONS`); a production version
  would call project 02's evaluation gate for genuinely uncertain
  decisions
- **Exponential backoff on retry** — currently instant retries; a real
  downstream failure needs backoff to avoid hammering an already-struggling
  dependency
- **Idempotency-key TTL** — the JSON dedup store never expires entries;
  a production version needs TTL-based expiry (same pattern as the
  resume's DynamoDB TTL marker) so old keys don't accumulate forever
- **Multi-agent coordination** — this is a single-agent workflow; project
  11's MCP delegation pattern shows agent-to-agent coordination but isn't
  integrated with this project's checkpointing

## Scaling considerations
- SQLite checkpointing is fine for single-process, moderate-throughput
  workflows; a production deployment running many concurrent agent
  workflows across multiple worker processes would need a shared
  checkpoint backend (Postgres-backed LangGraph checkpointer)
- The idempotency JSON file is not safe for concurrent writes from
  multiple processes — a production version needs the same
  Redis/DynamoDB-backed store pattern as project 06/20

## Security & compliance considerations
- Human-in-the-loop approval has no authentication — anything calling
  `Command(resume=True)` is trusted; a production version needs to record
  WHO approved, not just that approval happened
- No audit trail of which actions were auto-approved vs. human-approved
  beyond the in-memory log — should persist to the same durable audit
  pattern as project 02

## Operational readiness
- No metrics on retry rates, checkpoint-resume frequency, or human-
  approval latency — project 13's observability pattern isn't wired in
- No alerting if a workflow gets stuck waiting for human approval
  indefinitely — a production version needs an approval-timeout policy
