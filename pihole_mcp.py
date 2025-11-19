#!/usr/bin/env python3
"""
Pi-hole MCP Server v3
Provides DNS statistics from Pi-hole instances using session-based authentication
Supports Pi-hole v6 API with automatic session management and refresh
Reads host configuration from Ansible inventory
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

import aiohttp
import yaml

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from ansible_config_manager import load_group_hosts
from mcp_config_loader import load_env_file, COMMON_ALLOWED_ENV_VARS

server = Server("pihole-info")

# Load .env with security hardening
SCRIPT_DIR = Path(__file__).parent
ENV_FILE = SCRIPT_DIR / ".env"

PIHOLE_ALLOWED_VARS = COMMON_ALLOWED_ENV_VARS | {
    "PIHOLE_*",  # Matches PIHOLE_HOST, PIHOLE_PASSWORD, etc.
}

# Only load env file at module level if not in unified mode
if not os.getenv("MCP_UNIFIED_MODE"):
    load_env_file(ENV_FILE, allowed_vars=PIHOLE_ALLOWED_VARS, strict=True)

# Configuration
ANSIBLE_INVENTORY_PATH = os.getenv("ANSIBLE_INVENTORY_PATH", "")

logger.info(f"Ansible inventory: {ANSIBLE_INVENTORY_PATH}")

# Session cache: {hostname: {'sid': str, 'expires_at': datetime}}
SESSION_CACHE = {}


def load_pihole_hosts_from_ansible(inventory=None):
    """
    Load Pi-hole hosts from Ansible inventory using centralized config manager
    Returns list of tuples: [(display_name, host, port, api_key), ...]

    Args:
        inventory: Optional pre-loaded inventory (for compatibility, unused now)
    """
    # Use centralized config manager
    pihole_group_name = os.getenv("PIHOLE_ANSIBLE_GROUP", "PiHole")
    hosts = load_group_hosts(
        pihole_group_name,
        inventory_path=ANSIBLE_INVENTORY_PATH,
        logger_obj=logger
    )

    if not hosts:
        logger.warning(f"No hosts found in '{pihole_group_name}' group")
        return load_pihole_hosts_from_env()

    pihole_hosts = []
    for display_name, host in hosts.items():
        port = 80  # Default Pi-hole port
        api_key = os.getenv(f"PIHOLE_API_KEY_{display_name.replace('-', '_').upper()}", "")
        pihole_hosts.append((display_name, host, port, api_key))
        logger.info(f"Found Pi-hole host: {display_name} -> {host}:{port}")

    logger.info(f"Loaded {len(pihole_hosts)} Pi-hole hosts from Ansible inventory")
    return pihole_hosts


def load_pihole_hosts_from_env():
    """
    Fallback: Load Pi-hole hosts from environment variables
    Returns list of tuples: [(display_name, host, port, api_key), ...]
    
    BUG FIX (2025-10-21): Look for direct environment variables passed via -e flags
    The function now directly iterates os.environ to find PIHOLE_*_HOST and PIHOLE_API_KEY_* 
    variables, matching the pattern used in ollama_mcp.py for better container compatibility.
    """
    pihole_hosts = []
    processed_names = set()

    # Look for PIHOLE_*_HOST environment variables (direct env vars, not just .env)
    for key, value in os.environ.items():
        if key.startswith("PIHOLE_") and key.endswith("_HOST"):
            # Extract name: PIHOLE_DELL_HOST -> DELL
            name_part = key.replace("PIHOLE_", "").replace("_HOST", "")

            if name_part in processed_names:
                continue
            processed_names.add(name_part)

            # Get corresponding values from os.environ directly
            host = os.environ.get(f"PIHOLE_{name_part}_HOST", "")
            port_str = os.environ.get(f"PIHOLE_{name_part}_PORT", "80")
            api_key = os.environ.get(f"PIHOLE_API_KEY_{name_part}", "")
            
            try:
                port = int(port_str)
            except (ValueError, TypeError):
                port = 80
                logger.warning(f"Invalid port '{port_str}' for {name_part}, using default 80")

            # Format display name
            display_name = name_part.replace("_", "-").title()

            if host:
                pihole_hosts.append((display_name, host, port, api_key))
                logger.info(f"Loaded from env: {display_name} -> {host}:{port} (api_key: {'***' if api_key else 'NOT SET'})")
            else:
                logger.warning(f"PIHOLE_{name_part}_HOST is empty, skipping")

    return pihole_hosts


# Load Pi-hole hosts on startup (module-level for standalone mode)
PIHOLE_HOSTS = []

if __name__ == "__main__":
    PIHOLE_HOSTS = load_pihole_hosts_from_ansible()

    if not PIHOLE_HOSTS:
        logger.error("No Pi-hole hosts configured!")
        logger.error(
            "Please set ANSIBLE_INVENTORY_PATH or PIHOLE_*_HOST environment variables"
        )


class PiholeMCPServer:
    """Pi-hole MCP Server - Class-based implementation"""

    def __init__(self, ansible_inventory=None):
        """Initialize configuration using existing config loading logic

        Args:
            ansible_inventory: Optional pre-loaded Ansible inventory dict (for unified mode)
        """
        # Load environment configuration (skip if in unified mode)
        if not os.getenv("MCP_UNIFIED_MODE"):
            load_env_file(ENV_FILE, allowed_vars=PIHOLE_ALLOWED_VARS, strict=True)

        self.ansible_inventory_path = os.getenv("ANSIBLE_INVENTORY_PATH", "")
        logger.info(f"[PiholeMCPServer] Ansible inventory: {self.ansible_inventory_path}")

        # Load Pi-hole hosts (use pre-loaded inventory if provided)
        self.pihole_hosts = load_pihole_hosts_from_ansible(ansible_inventory)

        if not self.pihole_hosts:
            logger.warning("[PiholeMCPServer] No Pi-hole hosts configured!")

        # Session cache for this instance
        self.session_cache = {}

    async def list_tools(self) -> list[types.Tool]:
        """Return list of Tool objects this server provides (with pihole_ prefix)"""
        return [
            types.Tool(
                name="pihole_get_stats",
                description="Get DNS statistics from all Pi-hole instances",
                inputSchema={"type": "object", "properties": {}},
                title="Get Pi-hole Statistics",
                annotations=types.ToolAnnotations(
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=False,
                    openWorldHint=True,
                )
            ),
            types.Tool(
                name="pihole_get_status",
                description="Check which Pi-hole instances are online",
                inputSchema={"type": "object", "properties": {}},
                title="Get Pi-hole Status",
                annotations=types.ToolAnnotations(
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=False,
                    openWorldHint=True,
                )
            ),
        ]

    async def handle_tool(self, tool_name: str, arguments: dict | None) -> list[types.TextContent]:
        """Route tool calls to appropriate handler methods"""
        # Strip the pihole_ prefix for routing
        name = tool_name.replace("pihole_", "", 1) if tool_name.startswith("pihole_") else tool_name

        logger.info(f"[PiholeMCPServer] Tool called: {tool_name} -> {name} with args: {arguments}")

        # Call the shared implementation with this instance's hosts and session cache
        return await handle_call_tool_impl(name, arguments, self.pihole_hosts, self.session_cache)


async def get_pihole_session(host: str, port: int, password: str) -> dict:
    """
    Get or refresh a Pi-hole session

    Returns:
        dict with 'sid' and 'expires_at', or {'error': str} on failure
    """
    url = f"http://{host}:{port}/api/auth"
    payload = {"password": password}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, json=payload, timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    session_data = data.get("session", {})

                    if session_data.get("valid"):
                        # Calculate expiry time (session validity is in seconds)
                        validity_seconds = session_data.get("validity", 300)
                        # Refresh 30 seconds before expiry to be safe
                        expires_at = datetime.now() + timedelta(
                            seconds=validity_seconds - 30
                        )

                        return {"sid": session_data["sid"], "expires_at": expires_at}
                    else:
                        message = session_data.get("message", "Authentication failed")
                        return {"error": f"Auth failed: {message}"}
                else:
                    text = await response.text()
                    return {"error": f"HTTP {response.status}: {text[:100]}"}

    except asyncio.TimeoutError:
        return {"error": "Connection timeout"}
    except aiohttp.ClientConnectorError:
        return {"error": "Connection refused"}
    except Exception as e:
        return {"error": f"Exception: {str(e)}"}


async def get_cached_session(
    display_name: str, host: str, port: int, api_key: str, session_cache: dict
) -> dict:
    """
    Get a valid session from cache or create a new one

    Returns:
        dict with 'sid', or {'error': str} on failure
    """
    if not api_key:
        return {"error": "No API key configured"}

    # Check if we have a valid cached session
    cache_key = display_name
    if cache_key in session_cache:
        cached = session_cache[cache_key]
        if datetime.now() < cached["expires_at"]:
            # Session still valid
            return {"sid": cached["sid"]}
        else:
            logger.info(f"Session expired for {display_name}, refreshing...")

    # Get new session
    session_info = await get_pihole_session(host, port, api_key)

    if "error" not in session_info:
        # Cache the new session
        session_cache[cache_key] = session_info
        logger.info(
            f"New session obtained for {display_name}, expires at {session_info['expires_at']}"
        )
        return {"sid": session_info["sid"]}

    return session_info


async def pihole_api_request(
    host: str, port: int, endpoint: str, sid: str, timeout: int = 5
):
    """
    Make an authenticated request to Pi-hole API using session ID

    Uses URL query parameter method: ?sid=<SID>
    """
    # URL-encode the SID
    encoded_sid = quote(sid)
    url = f"http://{host}:{port}{endpoint}?sid={encoded_sid}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(
                        f"API request failed: HTTP {response.status} for {url}"
                    )
                    return None
    except asyncio.TimeoutError:
        logger.warning(f"Timeout requesting {url}")
        return None
    except Exception as e:
        logger.warning(f"Error requesting {url}: {str(e)}")
        return None


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available Pi-hole tools"""
    return [
        types.Tool(
            name="get_pihole_stats",
            description="Get DNS statistics from all Pi-hole instances",
            inputSchema={"type": "object", "properties": {}},
            title="Get Pi-hole Statistics",
            annotations=types.ToolAnnotations(
                readOnlyHint=True,
                destructiveHint=False,
                idempotentHint=False,
                openWorldHint=True,
            )
        ),
        types.Tool(
            name="get_pihole_status",
            description="Check which Pi-hole instances are online",
            inputSchema={"type": "object", "properties": {}},
            title="Get Pi-hole Status",
            annotations=types.ToolAnnotations(
                readOnlyHint=True,
                destructiveHint=False,
                idempotentHint=False,
                openWorldHint=True,
            )
        ),
    ]


async def handle_call_tool_impl(
    name: str, arguments: dict | None, pihole_hosts: list, session_cache: dict
) -> list[types.TextContent]:
    """Core tool execution logic that can be called by both class and module-level handlers"""
    try:
        if name == "get_stats" or name == "get_pihole_stats":
            output = "=== PI-HOLE DNS STATISTICS ===\n\n"

            for display_name, host, port, api_key in pihole_hosts:
                output += f"--- {display_name} ---\n"

                # Get session
                session_result = await get_cached_session(
                    display_name, host, port, api_key, session_cache
                )

                if "error" in session_result:
                    output += f"Error: {session_result['error']}\n\n"
                    continue

                # Get stats using session
                sid = session_result["sid"]
                data = await pihole_api_request(host, port, "/api/stats/summary", sid)

                if data:
                    # Extract stats from Pi-hole v6 API response
                    queries = data.get("queries", {})
                    clients = data.get("clients", {})
                    gravity = data.get("gravity", {})

                    # Format numbers with commas
                    total_queries = queries.get("total", 0)
                    blocked_queries = queries.get("blocked", 0)
                    percent_blocked = queries.get("percent_blocked", 0)
                    unique_clients = clients.get("active", 0)
                    domains_blocked = gravity.get("domains_being_blocked", 0)

                    output += f"Total Queries: {total_queries:,}\n"
                    output += f"Queries Blocked: {blocked_queries:,}\n"
                    output += f"Percent Blocked: {percent_blocked:.1f}%\n"
                    output += f"Unique Clients: {unique_clients:,}\n"
                    output += f"Domains on Blocklist: {domains_blocked:,}\n"
                else:
                    output += "Could not retrieve stats\n"

                output += "\n"

            return [types.TextContent(type="text", text=output)]

        elif name == "get_status" or name == "get_pihole_status":
            output = "=== PI-HOLE STATUS ===\n\n"
            online = 0

            for display_name, host, port, api_key in pihole_hosts:
                # Try to get a session (which tests connectivity and auth)
                session_result = await get_cached_session(
                    display_name, host, port, api_key, session_cache
                )

                if "error" in session_result:
                    output += f"✗ {display_name} ({host}:{port}): OFFLINE - {session_result['error']}\n"
                else:
                    online += 1
                    output += f"✓ {display_name} ({host}:{port}): ONLINE\n"

            output = f"Online: {online}/{len(pihole_hosts)}\n\n" + output
            return [types.TextContent(type="text", text=output)]

        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        logger.error(f"Error in tool {name}: {str(e)}")
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent]:
    """Handle tool calls (module-level wrapper for standalone mode)"""
    # For standalone mode, use the global variables
    return await handle_call_tool_impl(name, arguments, PIHOLE_HOSTS, SESSION_CACHE)


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="pihole-info",
                server_version="3.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
