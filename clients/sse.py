import asyncio
from mcp import Client

async def main():
    async with Client("http://127.0.0.1:2026/mcp") as client:
        print(client.server_info)

        tools_result = await client.list_tools()
        for tool in tools_result.tools:
            print(f"    - {tool.name}: {tool.description}")

if __name__ == "__main__":
    asyncio.run(main())
