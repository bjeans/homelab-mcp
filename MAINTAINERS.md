# Maintainer Guide

This document is for project maintainers and covers release processes, Docker builds, and advanced maintenance topics.

## Release Process

### Automated Docker Builds

**Docker images are automatically built and published to Docker Hub via GitHub Actions.**

**Trigger Conditions:**

1. **PR merged to `main` branch** → Builds and tags as `latest` and `edge`
2. **Release tags (`v*.*.*`)** → Builds with semantic versioning tags
3. **Manual workflow dispatch** → For testing or emergency builds

**Tagging Strategy:**

For a release tag `v2.1.0`, the following Docker tags are created:
- `2.1.0` (exact version)
- `2.1` (minor version)
- `2` (major version)
- `latest` (if from main branch)

**Multi-Platform Support:**
- `linux/amd64` - x86_64 servers and workstations
- `linux/arm64` - Raspberry Pi, ARM-based systems

### Creating a Release

**For maintainers:**

1. **Update version references:**
   ```bash
   # Update CHANGELOG.md with version number and changes
   # Update any version strings in documentation
   ```

2. **Commit and push to main:**
   ```bash
   git add CHANGELOG.md README.md
   git commit -m "chore: prepare release v2.1.0"
   git push origin main
   ```

3. **Create and push the release tag:**
   ```bash
   git tag -a v2.1.0 -m "Release v2.1.0"
   git push origin v2.1.0
   ```

4. **GitHub Actions automatically:**
   - Runs security checks and tests
   - Builds multi-platform Docker images
   - Pushes to Docker Hub with semantic version tags
   - Updates `latest` tag

5. **Create GitHub Release:**
   - Go to https://github.com/bjeans/homelab-mcp/releases/new
   - Select the tag you just created
   - Title: `v2.1.0`
   - Copy relevant entries from CHANGELOG.md
   - Publish release

6. **Verify the build:**
   - Check GitHub Actions: https://github.com/bjeans/homelab-mcp/actions
   - Verify Docker Hub: https://hub.docker.com/r/bjeans/homelab-mcp/tags
   - Test pulling the new image:
     ```bash
     docker pull bjeans/homelab-mcp:2.1.0
     docker pull bjeans/homelab-mcp:latest
     ```

### Testing Docker Builds Locally

**Before creating a release, test the Docker build:**

```bash
# Build for multiple platforms locally (requires Docker Buildx)
docker buildx create --use
docker buildx build --platform linux/amd64,linux/arm64 -t homelab-mcp:test .

# Test the image
docker run --rm homelab-mcp:test python -c "import sys; print(sys.version)"
```

### Manual Workflow Dispatch

**For testing or emergency builds without a release:**

1. Go to: https://github.com/bjeans/homelab-mcp/actions/workflows/docker-publish.yml
2. Click "Run workflow"
3. Optionally specify a custom tag
4. Click "Run workflow" button

This is useful for:
- Testing the build process
- Creating debug/test images
- Emergency hotfix deployments

### Rollback Process

**If a release has issues:**

1. **Identify the last known-good version:**
   ```bash
   # Users can always pull specific versions
   docker pull bjeans/homelab-mcp:2.0.0
   ```

2. **Create a hotfix:**
   - Fix the issue in a new branch
   - Create PR and merge to main
   - Create a new patch release (e.g., `v2.1.1`)

3. **Update `latest` tag if needed:**
   - The new release will automatically update `latest`
   - Or manually retag in Docker Hub if immediate rollback needed

## Docker Hub Access

**Repository:** https://hub.docker.com/r/bjeans/homelab-mcp

**Required Secrets (configured in GitHub repository settings):**
- `DOCKERHUB_USERNAME` - Docker Hub username
- `DOCKERHUB_TOKEN` - Docker Hub access token (not password!)

**Security Notes:**
- Use Docker Hub access tokens, never passwords
- Tokens should have write permissions only for `bjeans/homelab-mcp`
- Rotate tokens periodically
- Never commit tokens to repository

## Version Management

### Semantic Versioning

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version (e.g., 2.x.x → 3.0.0): Incompatible API changes
- **MINOR** version (e.g., 2.1.x → 2.2.0): New features, backward compatible
- **PATCH** version (e.g., 2.1.0 → 2.1.1): Bug fixes, backward compatible

### When to Bump Versions

**MAJOR (x.0.0):**
- Breaking changes to MCP server interfaces
- Removal of deprecated features
- Major architectural changes
- Changes to configuration format that require migration

**MINOR (0.x.0):**
- New MCP servers added
- New tools added to existing servers
- New features that don't break existing functionality
- Non-breaking enhancements

**PATCH (0.0.x):**
- Bug fixes
- Security updates
- Documentation improvements
- Performance improvements without API changes

## CHANGELOG Management

### Format

Follow [Keep a Changelog](https://keepachangelog.com/) format:

```markdown
## [2.1.0] - 2025-11-19

### Added
- New feature description

### Changed
- Modified behavior description

### Fixed
- Bug fix description

### Security
- Security improvement description

### Deprecated
- Feature marked for removal

### Removed
- Removed feature description
```

### Archive Old Versions

When CHANGELOG.md gets too long (> 300 lines), archive old versions:

1. Create `CHANGELOG_ARCHIVE.md`
2. Move versions older than 1 year or 2 major versions
3. Keep link to archive in main CHANGELOG.md

## Maintenance Tasks

### Weekly

- [ ] Review open issues
- [ ] Review open pull requests
- [ ] Check GitHub Actions status
- [ ] Review security advisories

### Monthly

- [ ] Update dependencies: `pip list --outdated`
- [ ] Review and update documentation
- [ ] Check Docker image sizes and optimization opportunities
- [ ] Review and close stale issues

### Quarterly

- [ ] Major dependency updates
- [ ] Security audit: `python helpers/run_checks.py --security`
- [ ] Review and update roadmap
- [ ] Community engagement (discussions, feature requests)

### Annually

- [ ] Review and update security policy
- [ ] Audit all dependencies for license compliance
- [ ] Review and update contribution guidelines
- [ ] Archive old CHANGELOG entries

## Security Response

### Handling Security Reports

1. **Acknowledge receipt** within 24 hours
2. **Assess severity** (Critical, High, Medium, Low)
3. **Develop fix** in private branch
4. **Test thoroughly**
5. **Coordinate disclosure** with reporter
6. **Release patch** as soon as ready
7. **Publish security advisory** on GitHub
8. **Update CHANGELOG.md** with security fix

### Emergency Hotfix Process

For critical security issues:

1. Create hotfix branch from main: `git checkout -b hotfix/security-issue`
2. Develop and test fix
3. Create PR with `[SECURITY]` prefix
4. Fast-track review (< 24 hours)
5. Merge to main
6. Create patch release immediately
7. Publish security advisory
8. Notify users via GitHub Discussions

## Community Management

### Issue Triage

**Label issues appropriately:**
- `bug` - Something isn't working
- `enhancement` - New feature or request
- `documentation` - Documentation improvements
- `good first issue` - Good for newcomers
- `help wanted` - Extra attention needed
- `security` - Security-related issues
- `question` - Further information requested

**Response times:**
- Security issues: < 24 hours
- Bugs: < 3 days
- Feature requests: < 1 week
- Questions: < 3 days

### Pull Request Review

**Review checklist:**
- [ ] Code follows project style
- [ ] No sensitive data in commits
- [ ] Tests pass (when implemented)
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Security implications reviewed
- [ ] Backward compatibility considered

**Merge criteria:**
- At least 1 maintainer approval
- All checks passing
- No unresolved conversations
- Branch up to date with main

## Infrastructure

### GitHub Actions Workflows

**Active workflows:**
- `security-check.yml` - Pre-publish security validation
- `docker-publish.yml` - Docker image builds and publishing
- `lint.yml` - Code quality checks (if implemented)
- `dependency-audit.yml` - Dependency vulnerability scanning (if implemented)

**Workflow maintenance:**
- Update action versions quarterly
- Review and optimize build times
- Monitor GitHub Actions usage/costs
- Update secrets and tokens as needed

### Docker Hub

**Image management:**
- Monitor image pull statistics
- Review image sizes regularly
- Clean up old development tags
- Update image descriptions as needed

## Contact

**Maintainer:** Barnaby Jeans
**Repository:** https://github.com/bjeans/homelab-mcp
**Issues:** https://github.com/bjeans/homelab-mcp/issues

---

Last updated: 2026-01-11
