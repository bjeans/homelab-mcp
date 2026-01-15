#!/usr/bin/env python3
"""
Homelab Unified MCP Server v2.3 (FastMCP)
Unified server that combines all homelab MCP servers into a single entry point
Uses FastMCP's native composition pattern - no manual wrappers needed
"""

import logging
import os
import sys
from pathlib import Path

from fastmcp import FastMCP
from mcp_config_loader import load_env_file, COMMON_ALLOWED_ENV_VARS

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Initialize FastMCP unified server
mcp = FastMCP("Homelab Unified")

# Load all environment variables ONCE before importing sub-servers
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

logger.info("Starting Unified Homelab MCP Server...")


def compose_servers():
    """Compose all sub-servers into unified server using FastMCP's native pattern

    This function runs at module import time to register all tools from sub-servers.
    FastMCP's add_tool() method properly handles tool registration without manual wrappers.
    """
    # Import sub-servers (they each have their own mcp instance with decorated tools)
    import ansible_mcp_server
    import docker_mcp_podman
    import ping_mcp_server
    import ollama_mcp
    import pihole_mcp
    import unifi_mcp_optimized
    import ups_mcp_server

    logger.info("Composing sub-servers...")

    # Store references to sub-servers for tool composition
    # We'll use FastMCP's internal tool registry to get tools from each server
    subservers = {
        'ansible': ansible_mcp_server.mcp,
        'docker': docker_mcp_podman.mcp,
        'ping': ping_mcp_server.mcp,
        'ollama': ollama_mcp.mcp,
        'pihole': pihole_mcp.mcp,
        'unifi': unifi_mcp_optimized.mcp,
        'ups': ups_mcp_server.mcp,
    }

    # Compose tools from all sub-servers
    # FastMCP's FunctionTool objects can be directly added to another FastMCP instance
    for server_name, server_mcp in subservers.items():
        # Access the internal tools dict (FastMCP stores tools in _tool_manager._tools)
        # Each tool is already properly registered with its prefix from the sub-server
        if hasattr(server_mcp, '_tool_manager') and hasattr(server_mcp._tool_manager, '_tools'):
            tools = server_mcp._tool_manager._tools
            for tool_name, tool in tools.items():
                # Add tool directly - FastMCP handles the registration
                mcp.add_tool(tool)
            logger.info(f"Added {len(tools)} {server_name} tools")
        else:
            logger.warning(f"Could not find tools in {server_name} server")

    logger.info("All sub-servers composed successfully")


# Compose servers at module import time
compose_servers()


if __name__ == "__main__":
    # Run the unified server
    mcp.run()
