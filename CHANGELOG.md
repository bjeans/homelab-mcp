# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-10-11

### Added
- Initial public release
- MCP Registry Inspector for Claude Desktop introspection
- Docker/Podman Container Manager with support for multiple hosts
- Ollama AI Model Manager with LiteLLM proxy support
- Pi-hole DNS Manager for monitoring DNS statistics
- Unifi Network Monitor with caching for performance
- Ansible Inventory Inspector for querying infrastructure
- Comprehensive security documentation (SECURITY.md)
- Automated pre-push security validation hook
- Configuration templates (.env.example, ansible_hosts.example.yml)
- Project instructions template for Claude Desktop
- Cross-platform support (Windows, macOS, Linux)

### Security
- Added pre_publish_check.py for automated security scanning
- Implemented git pre-push hook for security validation
- Sanitized all example configuration files
- Added comprehensive security guidelines in SECURITY.md
- Environment-based configuration to prevent credential exposure

## [2.0.0] - 2025-10-30

### Added
- **Containerized Deployment:** Full Docker support with Dockerfile, docker-compose.yml, and .dockerignore
- **Unified MCP Server:** Single `homelab_unified_mcp.py` runs all servers in one process with namespaced tools (e.g., `docker_get_containers`, `ping_ping_host`)
- **Docker Entrypoint Script:** Automatic mode detection (unified vs. legacy) with intelligent server startup
- **Enhanced Docker Configuration:** Support for both Ansible inventory and environment variable configuration
- **Health Checks:** Docker HEALTHCHECK configured for production deployments
- **Security Hardening:** Non-root user (mcpuser) in Docker containers with proper permissions
- **System Dependencies:** Added `iputils-ping` to Docker image for cross-platform ping support
- **Ping MCP Server:** New `ping_mcp_server.py` for network connectivity testing with cross-platform support
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

### Fixed
- Docker MCP initialization in unified mode
- Configuration loading in unified server
- Inconsistent logging across MCP servers
- Empty inventory handling in ping server

### Infrastructure
- Tested with 7 MCP servers
- Supports monitoring 24+ hosts
- Compatible with Docker Engine 20.10+ and Docker Compose 2.0+
- Verified on Windows, macOS, and Linux environments

### Planned
- Grafana dashboard integration
- Home Assistant integration
- Kubernetes deployment option
- Enhanced monitoring and alerting

## [Unreleased]

### Planned
- Additional MCP servers (suggestions welcome!)
- Advanced analytics and reporting features

---

## Guidelines for Updates

When updating this changelog:
- Add new entries under `[Unreleased]` section
- When releasing, move `[Unreleased]` items to a new version section
- Use categories: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`
- Link to issues/PRs where applicable
