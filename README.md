# Lab1830 Docker Homelab

Docker Compose configurations for Lab1830 homelab infrastructure.

## Services

### Media Stack
- **Plex**: Media server
- **Radarr/Sonarr/Whisparr**: Media automation
- **Overseerr**: Media requests
- **Jellyfin**: Alternative media server
- **Tautulli**: Plex analytics

### Download Clients
- **SABnzbd**: Primary usenet downloader
- **NZBGet**: Alternative usenet client
- **Prowlarr**: Indexer management

### Infrastructure
- **Traefik**: Reverse proxy with automatic HTTPS
- **Portainer**: Container management
- **Dockge**: Docker Compose stack management
- **Watchtower**: Automated updates
- **Socket Proxy**: Secure Docker API access

### Monitoring & Utilities
- **Promtail**: Log shipping to Kubernetes Loki
- **Speedtest Tracker**: Network monitoring
- **Mealie**: Recipe management
- **Smokeping**: Network latency monitoring

### Custom Applications
- **Budget Automation**: Custom Python financial automation

## Deployment

Each service is in its own directory with a `compose.yaml` file.

### Environment Variables
Copy `.env.example` to `.env` in each service directory and configure as needed.

### Traefik Certificates
Place SSL certificates in `traefik/certs/` (not included in repo).

## Directory Structure on Host
/home/blehnen/docker/
├── stacks/          # This repository
└── appdata/         # Persistent data (not in Git)

