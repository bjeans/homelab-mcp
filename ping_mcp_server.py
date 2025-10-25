#!/usr/bin/env python3
"""
Ping MCP Server v1.0
Provides network connectivity testing via ICMP ping across homelab infrastructure
Reads host configuration from Ansible inventory with fallback to .env

Features:
- Ping individual hosts by name
- Ping entire Ansible groups
- Ping all hosts
- Custom timeout and packet count
- Cross-platform support (Windows/Linux/macOS)
"""

import asyncio
import json
import logging
import os
import platform
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Union

import yaml

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from mcp_config_loader import load_env_file, load_indexed_env_vars, COMMON_ALLOWED_ENV_VARS

server = Server("ping-info")

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
INVENTORY_DATA = None


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


def load_ansible_inventory(inventory=None):
    """
    Load and cache the Ansible inventory with full variable inheritance.
    Falls back to environment variables if Ansible inventory not found.
    Returns dict with hosts and groups.

    Properly merges variables from:
    1. Group vars (from parent to child)
    2. Host vars (override group vars)
    3. Environment variables (fallback)

    Args:
        inventory: Optional pre-loaded Ansible inventory dict (avoids file locking in unified mode)
    """
    global INVENTORY_DATA

    # Use cached data if available (for standalone mode)
    if INVENTORY_DATA is not None:
        return INVENTORY_DATA

    # Use pre-loaded inventory if provided
    if inventory is None:
        # Get path from environment variable
        ansible_inventory_path = os.getenv("ANSIBLE_INVENTORY_PATH", "")

        if not ansible_inventory_path or not Path(ansible_inventory_path).exists():
            logger.warning(f"Ansible inventory not found at: {ansible_inventory_path}")
            logger.info("Attempting to load ping targets from environment variables")
            INVENTORY_DATA = load_ping_targets_from_env()
            if INVENTORY_DATA and INVENTORY_DATA.get("hosts"):
                logger.info(f"Loaded {len(INVENTORY_DATA['hosts'])} ping targets from environment")
                return INVENTORY_DATA
            logger.error("No ping targets configured in Ansible inventory or environment variables")
            return {"hosts": {}, "groups": {}}

        try:
            with open(ansible_inventory_path, "r") as f:
                inventory = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading Ansible inventory: {e}", exc_info=True)
            logger.info("Attempting to load ping targets from environment variables as fallback")
            INVENTORY_DATA = load_ping_targets_from_env()
            if INVENTORY_DATA and INVENTORY_DATA.get("hosts"):
                logger.info(f"Loaded {len(INVENTORY_DATA['hosts'])} ping targets from environment variables")
                return INVENTORY_DATA
            return {"hosts": {}, "groups": {}}

    # Process the inventory (whether pre-loaded or freshly loaded)
    try:

        hosts = {}
        groups = {}
        group_vars = {}  # Store vars for each group

        def collect_group_vars(group_name, group_data, parent_groups=None):
            """First pass: collect all group vars"""
            if parent_groups is None:
                parent_groups = []

            current_groups = parent_groups + [group_name]

            # Store group vars
            if group_name not in group_vars:
                group_vars[group_name] = {}

            if "vars" in group_data:
                group_vars[group_name] = group_data["vars"].copy()

            # Recursively process children
            if "children" in group_data:
                for child_name, child_data in group_data["children"].items():
                    collect_group_vars(child_name, child_data, current_groups)

        def process_group(
            group_name, group_data, parent_groups=None, inherited_vars=None
        ):
            """Second pass: process groups with inherited vars"""
            if parent_groups is None:
                parent_groups = []
            if inherited_vars is None:
                inherited_vars = {}

            current_groups = parent_groups + [group_name]

            # Merge inherited vars with this group's vars
            merged_vars = inherited_vars.copy()
            if group_name in group_vars:
                merged_vars.update(group_vars[group_name])

            # Process hosts in this group
            if "hosts" in group_data:
                for hostname, host_vars in group_data["hosts"].items():
                    if hostname not in hosts:
                        hosts[hostname] = {"groups": [], "vars": {}}

                    # Add groups
                    hosts[hostname]["groups"].extend(current_groups)

                    # Merge vars: group vars first, then host vars override
                    hosts[hostname]["vars"].update(merged_vars)
                    if host_vars:
                        hosts[hostname]["vars"].update(host_vars)

            # Track group membership (use set to avoid duplicates)
            if group_name not in groups:
                groups[group_name] = set()

            # Add hosts to group tracking
            if "hosts" in group_data:
                groups[group_name].update(group_data["hosts"].keys())

            # Process child groups with accumulated vars
            if "children" in group_data:
                for child_name, child_data in group_data["children"].items():
                    process_group(child_name, child_data, current_groups, merged_vars)
                    # Also add child group's hosts to parent group
                    if child_name in groups:
                        groups[group_name].update(groups[child_name])

        # First pass: collect all group vars
        all_group = inventory.get("all", {})
        if "children" in all_group:
            for group_name, group_data in all_group["children"].items():
                collect_group_vars(group_name, group_data)

        # Second pass: process groups with proper var inheritance
        if "children" in all_group:
            for group_name, group_data in all_group["children"].items():
                process_group(group_name, group_data)

        # Convert group sets to lists for JSON serialization
        groups = {k: list(v) for k, v in groups.items()}

        INVENTORY_DATA = {"hosts": hosts, "groups": groups}
        logger.info(
            f"Loaded {len(hosts)} hosts and {len(groups)} groups from Ansible inventory"
        )

        return INVENTORY_DATA

    except Exception as e:
        logger.error(f"Error processing Ansible inventory: {e}", exc_info=True)
        logger.info("Attempting to load ping targets from environment variables as fallback")
        INVENTORY_DATA = load_ping_targets_from_env()
        if INVENTORY_DATA and INVENTORY_DATA.get("hosts"):
            logger.info(f"Loaded {len(INVENTORY_DATA['hosts'])} ping targets from environment variables")
            return INVENTORY_DATA
        return {"hosts": {}, "groups": {}}


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


class PingMCPServer:
    """Ping MCP Server - Class-based implementation"""

    def __init__(self, ansible_inventory=None):
        """Initialize configuration using existing config loading logic

        Args:
            ansible_inventory: Optional pre-loaded Ansible inventory dict (for unified mode)
        """
        # Load environment configuration (skip if in unified mode)
        if not os.getenv("MCP_UNIFIED_MODE"):
            load_env_file(ENV_FILE, allowed_vars=PING_ALLOWED_VARS, strict=True)

        self.ansible_inventory_path = os.getenv("ANSIBLE_INVENTORY_PATH", "")
        logger.info(f"[PingMCPServer] Ansible inventory: {self.ansible_inventory_path}")

        # Load inventory (with caching)
        self.inventory_data = None
        self.ansible_inventory = ansible_inventory  # Store pre-loaded inventory
        self._load_inventory()

    def _load_inventory(self):
        """Load Ansible inventory (internal method)"""
        # Use pre-loaded inventory if available, otherwise load it
        self.inventory_data = load_ansible_inventory(self.ansible_inventory)
        logger.info(f"[PingMCPServer] Loaded {len(self.inventory_data['hosts'])} hosts")

    async def list_tools(self) -> list[types.Tool]:
        """Return list of Tool objects this server provides (with ping_ prefix)"""
        return [
            types.Tool(
                name="ping_ping_host",
                description="Ping a specific host by hostname from Ansible inventory",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "hostname": {
                            "type": "string",
                            "description": "Hostname from Ansible inventory (e.g., 'server1.example.com', 'server2.example.com')",
                        },
                        "count": {
                            "type": "integer",
                            "description": "Number of ping packets to send (default: 4)",
                            "default": 4,
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds per ping (default: 5)",
                            "default": 5,
                        },
                    },
                    "required": ["hostname"],
                },
            ),
            types.Tool(
                name="ping_ping_group",
                description="Ping all hosts in an Ansible group",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "group": {
                            "type": "string",
                            "description": "Ansible group name (e.g., 'webservers', 'databases', 'docker_hosts')",
                        },
                        "count": {
                            "type": "integer",
                            "description": "Number of ping packets to send (default: 2)",
                            "default": 2,
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds per ping (default: 3)",
                            "default": 3,
                        },
                    },
                    "required": ["group"],
                },
            ),
            types.Tool(
                name="ping_ping_all",
                description="Ping all hosts in the infrastructure",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "count": {
                            "type": "integer",
                            "description": "Number of ping packets to send (default: 2)",
                            "default": 2,
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds per ping (default: 3)",
                            "default": 3,
                        },
                    },
                    "required": [],
                },
            ),
            types.Tool(
                name="ping_list_groups",
                description="List all available Ansible groups for pinging",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            types.Tool(
                name="ping_list_hosts",
                description="List all hosts in the Ansible inventory with their resolved IPs",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            types.Tool(
                name="ping_reload_inventory",
                description="Reload Ansible inventory from disk (useful after inventory changes)",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
        ]

    async def handle_tool(self, tool_name: str, arguments: dict | None) -> list[types.TextContent]:
        """Route tool calls to appropriate handler methods"""
        # Strip the ping_ prefix for routing
        name = tool_name.replace("ping_", "", 1) if tool_name.startswith("ping_") else tool_name

        logger.info(f"[PingMCPServer] Tool called: {tool_name} -> {name} with args: {arguments}")

        # Call the shared implementation with this instance's inventory
        return await handle_call_tool_impl(name, arguments, self.inventory_data, self._reload_inventory_impl)

    async def _reload_inventory_impl(self):
        """Reload inventory for this instance"""
        self.inventory_data = None
        self._load_inventory()
        return self.inventory_data


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available ping tools"""
    return [
        types.Tool(
            name="ping_host",
            description="Ping a specific host by hostname from Ansible inventory",
            inputSchema={
                "type": "object",
                "properties": {
                    "hostname": {
                        "type": "string",
                        "description": "Hostname from Ansible inventory (e.g., 'server1.example.com', 'server2.example.com')",
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of ping packets to send (default: 4)",
                        "default": 4,
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds per ping (default: 5)",
                        "default": 5,
                    },
                },
                "required": ["hostname"],
            },
        ),
        types.Tool(
            name="ping_group",
            description="Ping all hosts in an Ansible group",
            inputSchema={
                "type": "object",
                "properties": {
                    "group": {
                        "type": "string",
                        "description": "Ansible group name (e.g., 'webservers', 'databases', 'docker_hosts')",
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of ping packets to send (default: 2)",
                        "default": 2,
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds per ping (default: 3)",
                        "default": 3,
                    },
                },
                "required": ["group"],
            },
        ),
        types.Tool(
            name="ping_all",
            description="Ping all hosts in the infrastructure",
            inputSchema={
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "Number of ping packets to send (default: 2)",
                        "default": 2,
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds per ping (default: 3)",
                        "default": 3,
                    },
                },
                "required": [],
            },
        ),
        types.Tool(
            name="list_groups",
            description="List all available Ansible groups for pinging",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="list_hosts",
            description="List all hosts in the Ansible inventory with their resolved IPs",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="reload_inventory",
            description="Reload Ansible inventory from disk (useful after inventory changes)",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
    ]


async def handle_call_tool_impl(
    name: str, arguments: dict | None, inventory: dict, reload_inventory_func=None
) -> list[types.TextContent]:
    """Core tool execution logic that can be called by both class and module-level handlers"""
    try:

        if name == "list_groups":
            output = "=== AVAILABLE ANSIBLE GROUPS ===\n\n"

            if not inventory["groups"]:
                output += "No groups found in inventory\n"
            else:
                for group_name, hosts in sorted(inventory["groups"].items()):
                    output += f"• {group_name} ({len(hosts)} hosts)\n"

            return [types.TextContent(type="text", text=output)]

        elif name == "list_hosts":
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
            return [types.TextContent(type="text", text=output)]

        elif name == "reload_inventory":
            # Use provided reload function or reload global inventory
            if reload_inventory_func:
                inventory = await reload_inventory_func()
            else:
                global INVENTORY_DATA
                INVENTORY_DATA = None
                inventory = load_ansible_inventory()

            output = "=== INVENTORY RELOADED ===\n\n"
            output += f"✓ Loaded {len(inventory['hosts'])} hosts\n"
            output += f"✓ Loaded {len(inventory['groups'])} groups\n"

            return [types.TextContent(type="text", text=output)]

        elif name == "ping_host":
            if not arguments or "hostname" not in arguments:
                return [
                    types.TextContent(
                        type="text", text="Error: hostname parameter required"
                    )
                ]

            hostname = arguments["hostname"]
            count = arguments.get("count", 4)
            timeout = arguments.get("timeout", 5)

            if hostname not in inventory["hosts"]:
                return [
                    types.TextContent(
                        type="text",
                        text=f"Error: Host '{hostname}' not found in inventory\nUse list_groups to see available hosts",
                    )
                ]

            host_data = inventory["hosts"][hostname]
            target = get_host_ip(hostname, host_data)

            output = f"=== PINGING {hostname} ===\n"
            output += f"Target: {target}\n"
            output += f"Packets: {count}, Timeout: {timeout}s\n\n"

            result = await ping_host(target, count, timeout)
            output += format_ping_result(result)

            return [types.TextContent(type="text", text=output)]

        elif name == "ping_group":
            if not arguments or "group" not in arguments:
                return [
                    types.TextContent(
                        type="text", text="Error: group parameter required"
                    )
                ]

            group_name = arguments["group"]
            count = arguments.get("count", 2)
            timeout = arguments.get("timeout", 3)

            if group_name not in inventory["groups"]:
                return [
                    types.TextContent(
                        type="text",
                        text=f"Error: Group '{group_name}' not found in inventory\nUse list_groups to see available groups",
                    )
                ]

            hostnames = inventory["groups"][group_name]

            output = f"=== PINGING GROUP: {group_name} ===\n"
            output += (
                f"Hosts: {len(hostnames)}, Packets: {count}, Timeout: {timeout}s\n\n"
            )

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

            return [types.TextContent(type="text", text=output)]

        elif name == "ping_all":
            count = arguments.get("count", 2) if arguments else 2
            timeout = arguments.get("timeout", 3) if arguments else 3

            hostnames = list(inventory["hosts"].keys())

            output = f"=== PINGING ALL HOSTS ===\n"
            output += f"Total: {len(hostnames)} hosts, Packets: {count}, Timeout: {timeout}s\n\n"

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
            output += f"Reachable: {reachable}/{len(results)} ({(reachable/len(results)*100):.1f}%)\n"

            return [types.TextContent(type="text", text=output)]

        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        logger.error(f"Error in tool {name}: {str(e)}", exc_info=True)
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent]:
    """Handle tool calls (module-level wrapper for standalone mode)"""
    # For standalone mode, load inventory fresh each time or use cached
    inventory = load_ansible_inventory()
    return await handle_call_tool_impl(name, arguments, inventory)


async def main():
    """Main entry point"""
    # Load inventory on startup
    inventory = load_ansible_inventory()
    logger.info(f"Ping MCP Server starting with {len(inventory['hosts'])} hosts")

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="ping-info",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
