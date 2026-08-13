# 05 — Agent Runtime: Checkpointing, Idempotency, Bounded Retry, Human-in-the-Loop

A LangGraph state machine for an automated remediation workflow, built to
demonstrate four reliability properties independently and provably, not
just claim them:

1. **Durable state / checkpointing** — a SQLite-backed checkpointer
   persists graph state to disk. A brand-new process (new `SqliteSaver`
   connection, same `thread_id`) can resume a graph that's paused
   mid-execution.
2. **Idempotency** — a JSON-file dedup marker (stand-in for a DynamoDB TTL
   marker) ensures the same `idempotency_key` never executes the action
   twice, even across separate graph runs.
3. **Bounded retry** — a transient-failure simulation retries up to
   `MAX_ATTEMPTS=3` before giving up, instead of retrying forever or
   failing on the first error.
4. **Human-in-the-loop** — actions in `RISKY_ACTIONS` (delete_data,
   widen_network_access, force_failover) pause the graph via LangGraph's
   `interrupt()` and wait for an explicit approve/reject before executing.

## Maps to resume claims
- "Self-Directed Agent Runtime": durable state, checkpoints, bounded
  retries, idempotency, failure isolation, least-privilege access,
  human-in-the-loop controls
- Mirrors CONDOR's "Checkpointed Self-Healing" and "Three-Pass
  Reconciliation with TTL-Based Idempotency" bullets, applied at
  agent-workflow granularity instead of batch-pipeline granularity

## Setup (isolated venv)

```bash
cd 05-agent-runtime
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
No Ollama needed for this project — the graph logic itself is what's under
test, not an LLM's decision quality (that's projects 02/03/04). The
`decide_action` node uses a static rule (`action in RISKY_ACTIONS`) instead
of an LLM call, deliberately, so the reliability mechanics can be tested
deterministically and fast, with model-based decision-making layered in
separately.

## Run it

```bash
source .venv/bin/activate
cd src
python run_demo.py
```

Runs four scenarios back to back:
- **Scenario 1**: safe action executes immediately, no approval needed.
- **Scenario 2**: risky action pauses for approval — the demo then opens a
  *brand new* checkpointer connection (simulating a process restart) before
  resuming with a rejection, proving the pause survived the "restart."
- **Scenario 3**: the same `idempotency_key` invoked twice — second call
  hits the dedup marker and does not re-execute.
- **Scenario 4**: execution simulates 2 transient failures, succeeds on
  the 3rd attempt (at `MAX_ATTEMPTS`).

## Tests

```bash
cd 05-agent-runtime && source .venv/bin/activate && pytest -q
```
5 tests, all deterministic and fast (in-memory SQLite, no LLM calls):
safe-action execution, interrupt+reject, interrupt+approve, idempotent
no-rerun, and bounded-retry give-up-after-max-attempts.

## What to say in an interview

- **Why SQLite checkpointing instead of in-memory state?** In-memory state
  dies with the process. The whole reliability story here is "if the
  worker process crashes or redeploys mid-workflow, the paused/in-progress
  work is not lost" — that's only provable if state genuinely persists to
  disk and can be reloaded by a *different* process instance, which is
  exactly what the demo's "simulated restart" (a fresh `SqliteSaver`
  connection) proves.
- **Why is the idempotency store a separate file from the checkpoint DB?**
  Different lifetimes and different failure semantics. The checkpoint DB
  tracks *workflow* progress (which node are we on); the idempotency store
  tracks *side-effect* completion (did the real-world action already
  happen). Conflating them risks a bug where replaying a workflow for
  legitimate reasons (e.g., resuming after a crash) accidentally treats a
  not-yet-executed action as already-executed, or vice versa.
- **Why does an unparsable/ambiguous decision not exist here the way it
  does in project 02/04?** This graph's `decide_action` is a static rule,
  not an LLM call, precisely so this project's tests can be 100%
  deterministic. The realistic version would call project 02's
  multi-model gate from inside `decide_action` — that integration is a
  natural next step, not built here to keep this project's test suite fast
  and flake-free.
- **Known limitation to volunteer:** `MAX_ATTEMPTS` retries happen with no
  backoff delay in this demo (each retry is instant) — a production
  version would add exponential backoff with jitter between attempts, the
  same "bounded retries" language used in the CONDOR bullets implies but
  doesn't fully specify here.
