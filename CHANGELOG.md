# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
- **Release Process Documentation:** Complete release workflow in CONTRIBUTING.md
  - Step-by-step release creation guide
  - Testing procedures for Docker builds
  - Rollback process for failed releases
  - Docker Hub access management
- **MCP Tool Annotations:** Added comprehensive metadata annotations to all tools across 6 MCP servers
  - `title`: Human-readable tool titles for better UX
  - `readOnlyHint`: Indicates tools only read data (all tools marked as read-only)
  - `destructiveHint`: Indicates tools can modify/delete data (all tools marked as non-destructive)
  - `idempotentHint`: Indicates repeated calls have same effect (varies by tool based on caching behavior)
  - `openWorldHint`: Indicates tools return dynamic/real-time data (all tools interact with external systems)
- Enhanced MCP Inspector visualization with tool metadata
- Improved AI understanding of tool safety and behavior
- Full MCP specification compliance for tool metadata
- **CLAUDE_CUSTOM.md:** New gitignored file for homelab-specific customizations
- **CLAUDE_CUSTOM.example.md:** Detailed template for local Claude customizations
- **Local Customizations Section:** Added to CLAUDE.md explaining the customization system

### Changed
- **docker-compose.yml:** Now uses Docker Hub images by default (with option to build from source)
- **README.md:** Added Docker Hub badges and quick start section
- **README.md:** Reorganized Docker deployment section with Docker Hub as primary option
- Updated all 27 tools across Docker, Ping, Ollama, Pi-hole, Unifi, and UPS servers with annotations
- Both unified mode (with prefixes) and standalone mode (without prefixes) tools now include annotations
- **CLAUDE.md:** Now public-ready with generalized examples (removed Dell-Server, HL16 references)
- **.gitignore:** Updated to exclude CLAUDE_CUSTOM.md instead of CLAUDE.md
- **README.md:** Updated setup instructions for CLAUDE_CUSTOM.md
- **SECURITY.md:** Added guidance for Claude customization files

### Fixed
- **MCP Tool Annotations Protocol Compliance:** Wrapped all annotation hints in `types.ToolAnnotations()` object per MCP specification
  - Affects 33 tools across all 7 MCP servers (Ansible, Docker, Ollama, Pi-hole, Ping, Unifi, UPS)
  - Annotation hints (readOnlyHint, destructiveHint, idempotentHint, openWorldHint) now properly encapsulated
  - Fixed in both class-based implementations (unified mode) and module-level handlers (standalone mode)
  - Ensures correct MCP protocol serialization and client interpretation

### Infrastructure
- GitHub Actions workflow: `.github/workflows/docker-publish.yml`
- Automated CI/CD pipeline for Docker image publishing
- Integration with existing security checks
- Build summaries and failure notifications

### Improved
- Separation of public documentation from homelab-specific details
- Claude can now access project documentation on web and GitHub
- Better security by keeping infrastructure details in separate gitignored file

### Benefits
- **Easier deployment:** Pull pre-built images instead of building locally
- **Faster setup:** No need for local build environment
- **Multi-platform support:** Works on x86_64 and ARM (Raspberry Pi)
- **Version control:** Semantic versioning allows pinning to specific versions
- **Continuous delivery:** Every release automatically available on Docker Hub
- Better client UI/UX with visual safety indicators
- Enhanced tool discovery capabilities
- Improved AI reasoning about tool usage patterns
- Consistent metadata across all homelab infrastructure tools

### Planned
- Additional MCP servers (suggestions welcome!)
- Advanced analytics and reporting features
- Grafana dashboard integration
- Home Assistant integration
- Kubernetes deployment option
- Enhanced monitoring and alerting

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
- Enhanced monitoring and alerting

---

## Guidelines for Updates

When updating this changelog:
- Add new entries under `[Unreleased]` section
- When releasing, move `[Unreleased]` items to a new version section
- Use categories: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`
- Link to issues/PRs where applicable
