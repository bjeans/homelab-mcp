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

1. Create the server file (e.g., `my_service_mcp.py`)
2. Follow the existing pattern from other servers
3. Add configuration to `.env.example`
4. Update `README.md` with server documentation
5. Update `PROJECT_INSTRUCTIONS.example.md`
6. Update `CLAUDE.example.md` if adding AI development context
7. Add security notes if the service uses API keys
8. Test thoroughly

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
