#!/usr/bin/env python3
"""
Unifi Network MCP Server v2.0 (FastMCP) - Optimized Version
Provides access to Unifi network devices and clients with better performance
Separates infrastructure (devices) from clients for faster queries

Features:
- Get network devices (switches, APs, gateways)
- Get network clients and their connections
- Get network summary (VLANs, device count, client count)
- Force refresh network data (bypass cache)
- Cached for better performance (5 minute cache)
- Supports stdio, HTTP, and SSE transports
"""

import asyncio
import glob
import json
import logging
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from fastmcp import FastMCP

from mcp_config_loader import load_env_file, COMMON_ALLOWED_ENV_VARS
from mcp_error_handler import MCPErrorClassifier, log_error_with_context

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("Unifi Network")

# Configuration
SCRIPT_DIR = Path(__file__).parent
ENV_FILE = SCRIPT_DIR / ".env"

# Load .env with security hardening
UNIFI_ALLOWED_VARS = COMMON_ALLOWED_ENV_VARS | {
    "UNIFI_HOST",
    "UNIFI_API_KEY",
}

# Only load env file at module level if not in unified mode
if not os.getenv("MCP_UNIFIED_MODE"):
    load_env_file(ENV_FILE, allowed_vars=UNIFI_ALLOWED_VARS, strict=True)

UNIFI_EXPORTER_PATH = SCRIPT_DIR / "unifi_exporter.py"
UNIFI_HOST = os.getenv("UNIFI_HOST", "192.168.1.1")
UNIFI_API_KEY = os.getenv("UNIFI_API_KEY", "")

# Cache configuration
CACHE_DIR = Path(tempfile.gettempdir()) / "unifi_mcp_cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_DURATION = timedelta(minutes=5)  # Cache data for 5 minutes

logger.info(f"Unifi host: {UNIFI_HOST}")
logger.info(f"API key configured: {'Yes' if UNIFI_API_KEY else 'No'}")
logger.info(f"Cache directory: {CACHE_DIR}")


def get_cached_data():
    """Get cached Unifi data if available and not expired"""
    cache_file = CACHE_DIR / "unifi_data.json"

    if not cache_file.exists():
        return None

    # Check if cache is still valid
    cache_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
    if datetime.now() - cache_time > CACHE_DURATION:
        logger.info("Cache expired")
        return None

    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            logger.info(f"Using cached data from {cache_time}")
            return data
    except Exception as e:
        logger.error(f"Error reading cache: {e}")
        return None


def save_cached_data(data):
    """Save Unifi data to cache"""
    cache_file = CACHE_DIR / "unifi_data.json"
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f)
        logger.info(f"Saved data to cache: {cache_file}")
    except Exception as e:
        logger.error(f"Error saving cache: {e}")


async def fetch_unifi_data():
    """
    Fetch fresh data from Unifi exporter

    Raises:
        FileNotFoundError: If exporter script not found
        ValueError: If API key not configured
        RuntimeError: If exporter fails with detailed error message
    """
    if not UNIFI_EXPORTER_PATH.exists():
        error_msg = MCPErrorClassifier.format_error_message(
            service_name="Unifi",
            error_type="Configuration Error",
            message=f"Unifi exporter script not found",
            remediation=f"Ensure unifi_exporter.py exists in the project directory at {UNIFI_EXPORTER_PATH.parent}",
            details=f"Expected path: {UNIFI_EXPORTER_PATH}"
        )
        raise FileNotFoundError(error_msg)

    if not UNIFI_API_KEY:
        error_msg = MCPErrorClassifier.format_error_message(
            service_name="Unifi",
            error_type="Configuration Error",
            message="UNIFI_API_KEY environment variable not set",
            remediation="Set UNIFI_API_KEY in your .env file. Generate an API key in Unifi Settings > Admins > API.",
            details="API key is required to authenticate with Unifi controller"
        )
        raise ValueError(error_msg)

    with tempfile.TemporaryDirectory() as tmpdir:
        logger.info(f"Running Unifi exporter for {UNIFI_HOST}...")

        # Fix Windows console encoding issues
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUNBUFFERED"] = "1"

        cmd = [
            "python",
            str(UNIFI_EXPORTER_PATH),
            "--host",
            UNIFI_HOST,
            "--api-key",
            UNIFI_API_KEY,
            "--format",
            "json",
            "--output-dir",
            tmpdir,
        ]

        # Use Popen with communicate() for proper subprocess handling
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,  # Prevent stdin blocking
            text=True,
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )

        try:
            stdout, stderr = process.communicate(timeout=30)

            if process.returncode != 0:
                # Parse stderr to identify specific error types
                stderr_lower = stderr.lower()

                # Classify error based on stderr content
                error_classification = MCPErrorClassifier.classify_text_error(stderr)

                if error_classification:
                    # Known error pattern detected
                    error_msg = MCPErrorClassifier.format_error_message(
                        service_name="Unifi",
                        error_type=error_classification["type"],
                        message=f"Unifi exporter failed (exit code {process.returncode})",
                        remediation=error_classification["remediation"],
                        details=stderr.strip()[:500],  # Limit stderr output
                        hostname=UNIFI_HOST
                    )
                elif "401" in stderr or "unauthorized" in stderr_lower:
                    # API authentication error
                    error_msg = MCPErrorClassifier.format_error_message(
                        service_name="Unifi",
                        error_type="Authentication Failed",
                        message=f"Invalid Unifi API key for {UNIFI_HOST}",
                        remediation="Verify UNIFI_API_KEY in .env matches the API key from Unifi Settings > Admins > API. Ensure the key has not expired.",
                        details=stderr.strip()[:500],
                        hostname=UNIFI_HOST
                    )
                elif "connection refused" in stderr_lower or "failed to connect" in stderr_lower:
                    # Connection error
                    error_msg = MCPErrorClassifier.format_connection_error(
                        service_name="Unifi",
                        hostname=UNIFI_HOST,
                        port=443,  # Default Unifi port
                        additional_guidance="Ensure Unifi controller is running and accessible. Check UNIFI_HOST setting."
                    )
                    error_msg += f"\n\nExporter output: {stderr.strip()[:500]}"
                elif "timeout" in stderr_lower or "timed out" in stderr_lower:
                    # Timeout error
                    error_msg = MCPErrorClassifier.format_timeout_error(
                        service_name="Unifi",
                        hostname=UNIFI_HOST,
                        port=443,
                        timeout_seconds=30
                    )
                    error_msg += f"\n\nExporter output: {stderr.strip()[:500]}"
                else:
                    # Generic error with return code context
                    error_msg = MCPErrorClassifier.format_error_message(
                        service_name="Unifi",
                        error_type=f"Exporter Failed (Code {process.returncode})",
                        message=f"Unifi exporter process failed",
                        remediation="Check the error details below. Verify UNIFI_HOST and UNIFI_API_KEY are correct.",
                        details=stderr.strip()[:500],
                        hostname=UNIFI_HOST
                    )

                log_error_with_context(
                    logger,
                    f"Unifi exporter failed with code {process.returncode}",
                    context={"host": UNIFI_HOST, "returncode": process.returncode, "stderr": stderr[:200]}
                )
                raise RuntimeError(error_msg)

        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            error_msg = MCPErrorClassifier.format_timeout_error(
                service_name="Unifi",
                hostname=UNIFI_HOST,
                timeout_seconds=30
            )
            error_msg += "\n\nThe exporter process was killed after timeout. Check if Unifi controller is responding slowly."
            log_error_with_context(logger, "Unifi exporter timeout", context={"host": UNIFI_HOST, "timeout": 30})
            logger.warning(f"Process timeout but checking for output files... STDERR: {stderr[:200]}")

        # Find the generated JSON file
        json_files = glob.glob(os.path.join(tmpdir, "unifi_network_*.json"))

        if not json_files:
            error_msg = MCPErrorClassifier.format_error_message(
                service_name="Unifi",
                error_type="Export Failed",
                message="No output file generated by Unifi exporter",
                remediation="The exporter ran but produced no output. Check if Unifi controller is accessible and responding.",
                details=f"STDOUT: {stdout[:200]}, STDERR: {stderr[:200]}",
                hostname=UNIFI_HOST
            )
            log_error_with_context(
                logger,
                "Unifi exporter generated no output",
                context={"host": UNIFI_HOST, "stdout": stdout[:100], "stderr": stderr[:100]}
            )
            raise FileNotFoundError(error_msg)

        # Read the most recent file
        latest_file = sorted(json_files)[-1]
        logger.info(f"Reading data from {latest_file}")

        with open(latest_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Save to cache
        save_cached_data(data)

        return data


async def get_unifi_data():
    """Get Unifi data from cache or fetch fresh"""
    # Try cache first
    data = get_cached_data()
    if data:
        return data

    # Fetch fresh data
    logger.info("Fetching fresh Unifi data...")
    return await fetch_unifi_data()


def format_network_devices(data: dict) -> str:
    """Format network devices output"""
    devices = data.get("devices", [])

    output = "=== NETWORK DEVICES ===\n\n"
    output += f"Total: {len(devices)} devices\n\n"

    # Group by type
    by_type = {}
    for device in devices:
        device_type = device.get("type", "unknown")
        if device_type not in by_type:
            by_type[device_type] = []
        by_type[device_type].append(device)

    type_names = {
        "ugw": "Gateways",
        "usw": "Switches",
        "uap": "Access Points",
        "unknown": "Other",
    }

    for device_type, type_devices in sorted(by_type.items()):
        output += f"\n{type_names.get(device_type, device_type.upper())} ({len(type_devices)}):\n"

        for device in type_devices:
            name = device.get("name", "Unknown")
            model = device.get("model", "N/A")
            ip = device.get("ip", "N/A")
            state = device.get("state", 0)
            status = "✓ Online" if state == 1 else "✗ Offline"
            version = device.get("version", "N/A")

            output += f"  • {name} ({model})\n"
            output += f"    IP: {ip} | Status: {status} | Version: {version}\n"

            # Add client count for APs
            if device_type == "uap":
                num_sta = device.get("num_sta", 0)
                output += f"    Connected clients: {num_sta}\n"

            # Add port info for switches
            if device_type == "usw":
                port_table = device.get("port_table", [])
                ports_up = sum(1 for p in port_table if p.get("up", False))
                output += f"    Ports: {ports_up}/{len(port_table)} up\n"

    return output


def format_network_clients(data: dict) -> str:
    """Format network clients output"""
    clients = data.get("clients", [])
    networks = {n["_id"]: n for n in data.get("networks", [])}

    output = "=== NETWORK CLIENTS ===\n\n"
    output += f"Total: {len(clients)} active clients\n\n"

    # Group by VLAN/network
    by_network = {}
    for client in clients:
        network_id = client.get("network_id", "unknown")
        if network_id not in by_network:
            by_network[network_id] = []
        by_network[network_id].append(client)

    for network_id, network_clients in sorted(
        by_network.items(), key=lambda x: len(x[1]), reverse=True
    ):
        network_name = networks.get(network_id, {}).get("name", "Unknown")
        vlan = networks.get(network_id, {}).get("vlan", "N/A")

        output += f"\n{network_name} (VLAN {vlan}) - {len(network_clients)} clients:\n"

        # Show first 10 clients per network
        for client in network_clients[:10]:
            hostname = client.get("hostname", client.get("name", "Unknown"))
            ip = client.get("ip", "N/A")
            mac = client.get("mac", "N/A")
            is_wired = client.get("is_wired", False)
            conn_type = "Wired" if is_wired else "Wireless"

            output += f"  • {hostname} ({ip})\n"
            output += f"    MAC: {mac} | {conn_type}\n"

        if len(network_clients) > 10:
            output += f"  ... and {len(network_clients) - 10} more\n"

    return output


def format_network_summary(data: dict) -> str:
    """Format network summary output"""
    networks = data.get("networks", [])
    devices = data.get("devices", [])
    clients = data.get("clients", [])

    output = "=== NETWORK SUMMARY ===\n\n"

    # Overall stats
    output += f"Networks/VLANs: {len(networks)}\n"
    output += f"Network Devices: {len(devices)}\n"
    output += f"Active Clients: {len(clients)}\n\n"

    # Device breakdown
    online_devices = sum(1 for d in devices if d.get("state") == 1)
    output += f"DEVICES:\n"
    output += f"  Online: {online_devices}/{len(devices)}\n"

    # Count by type
    device_types = {}
    for d in devices:
        dtype = d.get("type", "unknown")
        device_types[dtype] = device_types.get(dtype, 0) + 1

    type_names = {"ugw": "Gateways", "usw": "Switches", "uap": "Access Points"}
    for dtype, count in device_types.items():
        output += f"  {type_names.get(dtype, dtype)}: {count}\n"

    # Client breakdown
    wired = sum(1 for c in clients if c.get("is_wired", False))
    output += f"\nCLIENTS:\n"
    output += f"  Wired: {wired}\n"
    output += f"  Wireless: {len(clients) - wired}\n"

    # Top networks by client count
    by_network = {}
    for client in clients:
        network_id = client.get("network_id", "unknown")
        by_network[network_id] = by_network.get(network_id, 0) + 1

    output += f"\nTOP NETWORKS:\n"
    networks_dict = {n["_id"]: n for n in networks}
    for network_id, count in sorted(
        by_network.items(), key=lambda x: x[1], reverse=True
    )[:5]:
        name = networks_dict.get(network_id, {}).get("name", "Unknown")
        vlan = networks_dict.get(network_id, {}).get("vlan", "N/A")
        output += f"  • {name} (VLAN {vlan}): {count} clients\n"

    return output


# FastMCP Tools

@mcp.tool()
async def get_network_devices() -> str:
    """Get all Unifi network devices (switches, APs, gateways) with status and basic info. This is cached for better performance."""
    try:
        data = await get_unifi_data()
        return format_network_devices(data)
    except Exception as e:
        # Check if error is already formatted by our error handler
        error_text = str(e)
        if "✗ Unifi" in error_text or "→" in error_text:
            return error_text
        else:
            error_msg = MCPErrorClassifier.format_error_message(
                service_name="Unifi",
                error_type="Tool Execution Error",
                message="Failed to get network devices",
                remediation="Check the logs for detailed error information. Ensure Unifi controller is configured correctly.",
                details=str(e)
            )
            log_error_with_context(logger, "Error in get_network_devices", error=e)
            return error_msg


@mcp.tool()
async def get_network_clients() -> str:
    """Get all active network clients and their connections. This is cached for better performance."""
    try:
        data = await get_unifi_data()
        return format_network_clients(data)
    except Exception as e:
        error_text = str(e)
        if "✗ Unifi" in error_text or "→" in error_text:
            return error_text
        else:
            error_msg = MCPErrorClassifier.format_error_message(
                service_name="Unifi",
                error_type="Tool Execution Error",
                message="Failed to get network clients",
                remediation="Check the logs for detailed error information. Ensure Unifi controller is configured correctly.",
                details=str(e)
            )
            log_error_with_context(logger, "Error in get_network_clients", error=e)
            return error_msg


@mcp.tool()
async def get_network_summary() -> str:
    """Get network overview: VLANs, device count, client count. Fast summary view."""
    try:
        data = await get_unifi_data()
        return format_network_summary(data)
    except Exception as e:
        error_text = str(e)
        if "✗ Unifi" in error_text or "→" in error_text:
            return error_text
        else:
            error_msg = MCPErrorClassifier.format_error_message(
                service_name="Unifi",
                error_type="Tool Execution Error",
                message="Failed to get network summary",
                remediation="Check the logs for detailed error information. Ensure Unifi controller is configured correctly.",
                details=str(e)
            )
            log_error_with_context(logger, "Error in get_network_summary", error=e)
            return error_msg


@mcp.tool()
async def refresh_network_data() -> str:
    """Force refresh network data from Unifi controller (bypasses cache)."""
    try:
        logger.info("Force refreshing network data...")
        data = await fetch_unifi_data()
        return f"✓ Network data refreshed successfully\n\nDevices: {len(data.get('devices', []))}\nClients: {len(data.get('clients', []))}\nNetworks: {len(data.get('networks', []))}"
    except Exception as e:
        error_text = str(e)
        if "✗ Unifi" in error_text or "→" in error_text:
            return error_text
        else:
            error_msg = MCPErrorClassifier.format_error_message(
                service_name="Unifi",
                error_type="Tool Execution Error",
                message="Failed to refresh network data",
                remediation="Check the logs for detailed error information. Ensure Unifi controller is configured correctly.",
                details=str(e)
            )
            log_error_with_context(logger, "Error in refresh_network_data", error=e)
            return error_msg


# Entry point
if __name__ == "__main__":
    logger.info(f"Unifi Network MCP Server starting for host: {UNIFI_HOST}")

    # Run with stdio transport by default (backward compatible)
    mcp.run()

    # Alternative transports (comment/uncomment as needed):
    # mcp.run(transport="http", host="0.0.0.0", port=8000)
    # mcp.run(transport="sse", host="0.0.0.0", port=8000)
