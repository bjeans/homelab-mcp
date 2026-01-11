# Docker Deployment Guide

Complete guide for deploying Homelab MCP servers using Docker containers.

**Version 2.2.0+** supports unified mode (all 7 servers in one container) with automatic mode detection, dynamic enum generation, and marketplace-ready configuration via environment variables.

**Docker Hub:** https://hub.docker.com/r/bjeans/homelab-mcp/tags

---

## Quick Start

### Prerequisites
- Docker Engine 20.10+
- Docker Compose 2.0+ (optional but recommended)
- Network access to homelab services
- Ansible inventory file OR environment variables configured

### Pull Pre-Built Image (Recommended)

```bash
# Pull latest stable release
docker pull bjeans/homelab-mcp:latest

# Or pull specific commit build
docker pull bjeans/homelab-mcp:main-17bae01
```

**Available tags:**
- `latest` - Latest stable release from main branch (recommended)
- `edge` - Latest development build
- `main-<git-sha>` - Specific commit builds (e.g., `main-17bae01`)
- `2.2.1`, `2.2`, `2` - Semantic version tags (after release)

**Multi-platform support:**
- `linux/amd64` - x86_64 servers and workstations
- `linux/arm64` - Raspberry Pi, ARM-based systems

### Run with Docker Compose (Recommended)

```bash
# Start the unified server (all 7 MCP servers)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Run Unified Mode (Default)

**All 7 servers in one container - no ENABLED_SERVERS variable needed:**

```bash
# Using Ansible Inventory (Recommended)
docker run -d \
  --name homelab-mcp \
  --network host \
  -v $(pwd)/ansible_hosts.yml:/config/ansible_hosts.yml:ro \
  bjeans/homelab-mcp:latest

# Using Environment Variables (Marketplace Ready)
docker run -d \
  --name homelab-mcp \
  --network host \
  -e DOCKER_SERVER1_ENDPOINT=192.168.1.100:2375 \
  -e OLLAMA_SERVER1_ENDPOINT=192.168.1.100:11434 \
  -e PIHOLE_SERVER1_HOST=192.168.1.10 \
  -e PIHOLE_API_KEY_SERVER1=your-api-key \
  bjeans/homelab-mcp:latest
```

**Unified mode includes:** Ansible, Docker/Podman, Ollama, Pi-hole, Unifi, UPS, Ping (7 servers)

### Run Legacy Mode (Individual Servers)

For backward compatibility, run specific servers by setting `ENABLED_SERVERS`:

```bash
docker run -d \
  --name homelab-mcp-docker \
  --network host \
  -e ENABLED_SERVERS=docker \
  -v $(pwd)/ansible_hosts.yml:/config/ansible_hosts.yml:ro \
  bjeans/homelab-mcp:latest
```

**Valid server names:** `docker`, `ping`, `ollama`, `pihole`, `unifi`, `ups`, `ansible`

**Note:** Tool names differ between modes (unified has prefixes: `docker_*`, legacy has no prefix). Only set ENABLED_SERVERS if you want legacy mode.

---

## Configuration

### Method 1: Ansible Inventory (Recommended)

Mount your Ansible inventory file as a volume:

```yaml
# docker-compose.yml
volumes:
  - ./ansible_hosts.yml:/config/ansible_hosts.yml:ro
environment:
  - ANSIBLE_INVENTORY_PATH=/config/ansible_hosts.yml
```

**Advantages:**
- Centralized configuration
- Supports complex host groupings
- Single source of truth
- Works with unified and legacy modes

### Method 2: Environment Variables

Pass configuration via environment variables (marketplace-ready):

```yaml
# docker-compose.yml
environment:
  - DOCKER_SERVER1_ENDPOINT=192.168.1.100:2375
  - DOCKER_SERVER2_ENDPOINT=192.168.1.101:2375
  - OLLAMA_SERVER1_ENDPOINT=192.168.1.100:11434
  - PIHOLE_SERVER1_HOST=192.168.1.10
  - PIHOLE_API_KEY_SERVER1=your-api-key
```

**Advantages:**
- No external files needed
- Simple for basic setups
- Easy to test and debug
- Marketplace compatible

---

## Integration with Claude Desktop

### Unified Mode (Recommended)

**Config file location:**
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "homelab-unified": {
      "command": "docker",
      "args": ["exec", "-i", "homelab-mcp", "python", "homelab_unified_mcp.py"]
    }
  }
}
```

**Important:**
- Use `docker exec -i` (not `-it`) for proper MCP stdio communication
- Container must be running before Claude tries to connect
- Restart Claude Desktop completely after configuration changes

### Legacy Mode (Individual Servers)

```json
{
  "mcpServers": {
    "homelab-docker": {
      "command": "docker",
      "args": ["exec", "-i", "homelab-mcp-docker", "python", "docker_mcp_podman.py"]
    },
    "homelab-ping": {
      "command": "docker",
      "args": ["exec", "-i", "homelab-mcp-ping", "python", "ping_mcp_server.py"]
    }
  }
}
```

---

## Network Configuration

### Host Network Mode (Default)

The container uses `network_mode: host` for direct access to homelab services:

```yaml
network_mode: host
```

**Why?** Your Docker/Podman APIs and other services are on your local network. Host mode provides direct access without port mapping complexity.

**Security Note:** Review firewall rules. See [SECURITY.md](SECURITY.md) for details.

### Alternative: Bridge Mode

For isolated networking:

```yaml
networks:
  - homelab
```

Requires additional configuration for service discovery.

---

## Security

### Running as Non-Root

The container runs as user `mcpuser` (UID 1000):
```dockerfile
USER mcpuser
```

### File Permissions

If using Ansible inventory:
```bash
chmod 600 ansible_hosts.yml  # Restrict permissions (Linux/Mac)
```

### Sensitive Data

**Never include in image:**
- ✅ Mount Ansible inventory as read-only volume
- ✅ Use environment variables for API keys
- ✅ Use Docker secrets in production
- ❌ Don't hardcode credentials in Dockerfile

### Firewall Rules

Ensure Docker/Podman APIs are not exposed to internet. See [SECURITY.md](SECURITY.md) for comprehensive security guidelines.

---

## Testing

### Quick Verification (Unified Mode)

```bash
# PowerShell
docker run --rm --network host `
    -v "$PWD/ansible_hosts.yml:/config/ansible_hosts.yml:ro" `
    bjeans/homelab-mcp:latest

# Bash
docker run --rm --network host \
    -v $(pwd)/ansible_hosts.yml:/config/ansible_hosts.yml:ro \
    bjeans/homelab-mcp:latest
```

**Expected Output:**
- Server starts with "Starting Homelab MCP..."
- Mode message: "Mode: UNIFIED (all servers in one process)"
- Available tools displayed: `ansible_*`, `docker_*`, `ping_*`, `ollama_*`, `pihole_*`, `unifi_*`, `ups_*`
- Ansible inventory loaded successfully
- No error messages

### Docker Compose Testing

```bash
docker-compose up -d
docker-compose logs -f  # View logs
```

### Claude Desktop Integration Testing

1. Start container: `docker-compose up -d`
2. Update Claude Desktop config (see Integration section above)
3. Restart Claude Desktop completely
4. Test in Claude:
   - "What tools are available?"
   - "List Docker containers across all servers"
   - "What Ollama models are available?"
   - "Get Pi-hole statistics"
   - "Ping example.com"

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs homelab-mcp

# Common issues:
# 1. Missing configuration (no .env or ansible_hosts.yml)
# 2. Invalid ENABLED_SERVERS value
# 3. Port conflicts
```

### Can't Connect to Services

```bash
# Test connectivity from container
docker exec homelab-mcp curl http://192.168.1.100:2375/containers/json

# Check firewall rules
# Verify API is enabled on target hosts
```

### MCP Communication Issues

**Symptoms:** Claude Desktop can't connect to server

**Solutions:**
1. Ensure container is running: `docker ps`
2. Verify stdin/tty are enabled in docker-compose.yml: `stdin_open: true`, `tty: true`
3. Check container logs: `docker logs homelab-mcp`
4. Test with `docker exec -i`: `docker exec -i homelab-mcp python homelab_unified_mcp.py`

### Permission Denied

```bash
# Check volume mount permissions
ls -la ansible_hosts.yml

# Ensure file is readable
chmod 644 ansible_hosts.yml

# Check container user
docker exec homelab-mcp whoami
```

---

## Building from Source (Optional)

### Build Locally

```bash
# Clone repository
git clone https://github.com/bjeans/homelab-mcp
cd homelab-mcp

# Build image
docker build -t homelab-mcp:latest .
```

### Multi-Architecture Build

For ARM devices (Raspberry Pi, etc.):

```bash
# Setup buildx
docker buildx create --use

# Build for multiple architectures
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t homelab-mcp:latest \
  .
```

---

## Health Checks

The container includes built-in health checks:

```bash
# Check container health
docker inspect homelab-mcp | grep -A 10 Health

# Health check verifies Python MCP process is running
HEALTHCHECK CMD pgrep -f "python.*mcp" || exit 1
```

---

## Updating

### Update Pre-Built Image

```bash
# Pull latest image
docker pull bjeans/homelab-mcp:latest

# Restart services
docker-compose down
docker-compose up -d
```

### Rebuild from Source

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose build
docker-compose up -d
```

---

## Performance

### Resource Limits

Add resource constraints if needed:

```yaml
deploy:
  resources:
    limits:
      cpus: '0.5'
      memory: 256M
    reservations:
      cpus: '0.25'
      memory: 128M
```

### Layer Caching

Docker build uses layer caching for faster rebuilds:

```dockerfile
# Requirements cached separately
COPY requirements.txt .
RUN pip install -r requirements.txt

# Code (changes more frequently)
COPY *.py .
```

---

## Docker Features (v2.0.0+)

- ✅ Unified MCP server as default entrypoint (all 7 servers)
- ✅ Automatic mode detection (no ENABLED_SERVERS needed)
- ✅ Built-in health checks
- ✅ Non-root user security (mcpuser UID 1000)
- ✅ Proper signal handling and clean shutdown
- ✅ Optimized layer caching
- ✅ System dependencies included (iputils-ping for cross-platform support)
- ✅ Multi-platform support (amd64, arm64)

---

## Support

- **Issues**: https://github.com/bjeans/homelab-mcp/issues
- **Discussions**: https://github.com/bjeans/homelab-mcp/discussions
- **Security**: See [SECURITY.md](SECURITY.md)
