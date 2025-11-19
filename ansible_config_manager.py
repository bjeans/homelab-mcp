#!/usr/bin/env python3
"""
Ansible-based configuration manager for MCP servers
Properly integrates with Ansible's inventory and variable resolution system

This module eliminates manual YAML parsing and hostname duplication by using
the official Ansible Python library.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

# Import Ansible inventory management
try:
    from ansible.inventory.manager import InventoryManager
    from ansible.parsing.dataloader import DataLoader
    from ansible.vars.manager import VariableManager
    ANSIBLE_AVAILABLE = True
except ImportError:
    ANSIBLE_AVAILABLE = False

logger = logging.getLogger(__name__)


class AnsibleConfigManager:
    """Manages configuration using Ansible's official inventory system."""

    def __init__(
        self,
        inventory_path: Optional[str] = None,
        logger_obj: Optional[logging.Logger] = None,
    ):
        """Initialize the Ansible config manager."""
        if logger_obj:
            global logger
            logger = logger_obj

        self.inventory_path = inventory_path or os.getenv("ANSIBLE_INVENTORY_PATH", "")
        self.loader = None
        self.inventory = None
        self.variable_manager = None
        self._group_cache = {}

        if not ANSIBLE_AVAILABLE:
            logger.warning("Ansible not available. Install with: pip install ansible")
            return

        if not self.inventory_path:
            logger.warning("No inventory path provided")
            return

        try:
            self._initialize_ansible()
        except Exception as e:
            logger.error(f"Failed to initialize Ansible: {e}")

    def _initialize_ansible(self):
        """Initialize Ansible loader, inventory, and variable manager."""
        if not ANSIBLE_AVAILABLE or not self.inventory_path:
            return

        try:
            self.loader = DataLoader()
            self.loader.set_basedir(str(Path(self.inventory_path).parent))
            self.inventory = InventoryManager(
                loader=self.loader, sources=self.inventory_path
            )
            self.variable_manager = VariableManager(
                loader=self.loader, inventory=self.inventory
            )

            logger.info(f"Loaded Ansible inventory from: {self.inventory_path}")
            logger.info(f"Hosts: {len(self.inventory.get_hosts())}, Groups: {len(self.inventory.groups)}")

        except Exception as e:
            logger.error(f"Error initializing Ansible: {e}")
            self.inventory = None
            self.variable_manager = None

    def is_available(self) -> bool:
        """Check if Ansible inventory is properly initialized."""
        return ANSIBLE_AVAILABLE and self.inventory is not None

    def get_group_hosts(
        self,
        group_name: str,
        include_children: bool = True,
        resolve_ips: bool = True,
    ) -> Dict[str, str]:
        """
        Get hosts from a group with automatic IP resolution.

        Args:
            group_name: Name of the Ansible group
            include_children: Include hosts from child groups
            resolve_ips: Resolve hostnames to IP addresses

        Returns:
            Dict of {display_name: ip_address}
        """
        if not self.is_available():
            logger.error("Ansible inventory not available")
            return {}

        cache_key = f"{group_name}:{include_children}:{resolve_ips}"
        if cache_key in self._group_cache:
            return self._group_cache[cache_key]

        try:
            result = {}

            if group_name not in self.inventory.groups:
                logger.warning(f"Group not found: {group_name}")
                return {}

            group = self.inventory.groups[group_name]
            hosts_to_process = set(group.get_hosts())

            if include_children:
                for child_group in group.get_descendants():
                    hosts_to_process.update(child_group.get_hosts())

            logger.info(f"Processing {len(hosts_to_process)} hosts from {group_name}")

            for host in hosts_to_process:
                host_vars = self.variable_manager.get_vars(host=host)
                display_name = host.name.split(".")[0].lower().replace("_", "-")

                if resolve_ips:
                    ip = host_vars.get("ansible_host", host.name)
                else:
                    ip = host.name

                result[display_name] = str(ip)
                logger.debug(f"Added {display_name} -> {ip}")

            self._group_cache[cache_key] = result
            logger.info(f"Loaded {len(result)} hosts from group {group_name}")
            return result

        except Exception as e:
            logger.error(f"Error getting hosts from group {group_name}: {e}")
            return {}

    def get_host_variable(
        self, hostname: str, variable_name: str, default: str = ""
    ) -> str:
        """Get a host variable, respecting Ansible variable precedence."""
        if not self.is_available():
            return default

        try:
            all_hosts = self.inventory.get_hosts()
            matching_host = None

            for host in all_hosts:
                if host.name == hostname or host.name.startswith(hostname + "."):
                    matching_host = host
                    break

            if not matching_host:
                logger.warning(f"Host not found: {hostname}")
                return default

            host_vars = self.variable_manager.get_vars(host=matching_host)
            value = host_vars.get(variable_name, default)

            logger.debug(f"Got {variable_name}={value} for host {hostname}")
            return str(value) if value else default

        except Exception as e:
            logger.error(f"Error getting variable {variable_name} for {hostname}: {e}")
            return default

    def get_group_variable(self, group_name: str, variable_name: str, default: str = "") -> str:
        """Get a group-level variable."""
        if not self.is_available():
            return default

        try:
            if group_name not in self.inventory.groups:
                logger.warning(f"Group not found: {group_name}")
                return default

            group = self.inventory.groups[group_name]
            group_vars = group.get_vars()
            value = group_vars.get(variable_name, default)

            logger.debug(f"Got {variable_name}={value} for group {group_name}")
            return str(value) if value else default

        except Exception as e:
            logger.error(f"Error getting variable {variable_name} for group {group_name}: {e}")
            return default

    def get_inventory_summary(self) -> Dict:
        """Get summary of inventory contents."""
        if not self.is_available():
            return {}

        try:
            return {
                "hosts": len(self.inventory.get_hosts()),
                "groups": len(self.inventory.groups),
                "group_names": sorted(list(self.inventory.groups.keys())),
            }
        except Exception as e:
            logger.error(f"Error getting inventory summary: {e}")
            return {}

    def get_all_hosts_with_inheritance(self) -> Dict:
        """
        Get all hosts and groups with proper variable inheritance.
        
        Implements two-pass algorithm:
        1. First pass: Collect group variables
        2. Second pass: Process groups with inherited variables from parent groups
        
        Returns:
            Dict with structure: {"hosts": {...}, "groups": {...}}
            Each host includes merged variables from its groups
        """
        if not self.is_available():
            return {"hosts": {}, "groups": {}}

        try:
            hosts = {}
            groups = {}
            group_vars = {}

            def collect_group_vars(group_obj, parent_groups=None):
                """First pass: collect all group variables"""
                if parent_groups is None:
                    parent_groups = []

                group_name = group_obj.name
                current_groups = parent_groups + [group_name]

                # Store group vars
                if group_name not in group_vars:
                    group_vars[group_name] = {}

                group_vars[group_name] = group_obj.get_vars().copy()

                # Recursively process children
                for child_group in group_obj.get_descendants():
                    if child_group.name not in group_vars:
                        collect_group_vars(child_group, current_groups)

            def process_group(group_obj, parent_groups=None, inherited_vars=None):
                """Second pass: process groups with inherited vars"""
                if parent_groups is None:
                    parent_groups = []
                if inherited_vars is None:
                    inherited_vars = {}

                group_name = group_obj.name
                current_groups = parent_groups + [group_name]

                # Merge inherited vars with this group's vars
                merged_vars = inherited_vars.copy()
                if group_name in group_vars:
                    merged_vars.update(group_vars[group_name])

                # Process hosts in this group
                for host in group_obj.get_hosts():
                    if host.name not in hosts:
                        hosts[host.name] = {"groups": [], "vars": {}}

                    # Add groups
                    if group_name not in hosts[host.name]["groups"]:
                        hosts[host.name]["groups"].append(group_name)

                    # Merge vars: group vars first, then host vars override
                    hosts[host.name]["vars"].update(merged_vars)
                    host_vars = self.variable_manager.get_vars(host=host)
                    hosts[host.name]["vars"].update(host_vars)

                # Track group membership
                if group_name not in groups:
                    groups[group_name] = set()

                # Add hosts to group tracking
                for host in group_obj.get_hosts():
                    groups[group_name].add(host.name)

                # Process child groups with accumulated vars
                for child_group in group_obj.child_groups:
                    process_group(child_group, current_groups, merged_vars)
                    # Also add child group's hosts to parent group
                    if child_group.name in groups:
                        groups[group_name].update(groups[child_group.name])

            # Start with 'all' group
            all_group = self.inventory.groups.get("all")
            if all_group:
                # First pass: collect group vars
                collect_group_vars(all_group)

                # Second pass: process groups
                process_group(all_group)

            # Convert group sets to lists for JSON serialization
            groups_list = {k: list(v) for k, v in groups.items()}

            logger.info(
                f"Loaded {len(hosts)} hosts and {len(groups_list)} groups with inheritance"
            )
            return {"hosts": hosts, "groups": groups_list}

        except Exception as e:
            logger.error(f"Error getting all hosts with inheritance: {e}", exc_info=True)
            return {"hosts": {}, "groups": {}}

    def get_docker_hosts(self) -> List[str]:
        """
        Get hostnames with Docker or Podman API configured.

        Returns:
            Sorted list of normalized hostnames that have docker_api_port or podman_api_port defined
        """
        if not self.is_available():
            return []

        try:
            hosts = set()
            all_hosts = self.inventory.get_hosts()

            for host in all_hosts:
                host_vars = self.variable_manager.get_vars(host=host)
                # Check for docker_api_port or podman_api_port
                if host_vars.get("docker_api_port") or host_vars.get("podman_api_port"):
                    # Normalize hostname: split on '.', lowercase, replace '_' with '-'
                    normalized = host.name.split(".")[0].lower().replace("_", "-")
                    hosts.add(normalized)

            return sorted(list(hosts))
        except Exception as e:
            logger.error(f"Error getting Docker hosts: {e}")
            return []

    def get_ollama_hosts(self) -> List[str]:
        """
        Get hostnames in the ollama_servers group.

        Returns:
            Sorted list of normalized hostnames from ollama_servers group
        """
        if not self.is_available():
            return []

        try:
            group_name = "ollama_servers"
            if group_name not in self.inventory.groups:
                logger.debug(f"Group '{group_name}' not found in inventory")
                return []

            group = self.inventory.groups[group_name]
            hosts = set()

            for host in group.get_hosts():
                # Normalize hostname: split on '.', lowercase, replace '_' with '-'
                normalized = host.name.split(".")[0].lower().replace("_", "-")
                hosts.add(normalized)

            return sorted(list(hosts))
        except Exception as e:
            logger.error(f"Error getting Ollama hosts: {e}")
            return []

    def get_pihole_hosts(self) -> List[str]:
        """
        Get hostnames with Pi-hole configured.

        Returns:
            Sorted list of normalized hostnames that have pihole_url defined
        """
        if not self.is_available():
            return []

        try:
            hosts = set()
            all_hosts = self.inventory.get_hosts()

            for host in all_hosts:
                host_vars = self.variable_manager.get_vars(host=host)
                # Check for pihole_url variable
                if host_vars.get("pihole_url"):
                    # Normalize hostname: split on '.', lowercase, replace '_' with '-'
                    normalized = host.name.split(".")[0].lower().replace("_", "-")
                    hosts.add(normalized)

            return sorted(list(hosts))
        except Exception as e:
            logger.error(f"Error getting Pi-hole hosts: {e}")
            return []

    def get_ups_hosts(self) -> List[str]:
        """
        Get hostnames in the nut_servers group (Network UPS Tools).

        Returns:
            Sorted list of normalized hostnames from nut_servers group
        """
        if not self.is_available():
            return []

        try:
            group_name = "nut_servers"
            if group_name not in self.inventory.groups:
                logger.debug(f"Group '{group_name}' not found in inventory")
                return []

            group = self.inventory.groups[group_name]
            hosts = set()

            for host in group.get_hosts():
                # Normalize hostname: split on '.', lowercase, replace '_' with '-'
                normalized = host.name.split(".")[0].lower().replace("_", "-")
                hosts.add(normalized)

            return sorted(list(hosts))
        except Exception as e:
            logger.error(f"Error getting UPS hosts: {e}")
            return []

    def get_all_groups(self) -> List[str]:
        """
        Get all Ansible group names.

        Returns:
            Sorted list of all group names in the inventory
        """
        if not self.is_available():
            return []

        try:
            # Get all group names from the inventory
            group_names = sorted(list(self.inventory.groups.keys()))
            logger.debug(f"Found {len(group_names)} groups in inventory")
            return group_names
        except Exception as e:
            logger.error(f"Error getting all groups: {e}")
            return []

    def get_hosts_by_capability(self, capability: str) -> List[str]:
        """
        Generic method to get hosts with a specific variable defined.

        Args:
            capability: Variable name to check for (e.g., 'docker_api_port', 'pihole_url')

        Returns:
            Sorted list of normalized hostnames that have the specified variable
        """
        if not self.is_available():
            return []

        try:
            hosts = set()
            all_hosts = self.inventory.get_hosts()

            for host in all_hosts:
                host_vars = self.variable_manager.get_vars(host=host)
                if host_vars.get(capability):
                    # Normalize hostname: split on '.', lowercase, replace '_' with '-'
                    normalized = host.name.split(".")[0].lower().replace("_", "-")
                    hosts.add(normalized)

            return sorted(list(hosts))
        except Exception as e:
            logger.error(f"Error getting hosts by capability '{capability}': {e}")
            return []

    def clear_cache(self):
        """Clear internal cache."""
        self._group_cache.clear()
        logger.info("Cleared inventory cache")


def get_group_hosts_fallback(
    inventory_path: str, group_name: str, logger_obj: Optional[logging.Logger] = None
) -> Dict[str, str]:
    """Fallback method using manual YAML parsing."""
    import yaml

    if logger_obj:
        log = logger_obj.info
        log_warn = logger_obj.warning
    else:
        log = print
        log_warn = print

    if not Path(inventory_path).exists():
        log_warn(f"Inventory file not found: {inventory_path}")
        return {}

    try:
        with open(inventory_path, "r") as f:
            inventory = yaml.safe_load(f)
    except Exception as e:
        log_warn(f"Error loading inventory: {e}")
        return {}

    def find_group(data, target_name):
        if isinstance(data, dict):
            if target_name in data:
                return data[target_name]
            for value in data.values():
                if isinstance(value, dict):
                    found = find_group(value, target_name)
                    if found:
                        return found
        return None

    def get_hosts_from_group(group_data, inherited_vars=None):
        inherited_vars = inherited_vars or {}
        hosts_found = []
        current_vars = {**inherited_vars, **group_data.get("vars", {})}

        if "hosts" in group_data:
            for hostname, host_vars in group_data["hosts"].items():
                merged_vars = {**current_vars, **(host_vars or {})}
                hosts_found.append((hostname, merged_vars))

        if "children" in group_data:
            for child_name, child_data in group_data["children"].items():
                if not child_data or (not child_data.get("hosts") and not child_data.get("children")):
                    actual_child_group = find_group(inventory, child_name)
                    if actual_child_group:
                        hosts_found.extend(get_hosts_from_group(actual_child_group, current_vars))
                else:
                    hosts_found.extend(get_hosts_from_group(child_data, current_vars))

        return hosts_found

    group = find_group(inventory, group_name)
    if not group:
        log_warn(f"Group not found: {group_name}")
        return {}

    hosts_list = get_hosts_from_group(group)
    result = {}

    for hostname, host_vars in hosts_list:
        display_name = hostname.split(".")[0].lower().replace("_", "-")
        ip = host_vars.get("ansible_host", hostname.split(".")[0])
        result[display_name] = ip
        log(f"Added {display_name} -> {ip}")

    return result


def load_group_hosts(
    group_name: str,
    inventory_path: Optional[str] = None,
    logger_obj: Optional[logging.Logger] = None,
) -> Dict[str, str]:
    """High-level function to load hosts from a group."""
    if inventory_path is None:
        inventory_path = os.getenv("ANSIBLE_INVENTORY_PATH", "")

    if not inventory_path:
        if logger_obj:
            logger_obj.error("No inventory path provided")
        return {}

    if ANSIBLE_AVAILABLE:
        manager = AnsibleConfigManager(inventory_path, logger_obj)
        if manager.is_available():
            return manager.get_group_hosts(group_name)

    if logger_obj:
        logger_obj.info("Falling back to manual YAML parsing")

    return get_group_hosts_fallback(inventory_path, group_name, logger_obj)


__all__ = [
    "AnsibleConfigManager",
    "load_group_hosts",
    "get_group_hosts_fallback",
    "ANSIBLE_AVAILABLE",
]