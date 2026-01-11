#!/usr/bin/env python3
"""
Ping MCP Server v2.0 (FastMCP)
Provides network connectivity testing via ICMP ping across homelab infrastructure
Reads host configuration from Ansible inventory with fallback to .env

Features:
- Ping individual hosts by name
- Ping entire Ansible groups
- Ping all hosts
- Custom timeout and packet count
- Cross-platform support (Windows/Linux/macOS)
- Supports stdio, HTTP, and SSE transports
"""

import asyncio
import logging
import os
import platform
import re
import sys
from pathlib import Path
from typing import Dict, Optional

from fastmcp import FastMCP

from ansible_config_manager import AnsibleConfigManager
from mcp_config_loader import load_env_file, load_indexed_env_vars, COMMON_ALLOWED_ENV_VARS

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("Ping Monitor")

# Load .env with security hardening
SCRIPT_DIR = Path(__file__).parent
ENV_FILE = SCRIPT_DIR / ".env"

PING_ALLOWED_VARS = COMMON_ALLOWED_ENV_VARS | {
    "PING_*",  # Pattern for ping-specific variables if needed
}

# Only load env file at module level if not in unified mode
if not os.getenv("MCP_UNIFIED_MODE"):
    load_env_file(ENV_FILE, allowed_vars=PING_ALLOWED_VARS, strict=True)

# Configuration
ANSIBLE_INVENTORY_PATH = os.getenv("ANSIBLE_INVENTORY_PATH", "")
logger.info(f"Ansible inventory: {ANSIBLE_INVENTORY_PATH}")

# Global inventory cache
_inventory_cache = None


def load_ping_targets_from_env():
    """
    Fallback: Load ping targets from environment variables.
    Returns dict with hosts and groups in same format as Ansible inventory.

    Expects environment variables like:
    - PING_TARGET1=8.8.8.8
    - PING_TARGET1_NAME=Google-DNS
    - PING_TARGET2=1.1.1.1
    - PING_TARGET2_NAME=Cloudflare-DNS
    """
    # Use generic function to parse indexed environment variables
    indexed_targets = load_indexed_env_vars(
        prefix="PING_TARGET",
        name_suffix="_NAME",
        target_suffix="",
        logger_obj=logger
    )

    # Convert generic format to Ansible-like format
    hosts = {}
    for index, target_info in indexed_targets.items():
        target = target_info["target"]
        name = target_info["name"]

        if not target:
            logger.warning(f"PING_TARGET{index} name defined but no target IP/hostname provided")
            continue

        # Use provided name or derive from target
        hostname = name if name else f"ping-target-{index}"

        hosts[hostname] = {
            "groups": ["env_targets"],
            "vars": {
                "ansible_host": target
            }
        }
        logger.info(f"Added ping target: {hostname} ({target})")

    if not hosts:
        logger.warning("No ping targets found in environment variables")
        return {"hosts": {}, "groups": {}}

    logger.info(f"Loaded {len(hosts)} ping targets from environment variables")

    # Return in same format as Ansible inventory
    return {
        "hosts": hosts,
        "groups": {"env_targets": list(hosts.keys())}
    }


def _load_inventory():
    """
    Load and cache the Ansible inventory with full variable inheritance.
    Falls back to environment variables if Ansible inventory not found.
    """
    global _inventory_cache

    # Use cached data if available
    if _inventory_cache is not None:
        return _inventory_cache

    # Get ansible inventory path
    ansible_inventory_path = os.getenv("ANSIBLE_INVENTORY_PATH", "")

    if not ansible_inventory_path or not Path(ansible_inventory_path).exists():
        logger.warning(f"Ansible inventory not found at: {ansible_inventory_path}")
        logger.info("Attempting to load ping targets from environment variables")
        _inventory_cache = load_ping_targets_from_env()
        if _inventory_cache and _inventory_cache.get("hosts"):
            logger.info(f"Loaded {len(_inventory_cache['hosts'])} ping targets from environment")
            return _inventory_cache
        logger.error("No ping targets configured in Ansible inventory or environment variables")
        return {"hosts": {}, "groups": {}}

    # Use centralized config manager
    manager = AnsibleConfigManager(
        inventory_path=ansible_inventory_path,
        logger_obj=logger
    )

    if not manager.is_available():
        logger.warning("Ansible inventory not accessible via AnsibleConfigManager")
        logger.info("Attempting to load ping targets from environment variables as fallback")
        _inventory_cache = load_ping_targets_from_env()
        if _inventory_cache and _inventory_cache.get("hosts"):
            logger.info(f"Loaded {len(_inventory_cache['hosts'])} ping targets from environment variables")
            return _inventory_cache
        return {"hosts": {}, "groups": {}}

    # Get all hosts with proper inheritance
    _inventory_cache = manager.get_all_hosts_with_inheritance()

    if not _inventory_cache.get("hosts"):
        logger.warning("No hosts found in Ansible inventory, falling back to environment variables")
        _inventory_cache = load_ping_targets_from_env()
        if _inventory_cache and _inventory_cache.get("hosts"):
            logger.info(f"Loaded {len(_inventory_cache['hosts'])} ping targets from environment variables")
            return _inventory_cache

    logger.info(
        f"Loaded {len(_inventory_cache['hosts'])} hosts and {len(_inventory_cache['groups'])} groups "
        f"with variable inheritance"
    )
    return _inventory_cache


def get_host_ip(hostname: str, host_data: dict) -> str:
    """
    Extract IP address or hostname for pinging
    Checks: ansible_host var, static_ip var, or uses hostname directly
    """
    # Check for ansible_host variable
    if "vars" in host_data and "ansible_host" in host_data["vars"]:
        return host_data["vars"]["ansible_host"]

    # Check for static_ip variable
    if "vars" in host_data and "static_ip" in host_data["vars"]:
        return host_data["vars"]["static_ip"]

    # Handle special case: hostname with port (e.g., hostname.example.com:2222)
    if ":" in hostname:
        hostname = hostname.split(":")[0]

    # Use hostname directly
    return hostname


async def ping_host(host: str, count: int = 4, timeout: int = 5) -> Dict:
    """
    Ping a single host using system ping command

    Args:
        host: Hostname or IP address to ping
        count: Number of ping packets to send
        timeout: Timeout in seconds

    Returns:
        Dict with status, stats, and error info
    """
    system = platform.system().lower()

    # Build platform-specific ping command
    if system == "windows":
        cmd = ["ping", "-n", str(count), "-w", str(timeout * 1000), host]
    else:  # Linux, macOS, etc.
        cmd = ["ping", "-c", str(count), "-W", str(timeout), host]

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=timeout + 5
        )

        output = stdout.decode("utf-8", errors="ignore")

        # Parse output for statistics
        result = {
            "host": host,
            "reachable": process.returncode == 0,
            "packets_sent": count,
            "packets_received": 0,
            "packet_loss": 100.0,
            "rtt_min": None,
            "rtt_avg": None,
            "rtt_max": None,
        }

        if process.returncode == 0:
            # Parse statistics from output
            if system == "windows":
                # Windows format: "Packets: Sent = 4, Received = 4, Lost = 0 (0% loss)"
                match = re.search(r"Received = (\d+)", output)
                if match:
                    result["packets_received"] = int(match.group(1))
                    result["packet_loss"] = (
                        (count - result["packets_received"]) / count
                    ) * 100

                # Parse RTT: "Minimum = 1ms, Maximum = 2ms, Average = 1ms"
                min_match = re.search(r"Minimum = (\d+)ms", output)
                max_match = re.search(r"Maximum = (\d+)ms", output)
                avg_match = re.search(r"Average = (\d+)ms", output)

                if min_match:
                    result["rtt_min"] = float(min_match.group(1))
                if max_match:
                    result["rtt_max"] = float(max_match.group(1))
                if avg_match:
                    result["rtt_avg"] = float(avg_match.group(1))
            else:
                # Unix format: "4 packets transmitted, 4 received, 0% packet loss"
                match = re.search(r"(\d+) received", output)
                if match:
                    result["packets_received"] = int(match.group(1))
                    result["packet_loss"] = (
                        (count - result["packets_received"]) / count
                    ) * 100

                # Parse RTT: "rtt min/avg/max/mdev = 1.234/2.345/3.456/0.123 ms"
                rtt_match = re.search(
                    r"rtt min/avg/max[/\w]* = ([\d.]+)/([\d.]+)/([\d.]+)", output
                )
                if rtt_match:
                    result["rtt_min"] = float(rtt_match.group(1))
                    result["rtt_avg"] = float(rtt_match.group(2))
                    result["rtt_max"] = float(rtt_match.group(3))
        else:
            result["error"] = f"Ping failed with return code {process.returncode}"

        return result

    except asyncio.TimeoutError:
        return {
            "host": host,
            "reachable": False,
            "error": f"Ping timeout after {timeout + 5} seconds",
        }
    except Exception as e:
        logger.error(f"Ping exception for {host}: {e}", exc_info=True)
        return {
            "host": host,
            "reachable": False,
            "error": f"{type(e).__name__}: {str(e)}",
        }


def format_ping_result(result: Dict) -> str:
    """Format a single ping result for display"""
    output = []

    if result["reachable"]:
        output.append(f"✓ {result['host']}: REACHABLE")
        if result.get("packets_received") is not None:
            output.append(
                f"  Packets: {result['packets_received']}/{result['packets_sent']} received ({result['packet_loss']:.1f}% loss)"
            )
        if result.get("rtt_avg") is not None:
            output.append(
                f"  RTT: min={result['rtt_min']:.2f}ms avg={result['rtt_avg']:.2f}ms max={result['rtt_max']:.2f}ms"
            )
    else:
        output.append(f"✗ {result['host']}: UNREACHABLE")
        if "error" in result:
            output.append(f"  Error: {result['error']}")

    return "\n".join(output)


def format_inventory_error(item_type: str, requested_name: str, inventory: dict, discovery_tool: str) -> str:
    """
    Format a helpful error message when a host/group is not found.
    Shows first 10 available options + count of remaining, suggests discovery tool.
    """
    if item_type == "host":
        available = sorted(inventory["hosts"].keys())
        container_name = "hosts"
    elif item_type == "group":
        available = sorted(inventory["groups"].keys())
        container_name = "groups"
    else:
        return f"Error: {item_type} '{requested_name}' not found in inventory"

    error_msg = f"Error: {item_type.capitalize()} '{requested_name}' not found in inventory.\n\n"
    error_msg += f"Available {container_name} ({len(available)} total):\n"

    # Show first 10, then "and X more"
    for item in available[:10]:
        error_msg += f"  • {item}\n"

    if len(available) > 10:
        error_msg += f"  • ... and {len(available) - 10} more\n"

    error_msg += f"\nRun '{discovery_tool}' to see all available {container_name}."
    return error_msg


# FastMCP Tools

@mcp.tool()
def list_groups() -> str:
    """List all available Ansible groups for pinging (call this first to discover valid group names)"""
    inventory = _load_inventory()

    output = "=== AVAILABLE ANSIBLE GROUPS ===\n\n"

    if not inventory["groups"]:
        output += "No groups found in inventory\n"
    else:
        for group_name, hosts in sorted(inventory["groups"].items()):
            output += f"• {group_name} ({len(hosts)} hosts)\n"

    return output


@mcp.tool()
def list_hosts() -> str:
    """List all hosts in the Ansible inventory with their resolved IPs (call this first to discover valid hostnames)"""
    inventory = _load_inventory()

    output = "=== ALL HOSTS IN INVENTORY ===\n\n"

    if not inventory["hosts"]:
        output += "No hosts found in inventory\n"
    else:
        for hostname in sorted(inventory["hosts"].keys()):
            host_data = inventory["hosts"][hostname]
            target = get_host_ip(hostname, host_data)
            groups = ", ".join(host_data.get("groups", [])[:3])
            if len(host_data.get("groups", [])) > 3:
                groups += ", ..."
            output += f"• {hostname}\n"
            output += f"  Target: {target}\n"
            if groups:
                output += f"  Groups: {groups}\n"
            output += "\n"

    output += f"Total: {len(inventory['hosts'])} hosts\n"
    return output


@mcp.tool()
def reload_inventory() -> str:
    """Reload Ansible inventory from disk (useful after inventory changes)"""
    global _inventory_cache
    _inventory_cache = None
    inventory = _load_inventory()

    output = "=== INVENTORY RELOADED ===\n\n"
    output += f"✓ Loaded {len(inventory['hosts'])} hosts\n"
    output += f"✓ Loaded {len(inventory['groups'])} groups\n"

    return output


@mcp.tool()
async def ping_host_by_name(hostname: str, count: int = 4, timeout: int = 5) -> str:
    """
    Ping a specific host by hostname from Ansible inventory

    Args:
        hostname: Hostname from Ansible inventory (e.g., 'server1.example.com')
        count: Number of ping packets to send (default: 4)
        timeout: Timeout in seconds per ping (default: 5)

    Returns:
        Formatted ping results with statistics
    """
    inventory = _load_inventory()

    if hostname not in inventory["hosts"]:
        return format_inventory_error("host", hostname, inventory, "list_hosts")

    host_data = inventory["hosts"][hostname]
    target = get_host_ip(hostname, host_data)

    output = f"=== PINGING {hostname} ===\n"
    output += f"Target: {target}\n"
    output += f"Packets: {count}, Timeout: {timeout}s\n\n"

    result = await ping_host(target, count, timeout)
    output += format_ping_result(result)

    return output


@mcp.tool()
async def ping_group(group: str, count: int = 2, timeout: int = 3) -> str:
    """
    Ping all hosts in an Ansible group

    Args:
        group: Ansible group name from your inventory
        count: Number of ping packets to send (default: 2)
        timeout: Timeout in seconds per ping (default: 3)

    Returns:
        Formatted ping results for all hosts in the group
    """
    inventory = _load_inventory()

    if group not in inventory["groups"]:
        return format_inventory_error("group", group, inventory, "list_groups")

    hostnames = inventory["groups"][group]

    output = f"=== PINGING GROUP: {group} ===\n"
    output += f"Hosts: {len(hostnames)}, Packets: {count}, Timeout: {timeout}s\n\n"

    # Ping all hosts concurrently
    tasks = []
    for hostname in hostnames:
        if hostname in inventory["hosts"]:
            host_data = inventory["hosts"][hostname]
            target = get_host_ip(hostname, host_data)
            tasks.append(ping_host(target, count, timeout))

    results = await asyncio.gather(*tasks)

    # Sort by reachability (reachable first)
    results.sort(key=lambda r: (not r["reachable"], r["host"]))

    for result in results:
        output += format_ping_result(result) + "\n"

    # Summary
    reachable = sum(1 for r in results if r["reachable"])
    output += f"\n--- SUMMARY ---\n"
    output += f"Reachable: {reachable}/{len(results)}\n"

    return output


@mcp.tool()
async def ping_all(count: int = 2, timeout: int = 3) -> str:
    """
    Ping all hosts in the infrastructure

    Args:
        count: Number of ping packets to send (default: 2)
        timeout: Timeout in seconds per ping (default: 3)

    Returns:
        Formatted ping results for all hosts
    """
    inventory = _load_inventory()
    hostnames = list(inventory["hosts"].keys())

    output = f"=== PINGING ALL HOSTS ===\n"
    output += f"Total: {len(hostnames)} hosts, Packets: {count}, Timeout: {timeout}s\n\n"

    if not hostnames:
        output += "No hosts found in inventory\n"
        return output

    # Ping all hosts concurrently
    tasks = []
    for hostname in hostnames:
        host_data = inventory["hosts"][hostname]
        target = get_host_ip(hostname, host_data)
        tasks.append(ping_host(target, count, timeout))

    results = await asyncio.gather(*tasks)

    # Sort by reachability (reachable first)
    results.sort(key=lambda r: (not r["reachable"], r["host"]))

    for result in results:
        output += format_ping_result(result) + "\n"

    # Summary
    reachable = sum(1 for r in results if r["reachable"])
    output += f"\n--- SUMMARY ---\n"
    if len(results) > 0:
        output += f"Reachable: {reachable}/{len(results)} ({(reachable/len(results)*100):.1f}%)\n"
    else:
        output += "No results to summarize\n"

    return output


# Entry point
if __name__ == "__main__":
    # Load inventory on startup
    inventory = _load_inventory()
    logger.info(f"Ping MCP Server starting with {len(inventory['hosts'])} hosts")

    # Run with stdio transport by default (backward compatible)
    mcp.run()

    # Alternative transports (comment/uncomment as needed):
    # mcp.run(transport="http", host="0.0.0.0", port=8000)
    # mcp.run(transport="sse", host="0.0.0.0", port=8000)
