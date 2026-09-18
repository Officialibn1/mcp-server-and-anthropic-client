import os
from typing import Literal, Optional
from datetime import datetime, timedelta
from mcp.server.mcpserver import MCPServer
from dotenv import load_dotenv
from rich.console import Console

console = Console()
load_dotenv()
TRANSPORT_HOST = os.environ.get("TRANSPORT_HOST")
TRANSPORT_PORT = os.environ.get("TRANSPORT_PORT")

if not TRANSPORT_HOST:
    raise Exception("TRANSPORT_HOST not set in env file.")

if not TRANSPORT_PORT:
    raise Exception("TRANSPORT_PORT not set in env file.")

try:
    TRANSPORT_PORT = int(TRANSPORT_PORT)
except Exception as e:
    console.print(e)
    raise Exception("TRANSPORT_PORT should be a valid number.")

server = MCPServer(
    name="Calculator",
    version="0.0.1",
    description="A simple MCP server calculator"
)

@server.tool()
def add_duration_to_datetime(
    datetime_str: str, duration: int = 0, unit: Literal["seconds", "minutes", "hours", "days", "weeks", "months",  "years"] = "days", input_format="%Y-%m-%d"
):
    """Add or subtract a duration from a datetime and return the resulting date/time.

    Parses `datetime_str` using `input_format`, then shifts it forward (or backward,
    with a negative `duration`) by the given amount of time in the given `unit`.

    Args:
        datetime_str: The starting date/time as a string, e.g. "2026-09-17".
            Must match `input_format`.
        duration: The amount of time to add. Use a negative number to subtract
            (go backward in time). Defaults to 0 (no change).
        unit: The unit `duration` is measured in. One of:
            "seconds", "minutes", "hours", "days", "weeks", "months", "years".
            Defaults to "days".
        input_format: The strptime format string used to parse `datetime_str`.
            Defaults to "%Y-%m-%d" (e.g. "2026-09-17").

    Returns:
        The resulting date/time as a human-readable string, e.g.
        "Thursday, October 15, 2026 12:00:00 AM".
    """
    date = datetime.strptime(datetime_str, input_format)
    # duration = int(duration)
    if unit == "seconds":
        new_date = date + timedelta(seconds=duration)
    elif unit == "minutes":
        new_date = date + timedelta(minutes=duration)
    elif unit == "hours":
        new_date = date + timedelta(hours=duration)
    elif unit == "days":
        new_date = date + timedelta(days=duration)
    elif unit == "weeks":
        new_date = date + timedelta(weeks=duration)
    elif unit == "months":
        month = date.month + duration
        year = date.year + month // 12
        month = month % 12
        if month == 0:
            month = 12
            year -= 1
        day = min(
            date.day,
            [
                31,
                29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                31,
                30,
                31,
                30,
                31,
                31,
                30,
                31,
                30,
                31,
            ][month - 1],
        )
        new_date = date.replace(year=year, month=month, day=day)
    elif unit == "years":
        new_date = date.replace(year=date.year + duration)
    else:
        raise ValueError(f"Unsupported time unit: {unit}")

    return new_date.strftime("%A, %B %d, %Y %I:%M:%S %p")

@server.tool()
def get_current_datetime(date_format: Optional[str] = "%y-%m-%d %H:%M:%S"):
    """Get the current date and time, formatted as a string.

    Returns the current local date/time on the server, formatted according to
    `date_format`.

    Args:
        date_format: A strftime format string controlling the output, e.g.
            "%Y-%m-%d %H:%M:%S" for "2026-09-17 14:30:00", or "%A, %B %d, %Y"
            for "Thursday, September 17, 2026". Cannot be empty. Defaults to
            "%y-%m-%d %H:%M:%S" (note: lowercase %y gives a 2-digit year, e.g.
            "26-09-17").

    Returns:
        The current date/time as a formatted string.

    Raises:
        ValueError: If `date_format` is empty or only whitespace.
    """
    if not date_format or date_format.strip() == "":
        raise ValueError("Date format can'not be empty.")
    return datetime.now().strftime(date_format)

@server.tool()
def set_reminder(content, timestamp):
    # print(f"----\nSetting the following reminder for {timestamp}:\n{content}\n----")
    return(f"----\nSuccessfully set the following reminder for {timestamp}:\n{content}\n----")

@server.resource("greeting://{name}")
def greeting(name: str) -> str:
    return f"Name, {name}"

@server.prompt()
def coding_agent_system_prompt():
    """This is a system prompt that tells the AI agent that it is a professional python programmer"""
    return """You are a professional python programmer with expertise in MCP server design."""

if __name__ == "__main__":
    server.run(transport="streamable-http", host=TRANSPORT_HOST, port=TRANSPORT_PORT)
