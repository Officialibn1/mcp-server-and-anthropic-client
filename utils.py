import base64
import filetype
import pyperclip
from rich.live import Live
from mcp.client import Client
from mcp import ListToolsResult
from mcp.types import TextContent
from rich.console import Console
from rich.markdown import Markdown
from typing import Literal, Optional
from anthropic import AsyncAnthropic
from anthropic.types import ToolUseBlock, ServerToolUseBlock, WebSearchToolResultBlock, WebSearchResultBlock, ParsedTextBlock, ParsedMessage


def get_user_input():
    mode = input("""
Type message
or 'p' to paste from clipboard,
or 'f' to upload a file,
or 'exit' to quit:\n> """).strip()
    match mode:
        case "p":
            paste = pyperclip.paste().strip()
            print(f"[Pasted {len(paste)} characters form clipboard.]\n")
            return paste, False
        case "f":
            file_path = input("Enter the file path, starting with '/': \n> ").strip()
            return file_path, True
        case _:
            return mode, False

def add_message(messages: list, content: str | list, agent: Literal["user", "assistant"]):
    message = {
        "role": agent,
        "content": content
    }
    messages.append(message)

def structure_user_message(user_input: str) -> list[dict]:
    return [{
        "type": "document",
        "source": {
            "type": "text",
            "media_type": "text/plain",
            "data": user_input
        }
    }]

def mcp_tools_to_anthropic_tools(mcp_tools: ListToolsResult):
    return [
        {
            "name": tool.name,
            "description": tool.description or "",
            "input_schema": tool.input_schema
        } for tool in mcp_tools.tools
    ]
def print_block_status(block, console: Console):
    match block:
        case ServerToolUseBlock():
            console.print(f"[dim]-> Server tool call: {" ".join(block.name.split("_")).capitalize()}[/dim]", end="\n")
        case WebSearchToolResultBlock():
            for result in block.content:
                if isinstance(result, WebSearchResultBlock):
                    console.print(f"[dim]-> Search result page: [link={result.url}]{result.title}[/link][/dim]", end="\n",)
        case _:
            pass

async def upload_file(client: AsyncAnthropic, file_path: str):
    file_name = file_path.split("/")[-1]
    kind = filetype.guess(file_path)
    if kind is None:
        return None

    media_type: str = kind.mime
    uploaded = await client.files.upload(
        file=(file_name, open(file_path, "rb"), media_type)
    )
    document_type = uploaded.mime_type.split("/")[0]
    return [{
        "type": "document" if document_type == "application" else document_type,
        "source": {
            "type": uploaded.type,
            "file_id": uploaded.id
        },
    }]

async def agent_message_turn(
    client: AsyncAnthropic,
    mcp_client: Client,
    messages: list,
    tools: Optional[list],
    console: Console,
    streaming: bool
):
    total_tool_calls = 0
    while True:
        buffer = ""
        final_message = None
        with Live(console=console, refresh_per_second=5, vertical_overflow="visible") as live:
            async for event_type, data in chat(client=client, messages=messages, tools=tools, streaming=streaming):
                if event_type == "text" and isinstance(data, str):
                    buffer += data
                    live.update(Markdown(buffer))
                if event_type == "block":
                    print_block_status(block=data, console=console)
                elif event_type == "final" and isinstance(data, ParsedMessage):
                    final_message = data

        if final_message:
            add_message(messages=messages, content=final_message.content, agent="assistant")
            tool_results = []
            for block in final_message.content:
                match block:
                    case ToolUseBlock():
                        console.print(f"[dim]-> calling tool: {" ".join(block.name.split("_")).capitalize()} Input:({block.input})[/dim]", end="\n")
                        total_tool_calls += 1
                        try:
                            result = await mcp_client.call_tool(block.name, block.input)

                            # This only extract text contents but can me modified to handle Audio and other result types.
                            result_text = "\n".join(
                                item.text for item in result.content if isinstance(item, TextContent) and hasattr(item, "text")
                            )
                            console.print(f"[dim]-> result of tool:  ({result_text})[/dim] ", end="\n")
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result_text,
                                "is_error": result.is_error or False
                            })
                        except Exception as e:
                            console.print(f"[dim]-> error of calling tool:  ({e})[/dim] ", end="\n\n")
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": str(e),
                                "is_error": True
                            })
                    case ServerToolUseBlock():
                        pass
                    case WebSearchToolResultBlock():
                        pass
                    case ParsedTextBlock():
                        pass
                    case _:
                        console.print(f"Case have not been handled yet. CASE: {block}")

            if final_message.stop_reason != "tool_use":
                break

            if total_tool_calls >= 10:
                tool_results.append(structure_user_message(user_input="You have hit the limit of tools calls per turn.")[0])
                add_message(messages, content=tool_results, agent="user")
                break

            add_message(messages=messages, content=tool_results, agent="user")
        else:
            break


async def chat(
    client: AsyncAnthropic,
    messages: list,
    model: Optional[str] = "claude-sonnet-4-6",
    system: Optional[str] = None,
    tools: Optional[list] = None,
    max_tokens: int = 2048,
    thinking = False,
    streaming = False
):
    config = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens
    }

    if system:
        config["system"] = system

    if tools and len(tools) > 0:
        config["tools"] = tools

    if thinking:
        config["thinking"] = {
            "type": "adaptive"
        }
        config["output_config"] = {
            "effort": "medium"
        }

    if streaming:
        async with client.messages.stream(**config) as stream:
            async for event in stream:
                if event.type == "content_block_delta" and event.delta.type == "text_delta":
                    yield ("text", event.delta.text)
                elif event.type == "content_block_stop":
                    block = stream.current_message_snapshot.content[event.index]
                    if block.type != "text":
                        yield ("block", block)

            final_message = await stream.get_final_message()
            yield ("final", final_message)
    else:
        message = await client.messages.create(**config)
        yield ("final", message)


def read_file_bytes(path: str):
    try:
        with open(path, "rb") as f:
            data = base64.standard_b64encode(f.read()).decode("utf-8")
            return data
    except FileNotFoundError:
        print(f"File not found. Path = {path}")
        return None
    except PermissionError:
        print(f"You dont have permisson to read this file. Path = {path}")
        return None
    except IsADirectoryError:
        print(f"Expected a file but got a directory. Path = {path}")
        return None
    except OSError as e:
        print(f"Could not read file. Path = {path}")
        return None
