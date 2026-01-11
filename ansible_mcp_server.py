#!/usr/bin/env python3
"""
Ansible Inventory MCP Server v2.0 (FastMCP)
Provides read-only access to Ansible inventory information via MCP protocol

Features:
- Query all hosts and groups
- Search hosts by pattern or variable
- Get detailed host and group information
- Inventory summary and statistics
- Supports stdio, HTTP, and SSE transports
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional

import yaml

from fastmcp import FastMCP

from mcp_config_loader import load_env_file, COMMON_ALLOWED_ENV_VARS

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("Ansible Inventory")

# Load .env with security hardening
SCRIPT_DIR = Path(__file__).parent
ENV_FILE = SCRIPT_DIR / ".env"

# Ansible server only needs the common allowed variables
# Only load env file at module level if not in unified mode
if not os.getenv("MCP_UNIFIED_MODE"):
    load_env_file(ENV_FILE, allowed_vars=COMMON_ALLOWED_ENV_VARS, strict=True)

# Default inventory path - can be overridden via environment variable
DEFAULT_INVENTORY_PATH = os.getenv("ANSIBLE_INVENTORY_PATH", "ansible_hosts.yml")
INVENTORY_PATH = Path(DEFAULT_INVENTORY_PATH)

# Global inventory cache
_inventory_cache: Optional[dict] = None


def _load_inventory() -> dict:
    """Load and parse the Ansible inventory file"""
    global _inventory_cache

    if _inventory_cache is not None:
        return _inventory_cache

    if not INVENTORY_PATH.exists():
        logger.error(f"Inventory file not found: {INVENTORY_PATH}")
        return {}

    with open(INVENTORY_PATH, "r") as f:
        _inventory_cache = yaml.safe_load(f)

    logger.info(f"Loaded Ansible inventory from {INVENTORY_PATH}")
    return _inventory_cache


def _extract_hosts(data: dict, path: str = "") -> dict:
    """Recursively extract hosts from inventory structure"""
    hosts = {}

    if isinstance(data, dict):
        if "hosts" in data:
            for hostname, host_vars in data["hosts"].items():
                if hostname not in hosts:
                    hosts[hostname] = {"vars": host_vars or {}, "groups": []}
                if path:
                    hosts[hostname]["groups"].append(path)

        if "children" in data:
            for child_name, child_data in data["children"].items():
                new_path = f"{path}/{child_name}" if path else child_name
                child_hosts = _extract_hosts(child_data, new_path)
                # Merge hosts
                for hostname, host_info in child_hosts.items():
                    if hostname not in hosts:
                        hosts[hostname] = host_info
                    else:
                        hosts[hostname]["groups"].extend(host_info["groups"])

        for key, value in data.items():
            if key not in ["hosts", "children", "vars"]:
                new_path = f"{path}/{key}" if path else key
                child_hosts = _extract_hosts(value, new_path)
                for hostname, host_info in child_hosts.items():
                    if hostname not in hosts:
                        hosts[hostname] = host_info
                    else:
                        hosts[hostname]["groups"].extend(host_info["groups"])

    return hosts


def _extract_groups(data: dict, path: str = "") -> list:
    """Recursively extract groups from inventory structure"""
    groups = []

    if isinstance(data, dict):
        if "children" in data:
            for child_name in data["children"].keys():
                full_path = f"{path}/{child_name}" if path else child_name
                groups.append(full_path)
                groups.extend(_extract_groups(data["children"][child_name], full_path))

        for key, value in data.items():
            if key not in ["hosts", "children", "vars"] and isinstance(value, dict):
                full_path = f"{path}/{key}" if path else key
                groups.append(full_path)
                groups.extend(_extract_groups(value, full_path))

    return groups


def _find_group(data: dict, target: str, path: str = "") -> Optional[dict]:
    """Recursively find a group in the inventory"""
    if isinstance(data, dict):
        if "children" in data and target in data["children"]:
            return data["children"][target]

        for key, value in data.items():
            if key == target:
                return value
            if isinstance(value, dict):
                result = _find_group(value, target, f"{path}/{key}" if path else key)
                if result:
                    return result
    return None


# FastMCP Tools

@mcp.tool()
def list_all_hosts() -> str:
    """Get a list of all hosts in the Ansible inventory with their basic information"""
    inventory = _load_inventory()
    hosts = _extract_hosts(inventory.get("all", {}))

    result = {"total_hosts": len(hosts), "hosts": hosts}
    return json.dumps(result, indent=2)


@mcp.tool()
def list_groups() -> str:
    """Get a list of all groups defined in the Ansible inventory"""
    inventory = _load_inventory()
    groups = _extract_groups(inventory.get("all", {}))

    result = {"total_groups": len(groups), "groups": sorted(groups)}
    return json.dumps(result, indent=2)


@mcp.tool()
def get_host_details(hostname: str) -> str:
    """
    Get detailed information about a specific host including all variables and group memberships

    Args:
        hostname: The hostname to query
    """
    inventory = _load_inventory()
    all_hosts = _extract_hosts(inventory.get("all", {}))

    if hostname not in all_hosts:
        return json.dumps({"error": f"Host '{hostname}' not found in inventory"}, indent=2)

    result = {"hostname": hostname, "details": all_hosts[hostname]}
    return json.dumps(result, indent=2)




@mcp.tool()
def get_group_hosts(group_name: str) -> str:
    """
    Get all hosts that belong to a specific group

    Args:
        group_name: The group name to query
    """
    inventory = _load_inventory()
    group_data = _find_group(inventory.get("all", {}), group_name)

    if group_data is None:
        return json.dumps({"error": f"Group '{group_name}' not found in inventory"}, indent=2)

    hosts = group_data.get("hosts", {})

    result = {
        "group_name": group_name,
        "total_hosts": len(hosts),
        "hosts": list(hosts.keys()),
    }
    return json.dumps(result, indent=2)


@mcp.tool()
def query_hosts(pattern: str = "", variable: str = "", value: str = "") -> str:
    """
    Search for hosts by name pattern or by variable values

    Args:
        pattern: Pattern to match against hostnames (supports wildcards)
        variable: Variable name to search for
        value: Variable value to match (used with variable parameter)
    """
    inventory = _load_inventory()
    all_hosts = _extract_hosts(inventory.get("all", {}))
    matching_hosts = []

    for hostname, host_data in all_hosts.items():
        match = True

        # Check hostname pattern
        if pattern:
            import fnmatch
            if not fnmatch.fnmatch(hostname, pattern):
                match = False

        # Check variable match
        if variable and match:
            if variable not in host_data["vars"]:
                match = False
            elif value and str(host_data["vars"][variable]) != value:
                match = False

        if match:
            matching_hosts.append({
                "hostname": hostname,
                "vars": host_data["vars"],
                "groups": host_data["groups"],
            })

    result = {"total_matches": len(matching_hosts), "hosts": matching_hosts}
    return json.dumps(result, indent=2)




@mcp.tool()
def reload_inventory() -> str:
    """Reload the inventory file from disk (useful if it has been updated)"""
    global _inventory_cache
    _inventory_cache = None
    _load_inventory()

    result = {
        "status": "success",
        "message": "Inventory reloaded successfully",
        "path": str(INVENTORY_PATH),
    }
    return json.dumps(result, indent=2)


# Entry point
if __name__ == "__main__":
    # Load inventory on startup
    inventory = _load_inventory()
    logger.info(f"Ansible Inventory MCP Server starting with {len(_extract_hosts(inventory.get('all', {})))} hosts")

    # Run with stdio transport by default (backward compatible)
    mcp.run()

    # Alternative transports (comment/uncomment as needed):
    # mcp.run(transport="http", host="0.0.0.0", port=8000)
    # mcp.run(transport="sse", host="0.0.0.0", port=8000)
