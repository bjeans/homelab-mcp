#!/usr/bin/env python3
"""
Environment Variable Allowlists for All MCP Servers
This file documents exactly which environment variables each MCP server is allowed to load.

Use this as reference when adding new environment variables to .env file.
"""

from mcp_config_loader import COMMON_ALLOWED_ENV_VARS

# Per-server allowlists as of refactoring
ALLOWLISTS = {
    'ollama_mcp.py': COMMON_ALLOWED_ENV_VARS | {
        'OLLAMA_PORT',
        'LITELLM_HOST',
        'LITELLM_PORT',
        'OLLAMA_*',  # Pattern: OLLAMA_SERVER1, OLLAMA_CUSTOM_HOST, etc.
    },
    
    'docker_mcp_podman.py': COMMON_ALLOWED_ENV_VARS | {
        'DOCKER_*',   # Pattern: DOCKER_HOST, DOCKER_PORT, etc.
        'PODMAN_*',   # Pattern: PODMAN_HOST, PODMAN_PORT, etc.
    },
    
    'pihole_mcp.py': COMMON_ALLOWED_ENV_VARS | {
        'PIHOLE_*',   # Pattern: PIHOLE_HOST, PIHOLE_PASSWORD, etc.
    },
    
    'unifi_mcp_optimized.py': COMMON_ALLOWED_ENV_VARS | {
        'UNIFI_HOST',
        'UNIFI_API_KEY',
    },
    
    'ping_mcp_server.py': COMMON_ALLOWED_ENV_VARS | {
        'PING_*',     # Reserved for future ping-specific variables
    },
    
    'ansible_mcp_server.py': COMMON_ALLOWED_ENV_VARS,
    # Primarily uses ANSIBLE_INVENTORY_PATH from common
}

if __name__ == '__main__':
    # Print allowlists for reference
    print("=" * 70)
    print("MCP SERVER ENVIRONMENT VARIABLE ALLOWLISTS")
    print("=" * 70)
    
    for server, allowed_vars in ALLOWLISTS.items():
        print(f"\n{server}:")
        print("-" * 70)
        for var in sorted(allowed_vars):
            print(f"  • {var}")
        print(f"  Total: {len(allowed_vars)} allowed patterns")

