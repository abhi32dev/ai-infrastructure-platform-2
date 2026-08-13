"""A plain MCP client: spawns the specialist server as a subprocess over
stdio, discovers its tools (no hardcoded knowledge of what the server
offers beyond the protocol handshake), and runs a scripted
diagnose-and-remediate sequence by calling those tools.
"""

import asyncio
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_SCRIPT = Path(__file__).resolve().parent / "specialist_server.py"


async def run():
    server_params = StdioServerParameters(command="python", args=[str(SERVER_SCRIPT)])

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Discovered tools (no hardcoded client knowledge — this came from the server):")
            for t in tools.tools:
                print(f"  - {t.name}: {t.description}")

            print("\n--- Scripted diagnose-and-remediate sequence ---")

            health = await session.call_tool("get_instance_health", {"instance_id": "i-002"})
            print("1. health check:", health.content[0].text)

            if "unhealthy" in health.content[0].text:
                restart_result = await session.call_tool("restart_instance", {"instance_id": "i-002"})
                print("2. restart:", restart_result.content[0].text)

                incidents = await session.call_tool("search_incident_log", {"keyword": "health check"})
                print("3. related incident history:\n   " + incidents.content[0].text.replace("\n", "\n   "))

                recheck = await session.call_tool("get_instance_health", {"instance_id": "i-002"})
                print("4. re-check after restart:", recheck.content[0].text)


if __name__ == "__main__":
    asyncio.run(run())
