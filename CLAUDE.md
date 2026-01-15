# Claude Development Guide for Homelab MCP

## Project Overview

**Repository:** <https://github.com/bjeans/homelab-mcp>
**Docker Hub:** <https://hub.docker.com/r/bjeans/homelab-mcp>
**Version:** 3.0.0 (Released: 2026-01-14)
**License:** MIT
**Purpose:** Open-source MCP servers for homelab infrastructure management through Claude Desktop

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
│   ├── PROJECT_INSTRUCTIONS.example.md # AI assistant guide template
│   └── ansible_config_manager.py      # Centralized config loader
│
└── Documentation
    ├── README.md                      # User documentation
    ├── CONTRIBUTING.md                # Contribution guide
    ├── DOCKER.md                      # Docker deployment
    ├── SECURITY.md                    # Security guidelines
    └── CHANGELOG.md                   # Version history
```

## Architecture Patterns

### The Dual-Mode MCP Server Pattern

All servers follow this unified architecture supporting both **standalone** and **unified mode** operation:

#### 1. Class-Based Implementation

```python
class UpsMCPServer:
    """Service-specific MCP server with shared inventory support"""

    def __init__(self, ansible_inventory=None):
        """Initialize with optional pre-loaded inventory (for unified mode)"""
        self.ansible_inventory = ansible_inventory
        self.inventory_data = None

    async def list_tools(self) -> list[types.Tool]:
        """Return tools with SERVICE_ prefix (e.g., ups_get_status)"""
        return [
            types.Tool(
                name="ups_get_ups_status",
                description="...",
                inputSchema={"type": "object", "properties": {}},
            ),
            # ... more tools
        ]

    async def handle_tool(self, tool_name: str, arguments: dict) -> list[types.TextContent]:
        """Route tool calls to shared implementation"""
        name = tool_name.replace("ups_", "", 1) if tool_name.startswith("ups_") else tool_name
        return await handle_call_tool_impl(name, arguments, self._load_inventory())
```

#### 2. Shared Implementation Function

```python
async def handle_call_tool_impl(name: str, arguments: dict, inventory: dict) -> list[types.TextContent]:
    """Core tool execution logic - shared by both class and module handlers

    Key benefit: Single source of truth for all business logic
    """
    try:
        if name == "get_ups_status":
            # Implementation here
            ...
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]
```

#### 3. Module-Level Handlers (Standalone Mode)

```python
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """For standalone mode: tools WITHOUT prefix"""
    return [
        types.Tool(name="get_ups_status", ...),
        # ...
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """For standalone mode: delegate to shared implementation"""
    inventory = load_ansible_inventory_global()
    return await handle_call_tool_impl(name, arguments, inventory)
```

#### 4. Unified Server Integration

```python
# In homelab_unified_mcp.py
from ups_mcp_server import UpsMCPServer

class UnifiedHomelabServer:
    def __init__(self):
        shared_inventory = load_shared_ansible_inventory()
        self.ups = UpsMCPServer(ansible_inventory=shared_inventory)
        self.pihole = PiholeMCPServer(ansible_inventory=shared_inventory)
        # ... etc

    async def handle_list_tools(self):
        """Combine tools from all servers"""
        tools = []
        tools.extend(await self.ups.list_tools())      # Has ups_ prefix
        tools.extend(await self.pihole.list_tools())   # Has pihole_ prefix
        return tools
```

### Why This Pattern?

✅ **Unified Mode:** Single inventory read, no file locking, consistent config
✅ **Standalone Mode:** Works independently, clean tool names, useful for debugging
✅ **Development:** Core logic tested independently, easy to add servers, clear separation of concerns

### Configuration Hierarchy

1. **Ansible Inventory** (Primary) - Single source of truth for infrastructure
   - Set via `ANSIBLE_INVENTORY_PATH` environment variable
   - Contains all host configurations and group definitions

2. **Environment Variables** (Fallback) - `.env` file for service-specific config
   - Never committed to git (use `.gitignore`)
   - Created from `.env.example` template

3. **Defaults** (Last resort) - Hardcoded fallbacks in source code
   - Minimal, for development/testing only

## Common AI Assistant Tasks

### "Add feature X to server Y"
1. Read the server file completely
2. Understand current tool structure
3. Add new tool following existing patterns
4. Update docstrings and error handling
5. Test thoroughly with real service

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
4. Consider if SECURITY.md needs updates

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

## Testing & Validation

### Quick Validation
```bash
# Before submitting changes, ensure code works
python {service}_mcp_server.py        # Test standalone
python homelab_unified_mcp.py         # Test unified mode
python helpers/pre_publish_check.py   # Run security checks
```

### Troubleshooting Common Issues

**MCP tools don't appear in Claude Desktop:**
- Restart Claude Desktop (required after code changes)
- Check that `MCP_UNIFIED_MODE` env var is set correctly
- Verify `claude_desktop_config.json` path is correct

**"No Ansible inventory found" error:**
- Set `ANSIBLE_INVENTORY_PATH` in `.env`
- Path should point to your `ansible_hosts.yml`

**"Connection timeout" to service:**
- Check firewall allows connection to service port
- Verify service is running
- Test connectivity: `nc -zv hostname port`
- Check credentials in `.env`

**Tools work standalone but not unified:**
- Verify class is instantiated in `homelab_unified_mcp.py`
- Verify routing has correct prefix in `handle_call_tool()`
- Verify tool names have prefix in `list_tools()`

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

- **[CONTRIBUTING.md](CONTRIBUTING.md)** - How to add new servers, Docker integration, and development workflow
- **[DOCKER.md](DOCKER.md)** - Docker deployment guide and configuration
- **[SECURITY.md](SECURITY.md)** - Security guidelines and best practices
- **[README.md](README.md)** - User documentation and getting started
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and release notes

---

**Remember:** This project manages critical infrastructure. Security and reliability are paramount. Always test thoroughly and never commit sensitive data.

**Last Updated:** January 14, 2026
**Current Version:** 3.0.0 (FastMCP refactor with lazy imports)
