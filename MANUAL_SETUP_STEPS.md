# Manual Setup Steps for Logo Assets

This document contains the manual steps needed to complete the logo asset integration after the assets have been created.

## ✅ Completed (Automated)

- ✅ Created icon-only variants (PNG and SVG)
- ✅ Generated all icon sizes (16x16 through 512x512)
- ✅ Created favicon files (favicon.ico, favicon-16x16.png, favicon-32x32.png)
- ✅ Created Apple touch icon (apple-touch-icon.png)
- ✅ Created social media preview image (homelab-mcp-social-preview.png)
- ✅ Updated assets/README.md with documentation

## 📋 Manual Steps Required

### 1. GitHub Repository Social Preview

**Purpose:** Display a professional preview image when sharing the repository on social media.

**Steps:**
1. Go to: https://github.com/bjeans/homelab-mcp/settings
2. Scroll down to the **"Social preview"** section
3. Click **"Edit"** → **"Upload an image"**
4. Upload: `assets/homelab-mcp-social-preview.png`
5. The preview will be visible at: https://github.com/bjeans/homelab-mcp

**Preview dimensions:** 1200x630 pixels (GitHub's recommended size)

### 2. GitHub Repository Configuration

**Update repository description:**
```
MCP servers for managing homelab infrastructure through Claude Desktop. Infrastructure as Context.
```

**Add repository topics:**
Go to: https://github.com/bjeans/homelab-mcp

Click the gear icon ⚙️ next to "About" and add these topics:
- `mcp`
- `homelab`
- `claude`
- `docker`
- `infrastructure`
- `monitoring`
- `model-context-protocol`
- `ansible`
- `python`

### 3. Docker Hub Repository Logo

**Purpose:** Display the icon on the Docker Hub repository page.

**Steps:**
1. Go to: https://hub.docker.com/r/bjeans/homelab-mcp
2. Log in to Docker Hub
3. Click on your repository
4. Click **"Manage Repository"** or the settings icon
5. Look for **"Repository Logo"** or **"Icon"** section
6. Upload: `assets/homelab-mcp-icon.png` (or any square size like `homelab-mcp-icon-512.png`)
7. Save changes

**Note:** Docker Hub prefers square images, so use the icon-only version (not the full logo with text).

### 4. Docker Hub Description (Optional)

Ensure the Docker Hub description matches the GitHub repository:

```markdown
# Homelab MCP Servers

Model Context Protocol (MCP) servers for managing homelab infrastructure through Claude Desktop.

## Features

- 7 specialized MCP servers for homelab management
- Docker/Podman container monitoring
- Pi-hole DNS management
- Unifi network device monitoring
- UPS/NUT monitoring
- Ollama AI model management
- Ansible inventory integration
- Network connectivity testing

## Quick Start

```bash
docker pull bjeans/homelab-mcp:latest
```

See the full documentation at: https://github.com/bjeans/homelab-mcp
```

## 🎯 Optional Enhancements

### Website Favicon Integration

If you have a website or documentation site, add these to the `<head>` section:

```html
<!-- Standard favicons -->
<link rel="icon" type="image/x-icon" href="/assets/favicon.ico">
<link rel="icon" type="image/png" sizes="16x16" href="/assets/favicon-16x16.png">
<link rel="icon" type="image/png" sizes="32x32" href="/assets/favicon-32x32.png">

<!-- Apple touch icon -->
<link rel="apple-touch-icon" sizes="180x180" href="/assets/apple-touch-icon.png">

<!-- For web manifests (PWA) -->
<link rel="icon" type="image/png" sizes="512x512" href="/assets/homelab-mcp-icon-512.png">
```

### Open Graph Meta Tags

For better social media sharing on websites:

```html
<meta property="og:title" content="Homelab MCP">
<meta property="og:description" content="Infrastructure as Context - MCP servers for homelab management">
<meta property="og:image" content="https://raw.githubusercontent.com/bjeans/homelab-mcp/main/assets/homelab-mcp-social-preview.png">
<meta property="og:url" content="https://github.com/bjeans/homelab-mcp">
<meta property="og:type" content="website">

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Homelab MCP">
<meta name="twitter:description" content="Infrastructure as Context - MCP servers for homelab management">
<meta name="twitter:image" content="https://raw.githubusercontent.com/bjeans/homelab-mcp/main/assets/homelab-mcp-social-preview.png">
```

## 📊 Verification

After completing the manual steps, verify:

1. **GitHub social preview:** Share the repository link on Twitter/LinkedIn and check the preview
2. **Docker Hub logo:** Visit https://hub.docker.com/r/bjeans/homelab-mcp and verify icon appears
3. **Repository topics:** Check that all topics are visible on the GitHub page

## 📝 Notes

- The social preview image may take a few minutes to propagate after upload
- GitHub caches social previews, so you may need to clear cache or use a different platform to see changes
- Docker Hub logo may take up to 24 hours to fully propagate across all CDN nodes

---

**Last Updated:** December 7, 2024
**Related Issue:** bjeans/homelab-mcp#43
