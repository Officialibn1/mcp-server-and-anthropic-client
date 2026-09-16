from typing import Literal

from mcp.server.mcpserver import MCPServer
from dotenv import load_dotenv

load_dotenv()
server = MCPServer(
    name="Calculator",
    version="0.0.1",
    description="A simple MCP server calculator"
)

@server.tool()
def add(a: int, b: int) -> int:
    """This tool is used to add two numbers"""
    return a + b

@server.tool()
def multiply(a: int, b: int) -> int:
    """This tool is used to multiply two numbers"""
    return a * b

@server.tool()
def divide(a: int, b: int) -> float:
    """This tool divides the first number 'a' by second number 'b'"""
    return a / b

@server.resource("greeting://{name}")
def greeting(name: str) -> str:
    return f"Name, {name}"

@server.prompt()
def coding_agent_system_prompt():
    """This is a system prompt that tells the AI agent that it is a professional python programmer"""
    return """You are a professional python programmer with expertise in MCP server design."""

if __name__ == "__main__":
    transport: Literal["streamable-http", "stdio"] = "streamable-http"
    if transport == "stdio":
        server.run(transport=transport)
    else:
        server.run(transport=transport, host="127.0.0.1", port=2026)
