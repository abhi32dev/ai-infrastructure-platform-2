# 11 — MCP (Model Context Protocol) Agent-to-Agent Demo

Two real MCP servers, communicating over the actual protocol (stdio
transport, JSON-RPC under the hood), demonstrating both halves of what MCP
is used for in practice:

1. **Tool exposure** (`specialist_server.py` + `direct_client_demo.py`) —
   a server exposes infrastructure tools; a client discovers them
   dynamically (no hardcoded knowledge of what the server offers) and
   calls them.
2. **Agent-to-agent delegation** (`coordinator_server.py` +
   `agent_to_agent_demo.py`) — a *second* server exposes ONE high-level
   tool, but internally acts as an MCP *client* of the first server to get
   the subtask done. A caller of the coordinator never sees or knows about
   the specialist — that's the actual "agent talking to another agent"
   pattern MCP enables, distinct from project 05's agent calling
   in-process Python functions as tools.

## Maps to the request
- "MCP agent-to-agent and other protocols" — this is the standard protocol
  (not a custom tool-calling scheme) for how one agent exposes capabilities
  to another agent or model client

## Setup (isolated venv)

```bash
cd 11-mcp-agent-protocol
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
No Ollama/LLM needed — this project demonstrates the protocol mechanics
(discovery, tool calls, delegation) independent of any model's reasoning,
the same "test the mechanism deterministically" choice project 05 made for
its graph logic.

## Run it

```bash
source .venv/bin/activate
cd src

python direct_client_demo.py      # plain client <-> specialist server
python agent_to_agent_demo.py     # top-level client <-> coordinator <-> specialist
```

You can also run the specialist server standalone and point any
MCP-compatible client at it (Claude Desktop's MCP config, for example):
```bash
python specialist_server.py
```

## What each demo proves

**`direct_client_demo.py`**: connects to `specialist_server.py`, calls
`list_tools()` and prints what comes back — proving the tool list came
from the server's protocol response, not a hardcoded client-side list —
then runs a scripted diagnose → restart → search-incident-log → re-check
sequence, watching the simulated instance's status actually flip from
unhealthy to healthy across calls.

**`agent_to_agent_demo.py`**: the top-level client's `list_tools()` shows
**only** `diagnose_and_remediate_fleet` — the coordinator's one exposed
tool. Calling it produces a full multi-step remediation trace
(`[coordinator -> specialist] health check...restart...incident
history...re-check`), proving the coordinator internally delegated all
four sub-steps to the specialist over its own MCP client connection,
entirely hidden from the top-level caller.

## Tests

```bash
cd 11-mcp-agent-protocol && source .venv/bin/activate && pytest -q
```
5 live integration tests (real subprocess-spawned MCP servers, no
mocking): specialist tool discovery, restart-changes-state, graceful
handling of an unknown instance ID, proof the coordinator exposes only
its own tool (not the specialist's), and proof the full delegated
remediation trace completes end to end.

## What to say in an interview

- **Why MCP instead of just writing more Python tool functions like
  project 05?** MCP standardizes the *transport and discovery* — any
  MCP-compliant client (Claude Desktop, another team's agent, a different
  language's implementation) can talk to `specialist_server.py` without
  custom integration code, because discovery (`list_tools`) and invocation
  are protocol-level, not a bespoke Python API. Project 05's tools are
  fast and simple because they're in-process function calls; MCP tools are
  the right choice the moment the tool provider and the agent calling it
  are separately deployed, versioned, or owned by different teams.
- **Why does the coordinator hide the specialist entirely?** Encapsulation
  at the agent level, same reasoning as a well-designed microservice
  boundary: the top-level caller has a contract with the coordinator
  (`diagnose_and_remediate_fleet(instance_id)`), and the coordinator is
  free to change *how* it fulfills that contract — swap the specialist for
  a different backend, add a second specialist, change the sub-step order
  — without breaking anyone calling the coordinator.
- **The state-persistence bug I actually hit and fixed:** my first
  version of the coordinator opened a brand-new `stdio_client` connection
  (spawning a fresh specialist subprocess) for *each* of its four calls to
  the specialist. Since the specialist's simulated fleet state lives in
  that process's memory, every fresh spawn reset it — the final "re-check"
  call would have shown the instance as unhealthy again, because it was
  talking to a specialist process that never saw the restart. The fix:
  open one specialist session and reuse it for the whole
  `diagnose_and_remediate_fleet` call. This is a real, general lesson
  about agent-to-agent delegation — session/connection lifetime has to
  match the lifetime of the stateful operation, not be re-established per
  call.
- **Known limitation to volunteer:** both servers use stdio transport
  (subprocess spawn), which is right for local/same-host tools but not for
  a specialist running on a different host — MCP also supports HTTP/SSE
  transport for that case, not exercised here to keep the demo
  dependency-free and runnable with zero network setup.
