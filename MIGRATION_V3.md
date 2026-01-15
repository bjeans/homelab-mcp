# Migration Guide: v2.x to v3.0

## Overview

Version 3.0 represents a major architectural improvement to Homelab MCP, migrating from the standard MCP SDK to the FastMCP framework. This migration brings significant benefits but includes breaking changes to tool names for improved consistency.

## Why Upgrade?

**Benefits of v3.0:**
- **38% code reduction** (1,754 lines eliminated) - easier to maintain
- **Cleaner architecture** - FastMCP's decorator pattern vs manual class boilerplate
- **Tool annotations** - All 39 tools include behavioral hints (`readOnlyHint`, `idempotentHint`, etc.) to help Claude make informed decisions
- **Multiple transports** - stdio (default), HTTP, and SSE support
- **Better type safety** - Automatic schema generation from Python type hints
- **Faster development** - Add new tools with simple `@mcp.tool()` decorators
- **Consistent naming** - Tool names follow clear patterns (`list_*`, `get_*`)

## Breaking Changes

### Tool Name Changes

Version 3.0 standardizes tool naming conventions:
- `list_*` - Returns lists of items (hosts, containers, models)
- `get_*` - Returns detailed information about specific items

#### Ansible Tools

| v2.x Tool Name | v3.0 Tool Name | Change Reason |
|----------------|----------------|---------------|
| `ansible_get_all_hosts` | `ansible_list_all_hosts` | Consistency: lists use `list_*` |
| `ansible_get_all_groups` | `ansible_list_groups` | Consistency: lists use `list_*` |
| `ansible_get_host_details` | `ansible_get_host_details` | ✅ No change |
| `ansible_get_group_details` | `ansible_get_group_hosts` | Better clarity: returns list of hosts |
| `ansible_query_hosts` | `ansible_query_hosts` | ✅ No change |
| `ansible_reload_inventory` | `ansible_reload_inventory` | ✅ No change |

#### Docker Tools

| v2.x Tool Name | v3.0 Tool Name | Change Reason |
|----------------|----------------|---------------|
| `docker_get_containers` | `docker_list_containers` | Consistency: lists use `list_*` |
| `docker_get_all_containers` | `docker_list_containers` | Merged: same functionality |
| `docker_check_container` | `docker_get_container_details` | Better clarity |
| `docker_get_container_logs` | `docker_get_container_logs` | ✅ No change |
| `docker_get_container_stats` | `docker_get_stats` | Simplified |
| `docker_find_containers_by_label` | *(removed)* | Use `docker_list_containers` with filtering |
| `docker_get_container_labels` | *(removed)* | Included in `docker_get_container_details` |
| `docker_list_all_hosts` | `docker_list_all_hosts` | ✅ No change |
| `docker_reload_inventory` | `docker_reload_inventory` | ✅ No change |

#### Pi-hole Tools

| v2.x Tool Name | v3.0 Tool Name | Change Reason |
|----------------|----------------|---------------|
| `pihole_get_stats` | `pihole_get_summary` | Better clarity: summary of all stats |
| `pihole_get_status` | *(merged)* | Combined into `pihole_get_summary` |
| `pihole_list_hosts` | `pihole_list_hosts` | ✅ No change |
| `pihole_get_top_items` | `pihole_get_top_items` | ✅ No change |
| `pihole_get_query_types` | `pihole_get_query_types` | ✅ No change |
| `pihole_get_forward_destinations` | `pihole_get_forward_destinations` | ✅ No change |
| `pihole_reload_inventory` | `pihole_reload_inventory` | ✅ No change |

#### Ollama Tools

| v2.x Tool Name | v3.0 Tool Name | Change Reason |
|----------------|----------------|---------------|
| `ollama_get_status` | `ollama_list_hosts` | Better clarity: lists all Ollama hosts |
| `ollama_get_models` | `ollama_list_models` | Consistency: lists use `list_*` |
| `ollama_get_model_info` | `ollama_get_model_info` | ✅ No change |
| `ollama_get_running_models` | `ollama_get_running_models` | ✅ No change |
| `ollama_get_litellm_status` | *(removed)* | Use `ollama_list_hosts` |
| `ollama_reload_inventory` | `ollama_reload_inventory` | ✅ No change |

#### UPS/NUT Tools

| v2.x Tool Name | v3.0 Tool Name | Change Reason |
|----------------|----------------|---------------|
| `ups_list_ups_devices` | `ups_list_hosts` | Consistency with other servers |
| `ups_get_ups_status` | `ups_get_status` | Simplified |
| `ups_get_ups_details` | `ups_get_details` | Simplified |
| `ups_get_battery_runtime` | `ups_get_battery_info` | Better clarity: includes all battery info |
| `ups_get_power_events` | *(removed)* | Planned for future release |
| `ups_reload_inventory` | `ups_reload_inventory` | ✅ No change |

#### Ping Tools

| v2.x Tool Name | v3.0 Tool Name | Change Reason |
|----------------|----------------|---------------|
| `ping_ping_host` | `ping_host_by_name` | Better clarity |
| `ping_list_groups` | `ping_list_groups` | ✅ No change |
| `ping_list_hosts` | `ping_list_hosts` | ✅ No change |
| `ping_group` | `ping_group` | ✅ No change |
| `ping_all` | `ping_all` | ✅ No change |
| `ping_reload_inventory` | `ping_reload_inventory` | ✅ No change |

#### Unifi Tools

| v2.x Tool Name | v3.0 Tool Name | Notes |
|----------------|----------------|-------|
| All Unifi tools | *(no changes)* | ✅ Names unchanged |

## Migration Steps

### 1. Update Claude Desktop Workflows

If you have custom instructions or workflows that reference old tool names:

```markdown
<!-- OLD (v2.x) -->
When checking servers, use @ansible_get_all_hosts

<!-- NEW (v3.0) -->
When checking servers, use @ansible_list_all_hosts
```

### 2. Update Custom Scripts/Integrations

If you have scripts that invoke MCP tools programmatically:

```python
# OLD (v2.x)
result = mcp_client.call_tool("ansible_get_all_hosts")

# NEW (v3.0)
result = mcp_client.call_tool("ansible_list_all_hosts")
```

### 3. Update Docker Deployment

**No changes required** - Docker image name and configuration remain the same:

```bash
# Both v2.x and v3.0 use the same deployment
docker pull bjeans/homelab-mcp:latest
```

Just restart your containers to pick up the new version.

### 4. Test Common Workflows

After upgrading, test your most common workflows:

```bash
# Test Ansible tools
@ansible_list_all_hosts
@ansible_get_host_details hostname="server1"

# Test Docker tools
@docker_list_containers
@docker_get_container_details container_id="nginx"

# Test other tools
@pihole_get_summary
@ups_get_status
```

## Backward Compatibility

**None.** Version 3.0 intentionally breaks backward compatibility to establish a clean, consistent naming convention.

If you cannot update immediately:
- Pin to v2.2.1: `bjeans/homelab-mcp:v2.2.1`
- Update at your convenience within the next release cycle

## Getting Help

### Documentation
- **README.md** - Updated with v3.0 tool names
- **CLAUDE.md** - Updated development guide with FastMCP patterns
- **CHANGELOG.md** - Complete list of changes

### Support
- **GitHub Issues**: https://github.com/bjeans/homelab-mcp/issues
- **Discussions**: https://github.com/bjeans/homelab-mcp/discussions

## FAQ

**Q: Can I use both v2.x and v3.0 simultaneously?**
A: Yes, by using different Docker image tags in your Claude Desktop config. However, this is not recommended long-term.

**Q: Will there be a v2.3 release?**
A: No. Version 3.0 is the successor to v2.2.1. The architectural improvements warrant a major version bump.

**Q: What happened to removed tools like `docker_find_containers_by_label`?**
A: Removed tools were either:
- Merged into other tools (better UX)
- Functionality available through other means
- Planned for re-implementation in future releases if demand warrants

**Q: Why not provide a compatibility layer?**
A: A compatibility layer would:
- Add complexity to maintain
- Delay the transition to better naming
- Hide the improvements we made

Clean breaks are better for long-term project health.

**Q: Can I contribute a tool back?**
A: Absolutely! See CONTRIBUTING.md for guidelines. The new FastMCP pattern makes adding tools much easier.

## Summary

| Category | Impact |
|----------|--------|
| Tool Names | ❌ Breaking changes (20+ renamed) |
| API Signatures | ✅ Compatible (same parameters) |
| Configuration | ✅ Compatible (same `.env` and Ansible inventory) |
| Docker Deployment | ✅ Compatible (same configuration format) |
| Code Quality | ✅ Improved (38% reduction, cleaner patterns) |
| Future Development | ✅ Easier (FastMCP decorators vs manual classes) |

**Recommendation:** Upgrade to v3.0 for long-term maintainability and cleaner development experience. Budget 15-30 minutes to update tool references in your workflows.

---

**Version:** 3.0.0
**Date:** January 13, 2026
**Previous Version:** 2.2.1
