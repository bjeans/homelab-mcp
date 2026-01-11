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

from fastmcp import FastMCP

from ansible_config_manager import load_group_hosts
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

@mcp.tool()
async def get_ollama_status() -> str:
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


@mcp.tool()
async def get_ollama_models(host: str) -> str:
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


@mcp.tool()
async def get_litellm_status() -> str:
    """Check LiteLLM proxy status"""
    url = f"http://{LITELLM_HOST}:{LITELLM_PORT}/health/liveliness"
    logger.info(f"Checking LiteLLM at {url}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                logger.info(f"LiteLLM response status: {response.status}")
                if response.status == 200:
                    data = await response.text()  # Liveliness returns text, not JSON
                    output = f"✓ LiteLLM Proxy: ONLINE\n"
                    output += f"Endpoint: {LITELLM_HOST}:{LITELLM_PORT}\n\n"
                    output += f"Liveliness Check: {data}"
                    return output
                elif response.status == 401:
                    error_msg = MCPErrorClassifier.format_http_error(
                        service_name="LiteLLM Proxy",
                        status_code=401,
                        hostname=f"{LITELLM_HOST}:{LITELLM_PORT}",
                        custom_remediation="LiteLLM requires authentication. Configure API key if authentication is enabled."
                    )
                    return error_msg
                elif response.status == 429:
                    error_msg = MCPErrorClassifier.format_http_error(
                        service_name="LiteLLM Proxy",
                        status_code=429,
                        hostname=f"{LITELLM_HOST}:{LITELLM_PORT}",
                        custom_remediation="Rate limit exceeded. Wait a few moments before retrying."
                    )
                    return error_msg
                else:
                    error_msg = MCPErrorClassifier.format_http_error(
                        service_name="LiteLLM Proxy",
                        status_code=response.status,
                        hostname=f"{LITELLM_HOST}:{LITELLM_PORT}"
                    )
                    log_error_with_context(
                        logger,
                        f"LiteLLM returned HTTP {response.status}",
                        context={"host": LITELLM_HOST, "port": LITELLM_PORT, "status": response.status}
                    )
                    return error_msg
    except asyncio.TimeoutError:
        error_msg = MCPErrorClassifier.format_timeout_error(
            service_name="LiteLLM Proxy",
            hostname=LITELLM_HOST,
            port=int(LITELLM_PORT),
            timeout_seconds=5
        )
        log_error_with_context(
            logger,
            "LiteLLM connection timeout",
            context={"host": LITELLM_HOST, "port": LITELLM_PORT}
        )
        return error_msg
    except aiohttp.ClientConnectorError as e:
        error_msg = MCPErrorClassifier.format_connection_error(
            service_name="LiteLLM Proxy",
            hostname=LITELLM_HOST,
            port=int(LITELLM_PORT),
            additional_guidance="Ensure LiteLLM proxy is running. Check: docker ps | grep litellm"
        )
        log_error_with_context(
            logger,
            "LiteLLM connection refused",
            error=e,
            context={"host": LITELLM_HOST, "port": LITELLM_PORT}
        )
        return error_msg
    except Exception as e:
        error_msg = MCPErrorClassifier.format_error_message(
            service_name="LiteLLM Proxy",
            error_type="Unexpected Error",
            message=f"Failed to check LiteLLM status",
            remediation="Check the error details and ensure LiteLLM proxy is accessible.",
            details=str(e),
            hostname=f"{LITELLM_HOST}:{LITELLM_PORT}"
        )
        log_error_with_context(logger, "LiteLLM check error", error=e, context={"host": LITELLM_HOST, "port": LITELLM_PORT})
        return error_msg


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
