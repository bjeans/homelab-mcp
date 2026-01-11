# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

**For historical changes (v1.x), see [CHANGELOG_ARCHIVE.md](CHANGELOG_ARCHIVE.md)**

---

## [Unreleased]

### Added
- **Ansible MCP Server Integration:** Complete integration of `ansible_mcp_server.py` into unified server and Docker deployment
  - Refactored `AnsibleInventoryMCP` class to support dual-mode operation (standalone + unified)
  - Added `list_tools()` and `handle_tool()` methods with `ansible_` prefix for unified mode
  - Integrated into `homelab_unified_mcp.py` with proper routing and tool listing
  - Added to Dockerfile for Docker deployments
  - All 8 Ansible inventory tools now available: `ansible_get_all_hosts`, `ansible_get_all_groups`, `ansible_get_host_details`, `ansible_get_group_details`, `ansible_get_hosts_by_group`, `ansible_search_hosts`, `ansible_get_inventory_summary`, `ansible_reload_inventory`
  - Closes issue #39

### Changed
- **Unified Server:** Updated from 6 to 7 MCP servers with Ansible integration (Ansible, Docker, Ping, Ollama, Pi-hole, Unifi, UPS)
- **Documentation:** Updated README.md to reflect Ansible integration completion

---

## [2.2.1] - 2026-01-07

### Security
- **Docker Image Rebuild:** Rebuilt Docker image to address 9 dependency vulnerabilities
  - Updated aiohttp from 3.13.2 to 3.13.3, fixing:
    - 1 HIGH: CVE-2025-69223 (Improper Handling of Highly Compressed Data)
    - 3 MEDIUM: CVE-2025-69227 (Infinite Loop), CVE-2025-69228, CVE-2025-69229 (Resource Exhaustion)
    - 4 LOW: CVE-2025-69226, CVE-2025-69230 (Info Exposure, Excessive Logging)
  - Reduced total vulnerabilities from 11 to 2 (remaining are unfixed upstream Alpine issues)
  - Pinned `aiohttp>=3.13.3` in requirements.txt to enforce security fix

### Added
- **Dependabot Configuration:** Automated dependency update PRs via `.github/dependabot.yml`
  - Python dependencies checked daily (catches security updates quickly)
  - Docker base image checked weekly
  - GitHub Actions checked weekly
  - Auto-labels PRs with `dependencies`, `security`, `docker`, or `ci` tags

### Note
- 2 vulnerabilities remain in Alpine base image packages (zlib, busybox) with no upstream fix available yet

---

## [2.2.0] - 2025-11-20

### Added
- **Centralized Error Handling System:** New `mcp_error_handler.py` module providing consistent error handling across all MCP servers
  - `MCPErrorClassifier` class with HTTP status code classification and error pattern matching
  - User-friendly error message formatting with actionable remediation steps
  - Structured logging with automatic sensitive data sanitization
  - Context-aware error messages including hostname, port, and service details
- **Enhanced Error Messages:** All API errors now include:
  - Clear error type identification (Authentication Failed, Connection Failed, Timeout, etc.)
  - Specific HTTP status codes (401, 403, 404, 500, 503, etc.)
  - Hostname/endpoint information
  - Actionable remediation guidance (→ symbol for visibility)
  - Technical details with timestamps for debugging
  - No exposure of sensitive credentials in error messages
- **Comprehensive Troubleshooting Documentation:** New section in README.md with:
  - Error message format explanation
  - Common error types with examples (Authentication, Connection, Timeout, etc.)
  - Step-by-step remediation guides for each error type
  - Before/after examples showing improvement from v2.1.0 to v2.2.0
  - Debugging tips and direct API testing commands
  - Configuration validation commands

### Changed
- **Pi-hole MCP Server (`pihole_mcp.py`):** Enhanced error handling in authentication and API requests
- **Unifi MCP Server (`unifi_mcp_optimized.py`):** **CRITICAL FIX** for "Exporter failed with code 1" issue (#32)
- **Ollama MCP Server (`ollama_mcp.py`):** Improved error classification for Ollama and LiteLLM
- **Docker/Podman MCP Server (`docker_mcp_podman.py`):** Better container runtime error messages
- **UPS MCP Server (`ups_mcp_server.py`):** Enhanced NUT protocol error handling

### Improved
- **User Experience:** Error messages now guide users to the exact fix instead of generic "failed" messages
- **Security:** All sensitive data (API keys, passwords, tokens, session IDs) automatically sanitized in logs
- **Debugging:** Structured logging with full context (host, port, endpoint, status code) for all errors
- **Documentation:** Comprehensive troubleshooting guide reduces support requests
- **Developer Experience:** Consistent error handling pattern across all servers makes adding new servers easier

### Fixed
- **Issue #32:** "Exporter failed with code 1" error now provides specific details
- **Error Message Inconsistency:** All servers now use standardized error format
- **Missing Context:** Errors now include all relevant debugging information
- **Credential Exposure:** Sensitive data no longer appears in error messages or logs

---

## [2.1.0] - 2025-11-19

### Added
- **Dynamic Enum Generation for Tool Parameters:** Automatic population of tool parameter enums based on Ansible inventory
  - Claude Desktop now shows actual infrastructure options in dropdown menus
  - No more guessing or typing hostnames/group names manually
  - Reduces errors by showing only valid options
  - Works with Ping, Docker, Ollama, and UPS tools
- **Hostname Normalization Helper:** Shared `_normalize_hostname()` method for consistent hostname formatting
- **Group-based Host Lookup:** New `_get_hosts_from_group()` helper for cleaner code
- **Test Coverage:** Added `tests/ansible_enum_tests.py` with comprehensive tests for enum generation methods

### Changed
- **Code Refactoring:** Reduced code duplication in `ansible_config_manager.py`
  - Refactored enum methods to use shared helpers
  - Reduced approximately 100 lines of duplicated logic
- **MCP Server Updates:** All relevant servers now accept `ansible_config` parameter
  - `ping_mcp_server.py`: Dynamic enums for Ansible groups
  - `ollama_mcp.py`: Dynamic enums for Ollama hosts
  - `ups_mcp_server.py`: Dynamic enums for NUT hosts
  - `docker_mcp_podman.py`: Consistency update
  - `pihole_mcp.py`: Consistency update
- **Unified Server:** `homelab_unified_mcp.py` now creates and passes `AnsibleConfigManager` to all sub-servers

### Improved
- **User Experience:** Dropdown menus reduce manual entry and discovery tool calls
- **Code Quality:** Centralized hostname normalization prevents inconsistencies
- **Maintainability:** Shared helpers make adding new servers easier

---

## [2.0.0] - 2025-10-30

### Added
- **Automated Docker Image Builds:** GitHub Actions workflow for automated Docker image publishing
  - Multi-platform support: `linux/amd64` and `linux/arm64`
  - Semantic versioning tags (e.g., v2.1.0 → 2.1.0, 2.1, 2, latest)
  - Automated builds when PRs are merged to main branch (tagged as `latest` and `edge`)
  - Automated builds on release tags with semantic versioning
  - Manual workflow dispatch for testing and emergency builds
  - Docker layer caching for faster builds
  - Build status badges in README
- **Docker Hub Integration:** Pre-built images available at https://hub.docker.com/r/bjeans/homelab-mcp
  - No need to build locally - just `docker pull bjeans/homelab-mcp:latest`
  - Updated docker-compose.yml to use Docker Hub images by default
  - Comprehensive tagging strategy for version management
- **Release Process Documentation:** Complete release workflow in CONTRIBUTING.md (now MAINTAINERS.md)
- **MCP Tool Annotations:** Added comprehensive metadata annotations to all tools across 6 MCP servers
  - `title`: Human-readable tool titles for better UX
  - `readOnlyHint`: Indicates tools only read data (all tools marked as read-only)
  - `destructiveHint`: Indicates tools can modify/delete data (all tools marked as non-destructive)
  - `idempotentHint`: Indicates repeated calls have same effect
  - `openWorldHint`: Indicates tools return dynamic/real-time data
- **CLAUDE_CUSTOM.md:** New gitignored file for homelab-specific customizations
- **Containerized Deployment:** Full Docker support with Dockerfile, docker-compose.yml, and .dockerignore
- **Unified MCP Server:** Single `homelab_unified_mcp.py` runs all servers in one process with namespaced tools
- **Docker Entrypoint Script:** Automatic mode detection (unified vs. legacy) with intelligent server startup
- **Enhanced Docker Configuration:** Support for both Ansible inventory and environment variable configuration
- **Health Checks:** Docker HEALTHCHECK configured for production deployments
- **Security Hardening:** Non-root user (mcpuser) in Docker containers
- **System Dependencies:** Added `iputils-ping` to Docker image for cross-platform ping support
- **Ping MCP Server:** New `ping_mcp_server.py` for network connectivity testing
- **Docker Compose Support:** Complete docker-compose.yml with example configuration
- **UPS Monitoring:** Integrated UPS/NUT monitoring (`ups_mcp_server.py`) into unified server
- **Dual-Mode Architecture:** All servers support both standalone and unified mode operation

### Changed
- **Architecture:** Refactored to class-based dual-mode pattern for unified server integration
- **Docker Image:** Now packages homelab_unified_mcp.py as primary entry point
- **Unified Server Tools:** Prefixed with service name (`docker_*`, `ping_*`, `ollama_*`, `pihole_*`, `unifi_*`, `ups_*`)
- **Configuration Loading:** Centralized config management via `mcp_config_loader.py` and `ansible_config_manager.py`
- **Logging:** All diagnostic output routed to stderr to preserve MCP protocol stdout
- **Documentation:** Reorganized with Docker deployment guide, migration guide, and updated examples
- **docker-compose.yml:** Now uses Docker Hub images by default (with option to build from source)
- **README.md:** Added Docker Hub badges and quick start section
- Updated all 27 tools across Docker, Ping, Ollama, Pi-hole, Unifi, and UPS servers with annotations
- Both unified mode (with prefixes) and standalone mode (without prefixes) tools now include annotations
- **CLAUDE.md:** Now public-ready with generalized examples
- **.gitignore:** Updated to exclude CLAUDE_CUSTOM.md instead of CLAUDE.md

### Fixed
- **MCP Tool Annotations Protocol Compliance:** Wrapped all annotation hints in `types.ToolAnnotations()` object
  - Affects 33 tools across all 7 MCP servers (Ansible, Docker, Ollama, Pi-hole, Ping, Unifi, UPS)
  - Ensures correct MCP protocol serialization and client interpretation
- Docker MCP initialization in unified mode
- Configuration loading in unified server
- Inconsistent logging across MCP servers
- Empty inventory handling in ping server

### Infrastructure
- GitHub Actions workflow: `.github/workflows/docker-publish.yml`
- Automated CI/CD pipeline for Docker image publishing
- Integration with existing security checks
- Tested with 7 MCP servers monitoring 24+ hosts
- Compatible with Docker Engine 20.10+ and Docker Compose 2.0+

---

## Guidelines for Updates

When updating this changelog:
- Add new entries under `[Unreleased]` section
- When releasing, move `[Unreleased]` items to a new version section
- Use categories: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`
- Link to issues/PRs where applicable
- Archive versions older than 1 year to CHANGELOG_ARCHIVE.md
