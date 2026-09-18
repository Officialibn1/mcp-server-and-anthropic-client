import os
import asyncio
from mcp.client import Client
from dotenv import load_dotenv
from rich.console import Console
from anthropic import AsyncAnthropic, DefaultAioHttpClient
from utils import add_message, get_user_input, mcp_tools_to_anthropic_tools, upload_file, agent_message_turn, structure_user_message, get_max_tool_call_iteration

load_dotenv()
console = Console()
messages = []

# NO NEED TO VALIDATE BECUASE server.py ALREADY DOES THIS BEFORE RUNNING THE agent.py FILE
TRANSPORT_HOST = os.environ.get("TRANSPORT_HOST")
TRANSPORT_PORT = os.environ.get("TRANSPORT_PORT")

async def start_chat():
    chatting = True
    use_thinking = input("Enable thinking (y/n): ").strip().lower() == 'y'
    allow_streaming = input("Allow streaming of AI response (y/n): ").strip().lower() == 'y'
    max_tool_call_iteration = get_max_tool_call_iteration() or 10
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
                streaming=allow_streaming,
                thinking=use_thinking,
                max_tool_iteration=max_tool_call_iteration
            )

if __name__ == "__main__":
    asyncio.run(start_chat())
