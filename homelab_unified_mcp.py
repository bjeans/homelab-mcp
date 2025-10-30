#!/usr/bin/env python3
"""
Homelab Unified MCP Server
Unified server that combines all homelab MCP servers into a single entry point
Exposes all tools from docker, ping, ollama, pihole, and unifi servers with namespaced names
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

# Load all environment variables ONCE before importing sub-servers
from mcp_config_loader import load_env_file, COMMON_ALLOWED_ENV_VARS

SCRIPT_DIR = Path(__file__).parent
ENV_FILE = SCRIPT_DIR / ".env"

# Combined allowed variables for all servers
UNIFIED_ALLOWED_VARS = COMMON_ALLOWED_ENV_VARS | {
    "DOCKER_*",
    "PODMAN_*",
    "PING_*",
    "OLLAMA_*",
    "LITELLM_*",
    "PIHOLE_*",
    "UNIFI_*",
    "NUT_*",
}

# Load environment once for all servers
logger.info("Loading unified environment configuration...")
load_env_file(ENV_FILE, allowed_vars=UNIFIED_ALLOWED_VARS, strict=True)

# Set flag to skip individual server env loading
os.environ["MCP_UNIFIED_MODE"] = "1"

# Import all sub-servers (they will skip load_env_file if MCP_UNIFIED_MODE is set)
from docker_mcp_podman import DockerMCPServer
from ping_mcp_server import PingMCPServer
from ollama_mcp import OllamaMCPServer
from pihole_mcp import PiholeMCPServer
from unifi_mcp_optimized import UnifiMCPServer
import ups_mcp_server

# Import yaml for loading Ansible inventory
import yaml


def load_shared_ansible_inventory():
    """
    Load Ansible inventory once for all servers to avoid file locking issues.
    Returns the raw inventory dict or None if not found/error.
    """
    ansible_inventory_path = os.getenv("ANSIBLE_INVENTORY_PATH", "")

    if not ansible_inventory_path or not Path(ansible_inventory_path).exists():
        logger.info(f"Ansible inventory not found at: {ansible_inventory_path}")
        logger.info("Sub-servers will use environment variable fallback")
        return None

    try:
        logger.info(f"Loading shared Ansible inventory from: {ansible_inventory_path}")
        with open(ansible_inventory_path, "r") as f:
            inventory = yaml.safe_load(f)
        logger.info("Ansible inventory loaded successfully")
        return inventory
    except Exception as e:
        logger.error(f"Error loading Ansible inventory: {e}")
        logger.info("Sub-servers will use environment variable fallback")
        return None


class UnifiedHomelabServer:
    """Unified Homelab MCP Server - Combines all sub-servers"""

    def __init__(self):
        """Initialize all sub-servers"""
        logger.info("Initializing Unified Homelab MCP Server...")

        # Create MCP server instance
        self.app = Server("homelab-unified")

        # Load Ansible inventory ONCE to avoid file locking issues
        shared_inventory = load_shared_ansible_inventory()

        # Initialize all sub-servers with shared inventory
        logger.info("Initializing Docker/Podman MCP Server...")
        self.docker = DockerMCPServer(ansible_inventory=shared_inventory)

        logger.info("Initializing Ping MCP Server...")
        self.ping = PingMCPServer(ansible_inventory=shared_inventory)

        logger.info("Initializing Ollama MCP Server...")
        self.ollama = OllamaMCPServer(ansible_inventory=shared_inventory)

        logger.info("Initializing Pi-hole MCP Server...")
        self.pihole = PiholeMCPServer(ansible_inventory=shared_inventory)

        logger.info("Initializing Unifi MCP Server...")
        self.unifi = UnifiMCPServer()  # Unifi doesn't use Ansible inventory

        logger.info("Initializing UPS MCP Server...")
        self.ups = None  # UPS server is async and initialized separately

        # Register handlers
        self.setup_handlers()

        logger.info("Unified Homelab MCP Server initialized successfully")

    def setup_handlers(self):
        """Register MCP handlers"""

        @self.app.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            """List all available tools from all sub-servers"""
            tools = []

            # Get tools from each sub-server
            tools.extend(await self.docker.list_tools())
            tools.extend(await self.ping.list_tools())
            tools.extend(await self.ollama.list_tools())
            tools.extend(await self.pihole.list_tools())
            tools.extend(await self.unifi.list_tools())
            
            # Add UPS tools
            tools.extend([
                types.Tool(
                    name="ups_get_ups_status",
                    description="Get status of all UPS devices across all NUT servers",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                ),
                types.Tool(
                    name="ups_get_ups_details",
                    description="Get detailed information for a specific UPS device",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "host": {
                                "type": "string",
                                "description": "NUT server hostname (e.g., 'dell-server', 'cyber-server')",
                            },
                            "ups_name": {
                                "type": "string",
                                "description": "UPS device name (optional, defaults to first UPS on host)",
                            },
                        },
                        "required": ["host"],
                    },
                ),
                types.Tool(
                    name="ups_get_battery_runtime",
                    description="Get battery runtime estimates for all UPS devices",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                ),
                types.Tool(
                    name="ups_list_ups_devices",
                    description="List all UPS devices configured in the inventory",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                ),
                types.Tool(
                    name="ups_get_power_events",
                    description="Check for recent power events (status changes from online to battery)",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                ),
                types.Tool(
                    name="ups_reload_inventory",
                    description="Reload Ansible inventory from disk (useful after inventory changes)",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                ),
            ])

            logger.info(f"Total tools available: {len(tools)}")
            return tools

        @self.app.call_tool()
        async def handle_call_tool(
            name: str, arguments: dict | None
        ) -> list[types.TextContent]:
            """Route tool calls to the appropriate sub-server"""
            logger.info(f"Tool called: {name}")

            try:
                # Route based on tool name prefix
                if name.startswith("docker_"):
                    return await self.docker.handle_tool(name, arguments)
                elif name.startswith("ping_"):
                    return await self.ping.handle_tool(name, arguments)
                elif name.startswith("ollama_"):
                    return await self.ollama.handle_tool(name, arguments)
                elif name.startswith("pihole_"):
                    return await self.pihole.handle_tool(name, arguments)
                elif name.startswith("unifi_"):
                    return await self.unifi.handle_tool(name, arguments)
                elif name.startswith("ups_"):
                    # Route to UPS server - strip prefix to get the tool name
                    ups_tool_name = name[4:]  # Remove "ups_" prefix
                    return await ups_mcp_server.handle_call_tool(ups_tool_name, arguments)  # type: ignore
                else:
                    return [
                        types.TextContent(
                            type="text", text=f"Error: Unknown tool '{name}'"
                        )
                    ]

            except Exception as e:
                logger.error(f"Error executing tool {name}: {e}", exc_info=True)
                return [
                    types.TextContent(
                        type="text", text=f"Error executing {name}: {str(e)}"
                    )
                ]


async def main():
    """Run the unified MCP server"""
    logger.info("Starting Unified Homelab MCP Server...")

    # Create unified server
    server = UnifiedHomelabServer()

    # Run server
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="homelab-unified",
                server_version="2.0.0",
                capabilities=server.app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
