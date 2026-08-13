"""Specialist MCP server: exposes a small set of infrastructure tools over
the Model Context Protocol (stdio transport). Any MCP-compliant client —
Claude Desktop, a LangChain agent, or another agent acting as a client —
can discover and call these tools without any custom integration code,
which is the whole point of MCP as a standard versus the ad-hoc
tool-calling wired directly into project 05's agent.

Simulated infrastructure state (in-memory dict) so this server has
something real to report on and mutate, same Aegis-platform theme as
projects 01/02/06.
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("aegis-infra-specialist")

# Simulated fleet state
_INSTANCES = {
    "i-001": {"status": "healthy", "az": "us-west-2a"},
    "i-002": {"status": "unhealthy", "az": "us-west-2b"},
    "i-003": {"status": "healthy", "az": "us-west-2a"},
}

_INCIDENT_LOG = [
    {"id": "inc-101", "keyword": "health check", "summary": "i-002 failed 3 consecutive health checks, auto-restarted"},
    {"id": "inc-102", "keyword": "duplicate alarm", "summary": "duplicate alarm delivery due to race condition, see postmortem 2026-02-14"},
]


@mcp.tool()
def get_instance_health(instance_id: str) -> str:
    """Return the current health status of a given EC2 instance ID."""
    instance = _INSTANCES.get(instance_id)
    if instance is None:
        return f"unknown instance: {instance_id}"
    return f"{instance_id}: status={instance['status']} az={instance['az']}"


@mcp.tool()
def restart_instance(instance_id: str) -> str:
    """Restart the given EC2 instance. Only meaningful if it's unhealthy."""
    instance = _INSTANCES.get(instance_id)
    if instance is None:
        return f"cannot restart unknown instance: {instance_id}"
    instance["status"] = "healthy"
    return f"{instance_id} restarted, status now healthy"


@mcp.tool()
def search_incident_log(keyword: str) -> str:
    """Search past incident summaries for a keyword, return matches."""
    matches = [i for i in _INCIDENT_LOG if keyword.lower() in i["keyword"].lower() or keyword.lower() in i["summary"].lower()]
    if not matches:
        return f"no incidents found matching '{keyword}'"
    return "\n".join(f"{m['id']}: {m['summary']}" for m in matches)


if __name__ == "__main__":
    mcp.run(transport="stdio")
