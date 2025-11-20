# Claude Development Guide for Homelab MCP

## Project Overview

**Repository:** <https://github.com/bjeans/homelab-mcp>
**Docker Hub:** <https://hub.docker.com/r/bjeans/homelab-mcp>
**Version:** 2.1.0 (Released: 2025-11-19)
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
│   ├── claude_desktop_config.json     # Claude Desktop config (gitignored)
│   └── ansible_config_manager.py      # Centralized config loader
│
├── Documentation
│   ├── README.md                      # User documentation
│   ├── SECURITY.md                    # Security guidelines
│   ├── CONTRIBUTING.md                # Contribution guide
│   ├── CHANGELOG.md                   # Version history
│   ├── CONTEXT_AWARE_SECURITY.md      # Security scanning docs
│   ├── CI_CD_CHECKS.md                # CI/CD automation docs
│   └── LICENSE                        # MIT License
│
├── Docker Deployment
│   ├── Dockerfile                     # Container build config
│   ├── docker-compose.yml             # Container orchestration (uses bjeans/homelab-mcp:latest)
│   ├── docker-entrypoint.sh           # Docker container startup
│   └── Published at: <https://hub.docker.com/r/bjeans/homelab-mcp>
│
├── Utilities & Tools
│   ├── mcp_registry_inspector.py      # MCP file management
│   ├── unifi_exporter.py              # Unifi data export utility
│   ├── requirements.txt               # Python dependencies
│   └── .gitignore                     # Git ignore rules
│
└── helpers/                           # Development utilities
    ├── install_git_hook.py            # Git pre-push hook installer
    ├── pre_publish_check.py           # Security validation
    ├── run_checks.py                  # CI/CD check runner
    └── requirements-dev.txt           # Dev dependencies
```

## Architecture Patterns

### The Dual-Mode MCP Server Pattern

All servers follow this unified architecture supporting both **standalone** and **unified mode** operation:

#### 1. Class-Based Implementation

```python
class UpsMCPServer:
    """Service-specific MCP server with shared inventory support"""

    def __init__(self, ansible_inventory=None):
        """Initialize with optional pre-loaded inventory (for unified mode)

        Args:
            ansible_inventory: Pre-loaded inventory dict from unified server
                             If None, will load from file at runtime
        """
        self.ansible_inventory = ansible_inventory
        self.inventory_data = None

    async def list_tools(self) -> list[types.Tool]:
        """Return tools with SERVICE_ prefix (e.g., ups_get_status)

        Prefix ensures no collisions when combined in unified server
        """
        return [
            types.Tool(
                name="ups_get_ups_status",
                description="...",
                inputSchema={"type": "object", "properties": {}},
            ),
            # ... more tools
        ]

    async def handle_tool(self, tool_name: str, arguments: dict) -> list[types.TextContent]:
        """Route tool calls to shared implementation
        
        Strips prefix and delegates to handle_call_tool_impl()
        """
        name = tool_name.replace("ups_", "", 1) if tool_name.startswith("ups_") else tool_name
        return await handle_call_tool_impl(name, arguments, self._load_inventory())
    
    def _load_inventory(self):
        """Load inventory: use pre-loaded (unified) or file (standalone)"""
        if self.inventory_data is not None:
            return self.inventory_data
        # Load from file using AnsibleConfigManager
        ...
```

#### 2. Shared Implementation Function

```python
async def handle_call_tool_impl(name: str, arguments: dict, inventory: dict) -> list[types.TextContent]:
    """Core tool execution logic - shared by both class and module handlers
    
    This function contains ALL tool implementations. It's called by:
    - Class method: handle_tool() for unified mode
    - Module handler: handle_call_tool() for standalone mode
    
    Key benefit: Single source of truth for all business logic
    """
    try:
        if name == "get_ups_status":
            # Implementation here
            ...
        elif name == "get_ups_details":
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
        types.Tool(name="get_ups_status", ...),    # No "ups_" prefix
        types.Tool(name="get_ups_details", ...),
        # ...
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """For standalone mode: delegate to shared implementation"""
    inventory = load_ansible_inventory_global()  # Use global cache
    return await handle_call_tool_impl(name, arguments, inventory)
```

#### 4. Unified Server Integration

```python
# In homelab_unified_mcp.py

from ups_mcp_server import UpsMCPServer

class UnifiedHomelabServer:
    def __init__(self):
        # Load Ansible inventory ONCE for all servers
        shared_inventory = load_shared_ansible_inventory()
        
        # Instantiate all servers with shared inventory
        self.ups = UpsMCPServer(ansible_inventory=shared_inventory)
        self.pihole = PiholeMCPServer(ansible_inventory=shared_inventory)
        self.docker = DockerMCPServer(ansible_inventory=shared_inventory)
        # ... etc
    
    async def handle_list_tools(self):
        """Combine tools from all servers"""
        tools = []
        tools.extend(await self.ups.list_tools())      # Has ups_ prefix
        tools.extend(await self.pihole.list_tools())   # Has pihole_ prefix
        # ... etc
        return tools
    
    async def handle_call_tool(self, name: str, arguments: dict):
        """Route prefixed tool calls to correct server"""
        if name.startswith("ups_"):
            return await self.ups.handle_tool(name, arguments)
        elif name.startswith("pihole_"):
            return await self.pihole.handle_tool(name, arguments)
        # ... etc
```

### Why This Pattern?

✅ **Unified Mode Benefits:**
- Single shared inventory file read (not 7 separate reads)
- No file locking conflicts
- Consistent configuration across all servers
- Cleaner namespace with prefixes

✅ **Standalone Mode Benefits:**
- Server works independently
- Tools have clean names (no prefix)
- Useful for debugging specific service
- Can be deployed alone

✅ **Development Benefits:**
- Core logic tested independently of MCP framework
- Easy to add new servers (copy pattern)
- Clear separation of concerns
- Predictable behavior

### MCP Server Pattern (Essential Structure)

```python
# Standard structure all servers follow

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

import mcp.server.stdio
import mcp.types as types
from mcp.server import Server

# Setup
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

server = Server("service-name")

# Configuration loading
SCRIPT_DIR = Path(__file__).parent
ENV_FILE = SCRIPT_DIR / ".env"

# Only load .env if NOT in unified mode (to avoid duplicate loading)
if not os.getenv("MCP_UNIFIED_MODE"):
    from mcp_config_loader import load_env_file, COMMON_ALLOWED_ENV_VARS
    load_env_file(ENV_FILE, allowed_vars={"SERVICE_*"}, strict=True)

# Service-specific code here

# Class implementation for unified mode
class ServiceMCPServer:
    def __init__(self, ansible_inventory=None):
        ...

# Shared implementation
async def handle_call_tool_impl(name: str, arguments: dict, inventory: dict):
    ...

# Module handlers for standalone mode
@server.list_tools()
async def handle_list_tools():
    ...

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    ...

async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, ...)

if __name__ == "__main__":
    asyncio.run(main())
```

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
   - Should rarely be used in production

### Error Handling

- Always use try/except blocks
- Return structured error responses
- Log to stderr for debugging
- Never expose internal details to users

## Development Workflows

### Adding a New MCP Server: Decision Tree

Ask yourself these questions:

1. **Is this a new service/tool?**
   - YES → Create new `{service}_mcp_server.py`
   - NO → Extend existing server (add new tool to existing service)

2. **Does it need Ansible inventory configuration?**
   - YES → Add host group to `ansible_hosts.yml` (e.g., `minio_servers:`)
   - NO → Use .env variables only (e.g., `MINIO_API_KEY=...`)

3. **Can it share code/patterns with existing servers?**
   - YES → Study PiholeMCPServer or DockerMCPServer and follow pattern
   - NO → Still follow dual-mode pattern, but with unique logic

4. **Does it need real-time polling or querying?**
   - YES → Implement async queries in `handle_call_tool_impl()`
   - NO → Query on-demand only (lazy loading)

5. **Will this be used in unified mode?**
   - YES (recommended) → Must support class-based + shared inventory
   - NO → Standalone-only acceptable (but less preferred)

### Creating a New Server: Step-by-Step

#### Step 1: Copy Template
Use the most recent server as template (currently `ups_mcp_server.py`):
```bash
cp ups_mcp_server.py {newservice}_mcp_server.py
```

#### Step 2: Update Class and Function Names
```python
# Replace UpsMCPServer with your service name
class MinioMCPServer:
    def __init__(self, ansible_inventory=None):
        # Your code here
        pass
```

#### Step 3: Add Ansible Host Group
In `ansible_hosts.yml`:
```yaml
minio_servers:
  minio-1:
    ansible_host: 192.0.2.10
    minio_port: 9000
    minio_bucket: "backups"
```

#### Step 4: Add Environment Variables
In `.env.example`:
```
# Minio configuration
MINIO_ENDPOINT=http://minio-1:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

#### Step 5: Implement Tool Logic
In `handle_call_tool_impl()`:
```python
async def handle_call_tool_impl(name: str, arguments: dict, inventory: dict):
    minio_servers = inventory.get("minio_servers", {})
    
    if name == "list_buckets":
        # Implementation
        pass
    elif name == "get_bucket_stats":
        # Implementation
        pass
```

#### Step 6: Add to Unified Server
In `homelab_unified_mcp.py`:
```python
# Import
from minio_mcp_server import MinioMCPServer

# Initialize in __init__()
self.minio = MinioMCPServer(ansible_inventory=shared_inventory)

# In handle_list_tools()
tools.extend(await self.minio.list_tools())

# In handle_call_tool()
elif name.startswith("minio_"):
    return await self.minio.handle_tool(name, arguments)
```

#### Step 7: Update Documentation
- Add to README.md with example commands
- Add environment variables section to PROJECT_INSTRUCTIONS.example.md
- Update CHANGELOG.md with version notes
- Add host group to ansible_hosts.example.yml

#### Step 7b: Update Dockerfile

**CRITICAL:** All new Python files needed at runtime MUST be added to the Dockerfile:

In `Dockerfile`:
```dockerfile
# Add your new server file
COPY --chown=mcpuser:mcpuser minio_mcp_server.py .
```

**Verification:**
```bash
# Test Docker build locally
docker build -t homelab-mcp:test .

# Verify new file is in the image
# NOTE: The following command will start the MCP server and hang indefinitely waiting for stdio input.
# This is expected behavior for MCP servers. If you see the process hang, it means the file was found and started successfully.
# Use Ctrl+C to exit.
docker run --rm homelab-mcp:test python minio_mcp_server.py

# Alternatively, you can use a timeout to run the server briefly:
timeout 2 docker run --rm homelab-mcp:test python minio_mcp_server.py || [ $? -eq 124 ]

# Or simply check that the file can be imported:
docker run --rm homelab-mcp:test python -c "import minio_mcp_server"
# If imports fail, you missed a dependency file!
```

**Common mistake:** Creating a new `.py` file but forgetting to add it to Dockerfile.
This causes import errors in containerized deployments while working fine locally.

**Files that DON'T need to be in Dockerfile:**
- Test files in `tests/` directory
- Helper scripts in `helpers/` directory
- Example files (`*.example.*`)
- Development-only utilities

#### Step 8: Test
```bash
# Test standalone mode
python minio_mcp_server.py

# Restart Claude Desktop (required for MCP reload)
# Test in Claude with: @minio_list_buckets

# Test unified mode by restarting Claude again
# Test combined tool: @ups_get_status (still works)
```

### Modifying Existing Server

1. **Read current implementation** completely
2. **Maintain backward compatibility** unless major version bump
3. **Add new tool** to `handle_call_tool_impl()`
4. **Update both contexts**:
   - Add tool to class `list_tools()` (with service prefix)
   - Add tool to module `handle_list_tools()` (without prefix)
5. **Test standalone and unified modes**
6. **Update documentation** - README, docstrings, examples
7. **Run pre_publish_check.py** before commit

### Docker Integration Checklist

**Every time you create or modify Python files**, verify Docker integration:

#### When to Update Dockerfile

**ALWAYS update when:**
- ✅ Creating new MCP server file (e.g., `minio_mcp_server.py`)
- ✅ Creating new shared module (e.g., `mcp_error_handler.py`, `ansible_config_manager.py`)
- ✅ Adding any `.py` file imported by runtime code

**NEVER update for:**
- ❌ Test files in `tests/` directory
- ❌ Helper scripts in `helpers/` directory
- ❌ Example/template files (`*.example.*`)
- ❌ Documentation files (`.md`)

#### Docker Update Workflow

```bash
# 1. Add file to Dockerfile in an organized manner
COPY --chown=mcpuser:mcpuser your_new_file.py .

# 2. Test build locally
docker build -t homelab-mcp:test .

# 3. Test that imports work
docker run --rm homelab-mcp:test python -c "import your_new_module"

# 4. Test the unified server starts
# This command will start the server and hang indefinitely waiting for MCP stdio input (this is expected behavior).
# You should see no errors, and can use Ctrl+C to exit.
docker run --rm homelab-mcp:test python homelab_unified_mcp.py

# Alternatively, you can use a timeout to automatically exit after a few seconds:
timeout 2 docker run --rm homelab-mcp:test python homelab_unified_mcp.py || [ $? -eq 124 ]

# Or, for a quick import check (does not start the server):
docker run --rm homelab-mcp:test bash -c "python -c 'import homelab_unified_mcp'"
```

#### Common Docker Mistakes

**Mistake:** Adding Python file but forgetting Dockerfile
- **Symptom:** Works locally, fails in Docker with `ModuleNotFoundError`
- **Fix:** Add `COPY` line to Dockerfile
- **Example:** PR #32 created `mcp_error_handler.py` but forgot Dockerfile (fixed in commit d84d5d8)

**Mistake:** Adding to Dockerfile but not `requirements.txt`
- **Symptom:** Docker build fails with import errors
- **Fix:** Add missing package to `requirements.txt`

**Mistake:** Testing only standalone, not unified mode in Docker
- **Symptom:** Individual servers work but unified container fails
- **Fix:** Test `homelab_unified_mcp.py` in Docker before committing

### Security Checklist

Before any commit:

- [ ] No hardcoded IPs, hostnames, or credentials
- [ ] All sensitive data uses environment variables from `.env`
- [ ] Example files use placeholder data (example.com, 192.0.2.x ranges)
- [ ] Error messages don't expose internal details to users
- [ ] `pre_publish_check.py` passes all checks
- [ ] Git pre-push hook installed and working (`install_git_hook.py`)
- [ ] No real infrastructure details in commit messages
- [ ] All new runtime `.py` files added to Dockerfile
- [ ] Docker build tested locally (`docker build -t homelab-mcp:test .`)
- [ ] If adding dependencies, updated `requirements.txt`

### Git Workflow and Branch Protection

**CRITICAL: Never commit directly to main branch**

All development work MUST follow the branch → commit → PR → merge workflow:

#### 1. Create Feature Branch

```bash
# Always start from updated main
git checkout main
git pull origin main

# Create feature branch with descriptive name
git checkout -b feature/add-minio-server
git checkout -b fix/pihole-connection-timeout
git checkout -b docs/update-installation-guide
```

**Branch naming conventions:**
- `feature/` - New features or enhancements
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions or updates

#### 2. Make Changes and Commit

```bash
# Make your changes, then stage
git add -A

# Commit with conventional commit format
git commit -m "feat: add Minio MCP server for object storage"
git commit -m "fix: handle timeout in Pi-hole API calls"
git commit -m "docs: update Docker deployment instructions"

# Push to feature branch (NOT main)
git push origin feature/add-minio-server
```

#### 3. Create Pull Request

```bash
# Use GitHub CLI to create PR
gh pr create --title "feat: Add Minio MCP server" \
  --body "Description of changes..."

# Or create PR via GitHub web interface
```

#### 4. Merge After Review

- PRs should be reviewed before merging
- Ensure all CI/CD checks pass
- Security pre-push hooks must succeed
- Merge via GitHub interface (preserves audit trail)

#### Git Safety Rules

**NEVER do these (unless explicitly requested by user):**

- ❌ Commit directly to `main` or `master` branch
- ❌ Run `git push --force` to main/master (warn user if requested)
- ❌ Skip git hooks with `--no-verify` or `--no-gpg-sign`
- ❌ Run destructive commands like `git reset --hard` without confirmation
- ❌ Update git config without user approval
- ❌ Use `git commit --amend` (except for pre-commit hook fixes)
- ❌ Create commits without user explicitly asking

**ALWAYS do these:**

- ✅ Create feature branch before making changes
- ✅ Use conventional commit format (`feat:`, `fix:`, `docs:`, etc.)
- ✅ Run `pre_publish_check.py` before pushing
- ✅ Let pre-push hooks run (never skip)
- ✅ Check authorship before amending commits (`git log -1 --format='%an %ae'`)
- ✅ Push to feature branch, never directly to main
- ✅ Create PR for all changes to main branch

#### Emergency Direct Commits

In rare cases where direct commit to main is unavoidable (e.g., critical security hotfix):

1. **Get explicit user approval first**
2. Document reason in commit message
3. Still run all security checks
4. Create issue to track the emergency commit
5. Follow up with proper PR workflow for any additional changes

### Updating MCP Servers

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
5. Test thoroughly with real service
6. Update README.md documentation

### "Debug connection issue"

1. Check .env.example for required variables
2. Verify error handling in server code
3. Test API endpoint independently
4. Check firewall/network access
5. Validate credentials format

### "Improve error messages"

1. Review all error_response() calls
2. Make messages user-friendly
3. Don't expose internal details
4. Include actionable suggestions
5. Test each error path

### "Update documentation"

1. Update inline docstrings first
2. Update README.md server section
3. Update PROJECT_INSTRUCTIONS.example.md if workflow changes
4. Update CHANGELOG.md with changes
5. Consider if SECURITY.md needs updates

### "Create task reminder for user"

When user asks to remember something or track an issue:

1. Create GitHub issues in the homelab-mcp repository for bugs or feature requests
2. Use your preferred task management system (if configured)
3. Include detailed content with context and steps to reproduce
4. Add appropriate labels and assign if working on the project

**Examples of reminder requests:**

- "Remind me to reboot [server-name] to test auto-start"
- "Add upgrading Pi-hole to my todo list"
- "Don't forget to check that certificate renewal"
- "Track this workflow issue"
- "Report this bug in the homelab-mcp repository"

**Always help users track important tasks** - suggest appropriate tools.

## Testing Strategy

### Manual Testing Workflow

#### 1. Standalone Server Testing
```bash
# Set up environment
cp .env.example .env
# Edit .env with test credentials/endpoints

# Start standalone server
python {service}_mcp_server.py

# In another terminal, test with curl (MCP protocol is JSON-RPC over stdio)
# Or start Claude Desktop and type: @{service_without_prefix}_toolname
```

#### 2. Unified Server Testing
```bash
# All servers use same .env (loaded once at startup)
python homelab_unified_mcp.py

# In Claude Desktop, tools have prefixes:
# @ups_get_status
# @docker_list_containers
# @pihole_get_stats
# etc.
```

#### 3. Verify Both Modes Work
```bash
# After any changes, test BOTH:
# 1. Standalone mode
python ups_mcp_server.py

# 2. Unified mode (must restart Claude Desktop between tests)
python homelab_unified_mcp.py
```

### Security Testing

```bash
# Before every commit (hooks do this automatically)
python pre_publish_check.py

# Install git hook for automatic checks (one time)
python install_git_hook.py

# Now 'git push' will run checks automatically
```

### Troubleshooting Common Issues

**MCP tools don't appear in Claude Desktop:**
- → Restart Claude Desktop (required after code changes)
- → Check that `MCP_UNIFIED_MODE` env var is set correctly
- → Verify `claude_desktop_config.json` path is correct

**"No Ansible inventory found" error:**
- → Set `ANSIBLE_INVENTORY_PATH` in `.env`
- → Path should point to your `ansible_hosts.yml`
- → Verify file exists: `ls -la $ANSIBLE_INVENTORY_PATH`

**"Connection timeout" to service:**
- → Check firewall allows connection to service port
- → Verify service is running: `netstat -an | grep PORT`
- → Test connectivity: `nc -zv hostname port`
- → Check credentials in `.env`

**Tools work standalone but not unified:**
- → Verify class is instantiated: check `homelab_unified_mcp.py` init
- → Verify routing has correct prefix: check `handle_call_tool()` elif
- → Verify tool names have prefix: check `list_tools()` returns correct names

### Red Flags to Watch For

⚠️ **Never do these:**

- Hardcoding IPs, hostnames, ports, or credentials
- Exposing API keys or tokens in error messages or logs
- Committing `.env`, `.vscode/settings.json`, or other config files
- Using real infrastructure details in example files or comments
- Skipping error handling in network calls (always use timeouts)
- Assuming services are always available (always handle errors)
- Printing to stdout (breaks MCP protocol - use `logging.basicConfig(stream=sys.stderr)`)

✅ **Always do these:**

- Use environment variables for all sensitive config
- Validate user inputs before API calls
- Handle network timeouts gracefully (5-10 second default)
- Return structured JSON/text responses to users
- Log errors and debug info to `sys.stderr` only
- Run `pre_publish_check.py` before commits
- Test both standalone and unified modes
- Restart Claude Desktop after code changes

## Working with Issues and PRs

### Good Issue Reports Include

- MCP server name and version
- Claude Desktop version
- Operating system
- Error messages (sanitized)
- Steps to reproduce
- Expected vs actual behavior

### Good Pull Requests Include

- Clear description of problem solved
- Testing performed
- Documentation updates
- Security considerations
- Breaking changes noted
- Screenshots/examples if applicable

## Task Management: Tracking Homelab Work

### GitHub Issues (Recommended for Project-Level Work)

Use the homelab-mcp GitHub repository for tasks affecting the MCP servers or shared infrastructure:

**Bug Reports:**
- MCP server not responding
- Tool returns incorrect data
- Connection failures to services
- Security issues or concerns

**Feature Requests:**
- New MCP server suggestions
- New tools for existing servers
- Enhancement to existing functionality
- Configuration improvements

**Documentation:**
- Improvements to guides or examples
- Clarifying confusing sections
- Adding missing troubleshooting info

**Good Issue Template:**
```
Title: {service}: {clear problem}

Description:
- MCP Server: ups_mcp_server
- Claude Version: [X.X.X]
- OS: [macOS/Windows/Linux]

Problem:
[What isn't working?]

Expected:
[What should happen?]

Actual:
[What happens instead?]

Steps to reproduce:
1. ...
2. ...

Error message (sanitized):
[Include stderr output, no credentials]
```

### Personal Task Management (Optional Integration)

For homelab operations not directly related to MCP server code:

**Operational Tasks:**
- "Schedule [server-name] reboot for maintenance window"
- "Upgrade Ollama models to latest on all nodes"
- "Verify automated backups completed successfully"
- "Check NUT battery health on all UPS units"
- "Test network failover procedures"
- "Rotate API credentials quarterly"

**Maintenance Tasks:**
- "Update Ansible inventory with new host"
- "Review Docker container logs for errors"
- "Monitor disk usage on NAS storage"
- "Check certificate expiry dates"

**Decisions/Reminders:**
- "Document decision to use Ansible as config source"
- "Remember to test UPS failover before production use"
- "Remind team about infrastructure change policy"

**Pattern:** Use GitHub Issues for anything affecting shared code/infrastructure decisions. Use your personal system for day-to-day operations.

## Local Customizations

This repository supports local homelab-specific customizations through the `CLAUDE_CUSTOM.md` file.

### Purpose

`CLAUDE_CUSTOM.md` allows you to provide Claude with context about your specific homelab infrastructure without committing sensitive details to the public repository. This includes:

- Actual server names and infrastructure identifiers
- Custom operational workflows specific to your setup
- Infrastructure-specific task examples
- Local naming conventions and patterns
- Environment-specific troubleshooting notes

### Setup

1. **Copy the example template:**
   ```bash
   cp CLAUDE_CUSTOM.example.md CLAUDE_CUSTOM.md
   ```

2. **Customize with your details:**
   - Replace placeholder text with your actual server names
   - Document your naming conventions
   - Add your common operational tasks
   - Include environment-specific notes

3. **Keep it updated:**
   - Update as your infrastructure evolves
   - Add new patterns as they emerge
   - Document lessons learned

### What Goes Where

**CLAUDE_CUSTOM.md** (gitignored, your private customizations):
- Actual server names (e.g., "homelab-server-1", "prod-nas-01")
- Specific infrastructure examples
- Custom task patterns with real identifiers
- Private operational notes

**CLAUDE.md** (public, this file):
- Generic development patterns
- Project architecture and philosophy
- General troubleshooting guidance
- Public documentation standards

### How Claude Uses This

When Claude Code reads your project context, it will automatically read both:
1. `CLAUDE.md` - Public development guide (this file)
2. `CLAUDE_CUSTOM.md` - Your local customizations (if present)

This allows Claude to:
- Understand your specific infrastructure
- Use correct server names in suggestions
- Follow your custom workflows
- Provide environment-specific guidance

### Security Note

`CLAUDE_CUSTOM.md` is included in `.gitignore` and will never be committed. However:
- Still avoid putting credentials directly in this file
- Use environment variables (`.env`) for secrets
- Document server names and patterns, not passwords
- Reference configuration locations, don't embed sensitive data

## Links and Resources

- **Repository:** <https://github.com/bjeans/homelab-mcp>
- **Docker Hub:** <https://hub.docker.com/r/bjeans/homelab-mcp>
- **Issues:** <https://github.com/bjeans/homelab-mcp/issues>
- **Discussions:** <https://github.com/bjeans/homelab-mcp/discussions>
- **Security:** <https://github.com/bjeans/homelab-mcp/security/advisories>
- **Pull Requests:** <https://github.com/bjeans/homelab-mcp/pulls>
- **Releases:** <https://github.com/bjeans/homelab-mcp/releases>
- **MCP Docs:** <https://modelcontextprotocol.io/>
- **Claude Desktop:** <https://claude.ai/download>

## Quick Commands Reference

```bash
# One-time setup
cp .env.example .env                          # Create config file
cp ansible_hosts.example.yml ansible_hosts.yml # Create Ansible inventory
python install_git_hook.py                    # Install pre-push security checks

# Docker deployment (production)
docker pull bjeans/homelab-mcp:latest         # Pull pre-built image from Docker Hub
docker-compose up -d                          # Run with Docker Compose
docker build -t homelab-mcp:latest .          # Or build from source

# Development
python pre_publish_check.py                   # Run security checks before commit
python {service}_mcp_server.py               # Test specific server standalone
python homelab_unified_mcp.py                # Run unified server

# Git workflow (ALWAYS use feature branches, NEVER commit to main)
git checkout main && git pull origin main     # Start from updated main
git checkout -b feature/my-feature            # Create feature branch
git status                                    # Check what's changed
git diff                                      # Review changes before commit
git add -A                                    # Stage all changes
git commit -m "feat: description"            # Commit with conventional format
git push origin feature/my-feature            # Push to feature branch (hooks run checks)
gh pr create --title "feat: ..." --body "..." # Create pull request for review

# Debugging
grep -r "TODO\|FIXME" .                       # Find outstanding tasks
python -m py_compile *.py                     # Check syntax errors
ls -la .env                                   # Verify .env exists
cat $ANSIBLE_INVENTORY_PATH                   # View Ansible inventory
```

## Version History

See [CHANGELOG.md](CHANGELOG.md) for detailed version history, including containerized deployment and unified server (v2.0.0).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines and best practices.

---

**Remember:** This project manages critical infrastructure. Security and reliability are paramount. Always test thoroughly and never commit sensitive data.

**Last Updated:** November 19, 2025
**Current Version:** 2.1.0 (Dynamic enum generation for tool parameters)
