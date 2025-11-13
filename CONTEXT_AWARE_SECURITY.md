# Context-Aware Security Scanning

## Overview

The `pre_publish_check.py` script now includes **context-aware infrastructure scanning** that uses your Ansible inventory to detect real hostnames, IP addresses, and domain names in code that's about to be committed.

## How It Works

### 1. **Loads Your Ansible Inventory**
   - Reads from `ANSIBLE_INVENTORY_PATH` in `.env`
   - Falls back to `ansible_hosts.yml` if no path specified
   - Extracts all IP addresses, hostnames, and domains from your inventory

### 2. **Scans Public Files**
   - Python files (`.py`)
   - Example markdown files (`*.example.md`, `README.md`, etc.)
   - Example YAML files (`*.example.yml`, `*.example.yaml`)
   - Other documentation files

### 3. **Context-Aware Detection**
   - Knows YOUR specific infrastructure details
   - Detects real IPs/hostnames even when used as "examples"
   - Filters out legitimate example contexts (lines with "example", "replace", "placeholder", etc.)
   - Uses word boundaries to avoid false positives

## Benefits

✅ **No Hardcoded Secrets** - The security tool itself contains no sensitive data  
✅ **Catches AI Mistakes** - Detects when AI assistants accidentally use your real infrastructure  
✅ **Context-Aware** - Knows YOUR hostnames, not just generic patterns  
✅ **Smart Filtering** - Ignores legitimate documentation examples  
✅ **Graceful Degradation** - Skips check if Ansible inventory not found

## Example Output

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

## What Gets Scanned

### Extracted from Ansible Inventory:
- **IP Addresses**: From `ansible_host`, `ip`, `address` fields
- **Hostnames**: All host entries in the inventory
- **Domains**: Extracted from FQDNs (e.g., `server.home.local` → `home.local`)

### Files Scanned:
- All Python files (except `pre_publish_check.py` itself)
- Example templates (`*.example.md`, `*.example.yml`)
- Public documentation (`README.md`, `SECURITY.md`, `CONTRIBUTING.md`, etc.)

### Files NOT Scanned:
- `.env` (gitignored)
- `PROJECT_INSTRUCTIONS.md` (gitignored)
- `CLAUDE.md` (gitignored)
- `ansible_hosts.yml` (gitignored)

## Setup

### Automatic (Recommended)
If you have `ANSIBLE_INVENTORY_PATH` in your `.env`:
```bash
ANSIBLE_INVENTORY_PATH=/path/to/ansible_hosts.yml
```

### Fallback
Place `ansible_hosts.yml` in project root (it's gitignored by default)

### Skip Check
If no Ansible inventory is found, the check is automatically skipped with a warning.

## Smart Filtering

The scanner won't flag these contexts:
- Lines containing: "example", "replace", "your-ip", "your-host"
- Lines containing: "placeholder", "template", "e.g.", "i.e."
- Common domains: "local", "com", "net", "org", "home"

This prevents false positives in documentation that instructs users to "replace with your IP".

## Use Cases

### ✅ Catches These Problems:
```python
# AI accidentally uses your real hostname
docker_host = "Server-01"  # ❌ CAUGHT!

# Using real IP as example
EXAMPLE_HOST = "192.0.2.100"  # ❌ CAUGHT!
```

### ✅ Allows These Examples:
```markdown
# Good documentation
Replace `example-host` with your hostname
Use your IP address instead of `192.0.2.1`
```

## Requirements

- Python 3.10+
- PyYAML (for parsing Ansible inventory)
  ```bash
  pip install pyyaml
  ```

## Integration

The check runs automatically:
1. When you run `python helpers/pre_publish_check.py`
2. As part of the git pre-push hook
3. In CI/CD pipelines

## Troubleshooting

### "Ansible inventory not found - skipping context-aware infrastructure scan"
**Solution**: Set `ANSIBLE_INVENTORY_PATH` in `.env` or create `ansible_hosts.yml`

### "PyYAML not installed - skipping Ansible inventory check"
**Solution**: `pip install pyyaml`

### False Positives
If you get false positives for legitimate examples, ensure the line contains words like:
- "example"
- "replace"
- "your-ip" or "your-host"
- "placeholder"

## Security Philosophy

This approach solves the catch-22:
- **Problem**: How do you check for YOUR infrastructure without hardcoding it?
- **Solution**: Use the already-gitignored Ansible inventory as the source of truth
- **Result**: Context-aware scanning with zero secrets in the security tool itself

## Maintenance

The check automatically updates when you:
- Add new hosts to Ansible inventory
- Change IP addresses
- Update domain names

No maintenance needed - it reads fresh from inventory each run.
