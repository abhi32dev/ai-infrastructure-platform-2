"""The top-level caller only ever talks to the coordinator server. It has
no knowledge of the specialist server's existence, tools, or how the
subtask actually gets done — that delegation is entirely encapsulated
behind the coordinator's one exposed tool. This is what's meant by
'agent-to-agent': the coordinator is itself an agent (an MCP client) from
the specialist's point of view, and an agent (an MCP server) from this
top-level caller's point of view.
"""

import asyncio
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

COORDINATOR_SCRIPT = Path(__file__).resolve().parent / "coordinator_server.py"


async def run():
    server_params = StdioServerParameters(command="python", args=[str(COORDINATOR_SCRIPT)])

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Tools visible to the top-level caller (only the coordinator's):")
            for t in tools.tools:
                print(f"  - {t.name}: {t.description}")

            print("\nCalling the coordinator's single high-level tool for instance i-002...")
            result = await session.call_tool("diagnose_and_remediate_fleet", {"instance_id": "i-002"})
            print("\nCoordinator's response (internally delegated to the specialist agent over MCP):")
            print(result.content[0].text)


if __name__ == "__main__":
    asyncio.run(run())
