#!/usr/bin/env python3
"""
MCP Registry Inspector Server

⚠️ DEPRECATED (v2.3.0): This tool is deprecated. Claude Desktop now has native
file system access, making this MCP server unnecessary. You can simply ask Claude
to read your MCP server files or configuration directly.

REPLACEMENT: Use Claude's built-in file access:
- "Read my claude_desktop_config.json file"
- "Show me the source code for docker_mcp_podman.py"
- "List all .py files in this directory"

This server will continue to work but will not receive updates. It will be
removed from documentation in v3.0.0.

---

LEGACY DESCRIPTION:
This MCP server allows querying Claude Desktop's MCP configuration
and inspecting the MCP server directory contents.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

# Load .env file if it exists
SCRIPT_DIR = Path(__file__).parent
ENV_FILE = SCRIPT_DIR / ".env"

if ENV_FILE.exists():
    logger.info(f"Loading configuration from {ENV_FILE}")
    with open(ENV_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()
else:
    logger.warning(f".env file not found at {ENV_FILE}")

# Configuration paths with environment variable support
CLAUDE_CONFIG_PATH = Path(
    os.getenv(
        "CLAUDE_CONFIG_PATH",
        str(Path.home() / "AppData/Roaming/Claude/claude_desktop_config.json"),
    )
)

MCP_DIRECTORY = Path(os.getenv("MCP_DIRECTORY", str(SCRIPT_DIR)))

logger.debug(f"Claude config path: {CLAUDE_CONFIG_PATH}")
logger.debug(f"MCP directory: {MCP_DIRECTORY}")

server = Server("mcp-registry-inspector")


def read_claude_config() -> dict[str, Any]:
    """Read Claude Desktop configuration file."""
    try:
        with open(CLAUDE_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"error": "Claude config file not found"}
    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse config: {str(e)}"}


def list_mcp_servers_from_config(config: dict[str, Any]) -> dict[str, Any]:
    """Extract MCP server configurations from Claude config."""
    mcp_servers = config.get("mcpServers", {})

    result = {"total_servers": len(mcp_servers), "servers": {}}

    for name, server_config in mcp_servers.items():
        result["servers"][name] = {
            "command": server_config.get("command"),
            "args": server_config.get("args", []),
            "env": server_config.get("env", {}),
        }

    return result


def list_mcp_directory_contents() -> dict[str, Any]:
    """List contents of the MCP directory."""
    if not MCP_DIRECTORY.exists():
        return {"error": f"MCP directory not found: {MCP_DIRECTORY}"}

    result = {"directory": str(MCP_DIRECTORY), "contents": []}

    try:
        for item in sorted(MCP_DIRECTORY.iterdir()):
            item_info = {
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
                "path": str(item),
            }

            if item.is_file():
                item_info["size_bytes"] = item.stat().st_size
                item_info["extension"] = item.suffix

            result["contents"].append(item_info)
    except Exception as e:
        result["error"] = str(e)

    return result


def read_mcp_file(file_path: str) -> dict[str, Any]:
    """Read contents of an MCP file."""
    try:
        full_path = Path(file_path)

        # Security check: ensure path is within MCP_DIRECTORY
        if not str(full_path.resolve()).startswith(str(MCP_DIRECTORY.resolve())):
            return {"error": "Access denied: Path outside MCP directory"}

        if not full_path.exists():
            return {"error": f"File not found: {file_path}"}

        if not full_path.is_file():
            return {"error": f"Not a file: {file_path}"}

        # Read file based on extension
        extension = full_path.suffix.lower()

        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()

        result = {
            "file": str(full_path),
            "size_bytes": full_path.stat().st_size,
            "extension": extension,
            "content": content,
        }

        # Try to parse as JSON if it's a .json file
        if extension == ".json":
            try:
                result["parsed_json"] = json.loads(content)
            except json.JSONDecodeError:
                result["json_parse_error"] = "File is not valid JSON"

        return result

    except Exception as e:
        return {"error": f"Failed to read file: {str(e)}"}


def write_mcp_file(file_path: str, content: str) -> dict[str, Any]:
    """Write content to an MCP file."""
    try:
        full_path = Path(file_path)

        # Handle relative paths
        if not full_path.is_absolute():
            full_path = MCP_DIRECTORY / file_path

        # Security check: ensure path is within MCP_DIRECTORY
        if not str(full_path.resolve()).startswith(str(MCP_DIRECTORY.resolve())):
            return {"error": "Access denied: Path outside MCP directory"}

        # Create parent directories if they don't exist
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the file
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Successfully wrote file: {full_path}")

        return {
            "success": True,
            "file": str(full_path),
            "size_bytes": len(content),
            "message": f"File written successfully",
        }

    except Exception as e:
        logger.error(f"Failed to write file: {e}")
        return {"error": f"Failed to write file: {str(e)}"}


def search_mcp_files(query: str, file_extensions: list[str] = None) -> dict[str, Any]:
    """Search for files in MCP directory matching query."""
    if not MCP_DIRECTORY.exists():
        return {"error": f"MCP directory not found: {MCP_DIRECTORY}"}

    results = {"query": query, "extensions_filter": file_extensions, "matches": []}

    try:
        for item in MCP_DIRECTORY.rglob("*"):
            if item.is_file():
                # Check extension filter
                if file_extensions and item.suffix.lower() not in file_extensions:
                    continue

                # Check if query matches filename
                if query.lower() in item.name.lower():
                    results["matches"].append(
                        {
                            "name": item.name,
                            "path": str(item),
                            "relative_path": str(item.relative_to(MCP_DIRECTORY)),
                            "size_bytes": item.stat().st_size,
                            "extension": item.suffix,
                        }
                    )
    except Exception as e:
        results["error"] = str(e)

    results["total_matches"] = len(results["matches"])
    return results


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """List available tools."""
    return [
        types.Tool(
            name="get_claude_config",
            description="Get the Claude Desktop MCP server configuration. Shows all registered MCP servers.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="list_mcp_servers",
            description="List all MCP servers registered in Claude Desktop config with their details.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="list_mcp_directory",
            description="List all files and directories in the MCP development directory.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="read_mcp_file",
            description="Read the contents of a specific MCP file. Provide either absolute path or relative to MCP directory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file (absolute or relative to MCP directory)",
                    }
                },
                "required": ["file_path"],
            },
        ),
        types.Tool(
            name="search_mcp_files",
            description="Search for files in MCP directory by name. Optionally filter by extensions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (matches filename)",
                    },
                    "extensions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional: Filter by file extensions (e.g., ['.py', '.json'])",
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="write_mcp_file",
            description="Write content to an MCP file. Creates parent directories if needed. Path can be absolute or relative to MCP directory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file (absolute or relative to MCP directory)",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file",
                    },
                },
                "required": ["file_path", "content"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[types.TextContent]:
    """Handle tool calls."""

    if name == "get_claude_config":
        config = read_claude_config()
        return [types.TextContent(type="text", text=json.dumps(config, indent=2))]

    elif name == "list_mcp_servers":
        config = read_claude_config()
        servers = list_mcp_servers_from_config(config)
        return [types.TextContent(type="text", text=json.dumps(servers, indent=2))]

    elif name == "list_mcp_directory":
        contents = list_mcp_directory_contents()
        return [types.TextContent(type="text", text=json.dumps(contents, indent=2))]

    elif name == "read_mcp_file":
        file_path = arguments.get("file_path")
        if not file_path:
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({"error": "file_path is required"}, indent=2),
                )
            ]

        # Handle relative paths
        if not os.path.isabs(file_path):
            file_path = MCP_DIRECTORY / file_path

        result = read_mcp_file(str(file_path))
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "search_mcp_files":
        query = arguments.get("query", "")
        extensions = arguments.get("extensions")

        result = search_mcp_files(query, extensions)
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "write_mcp_file":
        file_path = arguments.get("file_path")
        content = arguments.get("content")

        if not file_path or content is None:
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {"error": "file_path and content are required"}, indent=2
                    ),
                )
            ]

        result = write_mcp_file(file_path, content)
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    else:
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"error": f"Unknown tool: {name}"}, indent=2),
            )
        ]


async def main():
    """Run the MCP server."""
    logger.warning("=" * 80)
    logger.warning("⚠️  MCP REGISTRY INSPECTOR IS DEPRECATED (v2.3.0)")
    logger.warning("⚠️  Claude Desktop now has native file system access.")
    logger.warning("⚠️  This server will not receive updates and will be removed in v3.0.0.")
    logger.warning("⚠️  Please use Claude's built-in file access instead.")
    logger.warning("=" * 80)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
