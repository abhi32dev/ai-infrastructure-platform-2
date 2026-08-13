"""Agent-to-agent handoff over MCP: this is itself an MCP server (exposes
ONE high-level tool, `diagnose_and_remediate_fleet`), but when that tool
runs, it acts as an MCP *client* of the specialist server — spawning it as
a subprocess and calling its lower-level tools to accomplish the subtask.

This is the actual agent-to-agent pattern: a coordinator agent delegates
work to a specialist agent through the same standard protocol it exposes
to ITS OWN callers, rather than the coordinator having the specialist's
logic hardcoded in-process. A caller of the coordinator never needs to
know the specialist server exists — that's an implementation detail behind
one coordinator-level tool call.
"""

from pathlib import Path
from mcp.server.fastmcp import FastMCP
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SPECIALIST_SCRIPT = Path(__file__).resolve().parent / "specialist_server.py"

mcp = FastMCP("aegis-fleet-coordinator")


@mcp.tool()
async def diagnose_and_remediate_fleet(instance_id: str) -> str:
    """High-level coordinator tool: checks an instance's health via the
    specialist agent, restarts it if unhealthy, and cross-references the
    incident log — delegating each low-level step to the specialist server
    over MCP rather than implementing infra access itself."""
    log = []
    server_params = StdioServerParameters(command="python", args=[str(SPECIALIST_SCRIPT)])

    # One persistent specialist session for the whole sub-workflow — the
    # specialist's simulated fleet state lives in that one process's
    # memory, so reusing a single session (instead of spawning a fresh
    # specialist per call) is what makes "restart, then re-check" actually
    # observe the restart's effect.
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            health_result = await session.call_tool("get_instance_health", {"instance_id": instance_id})
            health = health_result.content[0].text
            log.append(f"[coordinator -> specialist] health check: {health}")

            if "unhealthy" in health:
                restart_result = await session.call_tool("restart_instance", {"instance_id": instance_id})
                log.append(f"[coordinator -> specialist] restart: {restart_result.content[0].text}")

                incidents = await session.call_tool("search_incident_log", {"keyword": "health check"})
                log.append(f"[coordinator -> specialist] incident history: {incidents.content[0].text}")

                recheck = await session.call_tool("get_instance_health", {"instance_id": instance_id})
                log.append(f"[coordinator -> specialist] re-check: {recheck.content[0].text}")
            else:
                log.append("[coordinator] instance already healthy, no remediation needed")

    return "\n".join(log)


if __name__ == "__main__":
    mcp.run(transport="stdio")
