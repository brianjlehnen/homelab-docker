### homelab-docker/README.md

### Lab1830 Docker Services

Docker-based services for media management and personal utilities in a homelab environment.

### Overview

Collection of Docker Compose stacks for stable, high-performance services. Designed for services requiring direct host access, media processing, and external connectivity.

### Architecture

- **Platform:** Docker + Docker Compose
- **Networking:** Traefik reverse proxy
- **Storage:** NFS mounts to Synology NAS
- **Management:** Individual compose stacks

### Repository Structure
```bash
docker
├── appdata
├── secrets
└── stacks
    └── application
        └── compose.yaml
```
### Services

**Media Stack:**
- Plex media server
- ARR stack (content automation)
- NZBGet, SABnzbd (download clients)
- Overseerr (request management)

**Infrastructure:**
- Traefik (reverse proxy)
- Uptime Kuma (monitoring)
- Dockge (management)

**Utilities:**
- Smokeping
- Speedtest

### Technology Stack

- Docker + Docker Compose
- Traefik
- Cloudflare tunnel
- NFS storage

### Usage

Each service stack is independently deployable via Docker Compose. Services are routed through Traefik.
