#!/usr/bin/env python3
"""
Homelab Unified MCP Server
Unified server that combines all homelab MCP servers into a single entry point
Exposes all tools from docker, ping, ollama, pihole, and unifi servers with namespaced names
"""

import asyncio
import json
import logging
import os
import sys
from collections import defaultdict
from pathlib import Path

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from pydantic import AnyUrl

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
from ups_mcp_server import UpsMCPServer

# Import AnsibleConfigManager for enum generation
from ansible_config_manager import AnsibleConfigManager

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

        # Create AnsibleConfigManager for enum generation
        ansible_inventory_path = os.getenv("ANSIBLE_INVENTORY_PATH", "")
        ansible_config = None
        if ansible_inventory_path:
            ansible_config = AnsibleConfigManager(
                inventory_path=ansible_inventory_path,
                logger_obj=logger
            )
            if ansible_config.is_available():
                logger.info("AnsibleConfigManager initialized successfully for enum generation")
            else:
                logger.warning("AnsibleConfigManager not available, dynamic enums will be disabled")
                ansible_config = None
        else:
            logger.info("No Ansible inventory path configured, dynamic enums will be disabled")

        # Initialize all sub-servers with shared inventory and config manager
        logger.info("Initializing Docker/Podman MCP Server...")
        self.docker = DockerMCPServer(
            ansible_inventory=shared_inventory,
            ansible_config=ansible_config
        )

        logger.info("Initializing Ping MCP Server...")
        self.ping = PingMCPServer(
            ansible_inventory=shared_inventory,
            ansible_config=ansible_config
        )

        logger.info("Initializing Ollama MCP Server...")
        self.ollama = OllamaMCPServer(
            ansible_inventory=shared_inventory,
            ansible_config=ansible_config
        )

        logger.info("Initializing Pi-hole MCP Server...")
        self.pihole = PiholeMCPServer(
            ansible_inventory=shared_inventory,
            ansible_config=ansible_config
        )

        logger.info("Initializing Unifi MCP Server...")
        self.unifi = UnifiMCPServer()  # Unifi doesn't use Ansible inventory

        logger.info("Initializing UPS MCP Server...")
        self.ups = UpsMCPServer(
            ansible_inventory=shared_inventory,
            ansible_config=ansible_config
        )

        # Register handlers
        self.setup_handlers()

        logger.info("Unified Homelab MCP Server initialized successfully")

    async def get_tool_catalog(self) -> list[types.TextContent]:
        """
        Generate a grouped catalog of all tools from unified server.
        Returns both Markdown for human readability and raw JSON for programmatic use.
        """
        catalog = await self._generate_tool_catalog()
        return [types.TextContent(
            type="text",
            text=json.dumps(catalog, indent=2)
        )]

    async def _generate_tool_catalog(self) -> dict:
        """
        Generate the tool catalog as a dictionary.
        Can be used by both tool and resource handlers.
        Returns dict with 'markdown' and 'json' keys.
        """
        # Collect tools from all sub-servers (same pattern as handle_list_tools)
        all_tools = []
        all_tools.extend(await self.docker.list_tools())
        all_tools.extend(await self.ping.list_tools())
        all_tools.extend(await self.ollama.list_tools())
        all_tools.extend(await self.pihole.list_tools())
        all_tools.extend(await self.unifi.list_tools())
        all_tools.extend(await self.ups.list_tools())

        # Group by prefix
        grouped = defaultdict(list)
        for tool in all_tools:
            prefix = tool.name.split("_")[0]
            grouped[prefix].append({
                "name": tool.name,
                "description": tool.description,
                "schema": tool.inputSchema  # Already a dict, not JSON string
            })

        # Build markdown
        md_lines = ["# Homelab MCP Tool Catalog\n"]
        for category in sorted(grouped.keys()):
            md_lines.append(f"## {category.capitalize()} Tools\n")
            for entry in sorted(grouped[category], key=lambda x: x["name"]):
                md_lines.append(f"### {entry['name']}")
                md_lines.append(f"**Description:** {entry['description']}\n")
                if entry["schema"] and "properties" in entry["schema"]:
                    md_lines.append("**Parameters:**")
                    schema = entry["schema"]
                    for prop, details in schema.get("properties", {}).items():
                        req = "required" if prop in schema.get("required", []) else "optional"
                        md_lines.append(f"- `{prop}` ({req}): {details.get('description', '')}")
                md_lines.append("")

        # Return both formats
        return {
            "markdown": "\n".join(md_lines),
            "json": dict(grouped)  # Convert defaultdict to regular dict
        }

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
            tools.extend(await self.ups.list_tools())

            # Add the catalog tool itself
            tools.append(types.Tool(
                name="homelab_get_tool_catalog",
                description="Lists all available tools grouped by category with descriptions and input schemas",
                inputSchema={"type": "object", "properties": {}},
                title="Get Tool Catalog",
                annotations=types.ToolAnnotations(
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                )
            ))

            logger.info(f"Total tools available: {len(tools)}")
            return tools

        @self.app.call_tool()
        async def handle_call_tool(
            name: str, arguments: dict | None
        ) -> list[types.TextContent]:
            """Route tool calls to the appropriate sub-server"""
            logger.info(f"Tool called: {name}")

            try:
                # Handle catalog tool
                if name == "homelab_get_tool_catalog":
                    return await self.get_tool_catalog()

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
                    return await self.ups.handle_tool(name, arguments)
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

        @self.app.list_resources()
        async def handle_list_resources() -> list[types.Resource]:
            """List all available resources"""
            catalog_uri: AnyUrl = AnyUrl("homelab://catalog/tools")
            return [
                types.Resource(
                    uri=catalog_uri,
                    name="tool_catalog",
                    description="Catalog of all available tools grouped by category with descriptions and input schemas",
                    mimeType="application/json"
                )
            ]

        @self.app.read_resource()
        async def handle_read_resource(uri: AnyUrl) -> str:
            """Read resource content"""
            uri_str = str(uri)
            logger.info(f"Resource read requested: {uri_str}")

            if uri_str == "homelab://catalog/tools":
                catalog = await self._generate_tool_catalog()
                return json.dumps(catalog, indent=2)
            else:
                raise ValueError(f"Unknown resource: {uri_str}")


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
