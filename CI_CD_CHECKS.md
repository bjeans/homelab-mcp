# Automated Checks and CI/CD Overview

This document describes all automated checks configured for the Homelab MCP project.

## 🎯 Overview

The project uses multiple layers of automated checks to ensure code quality, security, and compatibility:

1. **Local MCP Testing** - Test individual servers before committing (optional but recommended)
2. **Local Pre-Commit Checks** - Run before git push
3. **Local Development Checks** - Run manually during development
4. **GitHub Actions CI/CD** - Run automatically on push/PR
5. **Scheduled Checks** - Run periodically for maintenance

---

## 🧪 Local MCP Testing with Inspector

**Recommended:** Test your MCP servers locally before running automated checks. This helps catch functional issues early.

### Prerequisites

Install the MCP Inspector tool:

```bash
npm install -g @modelcontextprotocol/inspector
```

### Testing Individual Servers

From the `Homelab-MCP` directory, use the MCP Inspector to test each server:

```bash
# General format
npx @modelcontextprotocol/inspector uv --directory . run <server_file>

# Examples:
npx @modelcontextprotocol/inspector uv --directory . run ollama_mcp.py
npx @modelcontextprotocol/inspector uv --directory . run docker_mcp_podman.py
npx @modelcontextprotocol/inspector uv --directory . run pihole_mcp.py
npx @modelcontextprotocol/inspector uv --directory . run ansible_mcp_server.py
npx @modelcontextprotocol/inspector uv --directory . run unifi_mcp_optimized.py
```

### Using the Inspector

1. Command opens a web-based debugger at `http://localhost:5173`
2. Interface shows all available tools for the MCP server
3. Test each tool with sample arguments
4. Verify responses are correct and properly formatted
5. Check for error messages or unexpected behavior
6. Terminal displays debug logs and errors (useful for development)

### Common Testing Workflow

```bash
# 1. Make your code changes to an MCP server
# 2. Test with MCP Inspector
npx @modelcontextprotocol/inspector uv --directory . run your_mcp.py

# 3. In browser: Test each tool with appropriate arguments
#    - Verify responses match expected format
#    - Check error handling for invalid inputs
#    - Confirm no sensitive data in responses

# 4. Review terminal output for debug logs
# 5. Stop MCP Inspector (Ctrl+C)

# 6. Then proceed to automated checks:
python helpers/run_checks.py
```

### Troubleshooting MCP Inspector Tests

**Server fails to start:**
- Verify `.env` file exists with required credentials
- Check Ansible inventory file exists (if applicable)
- Verify Python dependencies installed: `pip install -r requirements.txt`
- Check for syntax errors: `python -m py_compile your_mcp.py`

**Tools not showing up:**
- Verify `@server.list_tools()` decorator is present
- Confirm tools are properly defined
- Check server stdout/stderr in terminal

**Tool calls fail:**
- Verify `@server.call_tool()` decorator exists
- Test with valid arguments first
- Check `.env` configuration is correct
- Review error messages in terminal

**Response format issues:**
- All tool results must return `list[types.TextContent]`
- Verify: `return [types.TextContent(type="text", text="result")]`
- Check logging goes to stderr, not stdout

### When to Use Local Testing

- **Before submitting PRs** - Catch functional issues early
- **After major changes** - Verify tool implementations work as expected
- **When adding new tools** - Test each tool individually
- **Debugging** - Use MCP Inspector to isolate issues
- **Before automated checks** - Ensure basic functionality works

---

## 📋 Local Checks

### Pre-Push Hook (Automatic)

**File:** `.git/hooks/pre-push`  
**Install:** `python install_git_hook.py`  
**When:** Automatically before every `git push`

**What it checks:**
- ✅ No sensitive files committed (.env, ansible_hosts.yml)
- ✅ Example files are present
- ✅ No hardcoded credentials in Python files
- ✅ No real IP addresses in documentation
- ✅ All documentation files exist

**Bypass:** `git push --no-verify` (use with caution!)

---

### Development Checks (Manual)

**File:** `run_checks.py`  
**Usage:**
```bash
# Install dev dependencies once
python run_checks.py --install-deps

# Run all checks
python run_checks.py

# Fast checks only (quick validation)
python run_checks.py --fast

# Security checks only
python run_checks.py --security

# Auto-fix formatting issues
python run_checks.py --format
```

**What it checks:**
- ✅ **Black** - Code formatting (PEP 8 compliant)
- ✅ **isort** - Import statement sorting
- ✅ **Flake8** - Style guide enforcement
- ✅ **Pylint** - Comprehensive linting
- ✅ **MyPy** - Static type checking
- ✅ **Bandit** - Security issue detection
- ✅ **Safety** - Dependency vulnerabilities
- ✅ **Python compilation** - Syntax validation
- ✅ **YAML validation** - Config file validation

---

## 🤖 GitHub Actions Workflows

### 1. Security Check
**File:** `.github/workflows/security-check.yml`  
**Triggers:** Push to main/develop, Pull requests  
**Badge:** ![Security Check](https://github.com/bjeans/homelab-mcp/actions/workflows/security-check.yml/badge.svg)

**What it does:**
- Runs `pre_publish_check.py`
- Verifies no sensitive files in repo
- Blocks merge if security issues found

**Purpose:** Prevent accidental exposure of credentials, IPs, or sensitive data

---

### 2. Python Linting and Code Quality
**File:** `.github/workflows/lint.yml`  
**Triggers:** Push to main/develop, Pull requests  
**Badge:** ![Lint](https://github.com/bjeans/homelab-mcp/actions/workflows/lint.yml/badge.svg)

**What it does:**
- Black formatting check
- isort import sorting
- Flake8 style enforcement
- Pylint comprehensive linting
- Bandit security scanning
- MyPy type checking

**Purpose:** Maintain consistent code quality and catch common errors

---

### 3. Dependency Security Audit
**File:** `.github/workflows/dependency-audit.yml`  
**Triggers:** 
- Push to main/develop
- Pull requests
- Weekly schedule (Mondays at 9am UTC)

**Badge:** ![Security Audit](https://github.com/bjeans/homelab-mcp/actions/workflows/dependency-audit.yml/badge.svg)

**What it does:**
- Scans dependencies with Safety
- Audits packages with pip-audit
- Checks for outdated packages

**Purpose:** Early detection of vulnerable dependencies

---

### 4. Python Compatibility Testing
**File:** `.github/workflows/test-compatibility.yml`  
**Triggers:** Push to main/develop, Pull requests  
**Badge:** ![Compatibility](https://github.com/bjeans/homelab-mcp/actions/workflows/test-compatibility.yml/badge.svg)

**What it does:**
- Tests Python 3.10, 3.11, 3.12, 3.13
- Tests on Ubuntu, Windows, macOS
- Verifies imports work
- Checks all MCP servers compile

**Purpose:** Ensure cross-platform and multi-version compatibility

---

### 5. Documentation Checks
**File:** `.github/workflows/documentation.yml`  
**Triggers:** Push to main/develop, Pull requests  
**Badge:** ![Docs](https://github.com/bjeans/homelab-mcp/actions/workflows/documentation.yml/badge.svg)

**What it does:**
- Checks for broken links in markdown
- Spell checks documentation
- Validates YAML syntax
- Verifies all example files exist
- Confirms core docs are present

**Purpose:** Maintain high-quality, accurate documentation

---

## 🔧 Configuration Files

### Code Quality Configuration
**File:** `setup.cfg`

Contains settings for:
- Flake8 (line length, exclusions, complexity)
- MyPy (type checking rules)
- Pytest (test configuration)
- Coverage (coverage reporting)
- Pylint (linting rules)
- isort (import sorting)
- Black (code formatting)

### Development Dependencies
**File:** `requirements-dev.txt`

Install with:
```bash
pip install -r requirements-dev.txt
```

Includes:
- **Linting:** flake8, pylint, black, isort, mypy
- **Security:** bandit, safety, pip-audit
- **Testing:** pytest, pytest-asyncio, pytest-cov
- **Documentation:** pydocstyle
- **YAML:** yamllint

---

## 📊 Recommended Workflow

### Daily Development
```bash
# 1. Make your changes
git add .

# 2. Run fast checks
python run_checks.py --fast

# 3. Fix any formatting issues
python run_checks.py --format

# 4. Commit and push (pre-push hook runs automatically)
git commit -m "Your changes"
git push
```

### Before Major Commits
```bash
# Run comprehensive checks
python run_checks.py

# Review and fix all issues
# Then commit and push
```

### Weekly Maintenance
```bash
# Check for outdated dependencies
pip list --outdated

# Update dependencies (carefully!)
pip install --upgrade <package>

# Run full security audit
python run_checks.py --security
```

---

## 🎭 Optional: Pre-Commit Framework

For even more automation, consider using [pre-commit](https://pre-commit.com/):

```bash
pip install pre-commit
```

Create `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.1.1
    hooks:
      - id: black
        language_version: python3.10
  
  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
  
  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
  
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: ['-c', 'setup.cfg']
```

Install: `pre-commit install`

---

## 🚀 CI/CD Status

Check all workflow statuses at:
https://github.com/bjeans/homelab-mcp/actions

Individual workflow badges are in the README.md.

---

## 🔍 Troubleshooting

### Workflow fails but passes locally
- Ensure you're using the same Python version
- Check GitHub Actions logs for specific errors
- Verify all dependencies are in requirements.txt

### Too many linting errors
- Run `python run_checks.py --format` to auto-fix
- Review `setup.cfg` to adjust rules if needed
- Use `# noqa` comments for legitimate exceptions

### Pre-push hook blocks commit
- Review the error messages carefully
- Fix the issues or use `--no-verify` if absolutely necessary
- Never bypass security checks without reviewing!

---

## 📈 Future Enhancements

Consider adding:
- **Unit tests** - Test individual MCP server functions
- **Integration tests** - Test actual API connections
- **Code coverage** - Track test coverage percentage
- **Mutation testing** - Test the quality of tests
- **Performance benchmarks** - Track performance over time
- **Docker image scanning** - If containerizing
- **License compliance** - Verify dependency licenses

---

## 🎯 Summary

**Five layers of protection:**
1. ✅ Local pre-push hook (automatic)
2. ✅ Local development checks (manual)
3. ✅ GitHub Actions CI/CD (automatic)
4. ✅ Scheduled security audits (weekly)
5. ✅ Cross-platform compatibility testing

**Result:** High-quality, secure, maintainable code that works across platforms! 🎉
