#!/usr/bin/env python3
"""
Homelab Unified MCP Server v2.0 (FastMCP)
Unified server that combines all homelab MCP servers into a single entry point
Exposes all tools from docker, ping, ollama, pihole, unifi, ups, and ansible servers
Supports stdio, HTTP, and SSE transports
"""

import asyncio
import json
import logging
import os
import sys
from collections import defaultdict
from pathlib import Path

# CRITICAL: Import Ansible BEFORE FastMCP to avoid import hook conflicts
# FastMCP adds a second FileFinder import hook that breaks Ansible's collection loader
# Ansible's loader expects exactly 1 FileFinder hook, so we must import it first
from ansible_config_manager import AnsibleConfigManager

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

# Import tool functions from all sub-servers
# Each server module exports its tools as decorated functions
import ping_mcp_server
import ups_mcp_server
import ansible_mcp_server
import ollama_mcp
import pihole_mcp
import docker_mcp_podman
import unifi_mcp_optimized


# Ansible Tools (prefix: ansible_)

@mcp.tool()
def ansible_list_all_hosts() -> str:
    """List all hosts from Ansible inventory with their variables and group memberships"""
    return ansible_mcp_server.list_all_hosts.fn()


@mcp.tool()
def ansible_list_groups() -> str:
    """List all groups from Ansible inventory"""
    return ansible_mcp_server.list_groups.fn()


@mcp.tool()
def ansible_get_host_details(hostname: str) -> str:
    """
    Get detailed information about a specific host including all variables and groups

    Args:
        hostname: The hostname to query from Ansible inventory
    """
    return ansible_mcp_server.get_host_details.fn(hostname)


@mcp.tool()
def ansible_get_group_hosts(group: str) -> str:
    """
    List all hosts in a specific Ansible group

    Args:
        group: The group name to query
    """
    return ansible_mcp_server.get_group_hosts.fn(group)


@mcp.tool()
def ansible_query_hosts(pattern: str = "", variable: str = "", value: str = "") -> str:
    """
    Query hosts using Ansible-style patterns or variable matching

    Args:
        pattern: Pattern to match against hostnames (supports wildcards)
        variable: Variable name to search for
        value: Variable value to match (used with variable parameter)
    """
    return ansible_mcp_server.query_hosts.fn(pattern, variable, value)


@mcp.tool()
def ansible_reload_inventory() -> str:
    """Reload Ansible inventory from disk (useful after inventory changes)"""
    return ansible_mcp_server.reload_inventory.fn()


# Docker Tools (prefix: docker_)

@mcp.tool()
def docker_list_all_hosts() -> str:
    """List all Docker/Podman hosts from Ansible inventory"""
    return docker_mcp_podman.list_all_hosts.fn()


@mcp.tool()
async def docker_list_containers(host: str = None) -> str:
    """
    List all containers across Docker/Podman hosts

    Args:
        host: Optional specific host to query (default: all hosts)
    """
    return await docker_mcp_podman.list_containers.fn(host)


@mcp.tool()
async def docker_get_container_details(container_id: str, host: str = None) -> str:
    """
    Get detailed information about a specific container

    Args:
        container_id: Container ID or name
        host: Optional specific host (default: search all hosts)
    """
    # Note: sub-server expects (hostname, container) order
    return await docker_mcp_podman.get_container_details.fn(host, container_id)


@mcp.tool()
async def docker_get_container_logs(container_id: str, host: str = None, lines: int = 100) -> str:
    """
    Get logs from a container

    Args:
        container_id: Container ID or name
        host: Optional specific host
        lines: Number of log lines to retrieve (default: 100)
    """
    # Note: sub-server expects (hostname, container, tail) order
    return await docker_mcp_podman.get_container_logs.fn(host, container_id, lines)


@mcp.tool()
async def docker_get_stats(host: str = None) -> str:
    """
    Get resource usage statistics for containers

    Args:
        host: Optional specific host (default: all hosts)
    """
    return await docker_mcp_podman.get_stats.fn(host)


@mcp.tool()
def docker_reload_inventory() -> str:
    """Reload Docker/Podman inventory from disk"""
    return docker_mcp_podman.reload_inventory.fn()


# Ping Tools (prefix: ping_)

@mcp.tool()
def ping_list_groups() -> str:
    """List all available Ansible groups for pinging"""
    return ping_mcp_server.list_groups.fn()


@mcp.tool()
def ping_list_hosts() -> str:
    """List all hosts in the Ansible inventory with their resolved IPs"""
    return ping_mcp_server.list_hosts.fn()


@mcp.tool()
def ping_reload_inventory() -> str:
    """Reload Ansible inventory from disk"""
    return ping_mcp_server.reload_inventory.fn()


@mcp.tool()
async def ping_host_by_name(hostname: str, count: int = 4, timeout: int = 5) -> str:
    """
    Ping a specific host by hostname from Ansible inventory

    Args:
        hostname: Hostname from Ansible inventory
        count: Number of ping packets to send (default: 4)
        timeout: Timeout in seconds per ping (default: 5)
    """
    return await ping_mcp_server.ping_host_by_name.fn(hostname, count, timeout)


@mcp.tool()
async def ping_group(group: str, count: int = 2, timeout: int = 3) -> str:
    """
    Ping all hosts in an Ansible group

    Args:
        group: Ansible group name from your inventory
        count: Number of ping packets to send (default: 2)
        timeout: Timeout in seconds per ping (default: 3)
    """
    return await ping_mcp_server.ping_group.fn(group, count, timeout)


@mcp.tool()
async def ping_all(count: int = 2, timeout: int = 3) -> str:
    """
    Ping all hosts in the infrastructure

    Args:
        count: Number of ping packets to send (default: 2)
        timeout: Timeout in seconds per ping (default: 3)
    """
    return await ping_mcp_server.ping_all.fn(count, timeout)


# Ollama Tools (prefix: ollama_)

@mcp.tool()
def ollama_list_hosts() -> str:
    """List all Ollama hosts from Ansible inventory"""
    return ollama_mcp.list_hosts.fn()


@mcp.tool()
async def ollama_list_models(host: str = None) -> str:
    """
    List all available models across Ollama hosts

    Args:
        host: Optional specific host to query (default: all hosts)
    """
    return await ollama_mcp.list_models.fn(host)


@mcp.tool()
async def ollama_get_model_info(model_name: str, host: str) -> str:
    """
    Get detailed information about a specific model

    Args:
        model_name: Name of the model to query
        host: Specific Ollama host to query
    """
    # Note: sub-server expects (host, model_name) order
    return await ollama_mcp.get_model_info.fn(host, model_name)


@mcp.tool()
async def ollama_get_running_models() -> str:
    """Get currently running models across all Ollama hosts"""
    return await ollama_mcp.get_running_models.fn()


@mcp.tool()
def ollama_reload_inventory() -> str:
    """Reload Ollama inventory from disk"""
    return ollama_mcp.reload_inventory.fn()


# Pi-hole Tools (prefix: pihole_)

@mcp.tool()
def pihole_list_hosts() -> str:
    """List all Pi-hole hosts from Ansible inventory"""
    return pihole_mcp.list_hosts.fn()


@mcp.tool()
async def pihole_get_summary() -> str:
    """Get Pi-hole summary statistics from all configured Pi-hole instances"""
    return await pihole_mcp.get_summary.fn()


@mcp.tool()
async def pihole_get_top_items(display_name: str = "", limit: int = 10) -> str:
    """
    Get top blocked domains and top queries from Pi-hole

    Args:
        display_name: Optional specific Pi-hole instance (default: all instances)
        limit: Number of items to return (default: 10)
    """
    return await pihole_mcp.get_top_items.fn(display_name, limit)


@mcp.tool()
async def pihole_get_query_types(display_name: str = "") -> str:
    """
    Get breakdown of query types from Pi-hole

    Args:
        display_name: Optional specific Pi-hole instance (default: all instances)
    """
    return await pihole_mcp.get_query_types.fn(display_name)


@mcp.tool()
async def pihole_get_forward_destinations(display_name: str = "") -> str:
    """
    Get forward destination statistics from Pi-hole

    Args:
        display_name: Optional specific Pi-hole instance (default: all instances)
    """
    return await pihole_mcp.get_forward_destinations.fn(display_name)


@mcp.tool()
def pihole_reload_inventory() -> str:
    """Reload Pi-hole inventory from disk"""
    return pihole_mcp.reload_inventory.fn()


# Unifi Tools (prefix: unifi_)

@mcp.tool()
async def unifi_list_devices() -> str:
    """List all Unifi network devices"""
    return await unifi_mcp_optimized.list_devices.fn()


@mcp.tool()
async def unifi_get_device_details(device_id: str) -> str:
    """
    Get detailed information about a specific device

    Args:
        device_id: Device ID or MAC address
    """
    return await unifi_mcp_optimized.get_device_details.fn(device_id)


@mcp.tool()
async def unifi_list_clients() -> str:
    """List all connected clients"""
    return await unifi_mcp_optimized.list_clients.fn()


@mcp.tool()
async def unifi_get_client_details(client_id: str) -> str:
    """
    Get detailed information about a specific client

    Args:
        client_id: Client ID or MAC address
    """
    return await unifi_mcp_optimized.get_client_details.fn(client_id)


@mcp.tool()
async def unifi_get_network_stats() -> str:
    """Get overall network statistics"""
    return await unifi_mcp_optimized.get_network_stats.fn()


# UPS Tools (prefix: ups_)

@mcp.tool()
def ups_list_hosts() -> str:
    """List all UPS/NUT hosts from Ansible inventory"""
    return ups_mcp_server.list_hosts.fn()


@mcp.tool()
async def ups_get_status() -> str:
    """Get UPS status from all configured NUT servers"""
    return await ups_mcp_server.get_status.fn()


@mcp.tool()
async def ups_get_details(host: str, ups_name: str = "") -> str:
    """
    Get detailed UPS information from specific NUT server

    Args:
        host: Hostname of the NUT server to query
        ups_name: Optional specific UPS name (default: first UPS on host)
    """
    return await ups_mcp_server.get_details.fn(host, ups_name)


@mcp.tool()
async def ups_get_battery_info() -> str:
    """Get battery information from all configured UPS devices"""
    return await ups_mcp_server.get_battery_info.fn()


@mcp.tool()
def ups_reload_inventory() -> str:
    """Reload UPS/NUT inventory from disk"""
    return ups_mcp_server.reload_inventory.fn()


# Unified Catalog Tool

@mcp.tool()
def homelab_get_tool_catalog() -> str:
    """
    Get a grouped catalog of all available Homelab MCP tools
    Returns JSON with both markdown and structured data formats
    """
    # Get all registered tools from the FastMCP instance
    # Note: FastMCP doesn't have a public API to list tools, so we'll generate manually
    tools_by_category = {
        "ansible": [
            "ansible_list_all_hosts", "ansible_list_groups", "ansible_get_host_details",
            "ansible_get_group_hosts", "ansible_query_hosts", "ansible_reload_inventory"
        ],
        "docker": [
            "docker_list_all_hosts", "docker_list_containers", "docker_get_container_details",
            "docker_get_container_logs", "docker_get_stats", "docker_reload_inventory"
        ],
        "ping": [
            "ping_list_groups", "ping_list_hosts", "ping_reload_inventory",
            "ping_host_by_name", "ping_group", "ping_all"
        ],
        "ollama": [
            "ollama_list_hosts", "ollama_list_models", "ollama_get_model_info",
            "ollama_get_running_models", "ollama_reload_inventory"
        ],
        "pihole": [
            "pihole_list_hosts", "pihole_get_summary", "pihole_get_top_items",
            "pihole_get_query_types", "pihole_get_forward_destinations", "pihole_reload_inventory"
        ],
        "unifi": [
            "unifi_list_devices", "unifi_get_device_details", "unifi_list_clients",
            "unifi_get_client_details", "unifi_get_network_stats"
        ],
        "ups": [
            "ups_list_hosts", "ups_get_status", "ups_get_details",
            "ups_get_battery_info", "ups_reload_inventory"
        ],
        "homelab": [
            "homelab_get_tool_catalog"
        ]
    }

    # Build markdown catalog
    md_lines = ["# Homelab MCP Tool Catalog\n"]
    md_lines.append(f"Total tools: {sum(len(tools) for tools in tools_by_category.values())}\n")

    for category in sorted(tools_by_category.keys()):
        md_lines.append(f"\n## {category.capitalize()} Tools ({len(tools_by_category[category])} tools)\n")
        for tool_name in sorted(tools_by_category[category]):
            md_lines.append(f"- `{tool_name}`")

    catalog = {
        "markdown": "\n".join(md_lines),
        "categories": tools_by_category,
        "total_tools": sum(len(tools) for tools in tools_by_category.values())
    }

    return json.dumps(catalog, indent=2)


# Entry point
if __name__ == "__main__":
    logger.info("Starting Unified Homelab MCP Server...")
    logger.info("All sub-servers initialized via import")

    # Run with stdio transport by default (backward compatible)
    mcp.run()

    # Alternative transports (comment/uncomment as needed):
    # mcp.run(transport="http", host="0.0.0.0", port=8000)
    # mcp.run(transport="sse", host="0.0.0.0", port=8000)
