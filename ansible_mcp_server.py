#!/usr/bin/env python3
"""
Ansible Inventory MCP Server v2.0 (FastMCP)
Provides read-only access to Ansible inventory information via MCP protocol

Features:
- Query all hosts and groups
- Search hosts by pattern or variable
- Get detailed host and group information
- Inventory summary and statistics
- Dynamic enum generation for tool parameters
- Supports stdio, HTTP, and SSE transports
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional, List

import yaml

from fastmcp import FastMCP
from mcp import types

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

# Global Ansible config manager for enum generation (lazy-loaded)
_ansible_config_manager = None


def _get_ansible_config_manager():
    """
    Lazy-load AnsibleConfigManager for enum generation.

    Returns None if Ansible is not available or inventory path is not set.
    """
    global _ansible_config_manager

    if _ansible_config_manager is not None:
        return _ansible_config_manager

    # Only attempt if inventory path is configured
    if not INVENTORY_PATH or not Path(INVENTORY_PATH).exists():
        logger.debug("Ansible inventory not found, enum generation will be disabled")
        return None

    try:
        # Lazy import to avoid conflicts with FastMCP
        from ansible_config_manager import AnsibleConfigManager

        _ansible_config_manager = AnsibleConfigManager(
            inventory_path=str(INVENTORY_PATH),
            logger_obj=logger
        )

        if _ansible_config_manager.is_available():
            logger.info("AnsibleConfigManager loaded successfully for enum generation")
            return _ansible_config_manager
        else:
            logger.warning("AnsibleConfigManager not available, enum generation disabled")
            _ansible_config_manager = None
            return None

    except Exception as e:
        logger.warning(f"Failed to load AnsibleConfigManager: {e}")
        _ansible_config_manager = None
        return None


def _get_dynamic_enums() -> dict:
    """
    Generate dynamic enums from Ansible inventory.

    Returns dict with:
    - hostnames: List of all hostnames
    - groups: List of all group names
    """
    config_manager = _get_ansible_config_manager()

    if not config_manager:
        return {"hostnames": [], "groups": []}

    try:
        # Get all hostnames from inventory
        inventory_data = config_manager.get_all_hosts_with_inheritance()
        hostnames = sorted(list(inventory_data.get("hosts", {}).keys()))

        # Get all group names
        groups = config_manager.get_all_groups()

        logger.info(f"Generated enums: {len(hostnames)} hostnames, {len(groups)} groups")
        return {
            "hostnames": hostnames,
            "groups": groups
        }

    except Exception as e:
        logger.error(f"Error generating dynamic enums: {e}")
        return {"hostnames": [], "groups": []}


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

@mcp.tool(
    title="List All Hosts",
    annotations=types.ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
)
def list_all_hosts() -> str:
    """Get a list of all hosts in the Ansible inventory with their basic information"""
    inventory = _load_inventory()
    hosts = _extract_hosts(inventory.get("all", {}))

    result = {"total_hosts": len(hosts), "hosts": hosts}
    return json.dumps(result, indent=2)


@mcp.tool(
    title="List Groups",
    annotations=types.ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
)
def list_groups() -> str:
    """Get a list of all groups defined in the Ansible inventory"""
    inventory = _load_inventory()
    groups = _extract_groups(inventory.get("all", {}))

    result = {"total_groups": len(groups), "groups": sorted(groups)}
    return json.dumps(result, indent=2)


@mcp.tool(
    title="Get Host Details",
    annotations=types.ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
)
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




@mcp.tool(
    title="Get Group Hosts",
    annotations=types.ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
)
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


@mcp.tool(
    title="Query Hosts",
    annotations=types.ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    )
)
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
    """Reload the inventory file from disk (useful if it has been updated)"""
    global _inventory_cache, _ansible_config_manager
    _inventory_cache = None
    _ansible_config_manager = None  # Force reload of config manager too
    _load_inventory()

    result = {
        "status": "success",
        "message": "Inventory reloaded successfully",
        "path": str(INVENTORY_PATH),
    }
    return json.dumps(result, indent=2)


# Override list_tools handler to inject dynamic enums
@mcp.list_tools()
async def list_tools_with_enums() -> List[types.Tool]:
    """
    Custom list_tools handler that injects dynamic enums into tool schemas.

    This allows Claude Desktop to show dropdown menus with actual hostnames
    and groups from the Ansible inventory instead of requiring manual typing.
    """
    # Get dynamic enums from inventory
    enums = _get_dynamic_enums()
    hostnames = enums["hostnames"]
    groups = enums["groups"]

    # Build tool list with dynamic enums injected
    tools = [
        types.Tool(
            name="list_all_hosts",
            description="Get a list of all hosts in the Ansible inventory with their basic information",
            inputSchema={"type": "object", "properties": {}, "required": []},
            title="List All Hosts",
            annotations=types.ToolAnnotations(
                readOnlyHint=True,
                destructiveHint=False,
                idempotentHint=True,
                openWorldHint=True,
            ),
        ),
        types.Tool(
            name="list_groups",
            description="Get a list of all groups defined in the Ansible inventory",
            inputSchema={"type": "object", "properties": {}, "required": []},
            title="List Groups",
            annotations=types.ToolAnnotations(
                readOnlyHint=True,
                destructiveHint=False,
                idempotentHint=True,
                openWorldHint=True,
            ),
        ),
        types.Tool(
            name="get_host_details",
            description="Get detailed information about a specific host including all variables and group memberships",
            inputSchema={
                "type": "object",
                "properties": {
                    "hostname": {
                        "type": "string",
                        "description": "The hostname to query",
                        **({"enum": hostnames} if hostnames else {}),
                    }
                },
                "required": ["hostname"],
            },
            title="Get Host Details",
            annotations=types.ToolAnnotations(
                readOnlyHint=True,
                destructiveHint=False,
                idempotentHint=True,
                openWorldHint=True,
            ),
        ),
        types.Tool(
            name="get_group_hosts",
            description="Get all hosts that belong to a specific group",
            inputSchema={
                "type": "object",
                "properties": {
                    "group_name": {
                        "type": "string",
                        "description": "The group name to query",
                        **({"enum": groups} if groups else {}),
                    }
                },
                "required": ["group_name"],
            },
            title="Get Group Hosts",
            annotations=types.ToolAnnotations(
                readOnlyHint=True,
                destructiveHint=False,
                idempotentHint=True,
                openWorldHint=True,
            ),
        ),
        types.Tool(
            name="query_hosts",
            description="Search for hosts by name pattern or by variable values",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Pattern to match against hostnames (supports wildcards)",
                    },
                    "variable": {
                        "type": "string",
                        "description": "Variable name to search for",
                    },
                    "value": {
                        "type": "string",
                        "description": "Variable value to match (used with variable parameter)",
                    },
                },
                "required": [],
            },
            title="Query Hosts",
            annotations=types.ToolAnnotations(
                readOnlyHint=True,
                destructiveHint=False,
                idempotentHint=False,
                openWorldHint=True,
            ),
        ),
        types.Tool(
            name="reload_inventory",
            description="Reload the inventory file from disk (useful if it has been updated)",
            inputSchema={"type": "object", "properties": {}, "required": []},
            title="Reload Inventory",
            annotations=types.ToolAnnotations(
                readOnlyHint=True,
                destructiveHint=False,
                idempotentHint=False,
                openWorldHint=True,
            ),
        ),
    ]

    logger.debug(f"Generated {len(tools)} tools with dynamic enums (hostnames: {len(hostnames)}, groups: {len(groups)})")
    return tools


# Entry point
if __name__ == "__main__":
    # Load inventory on startup
    inventory = _load_inventory()
    logger.info(f"Ansible Inventory MCP Server starting with {len(_extract_hosts(inventory.get('all', {})))} hosts")

    # Pre-load config manager for enum generation (in standalone mode)
    if not os.getenv("MCP_UNIFIED_MODE"):
        config_manager = _get_ansible_config_manager()
        if config_manager:
            enums = _get_dynamic_enums()
            logger.info(f"Enum generation ready: {len(enums['hostnames'])} hosts, {len(enums['groups'])} groups")

    # Run with stdio transport by default (backward compatible)
    mcp.run()

    # Alternative transports (comment/uncomment as needed):
    # mcp.run(transport="http", host="0.0.0.0", port=8000)
    # mcp.run(transport="sse", host="0.0.0.0", port=8000)
