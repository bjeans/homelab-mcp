#!/usr/bin/env python3
"""
Ollama MCP Server
Provides access to Ollama instances and models
Reads host configuration from Ansible inventory
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

import aiohttp
import yaml

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from mcp_config_loader import COMMON_ALLOWED_ENV_VARS, load_env_file

server = Server("ollama-info")

# Load .env with security hardening
SCRIPT_DIR = Path(__file__).parent
ENV_FILE = SCRIPT_DIR / ".env"

# Allowlist for Ollama server - use pattern matching for flexibility
# OLLAMA_* matches OLLAMA_PORT, OLLAMA_SERVER1, OLLAMA_CUSTOM_HOST, etc.
# LITELLM_* matches all LiteLLM proxy configuration variables
OLLAMA_ALLOWED_VARS = COMMON_ALLOWED_ENV_VARS | {
    "OLLAMA_*",  # Pattern: covers OLLAMA_PORT, OLLAMA_SERVER*, OLLAMA_INVENTORY_GROUP, etc.
    "LITELLM_*",  # Pattern: covers LITELLM_HOST, LITELLM_PORT, etc.
}

# Only load env file at module level if not in unified mode
if not os.getenv("MCP_UNIFIED_MODE"):
    load_env_file(ENV_FILE, allowed_vars=OLLAMA_ALLOWED_VARS, strict=True)

# Configuration
ANSIBLE_INVENTORY_PATH = os.getenv("ANSIBLE_INVENTORY_PATH", "")
OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))
OLLAMA_INVENTORY_GROUP = os.getenv("OLLAMA_INVENTORY_GROUP", "ollama_servers")

# LiteLLM configuration
LITELLM_HOST = os.getenv("LITELLM_HOST", "localhost")
LITELLM_PORT = os.getenv("LITELLM_PORT", "4000")

logger.info(f"Ansible inventory: {ANSIBLE_INVENTORY_PATH}")
logger.info(f"LiteLLM endpoint: {LITELLM_HOST}:{LITELLM_PORT}")


def load_ollama_endpoints_from_ansible(inventory=None):
    """
    Load Ollama endpoints from Ansible inventory
    Returns dict of {display_name: ip_address}

    Args:
        inventory: Optional pre-loaded Ansible inventory dict (avoids file locking in unified mode)
    """
    # Use pre-loaded inventory if provided
    if inventory is None:
        # Get path from environment variable
        ansible_inventory_path = os.getenv("ANSIBLE_INVENTORY_PATH", "")

        if not ansible_inventory_path or not Path(ansible_inventory_path).exists():
            logger.warning(f"Ansible inventory not found at: {ansible_inventory_path}")
            logger.warning("Falling back to .env configuration")
            return load_ollama_endpoints_from_env()

        try:
            with open(ansible_inventory_path, "r") as f:
                inventory = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading Ansible inventory: {e}")
            logger.warning("Falling back to .env configuration")
            return load_ollama_endpoints_from_env()

    # Process the inventory (whether pre-loaded or freshly loaded)
    try:
        endpoints = {}

        # Helper function to find a group anywhere in the inventory tree
        def find_group(data, target_name):
            """Recursively search for a group by name"""
            if isinstance(data, dict):
                if target_name in data:
                    return data[target_name]
                for value in data.values():
                    if isinstance(value, dict):
                        result = find_group(value, target_name)
                        if result:
                            return result
            return None

        # Helper function to recursively find all hosts in a group
        def get_hosts_from_group(group_data, inherited_vars=None):
            """Recursively extract hosts from a group and its children"""
            inherited_vars = inherited_vars or {}
            hosts_found = []

            # Merge current group vars with inherited vars
            current_vars = {**inherited_vars, **group_data.get("vars", {})}

            # Get direct hosts in this group
            if "hosts" in group_data:
                for hostname, host_vars in group_data["hosts"].items():
                    merged_vars = {**current_vars, **(host_vars or {})}
                    hosts_found.append((hostname, merged_vars))

            # Recursively process child groups
            if "children" in group_data:
                for child_name, child_data in group_data["children"].items():
                    # Child groups in Ansible are often just references (empty {})
                    # We need to find the actual group definition
                    if not child_data or (not child_data.get("hosts") and not child_data.get("children")):
                        # This is a reference - find the actual group definition
                        actual_child_group = find_group(inventory, child_name)
                        if actual_child_group:
                            hosts_found.extend(get_hosts_from_group(actual_child_group, current_vars))
                    else:
                        # This is an inline definition - process directly
                        hosts_found.extend(get_hosts_from_group(child_data, current_vars))

            return hosts_found

        # Get Ollama group name from env (configurable)
        ollama_group_name = os.getenv("OLLAMA_ANSIBLE_GROUP", "ollama_servers")

        # Find and process Ollama hosts
        ollama_group = find_group(inventory, ollama_group_name)
        if ollama_group:
            ollama_hosts_list = get_hosts_from_group(ollama_group)
            logger.info(f"Found {len(ollama_hosts_list)} hosts in {ollama_group_name} group")

            for hostname, host_vars in ollama_hosts_list:
                # Clean up hostname for display (remove domain suffix)
                display_name = hostname.split(".")[0]
                # Capitalize and clean up for display
                display_name = display_name.replace("-", " ").title().replace(" ", "-")

                # Try to get IP from ansible_host var, or resolve hostname
                ip = host_vars.get("ansible_host", host_vars.get("static_ip", hostname.split(".")[0]))

                endpoints[display_name] = ip
                logger.info(f"Found Ollama host: {display_name} -> {ip}")
        else:
            logger.debug(f"Ollama group '{ollama_group_name}' not found in inventory")

        if not endpoints:
            logger.warning("No Ollama hosts found in Ansible inventory")
            return load_ollama_endpoints_from_env()

        return endpoints

    except Exception as e:
        logger.error(f"Error processing Ansible inventory: {e}")
        logger.warning("Falling back to .env configuration")
        return load_ollama_endpoints_from_env()


def load_ollama_endpoints_from_env():
    """
    Fallback: Load Ollama endpoints from environment variables
    Returns dict of {display_name: ip_address}
    
    BUG FIX (2025-10-21): Strip port numbers from env var values
    Environment variables may include ports (e.g., "192.168.1.100:11434")
    but the port is added separately in ollama_request() via OLLAMA_PORT config.
    Without stripping, URLs would have double ports (e.g., :11434:11434)
    """
    endpoints = {}

    # Look for OLLAMA_* environment variables
    for key, value in os.environ.items():
        if key.startswith("OLLAMA_") and key not in ["OLLAMA_PORT"]:
            # Convert OLLAMA_SERVER1 to Server1
            display_name = key.replace("OLLAMA_", "").replace("_", "-").title()
            # Strip port if included (e.g., "192.168.1.100:11434" -> "192.168.1.100")
            # Port is added separately in ollama_request() via OLLAMA_PORT config
            ip_only = value.split(":")[0] if ":" in value else value  # ✓ Strip port
            endpoints[display_name] = ip_only
            if ip_only != value:
                logger.info(f"Loaded from env: {display_name} -> {ip_only} (stripped port from {value})")
            else:
                logger.info(f"Loaded from env: {display_name} -> {ip_only}")

    return endpoints


# Load Ollama endpoints on startup (module-level for standalone mode)
OLLAMA_ENDPOINTS = {}
LITELLM_CONFIG = {}

if __name__ == "__main__":
    OLLAMA_ENDPOINTS = load_ollama_endpoints_from_ansible()
    LITELLM_CONFIG = {"host": LITELLM_HOST, "port": LITELLM_PORT}

    if not OLLAMA_ENDPOINTS:
        logger.error("No Ollama endpoints configured!")
        logger.error("Please set ANSIBLE_INVENTORY_PATH or OLLAMA_* environment variables")


class OllamaMCPServer:
    """Ollama MCP Server - Class-based implementation"""

    def __init__(self, ansible_inventory=None):
        """Initialize configuration using existing config loading logic

        Args:
            ansible_inventory: Optional pre-loaded Ansible inventory dict (for unified mode)
        """
        # Load environment configuration (skip if in unified mode)
        if not os.getenv("MCP_UNIFIED_MODE"):
            load_env_file(ENV_FILE, allowed_vars=OLLAMA_ALLOWED_VARS, strict=True)

        self.ansible_inventory_path = os.getenv("ANSIBLE_INVENTORY_PATH", "")
        self.ollama_port = int(os.getenv("OLLAMA_PORT", "11434"))
        self.ollama_inventory_group = os.getenv("OLLAMA_INVENTORY_GROUP", "ollama_servers")

        # LiteLLM configuration
        self.litellm_host = os.getenv("LITELLM_HOST", "localhost")
        self.litellm_port = os.getenv("LITELLM_PORT", "4000")

        logger.info(f"[OllamaMCPServer] Ansible inventory: {self.ansible_inventory_path}")
        logger.info(f"[OllamaMCPServer] LiteLLM endpoint: {self.litellm_host}:{self.litellm_port}")

        # Load Ollama endpoints (use pre-loaded inventory if provided)
        self.ollama_endpoints = load_ollama_endpoints_from_ansible(ansible_inventory)

        if not self.ollama_endpoints:
            logger.warning("[OllamaMCPServer] No Ollama endpoints configured!")

    async def list_tools(self) -> list[types.Tool]:
        """Return list of Tool objects this server provides (with ollama_ prefix)"""
        return [
            types.Tool(
                name="ollama_get_status",
                description="Check status of all Ollama instances",
                inputSchema={"type": "object", "properties": {}},
            ),
            types.Tool(
                name="ollama_get_models",
                description="Get models on a specific Ollama host",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "host": {
                            "type": "string",
                            "description": f"Host: {', '.join(self.ollama_endpoints.keys())}",
                        }
                    },
                    "required": ["host"],
                },
            ),
            types.Tool(
                name="ollama_get_litellm_status",
                description="Check LiteLLM proxy status",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    async def handle_tool(self, tool_name: str, arguments: dict | None) -> list[types.TextContent]:
        """Route tool calls to appropriate handler methods"""
        # Strip the ollama_ prefix for routing
        name = tool_name.replace("ollama_", "", 1) if tool_name.startswith("ollama_") else tool_name

        logger.info(f"[OllamaMCPServer] Tool called: {tool_name} -> {name} with args: {arguments}")

        # Call the shared implementation
        return await handle_call_tool_impl(
            name, arguments, self.ollama_endpoints, self.ollama_port,
            self.litellm_host, self.litellm_port
        )


async def ollama_request(host_ip: str, endpoint: str, port: int = 11434, timeout: int = 5):
    """Make request to Ollama API"""
    url = f"http://{host_ip}:{port}{endpoint}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                if response.status == 200:
                    return await response.json()
                return None
    except Exception as e:
        logger.debug(f"Ollama request failed for {host_ip}: {e}")
        return None


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available Ollama tools"""
    return [
        types.Tool(
            name="get_ollama_status",
            description="Check status of all Ollama instances",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="get_ollama_models",
            description="Get models on a specific Ollama host",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {
                        "type": "string",
                        "description": f"Host: {', '.join(OLLAMA_ENDPOINTS.keys())}",
                    }
                },
                "required": ["host"],
            },
        ),
        types.Tool(
            name="get_litellm_status",
            description="Check LiteLLM proxy status",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


async def handle_call_tool_impl(
    name: str, arguments: dict | None, ollama_endpoints: dict, ollama_port: int,
    litellm_host: str, litellm_port: str
) -> list[types.TextContent]:
    """Core tool execution logic that can be called by both class and module-level handlers"""
    try:
        if name == "get_status" or name == "get_ollama_status":
            output = "=== OLLAMA STATUS ===\n\n"
            total_models = 0
            online = 0

            for host_name, ip in ollama_endpoints.items():
                data = await ollama_request(ip, "/api/tags", ollama_port, timeout=3)

                if data:
                    models = data.get("models", [])
                    count = len(models)
                    total_models += count
                    online += 1

                    output += f"✓ {host_name} ({ip}): {count} models\n"
                    for model in models[:3]:
                        name = model.get("name", "Unknown")
                        size = model.get("size", 0) / (1024**3)
                        output += f"    - {name} ({size:.1f}GB)\n"
                    if count > 3:
                        output += f"    ... and {count-3} more\n"
                    output += "\n"
                else:
                    output += f"✗ {host_name} ({ip}): OFFLINE\n\n"

            output = (
                f"Summary: {online}/{len(ollama_endpoints)} online, {total_models} models\n\n"
                + output
            )
            return [types.TextContent(type="text", text=output)]

        elif name == "get_models" or name == "get_ollama_models":
            host = arguments.get("host")
            if host not in ollama_endpoints:
                return [types.TextContent(type="text", text=f"Invalid host: {host}")]

            ip = ollama_endpoints[host]
            data = await ollama_request(ip, "/api/tags", ollama_port, timeout=5)

            if not data:
                return [types.TextContent(type="text", text=f"{host} is offline")]

            models = data.get("models", [])
            output = f"=== {host} ({ip}) ===\n\n"
            output += f"Models: {len(models)}\n\n"

            for model in models:
                name = model.get("name", "Unknown")
                size = model.get("size", 0) / (1024**3)
                modified = model.get("modified_at", "Unknown")
                output += f"• {name}\n"
                output += f"  Size: {size:.2f}GB\n"
                output += f"  Modified: {modified}\n\n"

            return [types.TextContent(type="text", text=output)]

        elif name == "get_litellm_status":
            url = f"http://{litellm_host}:{litellm_port}/health/liveliness"
            logger.info(f"Checking LiteLLM at {url}")

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url, timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        logger.info(f"LiteLLM response status: {response.status}")
                        if response.status == 200:
                            data = (
                                await response.text()
                            )  # Liveliness returns text, not JSON
                            output = f"✓ LiteLLM Proxy: ONLINE\n"
                            output += f"Endpoint: {litellm_host}:{litellm_port}\n\n"
                            output += f"Liveliness Check: {data}"
                            return [types.TextContent(type="text", text=output)]
                        else:
                            return [
                                types.TextContent(
                                    type="text",
                                    text=f"✗ LiteLLM Proxy: HTTP {response.status}\nEndpoint: {url}",
                                )
                            ]
            except asyncio.TimeoutError:
                return [
                    types.TextContent(
                        type="text",
                        text=f"✗ LiteLLM Proxy: TIMEOUT\nEndpoint: {url}\nConnection timed out after 5 seconds",
                    )
                ]
            except aiohttp.ClientConnectorError as e:
                return [
                    types.TextContent(
                        type="text",
                        text=f"✗ LiteLLM Proxy: CONNECTION REFUSED\nEndpoint: {url}\nError: {str(e)}",
                    )
                ]
            except Exception as e:
                logger.error(f"LiteLLM check error: {e}", exc_info=True)
                return [
                    types.TextContent(
                        type="text",
                        text=f"✗ LiteLLM Proxy: ERROR\nEndpoint: {url}\nError: {str(e)}",
                    )
                ]

    except Exception as e:
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent]:
    """Handle tool calls (module-level wrapper for standalone mode)"""
    # For standalone mode, use the global variables
    return await handle_call_tool_impl(
        name, arguments, OLLAMA_ENDPOINTS, OLLAMA_PORT, LITELLM_HOST, LITELLM_PORT
    )


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="ollama-info",
                server_version="2.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
