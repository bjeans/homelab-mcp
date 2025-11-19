#!/usr/bin/env python3
"""
Ansible Inventory MCP Server
Provides read-only access to Ansible inventory information via MCP protocol
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Optional

import mcp.types as types
import yaml
from mcp.server import Server
from mcp.server.stdio import stdio_server

from mcp_config_loader import load_env_file, COMMON_ALLOWED_ENV_VARS

# Load .env with security hardening
SCRIPT_DIR = Path(__file__).parent
ENV_FILE = SCRIPT_DIR / ".env"

# Ansible server only needs the common allowed variables
load_env_file(ENV_FILE, allowed_vars=COMMON_ALLOWED_ENV_VARS, strict=True)

# Default inventory path - can be overridden via environment variable
DEFAULT_INVENTORY_PATH = os.getenv("ANSIBLE_INVENTORY_PATH", "ansible_hosts.yml")


class AnsibleInventoryMCP:
    """MCP Server for querying Ansible inventory"""

    def __init__(self, inventory_path: str = DEFAULT_INVENTORY_PATH):
        self.inventory_path = Path(inventory_path)
        self.inventory_data: Optional[dict] = None
        self.server = Server("ansible-inventory")
        self._setup_handlers()

    def _load_inventory(self) -> dict:
        """Load and parse the Ansible inventory file"""
        if not self.inventory_path.exists():
            raise FileNotFoundError(f"Inventory file not found: {self.inventory_path}")

        with open(self.inventory_path, "r") as f:
            return yaml.safe_load(f)

    def _get_inventory(self) -> dict:
        """Get cached inventory or load it"""
        if self.inventory_data is None:
            self.inventory_data = self._load_inventory()
        return self.inventory_data

    def _setup_handlers(self):
        """Setup MCP request handlers"""

        @self.server.list_tools()
        async def list_tools() -> list[types.Tool]:
            """List available Ansible inventory tools"""
            return [
                types.Tool(
                    name="get_all_hosts",
                    description="Get a list of all hosts in the Ansible inventory with their basic information",
                    inputSchema={"type": "object", "properties": {}, "required": []},
                    title="Get All Hosts",
                    annotations=types.ToolAnnotations(
                        readOnlyHint=True,
                        destructiveHint=False,
                        idempotentHint=True,
                        openWorldHint=True,
                    )
                ),
                types.Tool(
                    name="get_all_groups",
                    description="Get a list of all groups defined in the Ansible inventory",
                    inputSchema={"type": "object", "properties": {}, "required": []},
                    title="Get All Groups",
                    annotations=types.ToolAnnotations(
                        readOnlyHint=True,
                        destructiveHint=False,
                        idempotentHint=True,
                        openWorldHint=True,
                    )
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
                    )
                ),
                types.Tool(
                    name="get_group_details",
                    description="Get detailed information about a specific group including all hosts and variables",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "group_name": {
                                "type": "string",
                                "description": "The group name to query",
                            }
                        },
                        "required": ["group_name"],
                    },
                    title="Get Group Details",
                    annotations=types.ToolAnnotations(
                        readOnlyHint=True,
                        destructiveHint=False,
                        idempotentHint=True,
                        openWorldHint=True,
                    )
                ),
                types.Tool(
                    name="get_hosts_by_group",
                    description="Get all hosts that belong to a specific group",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "group_name": {
                                "type": "string",
                                "description": "The group name to query",
                            }
                        },
                        "required": ["group_name"],
                    },
                    title="Get Hosts by Group",
                    annotations=types.ToolAnnotations(
                        readOnlyHint=True,
                        destructiveHint=False,
                        idempotentHint=True,
                        openWorldHint=True,
                    )
                ),
                types.Tool(
                    name="search_hosts",
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
                    title="Search Hosts",
                    annotations=types.ToolAnnotations(
                        readOnlyHint=True,
                        destructiveHint=False,
                        idempotentHint=True,
                        openWorldHint=True,
                    )
                ),
                types.Tool(
                    name="get_inventory_summary",
                    description="Get a high-level summary of the inventory including counts and structure",
                    inputSchema={"type": "object", "properties": {}, "required": []},
                    title="Get Inventory Summary",
                    annotations=types.ToolAnnotations(
                        readOnlyHint=True,
                        destructiveHint=False,
                        idempotentHint=True,
                        openWorldHint=True,
                    )
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
                    )
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[types.TextContent]:
            """Handle tool calls"""
            try:
                if name == "get_all_hosts":
                    result = self._get_all_hosts()
                elif name == "get_all_groups":
                    result = self._get_all_groups()
                elif name == "get_host_details":
                    result = self._get_host_details(arguments["hostname"])
                elif name == "get_group_details":
                    result = self._get_group_details(arguments["group_name"])
                elif name == "get_hosts_by_group":
                    result = self._get_hosts_by_group(arguments["group_name"])
                elif name == "search_hosts":
                    result = self._search_hosts(
                        arguments.get("pattern"),
                        arguments.get("variable"),
                        arguments.get("value"),
                    )
                elif name == "get_inventory_summary":
                    result = self._get_inventory_summary()
                elif name == "reload_inventory":
                    result = self._reload_inventory()
                else:
                    raise ValueError(f"Unknown tool: {name}")

                return [
                    types.TextContent(type="text", text=json.dumps(result, indent=2))
                ]
            except Exception as e:
                return [
                    types.TextContent(
                        type="text", text=json.dumps({"error": str(e)}, indent=2)
                    )
                ]

    def _get_all_hosts(self) -> dict:
        """Get all hosts in the inventory"""
        inventory = self._get_inventory()
        hosts = {}

        def extract_hosts(data: dict, path: str = ""):
            """Recursively extract hosts from inventory structure"""
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
                        extract_hosts(child_data, new_path)

                for key, value in data.items():
                    if key not in ["hosts", "children", "vars"]:
                        new_path = f"{path}/{key}" if path else key
                        extract_hosts(value, new_path)

        extract_hosts(inventory.get("all", {}))

        return {"total_hosts": len(hosts), "hosts": hosts}

    def _get_all_groups(self) -> dict:
        """Get all groups in the inventory"""
        inventory = self._get_inventory()
        groups = []

        def extract_groups(data: dict, path: str = ""):
            """Recursively extract groups from inventory structure"""
            if isinstance(data, dict):
                if "children" in data:
                    for child_name in data["children"].keys():
                        full_path = f"{path}/{child_name}" if path else child_name
                        groups.append(full_path)
                        extract_groups(data["children"][child_name], full_path)

                for key, value in data.items():
                    if key not in ["hosts", "children", "vars"] and isinstance(
                        value, dict
                    ):
                        full_path = f"{path}/{key}" if path else key
                        groups.append(full_path)
                        extract_groups(value, full_path)

        extract_groups(inventory.get("all", {}))

        return {"total_groups": len(groups), "groups": sorted(groups)}

    def _get_host_details(self, hostname: str) -> dict:
        """Get detailed information about a specific host"""
        all_hosts = self._get_all_hosts()

        if hostname not in all_hosts["hosts"]:
            raise ValueError(f"Host '{hostname}' not found in inventory")

        return {"hostname": hostname, "details": all_hosts["hosts"][hostname]}

    def _get_group_details(self, group_name: str) -> dict:
        """Get detailed information about a specific group"""
        inventory = self._get_inventory()

        def find_group(data: dict, target: str, path: str = "") -> Optional[dict]:
            """Recursively find a group in the inventory"""
            if isinstance(data, dict):
                if "children" in data and target in data["children"]:
                    return data["children"][target]

                for key, value in data.items():
                    if key == target:
                        return value
                    if isinstance(value, dict):
                        result = find_group(
                            value, target, f"{path}/{key}" if path else key
                        )
                        if result:
                            return result
            return None

        group_data = find_group(inventory.get("all", {}), group_name)

        if group_data is None:
            raise ValueError(f"Group '{group_name}' not found in inventory")

        return {"group_name": group_name, "details": group_data}

    def _get_hosts_by_group(self, group_name: str) -> dict:
        """Get all hosts in a specific group"""
        group_details = self._get_group_details(group_name)
        hosts = group_details["details"].get("hosts", {})

        return {
            "group_name": group_name,
            "total_hosts": len(hosts),
            "hosts": list(hosts.keys()),
        }

    def _search_hosts(
        self,
        pattern: Optional[str] = None,
        variable: Optional[str] = None,
        value: Optional[str] = None,
    ) -> dict:
        """Search for hosts by pattern or variable"""
        all_hosts = self._get_all_hosts()["hosts"]
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
                matching_hosts.append(
                    {
                        "hostname": hostname,
                        "vars": host_data["vars"],
                        "groups": host_data["groups"],
                    }
                )

        return {"total_matches": len(matching_hosts), "hosts": matching_hosts}

    def _get_inventory_summary(self) -> dict:
        """Get a high-level summary of the inventory"""
        all_hosts = self._get_all_hosts()
        all_groups = self._get_all_groups()

        # Analyze host distribution by OS
        os_distribution = {}
        for hostname, host_data in all_hosts["hosts"].items():
            os_type = host_data["vars"].get("ansible_distribution", "Unknown")
            os_distribution[os_type] = os_distribution.get(os_type, 0) + 1

        return {
            "total_hosts": all_hosts["total_hosts"],
            "total_groups": all_groups["total_groups"],
            "os_distribution": os_distribution,
            "inventory_path": str(self.inventory_path),
            "groups": all_groups["groups"][:10],  # First 10 groups
        }

    def _reload_inventory(self) -> dict:
        """Reload the inventory from disk"""
        self.inventory_data = None
        self._get_inventory()
        return {
            "status": "success",
            "message": "Inventory reloaded successfully",
            "path": str(self.inventory_path),
        }


async def main():
    """Main entry point for the MCP server"""
    import os

    # Allow override via environment variable
    inventory_path = os.getenv("ANSIBLE_INVENTORY_PATH", DEFAULT_INVENTORY_PATH)

    mcp = AnsibleInventoryMCP(inventory_path)

    async with stdio_server() as (read_stream, write_stream):
        await mcp.server.run(
            read_stream, write_stream, mcp.server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
