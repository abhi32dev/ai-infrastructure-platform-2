# Production Readiness — Multi-Model Evaluation Gate

## Current state
AND-gate over two independent models (generator + judge) is implemented
and proven: 8 tests cover the gate logic, fail-safe behavior on malformed
model output, and an audit-log regression guard. Measured 5/6 agreement
with human-labeled expectations on a fixed 6-scenario evaluation set.

## Design decisions & trade-offs

| Decision | Why | Trade-off accepted |
|---|---|---|
| AND-gate, not majority vote or averaging | Conservative default — false REJECT costs a manual approval; false APPROVE costs a production incident | Higher false-reject rate than a voting scheme; acceptable given the asymmetric cost |
| Judge reviews raw situation, not generator's rationale | Avoids anchoring bias | Judge can't leverage generator's reasoning even when it's correct — pure independence, no collaboration |
| Two different model families (llama vs qwen) | Independence must come from genuinely different models, not two calls to the same one | Requires maintaining two models instead of one; more operational surface |
| 6-scenario fixed evaluation set | Enough to prove the mechanism | Not enough to certify accuracy at scale — a real deployment needs hundreds of labeled scenarios |

## What's missing for real production use
- **Scenario coverage** — 6 hand-written scenarios is a demonstration
  set, not a certification set; production needs an evaluation set sized
  to the actual decision space, likely hundreds of examples across edge
  cases
- **False-reject-rate monitoring** — the AND-gate's conservative bias
  needs to be tracked in production (too high = approval fatigue, too low
  = the gate isn't catching anything); no dashboard for this here
- **Human-in-the-loop escalation path** — when the gate blocks, nothing
  currently routes the decision to a human reviewer; it just returns
  BLOCKED
- **Judge model versioning** — swapping the judge model isn't tracked;
  project 03 adds this via MLflow but the two aren't integrated

## Scaling considerations
- Gate latency = generator call + judge call, sequential in this
  implementation — could run concurrently to halve wall-clock latency for
  high-throughput automation pipelines
- At high decision volume, the audit log (`logs/audit.jsonl`, append-only
  file) needs to move to a real datastore (DynamoDB, matching the
  resume's actual production pattern) — a flat file doesn't scale past
  single-process access

## Security & compliance considerations
- Audit log captures every decision with full situation/rationale text —
  appropriate for compliance/forensics, but contains no redaction if
  situations include sensitive data (customer IDs, internal system
  details)
- No rate limiting on gate calls — a runaway automation loop could hammer
  both models; project 12's rate limiter pattern isn't wired in here
- Models run locally (Ollama) — no data leaves the machine, which is
  actually a meaningful production advantage for compliance-sensitive
  automation decisions versus a cloud-API judge

## Operational readiness
- No alerting on gate-blocked decisions — a spike in BLOCKED outcomes
  (indicating either a real safety issue or a broken generator) would go
  unnoticed without external monitoring
- No circuit breaker if a model becomes unavailable — project 09
  demonstrates this pattern but it isn't applied to the generator/judge
  calls here; a downstream Ollama outage would hang or error ungracefully
- Audit log has no retention/rotation policy — would grow unbounded in a
  real deployment
