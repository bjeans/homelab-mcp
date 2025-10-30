# Claude Development Guide for Homelab MCP

**NOTE:** This is a template file. Copy to `CLAUDE.md` in your deployment and fill in YOUR project details.

## Quick Start

1. **Copy this template:**  
   `cp CLAUDE.example.md CLAUDE.md`

2. **Update with your details:**
   - Repository URL
   - Your infrastructure details
   - Team contact info

3. **Never commit:** CLAUDE.md contains YOUR specific infrastructure details

## Project Overview

This is an open-source MCP server collection providing infrastructure monitoring through Claude Desktop.

**Key insight:** All configuration uses **environment variables and Ansible inventory** - never hardcoded credentials or IPs.

## Core Philosophy

1. **Security First** - No credentials, IPs, or sensitive data in code
2. **Configuration as Code** - Settings via .env and Ansible only
3. **Production-Grade** - Suitable for critical infrastructure
4. **Open Source** - MIT licensed, community-friendly

## The Dual-Mode Architecture

All MCP servers work in TWO modes:

### Unified Mode (Recommended)
- All servers combined in one MCP entry
- Shared Ansible inventory (single file read)
- Prefixed tools: `ups_get_status`, `docker_list_containers`
- Lower resource usage

### Standalone Mode
- Individual servers for debugging
- Tools without prefix: `get_status`, `list_containers`
- Useful for testing or isolated deployments

## Server Structure

```python
# 1. CLASS - for unified mode
class ServiceMCPServer:
    def __init__(self, ansible_inventory=None):
        self.inventory = ansible_inventory  # Pre-loaded in unified

    async def list_tools(self):
        """Return tools WITH prefix (service_*)"""
        return [types.Tool(name="service_tool_name", ...)]

    async def handle_tool(self, name: str, arguments: dict):
        """Route to shared implementation"""
        name = name.replace("service_", "", 1)
        return await handle_call_tool_impl(name, arguments, inventory)

# 2. SHARED IMPLEMENTATION - tested independently
async def handle_call_tool_impl(name: str, arguments: dict, inventory: dict):
    """All tool logic here"""
    if name == "tool_name":
        # Implementation
        pass

# 3. MODULE HANDLERS - for standalone mode
@server.list_tools()
async def list_tools():
    """Return tools WITHOUT prefix"""
    return [types.Tool(name="tool_name", ...)]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Delegate to shared implementation"""
    return await handle_call_tool_impl(name, arguments, inventory)
```

## Creating a New Server

**Decision:**
- New service? → `{service}_mcp_server.py`
- Extend existing? → Add tool to `handle_call_tool_impl()`

**Template:**
```bash
cp ups_mcp_server.py yourservice_mcp_server.py
# Update class name and tool implementations
# Add to ansible_hosts.example.yml
# Add env vars to .env.example
# Integrate into homelab_unified_mcp.py
```

## Configuration Hierarchy

1. **Ansible Inventory** (Primary) - Single source of truth
   - Path via `ANSIBLE_INVENTORY_PATH` env var
   
2. **Environment Variables** (Fallback) - `.env` file
   - Never committed to git
   - Service-specific credentials

3. **Defaults** (Last Resort) - Hardcoded minimums

## Development Workflow

```bash
# Setup
cp .env.example .env
python install_git_hook.py

# Development
python pre_publish_check.py           # Security check
python {service}_mcp_server.py       # Test standalone
python homelab_unified_mcp.py        # Test unified

# Note: Restart Claude Desktop between modes!

# Commit
git add -A
git commit -m "feat: description"
git push origin feature-branch        # Hooks auto-run
```

## Security Rules

⚠️ **Never:**
- Hardcode IPs, hostnames, credentials
- Expose secrets in logs/errors
- Commit `.env` or config files
- Use real infrastructure in examples
- Print to stdout (breaks MCP)

✅ **Always:**
- Use environment variables
- Validate user inputs
- Handle timeouts (5-10 seconds)
- Log to stderr only
- Run `pre_publish_check.py`
- Test both modes

## Troubleshooting

**Tools don't appear:**
→ Restart Claude Desktop (required after code changes)

**Connection timeout:**
→ Check firewall, verify service running, check credentials

**Works standalone but not unified:**
→ Check class instantiation in `homelab_unified_mcp.py`

**Ansible error:**
→ Set `ANSIBLE_INVENTORY_PATH` env var to your inventory file

## Testing Both Modes

```bash
# Mode 1: Standalone
python ups_mcp_server.py
# In Claude: @get_ups_status (no prefix)

# Restart Claude Desktop!

# Mode 2: Unified
python homelab_unified_mcp.py
# In Claude: @ups_get_ups_status (with prefix)
```

## Quick Reference

```bash
# Security check before commit
python pre_publish_check.py

# Create new server
cp ups_mcp_server.py {service}_mcp_server.py

# View Ansible inventory
cat $ANSIBLE_INVENTORY_PATH

# Check for uncommitted secrets
grep -r "password\|secret\|key" . --exclude-dir=.git --exclude-dir=__pycache__
```

## Key Files

- `.env.example` - Configuration template (safe to commit)
- `ansible_hosts.example.yml` - Inventory template (safe to commit)
- `CLAUDE.md` - This file (DO NOT COMMIT - gitignored)
- `.env` - Your actual config (gitignored)
- `ansible_hosts.yml` - Your actual inventory (gitignored)

## Resources

- **MCP Docs:** <https://modelcontextprotocol.io/>
- **Ansible Docs:** <https://docs.ansible.com/>
- **GitHub:** Your repository

---

**Remember:**
- Never commit credentials or real infrastructure details
- Always use environment variables for config
- Always test both standalone and unified modes
- Always restart Claude Desktop after code changes
- Always run pre_publish_check.py before pushing

**Template Version:** 1.1.0  
**For production deployment, customize this guide with YOUR details**
