"""Live integration tests — these spawn the real MCP servers as
subprocesses over stdio, the same way the demo scripts do. No mocking:
the protocol handshake, tool discovery, and delegation are what's under
test.
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SPECIALIST_SCRIPT = Path(__file__).resolve().parent.parent / "src" / "specialist_server.py"
COORDINATOR_SCRIPT = Path(__file__).resolve().parent.parent / "src" / "coordinator_server.py"


@pytest.mark.asyncio
async def test_specialist_exposes_three_tools():
    params = StdioServerParameters(command="python", args=[str(SPECIALIST_SCRIPT)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = {t.name for t in tools.tools}
    assert names == {"get_instance_health", "restart_instance", "search_incident_log"}


@pytest.mark.asyncio
async def test_specialist_restart_changes_health_status():
    params = StdioServerParameters(command="python", args=[str(SPECIALIST_SCRIPT)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            before = await session.call_tool("get_instance_health", {"instance_id": "i-002"})
            assert "unhealthy" in before.content[0].text

            await session.call_tool("restart_instance", {"instance_id": "i-002"})

            after = await session.call_tool("get_instance_health", {"instance_id": "i-002"})
            assert "healthy" in after.content[0].text
            assert "unhealthy" not in after.content[0].text


@pytest.mark.asyncio
async def test_unknown_instance_handled_gracefully():
    params = StdioServerParameters(command="python", args=[str(SPECIALIST_SCRIPT)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("get_instance_health", {"instance_id": "i-does-not-exist"})
    assert "unknown instance" in result.content[0].text


@pytest.mark.asyncio
async def test_coordinator_exposes_only_its_own_tool_not_specialists():
    params = StdioServerParameters(command="python", args=[str(COORDINATOR_SCRIPT)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = {t.name for t in tools.tools}
    # the caller sees ONLY the coordinator's high-level tool — the
    # specialist's tools are an implementation detail, not exposed here
    assert names == {"diagnose_and_remediate_fleet"}


@pytest.mark.asyncio
async def test_coordinator_delegation_produces_full_remediation_trace():
    params = StdioServerParameters(command="python", args=[str(COORDINATOR_SCRIPT)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("diagnose_and_remediate_fleet", {"instance_id": "i-002"})
    text = result.content[0].text
    assert "health check" in text
    assert "restart" in text
    assert "incident history" in text
    assert "re-check" in text
    assert text.strip().endswith("status=healthy az=us-west-2b")


# --- Negative / edge cases ---

@pytest.mark.asyncio
async def test_search_incident_log_no_match_returns_explicit_no_results():
    params = StdioServerParameters(command="python", args=[str(SPECIALIST_SCRIPT)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("search_incident_log", {"keyword": "nonexistent-keyword-xyz"})
    assert "no incidents found" in result.content[0].text


@pytest.mark.asyncio
async def test_restart_unknown_instance_is_rejected_not_silently_ignored():
    params = StdioServerParameters(command="python", args=[str(SPECIALIST_SCRIPT)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("restart_instance", {"instance_id": "i-does-not-exist"})
    assert "cannot restart unknown instance" in result.content[0].text


@pytest.mark.asyncio
async def test_coordinator_skips_remediation_for_already_healthy_instance():
    """Regression guard on the coordinator's branch logic: a healthy
    instance (i-001) must short-circuit to 'no remediation needed'
    without calling restart/search_incident_log at all."""
    params = StdioServerParameters(command="python", args=[str(COORDINATOR_SCRIPT)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("diagnose_and_remediate_fleet", {"instance_id": "i-001"})
    text = result.content[0].text
    assert "already healthy, no remediation needed" in text
    assert "restart" not in text
