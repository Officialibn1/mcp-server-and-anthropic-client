# Learning MCP — Model Context Protocol with Claude

A hands-on learning project exploring the **Model Context Protocol (MCP)** alongside the **Anthropic Claude API**. It implements a custom MCP server exposing tools, resources, and prompts, and a CLI-based AI agent client that connects to that server and drives multi-turn conversations with tool use, web search, and file uploads.

---

## Architecture Overview

```
┌─────────────────────────────────────┐       ┌──────────────────────────────────────────┐
│            agent.py (client)         │       │            server.py (MCP server)         │
│                                     │       │                                          │
│  AsyncAnthropic (Claude API)        │       │  MCPServer — streamable-http transport   │
│  ↕ streaming / tool use loop        │ ───── │                                          │
│                                     │  MCP  │  Tools:                                  │
│  MCP Client                         │◄─────►│    • add_duration_to_datetime            │
│    list_tools → Anthropic schema    │       │    • get_current_datetime                │
│    call_tool  → result              │       │    • set_reminder                        │
│                                     │       │                                          │
│  utils.py                           │       │  Resource: greeting://{name}             │
│    input / file upload / rendering  │       │  Prompt:   coding_agent_system_prompt    │
└─────────────────────────────────────┘       └──────────────────────────────────────────┘
```

The server and client communicate over **streamable HTTP** (MCP's recommended transport). The agent also has access to Claude's built-in **web search** tool (`web_search_20250305`), so it can answer questions that require live internet data.

---

## What Has Been Implemented

### MCP Server (`server.py`)

| Feature | Details |
|---|---|
| **`add_duration_to_datetime`** | Add or subtract seconds / minutes / hours / days / weeks / months / years from any date string. Handles edge cases like month-end clamping and leap years. |
| **`get_current_datetime`** | Returns the current server date/time formatted with any `strftime` pattern. |
| **`set_reminder`** | Accepts content and a timestamp and confirms the reminder was set. |
| **`greeting` resource** | A URI-templated resource (`greeting://{name}`) that returns a personalised greeting string. |
| **`coding_agent_system_prompt` prompt** | An MCP prompt that instructs the agent to act as a professional Python/MCP programmer. |
| **Configurable transport** | Host and port are loaded from `.env`, with validation and clear error messages on misconfiguration. |

### AI Agent Client (`agent.py`)

- Connects to the MCP server and the Anthropic API simultaneously using async context managers.
- Automatically converts MCP tool schemas to Anthropic-compatible tool definitions.
- Runs a **multi-turn agentic loop**: sends the user message, handles `tool_use` stop reasons, calls the MCP server, feeds results back, and repeats — up to a configurable safety cap of **10 tool calls per turn**.
- Streams Claude's responses to the terminal in real time using `rich.live` and `rich.markdown`.
- Bundles **Claude's web search tool** alongside the MCP tools, so the agent can search the internet without any additional server-side code.

### Utilities (`utils.py`)

| Utility | Purpose |
|---|---|
| `get_user_input()` | Interactive prompt with three modes: type a message, paste from clipboard (`p`), or upload a file (`f`). |
| `upload_file()` | Detects file MIME type with `filetype`, uploads to Anthropic's Files API, and returns a document/image block ready to include in the message. |
| `structure_user_message()` | Wraps plain text in an Anthropic `document` content block for consistent message formatting. |
| `mcp_tools_to_anthropic_tools()` | Converts `ListToolsResult` from the MCP SDK into the schema format the Anthropic SDK expects. |
| `agent_message_turn()` | Orchestrates the full tool-use loop: streaming output, block status printing, tool dispatch, result injection, and loop termination. |
| `chat()` | Low-level async generator that wraps the Anthropic streaming and non-streaming APIs behind a unified `(event_type, data)` interface. Supports extended thinking (`adaptive` mode). |
| `print_block_status()` | Prints dim status lines for server tool calls and web search result links as they arrive. |
| `read_file_bytes()` | Safely reads a file as base64-encoded bytes with descriptive error messages. |

---

## Project Structure

```
learning-mcp/
├── server.py          # MCP server — tools, resources, and prompts
├── agent.py           # CLI chat client — connects to the MCP server and Claude
├── utils.py           # Shared helpers: input, file upload, tool conversion, streaming
├── pyproject.toml     # Project metadata and dependencies (managed with uv)
├── .env.example       # Environment variable template
└── .python-version    # Pins Python 3.12
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) (recommended) or `pip`
- An [Anthropic API key](https://console.anthropic.com/)

### Installation

```bash
# Clone the repo
git clone <repo-url>
cd learning-mcp

# Install dependencies with uv
uv sync

# Or with pip in a virtual environment
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Configuration

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

```env
ANTHROPIC_API_KEY=sk-ant-...
TRANSPORT_HOST=127.0.0.1
TRANSPORT_PORT=2026
```

### Running

Start the MCP server first, then the agent in a separate terminal:

```bash
# Terminal 1 — start the MCP server
uv run python server.py

# Terminal 2 — start the agent
uv run python agent.py
```

The agent will prompt you to type a message, paste from clipboard, or upload a file. Type `exit` to quit.

---

## Dependencies

| Package | Role |
|---|---|
| `anthropic[aiohttp]` | Claude API client with async HTTP support |
| `mcp[cli,rich]` | Model Context Protocol SDK (server + client) |
| `python-dotenv` | Loads `.env` configuration |
| `rich` | Terminal formatting, live streaming output, markdown rendering |
| `pyperclip` | Clipboard paste support |
| `filetype` | MIME type detection for file uploads |
| `httpx` | HTTP client (transitive, used by MCP) |
| `ipykernel` | Jupyter kernel for notebook-based exploration |

---

## What Could Be Added or Improved

### Features

- **Persistent conversation history** — save and reload message threads to/from disk (JSON or SQLite) so context survives between sessions.
- **More MCP tools** — calculator operations, unit conversion, weather lookups, code execution, database queries, or anything domain-specific.
- **Multi-server support** — connect the agent to multiple MCP servers simultaneously and merge their tool lists.
- **System prompt configuration** — expose the `coding_agent_system_prompt` MCP prompt through the agent, or allow the user to select a system prompt at startup.
- **`set_reminder` persistence** — the reminder tool currently just echoes back; it could store reminders to a file or database and trigger notifications.
- **Audio and image content blocks** — `upload_file` only handles documents and images today; the `read_file_bytes` helper is already in place and the result parsing could be extended for audio.
- **Extended thinking** — the `chat()` function already supports `thinking=True` with adaptive effort; exposing this as a CLI flag would unlock it for users.

### Developer Experience

- **CLI flags / `argparse`** — configure model, max tokens, streaming mode, and the MCP server URL from the command line instead of hardcoding defaults.
- **Logging** — replace `print` and `console.print` calls with structured logging (`structlog` or `logging`) with configurable verbosity.
- **Tests** — unit tests for `utils.py` helpers and integration tests for the MCP server tools using `pytest` and `pytest-asyncio`.
- **Type safety** — tighten remaining `Any`-typed parameters (e.g. `content`, `timestamp` in `set_reminder`) and add full `mypy` coverage.
- **Docker / `docker-compose`** — containerise the server and agent so they are runnable without local Python setup.
- **Connection retry** — if the MCP server is not yet available when the agent starts, retry with exponential backoff instead of crashing.
- **Tool call cap as a config value** — the hard-coded `10` tool call limit in `agent_message_turn` should be an environment variable or CLI parameter.

### Architecture

- **Authentication** — add an API key or bearer token check on the MCP server's HTTP transport for non-localhost deployments.
- **WebSocket / SSE transport** — benchmark streamable-HTTP vs WebSocket transport for latency-sensitive workloads.
