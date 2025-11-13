# Local Homelab Customizations for Claude

> **Note:** This is an example template. Copy this file to `CLAUDE_CUSTOM.md` and customize it with your actual homelab details.
>
> ```bash
> cp CLAUDE_CUSTOM.example.md CLAUDE_CUSTOM.md
> ```
>
> `CLAUDE_CUSTOM.md` is gitignored and will not be committed to the repository.

## Purpose

This file contains **homelab-specific customizations** that Claude should be aware of when working with your infrastructure. This includes:

- Actual server names and infrastructure identifiers
- Custom operational workflows specific to your setup
- Infrastructure-specific task examples
- Local naming conventions and patterns
- Environment-specific troubleshooting notes

## Your Infrastructure Overview

**Replace this section with details about your specific homelab setup:**

```yaml
# Example: Document your key infrastructure components
infrastructure:
  servers:
    - name: [your-main-server]        # e.g., "Dell-R720", "ProxmoxHost1"
      role: [primary/backup/compute]
      location: [rack/desk/closet]

    - name: [your-secondary-server]   # e.g., "NUC-01", "HL16"
      role: [role description]
      location: [physical location]

  network:
    - device: [your-router]            # e.g., "UDM-Pro", "pfSense"
      management_ip: [IP or hostname]

    - device: [your-switch]            # e.g., "US-24-POE"
      management_ip: [IP or hostname]

  storage:
    - device: [your-nas]               # e.g., "Synology-DS920", "TrueNAS"
      primary_purpose: [backups/media/vm-storage]
      mount_points: [relevant paths]
```

## Custom Task Examples

### Operational Tasks

Document common operational tasks specific to your homelab infrastructure:

**Template:**
```
- "Schedule [your-server-name] reboot for maintenance window"
- "Upgrade [service-name] on [your-server-name]"
- "Verify [your-backup-system] completed successfully"
- "Check [your-monitoring-service] alerts for [server-name]"
- "Test [your-failover-setup] procedures"
- "Rotate API credentials for [your-services]"
```

**Your Examples:**
```
# Replace these with your actual task patterns:
- "Schedule [SERVER-NAME] reboot for maintenance window"
- "Upgrade Ollama models to latest on [NODE-NAMES]"
- "Verify [BACKUP-SERVICE] completed successfully"
- "Check NUT battery health on [UPS-IDENTIFIER]"
- "Test network failover for [PRIMARY-NETWORK-DEVICE]"
- "Rotate API credentials for [SERVICE-LIST]"
```

### Maintenance Tasks

**Template:**
```
- "Update Ansible inventory with new [host-identifier]"
- "Review [container-platform] logs on [server-name]"
- "Monitor disk usage on [storage-system]"
- "Check certificate expiry for [domain/service]"
- "Clean up old snapshots on [hypervisor/storage]"
- "Update firmware on [device-name]"
```

**Your Examples:**
```
# Replace these with your actual maintenance patterns:
- "Update Ansible inventory with new [HOST-ID] host"
- "Review Docker container logs on [SERVER-NAME]"
- "Monitor disk usage on [NAS-NAME] storage"
- "Check certificate expiry for [YOUR-DOMAINS]"
- "Clean up old snapshots on [HYPERVISOR-NAME]"
- "Update firmware on [NETWORK-DEVICE]"
```

### Decisions and Reminders

**Template:**
```
- "Document decision to use [technology-choice] for [use-case]"
- "Remember to test [specific-feature] before production deployment"
- "Remind about [policy/procedure] when making infrastructure changes"
- "Track [specific-issue] that needs investigation"
- "Follow up on [planned-upgrade] after testing period"
```

**Your Examples:**
```
# Replace these with your actual decision patterns:
- "Document decision to use [CONFIG-APPROACH] for infrastructure"
- "Remember to test [FAILOVER-SCENARIO] before production use"
- "Remind about [CHANGE-POLICY] when modifying services"
- "Track [SPECIFIC-ISSUE] for future resolution"
- "Follow up on [PLANNED-CHANGE] after validation"
```

## Custom Naming Conventions

Document any specific naming patterns used in your homelab:

**Template:**
```yaml
servers:
  pattern: "[prefix]-[number]"       # e.g., "HL16" = Homelab-16
  examples:
    - physical: [name-pattern]
    - virtual: [name-pattern]

containers:
  pattern: "[service-name]-[env]"    # e.g., "pihole-prod"
  examples: [your-examples]

networks:
  pattern: "[vlan-id]-[purpose]"     # e.g., "10-management"
  vlans:
    - id: [number]
      name: [name]
      purpose: [purpose]
```

**Your Conventions:**
```yaml
# Replace with your actual naming conventions:
servers:
  pattern: "[your-pattern]"
  examples:
    - physical:
    - virtual:

containers:
  pattern: "[your-pattern]"
  examples: []

networks:
  pattern: "[your-pattern]"
  vlans:
    - id:
      name:
      purpose:
```

## Environment-Specific Configuration Notes

### Ansible Inventory Location

```bash
# Your actual Ansible inventory path (already in .env, but document here for reference)
ANSIBLE_INVENTORY_PATH="/path/to/your/ansible_hosts.yml"
```

### Service Endpoints

Document non-standard service locations or ports:

```yaml
# Example customizations:
services:
  pihole:
    primary: "[hostname/IP]:[port]"
    backup: "[hostname/IP]:[port]"

  docker:
    hosts:
      - "[host1]:[port]"
      - "[host2]:[port]"

  unifi:
    controller: "[hostname/IP]:[port]"

  # Add your other services...
```

## Common Troubleshooting Scenarios

Document specific issues and solutions for your environment:

**Template:**
```markdown
### [Issue Description]

**Symptoms:**
- [What you observe]

**Cause:**
- [Why it happens in your environment]

**Resolution:**
- [Steps to fix]

**Prevention:**
- [How to avoid in future]
```

**Your Scenarios:**
```markdown
### [Add your common issues here]

**Example: Service X doesn't start after server reboot**

**Symptoms:**
- [Your symptoms]

**Cause:**
- [Your cause]

**Resolution:**
- [Your steps]

**Prevention:**
- [Your prevention]
```

## Integration Notes

### Custom MCP Tools or Modifications

Document any custom tools you've added or modifications you've made:

```markdown
### Custom Tool: [tool-name]

**Purpose:** [what it does]

**Usage:** `@[tool_name] [arguments]`

**Example:**
[your example]

**Notes:**
- [special considerations]
- [dependencies]
```

### Workflow Integrations

Document how this project integrates with your other tools:

```markdown
### Integration with [Tool/System Name]

**Purpose:** [why you integrate]

**Setup:**
1. [step 1]
2. [step 2]

**Usage:**
[how to use]
```

## Quick Reference Commands

Document your most-used commands specific to your homelab:

```bash
# Custom aliases or shortcuts you use
alias [your-alias]='[your-command]'

# Environment-specific commands
[your-commands]

# Monitoring shortcuts
[your-shortcuts]
```

## Notes for Claude

> Add any specific instructions you want Claude to remember when working with your homelab:

**Example instructions:**
- "Always check [specific-service] health before making changes to [specific-component]"
- "When modifying [specific-system], remember to notify [method/person]"
- "Prefer [approach-A] over [approach-B] for [specific-task] in this environment"
- "[Any other context-specific guidance]"

**Your Instructions:**
```
# Add your specific instructions here:
-
-
-
```

---

## Maintenance

**Last Updated:** [Date]
**Homelab Version/State:** [Your versioning or state description]

## Reminders

- Keep this file updated as your infrastructure evolves
- This file is gitignored - never commit actual infrastructure details
- Review periodically to ensure accuracy
- Document new patterns as they emerge
- Keep sensitive information (IPs, credentials) in `.env`, not here
