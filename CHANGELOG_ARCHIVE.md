# Changelog Archive

Historical changelog entries for versions prior to 2.0.0.

For recent changes, see [CHANGELOG.md](CHANGELOG.md).

---

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
