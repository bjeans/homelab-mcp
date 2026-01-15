# Docker Deployment Guide

This guide covers deploying the Homelab MCP servers using Docker containers.

**Version 3.0.0:** The Docker image defaults to unified mode (all 7 servers in one container) with FastMCP decorator pattern for simplified tool definitions. The image is marketplace-ready and fully configurable via environment variables with no external dependencies. See [Configuration Methods](#configuration-methods) below.

**Docker Hub:** Pre-built images available at https://hub.docker.com/r/bjeans/homelab-mcp/tags

## Quick Start

### Prerequisites
- Docker Engine 20.10+
- Docker Compose 2.0+ (optional but recommended)
- Network access to your homelab services
- Ansible inventory file OR environment variables configured

### Pull Pre-Built Image (Recommended)
```bash
# Pull the latest stable release from Docker Hub
docker pull bjeans/homelab-mcp:latest

# Or pull a specific commit build
docker pull bjeans/homelab-mcp:main-17bae01
```

**Available tags:**
- `latest` - Latest stable release from main branch (recommended)
- `edge` - Latest development build
- `main-<git-sha>` - Specific commit builds (e.g., `main-17bae01`)

### Build from Source (For Customization)
```bash
# Clone the repository
git clone https://github.com/bjeans/homelab-mcp.git
cd homelab-mcp

# Build the Docker image locally
docker build -t homelab-mcp:latest .
```

### Run with Docker Compose (Recommended)
```bash
# Copy the example environment file
cp .env.docker.example .env

# Edit .env with your configuration
nano .env

# Start the services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the services
docker-compose down
```

### Run Unified Mode (Default)

**All 7 servers in one container - no ENABLED_SERVERS needed:**

```bash
# Using Ansible Inventory (Recommended)
docker run -d \
  --name homelab-mcp \
  --network host \
  -v $(pwd)/ansible_hosts.yml:/config/ansible_hosts.yml:ro \
  --stdin \
  --tty \
  bjeans/homelab-mcp:latest

# Or using Environment Variables
docker run -d \
  --name homelab-mcp \
  --network host \
  -e DOCKER_SERVER1_ENDPOINT=192.168.1.100:2375 \
  -e OLLAMA_SERVER1_ENDPOINT=192.168.1.100:11434 \
  -e PIHOLE_SERVER1_ENDPOINT=192.168.1.100:8053 \
  --stdin \
  --tty \
  bjeans/homelab-mcp:latest
```

### Run Legacy Mode (Individual Servers)

**For backward compatibility, run specific servers with ENABLED_SERVERS:**

```bash
# Using Ansible Inventory
docker run -d \
  --name homelab-mcp-docker \
  --network host \
  -e ENABLED_SERVERS=docker \
  -e ANSIBLE_INVENTORY_PATH=/config/ansible_hosts.yml \
  -v $(pwd)/ansible_hosts.yml:/config/ansible_hosts.yml:ro \
  --stdin \
  --tty \
  bjeans/homelab-mcp:latest

# Using Environment Variables
docker run -d \
  --name homelab-mcp-docker \
  --network host \
  -e ENABLED_SERVERS=docker \
  -e DOCKER_SERVER1_ENDPOINT=192.168.1.100:2375 \
  -e DOCKER_SERVER2_ENDPOINT=192.168.1.101:2375 \
  --stdin \
  --tty \
  bjeans/homelab-mcp:latest
```

## Configuration

### Configuration Methods

The container supports two configuration methods that work with both unified and legacy modes:

#### Method 1: Ansible Inventory (Recommended)

Mount your Ansible inventory file as a volume:
```yaml
volumes:
  - ./ansible_hosts.yml:/config/ansible_hosts.yml:ro
environment:
  - ANSIBLE_INVENTORY_PATH=/config/ansible_hosts.yml
```

**Advantages:**
- Centralized configuration
- Supports complex host groupings
- Better for multi-host environments
- Single source of truth
- Works with unified and legacy modes

#### Method 2: Environment Variables

Pass configuration via environment variables:
```yaml
environment:
  - DOCKER_SERVER1_ENDPOINT=192.168.1.100:2375
  - DOCKER_SERVER2_ENDPOINT=192.168.1.101:2375
  - OLLAMA_SERVER1_ENDPOINT=192.168.1.100:11434
```

**Advantages:**
- Marketplace-ready (no external files)
- Simple for basic setups
- No additional files needed
- Easy to test and debug
- Works with unified and legacy modes

### Deployment Modes

**Unified Mode (Default):**
```bash
# No ENABLED_SERVERS needed - all 7 servers run in one container
docker run -d --name homelab-mcp --network host homelab-mcp:latest
```

Available tools: `ansible_*`, `docker_*`, `ping_*`, `ollama_*`, `pihole_*`, `unifi_*`, `ups_*`

**Legacy Mode (Individual Servers):**
```bash
# Set ENABLED_SERVERS for specific server
-e ENABLED_SERVERS=docker,ping,ollama,pihole,unifi,ups,ansible
```

Valid servers: `docker`, `ping`, `ollama`, `pihole`, `unifi`, `ups`, `ansible`

**Note:** `registry` (MCP Registry Inspector) is NOT included in Docker image - run directly only: `python mcp_registry_inspector.py`

**Important:** Only set ENABLED_SERVERS if you want legacy mode. Default (no variable) runs unified mode.

## Network Configuration

### Host Network Mode

The container uses `network_mode: host` to access homelab services:
```yaml
network_mode: host
```

**Why?** Your Docker/Podman APIs and ping targets are on your local network. Host mode provides direct access without port mapping complexity.

**Security Note:** Review firewall rules. See [SECURITY.md](SECURITY.md) for details.

### Alternative: Bridge Mode

For isolated networking:
```yaml
networks:
  - homelab
```

Requires additional configuration for service discovery.

## Security

### Running as Non-Root

The container runs as user `mcpuser` (UID 1000) for security:
```dockerfile
USER mcpuser
```

### Sensitive Data

**Never include sensitive data in the image:**
- ✅ Mount Ansible inventory as read-only volume
- ✅ Use environment variables for API keys
- ✅ Use Docker secrets in production
- ❌ Don't hardcode credentials in Dockerfile

### File Permissions

If using Ansible inventory:
```bash
# Restrict permissions (Linux/Mac)
chmod 600 ansible_hosts.yml
```

### Firewall Rules

Ensure Docker/Podman APIs are not exposed to internet:
```bash
# Example iptables rule (adjust for your setup)
iptables -A INPUT -p tcp --dport 2375 -s 192.168.1.0/24 -j ACCEPT
iptables -A INPUT -p tcp --dport 2375 -j DROP
```

## Integration with Claude Desktop

### Configuration Overview

The Docker containers can be configured two ways:

1. **Environment Variables (Recommended for Marketplace)** - No external files needed
2. **Ansible Inventory Volume Mount** - For advanced setups with many hosts

### Option 1: Environment Variables (Minimal Dependencies)

This approach requires no external files - everything is passed as environment variables. **Best for Docker MCP marketplace distribution.**

**Step 1: Start the container**

```bash
# Docker Compose approach
docker-compose up -d

# Or manually:
docker run -d --name homelab-mcp-docker --network host \
  -e ENABLED_SERVERS=docker \
  -e DOCKER_SERVER1_ENDPOINT=192.168.1.100:2375 \
  -e DOCKER_SERVER2_ENDPOINT=192.168.1.101:2375 \
  homelab-mcp:latest
```

**Step 2: Configure Claude Desktop**

Edit Claude Desktop config file:

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Linux:** `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "homelab-docker": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "homelab-mcp-docker",
        "python",
        "docker_mcp_podman.py"
      ]
    },
    "homelab-ping": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "homelab-mcp-ping",
        "python",
        "ping_mcp_server.py"
      ]
    }
  }
}
```

### Option 2: Ansible Inventory Volume Mount (Advanced)

For complex setups with many hosts, mount an Ansible inventory file:

```bash
docker run -d --name homelab-mcp-docker --network host \
  -e ENABLED_SERVERS=docker \
  -e ANSIBLE_INVENTORY_PATH=/config/ansible_hosts.yml \
  -v $(pwd)/ansible_hosts.yml:/config/ansible_hosts.yml:ro \
  homelab-mcp:latest
```

See [Configuration section](#configuration) above for details.

### Important Notes

- **Use `docker exec -i`** (not `-it`) for proper MCP stdio communication
- Do NOT use `-t` (tty) as it interferes with MCP protocol
- Container must be running before Claude tries to connect
- Restart Claude Desktop completely after configuration changes

## Troubleshooting

### Container Won't Start
```bash
# Check logs
docker logs homelab-mcp-docker

# Common issues:
# 1. ENABLED_SERVERS not set
# 2. Invalid server name
# 3. Missing configuration
```

### Can't Connect to Docker API
```bash
# Test connectivity from container
docker exec homelab-mcp-docker curl http://192.168.1.100:2375/containers/json

# Check firewall rules
# Verify API is enabled on target hosts
```

### Ping Not Working
```bash
# Ensure NET_RAW capability is granted
docker run --cap-add=NET_RAW ...

# Or in docker-compose.yml:
cap_add:
  - NET_RAW
```

### MCP Communication Issues

**Symptoms:** Claude Desktop can't connect to server

**Solutions:**
1. Ensure container is running: `docker ps`
2. Check stdin/tty are enabled: `--stdin --tty`
3. Verify container logs: `docker logs <container>`
4. Test with `docker exec -i`: `docker exec -i <container> python <server>.py`

### Permission Denied
```bash
# If you see permission errors:
# 1. Check volume mount permissions
ls -la ansible_hosts.yml

# 2. Ensure file is readable
chmod 644 ansible_hosts.yml

# 3. Check container user
docker exec homelab-mcp-docker whoami
```

## Building Multi-Architecture Images

For ARM devices (Raspberry Pi, etc.):
```bash
# Setup buildx
docker buildx create --use

# Build for multiple architectures
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t bjeans/homelab-mcp:latest \
  --push \
  .
```

## Testing

### Quick Verification Test - Unified Mode (Recommended)

Test the Docker image quickly with unified mode (default):

**Test Unified Server:**

```bash
# PowerShell (Unified - all servers)
docker run --rm --network host `
    -v "$PWD/ansible_hosts.yml:/config/ansible_hosts.yml:ro" `
    homelab-mcp:latest

# Bash (Unified - all servers)
docker run --rm --network host \
    -v $(pwd)/ansible_hosts.yml:/config/ansible_hosts.yml:ro \
    homelab-mcp:latest
```

**Expected Output:**

- Server starts with "Starting Homelab MCP..." 
- Unified mode message: "Mode: UNIFIED (all servers in one process)"
- Available tools displayed: `ansible_*`, `docker_*`, `ping_*`, `ollama_*`, `pihole_*`, `unifi_*`, `ups_*`
- Ansible inventory loaded from `/config/ansible_hosts.yml`
- Hosts/endpoints are discovered
- No error messages

### Legacy Mode Testing (Individual Servers)

For backward compatibility, test individual servers with ENABLED_SERVERS:

**Test Docker Server (Legacy):**

```bash
# PowerShell
docker run --rm --network host `
    -e ENABLED_SERVERS=docker `
    -e ANSIBLE_INVENTORY_PATH=/config/ansible_hosts.yml `
    -v "$PWD/ansible_hosts.yml:/config/ansible_hosts.yml:ro" `
    homelab-mcp:latest

# Bash
docker run --rm --network host \
    -e ENABLED_SERVERS=docker \
    -e ANSIBLE_INVENTORY_PATH=/config/ansible_hosts.yml \
    -v $(pwd)/ansible_hosts.yml:/config/ansible_hosts.yml:ro \
    homelab-mcp:latest
```

**Test Ping Server (Legacy):**

```bash
# Bash
docker run --rm --network host \
    -e ENABLED_SERVERS=ping \
    -e ANSIBLE_INVENTORY_PATH=/config/ansible_hosts.yml \
    -v $(pwd)/ansible_hosts.yml:/config/ansible_hosts.yml:ro \
    homelab-mcp:latest
```

**Expected Output (Legacy Mode):**

- Server starts with "Starting Homelab MCP..."
- Legacy mode message: "Mode: LEGACY (individual server)"
- Single server tools displayed (no prefix: `get_docker_containers`, `ping_host`, etc.)
- No error messages

### Docker Compose Testing

Start services using docker-compose and view logs:

```bash
docker-compose up -d

# View unified server logs (default)
docker-compose logs -f homelab-mcp

# Or view legacy mode logs (if using individual servers)
docker-compose logs -f homelab-mcp-docker
docker-compose logs -f homelab-mcp-ping
```

### Claude Desktop Integration Testing

**Unified Mode (Recommended):**

1. Start container with Docker Compose:

```bash
docker-compose up -d
```

2. Update Claude Desktop config (`%APPDATA%\Claude\claude_desktop_config.json`):

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

3. Restart Claude Desktop completely

4. Test in Claude:
   - Ask: "What tools are available?"
   - Ask: "Can you list the Docker containers across all servers?"
   - Ask: "What Ollama models are available?"
   - Ask: "Get Pi-hole statistics"
   - Ask: "Ping example.com"

**Legacy Mode (Individual Servers - For Testing):**

1. Start containers with Docker Compose:

```bash
docker-compose up -d
```

2. Update Claude Desktop config (`%APPDATA%\Claude\claude_desktop_config.json`):

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

3. Restart Claude Desktop completely

4. Test in Claude:
   - Ask: "What tools are available from homelab-docker?"
   - Ask: "Can you list the Docker containers on my servers?"
   - Ask: "Ping 8.8.8.8"

## Health Checks

The container includes health checks:

```bash
# Check container health
docker inspect homelab-mcp-docker | grep -A 10 Health

# Health check looks for Python MCP process
HEALTHCHECK CMD pgrep -f "python.*mcp" || exit 1
```

## Updating
```bash
# Pull latest changes
git pull

# Rebuild image
docker-compose build

# Restart services
docker-compose up -d
```

## Development

### Local Testing
```bash
# Build with different tag
docker build -t homelab-mcp:dev .

# Run with volume mounts for live code changes
docker run -it --rm \
  -v $(pwd):/app \
  homelab-mcp:dev \
  python docker_mcp_podman.py
```

### Debugging
```bash
# Run interactively with shell
docker run -it --rm \
  --entrypoint /bin/bash \
  homelab-mcp:latest

# Inside container, test servers manually:
python docker_mcp_podman.py
```

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

### Caching

Docker build uses layer caching. Requirements install is cached separately:
```dockerfile
# Copy requirements first (cached unless changed)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy code (changes more frequently)
COPY *.py .
```

## Next Steps

- Publish to Docker Hub marketplace
- Submit to MCP Registry
- Add Grafana dashboard integration
- Add Home Assistant integration
- Expand Kubernetes deployment support

## Support

- Issues: https://github.com/bjeans/homelab-mcp/issues
- Discussions: https://github.com/bjeans/homelab-mcp/discussions
- Security: See [SECURITY.md](SECURITY.md)
