# Security Policy

## Overview

This project provides MCP (Model Context Protocol) servers for managing homelab infrastructure. Because it interacts with critical infrastructure components (containers, DNS, network devices, AI models), security is paramount.

## 🔒 Security Best Practices

### Configuration Security

#### Environment Variables
- **NEVER commit `.env` files** to version control
- Use `.env.example` as a template
- Generate unique API keys for each service
- Rotate API keys regularly (recommended: every 90 days)
- Use strong, randomly-generated API keys (minimum 32 characters)

#### Ansible Inventory
- **NEVER commit `ansible_hosts.yml`** with real infrastructure details
- Use `ansible_hosts.example.yml` as a template
- Keep production inventory files outside the git repository
- Use Ansible Vault for sensitive variables in production

#### Project Instructions
- **NEVER commit `PROJECT_INSTRUCTIONS.md`** with real infrastructure details
- Use `PROJECT_INSTRUCTIONS.example.md` as a template
- Customize with your actual infrastructure only in your local environment

#### Claude Customizations
- **NEVER commit `CLAUDE_CUSTOM.md`** with real infrastructure details
- Use `CLAUDE_CUSTOM.example.md` as a template
- This file allows Claude to understand your specific homelab setup
- Include server names and patterns, but **NOT credentials** (use `.env` for secrets)
- File is gitignored by default to prevent accidental commits
- See `CLAUDE.md` section on "Local Customizations" for usage details

### Automated Security Validation

#### Pre-Publish Security Check

The project includes automated security scanning via `helpers/pre_publish_check.py` to prevent accidental exposure of sensitive data.

**Install the pre-push git hook (recommended):**
```bash
python helpers/install_git_hook.py
```

**What it does:**
- Automatically runs before every `git push`
- Blocks pushes containing potential secrets or sensitive data
- Protects against accidentally committing API keys, passwords, or personal information

**Manual security check:**
```bash
python helpers/pre_publish_check.py
```

**Bypass security check (use with extreme caution):**
```bash
git push --no-verify  # Only when absolutely necessary
```

#### Context-Aware Infrastructure Scanning

The security scanner includes intelligent detection that uses your Ansible inventory to identify real infrastructure details in code.

**How it works:**

1. **Loads Your Ansible Inventory**
   - Reads from `ANSIBLE_INVENTORY_PATH` in `.env`
   - Falls back to `ansible_hosts.yml` if no path specified
   - Extracts all IP addresses, hostnames, and domains from your inventory

2. **Scans Public Files**
   - Python files (`.py`)
   - Example markdown files (`*.example.md`, `README.md`, etc.)
   - Example YAML files (`*.example.yml`, `*.example.yaml`)
   - Other documentation files

3. **Context-Aware Detection**
   - Knows YOUR specific infrastructure details
   - Detects real IPs/hostnames even when used as "examples"
   - Filters out legitimate example contexts (lines with "example", "replace", "placeholder", etc.)
   - Uses word boundaries to avoid false positives

**Benefits:**
- ✅ No hardcoded secrets in the security tool itself
- ✅ Catches AI mistakes (when assistants accidentally use your real infrastructure)
- ✅ Context-aware (knows YOUR hostnames, not just generic patterns)
- ✅ Smart filtering (ignores legitimate documentation examples)
- ✅ Graceful degradation (skips check if Ansible inventory not found)

**Example output:**
```
======================================================================
Scanning for Real Infrastructure Details (Context-Aware)
======================================================================

Loaded 22 IP addresses, 24 hostnames, 3 domains from inventory
✓ ansible_mcp_server.py: No real infrastructure details found
✓ docker_mcp_podman.py: No real infrastructure details found
✗ README.md: Found real infrastructure details!
  → Real IP address: 192.0.2.100
  → Real hostname: Server-01

✗ ❌ Found references to real infrastructure in files that will be committed!
✗ These files should only contain example/placeholder data.
```

**What gets scanned:**

Extracted from Ansible inventory:
- **IP Addresses**: From `ansible_host`, `ip`, `address` fields
- **Hostnames**: All host entries in the inventory
- **Domains**: Extracted from FQDNs (e.g., `server.home.local` → `home.local`)

Files scanned:
- All Python files (except `pre_publish_check.py` itself)
- Example templates (`*.example.md`, `*.example.yml`)
- Public documentation (`README.md`, `SECURITY.md`, `CONTRIBUTING.md`, etc.)

Files NOT scanned (gitignored):
- `.env`
- `PROJECT_INSTRUCTIONS.md`
- `CLAUDE_CUSTOM.md`
- `ansible_hosts.yml`

**Setup:**

Set `ANSIBLE_INVENTORY_PATH` in your `.env`:
```bash
ANSIBLE_INVENTORY_PATH=/path/to/ansible_hosts.yml
```

Or place `ansible_hosts.yml` in project root (it's gitignored by default).

**Smart filtering:**

The scanner won't flag these contexts:
- Lines containing: "example", "replace", "your-ip", "your-host"
- Lines containing: "placeholder", "template", "e.g.", "i.e."
- Common domains: "local", "com", "net", "org", "home"

This prevents false positives in documentation that instructs users to "replace with your IP".

**Troubleshooting:**

- **"Ansible inventory not found - skipping context-aware infrastructure scan"**
  - Solution: Set `ANSIBLE_INVENTORY_PATH` in `.env` or create `ansible_hosts.yml`

- **"PyYAML not installed - skipping Ansible inventory check"**
  - Solution: `pip install pyyaml`

- **False Positives**
  - If legitimate examples are flagged, ensure the line contains words like "example", "replace", "your-ip", or "placeholder"

### Network Security

#### Docker/Podman APIs
⚠️ **CRITICAL SECURITY WARNING**

Docker and Podman APIs accessed by this project use **unencrypted HTTP connections** and typically have **no authentication** by default.

**Required Security Measures:**
1. **NEVER expose Docker/Podman APIs to the internet**
2. **Use firewall rules** to restrict API access to trusted networks only
3. **Consider using SSH tunneling** for remote access
4. **Enable TLS with client certificates** (mTLS) in production
5. **Use Docker socket proxy** (like tecnativa/docker-socket-proxy) to limit API access

**Firewall Configuration Example (Linux):**
```bash
# Allow only from local network
iptables -A INPUT -p tcp --dport 2375 -s 192.168.1.0/24 -j ACCEPT
iptables -A INPUT -p tcp --dport 2375 -j DROP
```

**Docker API with TLS:**
```bash
# Generate certificates
openssl genrsa -out ca-key.pem 4096
openssl req -new -x509 -days 365 -key ca-key.pem -sha256 -out ca.pem

# Configure Docker daemon
{
  "tls": true,
  "tlscacert": "/etc/docker/ca.pem",
  "tlscert": "/etc/docker/server-cert.pem",
  "tlskey": "/etc/docker/server-key.pem",
  "hosts": ["tcp://0.0.0.0:2376"]
}
```

#### Pi-hole API Security
1. **Generate unique API keys** for each Pi-hole instance
   - Pi-hole Settings → API → Generate new API key
   - Command line: `pihole -a -p`
2. **NEVER reuse API keys** between environments
3. **Store keys in `.env` file only** - never hardcode in scripts
4. **Use HTTPS** when accessing Pi-hole remotely
5. **Limit API key permissions** if possible in future Pi-hole versions

#### Unifi Controller Security
1. **Use dedicated API key** with minimal required permissions
2. **Enable 2FA** on Unifi controller admin account
3. **Restrict controller access** to management VLAN
4. **Keep controller software updated**
5. **Use HTTPS only** for controller access

#### Ollama/LiteLLM Security
1. **Do not expose Ollama ports** to the internet
2. **Use authentication** on LiteLLM proxy (if exposed externally)
3. **Implement rate limiting** to prevent abuse
4. **Monitor for unusual API usage**
5. **Keep models and software updated**

#### Network Isolation
**Recommended VLAN Structure:**
- Management VLAN: MCP client, Ansible controller
- Services VLAN: Docker hosts, Ollama, Pi-hole
- IoT VLAN: Unifi devices (separate from services)
- Guest VLAN: Isolated from management and services

### Access Control

#### MCP Server Access
- MCP servers run with **Claude Desktop's privileges**
- They have **file system access** to the MCP directory
- They can **execute system commands** (unifi_exporter.py subprocess)
- They can **make network requests** to configured services

**Security Implications:**
- **Limit file write permissions** in MCP Registry Inspector (deprecated v2.3.0)
- **Validate all file paths** to prevent directory traversal
- **Sanitize command arguments** to prevent injection
- **Use minimal network permissions**

#### Principle of Least Privilege
1. **Docker API**: Consider using read-only API proxy
2. **Ansible**: Use read-only inventory queries only
3. **Network access**: Firewall rules to limit connections

### Data Protection

#### Sensitive Data Handling
**Never include in code or logs:**
- API keys and passwords
- Private IP addresses (in public repositories)
- Internal hostnames
- Network topology details
- User credentials
- Authentication tokens

**Safe Data Storage:**
- Use environment variables (`.env` file)
- Use Ansible Vault for sensitive playbook variables
- Use secrets management tools (HashiCorp Vault, etc.) in production
- Encrypt backups containing configuration files

**File Permissions (Linux/Mac):**
```bash
chmod 600 .env  # Read/write for owner only
chown $USER:$USER .env
```

#### Logging Security
Current implementation logs to `stderr`. Be aware that logs may contain:
- API endpoints (URLs)
- Host information
- Error messages with partial data

**Recommendations:**
- Review logs before sharing for troubleshooting
- Implement log sanitization for sensitive data
- Use log rotation to prevent disk filling
- Secure log files with appropriate permissions

### Code Security

#### Input Validation
The project implements basic input validation, but you should:
1. **Validate port numbers** (1-65535 range)
2. **Sanitize file paths** (prevent directory traversal)
3. **Validate hostnames** (prevent DNS rebinding)
4. **Check API response sizes** (prevent memory exhaustion)

#### Subprocess Security
The Unifi exporter uses subprocess calls:
```python
# CURRENT: API key visible in process list
cmd = ['python', 'script.py', '--api-key', KEY]

# BETTER: Use environment variables
env['UNIFI_API_KEY'] = KEY
cmd = ['python', 'script.py']
```

**Known Issue**: API keys may be visible in process listings. Consider passing via environment instead.

#### Dependency Security
- Keep Python dependencies updated: `pip install -U -r requirements.txt`
- Monitor for security advisories in dependencies
- Use `pip-audit` to check for known vulnerabilities
- Pin dependency versions in `requirements.txt`

### Transport Security

#### API Communication
Current implementation uses **HTTP** (unencrypted) for most API calls:
- Docker/Podman APIs
- Ollama APIs
- Pi-hole APIs
- Unifi Controller API (depends on configuration)

**For Production:**
1. **Enable TLS/HTTPS** on all services
2. **Validate SSL certificates** (set `verify=True` in aiohttp)
3. **Use certificate pinning** for critical services
4. **Implement mTLS** for Docker API

## 🚨 Reporting Security Vulnerabilities

If you discover a security vulnerability in this project:

1. **DO NOT** create a public GitHub issue
2. **DO NOT** disclose the vulnerability publicly
3. **Email the maintainer** with details (if provided)
4. **Or create a private security advisory** on GitHub

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if you have one)

## 📋 Security Checklist for Deployment

Before deploying this project in your homelab:

### Initial Setup
- [ ] Copy `.env.example` to `.env` and configure
- [ ] Generate unique API keys for all services
- [ ] Copy `ansible_hosts.example.yml` and customize
- [ ] Copy `PROJECT_INSTRUCTIONS.example.md` and customize
- [ ] Verify `.gitignore` excludes sensitive files
- [ ] Review and understand all security implications
- [ ] Install pre-push git hook: `python helpers/install_git_hook.py`

### Network Security
- [ ] Configure firewall rules for Docker/Podman APIs
- [ ] Verify APIs are not exposed to internet
- [ ] Enable TLS on all external-facing services
- [ ] Implement network segmentation (VLANs)
- [ ] Set up monitoring for unusual network activity

### Access Control
- [ ] Use unique credentials per service
- [ ] Implement 2FA where available
- [ ] Apply principle of least privilege
- [ ] Regular audit of API key usage
- [ ] Monitor for unauthorized access attempts

### Monitoring & Auditing
- [ ] Set up log aggregation
- [ ] Monitor for failed authentication attempts
- [ ] Alert on unusual API usage patterns
- [ ] Regular security audits of configurations
- [ ] Keep inventory of all API keys and their purposes

### Maintenance
- [ ] Schedule regular security updates
- [ ] Rotate API keys quarterly
- [ ] Review and update firewall rules
- [ ] Test disaster recovery procedures
- [ ] Keep documentation updated

## 📅 Revision History

- **2026-01**: Merged context-aware security scanning documentation
- **2024-10**: Initial security policy created

---

**Remember**: Security is not a one-time setup but an ongoing process. Stay vigilant, keep software updated, and regularly review your security posture.
