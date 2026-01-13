#!/usr/bin/env python3
"""
Ollama MCP Server v2.0 (FastMCP)
Provides access to Ollama instances and models
Reads host configuration from Ansible inventory

Features:
- Check status of all Ollama instances
- Get models on specific hosts
- Check LiteLLM proxy status
- Automatic discovery via Ansible inventory
- Supports stdio, HTTP, and SSE transports
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import aiohttp

# CRITICAL: Import Ansible BEFORE FastMCP to avoid import hook conflicts
# FastMCP adds a second FileFinder import hook that breaks Ansible's collection loader
from ansible_config_manager import load_group_hosts

from fastmcp import FastMCP
from mcp import types

from mcp_config_loader import COMMON_ALLOWED_ENV_VARS, load_env_file
from mcp_error_handler import MCPErrorClassifier, log_error_with_context

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("Ollama Monitor")

# Load .env with security hardening
SCRIPT_DIR = Path(__file__).parent
ENV_FILE = SCRIPT_DIR / ".env"

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

# Global cache for ollama endpoints
_endpoints_cache = None


def _load_ollama_endpoints():
    """Load Ollama endpoints from Ansible inventory or environment variables"""
    global _endpoints_cache

    if _endpoints_cache is not None:
        return _endpoints_cache

    # Try Ansible inventory first
    hosts = load_group_hosts(
        OLLAMA_INVENTORY_GROUP,
        inventory_path=ANSIBLE_INVENTORY_PATH,
        logger_obj=logger
    )

    if hosts:
        logger.info(f"Found {len(hosts)} Ollama hosts from Ansible inventory")
        _endpoints_cache = hosts
        return _endpoints_cache

    # Fallback to environment variables
    logger.warning(f"No hosts found in '{OLLAMA_INVENTORY_GROUP}' group, checking environment variables")
    endpoints = {}

    for key, value in os.environ.items():
        if key.startswith("OLLAMA_") and key not in ["OLLAMA_PORT", "OLLAMA_INVENTORY_GROUP"]:
            display_name = key.replace("OLLAMA_", "").replace("_", "-").title()
            # Strip port if included (port is added separately via OLLAMA_PORT)
            ip_only = value.split(":")[0] if ":" in value else value
            endpoints[display_name] = ip_only
            if ip_only != value:
                logger.info(f"Loaded from env: {display_name} -> {ip_only} (stripped port from {value})")
            else:
                logger.info(f"Loaded from env: {display_name} -> {ip_only}")

    _endpoints_cache = endpoints
    return _endpoints_cache


async def ollama_request(host_ip: str, endpoint: str, port: int = 11434, timeout: int = 5) -> Optional[dict]:
    """
    Make request to Ollama API

    Args:
        host_ip: Ollama host IP address
        endpoint: API endpoint (e.g., /api/tags)
        port: Ollama port (default 11434)
        timeout: Request timeout in seconds

    Returns:
        JSON response data on success, None on failure
    """
    url = f"http://{host_ip}:{port}{endpoint}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 401:
                    logger.warning(f"Ollama API authentication required at {host_ip}:{port} (HTTP 401)")
                    return None
                elif response.status == 404:
                    logger.warning(f"Ollama endpoint not found: {endpoint} at {host_ip}:{port} (HTTP 404)")
                    return None
                elif response.status == 500:
                    logger.warning(f"Ollama server error at {host_ip}:{port} (HTTP 500)")
                    return None
                else:
                    log_error_with_context(
                        logger,
                        f"Ollama API request failed with HTTP {response.status}",
                        context={"host": host_ip, "port": port, "endpoint": endpoint, "status": response.status}
                    )
                    return None
    except asyncio.TimeoutError:
        log_error_with_context(
            logger,
            f"Ollama request timeout after {timeout}s",
            context={"host": host_ip, "port": port, "endpoint": endpoint, "timeout": timeout}
        )
        return None
    except aiohttp.ClientConnectorError as e:
        logger.debug(f"Ollama connection failed for {host_ip}:{port} - service may be offline")
        return None
    except Exception as e:
        log_error_with_context(
            logger,
            f"Ollama request error",
            error=e,
            context={"host": host_ip, "port": port, "endpoint": endpoint}
        )
        return None


# FastMCP Tools

@mcp.tool(
    title="List Ollama Instances",
    annotations=types.ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    )
)
async def list_hosts() -> str:
    """Check status of all Ollama instances"""
    endpoints = _load_ollama_endpoints()

    if not endpoints:
        return "No Ollama endpoints configured. Please set ANSIBLE_INVENTORY_PATH or OLLAMA_* environment variables."

    output = "=== OLLAMA STATUS ===\n\n"
    total_models = 0
    online = 0

    for host_name, ip in endpoints.items():
        data = await ollama_request(ip, "/api/tags", OLLAMA_PORT, timeout=3)

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

    output = f"Summary: {online}/{len(endpoints)} online, {total_models} models\n\n" + output
    return output


@mcp.tool(
    title="List Models on Host",
    annotations=types.ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    )
)
async def list_models(host: str) -> str:
    """
    Get models on a specific Ollama host

    Args:
        host: Ollama host from your Ansible inventory
    """
    endpoints = _load_ollama_endpoints()

    if host not in endpoints:
        return f"Invalid host: {host}\nAvailable hosts: {', '.join(endpoints.keys())}"

    ip = endpoints[host]
    data = await ollama_request(ip, "/api/tags", OLLAMA_PORT, timeout=5)

    if not data:
        return f"{host} is offline or unreachable"

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

    return output


@mcp.tool(
    title="Get Model Info",
    annotations=types.ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    )
)
async def get_model_info(host: str, model_name: str) -> str:
    """
    Get detailed information about a specific model on a host

    Args:
        host: Ollama host from your Ansible inventory
        model_name: Name of the model to query
    """
    endpoints = _load_ollama_endpoints()

    if host not in endpoints:
        return f"Invalid host: {host}\nAvailable hosts: {', '.join(endpoints.keys())}"

    ip = endpoints[host]
    data = await ollama_request(ip, "/api/tags", OLLAMA_PORT, timeout=5)

    if not data:
        return f"{host} is offline or unreachable"

    models = data.get("models", [])

    # Find the specific model
    for model in models:
        name = model.get("name", "")
        if name == model_name or name.startswith(model_name):
            size = model.get("size", 0) / (1024**3)
            modified = model.get("modified_at", "Unknown")
            digest = model.get("digest", "Unknown")

            output = f"=== MODEL INFO: {name} on {host} ===\n\n"
            output += f"Size: {size:.2f}GB\n"
            output += f"Modified: {modified}\n"
            output += f"Digest: {digest}\n"

            details = model.get("details", {})
            if details:
                output += f"\nDetails:\n"
                for key, value in details.items():
                    output += f"  {key}: {value}\n"

            return output

    return f"Model '{model_name}' not found on {host}"


@mcp.tool(
    title="Get Running Models",
    annotations=types.ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    )
)
async def get_running_models() -> str:
    """Get currently running models across all Ollama hosts"""
    endpoints = _load_ollama_endpoints()

    if not endpoints:
        return "No Ollama endpoints configured."

    output = "=== RUNNING MODELS ===\n\n"
    total_running = 0

    for host_name, ip in endpoints.items():
        # Query running models endpoint
        data = await ollama_request(ip, "/api/ps", OLLAMA_PORT, timeout=3)

        if data:
            models = data.get("models", [])
            if models:
                total_running += len(models)
                output += f"• {host_name} ({ip}):\n"
                for model in models:
                    name = model.get("name", "Unknown")
                    size = model.get("size", 0) / (1024**3)
                    output += f"    - {name} ({size:.1f}GB)\n"
                output += "\n"
        else:
            output += f"✗ {host_name} ({ip}): OFFLINE\n\n"

    if total_running == 0:
        output += "No models currently running\n"
    else:
        output = f"Total running: {total_running} model(s)\n\n" + output

    return output


@mcp.tool(
    title="Reload Inventory",
    annotations=types.ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    )
)
def reload_inventory() -> str:
    """Reload Ollama endpoints from Ansible inventory (useful after inventory changes)"""
    global _endpoints_cache
    _endpoints_cache = None
    endpoints = _load_ollama_endpoints()

    output = "=== INVENTORY RELOADED ===\n\n"
    output += f"✓ Loaded {len(endpoints)} Ollama endpoint(s)\n\n"

    for host_name, ip in endpoints.items():
        output += f"  • {host_name} -> {ip}:{OLLAMA_PORT}\n"

    return output


# Entry point
if __name__ == "__main__":
    # Load endpoints on startup
    endpoints = _load_ollama_endpoints()
    logger.info(f"Ollama MCP Server starting with {len(endpoints)} endpoint(s)")

    if not endpoints:
        logger.error("No Ollama endpoints configured!")
        logger.error("Please set ANSIBLE_INVENTORY_PATH or OLLAMA_* environment variables")

    # Run with stdio transport by default (backward compatible)
    mcp.run()

    # Alternative transports (comment/uncomment as needed):
    # mcp.run(transport="http", host="0.0.0.0", port=8000)
    # mcp.run(transport="sse", host="0.0.0.0", port=8000)
