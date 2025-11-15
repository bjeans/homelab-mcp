#!/usr/bin/env python3
"""
Docker/Podman MCP Server
Provides access to Docker and Podman containers via HTTP API
Reads host configuration from Ansible inventory
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Optional

import aiohttp
import yaml

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from ansible_config_manager import AnsibleConfigManager
from mcp_config_loader import load_env_file, load_indexed_env_vars, COMMON_ALLOWED_ENV_VARS

# Module-level initialization for standalone mode
server = Server("docker-info")

# Load .env with security hardening
SCRIPT_DIR = Path(__file__).parent
ENV_FILE = SCRIPT_DIR / ".env"

DOCKER_ALLOWED_VARS = COMMON_ALLOWED_ENV_VARS | {
    "DOCKER_*",  # Matches DOCKER_HOST, DOCKER_PORT, etc.
    "PODMAN_*",  # Matches PODMAN_HOST, PODMAN_PORT, etc.
}

# Only load env file at module level (for standalone mode)
# When used as a class, config loading happens in __init__
if __name__ == "__main__":
    load_env_file(ENV_FILE, allowed_vars=DOCKER_ALLOWED_VARS, strict=True)
    ANSIBLE_INVENTORY_PATH = os.getenv("ANSIBLE_INVENTORY_PATH", "")
    logger.info(f"Ansible inventory: {ANSIBLE_INVENTORY_PATH}")


def load_container_hosts_from_ansible(inventory=None):
    """
    Load container hosts from Ansible inventory using centralized config manager
    Returns dict of {hostname: {'endpoint': 'ip:port', 'runtime': 'docker|podman'}}

    Args:
        inventory: Optional pre-loaded inventory (for compatibility, unused now)
    """
    ansible_inventory_path = os.getenv("ANSIBLE_INVENTORY_PATH", "")
    if not ansible_inventory_path:
        logger.warning("No Ansible inventory path provided")
        return load_container_hosts_from_env()

    container_hosts = {}
    manager = AnsibleConfigManager(
        inventory_path=ansible_inventory_path,
        logger_obj=logger
    )

    if not manager.is_available():
        logger.warning("Ansible not available, using .env fallback")
        return load_container_hosts_from_env()

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
        logger.warning("No container hosts found in Ansible inventory")
        return load_container_hosts_from_env()

    logger.info(f"Loaded {len(container_hosts)} container hosts from Ansible")
    return container_hosts


def load_container_hosts_from_env():
    """
    Fallback: Load container hosts from environment variables
    Returns dict of {hostname: {'endpoint': 'ip:port', 'runtime': 'docker|podman'}}
    
    Supports two patterns:
    1. Indexed: DOCKER_SERVER1_ENDPOINT, DOCKER_SERVER1_NAME
    2. Named: DOCKER_CYBER_ENDPOINT, PODMAN_HL15_ENDPOINT
    """
    container_hosts = {}
    
    # Pattern 1: Indexed servers (DOCKER_SERVER1_ENDPOINT, PODMAN_HL15_ENDPOINT)
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
        
        # Skip unnamed indexed entries if the same endpoint will be loaded by Pattern 2
        # with a better display name (e.g., skip "podman-server15" if "hl15" will be loaded)
        if not name:
            # Check if there's a named PODMAN_*_ENDPOINT that has the same value
            for env_key, env_value in os.environ.items():
                if env_key.startswith("PODMAN_") and env_key.endswith("_ENDPOINT") and env_value == endpoint:
                    middle = env_key[7:-9]
                    # Only skip if it's a named pattern (not purely numeric)
                    if middle and not middle.isdigit():
                        logger.debug(f"Skipping podman-server{index} (using {middle.lower()} instead)")
                        break
            else:
                # No better name found, use the indexed name
                container_hosts[display_name] = {"endpoint": endpoint, "runtime": "podman"}
                logger.info(f"Loaded Podman from env: {display_name} -> {endpoint}")
                continue
            continue
        
        container_hosts[display_name] = {"endpoint": endpoint, "runtime": "podman"}
        logger.info(f"Loaded Podman from env: {display_name} -> {endpoint}")
    
    # Pattern 2: Named servers (DOCKER_CYBER_ENDPOINT, PODMAN_HL15_ENDPOINT)
    # These are non-indexed named servers from .env configuration
    for key, value in os.environ.items():
        # Match DOCKER_*_ENDPOINT pattern
        if key.startswith("DOCKER_") and key.endswith("_ENDPOINT"):
            # Extract the middle part (e.g., DOCKER_CYBER_ENDPOINT -> CYBER)
            middle = key[7:-9]  # Remove "DOCKER_" prefix and "_ENDPOINT" suffix
            
            # Skip indexed patterns (they should have been caught above)
            if middle and middle.isdigit():
                continue
            
            display_name = middle.lower() if middle else "docker"
            if display_name not in container_hosts:
                container_hosts[display_name] = {"endpoint": value, "runtime": "docker"}
                logger.info(f"Loaded Docker from env: {display_name} -> {value}")
        
        # Match PODMAN_*_ENDPOINT pattern
        elif key.startswith("PODMAN_") and key.endswith("_ENDPOINT"):
            # Extract the middle part (e.g., PODMAN_HL15_ENDPOINT -> HL15)
            middle = key[7:-9]  # Remove "PODMAN_" prefix and "_ENDPOINT" suffix
            
            # Skip if it's purely numeric (indexed pattern)
            if middle and middle.isdigit():
                continue
            
            display_name = middle.lower() if middle else "podman"
            if display_name not in container_hosts:
                container_hosts[display_name] = {"endpoint": value, "runtime": "podman"}
                logger.info(f"Loaded Podman from env: {display_name} -> {value}")

    return container_hosts


# Load container hosts on startup (module-level, works for both standalone and imported mode)
# This needs to be at module level for the @server decorators to access it
CONTAINER_HOSTS = {}

# Always try to load hosts from Ansible/env, regardless of how the module is being used
# This ensures both standalone mode and unified server mode work correctly
try:
    CONTAINER_HOSTS = load_container_hosts_from_ansible()
    if not CONTAINER_HOSTS:
        logger.warning("No container hosts configured!")
        logger.warning(
            "Please set ANSIBLE_INVENTORY_PATH or DOCKER_/PODMAN_*_ENDPOINT environment variables"
        )
except Exception as e:
    logger.error(f"Error loading container hosts: {e}")
    # Don't raise, allow the module to load even if config is missing

async def container_api_request(
    host: str, endpoint: str, timeout: int = 5
) -> Optional[Dict]:
    """
    Make a request to Docker or Podman API

    Args:
        host: Hostname from CONTAINER_HOSTS
        endpoint: API endpoint (e.g., '/containers/json')
        timeout: Request timeout in seconds

    Returns:
        JSON response dict or None on error
    """
    if host not in CONTAINER_HOSTS:
        logger.error(f"Unknown host: {host}")
        return None

    config = CONTAINER_HOSTS[host]
    runtime = config["runtime"]

    # Podman API uses /v4.0.0/libpod prefix for some endpoints
    # Docker uses standard Docker API
    if runtime == "podman":
        # Convert Docker-style endpoints to Podman libpod endpoints
        if endpoint.startswith("/containers"):
            endpoint = f"/v4.0.0/libpod{endpoint}"

    url = f"http://{config['endpoint']}{endpoint}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(
                        f"{runtime.capitalize()} API returned HTTP {response.status} for {host} ({url})"
                    )
                    return None
    except asyncio.TimeoutError:
        logger.error(
            f"Timeout connecting to {runtime} API on {host} (timeout={timeout}s)"
        )
        return None
    except aiohttp.ClientError as e:
        logger.error(f"Connection error to {runtime} API on {host}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error connecting to {runtime} API on {host}: {e}")
        return None


def normalize_container_info(container: Dict, runtime: str) -> Dict:
    """
    Normalize container information between Docker and Podman formats

    Args:
        container: Raw container dict from API
        runtime: 'docker' or 'podman'

    Returns:
        Normalized container dict with common fields
    """
    if runtime == "podman":
        # Podman uses different field names
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
        # Docker format (already normalized)
        container["runtime"] = "docker"
        return container


def format_labels_output(labels: Dict, indent: str = "  ") -> str:
    """
    Format container labels for display, highlighting traefik and custom domain labels

    Args:
        labels: Dictionary of container labels
        indent: Indentation string

    Returns:
        Formatted label string for display
    """
    if not labels:
        return ""

    output = f"{indent}Labels:\n"

    # Separate and prioritize traefik labels
    traefik_labels = {}
    domain_labels = {}
    other_labels = {}

    for key, value in labels.items():
        if "traefik" in key.lower():
            traefik_labels[key] = value
        elif any(domain_key in key.lower() for domain_key in ["domain", "host", "url"]):
            domain_labels[key] = value
        else:
            other_labels[key] = value

    # Display traefik labels first
    for key, value in traefik_labels.items():
        output += f"{indent}  • {key}: {value}\n"

    # Then domain-related labels
    for key, value in domain_labels.items():
        output += f"{indent}  • {key}: {value}\n"

    # Then other labels (show first 5)
    for i, (key, value) in enumerate(other_labels.items()):
        if i < 5:
            output += f"{indent}  • {key}: {value}\n"

    if len(other_labels) > 5:
        remaining = len(other_labels) - 5
        output += f"{indent}  ... and {remaining} more labels\n"

    return output


class DockerMCPServer:
    """Docker/Podman MCP Server - Class-based implementation"""

    def __init__(self, ansible_inventory=None):
        """Initialize configuration using existing config loading logic

        Args:
            ansible_inventory: Optional pre-loaded Ansible inventory dict (for unified mode)
        """
        # Load environment configuration (skip if in unified mode)
        if not os.getenv("MCP_UNIFIED_MODE"):
            load_env_file(ENV_FILE, allowed_vars=DOCKER_ALLOWED_VARS, strict=True)

        self.ansible_inventory_path = os.getenv("ANSIBLE_INVENTORY_PATH", "")
        logger.info(f"[DockerMCPServer] Ansible inventory: {self.ansible_inventory_path}")

        # Load container hosts (use pre-loaded inventory if provided)
        self.container_hosts = load_container_hosts_from_ansible(ansible_inventory)

        if not self.container_hosts:
            logger.warning("[DockerMCPServer] No container hosts configured!")
            logger.warning("Please set ANSIBLE_INVENTORY_PATH or DOCKER_/PODMAN_*_ENDPOINT environment variables")

    async def list_tools(self) -> list[types.Tool]:
        """Return list of Tool objects this server provides (with docker_ prefix)"""
        return [
            types.Tool(
                name="docker_get_containers",
                description="Get containers on a specific host (works with both Docker and Podman)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "hostname": {
                            "type": "string",
                            "description": f"Host: {', '.join(self.container_hosts.keys())}",
                            "enum": list(self.container_hosts.keys()),
                        }
                    },
                    "required": ["hostname"],
                },
                title="Get Containers on Host",
                readOnlyHint=True,
                destructiveHint=False,
                idempotentHint=False,
                openWorldHint=True,
            ),
            types.Tool(
                name="docker_get_all_containers",
                description="Get all containers across all hosts",
                inputSchema={"type": "object", "properties": {}},
                title="Get All Containers",
                readOnlyHint=True,
                destructiveHint=False,
                idempotentHint=False,
                openWorldHint=True,
            ),
            types.Tool(
                name="docker_get_container_stats",
                description="Get CPU and memory stats for containers on a host",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "hostname": {
                            "type": "string",
                            "description": f"Host: {', '.join(self.container_hosts.keys())}",
                            "enum": list(self.container_hosts.keys()),
                        }
                    },
                    "required": ["hostname"],
                },
                title="Get Container Stats",
                readOnlyHint=True,
                destructiveHint=False,
                idempotentHint=False,
                openWorldHint=True,
            ),
            types.Tool(
                name="docker_check_container",
                description="Check if a specific container is running on a host",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "hostname": {
                            "type": "string",
                            "description": f"Host: {', '.join(self.container_hosts.keys())}",
                            "enum": list(self.container_hosts.keys()),
                        },
                        "container": {
                            "type": "string",
                            "description": "Container name to check",
                        },
                    },
                    "required": ["hostname", "container"],
                },
                title="Check Container Status",
                readOnlyHint=True,
                destructiveHint=False,
                idempotentHint=False,
                openWorldHint=True,
            ),
            types.Tool(
                name="docker_find_containers_by_label",
                description="Find containers by label key-value pair (e.g., find traefik-enabled containers or containers with specific domains)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "hostname": {
                            "type": "string",
                            "description": f"Host to search (or 'all' for all hosts): {', '.join(self.container_hosts.keys())}",
                        },
                        "label_key": {
                            "type": "string",
                            "description": "Label key to search for (e.g., 'traefik.http.routers.web.rule', 'domain', 'app')",
                        },
                        "label_value": {
                            "type": "string",
                            "description": "Optional: Label value to match (substring match). If not provided, returns all containers with this key",
                        },
                    },
                    "required": ["label_key"],
                },
                title="Find Containers by Label",
                readOnlyHint=True,
                destructiveHint=False,
                idempotentHint=False,
                openWorldHint=True,
            ),
            types.Tool(
                name="docker_get_container_labels",
                description="Get all labels for a specific container",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "hostname": {
                            "type": "string",
                            "description": f"Host: {', '.join(self.container_hosts.keys())}",
                            "enum": list(self.container_hosts.keys()),
                        },
                        "container": {
                            "type": "string",
                            "description": "Container name",
                        },
                    },
                    "required": ["hostname", "container"],
                },
                title="Get Container Labels",
                readOnlyHint=True,
                destructiveHint=False,
                idempotentHint=False,
                openWorldHint=True,
            ),
        ]

    async def handle_tool(self, tool_name: str, arguments: dict | None) -> list[types.TextContent]:
        """Route tool calls to appropriate handler methods"""
        # Strip the docker_ prefix for routing to the original tool names
        name = tool_name.replace("docker_", "", 1) if tool_name.startswith("docker_") else tool_name

        # Map class tool names back to module-level tool names
        # docker_get_containers -> get_docker_containers
        if name.startswith("get_"):
            if not name.startswith("get_docker_") and not name.startswith("get_all_") and not name.startswith("get_container_"):
                name = f"get_docker_{name[4:]}"  # get_containers -> get_docker_containers
            elif name == "get_containers":
                name = "get_docker_containers"

        logger.info(f"[DockerMCPServer] Tool called: {tool_name} -> {name} with args: {arguments}")

        # Call the shared implementation with this instance's container_hosts
        return await handle_call_tool_impl(name, arguments, self.container_hosts)


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available container management tools"""
    return [
        types.Tool(
            name="get_docker_containers",
            description="Get containers on a specific host (works with both Docker and Podman)",
            inputSchema={
                "type": "object",
                "properties": {
                    "hostname": {
                        "type": "string",
                        "description": f"Host: {', '.join(CONTAINER_HOSTS.keys())}",
                        "enum": list(CONTAINER_HOSTS.keys()),
                    }
                },
                "required": ["hostname"],
            },
            title="Get Containers on Host",
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
        types.Tool(
            name="get_all_containers",
            description="Get all containers across all hosts",
            inputSchema={"type": "object", "properties": {}},
            title="Get All Containers",
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
        types.Tool(
            name="get_container_stats",
            description="Get CPU and memory stats for containers on a host",
            inputSchema={
                "type": "object",
                "properties": {
                    "hostname": {
                        "type": "string",
                        "description": f"Host: {', '.join(CONTAINER_HOSTS.keys())}",
                        "enum": list(CONTAINER_HOSTS.keys()),
                    }
                },
                "required": ["hostname"],
            },
            title="Get Container Stats",
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
        types.Tool(
            name="check_container",
            description="Check if a specific container is running on a host",
            inputSchema={
                "type": "object",
                "properties": {
                    "hostname": {
                        "type": "string",
                        "description": f"Host: {', '.join(CONTAINER_HOSTS.keys())}",
                        "enum": list(CONTAINER_HOSTS.keys()),
                    },
                    "container": {
                        "type": "string",
                        "description": "Container name to check",
                    },
                },
                "required": ["hostname", "container"],
            },
            title="Check Container Status",
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
        types.Tool(
            name="find_containers_by_label",
            description="Find containers by label key-value pair (e.g., find traefik-enabled containers or containers with specific domains)",
            inputSchema={
                "type": "object",
                "properties": {
                    "hostname": {
                        "type": "string",
                        "description": f"Host to search (or 'all' for all hosts): {', '.join(CONTAINER_HOSTS.keys())}",
                    },
                    "label_key": {
                        "type": "string",
                        "description": "Label key to search for (e.g., 'traefik.http.routers.web.rule', 'domain', 'app')",
                    },
                    "label_value": {
                        "type": "string",
                        "description": "Optional: Label value to match (substring match). If not provided, returns all containers with this key",
                    },
                },
                "required": ["label_key"],
            },
            title="Find Containers by Label",
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
        types.Tool(
            name="get_container_labels",
            description="Get all labels for a specific container",
            inputSchema={
                "type": "object",
                "properties": {
                    "hostname": {
                        "type": "string",
                        "description": f"Host: {', '.join(CONTAINER_HOSTS.keys())}",
                        "enum": list(CONTAINER_HOSTS.keys()),
                    },
                    "container": {
                        "type": "string",
                        "description": "Container name",
                    },
                },
                "required": ["hostname", "container"],
            },
            title="Get Container Labels",
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
    ]


async def handle_call_tool_impl(
    name: str, arguments: dict | None, container_hosts: Dict
) -> list[types.TextContent]:
    """Core tool execution logic that can be called by both class and module-level handlers"""
    try:
        if name == "get_docker_containers":
            default_hostname = (
                list(container_hosts.keys())[0]
                if container_hosts
                else "no-hosts-configured"
            )
            hostname = (
                arguments.get("hostname", default_hostname)
                if arguments
                else default_hostname
            )

            if hostname not in container_hosts:
                return [
                    types.TextContent(
                        type="text",
                        text=f"Error: Unknown host '{hostname}'. Valid hosts: {', '.join(container_hosts.keys())}",
                    )
                ]

            runtime = container_hosts[hostname]["runtime"]
            containers = await container_api_request(hostname, "/containers/json")

            if containers is None:
                return [
                    types.TextContent(
                        type="text",
                        text=f"Error: Could not connect to {runtime.capitalize()} API on {hostname}",
                    )
                ]

            output = f"=== {hostname.upper()} ({runtime.upper()}) ===\n\n"

            if not containers:
                output += "No containers running\n"
            else:
                for container in containers:
                    norm = normalize_container_info(container, runtime)

                    name_str = (
                        norm["Names"][0].lstrip("/") if norm["Names"] else "Unknown"
                    )
                    image = norm["Image"]
                    state = norm["State"]
                    status = norm["Status"]

                    # Format ports
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

                    # Show relevant labels if present
                    labels = norm.get("Labels", {})
                    if labels:
                        # Extract traefik and domain labels for quick reference
                        traefik_labels = {k: v for k, v in labels.items() if "traefik" in k.lower()}
                        domain_labels = {
                            k: v
                            for k, v in labels.items()
                            if any(d in k.lower() for d in ["domain", "host", "url"])
                        }

                        if traefik_labels or domain_labels:
                            output += "  Labels:\n"
                            for key, value in list(traefik_labels.items())[:3]:
                                # Truncate long values
                                display_value = value if len(str(value)) <= 50 else str(value)[:47] + "..."
                                output += f"    • {key}: {display_value}\n"
                            for key, value in list(domain_labels.items())[:2]:
                                display_value = value if len(str(value)) <= 50 else str(value)[:47] + "..."
                                output += f"    • {key}: {display_value}\n"

                    output += "\n"

            return [types.TextContent(type="text", text=output)]

        elif name == "get_all_containers":
            output = f"Total: ? containers\n\n=== ALL CONTAINER HOSTS ===\n\n"
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
                            name_str = (
                                norm["Names"][0].lstrip("/")
                                if norm["Names"]
                                else "Unknown"
                            )
                            image = norm["Image"]
                            host_output += f"  • {name_str} ({image})\n"
                    else:
                        host_output += "  No containers\n"
                else:
                    host_output += f"  Error\n"

                results.append(host_output)

            # Update total count
            output = (
                f"Total: {total_containers} containers\n\n=== ALL CONTAINER HOSTS ===\n\n"
                + "\n".join(results)
            )
            return [types.TextContent(type="text", text=output)]

        elif name == "get_container_stats":
            default_hostname = (
                list(container_hosts.keys())[0]
                if container_hosts
                else "no-hosts-configured"
            )
            hostname = (
                arguments.get("hostname", default_hostname)
                if arguments
                else default_hostname
            )

            if hostname not in container_hosts:
                return [
                    types.TextContent(
                        type="text", text=f"Error: Unknown host '{hostname}'"
                    )
                ]

            runtime = container_hosts[hostname]["runtime"]
            containers = await container_api_request(hostname, "/containers/json")

            if containers is None:
                return [
                    types.TextContent(
                        type="text",
                        text=f"Error: Could not connect to {runtime.capitalize()} API on {hostname}",
                    )
                ]

            output = f"=== STATS: {hostname.upper()} ===\n\n"

            # Stats endpoint differs between Docker and Podman
            stats_endpoint_template = "/containers/{}/stats?stream=false"

            for container in containers[:10]:  # Limit to 10 for performance
                norm = normalize_container_info(container, runtime)
                container_id = norm["Id"]
                name = norm["Names"][0].lstrip("/") if norm["Names"] else "Unknown"

                stats = await container_api_request(
                    hostname, stats_endpoint_template.format(container_id), timeout=10
                )

                if stats:
                    # Calculate CPU percentage
                    cpu_percent = 0.0
                    try:
                        cpu_stats = stats.get("cpu_stats", {})
                        precpu_stats = stats.get("precpu_stats", {})

                        cpu_delta = cpu_stats.get("cpu_usage", {}).get(
                            "total_usage", 0
                        ) - precpu_stats.get("cpu_usage", {}).get("total_usage", 0)
                        system_delta = cpu_stats.get(
                            "system_cpu_usage", 0
                        ) - precpu_stats.get("system_cpu_usage", 0)

                        num_cpus = len(
                            cpu_stats.get("cpu_usage", {}).get("percpu_usage", [])
                        )
                        if num_cpus == 0:
                            num_cpus = 1

                        if system_delta > 0 and cpu_delta > 0:
                            cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0
                    except Exception as e:
                        logger.debug(f"Error calculating CPU for {name}: {e}")

                    # Calculate memory usage
                    mem_usage = 0.0
                    mem_limit = 0.0
                    mem_percent = 0.0
                    try:
                        mem_stats = stats.get("memory_stats", {})
                        mem_usage = mem_stats.get("usage", 0) / (
                            1024**3
                        )  # Convert to GB
                        mem_limit = mem_stats.get("limit", 0) / (1024**3)

                        if mem_limit > 0:
                            mem_percent = (
                                mem_stats.get("usage", 0) / mem_stats.get("limit", 1)
                            ) * 100.0
                    except Exception as e:
                        logger.debug(f"Error calculating memory for {name}: {e}")

                    output += f"• {name}\n"
                    output += f"  CPU: {cpu_percent:.1f}%\n"
                    output += f"  Memory: {mem_usage:.2f}GB / {mem_limit:.2f}GB ({mem_percent:.1f}%)\n\n"
                else:
                    output += f"• {name}\n  Stats unavailable\n\n"

            return [types.TextContent(type="text", text=output)]

        elif name == "check_container":
            hostname = arguments.get("hostname", "") if arguments else ""
            container_name = arguments.get("container", "") if arguments else ""

            if not hostname or not container_name:
                return [
                    types.TextContent(
                        type="text",
                        text="Error: Both hostname and container name are required",
                    )
                ]

            runtime = container_hosts.get(hostname, {}).get("runtime", "docker")
            containers = await container_api_request(hostname, "/containers/json")

            if containers is None:
                return [
                    types.TextContent(
                        type="text",
                        text=f"Error: Could not connect to {runtime.capitalize()} API on {hostname}",
                    )
                ]

            for container in containers:
                norm = normalize_container_info(container, runtime)
                names = norm["Names"]

                # Check if container name matches (with or without leading /)
                for name in names:
                    clean_name = name.lstrip("/")
                    if clean_name == container_name or name == container_name:
                        output = f"✓ Container '{container_name}' is RUNNING on {hostname}\n"
                        output += f"  Image: {norm['Image']}\n"
                        output += f"  Status: {norm['Status']}\n"
                        output += f"  Runtime: {runtime}\n"

                        # Include labels if present
                        labels = norm.get("Labels", {})
                        if labels:
                            output += "\n" + format_labels_output(labels)

                        return [types.TextContent(type="text", text=output)]

            return [
                types.TextContent(
                    type="text",
                    text=f"✗ Container '{container_name}' is NOT running on {hostname}",
                )
            ]

        elif name == "find_containers_by_label":
            label_key = arguments.get("label_key", "") if arguments else ""
            label_value = arguments.get("label_value", "") if arguments else ""
            hostname_arg = arguments.get("hostname", "all") if arguments else "all"

            if not label_key:
                return [
                    types.TextContent(
                        type="text",
                        text="Error: label_key is required",
                    )
                ]

            # Determine which hosts to search
            hosts_to_search = (
                container_hosts.keys()
                if hostname_arg.lower() == "all"
                else [hostname_arg]
            )

            output = f"Searching for containers with label key: '{label_key}'\n"
            if label_value:
                output += f"Value filter: '{label_value}'\n"
            output += f"Hosts: {', '.join(hosts_to_search)}\n\n"

            results_found = False

            for hostname in hosts_to_search:
                if hostname not in container_hosts:
                    output += f"✗ Unknown host: {hostname}\n"
                    continue

                runtime = container_hosts[hostname]["runtime"]
                containers = await container_api_request(hostname, "/containers/json")

                if containers is None:
                    output += f"✗ Could not connect to {hostname}\n"
                    continue

                matching_containers = []

                for container in containers:
                    norm = normalize_container_info(container, runtime)
                    labels = norm.get("Labels", {})

                    # Check if label key exists
                    for key, value in labels.items():
                        if label_key.lower() in key.lower():
                            # If label_value provided, check if it matches (substring)
                            if label_value and label_value.lower() not in str(value).lower():
                                continue

                            matching_containers.append((key, value, norm))
                            results_found = True

                if matching_containers:
                    output += f"--- {hostname.upper()} ({runtime.upper()}) ---\n"
                    for label_key_found, label_value_found, norm in matching_containers:
                        name_str = (
                            norm["Names"][0].lstrip("/") if norm["Names"] else "Unknown"
                        )
                        output += f"• {name_str}\n"
                        output += f"  Label: {label_key_found}\n"
                        output += f"  Value: {label_value_found}\n"
                        output += f"  Image: {norm['Image']}\n\n"

            if not results_found:
                output += "No containers found matching the label criteria.\n"

            return [types.TextContent(type="text", text=output)]

        elif name == "get_container_labels":
            hostname = arguments.get("hostname", "") if arguments else ""
            container_name = arguments.get("container", "") if arguments else ""

            if not hostname or not container_name:
                return [
                    types.TextContent(
                        type="text",
                        text="Error: Both hostname and container name are required",
                    )
                ]

            if hostname not in container_hosts:
                return [
                    types.TextContent(
                        type="text",
                        text=f"Error: Unknown host '{hostname}'",
                    )
                ]

            runtime = container_hosts[hostname]["runtime"]
            containers = await container_api_request(hostname, "/containers/json")

            if containers is None:
                return [
                    types.TextContent(
                        type="text",
                        text=f"Error: Could not connect to {runtime.capitalize()} API on {hostname}",
                    )
                ]

            for container in containers:
                norm = normalize_container_info(container, runtime)
                names = norm["Names"]

                # Check if container name matches (with or without leading /)
                for name in names:
                    clean_name = name.lstrip("/")
                    if clean_name == container_name or name == container_name:
                        labels = norm.get("Labels", {})

                        output = f"Container: {container_name}\n"
                        output += f"Host: {hostname}\n"
                        output += f"Image: {norm['Image']}\n"
                        output += f"Status: {norm['Status']}\n\n"

                        if not labels:
                            output += "No labels configured for this container.\n"
                        else:
                            output += f"Total Labels: {len(labels)}\n\n"

                            # Group labels by prefix
                            label_groups = {}
                            for key, value in sorted(labels.items()):
                                prefix = key.split(".")[0] if "." in key else "other"
                                if prefix not in label_groups:
                                    label_groups[prefix] = []
                                label_groups[prefix].append((key, value))

                            # Display grouped labels
                            for prefix in sorted(label_groups.keys()):
                                output += f"{prefix.upper()}:\n"
                                for key, value in label_groups[prefix]:
                                    output += f"  {key}: {value}\n"
                                output += "\n"

                        return [types.TextContent(type="text", text=output)]

            return [
                types.TextContent(
                    type="text",
                    text=f"✗ Container '{container_name}' not found on {hostname}",
                )
            ]

        else:
            return [
                types.TextContent(type="text", text=f"Error: Unknown tool '{name}'")
            ]

    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}", exc_info=True)
        return [
            types.TextContent(type="text", text=f"Error executing {name}: {str(e)}")
        ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent]:
    """Handle tool execution requests (module-level wrapper for standalone mode)"""
    logger.info(f"Tool called: {name} with args: {arguments}")

    # For standalone mode, use the global CONTAINER_HOSTS
    if 'CONTAINER_HOSTS' not in globals():
        return [types.TextContent(type="text", text="Error: CONTAINER_HOSTS not initialized")]

    return await handle_call_tool_impl(name, arguments, CONTAINER_HOSTS)


async def main():
    """Run the MCP server"""
    logger.info("Starting Docker/Podman MCP Server...")
    logger.info(f"Configured hosts: {', '.join(CONTAINER_HOSTS.keys())}")

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="docker-info",
                server_version="2.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
