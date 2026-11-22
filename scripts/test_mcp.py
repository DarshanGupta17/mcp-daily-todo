import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.mcp_client import mcp_client


async def main() -> None:
    await mcp_client.connect()
    print("connected:", mcp_client.connected, flush=True)
    print("tools:", [t.name for t in mcp_client.tools], flush=True)
    result = await mcp_client.call_tool(
        "list_tasks", {"start_date": "2020-01-01", "end_date": "2030-12-31"}
    )
    print("list_tasks count:", result.get("count"), flush=True)
    await mcp_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())