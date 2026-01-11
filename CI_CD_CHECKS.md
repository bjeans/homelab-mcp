# Automated Checks and CI/CD

Quick reference for automated checks configured for the Homelab MCP project.

## Overview

Multiple layers of automated checks ensure code quality, security, and compatibility:

1. **Local MCP Testing** - Test individual servers before committing (optional)
2. **Local Pre-Push Checks** - Run automatically before git push
3. **Local Development Checks** - Run manually during development
4. **GitHub Actions CI/CD** - Run automatically on push/PR
5. **Scheduled Checks** - Run periodically for maintenance

---

## Local MCP Testing with Inspector

**Recommended:** Test your MCP servers locally before running automated checks.

### Quick Start

```bash
# Use npx (no installation needed - recommended)
npx @modelcontextprotocol/inspector uv --directory . run <server_file>

# Or install globally once
npm install -g @modelcontextprotocol/inspector
```

### Test Individual Servers

```bash
npx @modelcontextprotocol/inspector uv --directory . run ollama_mcp.py
npx @modelcontextprotocol/inspector uv --directory . run docker_mcp_podman.py
npx @modelcontextprotocol/inspector uv --directory . run pihole_mcp.py
npx @modelcontextprotocol/inspector uv --directory . run ansible_mcp_server.py
npx @modelcontextprotocol/inspector uv --directory . run unifi_mcp_optimized.py
```

Opens web debugger at `http://localhost:5173` for interactive tool testing.

### What to Test

1. Open terminal in `Homelab-MCP` directory
2. Run MCP Inspector command for your server
3. Browser opens to debugger interface
4. Test each tool with appropriate arguments
5. Verify responses are correct
6. Check error handling
7. Review logs in terminal

---

## Local Checks

### Pre-Push Hook (Automatic)

**Install once:**
```bash
python helpers/install_git_hook.py
```

**What it checks:**
- ✅ No sensitive files committed (.env, ansible_hosts.yml)
- ✅ Example files are present
- ✅ No hardcoded credentials in Python files
- ✅ No real IP addresses in documentation
- ✅ All documentation files exist

**Bypass (use with caution):**
```bash
git push --no-verify
```

### Development Checks (Manual)

**Usage:**
```bash
# Install dev dependencies once
python helpers/run_checks.py --install-deps

# Run all checks
python helpers/run_checks.py

# Fast checks only
python helpers/run_checks.py --fast

# Security checks only
python helpers/run_checks.py --security

# Auto-fix formatting
python helpers/run_checks.py --format
```

**What it checks:**
- ✅ **Black** - Code formatting
- ✅ **isort** - Import sorting
- ✅ **Flake8** - Style guide enforcement
- ✅ **Pylint** - Comprehensive linting
- ✅ **MyPy** - Static type checking
- ✅ **Bandit** - Security issue detection
- ✅ **Safety** - Dependency vulnerabilities
- ✅ **Python compilation** - Syntax validation

---

## GitHub Actions Workflows

### 1. Security Check

**File:** `.github/workflows/security-check.yml`
**Triggers:** Push to main/develop, Pull requests

**What it does:**
- Runs `helpers/pre_publish_check.py`
- Verifies no sensitive files in repo
- Blocks merge if security issues found

### 2. Python Linting and Code Quality

**File:** `.github/workflows/lint.yml`
**Triggers:** Push to main/develop, Pull requests

**What it does:**
- Black formatting check
- isort import sorting
- Flake8 style enforcement
- Pylint comprehensive linting
- Bandit security scanning
- MyPy type checking

### 3. Dependency Security Audit

**File:** `.github/workflows/dependency-audit.yml`
**Triggers:** Push, Pull requests, Weekly schedule (Mondays 9am UTC)

**What it does:**
- Scans dependencies with Safety
- Audits packages with pip-audit
- Checks for outdated packages

### 4. Python Compatibility Testing

**File:** `.github/workflows/test-compatibility.yml`
**Triggers:** Push to main/develop, Pull requests

**What it does:**
- Tests Python 3.10, 3.11, 3.12, 3.13
- Tests on Ubuntu, Windows, macOS
- Verifies imports work
- Checks all MCP servers compile

### 5. Documentation Checks

**File:** `.github/workflows/documentation.yml`
**Triggers:** Push to main/develop, Pull requests

**What it does:**
- Checks for broken links
- Spell checks documentation
- Validates YAML syntax
- Verifies example files exist

---

## Configuration Files

### Code Quality Configuration

**File:** `setup.cfg`

Contains settings for:
- Flake8 (line length, exclusions, complexity)
- MyPy (type checking rules)
- Pylint (linting rules)
- isort (import sorting)
- Black (code formatting)

### Development Dependencies

**File:** `helpers/requirements-dev.txt`

Install with:
```bash
pip install -r helpers/requirements-dev.txt
```

Includes:
- **Linting:** flake8, pylint, black, isort, mypy
- **Security:** bandit, safety, pip-audit
- **Testing:** pytest, pytest-asyncio, pytest-cov

---

## Recommended Workflow

### Daily Development

```bash
# 1. Make changes
git add .

# 2. Run fast checks
python helpers/run_checks.py --fast

# 3. Fix formatting
python helpers/run_checks.py --format

# 4. Commit and push (hook runs automatically)
git commit -m "Your changes"
git push
```

### Before Major Commits

```bash
# Run comprehensive checks
python helpers/run_checks.py

# Review and fix all issues
# Then commit and push
```

---

## Troubleshooting

### Workflow Fails But Passes Locally

- Ensure same Python version
- Check GitHub Actions logs
- Verify dependencies in requirements.txt

### Too Many Linting Errors

- Run `python helpers/run_checks.py --format` to auto-fix
- Review `setup.cfg` to adjust rules
- Use `# noqa` comments for legitimate exceptions

### Pre-Push Hook Blocks Commit

- Review error messages carefully
- Fix issues or use `--no-verify` if absolutely necessary
- Never bypass security checks without reviewing

### MCP Inspector Not Working

- Verify `.env` file exists with credentials
- Check Ansible inventory file exists (if applicable)
- Verify dependencies: `pip install -r requirements.txt`
- Check for syntax errors: `python -m py_compile your_mcp.py`

---

## CI/CD Status

**Check all workflow statuses:**
https://github.com/bjeans/homelab-mcp/actions

**Individual workflow badges** are in README.md.

---

## Summary

**Five layers of protection:**
1. ✅ Local pre-push hook (automatic)
2. ✅ Local development checks (manual)
3. ✅ GitHub Actions CI/CD (automatic)
4. ✅ Scheduled security audits (weekly)
5. ✅ Cross-platform compatibility testing

**Result:** High-quality, secure, maintainable code that works across platforms!
