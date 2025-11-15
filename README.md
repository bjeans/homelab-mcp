# Homelab MCP Servers

[![GitHub release](https://img.shields.io/github/v/release/bjeans/homelab-mcp)](https://github.com/bjeans/homelab-mcp/releases)
[![Security Check](https://github.com/bjeans/homelab-mcp/actions/workflows/security-check.yml/badge.svg)](https://github.com/bjeans/homelab-mcp/actions/workflows/security-check.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/bjeans/homelab-mcp/blob/main/LICENSE)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)

Model Context Protocol (MCP) servers for managing homelab infrastructure through Claude Desktop.

A collection of Model Context Protocol (MCP) servers for managing and monitoring your homelab infrastructure through Claude Desktop.

## 🔒 Security Notice

**⚠️ IMPORTANT: Please read [SECURITY.md](SECURITY.md) before deploying this project.**

This project interacts with critical infrastructure (Docker APIs, DNS, network devices). Improper configuration can expose your homelab to security risks.

**Key Security Requirements:**

- **NEVER expose Docker/Podman APIs to the internet** - Use firewall rules to restrict access
- **Keep `.env` file secure** - Contains API keys and should never be committed
- **Use unique API keys** - Generate separate keys for each service
- **Review network security** - Ensure proper VLAN segmentation and firewall rules

See [SECURITY.md](SECURITY.md) for comprehensive security guidance.

## � Documentation Overview

This project includes several documentation files for different audiences:

- **[README.md](README.md)** (this file) - Installation, setup, and usage guide
- **[MIGRATION.md](MIGRATION.md)** - Migration guide for v2.0 unified server
- **[PROJECT_INSTRUCTIONS.md](PROJECT_INSTRUCTIONS.example.md)** - Copy into Claude project instructions for AI context
- **[CLAUDE.md](CLAUDE.md)** - Developer guide for AI assistants and contributors
- **[SECURITY.md](SECURITY.md)** - Security policies and best practices
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - How to contribute to this project
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and changes

**👥 For End Users:** Follow this README + copy PROJECT_INSTRUCTIONS.md to Claude
**🔄 Migrating from v1.x?** See [MIGRATION.md](MIGRATION.md) for unified server migration
**🤖 For AI Assistants:** Read [CLAUDE.md](CLAUDE.md) for complete development context
**🔧 For Contributors:** Start with CONTRIBUTING.md and [CLAUDE.md](CLAUDE.md)

## �📖 Important: Configure Claude Project Instructions

After setting up the MCP servers, **create your personalized project instructions**:

1. **Copy the example template:**

   ```bash
   # Windows
   copy PROJECT_INSTRUCTIONS.example.md PROJECT_INSTRUCTIONS.md

   # Linux/Mac
   cp PROJECT_INSTRUCTIONS.example.md PROJECT_INSTRUCTIONS.md
   ```

2. **Edit the file** with your actual infrastructure details:

   **PROJECT_INSTRUCTIONS.md** (for Claude Desktop project instructions):
   - Replace example IP addresses with your real network addresses
   - Add your actual server hostnames
   - Customize with your specific services and configurations
   - **Keep this file private** - it contains your network topology

   **CLAUDE_CUSTOM.md** (for AI development work - contributors only):
   - Update repository URLs with your actual GitHub repository
   - Add your Notion workspace URLs if using task management
   - Customize infrastructure references
   - **Keep this file private** - contains your specific URLs and setup

3. **Add to Claude Desktop:**
   - Open Claude Desktop
   - Go to your project settings
   - Copy the contents of your customized `PROJECT_INSTRUCTIONS.md`
   - Paste into the "Project instructions" field

**What's included:**

- Detailed MCP server capabilities and usage patterns
- Infrastructure overview and monitoring capabilities  
- Specific commands and tools available for each service
- Troubleshooting and development guidance

This README covers installation and basic setup. The project instructions provide Claude with comprehensive usage context.

## 🎯 Deployment Options

**Version 2.0.0+** offers two deployment modes:

### Unified Server (Recommended for New Deployments)

Run all MCP servers in a single process with namespaced tools. This is the recommended approach for new installations and Docker deployments:

```json
{
  "mcpServers": {
    "homelab-unified": {
      "command": "python",
      "args": ["C:\\Path\\To\\Homelab-MCP\\homelab_unified_mcp.py"]
    }
  }
}
```

**Advantages:**
- ✅ Single configuration entry
- ✅ One Python process for all servers
- ✅ Better Docker deployment with unified entrypoint
- ✅ Cleaner logs (no duplicate warnings)
- ✅ All tools namespaced (e.g., `docker_get_containers`, `ping_ping_host`)
- ✅ Built-in health checks (Docker)
- ✅ Production-ready containerization

### Individual Servers (Legacy, Fully Supported)

Run each MCP server as a separate process. This mode remains fully supported for backward compatibility:

```json
{
  "mcpServers": {
    "docker": {
      "command": "python",
      "args": ["C:\\Path\\To\\Homelab-MCP\\docker_mcp_podman.py"]
    },
    "ollama": {
      "command": "python",
      "args": ["C:\\Path\\To\\Homelab-MCP\\ollama_mcp.py"]
    }
  }
}
```

**Advantages:**
- ✅ Granular control over each server
- ✅ Can enable/disable servers individually
- ✅ Original tool names (e.g., `get_docker_containers`, `ping_host`)
- ✅ Backward compatible with v1.x

**Migration Guide:** See [MIGRATION.md](MIGRATION.md) for detailed migration instructions and tool name changes.

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/bjeans/homelab-mcp
cd homelab-mcp
```

### 2. Install security checks (recommended)

```bash
# Install pre-push git hook for automatic security validation
python helpers/install_git_hook.py
```

### 3. Set up configuration files

**Environment variables:**

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

Edit `.env` with your actual values:

```bash
# Windows
notepad .env

# Linux/Mac
nano .env
```

**Ansible inventory (if using):**

```bash
# Windows
copy ansible_hosts.example.yml ansible_hosts.yml

# Linux/Mac
cp ansible_hosts.example.yml ansible_hosts.yml
```

Edit with your infrastructure details.

**Project instructions:**

```bash
# Windows
copy PROJECT_INSTRUCTIONS.example.md PROJECT_INSTRUCTIONS.md

# Linux/Mac
cp PROJECT_INSTRUCTIONS.example.md PROJECT_INSTRUCTIONS.md
```

Customize with your network topology and servers.

**AI development guide customizations (optional):**

```bash
# Windows
copy CLAUDE_CUSTOM.example.md CLAUDE_CUSTOM.md

# Linux/Mac
cp CLAUDE_CUSTOM.example.md CLAUDE_CUSTOM.md
```

Customize with your actual server names and infrastructure details. This file is gitignored and allows Claude to understand your specific homelab setup. See `CLAUDE.md` for more information about local customizations.

### 4. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 5. Add to Claude Desktop config

**Config file location:**

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

**Option A: Unified Server (Recommended)**

Single entry for all homelab servers:

```json
{
  "mcpServers": {
    "homelab-unified": {
      "command": "python",
      "args": ["C:\\Path\\To\\Homelab-MCP\\homelab_unified_mcp.py"]
    },
    "mcp-registry-inspector": {
      "command": "python",
      "args": ["C:\\Path\\To\\Homelab-MCP\\mcp_registry_inspector.py"]
    },
    "ansible-inventory": {
      "command": "python",
      "args": ["C:\\Path\\To\\Homelab-MCP\\ansible_mcp_server.py"]
    }
  }
}
```

**Option B: Individual Servers (Legacy)**

Separate entry for each server:

```json
{
  "mcpServers": {
    "mcp-registry-inspector": {
      "command": "python",
      "args": ["C:\\Path\\To\\Homelab-MCP\\mcp_registry_inspector.py"]
    },
    "docker": {
      "command": "python",
      "args": ["C:\\Path\\To\\Homelab-MCP\\docker_mcp_podman.py"]
    },
    "ollama": {
      "command": "python",
      "args": ["C:\\Path\\To\\Homelab-MCP\\ollama_mcp.py"]
    },
    "pihole": {
      "command": "python",
      "args": ["C:\\Path\\To\\Homelab-MCP\\pihole_mcp.py"]
    },
    "unifi": {
      "command": "python",
      "args": ["C:\\Path\\To\\Homelab-MCP\\unifi_mcp_optimized.py"]
    },
    "ping": {
      "command": "python",
      "args": ["C:\\Path\\To\\Homelab-MCP\\ping_mcp_server.py"]
    },
    "ups-monitor": {
      "command": "python",
      "args": ["C:\\Path\\To\\Homelab-MCP\\ups_mcp_server.py"]
    },
    "ansible-inventory": {
      "command": "python",
      "args": ["C:\\Path\\To\\Homelab-MCP\\ansible_mcp_server.py"]
    }
  }
}
```

**Note:** Tool names differ between modes. See [MIGRATION.md](MIGRATION.md) for details.

### 6. Restart Claude Desktop

### 7. Add project instructions to Claude

- Copy the contents of your customized `PROJECT_INSTRUCTIONS.md`
- Paste into your Claude project's "Project instructions" field
- This gives Claude comprehensive context about your MCP capabilities


## 🐳 Docker Deployment (Alternative)

Run the MCP servers in Docker containers for easier distribution, isolation, and production deployment.

### Quick Start with Docker (Unified Mode - Recommended)

**All servers in one container using unified mode:**

```bash
# Clone and navigate to repository
git clone https://github.com/bjeans/homelab-mcp
cd homelab-mcp

# Build the image
docker build -t homelab-mcp:latest .

# Run with Docker Compose (recommended for production)
docker-compose up -d

# Or run unified server directly
docker run -d \
  --name homelab-mcp \
  --network host \
  -v $(pwd)/ansible_hosts.yml:/config/ansible_hosts.yml:ro \
  homelab-mcp:latest
```

### Docker Features

**2.0.0 Docker Improvements:**
- ✅ Unified MCP server as default entrypoint (all 7 servers in one container)
- ✅ Automatic unified mode detection (no ENABLED_SERVERS needed)
- ✅ Built-in health checks (HEALTHCHECK configured)
- ✅ Non-root user security (mcpuser UID 1000)
- ✅ Proper signal handling and clean shutdown
- ✅ Optimized layer caching for faster rebuilds
- ✅ System dependencies included (iputils-ping for cross-platform support)

### Configuration Methods

**Method 1: Ansible Inventory (Recommended)**

```bash
# Create your ansible_hosts.yml with infrastructure details
# Then mount as volume:

docker run -d \
  --name homelab-mcp \
  --network host \
  -v $(pwd)/ansible_hosts.yml:/config/ansible_hosts.yml:ro \
  homelab-mcp:latest
```

**Method 2: Environment Variables (Marketplace Ready)**

```bash
docker run -d \
  --name homelab-mcp \
  --network host \
  -e DOCKER_SERVER1_ENDPOINT=192.168.1.100:2375 \
  -e DOCKER_SERVER1_NAME=Local-Docker \
  -e OLLAMA_SERVER1_ENDPOINT=192.168.1.100:11434 \
  homelab-mcp:latest
```

### Legacy Mode: Individual Servers (Docker)

For backward compatibility, you can still run individual servers by setting `ENABLED_SERVERS`:

```bash
docker run -d \
  --name homelab-mcp-docker \
  --network host \
  -e ENABLED_SERVERS=docker \
  -v $(pwd)/ansible_hosts.yml:/config/ansible_hosts.yml:ro \
  homelab-mcp:latest
```

### Available Servers

**Unified Mode (Default):**
- ✅ All 7 servers in one process: Ansible, Docker, Ping, Ollama, Pi-hole, Unifi, UPS
- ✅ Namespaced tools (e.g., `docker_get_containers`, `ups_get_ups_status`)
- ✅ Single configuration entry
- ✅ Built-in health checks

**Legacy Mode (Set `ENABLED_SERVERS`):**
- ✅ `ansible` - Ansible inventory queries
- ✅ `docker` - Docker/Podman container management
- ✅ `ping` - Network ping utilities
- ✅ `ollama` - Ollama AI model management
- ✅ `pihole` - Pi-hole DNS statistics
- ✅ `unifi` - Unifi network device monitoring
- ✅ `ups` - UPS/NUT power monitoring

### Docker Configuration

**Two configuration methods supported:**

1. **Ansible Inventory (Recommended)** - Mount as volume
2. **Environment Variables** - Pass via Docker `-e` flags

See [DOCKER.md](DOCKER.md) for comprehensive Docker deployment guide including:
- Detailed setup instructions
- Network configuration options
- Security best practices
- Claude Desktop integration
- Troubleshooting common issues

### Integration with Claude Desktop

**Unified Mode (Recommended):**

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

**Legacy Mode (Individual Servers):**

```json
{
  "mcpServers": {
    "homelab-docker": {
      "command": "docker",
      "args": ["exec", "-i", "homelab-mcp-docker", "python", "docker_mcp_podman.py"]
    },
    "homelab-ping": {
      "command": "docker",
      "args": ["exec", "-i", "homelab-mcp", "python", "ping_mcp_server.py"]
    }
  }
}
```

**Important:** Use `docker exec -i` (not `-it`) for proper MCP stdio communication.

### Testing Docker Containers

**Quick verification test (using environment variables - marketplace ready):**

```bash
# Test Unified Server
docker run --rm --network host \
    -e DOCKER_SERVER1_ENDPOINT=localhost:2375 \
    -e OLLAMA_SERVER1_ENDPOINT=localhost:11434 \
    homelab-mcp:latest

# Test Individual Server (legacy)
docker run --rm --network host \
    -e ENABLED_SERVERS=ping \
    homelab-mcp:latest
```

**Docker Compose testing:**

```bash
docker-compose up -d
docker-compose logs -f
```

For comprehensive Docker deployment guide, see [DOCKER.md](DOCKER.md).


## 📦 Available MCP Servers

### MCP Registry Inspector

Provides introspection into your MCP development environment.

**⚠️ Note:** MCP Registry Inspector is NOT included in Docker image - run directly on your host machine only.

**Tools:**

- `get_claude_config` - View Claude Desktop MCP configuration
- `list_mcp_servers` - List all registered MCP servers
- `list_mcp_directory` - Browse MCP development directory
- `read_mcp_file` - Read MCP server source code
- `write_mcp_file` - Write/update MCP server files
- `search_mcp_files` - Search for files by name

**Configuration:**

```bash
MCP_DIRECTORY=/path/to/your/Homelab-MCP
CLAUDE_CONFIG_PATH=/path/to/claude_desktop_config.json  # Optional
```

### Docker/Podman Container Manager

Manage Docker and Podman containers across multiple hosts.

**🔒 Security Warning:** Docker/Podman APIs typically use unencrypted HTTP without authentication. See [SECURITY.md](SECURITY.md) for required firewall configuration.

**Tools:**

Individual server mode:
- `get_docker_containers` - Get containers on a specific host
- `get_all_containers` - Get all containers across all hosts
- `get_container_stats` - Get CPU and memory stats
- `check_container` - Check if a specific container is running
- `find_containers_by_label` - Find containers by label
- `get_container_labels` - Get all labels for a container

Unified server mode (namespaced):
- `docker_get_containers` - Get containers on a specific host
- `docker_get_all_containers` - Get all containers across all hosts
- `docker_get_container_stats` - Get CPU and memory stats
- `docker_check_container` - Check if a specific container is running
- `docker_find_containers_by_label` - Find containers by label
- `docker_get_container_labels` - Get all labels for a container

**Configuration Options:**

**Option 1: Using Ansible Inventory (Recommended)**

```bash
ANSIBLE_INVENTORY_PATH=/path/to/ansible_hosts.yml

# Ansible inventory group names (default: docker_hosts, podman_hosts)
# Change these if you use different group names in your ansible_hosts.yml
DOCKER_ANSIBLE_GROUP=docker_hosts
PODMAN_ANSIBLE_GROUP=podman_hosts
```

**Option 2: Using Environment Variables**

```bash
DOCKER_SERVER1_ENDPOINT=192.168.1.100:2375
DOCKER_SERVER2_ENDPOINT=192.168.1.101:2375
PODMAN_SERVER1_ENDPOINT=192.168.1.102:8080
```


### Ollama AI Model Manager

Monitor and manage Ollama AI model instances across your homelab, plus check your LiteLLM proxy for unified API access.

#### What's Included

**Ollama Monitoring:**

- Track multiple Ollama instances across different hosts
- View available models and their sizes
- Check instance health and availability

**LiteLLM Proxy Integration:**

- LiteLLM provides a unified OpenAI-compatible API across all your Ollama instances
- Enables load balancing and failover between multiple Ollama servers
- Allows you to use OpenAI client libraries with your local models
- The MCP server can verify your LiteLLM proxy is online and responding

**Why use LiteLLM?**

- **Load Balancing**: Automatically distributes requests across multiple Ollama instances
- **Failover**: If one Ollama server is down, requests route to healthy servers
- **OpenAI Compatibility**: Use any OpenAI SDK/library with your local models
- **Centralized Access**: Single endpoint (e.g., `http://192.0.2.10:4000`) for all models
- **Usage Tracking**: Monitor which models are being used most

**Tools:**

- `get_ollama_status` - Check status of all Ollama instances and model counts
- `get_ollama_models` - Get detailed model list for a specific host
- `get_litellm_status` - Verify LiteLLM proxy is online and responding

**Configuration Options:**

**Option 1: Using Ansible Inventory (Recommended)**

```bash
ANSIBLE_INVENTORY_PATH=/path/to/ansible_hosts.yml
OLLAMA_PORT=11434  # Default Ollama port

# Ansible inventory group name (default: ollama_servers)
# Change this if you use a different group name in your ansible_hosts.yml
OLLAMA_INVENTORY_GROUP=ollama_servers

# LiteLLM Configuration
LITELLM_HOST=192.168.1.100  # Host running LiteLLM proxy
LITELLM_PORT=4000           # LiteLLM proxy port (default: 4000)
```

**Option 2: Using Environment Variables**

```bash
# Ollama Instances
OLLAMA_SERVER1=192.168.1.100
OLLAMA_SERVER2=192.168.1.101
OLLAMA_WORKSTATION=192.168.1.150

# LiteLLM Proxy
LITELLM_HOST=192.168.1.100
LITELLM_PORT=4000
```


**Setting Up LiteLLM (Optional):**

If you want to use LiteLLM for unified access to your Ollama instances:

1. **Install LiteLLM** on one of your servers:

   ```bash
   pip install litellm[proxy]
   ```

2. **Create configuration** (`litellm_config.yaml`):

   ```yaml
   model_list:
     - model_name: llama3.2
       litellm_params:
         model: ollama/llama3.2
         api_base: http://server1:11434
     - model_name: llama3.2
       litellm_params:
         model: ollama/llama3.2
         api_base: http://server2:11434
   
   router_settings:
     routing_strategy: usage-based-routing
   ```

3. **Start LiteLLM proxy**:

   ```bash
   litellm --config litellm_config.yaml --port 4000
   ```

4. **Use the MCP tool** to verify it's running:

   - In Claude: "Check my LiteLLM proxy status"

**Example Usage:**

- "What Ollama instances do I have running?"
- "Show me all models on my Dell-Server"
- "Is my LiteLLM proxy online?"
- "How many models are available across all servers?"


### Pi-hole DNS Manager

Monitor Pi-hole DNS statistics and status.

**🔒 Security Note:** Store Pi-hole API keys securely in `.env` file. Generate unique keys per instance.

**Tools:**

- `get_pihole_stats` - Get DNS statistics from all Pi-hole instances
- `get_pihole_status` - Check which Pi-hole instances are online

**Configuration Options:**

**Option 1: Using Ansible Inventory (Recommended)**

```bash
ANSIBLE_INVENTORY_PATH=/path/to/ansible_hosts.yml

# Ansible inventory group name (default: PiHole)
# Change this if you use a different group name in your ansible_hosts.yml
PIHOLE_ANSIBLE_GROUP=PiHole

# API keys still required in .env:
PIHOLE_API_KEY_SERVER1=your-api-key-here
PIHOLE_API_KEY_SERVER2=your-api-key-here
```

**Option 2: Using Environment Variables**

```bash
PIHOLE_API_KEY_SERVER1=your-api-key
PIHOLE_API_KEY_SERVER2=your-api-key
PIHOLE_SERVER1_HOST=pihole1.local
PIHOLE_SERVER1_PORT=80
PIHOLE_SERVER2_HOST=pihole2.local
PIHOLE_SERVER2_PORT=8053
```

**Getting Pi-hole API Keys:**

- Web UI: Settings → API → Show API Token
- Or generate new: `pihole -a -p` on Pi-hole server

### Unifi Network Monitor

Monitor Unifi network infrastructure and clients with caching for performance.

**🔒 Security Note:** Use a dedicated API key with minimal required permissions.

**Tools:**

- `get_network_devices` - Get all network devices (switches, APs, gateways)
- `get_network_clients` - Get all active network clients
- `get_network_summary` - Get network overview
- `refresh_network_data` - Force refresh from controller (bypasses cache)

**Configuration:**

```bash
UNIFI_API_KEY=your-unifi-api-key
UNIFI_HOST=192.168.1.1
```

**Note:** Data is cached for 5 minutes to improve performance. Use `refresh_network_data` to force update.

### Ansible Inventory Inspector

Query Ansible inventory information (read-only).

**Tools:**

- `get_all_hosts` - Get all hosts in inventory
- `get_all_groups` - Get all groups
- `get_host_details` - Get detailed host information
- `get_group_details` - Get detailed group information
- `get_hosts_by_group` - Get hosts in specific group
- `search_hosts` - Search hosts by pattern or variable
- `get_inventory_summary` - High-level inventory overview
- `reload_inventory` - Reload inventory from disk

**Configuration:**

```bash
ANSIBLE_INVENTORY_PATH=/path/to/ansible_hosts.yml
```

### Ping Network Connectivity Monitor

Test network connectivity and host availability using ICMP ping across your infrastructure.

**Why use this?**

- Quick health checks during outages or after power events
- Verify which hosts are reachable before querying service-specific MCPs
- Simple troubleshooting tool to identify network issues
- Baseline connectivity testing for your infrastructure

**Tools:**

- `ping_host` - Ping a single host by name (resolved from Ansible inventory)
- `ping_group` - Ping all hosts in an Ansible group concurrently
- `ping_all` - Ping all infrastructure hosts concurrently
- `list_groups` - List available Ansible groups for ping operations

**Features:**

- ✅ **Cross-platform support** - Works on Windows, Linux, and macOS
- ✅ **Ansible integration** - Automatically resolves hostnames/IPs from inventory
- ✅ **Concurrent pings** - Test multiple hosts simultaneously for faster results
- ✅ **Detailed statistics** - RTT min/avg/max, packet loss percentage
- ✅ **Customizable** - Configure timeout and packet count
- ✅ **No dependencies** - Uses system `ping` command (no extra libraries needed)

**Configuration:**

```bash
ANSIBLE_INVENTORY_PATH=/path/to/ansible_hosts.yml
# No additional API keys required!
```

**Example Usage:**

- "Ping server1.example.local"
- "Check connectivity to all Pi-hole servers"
- "Ping all Ubuntu_Server hosts"
- "Test connectivity to entire infrastructure"
- "What groups can I ping?"

**When to use:**

- **After power outages** - Quickly identify which hosts came back online
- **Before service checks** - Verify host is reachable before checking specific services
- **Network troubleshooting** - Isolate connectivity issues from service issues
- **Health monitoring** - Regular checks to ensure infrastructure availability

### UPS Monitoring (Network UPS Tools)

Monitor UPS (Uninterruptible Power Supply) devices across your infrastructure using Network UPS Tools (NUT) protocol.

**Why use this?**

- Real-time visibility into power infrastructure status
- Proactive alerts before battery depletion during outages
- Monitor multiple UPS devices across different hosts
- Track battery health and runtime estimates
- Essential for critical infrastructure planning

**Tools:**

- `get_ups_status` - Check status of all UPS devices across all NUT servers
- `get_ups_details` - Get detailed information for a specific UPS device
- `get_battery_runtime` - Get battery runtime estimates for all UPS devices
- `get_power_events` - Check for recent power events (on battery, low battery)
- `list_ups_devices` - List all UPS devices configured in inventory
- `reload_inventory` - Reload Ansible inventory after changes

**Features:**

- ✅ **NUT protocol support** - Uses Network UPS Tools standard protocol (port 3493)
- ✅ **Ansible integration** - Automatically discovers UPS from inventory
- ✅ **Multiple UPS per host** - Support for servers with multiple UPS devices
- ✅ **Battery monitoring** - Track charge level, runtime remaining, load percentage
- ✅ **Power event detection** - Identify when UPS switches to battery or low battery
- ✅ **Cross-platform** - Works with any NUT-compatible UPS (TrippLite, APC, CyberPower, etc.)
- ✅ **Flexible auth** - Optional username/password authentication

**Configuration:**

**Option 1: Using Ansible Inventory (Recommended)**

```bash
ANSIBLE_INVENTORY_PATH=/path/to/ansible_hosts.yml

# Default NUT port (optional, defaults to 3493)
NUT_PORT=3493

# NUT authentication (optional - only if your NUT server requires it)
NUT_USERNAME=monuser
NUT_PASSWORD=secret
```

**Ansible inventory example:**

```yaml
nut_servers:
  hosts:
    dell-server.example.local:
      ansible_host: 192.168.1.100
      nut_port: 3493
      ups_devices:
        - name: tripplite
          description: "TrippLite SMART1500LCDXL"
```

**Option 2: Using Environment Variables**

```bash
NUT_PORT=3493
NUT_USERNAME=monuser
NUT_PASSWORD=secret
```

**Prerequisites:**

1. **Install NUT on servers with UPS devices:**
   ```bash
   # Debian/Ubuntu
   sudo apt install nut nut-client nut-server

   # RHEL/Rocky/CentOS
   sudo dnf install nut nut-client
   ```

2. **Configure NUT daemon (`/etc/nut/ups.conf`):**
   ```ini
   [tripplite]
       driver = usbhid-ups
       port = auto
       desc = "TrippLite SMART1500LCDXL"
   ```

3. **Enable network monitoring (`/etc/nut/upsd.conf`):**
   ```ini
   LISTEN 0.0.0.0 3493
   ```

4. **Configure access (`/etc/nut/upsd.users`):**
   ```ini
   [monuser]
       password = secret
       upsmon master
   ```

5. **Start NUT services:**
   ```bash
   sudo systemctl enable nut-server nut-client
   sudo systemctl start nut-server nut-client
   ```

**Example Usage:**

- "What's the status of all my UPS devices?"
- "Show me battery runtime for the Dell server UPS"
- "Check for any power events"
- "Get detailed info about the TrippLite UPS"
- "List all configured UPS devices"

**When to use:**

- **After power flickers** - Verify UPS devices handled the event properly
- **Before maintenance** - Check battery levels and estimated runtime
- **Regular monitoring** - Track UPS health and battery condition
- **Capacity planning** - Understand how long systems can run on battery

**Common UPS Status Codes:**

- `OL` - Online (normal operation, AC power present)
- `OB` - On Battery (power outage, running on battery)
- `LB` - Low Battery (critically low battery, shutdown imminent)
- `CHRG` - Charging (battery is charging)
- `RB` - Replace Battery (battery needs replacement)

## 🔒 Security

### Automated Security Checks

This project includes automated security validation to prevent accidental exposure of sensitive data:

**Install the pre-push git hook (recommended):**

```bash
# From project root
python helpers/install_git_hook.py
```

**What it does:**

- Automatically runs `helpers/pre_publish_check.py` before every git push
- Blocks pushes that contain potential secrets or sensitive data
- Protects against accidentally committing API keys, passwords, or personal information

**Manual security check:**

```bash
# Run security validation manually
python helpers/pre_publish_check.py
```

**Bypass security check (use with extreme caution):**

```bash
# Only when absolutely necessary
git push --no-verify
```

### Critical Security Practices

**Configuration Files:**

- ✅ **DO** use `.env.example` as a template
- ✅ **DO** keep `.env` file permissions restrictive (`chmod 600` on Linux/Mac)
- ❌ **NEVER** commit `.env` to version control
- ❌ **NEVER** commit `ansible_hosts.yml` with real infrastructure
- ❌ **NEVER** commit `PROJECT_INSTRUCTIONS.md` with real network topology

**API Security:**

- ✅ **DO** use unique API keys for each service
- ✅ **DO** rotate API keys regularly (every 90 days recommended)
- ✅ **DO** use strong, randomly-generated keys (32+ characters)
- ❌ **NEVER** expose Docker/Podman APIs to the internet
- ❌ **NEVER** reuse API keys between environments

**Network Security:**

- ✅ **DO** use firewall rules to restrict API access
- ✅ **DO** implement VLAN segmentation
- ✅ **DO** enable TLS/HTTPS where possible
- ❌ **NEVER** expose management interfaces publicly

**For detailed security guidance, see [SECURITY.md](SECURITY.md)**

## 📋 Requirements

### System Requirements

- **Python**: 3.10 or higher
- **Claude Desktop**: Latest version recommended
- **Network Access**: Connectivity to homelab services

### Python Dependencies

Install via `requirements.txt`:

```bash
pip install -r requirements.txt
```

Core dependencies:

- `mcp` - Model Context Protocol SDK
- `aiohttp` - Async HTTP client
- `pyyaml` - YAML parsing for Ansible inventory

### Service Requirements

- **Docker/Podman**: API enabled on monitored hosts
- **Pi-hole**: v6+ with API enabled
- **Unifi Controller**: API access enabled
- **Ollama**: Running instances with API accessible
- **NUT (Network UPS Tools)**: Installed and configured on hosts with UPS devices
- **Ansible**: Inventory file (optional but recommended)

## 💻 Compatibility

### Tested Platforms

**Developed and tested on:**

- **OS**: Windows 11
- **Claude Desktop**: Version 0.13.64
- **Python**: Version 3.13.8

### Cross-Platform Notes

**Windows**: Fully tested and supported ✅
**macOS**: Should work but untested ⚠️
**Linux**: Should work but untested ⚠️

**Known platform differences:**

- File paths in documentation are Windows-style
- Path separators may need adjustment for Unix systems
- `.env` file permissions should be set on Unix (`chmod 600 .env`)

**Contributions for other platforms welcome!**

## 🛠️ Development

**📖 First time contributing?** Read [CLAUDE.md](CLAUDE.md) for complete development guidance including architecture patterns, security requirements, and AI assistant workflows.

### Getting Started

1. **Install security git hook (required for contributors):**

   ```bash
   python helpers/install_git_hook.py
   ```

2. **Set up development environment:**

   ```bash
   pip install -r requirements.txt
   cp .env.example .env
   # Edit .env with your test values
   ```

### Testing MCP Servers Locally

**Before submitting a PR, test your MCP server changes locally using the MCP Inspector tool.**

**Quick start:**

```bash
# MCP Inspector is an optional Node.js tool for interactive testing
# Option 1: Use npx (no installation needed - recommended)
npx @modelcontextprotocol/inspector uv --directory . run <server>_mcp.py

# Option 2: Install globally first (one-time setup)
npm install -g @modelcontextprotocol/inspector
# Then run: mcp-inspector uv --directory . run <server>_mcp.py
```

This opens a web-based debugger at `http://localhost:5173` where you can:
- See all available tools for the MCP server
- Test each tool with sample arguments
- Verify responses are properly formatted
- Debug issues before submitting PRs

**For detailed testing instructions**, see the **Testing MCP Servers Locally** section in [CONTRIBUTING.md](CONTRIBUTING.md).

### Helper Scripts

The `helpers/` directory contains utility scripts for development and deployment:

- **`install_git_hook.py`** - Installs git pre-push hook for automatic security checks
- **`pre_publish_check.py`** - Security validation script (runs automatically via git hook)

**Usage:**

```bash
# Install security git hook
python helpers/install_git_hook.py

# Run security check manually  
python helpers/pre_publish_check.py
```

### Project Structure

```text
Homelab-MCP/
├── helpers/                 # Utility and setup scripts
│   ├── install_git_hook.py # Git pre-push hook installer
│   └── pre_publish_check.py # Security validation script
├── .env.example              # Template for environment variables
├── .gitignore               # Excludes sensitive files
├── SECURITY.md              # Security best practices
├── README.md                # This file
├── CLAUDE_CUSTOM.example.md # Example for custom Claude instructions
├── CLAUDE.md                # Public Claude AI assistant guide
├── CONTRIBUTING.md          # Contribution guidelines
├── CHANGELOG.md             # Version history
├── requirements.txt         # Python dependencies
├── ansible_hosts.example.yml    # Example Ansible inventory
├── PROJECT_INSTRUCTIONS.example.md  # Example Claude instructions
├── ansible_mcp_server.py    # Ansible inventory MCP
├── docker_mcp_podman.py     # Docker/Podman MCP
├── ollama_mcp.py            # Ollama AI MCP
├── pihole_mcp.py            # Pi-hole DNS MCP
├── unifi_mcp_optimized.py   # Unifi network MCP
├── unifi_exporter.py        # Unifi data export utility
└── mcp_registry_inspector.py  # MCP development tools
```

### Adding a New MCP Server

1. **Create the server file**

   ```python
   #!/usr/bin/env python3
   """
   My Service MCP Server
   Description of what it does
   """
   import asyncio
   from mcp.server import Server
   # ... implement tools ...
   ```

2. **Add configuration to `.env.example`**

   ```bash
   # My Service Configuration
   MY_SERVICE_HOST=192.168.1.100
   MY_SERVICE_API_KEY=your-api-key
   ```

3. **Update documentation**
   - Add server details to this README
   - Update `PROJECT_INSTRUCTIONS.example.md`
   - Update `CLAUDE.md` if adding new patterns or capabilities
   - Add security notes if applicable

4. **Test thoroughly**
   - Test with real infrastructure
   - Verify error handling
   - Check for sensitive data leaks
   - Review security implications

### Environment Variables

All MCP servers support two configuration methods:

**1. Environment Variables (`.env` file)**

- Simple key=value pairs
- Loaded automatically by each MCP server
- Good for simple setups or testing

**2. Ansible Inventory (recommended for production)**

- Centralized infrastructure definition
- Supports complex host groupings
- Better for multi-host environments
- Set `ANSIBLE_INVENTORY_PATH` in `.env`

### Coding Standards

- **Python 3.10+** syntax and features
- **Async/await** for all I/O operations
- **Type hints** where beneficial
- **Error handling** for network operations
- **Logging** to stderr for debugging
- **Security**: Validate inputs, sanitize outputs

### Testing Checklist

Before committing changes:

- [ ] Security git hook installed (`python helpers/install_git_hook.py`)
- [ ] Manual security check passes (`python helpers/pre_publish_check.py`)
- [ ] No sensitive data in code or commits
- [ ] Environment variables for all configuration
- [ ] Error handling for network failures
- [ ] Logging doesn't expose secrets
- [ ] Documentation updated
- [ ] Security implications reviewed
- [ ] `.gitignore` updated if needed

## 🐛 Troubleshooting

### MCP Servers Not Appearing in Claude

1. **Check Claude Desktop config:**

   ```bash
   # Windows
   type %APPDATA%\Claude\claude_desktop_config.json
   
   # Mac/Linux
   cat ~/.config/Claude/claude_desktop_config.json
   ```

2. **Verify Python path is correct** in config
3. **Restart Claude Desktop** completely
4. **Check logs** - MCP servers log to stderr

### Connection Errors

**Docker/Podman API:**

```bash
# Test connectivity
curl http://your-host:2375/containers/json

# Check firewall
netstat -an | grep 2375
```

**Pi-hole API:**

```bash
# Test API key
curl "http://your-pihole/api/stats/summary?sid=YOUR_API_KEY"
```

**Ollama:**

```bash
# Test Ollama endpoint
curl http://your-host:11434/api/tags
```

### Import Errors

If you get Python import errors:

```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt

# Verify MCP installation
pip show mcp
```

### Permission Errors

**On Linux/Mac:**

```bash
# Fix .env permissions
chmod 600 .env

# Make scripts executable
chmod +x *.py
```

## 📚 Additional Resources

### MCP Protocol

- [MCP Documentation](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Claude Desktop MCP Guide](https://docs.anthropic.com/claude/docs)

### Related Projects

- [Ansible Documentation](https://docs.ansible.com/)
- [Docker API Reference](https://docs.docker.com/engine/api/)
- [Pi-hole API](https://docs.pi-hole.net/)
- [Unifi Controller API](https://ubntwiki.com/products/software/unifi-controller/api)
- [Ollama API](https://github.com/ollama/ollama/blob/main/docs/api.md)

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details

Copyright (c) 2025 Barnaby Jeans

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

### For AI Assistants & Developers

**📖 Read [CLAUDE.md](CLAUDE.md) first** - This file contains:

- Complete project architecture and development patterns
- Security requirements and common pitfalls to avoid
- Specific workflows for adding features and fixing bugs
- AI assistant-specific guidance for working with this codebase

### Quick Start for Contributors

1. **Install security git hook** (`python helpers/install_git_hook.py`)
2. **Review security guidelines** in [SECURITY.md](SECURITY.md)
3. **No sensitive data** in commits (hook will block automatically)
4. **All configuration** uses environment variables or Ansible
5. **Update documentation** for any changes
6. **Test thoroughly** with real infrastructure

### Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test with your homelab setup
5. Update README and other docs as needed
6. Commit with clear messages (`git commit -m 'Add amazing feature'`)
7. Push to your fork (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Code Review Criteria

- Security best practices followed
- No hardcoded credentials or IPs
- Proper error handling
- Code follows existing patterns
- Documentation is clear and complete
- Changes are tested

## 🙏 Acknowledgments

- [Anthropic](https://anthropic.com/) for Claude and MCP
- The homelab community for inspiration
- Contributors and testers

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/bjeans/homelab-mcp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/bjeans/homelab-mcp/discussions)
- **Security**: See [SECURITY.md](SECURITY.md) for reporting vulnerabilities

---

**Remember**: This project handles critical infrastructure. Always prioritize security and test changes in a safe environment first!
