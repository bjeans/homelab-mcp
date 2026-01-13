#!/usr/bin/env python3
"""
Pi-hole MCP Server v3.0 (FastMCP)
Provides DNS statistics from Pi-hole instances using session-based authentication
Supports Pi-hole v6 API with automatic session management and refresh
Reads host configuration from Ansible inventory

Features:
- Get DNS statistics from all Pi-hole instances
- Check which Pi-hole instances are online
- Session-based authentication with automatic refresh
- Supports stdio, HTTP, and SSE transports
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

import aiohttp

# CRITICAL: Import Ansible BEFORE FastMCP to avoid import hook conflicts
# FastMCP adds a second FileFinder import hook that breaks Ansible's collection loader
from ansible_config_manager import load_group_hosts

from fastmcp import FastMCP

from mcp_config_loader import load_env_file, COMMON_ALLOWED_ENV_VARS
from mcp_error_handler import MCPErrorClassifier, log_error_with_context

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("Pi-hole Monitor")

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

# Global caches
_pihole_hosts_cache = None
_session_cache = {}  # {hostname: {'sid': str, 'expires_at': datetime}}


def _load_pihole_hosts():
    """Load Pi-hole hosts from Ansible inventory or environment variables"""
    global _pihole_hosts_cache

    if _pihole_hosts_cache is not None:
        return _pihole_hosts_cache

    # Try Ansible inventory first
    pihole_group_name = os.getenv("PIHOLE_ANSIBLE_GROUP", "PiHole")
    hosts = load_group_hosts(
        pihole_group_name,
        inventory_path=ANSIBLE_INVENTORY_PATH,
        logger_obj=logger
    )

    if hosts:
        pihole_hosts = []
        for display_name, host in hosts.items():
            port = 80  # Default Pi-hole port
            api_key = os.getenv(f"PIHOLE_API_KEY_{display_name.replace('-', '_').upper()}", "")
            pihole_hosts.append((display_name, host, port, api_key))
            logger.info(f"Found Pi-hole host: {display_name} -> {host}:{port}")

        _pihole_hosts_cache = pihole_hosts
        logger.info(f"Loaded {len(pihole_hosts)} Pi-hole hosts from Ansible inventory")
        return _pihole_hosts_cache

    # Fallback to environment variables
    logger.warning(f"No hosts found in '{pihole_group_name}' group, checking environment variables")
    pihole_hosts = []
    processed_names = set()

    for key, value in os.environ.items():
        if key.startswith("PIHOLE_") and key.endswith("_HOST"):
            name_part = key.replace("PIHOLE_", "").replace("_HOST", "")

            if name_part in processed_names:
                continue
            processed_names.add(name_part)

            host = os.environ.get(f"PIHOLE_{name_part}_HOST", "")
            port_str = os.environ.get(f"PIHOLE_{name_part}_PORT", "80")
            api_key = os.environ.get(f"PIHOLE_API_KEY_{name_part}", "")

            try:
                port = int(port_str)
            except (ValueError, TypeError):
                port = 80
                logger.warning(f"Invalid port '{port_str}' for {name_part}, using default 80")

            display_name = name_part.replace("_", "-").title()

            if host:
                pihole_hosts.append((display_name, host, port, api_key))
                logger.info(f"Loaded from env: {display_name} -> {host}:{port} (api_key: {'***' if api_key else 'NOT SET'})")

    _pihole_hosts_cache = pihole_hosts
    return _pihole_hosts_cache


async def get_pihole_session(host: str, port: int, password: str):
    """Get or refresh a Pi-hole session"""
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
                        validity_seconds = session_data.get("validity", 300)
                        expires_at = datetime.now() + timedelta(seconds=validity_seconds - 30)
                        return {"sid": session_data["sid"], "expires_at": expires_at}
                    else:
                        message = session_data.get("message", "Authentication failed")
                        return {"error": f"Invalid password for {host}: {message}"}
                elif response.status == 401:
                    error_msg = MCPErrorClassifier.format_http_error(
                        service_name="Pi-hole",
                        status_code=401,
                        hostname=f"{host}:{port}",
                        custom_remediation=f"Invalid API password. Check the PIHOLE_API_KEY environment variable."
                    )
                    return {"error": error_msg}
                else:
                    text = await response.text()
                    error_msg = MCPErrorClassifier.format_http_error(
                        service_name="Pi-hole",
                        status_code=response.status,
                        response_text=text,
                        hostname=f"{host}:{port}"
                    )
                    return {"error": error_msg}

    except asyncio.TimeoutError:
        error_msg = MCPErrorClassifier.format_timeout_error(
            service_name="Pi-hole",
            hostname=host,
            port=port,
            timeout_seconds=5
        )
        return {"error": error_msg}
    except aiohttp.ClientConnectorError as e:
        error_msg = MCPErrorClassifier.format_connection_error(
            service_name="Pi-hole",
            hostname=host,
            port=port,
            additional_guidance="Check if Pi-hole service is running: systemctl status pihole-FTL"
        )
        return {"error": error_msg}
    except Exception as e:
        error_msg = f"Failed to connect to Pi-hole at {host}:{port}: {str(e)}"
        return {"error": error_msg}


async def get_cached_session(display_name: str, host: str, port: int, api_key: str):
    """Get a valid session from cache or create a new one"""
    if not api_key:
        return {"error": "No API key configured"}

    cache_key = display_name
    if cache_key in _session_cache:
        cached = _session_cache[cache_key]
        if datetime.now() < cached["expires_at"]:
            return {"sid": cached["sid"]}
        else:
            logger.info(f"Session expired for {display_name}, refreshing...")

    session_info = await get_pihole_session(host, port, api_key)

    if "error" not in session_info:
        _session_cache[cache_key] = session_info
        logger.info(f"New session obtained for {display_name}, expires at {session_info['expires_at']}")
        return {"sid": session_info["sid"]}

    return session_info


async def pihole_api_request(host: str, port: int, endpoint: str, sid: str, timeout: int = 5):
    """Make an authenticated request to Pi-hole API using session ID"""
    encoded_sid = quote(sid)
    url = f"http://{host}:{port}{endpoint}?sid={encoded_sid}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 401:
                    logger.warning(f"Session expired or invalid for {host} (HTTP 401)")
                    return None
                else:
                    log_error_with_context(
                        logger,
                        f"Pi-hole API request failed with HTTP {response.status}",
                        context={"host": host, "port": port, "endpoint": endpoint, "status": response.status}
                    )
                    return None
    except asyncio.TimeoutError:
        log_error_with_context(
            logger,
            "Pi-hole API request timeout",
            context={"host": host, "port": port, "endpoint": endpoint, "timeout": timeout}
        )
        return None
    except Exception as e:
        log_error_with_context(
            logger,
            "Pi-hole API request error",
            error=e,
            context={"host": host, "port": port, "endpoint": endpoint}
        )
        return None


# FastMCP Tools

@mcp.tool()
async def get_summary() -> str:
    """Get DNS statistics from all Pi-hole instances"""
    pihole_hosts = _load_pihole_hosts()

    if not pihole_hosts:
        return "No Pi-hole hosts configured. Please set ANSIBLE_INVENTORY_PATH or PIHOLE_*_HOST environment variables."

    output = "=== PI-HOLE DNS STATISTICS ===\n\n"

    for display_name, host, port, api_key in pihole_hosts:
        output += f"--- {display_name} ---\n"

        session_result = await get_cached_session(display_name, host, port, api_key)

        if "error" in session_result:
            output += f"Error: {session_result['error']}\n\n"
            continue

        sid = session_result["sid"]
        data = await pihole_api_request(host, port, "/api/stats/summary", sid)

        if data:
            queries = data.get("queries", {})
            clients = data.get("clients", {})
            gravity = data.get("gravity", {})

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

    return output


@mcp.tool()
async def list_hosts() -> str:
    """Check which Pi-hole instances are online"""
    pihole_hosts = _load_pihole_hosts()

    if not pihole_hosts:
        return "No Pi-hole hosts configured."

    output = "=== PI-HOLE STATUS ===\n\n"
    online = 0

    for display_name, host, port, api_key in pihole_hosts:
        session_result = await get_cached_session(display_name, host, port, api_key)

        if "error" in session_result:
            output += f"✗ {display_name} ({host}:{port}): OFFLINE\n"
        else:
            online += 1
            output += f"✓ {display_name} ({host}:{port}): ONLINE\n"

    output = f"Online: {online}/{len(pihole_hosts)}\n\n" + output
    return output


@mcp.tool()
async def get_top_items(display_name: str = "", limit: int = 10) -> str:
    """
    Get top blocked domains and top clients

    Args:
        display_name: Pi-hole instance name (optional, queries all if not specified)
        limit: Number of top items to return (default: 10)
    """
    pihole_hosts = _load_pihole_hosts()

    if not pihole_hosts:
        return "No Pi-hole hosts configured."

    # Filter to specific host if provided
    if display_name:
        pihole_hosts = [(n, h, p, k) for n, h, p, k in pihole_hosts if n == display_name]
        if not pihole_hosts:
            return f"Error: Pi-hole instance '{display_name}' not found"

    output = "=== TOP ITEMS ===\n\n"

    for name, host, port, api_key in pihole_hosts:
        output += f"--- {name} ---\n"

        session_result = await get_cached_session(name, host, port, api_key)

        if "error" in session_result:
            output += f"Error: {session_result['error']}\n\n"
            continue

        sid = session_result["sid"]

        # Get top blocked domains
        top_blocked = await pihole_api_request(host, port, f"/api/stats/top_blocked?count={limit}", sid)

        if top_blocked and "top_blocked" in top_blocked:
            output += "Top Blocked Domains:\n"
            for i, (domain, count) in enumerate(top_blocked["top_blocked"].items(), 1):
                output += f"  {i}. {domain}: {count:,} queries\n"
            output += "\n"

        # Get top clients
        top_clients = await pihole_api_request(host, port, f"/api/stats/top_clients?count={limit}", sid)

        if top_clients and "top_clients" in top_clients:
            output += "Top Clients:\n"
            for i, (client, count) in enumerate(top_clients["top_clients"].items(), 1):
                output += f"  {i}. {client}: {count:,} queries\n"
            output += "\n"

    return output


@mcp.tool()
async def get_query_types(display_name: str = "") -> str:
    """
    Get DNS query type statistics

    Args:
        display_name: Pi-hole instance name (optional, queries all if not specified)
    """
    pihole_hosts = _load_pihole_hosts()

    if not pihole_hosts:
        return "No Pi-hole hosts configured."

    # Filter to specific host if provided
    if display_name:
        pihole_hosts = [(n, h, p, k) for n, h, p, k in pihole_hosts if n == display_name]
        if not pihole_hosts:
            return f"Error: Pi-hole instance '{display_name}' not found"

    output = "=== QUERY TYPES ===\n\n"

    for name, host, port, api_key in pihole_hosts:
        output += f"--- {name} ---\n"

        session_result = await get_cached_session(name, host, port, api_key)

        if "error" in session_result:
            output += f"Error: {session_result['error']}\n\n"
            continue

        sid = session_result["sid"]
        data = await pihole_api_request(host, port, "/api/stats/query_types", sid)

        if data and "query_types" in data:
            query_types = data["query_types"]
            output += "DNS Query Types:\n"
            for qtype, percentage in sorted(query_types.items(), key=lambda x: x[1], reverse=True):
                output += f"  {qtype}: {percentage:.1f}%\n"
            output += "\n"
        else:
            output += "Could not retrieve query types\n\n"

    return output


@mcp.tool()
async def get_forward_destinations(display_name: str = "") -> str:
    """
    Get upstream DNS server statistics

    Args:
        display_name: Pi-hole instance name (optional, queries all if not specified)
    """
    pihole_hosts = _load_pihole_hosts()

    if not pihole_hosts:
        return "No Pi-hole hosts configured."

    # Filter to specific host if provided
    if display_name:
        pihole_hosts = [(n, h, p, k) for n, h, p, k in pihole_hosts if n == display_name]
        if not pihole_hosts:
            return f"Error: Pi-hole instance '{display_name}' not found"

    output = "=== FORWARD DESTINATIONS ===\n\n"

    for name, host, port, api_key in pihole_hosts:
        output += f"--- {name} ---\n"

        session_result = await get_cached_session(name, host, port, api_key)

        if "error" in session_result:
            output += f"Error: {session_result['error']}\n\n"
            continue

        sid = session_result["sid"]
        data = await pihole_api_request(host, port, "/api/stats/upstreams", sid)

        if data and "upstreams" in data:
            upstreams = data["upstreams"]
            output += "Upstream DNS Servers:\n"
            for upstream, stats in sorted(upstreams.items(), key=lambda x: x[1].get("count", 0), reverse=True):
                count = stats.get("count", 0)
                percentage = stats.get("percentage", 0)
                output += f"  {upstream}: {count:,} queries ({percentage:.1f}%)\n"
            output += "\n"
        else:
            output += "Could not retrieve upstream statistics\n\n"

    return output


@mcp.tool()
def reload_inventory() -> str:
    """Reload Pi-hole hosts from Ansible inventory (useful after inventory changes)"""
    global _pihole_hosts_cache
    _pihole_hosts_cache = None
    pihole_hosts = _load_pihole_hosts()

    output = "=== INVENTORY RELOADED ===\n\n"
    output += f"✓ Loaded {len(pihole_hosts)} Pi-hole host(s)\n\n"

    for display_name, host, port, api_key in pihole_hosts:
        output += f"  • {display_name} -> {host}:{port}\n"

    return output


# Entry point
if __name__ == "__main__":
    # Load hosts on startup
    pihole_hosts = _load_pihole_hosts()
    logger.info(f"Pi-hole MCP Server starting with {len(pihole_hosts)} Pi-hole host(s)")

    if not pihole_hosts:
        logger.error("No Pi-hole hosts configured!")
        logger.error("Please set ANSIBLE_INVENTORY_PATH or PIHOLE_*_HOST environment variables")

    # Run with stdio transport by default (backward compatible)
    mcp.run()

    # Alternative transports (comment/uncomment as needed):
    # mcp.run(transport="http", host="0.0.0.0", port=8000)
    # mcp.run(transport="sse", host="0.0.0.0", port=8000)
