import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.mcp_client import mcp_client


async def main() -> None:
    await mcp_client.connect()
    for t in mcp_client.tools:
        print(t.name)
        print(json.dumps(t.inputSchema, indent=2))
        print("---")
    await mcp_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())