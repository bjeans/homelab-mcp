#!/usr/bin/env python3
"""
UPS Monitoring MCP Server v2.0 (FastMCP)
Provides UPS status monitoring via Network UPS Tools (NUT) protocol
Reads host configuration from Ansible inventory with fallback to .env

Features:
- Query UPS status across all NUT servers
- Check battery level, runtime remaining, load percentage
- Monitor AC power status (online/on battery/offline)
- Track UPS health metrics
- Support for multiple UPS devices per host
- Cross-platform NUT protocol support
- Supports stdio, HTTP, and SSE transports
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

from fastmcp import FastMCP
from mcp import types

from mcp_config_loader import load_env_file, COMMON_ALLOWED_ENV_VARS
from mcp_error_handler import log_error_with_context

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("UPS Monitor")

# Load .env with security hardening
SCRIPT_DIR = Path(__file__).parent
ENV_FILE = SCRIPT_DIR / ".env"

UPS_ALLOWED_VARS = COMMON_ALLOWED_ENV_VARS | {
    "NUT_*",  # Pattern for NUT-specific variables
}

# Only load env file at module level if not in unified mode
if not os.getenv("MCP_UNIFIED_MODE"):
    load_env_file(ENV_FILE, allowed_vars=UPS_ALLOWED_VARS, strict=True)

# Configuration
ANSIBLE_INVENTORY_PATH = os.getenv("ANSIBLE_INVENTORY_PATH", "")
DEFAULT_NUT_PORT = int(os.getenv("NUT_PORT", "3493"))
DEFAULT_NUT_USERNAME = os.getenv("NUT_USERNAME", "")
DEFAULT_NUT_PASSWORD = os.getenv("NUT_PASSWORD", "")

logger.info(f"Ansible inventory: {ANSIBLE_INVENTORY_PATH}")

# Global inventory cache
_inventory_cache = None

# NUT Status codes - OL = Online, OB = On Battery, LB = Low Battery, etc.
NUT_STATUS_CODES = {
    "OL": "Online",
    "OB": "On Battery",
    "LB": "Low Battery",
    "HB": "High Battery",
    "RB": "Replace Battery",
    "CHRG": "Charging",
    "DISCHRG": "Discharging",
    "BYPASS": "Bypass Mode",
    "CAL": "Calibrating",
    "OFF": "Offline",
    "OVER": "Overloaded",
    "TRIM": "Trimming Voltage",
    "BOOST": "Boosting Voltage",
    "FSD": "Forced Shutdown",
}


def _load_inventory():
    """
    Load and cache the Ansible inventory with NUT server configuration.
    Returns dict with nut_servers configuration.
    """
    global _inventory_cache

    if _inventory_cache is not None:
        return _inventory_cache

    if not ANSIBLE_INVENTORY_PATH:
        logger.error("No Ansible inventory path provided")
        return {"nut_servers": {}}

    # Lazy import - only load Ansible when needed
    from ansible_config_manager import AnsibleConfigManager

    # Use centralized config manager
    manager = AnsibleConfigManager(
        inventory_path=ANSIBLE_INVENTORY_PATH,
        logger_obj=logger
    )

    if not manager.is_available():
        logger.error(f"Ansible inventory not accessible at: {ANSIBLE_INVENTORY_PATH}")
        return {"nut_servers": {}}

    # Load NUT servers group
    nut_hosts = manager.get_group_hosts("nut_servers")
    if not nut_hosts:
        logger.warning("No hosts found in 'nut_servers' group")
        return {"nut_servers": {}}

    nut_servers = _build_nut_servers_dict(manager, nut_hosts)

    _inventory_cache = {"nut_servers": nut_servers}
    logger.info(f"Loaded {len(nut_servers)} NUT servers from Ansible inventory")
    return _inventory_cache


def _build_nut_servers_dict(manager, nut_hosts):
    """Build the NUT servers configuration dict from hosts"""
    nut_servers = {}
    for hostname, host_ip in nut_hosts.items():
        # Extract NUT-specific configuration
        nut_port_str = manager.get_host_variable(hostname, "nut_port", str(DEFAULT_NUT_PORT))
        nut_username = manager.get_host_variable(hostname, "nut_username", DEFAULT_NUT_USERNAME)
        nut_password = manager.get_host_variable(hostname, "nut_password", DEFAULT_NUT_PASSWORD)

        # Try to get UPS devices configuration
        ups_devices_raw = manager.get_host_variable(hostname, "ups_devices", "ups")

        logger.debug(f"Raw ups_devices for {hostname}: {ups_devices_raw}, type: {type(ups_devices_raw)}")

        # If ups_devices comes back as a string representation of a list, parse it
        if isinstance(ups_devices_raw, str) and ups_devices_raw.startswith('['):
            try:
                import ast
                ups_devices_raw = ast.literal_eval(ups_devices_raw)
                logger.debug(f"Parsed string to list for {hostname}")
            except (ValueError, SyntaxError) as e:
                logger.warning(f"Could not parse ups_devices string for {hostname}: {e}")

        # Normalize UPS devices to list of dicts
        if isinstance(ups_devices_raw, str):
            ups_devices = [{"name": ups_devices_raw, "description": ""}]
        elif isinstance(ups_devices_raw, list):
            normalized_devices = []
            for device in ups_devices_raw:
                if isinstance(device, str):
                    normalized_devices.append({"name": device, "description": ""})
                elif isinstance(device, dict):
                    normalized_devices.append(device)
            ups_devices = normalized_devices if normalized_devices else [{"name": "ups", "description": "UPS"}]
        else:
            ups_devices = [{"name": "ups", "description": "UPS"}]

        try:
            nut_port = int(nut_port_str)
        except (ValueError, TypeError):
            nut_port = DEFAULT_NUT_PORT

        nut_servers[hostname] = {
            "hostname": hostname,
            "host": host_ip,
            "port": nut_port,
            "username": nut_username,
            "password": nut_password,
            "ups_devices": ups_devices,
        }
        logger.info(
            f"Found NUT server: {hostname} -> {host_ip}:{nut_port} "
            f"({len(ups_devices)} UPS device(s))"
        )

    return nut_servers


async def query_nut_server(
    host: str, port: int, ups_name: str, username: str = "", password: str = ""
) -> Optional[Dict]:
    """
    Query NUT server using basic network protocol

    Args:
        host: NUT server hostname or IP
        port: NUT server port (usually 3493)
        ups_name: Name of the UPS device
        username: Optional username for authentication
        password: Optional password for authentication

    Returns:
        Dict with UPS variables or None on error
    """
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=5.0
        )

        variables = {}

        try:
            # Login if credentials provided
            if username and password:
                writer.write(f"USERNAME {username}\n".encode())
                await writer.drain()
                await reader.readline()  # Read response

                writer.write(f"PASSWORD {password}\n".encode())
                await writer.drain()
                await reader.readline()  # Read response

            # List all variables for the UPS
            writer.write(f"LIST VAR {ups_name}\n".encode())
            await writer.drain()

            # Read variables until we get "END LIST VAR"
            while True:
                line = await asyncio.wait_for(reader.readline(), timeout=5.0)
                line = line.decode('utf-8', errors='ignore').strip()

                if not line or line.startswith("END LIST VAR"):
                    break

                # Parse: VAR ups_name variable.name "value"
                if line.startswith("VAR"):
                    parts = line.split(None, 3)  # Split into max 4 parts
                    if len(parts) >= 4:
                        var_name = parts[2].strip('"')
                        var_value = parts[3].strip('"')
                        variables[var_name] = var_value

            # Logout
            writer.write(b"LOGOUT\n")
            await writer.drain()

        finally:
            writer.close()
            await writer.wait_closed()

        return {
            "variables": variables,
            "commands": [],
        }

    except asyncio.TimeoutError:
        log_error_with_context(
            logger,
            f"Timeout connecting to NUT server",
            context={"host": host, "port": port, "ups_name": ups_name, "timeout": 5}
        )
        return None
    except ConnectionRefusedError as e:
        logger.debug(f"NUT server connection refused at {host}:{port} - service may be offline")
        return None
    except OSError as e:
        log_error_with_context(
            logger,
            f"Network error connecting to NUT server",
            error=e,
            context={"host": host, "port": port, "ups_name": ups_name}
        )
        return None
    except Exception as e:
        log_error_with_context(
            logger,
            f"Error in basic NUT protocol query",
            error=e,
            context={"host": host, "port": port, "ups_name": ups_name}
        )
        return None


def parse_ups_status(status_str: str) -> List[str]:
    """
    Parse NUT status string into human-readable list

    Args:
        status_str: Space-separated status codes (e.g., "OL CHRG")

    Returns:
        List of human-readable status strings
    """
    if not status_str:
        return ["Unknown"]

    codes = status_str.split()
    statuses = []

    for code in codes:
        readable = NUT_STATUS_CODES.get(code, code)
        statuses.append(readable)

    return statuses


def format_ups_details(ups_name: str, ups_data: Optional[Dict], host_name: str) -> str:
    """
    Format UPS details for display

    Args:
        ups_name: Name of the UPS device
        ups_data: Dict of UPS variables or None
        host_name: Name of the host running NUT

    Returns:
        Formatted string for display
    """
    if not ups_data or "variables" not in ups_data:
        return f"✗ {ups_name} on {host_name}: No data available\n"

    vars = ups_data["variables"]

    # Extract key metrics
    status = vars.get("ups.status", "UNKNOWN")
    battery_charge = vars.get("battery.charge", "N/A")
    battery_runtime = vars.get("battery.runtime", "N/A")
    battery_voltage = vars.get("battery.voltage", "N/A")
    input_voltage = vars.get("input.voltage", "N/A")
    output_voltage = vars.get("output.voltage", "N/A")
    load = vars.get("ups.load", "N/A")
    model = vars.get("ups.model", "Unknown Model")
    manufacturer = vars.get("ups.mfr", "Unknown Manufacturer")

    # Parse status
    status_list = parse_ups_status(status)
    status_display = ", ".join(status_list)

    # Determine health icon
    if "OL" in status or "Online" in status_list:
        icon = "✓"
    elif "OB" in status or "On Battery" in status_list:
        icon = "⚠"
    else:
        icon = "✗"

    # Format runtime
    runtime_display = "N/A"
    if battery_runtime != "N/A":
        try:
            runtime_seconds = int(float(battery_runtime))
            runtime_minutes = runtime_seconds // 60
            runtime_display = f"{runtime_minutes} min ({runtime_seconds}s)"
        except:
            runtime_display = battery_runtime

    output = f"{icon} {ups_name} on {host_name}\n"
    output += f"  Model: {manufacturer} {model}\n"
    output += f"  Status: {status_display}\n"
    output += f"  Battery: {battery_charge}%"

    # Add runtime if available
    if runtime_display != "N/A":
        output += f" ({runtime_display} remaining)"
    output += "\n"

    output += f"  Load: {load}%\n"

    # Add voltage info if available
    if input_voltage != "N/A" or output_voltage != "N/A":
        output += f"  Voltage: IN={input_voltage}V OUT={output_voltage}V"
        if battery_voltage != "N/A":
            output += f" BAT={battery_voltage}V"
        output += "\n"

    return output


# FastMCP Tools

@mcp.tool(
    title="List UPS Devices",
    annotations=types.ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
)
def list_hosts() -> str:
    """List all UPS devices configured in the inventory"""
    inventory = _load_inventory()
    nut_servers = inventory.get("nut_servers", {})

    output = "=== CONFIGURED UPS DEVICES ===\n\n"

    if not nut_servers:
        output += "No NUT servers configured in inventory.\n"
        output += "Add a 'nut_servers' group to your ansible_hosts.yml file.\n"
    else:
        for server_name, config in sorted(nut_servers.items()):
            output += f"• {server_name} ({config['host']}:{config['port']})\n"
            for ups in config["ups_devices"]:
                ups_name = ups.get("name", "Unknown")
                ups_desc = ups.get("description", "")
                if ups_desc:
                    output += f"  - {ups_name}: {ups_desc}\n"
                else:
                    output += f"  - {ups_name}\n"
            output += "\n"

    output += f"Total: {len(nut_servers)} NUT server(s)\n"
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
    """Reload Ansible inventory from disk (useful after inventory changes)"""
    global _inventory_cache
    _inventory_cache = None
    inventory = _load_inventory()
    nut_servers = inventory.get("nut_servers", {})

    output = "=== INVENTORY RELOADED ===\n\n"
    output += f"✓ Loaded {len(nut_servers)} NUT server(s)\n"

    total_ups = sum(len(cfg["ups_devices"]) for cfg in nut_servers.values())
    output += f"✓ Loaded {total_ups} UPS device(s)\n"

    return output


@mcp.tool(
    title="Get UPS Status",
    annotations=types.ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    )
)
async def get_status() -> str:
    """Get status of all UPS devices across all NUT servers"""
    inventory = _load_inventory()
    nut_servers = inventory.get("nut_servers", {})

    if not nut_servers:
        return "No NUT servers configured. Please add 'nut_servers' group to ansible_hosts.yml"

    output = "=== UPS STATUS ===\n\n"

    # Query all UPS devices
    all_online = True
    total_devices = 0

    for server_name, config in sorted(nut_servers.items()):
        for ups in config["ups_devices"]:
            total_devices += 1
            ups_name = ups.get("name", "ups")

            ups_data = await query_nut_server(
                config["host"],
                config["port"],
                ups_name,
                config.get("username", ""),
                config.get("password", ""),
            )

            output += format_ups_details(ups_name, ups_data, server_name)
            output += "\n"

            # Check if any UPS is not online
            if ups_data and "variables" in ups_data:
                status = ups_data["variables"].get("ups.status", "")
                if "OL" not in status:
                    all_online = False

    # Summary
    output += "--- SUMMARY ---\n"
    output += f"Total UPS Devices: {total_devices}\n"
    if all_online:
        output += "Status: All systems online ✓\n"
    else:
        output += "Status: ⚠ ALERT - One or more UPS on battery or offline\n"

    return output


@mcp.tool(
    title="Get UPS Details",
    annotations=types.ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    )
)
async def get_details(host: str, ups_name: str = "") -> str:
    """
    Get detailed information for a specific UPS device

    Args:
        host: NUT server hostname from your Ansible inventory
        ups_name: UPS device name (optional, uses first device if not specified)
    """
    inventory = _load_inventory()
    nut_servers = inventory.get("nut_servers", {})

    if host not in nut_servers:
        return f"Error: Host '{host}' not found in inventory.\nAvailable hosts: {', '.join(nut_servers.keys())}"

    config = nut_servers[host]

    # Determine which UPS to query
    if ups_name:
        # Find the specific UPS
        ups_device = None
        for ups in config["ups_devices"]:
            if ups.get("name") == ups_name:
                ups_device = ups
                break

        if not ups_device:
            return f"Error: UPS '{ups_name}' not found on host '{host}'"
        target_ups_name = ups_name
    else:
        # Use first UPS
        if not config["ups_devices"]:
            return f"Error: No UPS devices configured for host '{host}'"
        ups_device = config["ups_devices"][0]
        target_ups_name = ups_device.get("name", "ups")

    output = f"=== UPS DETAILS: {target_ups_name} on {host} ===\n\n"

    ups_data = await query_nut_server(
        config["host"],
        config["port"],
        target_ups_name,
        config.get("username", ""),
        config.get("password", ""),
    )

    if not ups_data:
        output += f"✗ Unable to connect to NUT server at {config['host']}:{config['port']}\n"
        output += "Check that:\n"
        output += "  - NUT daemon (upsd) is running\n"
        output += "  - Firewall allows port 3493\n"
        output += "  - UPS device name is correct\n"
        return output

    vars = ups_data.get("variables", {})

    if not vars:
        output += "No data available from UPS\n"
        return output

    # Display all variables grouped by category
    categories = {
        "Device Info": ["device.", "ups.mfr", "ups.model", "ups.serial", "ups.firmware"],
        "Status": ["ups.status", "ups.alarm"],
        "Battery": ["battery."],
        "Input": ["input."],
        "Output": ["output."],
        "Load": ["ups.load", "ups.power", "ups.realpower"],
        "Other": [],
    }

    for category, prefixes in categories.items():
        matching_vars = {}

        for var_name, var_value in sorted(vars.items()):
            # Check if variable matches any prefix in this category
            if prefixes:
                if any(var_name.startswith(prefix) or var_name == prefix for prefix in prefixes):
                    matching_vars[var_name] = var_value

        if matching_vars:
            output += f"{category}:\n"
            for var_name, var_value in matching_vars.items():
                output += f"  {var_name}: {var_value}\n"
            output += "\n"

    # Show other variables not in categories
    categorized_vars = set()
    for prefixes in categories.values():
        for var_name in vars.keys():
            if any(var_name.startswith(prefix) or var_name == prefix for prefix in prefixes):
                categorized_vars.add(var_name)

    other_vars = {k: v for k, v in vars.items() if k not in categorized_vars}
    if other_vars:
        output += "Other Variables:\n"
        for var_name, var_value in sorted(other_vars.items()):
            output += f"  {var_name}: {var_value}\n"

    return output


@mcp.tool(
    title="Get Battery Runtime",
    annotations=types.ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    )
)
async def get_battery_info() -> str:
    """Get battery runtime estimates for all UPS devices"""
    inventory = _load_inventory()
    nut_servers = inventory.get("nut_servers", {})

    if not nut_servers:
        return "No NUT servers configured."

    output = "=== BATTERY RUNTIME ESTIMATES ===\n\n"

    for server_name, config in sorted(nut_servers.items()):
        for ups in config["ups_devices"]:
            ups_name = ups.get("name", "ups")

            ups_data = await query_nut_server(
                config["host"],
                config["port"],
                ups_name,
                config.get("username", ""),
                config.get("password", ""),
            )

            if ups_data and "variables" in ups_data:
                vars = ups_data["variables"]
                battery_charge = vars.get("battery.charge", "N/A")
                battery_runtime = vars.get("battery.runtime", "N/A")
                load = vars.get("ups.load", "N/A")
                status = vars.get("ups.status", "UNKNOWN")

                # Format runtime
                runtime_display = "N/A"
                if battery_runtime != "N/A":
                    try:
                        runtime_seconds = int(float(battery_runtime))
                        runtime_hours = runtime_seconds // 3600
                        runtime_minutes = (runtime_seconds % 3600) // 60
                        if runtime_hours > 0:
                            runtime_display = f"{runtime_hours}h {runtime_minutes}m"
                        else:
                            runtime_display = f"{runtime_minutes} min"
                    except:
                        runtime_display = battery_runtime

                # Status icon
                if "OL" in status:
                    icon = "✓"
                elif "OB" in status:
                    icon = "⚠"
                else:
                    icon = "✗"

                output += f"{icon} {ups_name} ({server_name})\n"
                output += f"  Battery Charge: {battery_charge}%\n"
                output += f"  Runtime Remaining: {runtime_display}\n"
                output += f"  Current Load: {load}%\n"
                output += "\n"
            else:
                output += f"✗ {ups_name} ({server_name}): Unable to query\n\n"

    return output




# Entry point
if __name__ == "__main__":
    # Load inventory on startup
    inventory = _load_inventory()
    nut_servers = inventory.get("nut_servers", {})
    total_ups = sum(len(cfg["ups_devices"]) for cfg in nut_servers.values())
    logger.info(f"UPS Monitor MCP Server starting with {len(nut_servers)} NUT server(s), {total_ups} UPS device(s)")

    # Run with stdio transport by default (backward compatible)
    mcp.run()

    # Alternative transports (comment/uncomment as needed):
    # mcp.run(transport="http", host="0.0.0.0", port=8000)
    # mcp.run(transport="sse", host="0.0.0.0", port=8000)
