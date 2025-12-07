# Homelab MCP Logo Assets

This directory contains the official branding assets for the Homelab MCP project.

## Available Files

### Logo Files

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

✅ GitHub README headers
✅ Documentation and presentations
✅ Social media sharing (use transparent version)
✅ Docker Hub repository logo
✅ Blog posts and articles

### Attribution

When using the logo in derivative works, please attribute:
> Logo for Homelab MCP - https://github.com/bjeans/homelab-mcp

## Need Different Sizes?

The PNG files are 1024x1024 and can be resized as needed using image editing tools:

```bash
# Using ImageMagick to resize
magick Homelab-mcp-logo-transparent.png -resize 512x512 logo-512.png

# Using macOS sips
sips -Z 512 Homelab-mcp-logo-transparent.png --out logo-512.png
```

## License

The Homelab MCP logo is part of the Homelab MCP project and is licensed under the MIT License.
See the main [LICENSE](../LICENSE) file for details.
