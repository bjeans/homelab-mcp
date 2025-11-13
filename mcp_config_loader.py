#!/usr/bin/env python3
"""
Shared configuration loader for MCP servers
Handles .env file loading with security hardening and allowlist validation
"""

import fnmatch
import logging
import os
import re
from pathlib import Path
from typing import Dict, Optional, Set

logger = logging.getLogger(__name__)


# Define allowed environment variables per MCP server
# Each server should pass its own allowlist to load_env_file()
COMMON_ALLOWED_ENV_VARS = {
    "ANSIBLE_INVENTORY_PATH",
}


def load_env_file(
    env_file_path: Optional[Path] = None,
    allowed_vars: Optional[Set[str]] = None,
    strict: bool = False,
) -> Dict[str, str]:
    """
    Load environment variables from .env file with security hardening.

    Args:
        env_file_path: Path to .env file (defaults to .env in script directory)
        allowed_vars: Set of allowed variable names (supports fnmatch patterns)
                     If None, all variables are allowed (legacy behavior)
        strict: If True, log warnings for variables not in allowlist

    Returns:
        Dict of loaded environment variables

    Example:
        allowed = COMMON_ALLOWED_ENV_VARS | {'OLLAMA_*', 'LITELLM_*'}
        config = load_env_file(allowed_vars=allowed, strict=True)
    """
    if env_file_path is None:
        env_file_path = Path(__file__).parent / ".env"

    loaded = {}

    if not env_file_path.exists():
        logger.debug(f".env file not found at {env_file_path}")
        return loaded

    logger.info(f"Loading configuration from {env_file_path}")

    try:
        with open(env_file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                # Parse key=value format
                if "=" not in line:
                    logger.warning(f"Skipping malformed line {line_num}: {line}")
                    continue

                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                # Strip quotes if present (handles both single and double quotes)
                if (value.startswith('"') and value.endswith('"')) or (
                    value.startswith("'") and value.endswith("'")
                ):
                    value = value[1:-1]

                # Validate key format (alphanumeric, underscore only)
                if not is_valid_env_var_name(key):
                    logger.warning(
                        f"Skipping invalid variable name at line {line_num}: {key}"
                    )
                    continue

                # Check allowlist if provided
                if allowed_vars is not None:
                    if not any(
                        fnmatch.fnmatch(key, pattern) for pattern in allowed_vars
                    ):
                        if strict:
                            logger.warning(
                                f"Ignoring non-allowed environment variable: {key}"
                            )
                        continue

                # Set the environment variable
                os.environ[key] = value
                loaded[key] = value
                logger.debug(
                    f"Loaded {key}={value[:20]}{'...' if len(value) > 20 else ''}"
                )

    except Exception as e:
        logger.error(f"Error loading .env file: {e}")

    return loaded


def is_valid_env_var_name(name: str) -> bool:
    """
    Validate environment variable name format.
    Must contain only alphanumeric characters and underscores, start with letter or underscore.

    Args:
        name: Variable name to validate

    Returns:
        True if valid, False otherwise
    """
    if not name:
        return False

    # First character must be letter or underscore
    if not (name[0].isalpha() or name[0] == "_"):
        return False

    # Rest must be alphanumeric or underscore
    return all(c.isalnum() or c == "_" for c in name)


def get_config(
    key: str, default: str = "", allowed_vars: Optional[Set[str]] = None
) -> str:
    """
    Get a configuration value from environment with optional allowlist check.

    Args:
        key: Environment variable name
        default: Default value if not found
        allowed_vars: Set of allowed variables to check against (security audit)

    Returns:
        Configuration value or default

    Raises:
        ValueError: If allowed_vars is provided and key is not allowed
    """
    if allowed_vars is not None:
        if not any(fnmatch.fnmatch(key, pattern) for pattern in allowed_vars):
            raise ValueError(f"Access to environment variable '{key}' is not allowed")

    return os.getenv(key, default)


def load_indexed_env_vars(
    prefix: str,
    name_suffix: str = "_NAME",
    target_suffix: str = "",
    logger_obj = None,
) -> dict:
    """
    Load indexed environment variables into a structured dict.
    
    Supports patterns like:
    - PING_TARGET1=value, PING_TARGET1_NAME=display_name
    - DOCKER_SERVER1_ENDPOINT=value, DOCKER_SERVER1_NAME=display_name (extracts "1" from "SERVER1")
    
    Args:
        prefix: Variable name prefix (e.g., "PING_TARGET", "DOCKER_", "PODMAN_")
        name_suffix: Suffix for display name variable (default: "_NAME")
        target_suffix: Suffix for target/endpoint variable (default: "" means no suffix)
        logger_obj: Optional logger instance for logging (uses print if None)
    
    Returns:
        Dict with structure:
        {
            "index": {
                "name": "display_name or None",
                "target": "value or None"
            }
        }
        Indexed items are sorted by numeric index.
    
    Example:
        result = load_indexed_env_vars("PING_TARGET", name_suffix="_NAME")
        # With PING_TARGET1=8.8.8.8, PING_TARGET1_NAME=Google
        # Returns: {"1": {"name": "Google", "target": "8.8.8.8"}}
        
        result = load_indexed_env_vars("DOCKER_", name_suffix="_NAME", target_suffix="_ENDPOINT")
        # With DOCKER_SERVER1_ENDPOINT=192.168.1.100:2375, DOCKER_SERVER1_NAME=MyDocker
        # Returns: {"1": {"name": "MyDocker", "target": "192.168.1.100:2375"}}
    """
    targets_by_index = {}
    
    log = logger_obj.info if logger_obj else print
    log_warning = logger_obj.warning if logger_obj else print
    
    # Collect all matching environment variables
    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue
        
        # Extract suffix after prefix
        suffix = key[len(prefix):]
        
        # Extract numeric index from the suffix (handles patterns like SERVER1_NAME, SERVER1_ENDPOINT, 1, etc.)
        # Look for the first consecutive digits in the suffix
        index_match = re.search(r'(\d+)', suffix)
        if not index_match:
            continue
        
        index = index_match.group(1)
        
        # Check for _NAME suffix
        if suffix.endswith(name_suffix):
            targets_by_index.setdefault(index, {"name": None, "target": None})
            targets_by_index[index]["name"] = value
            log(f"Found {prefix}*{index}{name_suffix}: {value}")
        
        # Check for target/value with target_suffix (if specified)
        elif target_suffix and suffix.endswith(target_suffix):
            targets_by_index.setdefault(index, {"name": None, "target": None})
            targets_by_index[index]["target"] = value
            log(f"Loaded {prefix}*{index}{target_suffix}: {value}")
        
        # Check for plain value (no suffix required)
        elif not target_suffix and not suffix.endswith(name_suffix):
            targets_by_index.setdefault(index, {"name": None, "target": None})
            targets_by_index[index]["target"] = value
            log(f"Loaded {prefix}*{index}: {value}")
    
    # Sort by numeric index
    sorted_targets = {}
    for index in sorted(targets_by_index.keys(), key=lambda x: int(x)):
        sorted_targets[index] = targets_by_index[index]
    
    return sorted_targets


__all__ = [
    "load_env_file",
    "is_valid_env_var_name",
    "get_config",
    "load_indexed_env_vars",
    "COMMON_ALLOWED_ENV_VARS",
]
