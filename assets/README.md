# Homelab MCP Logo Assets

This directory contains the official branding assets for the Homelab MCP project.

## Available Files

### Logo Files (Full Logo with Text)

- **`Homelab-mcp-logo-transparent.png`** (1024x1024, 1.0MB)
  - High-resolution logo with transparent background
  - Use for: Documentation, GitHub social preview, presentations

- **`Homelab-mcp-logo-white.png`** (1024x1024, 477KB)
  - High-resolution logo with white background
  - Use for: Print materials, light backgrounds

- **`Homelab-mcp-logo-transparent.svg`** (160KB)
  - Vector version of the logo (traced from PNG)
  - Use for: Scalable graphics, web use
  - Note: Large file size due to tracing complexity

### Icon Files (Icon Only, No Text)

- **`homelab-mcp-icon.png`** (1024x1024, 735KB)
  - Square icon featuring house and network graph only
  - Transparent background
  - Use for: App icons, avatars, square displays

- **`homelab-mcp-icon.svg`** (482 bytes)
  - Vector version of icon-only design
  - Use for: Scalable icon applications

### Icon Sizes (Multiple Resolutions)

Pre-generated icon sizes for various use cases:

- **`homelab-mcp-icon-16.png`** (16x16, 716 bytes)
- **`homelab-mcp-icon-32.png`** (32x32, 1.6KB)
- **`homelab-mcp-icon-64.png`** (64x64, 4.1KB)
- **`homelab-mcp-icon-128.png`** (128x128, 11KB)
- **`homelab-mcp-icon-256.png`** (256x256, 31KB)
- **`homelab-mcp-icon-512.png`** (512x512, 136KB)

### Favicon Files

Ready-to-use favicon files for websites:

- **`favicon.ico`** (22KB)
  - Multi-resolution ICO file (contains 16x16, 32x32, 64x64)
  - Use for: Browser tab icons, bookmarks

- **`favicon-16x16.png`** (16x16, 716 bytes)
  - Standard small favicon
  
- **`favicon-32x32.png`** (32x32, 1.6KB)
  - Standard medium favicon

- **`apple-touch-icon.png`** (180x180, 17KB)
  - Apple device home screen icon
  - Use for: iOS/iPadOS web app icons, Safari pinned tabs

### Social Media Assets

- **`homelab-mcp-social-preview.png`** (1200x630, 599KB)
  - Social media preview image with logo and tagline
  - Dark background (#0e1a2b) matching logo theme
  - Use for: GitHub repository social preview, Twitter/LinkedIn cards, Open Graph images

## Logo Design

The logo features:
- **House icon** - Represents the homelab infrastructure
- **Network graph** - Represents the Model Context Protocol connections
- **Tagline** - "Infrastructure as Context"

### Color Palette

- **Navy Blue** (#1e3a5f) - House and servers
- **Bright Blue** (#3b82f6) - Central MCP node
- **Green** (#10b981) - Network connection nodes
- **Purple** (#8b5cf6) - Network peripheral nodes
- **Light Blue** (#60a5fa) - Connection lines

## Usage Guidelines

### Recommended Uses

**Full Logo (with text):**
- ✅ GitHub README headers
- ✅ Documentation and presentations
- ✅ Blog posts and articles (hero images)
- ✅ Marketing materials with clear branding

**Icon Only (no text):**
- ✅ Docker Hub repository logo
- ✅ Browser favicons
- ✅ App icons
- ✅ Social media profile pictures
- ✅ Small displays where text would be illegible

**Social Preview:**
- ✅ GitHub repository settings → Social preview
- ✅ Open Graph meta tags for websites
- ✅ Twitter/X Card images
- ✅ LinkedIn article previews

### How to Use Favicons in HTML

Add these lines to your HTML `<head>` section:

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

### Setting Up GitHub Social Preview

1. Go to your GitHub repository
2. Navigate to **Settings** → **General**
3. Scroll to **Social preview**
4. Click **Edit** → **Upload an image**
5. Upload `homelab-mcp-social-preview.png`

The preview will appear when sharing your repository on social media.

### Setting Up Docker Hub Logo

1. Go to https://hub.docker.com/r/bjeans/homelab-mcp
2. Click on repository settings
3. Upload `homelab-mcp-icon.png` (or any square icon size) as repository logo

### Attribution

When using the logo in derivative works, please attribute:
> Logo for Homelab MCP - https://github.com/bjeans/homelab-mcp

## License

The Homelab MCP logo is part of the Homelab MCP project and is licensed under the MIT License.
See the main [LICENSE](../LICENSE) file for details.
