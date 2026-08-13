# Production Readiness — MCP Agent-to-Agent Protocol

## Current state
Real MCP servers (specialist + coordinator) over stdio transport,
verified tool discovery and delegated remediation. Found and fixed a
real state-persistence bug (server lifecycle spanning multiple calls).
8 tests including negative cases (unknown instance, no-match search) and
a regression guard on the coordinator's healthy-instance skip logic.

## Design decisions & trade-offs

| Decision | Why | Trade-off accepted |
|---|---|---|
| stdio transport, not HTTP/SSE | Zero network setup, right for local/same-host tools | Doesn't demonstrate MCP's remote-server capability — a specialist running on a different host needs HTTP/SSE transport, not exercised here |
| Single persistent specialist session per coordinator call | Required for the specialist's in-memory state to persist across the sub-steps of one delegated task | The coordinator holds one long-lived subprocess connection per top-level call rather than reusing a pooled connection across calls |
| In-memory simulated fleet state | Keeps the demo self-contained, no external dependencies | Not representative of a real specialist backed by actual infrastructure APIs (AWS SDK calls, etc.) |

## What's missing for real production use
- **HTTP/SSE transport for remote specialists** — a real deployment would
  have the coordinator and specialist on different hosts/services; stdio
  requires same-host process spawning
- **Authentication between agents** — no credential/identity verification
  between coordinator and specialist; a production MCP deployment needs
  this, especially over network transport
- **Connection pooling** — spawning a fresh specialist subprocess per
  coordinator invocation is wasteful at scale; production would maintain
  a persistent connection pool
- **Real infrastructure backend** — the specialist's tools operate on
  simulated in-memory state; a production specialist would call real AWS/
  Kubernetes/monitoring APIs

## Scaling considerations
- stdio subprocess spawning has real overhead per call — fine for a
  demo's occasional invocations, not viable for high-frequency agent-to-
  agent calls at scale (HTTP with connection reuse would be needed)
- No load balancing across multiple specialist instances — a production
  deployment serving many concurrent coordinator requests would need
  multiple specialist replicas and a way to route between them

## Security & compliance considerations
- No least-privilege scoping on what tools a coordinator can invoke on a
  specialist — any coordinator with a connection can call any exposed
  tool; a production MCP deployment needs per-caller tool authorization
- No audit trail of agent-to-agent delegation — which coordinator called
  which specialist tool, when, with what arguments — needed for
  compliance in any automated-infrastructure-action context

## Operational readiness
- No health check on the specialist before the coordinator attempts to
  delegate to it — a production version needs to detect and handle a
  specialist that's down before wasting a full call cycle
- No timeout on the specialist connection — a hung specialist subprocess
  would hang the coordinator's tool call indefinitely
- No retry/circuit-breaker pattern (project 09's pattern) applied to the
  coordinator-to-specialist connection
