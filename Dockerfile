# Homelab MCP Servers - Docker Container
# Packages Docker and Ping MCP servers for easy distribution
# https://github.com/bjeans/homelab-mcp
# https://hub.docker.com/r/bjeans/homelab-mcp

# === Builder Stage ===
FROM python:3.11-alpine3.19 AS builder

# Install build dependencies (temporary, will be removed in runtime stage)
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    openssl-dev \
    yaml-dev

# Copy requirements
COPY requirements.txt .

# Install Python dependencies into /install directory
RUN pip install --no-cache-dir --target=/install -r requirements.txt

# === Runtime Stage ===
FROM python:3.11-alpine3.19

# Metadata
LABEL maintainer="Barnaby Jeans <barnaby@bjeans.dev>"
LABEL description="MCP servers for homelab infrastructure management"
LABEL org.opencontainers.image.source="https://github.com/bjeans/homelab-mcp"
LABEL org.opencontainers.image.licenses="MIT"

# Install runtime dependencies first (before creating user with bash shell)
RUN apk add --no-cache \
    bash \
    iputils-ping \
    procps-ng \
    yaml \
    libffi

# Create non-root user for security (now bash is available)
RUN adduser -D -u 1000 -s /bin/bash mcpuser && \
    mkdir -p /config /app && \
    chown -R mcpuser:mcpuser /app /config

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /install /usr/local/lib/python3.11/site-packages

# Copy requirements for reference
COPY --chown=mcpuser:mcpuser requirements.txt .

# Copy MCP server files
COPY --chown=mcpuser:mcpuser ansible_config_manager.py .
COPY --chown=mcpuser:mcpuser homelab_unified_mcp.py .
COPY --chown=mcpuser:mcpuser docker_mcp_podman.py .
COPY --chown=mcpuser:mcpuser ping_mcp_server.py .
COPY --chown=mcpuser:mcpuser ollama_mcp.py .
COPY --chown=mcpuser:mcpuser pihole_mcp.py .
COPY --chown=mcpuser:mcpuser unifi_mcp_optimized.py .
# COPY --chown=mcpuser:mcpuser mcp_registry_inspector.py .
COPY --chown=mcpuser:mcpuser unifi_exporter.py .
COPY --chown=mcpuser:mcpuser mcp_config_loader.py .
COPY --chown=mcpuser:mcpuser ups_mcp_server.py .

# Copy entrypoint script
COPY --chown=mcpuser:mcpuser docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Switch to non-root user
USER mcpuser

# Environment variables with defaults
ENV PYTHONUNBUFFERED=1 \
    # ENABLED_SERVERS=docker,ping \
    ANSIBLE_INVENTORY_PATH=/config/ansible_hosts.yml 

# Expose stdio for MCP communication
# MCP servers communicate over stdin/stdout, no ports needed

# Health check (checks if Python process is running)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep -f "python.*mcp" || exit 1

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
