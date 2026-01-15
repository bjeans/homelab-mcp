# Claude Development Guide for Homelab MCP

## Project Overview

**Repository:** <https://github.com/bjeans/homelab-mcp>
**Docker Hub:** <https://hub.docker.com/r/bjeans/homelab-mcp>
**Version:** 3.0.0 (Released: 2026-01-14)
**License:** MIT
**Purpose:** Open-source MCP servers for homelab infrastructure management through Claude Desktop

**⚠️ Breaking Changes in v3.0:** See [MIGRATION_V3.md](MIGRATION_V3.md) for upgrade guide.

This project provides real-time monitoring and control of homelab infrastructure through 7 specialized MCP servers, including Docker/Podman containers, Ollama AI models, Pi-hole DNS, Unifi networks, UPS monitoring, and Ansible inventory management via the Model Context Protocol.

**Deployment Options:**
- Native Python installation (recommended for development)
- Docker container from Docker Hub: `bjeans/homelab-mcp:latest` (recommended for production)
- Docker build from source (for customization)

## Core Philosophy

1. **Security First** - Never commit credentials, IPs, or sensitive data
2. **Configuration as Code** - All settings via environment variables or Ansible inventory
3. **User Privacy** - All example files use placeholder data
4. **Production-Grade** - Code quality suitable for critical infrastructure
5. **Open Source** - Community-friendly, well-documented, MIT licensed

## Project Structure

```text
homelab-mcp/
├── MCP Servers (7 production servers)
│   ├── ansible_mcp_server.py          # Ansible inventory queries
│   ├── docker_mcp_podman.py           # Docker/Podman container monitoring
│   ├── ollama_mcp.py                  # Ollama AI model management
│   ├── pihole_mcp.py                  # Pi-hole DNS monitoring
│   ├── unifi_mcp_optimized.py         # Unifi network device monitoring
│   ├── ups_mcp_server.py              # UPS/NUT monitoring
│   └── ping_mcp_server.py             # Network connectivity testing
│
├── Unified Server
│   ├── homelab_unified_mcp.py         # Combines all 7 servers
│   ├── mcp_config_loader.py           # Environment variable security
│   └── mcp_error_handler.py           # Centralized error handling
│
├── Configuration & Examples
│   ├── .env.example                   # Configuration template (gitignored)
│   ├── ansible_hosts.example.yml      # Ansible inventory example (gitignored)
│   └── ansible_config_manager.py      # Centralized config loader
│
└── Documentation
    ├── README.md                      # User documentation
    ├── MIGRATION_V3.md                # v2.x → v3.0 upgrade guide
    ├── CONTRIBUTING.md                # Contribution guide & development workflows
    ├── DOCKER.md                      # Docker deployment
    ├── SECURITY.md                    # Security guidelines
    └── CHANGELOG.md                   # Version history
```

## Architecture Patterns

### FastMCP Decorator Pattern (v3.0+)

All servers use **FastMCP's decorator pattern** for simple, pythonic tool definitions. No classes or boilerplate needed!

#### 1. Basic MCP Server Structure

```python
#!/usr/bin/env python3
"""
UPS MCP Server v3.0 (FastMCP)
Provides UPS monitoring via NUT (Network UPS Tools)
"""

import logging
import os
import sys
from pathlib import Path

from fastmcp import FastMCP
from mcp_config_loader import load_env_file

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("UPS Monitor")

# Load environment variables
SCRIPT_DIR = Path(__file__).parent
ENV_FILE = SCRIPT_DIR / ".env"

# Only load .env if NOT in unified mode (to avoid duplicate loading)
if not os.getenv("MCP_UNIFIED_MODE"):
    load_env_file(ENV_FILE, allowed_vars={"UPS_*", "NUT_*"}, strict=True)

# Service-specific helper functions
def _load_ups_hosts():
    """Load UPS hosts from Ansible inventory"""
    # Lazy import - only load Ansible when needed (avoids FastMCP import hook conflict)
    from ansible_config_manager import AnsibleConfigManager
    # Implementation here
    ...
```

#### 2. Adding Tools with @mcp.tool() Decorator

```python
from mcp import types

# Simple tool with annotations
@mcp.tool(
    annotations=types.ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=False,  # Status changes over time
        openWorldHint=True,
    )
)
def ups_get_status() -> str:
    """Get UPS status from all configured NUT servers"""
    ups_hosts = _load_ups_hosts()

    if not ups_hosts:
        return "No UPS hosts configured"

    output = "=== UPS STATUS ===\n\n"
    for host, config in ups_hosts.items():
        # Query UPS status
        ...
    return output


# Tool with parameters and type hints
@mcp.tool(
    annotations=types.ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    )
)
def ups_get_details(host: str, ups_name: str = "") -> str:
    """
    Get detailed UPS information from specific NUT server

    Args:
        host: Hostname of the NUT server to query
        ups_name: Optional specific UPS name (default: first UPS on host)
    """
    ups_hosts = _load_ups_hosts()

    if host not in ups_hosts:
        return f"Unknown host: {host}"

    # Query UPS details
    ...
    return output


# Run server
if __name__ == "__main__":
    mcp.run()
```

**Key Points:**
- ✅ Use `@mcp.tool()` decorator on any function
- ✅ Type hints automatically generate MCP schemas
- ✅ Docstrings become tool descriptions
- ✅ Both sync and async functions supported
- ✅ No manual schema definitions needed
- ✅ Tool annotations provide behavioral hints to Claude

#### 3. Tool Annotations (MCP Behavioral Hints)

All tools should include `ToolAnnotations` to provide behavioral hints to MCP clients:

| Hint | Purpose | When to Use |
|------|---------|-------------|
| `readOnlyHint` | Tool only reads data, never modifies | ✅ All monitoring operations<br>❌ Any mutating operations |
| `destructiveHint` | Tool may delete/destroy data | ❌ All homelab-mcp tools (monitoring only)<br>✅ Would be True for delete/destroy operations |
| `idempotentHint` | Same inputs → same outputs | ✅ Inventory queries (stable data)<br>❌ Runtime status (time-varying data) |
| `openWorldHint` | Interacts with external systems | ✅ All tools (query external services)<br>❌ Pure computation tools |

**All 39 tools** across 7 servers in homelab-mcp include proper annotations.

#### 4. Unified Server Composition

The unified server uses **FastMCP's native composition** - no manual wrapper functions needed!

```python
#!/usr/bin/env python3
"""
Homelab Unified MCP Server v3.0 (FastMCP)
Combines all 7 sub-servers using FastMCP's native composition
"""

from fastmcp import FastMCP
from mcp_config_loader import load_env_file

# Initialize unified server
mcp = FastMCP("Homelab Unified")

# Load environment once for all servers
load_env_file(ENV_FILE, allowed_vars=UNIFIED_ALLOWED_VARS, strict=True)
os.environ["MCP_UNIFIED_MODE"] = "1"


def compose_servers():
    """Compose all sub-servers into unified server"""
    # Import sub-servers (each has its own mcp instance with decorated tools)
    import ansible_mcp_server
    import docker_mcp_podman
    import ups_mcp_server
    # ... etc

    # Collect sub-servers
    subservers = {
        'ansible': ansible_mcp_server.mcp,
        'docker': docker_mcp_podman.mcp,
        'ups': ups_mcp_server.mcp,
        # ... etc
    }

    # Compose tools from all sub-servers
    for server_name, server_mcp in subservers.items():
        if hasattr(server_mcp, '_tool_manager'):
            tools = server_mcp._tool_manager._tools
            for tool_name, tool in tools.items():
                mcp.add_tool(tool)

    logger.info("All sub-servers composed successfully")


# Compose at module import time
compose_servers()
```

**Key Benefits:**
- ✅ Only **~105 lines** vs 500+ with manual wrappers
- ✅ No parameter duplication or signature mismatches
- ✅ FastMCP handles tool registration automatically
- ✅ Each sub-server works standalone or in unified mode
- ✅ Single source of truth for each tool

### Why FastMCP?

**Advantages over Standard MCP SDK:**

| Feature | Standard MCP SDK | FastMCP |
|---------|-----------------|---------|
| **Code Volume** | Manual schema definitions | 38% reduction |
| **Type Safety** | Manual schema validation | Automatic from type hints |
| **Tool Definition** | Class methods + decorators | Single `@mcp.tool()` decorator |
| **Async Support** | Manual async handling | Native async/await support |
| **Transports** | stdio only (default) | stdio, HTTP, SSE |
| **Composition** | Manual wrapper functions | Native `add_tool()` method |

**Development Speed:**
- Standard SDK: ~100 lines per tool (class + schema + handler)
- FastMCP: ~10-20 lines per tool (decorator + implementation)

### Lazy Import Pattern (v3.0+)

All servers use **lazy imports** for Ansible to avoid import hook conflicts with FastMCP:

```python
from fastmcp import FastMCP  # FastMCP imported at module level

def _load_config():
    # Ansible imported lazily when function is first called
    from ansible_config_manager import AnsibleConfigManager
    manager = AnsibleConfigManager(...)
```

**Why This Works:**
- At module import time: Only FastMCP is imported
- At runtime (first tool call): Ansible is imported inside the function
- No import hook conflict because they never execute at the same time
- Caching ensures Ansible is only imported once per process

**Benefits:**
- ✅ Import order is flexible - no more conflicts
- ✅ `uvx fastmcp inspect` works correctly on all servers
- ✅ All Ansible functionality preserved (nested groups, variable inheritance)
- ✅ Performance identical after first load

### Configuration Hierarchy

1. **Ansible Inventory** (Primary) - Single source of truth for infrastructure
   - Set via `ANSIBLE_INVENTORY_PATH` environment variable
   - Contains all host configurations and group definitions
   - Example: `/path/to/ansible_hosts.yml`

2. **Environment Variables** (Fallback) - `.env` file for service-specific config
   - Never committed to git (use `.gitignore`)
   - Created from `.env.example` template
   - Used when host not in Ansible inventory

3. **Defaults** (Last resort) - Hardcoded fallbacks in source code
   - Minimal, for development/testing only

## Development Workflows

### Adding a New MCP Server

**See [CONTRIBUTING.md - Adding a New MCP Server](CONTRIBUTING.md#adding-a-new-mcp-server) for complete step-by-step guide with FastMCP examples.**

Quick overview:
1. Copy template server file (e.g., `cp pihole_mcp.py minio_mcp.py`)
2. Define tools with `@mcp.tool()` decorators
3. Use lazy imports for Ansible: `from ansible_config_manager import ...` inside functions
4. Add Ansible host group to `ansible_hosts.yml`
5. Update `.env.example` with environment variables
6. Update documentation (README.md, CHANGELOG.md)
7. Update Dockerfile (see CONTRIBUTING.md for Docker integration)
8. Test standalone and unified modes
9. Run security checks: `python helpers/pre_publish_check.py`

### Modifying Existing Server

1. Read the server file completely
2. Add new tool with `@mcp.tool()` decorator
3. Include proper tool annotations
4. Use lazy imports for Ansible if needed
5. Test standalone and unified modes
6. Update documentation
7. Run pre_publish_check.py

## Key Technical Decisions

### Why Ansible Inventory as Primary Config?
- Users already manage infrastructure with Ansible
- Single source of truth for all host details
- Reduces duplication across MCP servers
- Easier to keep configuration in sync

### Why Individual Server Files?
- Easier to maintain and debug
- Users can enable only what they need
- Clearer separation of concerns
- Simpler dependency management

### Why Python?
- Native MCP SDK support
- Strong async/await support
- Rich ecosystem for API clients
- Familiar to sysadmins and developers

### Why No Database?
- All data fetched in real-time from services
- Reduces complexity and maintenance
- Ensures data is always current
- No state synchronization issues

## Common AI Assistant Tasks

### "Add feature X to server Y"
1. Read the server file completely
2. Understand current tool structure
3. Add new tool following existing patterns
4. Update docstrings and error handling
5. Include proper tool annotations
6. Test thoroughly with real service

### "Debug connection issue"
1. Check `.env.example` for required variables
2. Verify error handling in server code
3. Test API endpoint independently
4. Check firewall/network access
5. Validate credentials format

### "Update documentation"
1. Update inline docstrings first
2. Update README.md server section
3. Update CHANGELOG.md with changes
4. Consider if SECURITY.md or MIGRATION_V3.md need updates

## Testing & Validation

### Quick Validation
```bash
# Before submitting changes
python {service}_mcp_server.py        # Test standalone mode
python homelab_unified_mcp.py         # Test unified mode
python helpers/pre_publish_check.py   # Run security checks

# FastMCP inspection (validates configuration)
./venv/bin/fastmcp inspect --skip-env  # Should show Tools: 39
```

### Troubleshooting Common Issues

**MCP tools don't appear in Claude Desktop:**
- Restart Claude Desktop (required after code changes)
- Check that `MCP_UNIFIED_MODE` env var is set correctly
- Verify `claude_desktop_config.json` path is correct

**"No Ansible inventory found" error:**
- Set `ANSIBLE_INVENTORY_PATH` in `.env`
- Path should point to your `ansible_hosts.yml`
- Verify file exists: `ls -la $ANSIBLE_INVENTORY_PATH`

**"Connection timeout" to service:**
- Check firewall allows connection to service port
- Verify service is running: `netstat -an | grep PORT`
- Test connectivity: `nc -zv hostname port`
- Check credentials in `.env`

**Tools work standalone but not unified:**
- Verify class is instantiated in `homelab_unified_mcp.py`
- Verify tool registration in compose_servers()
- Check logs for import errors

## Local Customizations

This repository supports local homelab-specific customizations through the `CLAUDE_CUSTOM.md` file (gitignored).

### Purpose
`CLAUDE_CUSTOM.md` allows you to provide Claude with context about your specific homelab infrastructure without committing sensitive details to the public repository. This includes:
- Actual server names and infrastructure identifiers
- Custom operational workflows specific to your setup
- Infrastructure-specific task examples
- Local naming conventions and patterns

### Setup
1. Copy the example template: `cp CLAUDE_CUSTOM.example.md CLAUDE_CUSTOM.md`
2. Customize with your details (server names, workflows, patterns)
3. Keep it updated as your infrastructure evolves

### Security Note
- `CLAUDE_CUSTOM.md` is gitignored and will never be committed
- Still avoid putting credentials directly in this file
- Use environment variables (`.env`) for secrets
- Document server names and patterns, not passwords

## Links and Resources

- **Repository:** <https://github.com/bjeans/homelab-mcp>
- **Docker Hub:** <https://hub.docker.com/r/bjeans/homelab-mcp>
- **Issues:** <https://github.com/bjeans/homelab-mcp/issues>
- **Discussions:** <https://github.com/bjeans/homelab-mcp/discussions>
- **Security:** <https://github.com/bjeans/homelab-mcp/security/advisories>
- **Pull Requests:** <https://github.com/bjeans/homelab-mcp/pulls>
- **MCP Docs:** <https://modelcontextprotocol.io/>
- **Claude Desktop:** <https://claude.ai/download>

## Documentation

- **[README.md](README.md)** - User documentation and getting started
- **[MIGRATION_V3.md](MIGRATION_V3.md)** - Upgrade guide from v2.x to v3.0
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - How to add new servers, Docker integration, and development workflows
- **[DOCKER.md](DOCKER.md)** - Docker deployment guide and configuration
- **[SECURITY.md](SECURITY.md)** - Security guidelines and best practices
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and release notes

---

**Remember:** This project manages critical infrastructure. Security and reliability are paramount. Always test thoroughly and never commit sensitive data.

**Last Updated:** January 14, 2026
**Current Version:** 3.0.0 (FastMCP refactor with lazy imports)
