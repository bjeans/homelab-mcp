# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [3.0.0] - 2026-01-13

⚠️ **BREAKING CHANGES** - See [MIGRATION_V3.md](MIGRATION_V3.md) for upgrade guide.

### Breaking Changes

- **Tool Name Changes:** 20+ tool names renamed for consistency
  - All list operations now use `list_*` prefix (e.g., `get_all_hosts` → `list_all_hosts`)
  - All detail operations now use `get_*` prefix (e.g., `check_container` → `get_container_details`)
  - See [MIGRATION_V3.md](MIGRATION_V3.md) for complete mapping
- **Removed Tools:**
  - `docker_get_all_containers` - Merged into `docker_list_containers`
  - `docker_find_containers_by_label` - Use `docker_list_containers` with filtering
  - `docker_get_container_labels` - Included in `docker_get_container_details`
  - `pihole_get_status` - Merged into `pihole_get_summary`
  - `ollama_get_litellm_status` - Use `ollama_list_hosts`
  - `ups_get_power_events` - Planned for future release

### Changed

- **Complete Architecture Rewrite:**
  - Unified server now uses FastMCP's native composition pattern
  - Eliminated 500+ lines of manual wrapper functions
  - Reduced unified server to ~105 lines (79% reduction)
  - No more parameter duplication or signature mismatches
  - Direct tool registration via FastMCP's `add_tool()` method

- **Improved Code Quality:**
  - 38% overall code reduction (1,754 lines eliminated)
  - Single source of truth for each tool
  - Cleaner, more maintainable architecture
  - Better type safety through FastMCP

- **Import Order Fix:**
  - Critical requirement: Import Ansible BEFORE FastMCP
  - Prevents FileFinder hook conflicts
  - Applied to all relevant server files
  - Documented in CLAUDE.md

### Added

- **Comprehensive Documentation:**
  - **[MIGRATION_V3.md](MIGRATION_V3.md)** - Complete v2.x to v3.0 upgrade guide
  - Updated **CLAUDE.md** with FastMCP decorator patterns
  - Removed outdated dual-mode class-based patterns
  - Added FastMCP composition examples
  - Import order requirements documented

### Fixed

- **Parameter Order Issues:** Resolved mismatched parameter ordering in:
  - `docker_get_container_details` - Now correctly passes `(host, container_id)`
  - `docker_get_container_logs` - Now correctly passes `(host, container_id, lines)`
  - `ollama_get_model_info` - Now correctly passes `(host, model_name)`

- **Async/Await Issues:** Fixed synchronous functions incorrectly marked as async:
  - `ansible_query_hosts` - Removed incorrect `await`

- **Signature Mismatches:** Fixed parameter count/name mismatches:
  - Pi-hole tools: Corrected `host` → `display_name` parameter names
  - UPS tools: Removed invalid `host` parameters
  - Ollama tools: Removed invalid `host` parameter from `get_running_models`

### Technical Improvements

- **FastMCP Native Composition:** Eliminates manual wrapper pattern
  - Uses `mcp._tool_manager._tools` to access decorated tools
  - Direct `add_tool()` registration instead of manual wrapping
  - No more `.fn()` accessor hacks
  - Tools remain callable and properly typed

- **Consistent Naming Convention:**
  - `list_*` - Returns lists/collections
  - `get_*` - Returns specific item details
  - `reload_*` - Reloads configuration

- **Better Developer Experience:**
  - Standard SDK: ~100 lines per tool
  - FastMCP: ~10-20 lines per tool
  - Type hints auto-generate schemas
  - Docstrings become descriptions

### Migration Impact

| Category | Impact |
|----------|--------|
| Tool Names | ❌ Breaking (20+ renamed) |
| API Signatures | ✅ Compatible |
| Configuration | ✅ Compatible |
| Docker Deployment | ✅ Compatible |
| Code Quality | ✅ Significantly improved |

**Upgrade Time:** 15-30 minutes to update tool references in workflows

### Credits

- Architecture redesign and implementation by Claude Code (Anthropic)
- Code review feedback incorporated from automated PR review agents
- Testing and validation by @bjeans

## [2.3.0] - 2026-01-11

### Added
- **FastMCP Framework Migration:** Complete migration of all 7 MCP servers to the FastMCP framework
  - Modern, simplified server architecture reducing code complexity
  - Support for multiple transport mechanisms (stdio, HTTP, SSE)
  - Improved error handling and logging capabilities
  - Enhanced type safety and code organization
- **Multiple Transport Support:**
  - **stdio transport (default)** - Traditional MCP protocol via stdin/stdout for Claude Desktop
  - **HTTP transport** - REST API for remote deployments and web integrations
  - **SSE transport** - Server-Sent Events for real-time bidirectional communication
  - All transports configurable via command-line arguments (`--transport`, `--host`, `--port`)
- **Comprehensive Documentation:**
  - New FastMCP framework section in README.md explaining transport options
  - Migration guide for v2.2.0 users (no breaking changes)
  - Examples for running servers with different transport mechanisms
  - Updated version number to v2.3.0 throughout documentation

### Changed
- **All 7 MCP Servers:** Migrated from standard MCP SDK to FastMCP framework
  - `homelab_unified_mcp.py` - Unified server with all 7 servers
  - `ansible_mcp_server.py` - Ansible inventory queries
  - `docker_mcp_podman.py` - Docker/Podman container monitoring
  - `ollama_mcp.py` - Ollama AI model management
  - `pihole_mcp.py` - Pi-hole DNS monitoring
  - `ping_mcp_server.py` - Network connectivity testing
  - `unifi_mcp_optimized.py` - Unifi network device monitoring
  - `ups_mcp_server.py` - UPS/NUT monitoring
- **Server Architecture:** Simplified from dual-mode pattern to unified FastMCP pattern
  - Eliminates complex class/module handler splitting
  - Cleaner tool registration and dispatch
  - More maintainable codebase for future development
- **Documentation:** Updated README.md with FastMCP framework section and transport options

### Improved
- **Code Quality:** 38% reduction in codebase (1,754 lines eliminated)
  - Cleaner server implementations
  - Reduced code duplication
  - Better separation of concerns
  - Improved maintainability for contributors
- **Developer Experience:**
  - Simpler pattern for creating new servers
  - Easier debugging with FastMCP tools
  - Better error messages and logging
- **Deployment Flexibility:** Multiple transport options enable new use cases
  - Remote server deployments with HTTP transport
  - Real-time monitoring with SSE transport
  - Web-based integrations
  - Load balancing scenarios

### Backward Compatibility
- ✅ **No breaking changes** - All existing Claude Desktop configurations continue to work
- ✅ **Same functionality** - All 7 servers and all tools remain identical
- ✅ **Same tool names** - Unified mode prefixes and standalone tool names unchanged
- ✅ **Same configuration** - `.env` and Ansible inventory files work without modification
- Upgrade path: Simply update and restart Claude Desktop - no action required

### Technical Details
- FastMCP framework provides native support for multiple transports
- Reduced server initialization overhead with FastMCP's optimized startup
- Improved async/await handling for better concurrency
- Enhanced tool metadata support for better Claude Desktop integration
- Cleaner error handling with FastMCP's built-in error management

### Benefits
- **For Users:** No disruption - everything works as before, with new deployment options
- **For Developers:** Cleaner codebase and easier to add new servers
- **For Operations:** New transport options enable more flexible deployments
- **For Maintenance:** Simpler code reduces bugs and makes fixes faster

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
  - Specific handling for 401 (Invalid Password) vs 403 (Insufficient Permissions)
  - Detailed session authentication error messages with Pi-hole Settings guidance
  - Improved timeout and connection error messages with troubleshooting commands
  - Context logging for all API failures
- **Unifi MCP Server (`unifi_mcp_optimized.py`):** **CRITICAL FIX** for "Exporter failed with code 1" issue (#32)
  - Parse subprocess stderr to identify specific error patterns (auth, connection, timeout, certificate)
  - Map exit codes to specific error types with remediation
  - Pre-flight validation for missing API keys with helpful guidance
  - Distinguish between invalid API key (401) and connection failures
  - Include exporter output in error messages for debugging
  - Guidance on where to find/generate Unifi API keys
- **Ollama MCP Server (`ollama_mcp.py`):** Improved error classification for Ollama and LiteLLM
  - HTTP status code differentiation (401, 404, 429, 500)
  - Enhanced LiteLLM proxy error handling with rate limit detection
  - Specific guidance for authentication and service availability
  - Context logging for all API failures
- **Docker/Podman MCP Server (`docker_mcp_podman.py`):** Better container runtime error messages
  - Distinguish between authentication (401), not found (404), and server errors (500)
  - Socket connection failures with clear guidance
  - Context logging for debugging container API issues
- **UPS MCP Server (`ups_mcp_server.py`):** Enhanced NUT protocol error handling
  - Network error classification (timeout, connection refused, OSError)
  - Context logging for all NUT server communication failures
  - Improved debugging information for UPS monitoring issues

### Improved
- **User Experience:** Error messages now guide users to the exact fix instead of generic "failed" messages
- **Security:** All sensitive data (API keys, passwords, tokens, session IDs) automatically sanitized in logs
- **Debugging:** Structured logging with full context (host, port, endpoint, status code) for all errors
- **Documentation:** Comprehensive troubleshooting guide reduces support requests
- **Developer Experience:** Consistent error handling pattern across all servers makes adding new servers easier

### Fixed
- **Issue #32:** "Exporter failed with code 1" error now provides specific details:
  - Invalid API key detection with Unifi Settings guidance
  - Connection failure detection with network troubleshooting commands
  - Timeout detection with service health check guidance
  - Certificate error detection with SSL troubleshooting
  - No more ambiguous exit codes - users know exactly what went wrong
- **Error Message Inconsistency:** All servers now use standardized error format
- **Missing Context:** Errors now include all relevant debugging information (timestamp, host, status)
- **Credential Exposure:** Sensitive data no longer appears in error messages or logs

### Technical Details
- HTTP error codes properly classified: 400, 401, 403, 404, 429, 500, 502, 503, 504
- Error pattern matching with regex for common issues (invalid API key, connection refused, timeout, certificate errors)
- Automatic sensitive data sanitization using configurable regex patterns
- Context-aware logging that preserves debugging information while protecting credentials
- Backward compatible - existing code continues to work, but with better error messages

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
  - Tests for hostname normalization edge cases (FQDN, uppercase, underscores, mixed cases)
  - Tests for graceful degradation when Ansible is unavailable
  - Tests for enum method signatures and return types
  - Runnable with pytest or standalone: `python3 tests/ansible_enum_tests.py`

### Changed
- **Code Refactoring:** Reduced code duplication in `ansible_config_manager.py`
  - Refactored enum methods to use shared `get_hosts_by_capability()` and `_get_hosts_from_group()`
  - Reduced approximately 100 lines of duplicated logic
  - Improved maintainability and consistency
- **MCP Server Updates:** All relevant servers now accept `ansible_config` parameter
  - `ping_mcp_server.py`: Dynamic enums for Ansible groups in `ping_ping_group` tool
  - `ollama_mcp.py`: Dynamic enums for Ollama hosts in `ollama_get_models` tool
  - `ups_mcp_server.py`: Dynamic enums for NUT hosts in `ups_get_ups_details` tool
  - `docker_mcp_podman.py`: Consistency update (already had enum support)
  - `pihole_mcp.py`: Consistency update (prepared for future host-specific tools)
- **Unified Server:** `homelab_unified_mcp.py` now creates and passes `AnsibleConfigManager` to all sub-servers

### Improved
- **User Experience:** Dropdown menus reduce manual entry and discovery tool calls
- **Code Quality:** Centralized hostname normalization prevents inconsistencies
- **Maintainability:** Shared helpers make adding new servers easier
- **Documentation:** README.md includes new section explaining dynamic enum feature

### Benefits
- **Faster Workflow:** Select from dropdown instead of typing or calling discovery tools first
- **Fewer Errors:** Can't typo hostnames anymore - only valid options shown
- **Better Discoverability:** Users immediately see what infrastructure they have configured
- **Graceful Degradation:** Works without Ansible inventory (just no enum suggestions)
- **Performance:** Enums generated once at startup, not on every tool call

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
