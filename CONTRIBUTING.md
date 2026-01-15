# Contributing to Homelab MCP

First off, thank you for considering contributing to Homelab MCP! It's people like you that make this project better for everyone.

## Code of Conduct

Be respectful, inclusive, and considerate. We're all here to learn and build cool things for our homelabs.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When creating a bug report, include:

- A clear and descriptive title
- Steps to reproduce the problem
- Expected behavior vs. actual behavior
- Your environment (OS, Python version, Claude Desktop version)
- Relevant logs (with sensitive data removed!)

**Important:** Never include API keys, passwords, or real IP addresses in bug reports.

### Suggesting Features

Feature requests are welcome! Please:

- Use a clear and descriptive title
- Provide a detailed description of the proposed feature
- Explain why this feature would be useful
- Include examples of how it would work

### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Install dependencies:** `pip install -r requirements.txt`
3. **Make your changes:**
   - Follow the existing code style
   - Add/update tests if applicable
   - Update documentation as needed
4. **Test thoroughly** with real infrastructure
5. **Run security check:** `python helpers/pre_publish_check.py`
6. **Commit your changes** with clear, descriptive messages
7. **Push to your fork** and submit a pull request

### Pull Request Guidelines

**Before submitting:**
- [ ] Code follows existing style and patterns
- [ ] No sensitive data in commits (API keys, passwords, real IPs)
- [ ] Documentation updated (README, docstrings, comments)
- [ ] Security implications reviewed
- [ ] Tested with actual homelab services
- [ ] `helpers/pre_publish_check.py` passes

**PR Description should include:**
- What problem does this solve?
- How does it solve it?
- Any breaking changes?
- Screenshots/examples (if applicable)

## Development Setup

### Initial Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/homelab-mcp
cd homelab-mcp

# Install dependencies
pip install -r requirements.txt

# Set up configuration
cp .env.example .env
# Edit .env with your test environment details

# Install git hook (recommended)
python helpers/install_git_hook.py
```

### Testing MCP Servers Locally

Before submitting a PR, test your MCP servers locally using the MCP Inspector:

**Install the MCP Inspector tool (optional developer tool):**

The MCP Inspector is a Node.js-based debugging tool. It's **not** a project dependency - install it globally on your development machine if you need to test MCP servers interactively.

```bash
# Option 1: Install globally (one-time setup)
npm install -g @modelcontextprotocol/inspector

# Option 2: Use npx without installing (recommended)
# Just use npx in the commands below - it will download and run automatically
```

**Test individual servers:**

```bash
# Test Ollama MCP server
npx @modelcontextprotocol/inspector uv --directory . run ollama_mcp.py

# Test Docker/Podman MCP server
npx @modelcontextprotocol/inspector uv --directory . run docker_mcp_podman.py

# Test Pi-hole MCP server
npx @modelcontextprotocol/inspector uv --directory . run pihole_mcp.py

# Test Ansible inventory MCP server
npx @modelcontextprotocol/inspector uv --directory . run ansible_mcp_server.py

# Test Unifi MCP server
npx @modelcontextprotocol/inspector uv --directory . run unifi_mcp_optimized.py

# Test MCP Registry Inspector
npx @modelcontextprotocol/inspector uv --directory . run mcp_registry_inspector.py
```

**What the MCP Inspector does:**

- Launches an interactive web-based debugger at `http://localhost:5173`
- Shows all available tools for the MCP server
- Allows you to test tool calls with sample arguments
- Displays tool responses and error messages
- Helpful for debugging tool implementations before Claude integration

**Quick testing workflow:**

1. Open terminal in the `Homelab-MCP` directory
2. Run the MCP Inspector command for the server you're testing
3. Browser opens to the debugger interface
4. Test each tool with appropriate arguments
5. Verify responses are correct and complete
6. Check for any error messages or unexpected behavior
7. Review logs in the terminal for debug output

**Debugging tips:**

- Check `.env` file is configured with test credentials
- Verify Ansible inventory file exists if testing Ansible-dependent servers
- Use `logging` statements in your code (logged to stderr, visible in terminal)
- Test with both valid and invalid arguments to verify error handling
- Pay attention to response format - must return `list[types.TextContent]`

### Running Security Checks

Before submitting a PR:

```bash
# Run security checker
python helpers/pre_publish_check.py

# Run all development checks
python helpers/run_checks.py
```

### Adding a New MCP Server

See [CLAUDE.md - Architecture Patterns](CLAUDE.md#architecture-patterns) to understand the dual-mode server pattern before starting.

#### Decision Tree

Ask yourself these questions:

1. **Is this a new service/tool?**
   - YES → Create new `{service}_mcp_server.py`
   - NO → Extend existing server (add new tool to existing service)

2. **Does it need Ansible inventory configuration?**
   - YES → Add host group to `ansible_hosts.yml` (e.g., `minio_servers:`)
   - NO → Use .env variables only (e.g., `MINIO_API_KEY=...`)

3. **Can it share code/patterns with existing servers?**
   - YES → Study an existing server and follow the pattern
   - NO → Still follow dual-mode pattern, but with unique logic

4. **Does it need real-time polling or querying?**
   - YES → Implement async queries in `handle_call_tool_impl()`
   - NO → Query on-demand only (lazy loading)

5. **Will this be used in unified mode?**
   - YES (recommended) → Must support class-based + shared inventory
   - NO → Standalone-only acceptable (but less preferred)

#### Step-by-Step Guide

**Step 1: Copy Template**
Use the most recent server as template (currently `ups_mcp_server.py`):
```bash
cp ups_mcp_server.py {newservice}_mcp_server.py
```

**Step 2: Update Class and Function Names**
```python
# Replace UpsMCPServer with your service name
class MinioMCPServer:
    def __init__(self, ansible_inventory=None):
        # Your code here
        pass
```

**Step 3: Add Ansible Host Group**
In `ansible_hosts.yml`:
```yaml
minio_servers:
  minio-1:
    ansible_host: 192.0.2.10
    minio_port: 9000
    minio_bucket: "backups"
```

**Step 4: Add Environment Variables**
In `.env.example`:
```
# Minio configuration
MINIO_ENDPOINT=http://minio-1:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

**Step 5: Implement Tool Logic**
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

**Step 6: Add to Unified Server**
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

**Step 7: Update Documentation**
- Add to README.md with example commands
- Add environment variables section to PROJECT_INSTRUCTIONS.example.md
- Update CHANGELOG.md with version notes
- Add host group to ansible_hosts.example.yml

**Step 8: Update Dockerfile**
See [Docker Integration Checklist](#docker-integration-checklist) below.

**Step 9: Test**
```bash
# Test standalone mode
python minio_mcp_server.py

# Restart Claude Desktop (required for MCP reload)
# Test in Claude with: @minio_list_buckets

# Test unified mode by restarting Claude again
# Test combined tool: @ups_get_status (still works)
```

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

### Code Style

- **Python 3.10+** features
- **Async/await** for I/O operations
- **Type hints** where beneficial
- **Error handling** for network operations
- **Logging to stderr** for debugging
- **Security first:** Validate inputs, sanitize outputs

### Security Requirements

**Critical:**
- ❌ Never hardcode credentials or API keys
- ❌ Never commit real IP addresses or hostnames
- ✅ Always use environment variables for secrets
- ✅ Always validate user inputs
- ✅ Run `helpers/pre_publish_check.py` before committing

## Release Process

### Automated Docker Builds

**Docker images are automatically built and published to Docker Hub via GitHub Actions.**

**Trigger Conditions:**

1. **PR merged to `main` branch** → Builds and tags as `latest` and `edge`
2. **Release tags (`v*.*.*`)** → Builds with semantic versioning tags
3. **Manual workflow dispatch** → For testing or emergency builds

**Tagging Strategy:**

For a release tag `v2.1.0`, the following Docker tags are created:
- `2.1.0` (exact version)
- `2.1` (minor version)
- `2` (major version)
- `latest` (if from main branch)

**Multi-Platform Support:**
- `linux/amd64` - x86_64 servers and workstations
- `linux/arm64` - Raspberry Pi, ARM-based systems

### Creating a Release

**For maintainers:**

1. **Update version references:**
   ```bash
   # Update CHANGELOG.md with version number and changes
   # Update any version strings in documentation
   ```

2. **Commit and push to main:**
   ```bash
   git add CHANGELOG.md
   git commit -m "chore: prepare release v2.1.0"
   git push origin main
   ```

3. **Create and push the release tag:**
   ```bash
   git tag -a v2.1.0 -m "Release v2.1.0"
   git push origin v2.1.0
   ```

4. **GitHub Actions automatically:**
   - Runs security checks and tests
   - Builds multi-platform Docker images
   - Pushes to Docker Hub with semantic version tags
   - Updates `latest` tag

5. **Create GitHub Release:**
   - Go to https://github.com/bjeans/homelab-mcp/releases/new
   - Select the tag you just created
   - Title: `v2.1.0`
   - Copy relevant entries from CHANGELOG.md
   - Publish release

6. **Verify the build:**
   - Check GitHub Actions: https://github.com/bjeans/homelab-mcp/actions
   - Verify Docker Hub: https://hub.docker.com/r/bjeans/homelab-mcp/tags
   - Test pulling the new image:
     ```bash
     docker pull bjeans/homelab-mcp:2.1.0
     docker pull bjeans/homelab-mcp:latest
     ```

### Testing Docker Builds Locally

**Before creating a release, test the Docker build:**

```bash
# Build for multiple platforms locally (requires Docker Buildx)
docker buildx create --use
docker buildx build --platform linux/amd64,linux/arm64 -t homelab-mcp:test .

# Test the image
docker run --rm homelab-mcp:test python -c "import sys; print(sys.version)"
```

### Manual Workflow Dispatch

**For testing or emergency builds without a release:**

1. Go to: https://github.com/bjeans/homelab-mcp/actions/workflows/docker-publish.yml
2. Click "Run workflow"
3. Optionally specify a custom tag
4. Click "Run workflow" button

This is useful for:
- Testing the build process
- Creating debug/test images
- Emergency hotfix deployments

### Rollback Process

**If a release has issues:**

1. **Identify the last known-good version:**
   ```bash
   # Users can always pull specific versions
   docker pull bjeans/homelab-mcp:2.0.0
   ```

2. **Create a hotfix:**
   - Fix the issue in a new branch
   - Create PR and merge to main
   - Create a new patch release (e.g., `v2.1.1`)

3. **Update `latest` tag if needed:**
   - The new release will automatically update `latest`
   - Or manually retag in Docker Hub if immediate rollback needed

### Docker Hub Access

**Repository:** https://hub.docker.com/r/bjeans/homelab-mcp

**Required Secrets (configured in GitHub repository settings):**
- `DOCKERHUB_USERNAME` - Docker Hub username
- `DOCKERHUB_TOKEN` - Docker Hub access token (not password!)

**Security Notes:**
- Use Docker Hub access tokens, never passwords
- Tokens should have write permissions only for `bjeans/homelab-mcp`
- Rotate tokens periodically
- Never commit tokens to repository

## Project Structure

```
homelab-mcp/
├── *_mcp*.py          # MCP server implementations
├── .env.example       # Configuration template
├── SECURITY.md        # Security documentation
├── README.md          # User documentation
├── requirements.txt   # Python dependencies
├── helpers/           # Development and validation tools
│   ├── pre_publish_check.py   # Security validation
│   ├── install_git_hook.py    # Git pre-commit hook installer
│   ├── run_checks.py          # CI/CD check runner
│   └── requirements-dev.txt   # Development dependencies
└── archive-ignore/    # Archived versions and test files
```

## Questions?

- Check the [README](README.md)
- Review [SECURITY.md](SECURITY.md)
- Open a [Discussion](https://github.com/bjeans/homelab-mcp/discussions)
- File an [Issue](https://github.com/bjeans/homelab-mcp/issues)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Homelab MCP! 🚀
