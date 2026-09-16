import sys
import asyncio
import nest_asyncio2
from mcp import ClientSession, StdioServerParameters
from mcp import stdio_client
from pathlib import Path

nest_asyncio2.apply()

try:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
except NameError:
    PROJECT_ROOT = Path.cwd()

SERVER_PATH = PROJECT_ROOT / "server.py"

async def main():
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_PATH)],
        cwd=str(PROJECT_ROOT)
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tool_result = await session.list_tools()
            print("Available tools:", file=sys.stderr)
            for tool in tool_result.tools:
                print(f"    - {tool.name}: {tool.description}", file=sys.stderr)

            for tool in tool_result.tools:
                a = int(input("Enter first number: ").strip())
                b = int(input("Enter second number: ").strip())
                print(f"Calling the {tool.name} tool.")
                result = await session.call_tool(tool.name, arguments={'a': a, "b": b})
                print(f"The result of the tool with arguments {a} and {b} is {result.content[0].text}.")

if __name__ == "__main__":
    asyncio.run(main())
