import os
import asyncio
from typing import cast
from mcp.client import Client
from dotenv import load_dotenv
from rich.console import Console
from InquirerPy.resolver import prompt
from InquirerPy.validator import EmptyInputValidator
from anthropic import AsyncAnthropic, DefaultAioHttpClient
from utils import add_message, get_user_input, mcp_tools_to_anthropic_tools, upload_file, agent_message_turn, structure_user_message

load_dotenv()
console = Console()
messages = []

TRANSPORT_HOST = os.environ.get("TRANSPORT_HOST")
TRANSPORT_PORT = os.environ.get("TRANSPORT_PORT")

choices = prompt([
    {
        "type": "list",
        "name": "model",
        "message": "Choose a model",
        "choices": ["claude-haiku-4-5", "claude-haiku-4-6", "claude-sonnet-4-6"]
    },
    {
        "type": "confirm",
        "name": "streaming",
        "message": "Do you want to enable streaming?",
        "default": False
    },
    {
        "type": "confirm",
        "name": "thinking",
        "message": "Do you want to enable thinking?",
        "default": False
    },
    {
        "type": "number",
        "name": "max_tool_calls",
        "message": "Set maximum tool calls per message",
        "min_allowed": 3,
        "max_allowed": 10,
        # "float_allowed": True,
        "default": 3,
        "validate": EmptyInputValidator()
    },
])

async def start_chat():
    chatting = True

    async with AsyncAnthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
        http_client=DefaultAioHttpClient()
    ) as client, Client(F"http://{TRANSPORT_HOST}:{TRANSPORT_PORT}/mcp") as mcp_client:
        try:
            tool_result = await mcp_client.list_tools()
            tools = mcp_tools_to_anthropic_tools(tool_result) + [
                {"type": "web_search_20250305", "name": "web_search"}
            ]
        except Exception as e:
            tools = None
            print(f"[dim]-> Failed to get tools from the MCP server, with the following errors: {e} [/dim] ")

        while chatting:
            user_input, is_file = get_user_input()
            if user_input == "":
                print("Your input cannot be empty!")
                continue
            if user_input == "exit":
                chatting = False
                break
            if is_file:
                try:
                    message = await upload_file(client=client, file_path=user_input)
                    if message is None:
                        print(f"Unable to read or upload the data of this file '{user_input}'")
                        continue

                    add_message(messages=messages, content=message, agent="user")
                    continue
                except IndexError:
                    print("Please enter a valid file path starting with '/'!")
                    continue
                except Exception as e:
                    print(f"Something went wrong!!\n\n {e}")
                    continue

            user_message = structure_user_message(user_input)
            add_message(messages=messages, content=user_message, agent="user")
            await agent_message_turn(
                client,
                mcp_client,
                messages,
                tools,
                console,
                model=str(choices["model"]),
                streaming=bool(choices["streaming"]),
                thinking=bool(choices["thinking"]),
                max_tool_iteration=cast(int, choices["max_tool_calls"])
            )

if __name__ == "__main__":
    asyncio.run(start_chat())
