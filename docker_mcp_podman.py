#!/usr/bin/env python3
"""
Docker/Podman MCP Server v2.0 (FastMCP)
Provides access to Docker and Podman containers via HTTP API
Reads host configuration from Ansible inventory

Features:
- List containers on specific hosts or all hosts
- Get container stats (CPU, memory)
- Check specific container status
- Find containers by label
- Get container labels
- Supports both Docker and Podman
- Supports stdio, HTTP, and SSE transports
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Optional

import aiohttp

from fastmcp import FastMCP
from mcp import types

from mcp_config_loader import load_env_file, load_indexed_env_vars, COMMON_ALLOWED_ENV_VARS
from mcp_error_handler import log_error_with_context

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("Docker/Podman Monitor")

# Load .env with security hardening
SCRIPT_DIR = Path(__file__).parent
ENV_FILE = SCRIPT_DIR / ".env"

DOCKER_ALLOWED_VARS = COMMON_ALLOWED_ENV_VARS | {
    "DOCKER_*",  # Matches DOCKER_HOST, DOCKER_PORT, etc.
    "PODMAN_*",  # Matches PODMAN_HOST, PODMAN_PORT, etc.
}

# Only load env file at module level if not in unified mode
if not os.getenv("MCP_UNIFIED_MODE"):
    load_env_file(ENV_FILE, allowed_vars=DOCKER_ALLOWED_VARS, strict=True)

# Configuration
ANSIBLE_INVENTORY_PATH = os.getenv("ANSIBLE_INVENTORY_PATH", "")
logger.info(f"Ansible inventory: {ANSIBLE_INVENTORY_PATH}")

# Global cache for container hosts
_container_hosts_cache = None


def _load_container_hosts():
    """Load container hosts from Ansible inventory or environment variables"""
    global _container_hosts_cache

    if _container_hosts_cache is not None:
        return _container_hosts_cache

    ansible_inventory_path = os.getenv("ANSIBLE_INVENTORY_PATH", "")
    if not ansible_inventory_path:
        logger.warning("No Ansible inventory path provided, using .env fallback")
        _container_hosts_cache = _load_container_hosts_from_env()
        return _container_hosts_cache

    # Lazy import - only load Ansible when needed
    from ansible_config_manager import AnsibleConfigManager

    container_hosts = {}
    manager = AnsibleConfigManager(
        inventory_path=ansible_inventory_path,
        logger_obj=logger
    )

    if not manager.is_available():
        logger.warning("Ansible not available, using .env fallback")
        _container_hosts_cache = _load_container_hosts_from_env()
        return _container_hosts_cache

    # Load Docker hosts
    docker_group_name = os.getenv("DOCKER_ANSIBLE_GROUP", "docker_hosts")
    docker_hosts = manager.get_group_hosts(docker_group_name)
    for hostname, ip in docker_hosts.items():
        port = manager.get_host_variable(hostname, "docker_api_port", "2375")
        container_hosts[hostname] = {
            "endpoint": f"{ip}:{port}",
            "runtime": "docker",
        }
        logger.info(f"Found Docker host: {hostname} -> {ip}:{port}")

    # Load Podman hosts
    podman_group_name = os.getenv("PODMAN_ANSIBLE_GROUP", "podman_hosts")
    podman_hosts = manager.get_group_hosts(podman_group_name)
    for hostname, ip in podman_hosts.items():
        port = manager.get_host_variable(hostname, "podman_api_port", "8080")
        container_hosts[hostname] = {
            "endpoint": f"{ip}:{port}",
            "runtime": "podman",
        }
        logger.info(f"Found Podman host: {hostname} -> {ip}:{port}")

    if not container_hosts:
        logger.warning("No container hosts found in Ansible inventory, using .env fallback")
        _container_hosts_cache = _load_container_hosts_from_env()
        return _container_hosts_cache

    _container_hosts_cache = container_hosts
    logger.info(f"Loaded {len(container_hosts)} container hosts from Ansible")
    return _container_hosts_cache


def _load_container_hosts_from_env():
    """Fallback: Load container hosts from environment variables"""
    container_hosts = {}

    # Load Docker servers using generic function
    docker_servers = load_indexed_env_vars(
        prefix="DOCKER_",
        name_suffix="_NAME",
        target_suffix="_ENDPOINT",
        logger_obj=logger
    )

    for index, server_info in docker_servers.items():
        endpoint = server_info["target"]
        name = server_info["name"]

        if not endpoint:
            continue

        display_name = name if name else f"docker-server{index}".lower()
        container_hosts[display_name] = {"endpoint": endpoint, "runtime": "docker"}
        logger.info(f"Loaded Docker from env: {display_name} -> {endpoint}")

    # Load Podman servers using generic function
    podman_servers = load_indexed_env_vars(
        prefix="PODMAN_",
        name_suffix="_NAME",
        target_suffix="_ENDPOINT",
        logger_obj=logger
    )

    for index, server_info in podman_servers.items():
        endpoint = server_info["target"]
        name = server_info["name"]

        if not endpoint:
            continue

        display_name = name if name else f"podman-server{index}".lower()
        container_hosts[display_name] = {"endpoint": endpoint, "runtime": "podman"}
        logger.info(f"Loaded Podman from env: {display_name} -> {endpoint}")

    return container_hosts


async def container_api_request(
    host: str, endpoint: str, timeout: int = 5
) -> Optional[Dict]:
    """Make a request to Docker or Podman API"""
    container_hosts = _load_container_hosts()

    if host not in container_hosts:
        logger.error(f"Unknown host: {host}")
        return None

    config = container_hosts[host]
    runtime = config["runtime"]

    # Podman API uses /v4.0.0/libpod prefix for some endpoints
    if runtime == "podman" and endpoint.startswith("/containers"):
        endpoint = f"/v4.0.0/libpod{endpoint}"

    url = f"http://{config['endpoint']}{endpoint}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status in [401, 404, 500]:
                    logger.debug(f"{runtime} API returned HTTP {response.status} for {url}")
                    return None
                else:
                    log_error_with_context(
                        logger,
                        f"{runtime} API returned HTTP {response.status}",
                        context={"host": host, "endpoint": endpoint, "status": response.status, "url": url}
                    )
                    return None
    except asyncio.TimeoutError:
        log_error_with_context(
            logger,
            f"Timeout connecting to {runtime} API",
            context={"host": host, "endpoint": config['endpoint'], "timeout": timeout}
        )
        return None
    except (aiohttp.ClientConnectorError, aiohttp.ClientError) as e:
        logger.debug(f"Connection failed to {runtime} API on {host} - service may be offline")
        return None
    except Exception as e:
        log_error_with_context(
            logger,
            f"Unexpected error connecting to {runtime} API",
            error=e,
            context={"host": host, "endpoint": config['endpoint']}
        )
        return None


def normalize_container_info(container: Dict, runtime: str) -> Dict:
    """Normalize container information between Docker and Podman formats"""
    if runtime == "podman":
        return {
            "Id": container.get("Id", ""),
            "Names": [
                (
                    container.get("Names", ["Unknown"])[0]
                    if isinstance(container.get("Names"), list)
                    else container.get("Name", "Unknown")
                )
            ],
            "Image": container.get("Image", "Unknown"),
            "ImageID": container.get("ImageID", ""),
            "Command": container.get("Command", []),
            "Created": container.get("Created", 0),
            "State": container.get("State", "unknown"),
            "Status": container.get("Status", "Unknown"),
            "Ports": container.get("Ports", []),
            "Labels": container.get("Labels", {}),
            "runtime": "podman",
        }
    else:
        container["runtime"] = "docker"
        return container


def format_labels_output(labels: Dict, indent: str = "  ") -> str:
    """Format container labels for display"""
    if not labels:
        return ""

    output = f"{indent}Labels:\n"

    traefik_labels = {k: v for k, v in labels.items() if "traefik" in k.lower()}
    domain_labels = {k: v for k, v in labels.items() if any(d in k.lower() for d in ["domain", "host", "url"])}
    other_labels = {k: v for k, v in labels.items() if k not in traefik_labels and k not in domain_labels}

    for key, value in traefik_labels.items():
        output += f"{indent}  • {key}: {value}\n"

    for key, value in domain_labels.items():
        output += f"{indent}  • {key}: {value}\n"

    for i, (key, value) in enumerate(other_labels.items()):
        if i < 5:
            output += f"{indent}  • {key}: {value}\n"

    if len(other_labels) > 5:
        remaining = len(other_labels) - 5
        output += f"{indent}  ... and {remaining} more labels\n"

    return output


# FastMCP Tools

@mcp.tool(
    title="Get Containers on Host",
    annotations=types.ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    )
)
async def list_containers(hostname: str) -> str:
    """
    Get containers on a specific host (works with both Docker and Podman)

    Args:
        hostname: Container host from your Ansible inventory
    """
    container_hosts = _load_container_hosts()

    if hostname not in container_hosts:
        return f"Error: Unknown host '{hostname}'. Valid hosts: {', '.join(container_hosts.keys())}"

    runtime = container_hosts[hostname]["runtime"]
    containers = await container_api_request(hostname, "/containers/json")

    if containers is None:
        return f"Error: Could not connect to {runtime.capitalize()} API on {hostname}"

    output = f"=== {hostname.upper()} ({runtime.upper()}) ===\n\n"

    if not containers:
        output += "No containers running\n"
    else:
        for container in containers:
            norm = normalize_container_info(container, runtime)

            name_str = norm["Names"][0].lstrip("/") if norm["Names"] else "Unknown"
            image = norm["Image"]
            status = norm["Status"]

            port_str = ""
            ports = norm.get("Ports", [])
            if ports:
                port_mappings = []
                for port in ports:
                    if "PublicPort" in port:
                        port_mappings.append(
                            f"{port.get('PublicPort', '?')}->{port.get('PrivatePort', '?')}"
                        )
                if port_mappings:
                    port_str = f" | Ports: {', '.join(port_mappings)}"

            output += f"• {name_str} ({image})\n"
            output += f"  Status: {status}{port_str}\n"

            labels = norm.get("Labels", {})
            if labels:
                traefik_labels = {k: v for k, v in labels.items() if "traefik" in k.lower()}
                domain_labels = {k: v for k, v in labels.items() if any(d in k.lower() for d in ["domain", "host", "url"])}

                if traefik_labels or domain_labels:
                    output += "  Labels:\n"
                    for key, value in list(traefik_labels.items())[:3]:
                        display_value = value if len(str(value)) <= 50 else str(value)[:47] + "..."
                        output += f"    • {key}: {display_value}\n"
                    for key, value in list(domain_labels.items())[:2]:
                        display_value = value if len(str(value)) <= 50 else str(value)[:47] + "..."
                        output += f"    • {key}: {display_value}\n"

            output += "\n"

    return output


@mcp.tool(
    title="Get All Containers",
    annotations=types.ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    )
)
async def list_all_hosts() -> str:
    """Get all containers across all hosts"""
    container_hosts = _load_container_hosts()

    output = "=== ALL CONTAINER HOSTS ===\n\n"
    total_containers = 0
    results = []

    for hostname, config in container_hosts.items():
        runtime = config["runtime"]
        containers = await container_api_request(hostname, "/containers/json")

        host_output = f"--- {hostname.upper()} ---\n"

        if containers is not None:
            total_containers += len(containers)
            if containers:
                for container in containers:
                    norm = normalize_container_info(container, runtime)
                    name_str = norm["Names"][0].lstrip("/") if norm["Names"] else "Unknown"
                    image = norm["Image"]
                    host_output += f"  • {name_str} ({image})\n"
            else:
                host_output += "  No containers\n"
        else:
            host_output += f"  Error connecting\n"

        results.append(host_output)

    output = f"Total: {total_containers} containers\n\n" + output + "\n".join(results)
    return output


@mcp.tool(
    title="Get Container Stats",
    annotations=types.ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    )
)
async def get_stats(hostname: str) -> str:
    """
    Get CPU and memory stats for containers on a host

    Args:
        hostname: Container host from your Ansible inventory
    """
    container_hosts = _load_container_hosts()

    if hostname not in container_hosts:
        return f"Error: Unknown host '{hostname}'"

    runtime = container_hosts[hostname]["runtime"]
    containers = await container_api_request(hostname, "/containers/json")

    if containers is None:
        return f"Error: Could not connect to {runtime.capitalize()} API on {hostname}"

    output = f"=== STATS: {hostname.upper()} ===\n\n"

    stats_endpoint_template = "/containers/{}/stats?stream=false"

    for container in containers[:10]:  # Limit to 10 for performance
        norm = normalize_container_info(container, runtime)
        container_id = norm["Id"]
        name = norm["Names"][0].lstrip("/") if norm["Names"] else "Unknown"

        stats = await container_api_request(
            hostname, stats_endpoint_template.format(container_id), timeout=10
        )

        if stats:
            cpu_percent = 0.0
            try:
                cpu_stats = stats.get("cpu_stats", {})
                precpu_stats = stats.get("precpu_stats", {})

                cpu_delta = cpu_stats.get("cpu_usage", {}).get("total_usage", 0) - precpu_stats.get("cpu_usage", {}).get("total_usage", 0)
                system_delta = cpu_stats.get("system_cpu_usage", 0) - precpu_stats.get("system_cpu_usage", 0)

                num_cpus = len(cpu_stats.get("cpu_usage", {}).get("percpu_usage", []))
                if num_cpus == 0:
                    num_cpus = 1

                if system_delta > 0 and cpu_delta > 0:
                    cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0
            except:
                pass

            mem_usage = 0.0
            mem_limit = 0.0
            mem_percent = 0.0
            try:
                mem_stats = stats.get("memory_stats", {})
                mem_usage = mem_stats.get("usage", 0) / (1024**3)
                mem_limit = mem_stats.get("limit", 0) / (1024**3)

                if mem_limit > 0:
                    mem_percent = (mem_stats.get("usage", 0) / mem_stats.get("limit", 1)) * 100.0
            except:
                pass

            output += f"• {name}\n"
            output += f"  CPU: {cpu_percent:.1f}%\n"
            output += f"  Memory: {mem_usage:.2f}GB / {mem_limit:.2f}GB ({mem_percent:.1f}%)\n\n"
        else:
            output += f"• {name}\n  Stats unavailable\n\n"

    return output


@mcp.tool(
    title="Check Container Status",
    annotations=types.ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    )
)
async def get_container_details(hostname: str, container: str) -> str:
    """
    Check if a specific container is running on a host

    Args:
        hostname: Container host from your Ansible inventory
        container: Container name to check
    """
    container_hosts = _load_container_hosts()

    if hostname not in container_hosts:
        return f"Error: Unknown host '{hostname}'"

    runtime = container_hosts[hostname]["runtime"]
    containers = await container_api_request(hostname, "/containers/json")

    if containers is None:
        return f"Error: Could not connect to {runtime.capitalize()} API on {hostname}"

    for c in containers:
        norm = normalize_container_info(c, runtime)
        names = norm["Names"]

        for name in names:
            clean_name = name.lstrip("/")
            if clean_name == container or name == container:
                output = f"✓ Container '{container}' is RUNNING on {hostname}\n"
                output += f"  Image: {norm['Image']}\n"
                output += f"  Status: {norm['Status']}\n"
                output += f"  Runtime: {runtime}\n"

                labels = norm.get("Labels", {})
                if labels:
                    output += "\n" + format_labels_output(labels)

                return output

    return f"✗ Container '{container}' is NOT running on {hostname}"


@mcp.tool(
    title="Get Container Logs",
    annotations=types.ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    )
)
async def get_container_logs(hostname: str, container: str, tail: int = 100) -> str:
    """
    Get recent logs from a specific container

    Args:
        hostname: Container host from your Ansible inventory
        container: Container name
        tail: Number of recent log lines to retrieve (default: 100)
    """
    container_hosts = _load_container_hosts()

    if hostname not in container_hosts:
        return f"Error: Unknown host '{hostname}'. Valid hosts: {', '.join(container_hosts.keys())}"

    runtime = container_hosts[hostname]["runtime"]
    containers = await container_api_request(hostname, "/containers/json")

    if containers is None:
        return f"Error: Could not connect to {runtime.capitalize()} API on {hostname}"

    # Find the container ID
    container_id = None
    for c in containers:
        norm = normalize_container_info(c, runtime)
        names = norm["Names"]

        for name in names:
            clean_name = name.lstrip("/")
            if clean_name == container or name == container:
                container_id = norm["Id"]
                break
        if container_id:
            break

    if not container_id:
        return f"✗ Container '{container}' not found on {hostname}"

    # Get logs via API
    log_endpoint = f"/containers/{container_id}/logs?stdout=true&stderr=true&tail={tail}"

    try:
        # For logs endpoint, we need special handling as it returns plain text
        config = container_hosts[hostname]
        if runtime == "podman":
            log_endpoint = f"/v4.0.0/libpod{log_endpoint}"

        url = f"http://{config['endpoint']}{log_endpoint}"

        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    log_data = await response.text()
                    output = f"=== LOGS: {container} on {hostname} ===\n\n"
                    output += f"Last {tail} lines:\n\n"
                    output += log_data
                    return output
                else:
                    return f"Error: Could not retrieve logs (HTTP {response.status})"
    except Exception as e:
        return f"Error retrieving logs: {str(e)}"


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
    """Reload container hosts from Ansible inventory (useful after inventory changes)"""
    global _container_hosts_cache
    _container_hosts_cache = None
    container_hosts = _load_container_hosts()

    output = "=== INVENTORY RELOADED ===\n\n"
    output += f"✓ Loaded {len(container_hosts)} container host(s)\n\n"

    for hostname, config in container_hosts.items():
        runtime = config["runtime"]
        output += f"  • {hostname} ({runtime.upper()}) - {config['endpoint']}\n"

    return output


# Entry point
if __name__ == "__main__":
    # Load container hosts on startup
    container_hosts = _load_container_hosts()
    logger.info(f"Docker/Podman MCP Server starting with {len(container_hosts)} container host(s)")

    if not container_hosts:
        logger.warning("No container hosts configured!")
        logger.warning("Please set ANSIBLE_INVENTORY_PATH or DOCKER_/PODMAN_*_ENDPOINT environment variables")

    # Run with stdio transport by default (backward compatible)
    mcp.run()

    # Alternative transports (comment/uncomment as needed):
    # mcp.run(transport="http", host="0.0.0.0", port=8000)
    # mcp.run(transport="sse", host="0.0.0.0", port=8000)
