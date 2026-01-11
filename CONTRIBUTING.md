# Contributing to Homelab MCP

Thank you for considering contributing to Homelab MCP! Your contributions help make this project better for everyone.

## Code of Conduct

Be respectful, inclusive, and considerate. We're all here to learn and build cool things for our homelabs.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, check existing issues to avoid duplicates. When creating a bug report, include:

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

**Use MCP Inspector for interactive testing:**

```bash
# Option 1: Use npx without installing (recommended)
npx @modelcontextprotocol/inspector uv --directory . run ollama_mcp.py

# Option 2: Install globally
npm install -g @modelcontextprotocol/inspector
mcp-inspector uv --directory . run docker_mcp_podman.py
```

This opens a web-based debugger at `http://localhost:5173` for testing tools.

**See [CI_CD_CHECKS.md](CI_CD_CHECKS.md) for comprehensive testing guide.**

### Running Security Checks

```bash
# Run security checker
python helpers/pre_publish_check.py

# Run all development checks
python helpers/run_checks.py
```

## Adding a New MCP Server

1. Create the server file (e.g., `my_service_mcp.py`)
2. Follow the dual-mode pattern from existing servers
3. Add configuration to `.env.example`
4. Update `README.md` with server documentation
5. Update `PROJECT_INSTRUCTIONS.example.md`
6. Add to `homelab_unified_mcp.py` for unified mode
7. **Add to Dockerfile** if creating new Python file
8. Add security notes if the service uses API keys
9. Test thoroughly (standalone and unified modes)

**See [CLAUDE.md](CLAUDE.md) for detailed development patterns and architecture.**

## Code Style

- **Python 3.10+** features
- **Async/await** for I/O operations
- **Type hints** where beneficial
- **Error handling** for network operations
- **Logging to stderr** for debugging
- **Security first:** Validate inputs, sanitize outputs

## Security Requirements

**Critical:**
- ❌ Never hardcode credentials or API keys
- ❌ Never commit real IP addresses or hostnames
- ✅ Always use environment variables for secrets
- ✅ Always validate user inputs
- ✅ Run `helpers/pre_publish_check.py` before committing
- ✅ Install pre-push git hook: `python helpers/install_git_hook.py`

## Docker Testing

**If you modify Python files used at runtime, update Dockerfile:**

```bash
# Test Docker build locally
docker build -t homelab-mcp:test .

# Verify new file is in the image
docker run --rm homelab-mcp:test python -c "import your_new_module"
```

**See [DOCKER.md](DOCKER.md) for comprehensive Docker deployment guide.**

## Questions?

- Check the [README](README.md)
- Review [SECURITY.md](SECURITY.md)
- Read [CLAUDE.md](CLAUDE.md) for development details
- Open a [Discussion](https://github.com/bjeans/homelab-mcp/discussions)
- File an [Issue](https://github.com/bjeans/homelab-mcp/issues)

## For Maintainers

**Release process and advanced topics:** See [MAINTAINERS.md](MAINTAINERS.md)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Homelab MCP! 🚀
