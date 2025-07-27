# MacReplay Docker Setup

This guide explains how to run MacReplay in a Docker container instead of as a Windows executable.

## Features in Docker
- ✅ Cross-platform compatibility (Linux, macOS, Windows with Docker)
- ✅ Easy deployment and management
- ✅ Persistent configuration and logs
- ✅ System-level ffmpeg integration
- ✅ Health checks and automatic restart

## Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Basic familiarity with Docker concepts

### 1. Clone or Download Files
Ensure you have the following files:
- `Dockerfile`
- `docker-compose.yml`
- `requirements.txt`
- `app.py` (or `app-docker.py`)
- `stb.py`
- `templates/` directory
- `static/` directory

### 2. Build and Run
```bash
# Using Docker Compose (recommended)
docker-compose up -d

# Or build and run manually
docker build -t macreplay .
docker run -d -p 8001:8001 -v $(pwd)/data:/app/data -v $(pwd)/logs:/app/logs macreplay
```

### 3. Access the Application
Open your browser to `http://localhost:8001`

## Configuration

### Data Persistence
The container uses volumes to persist data:
- `./data/` - Configuration files (MacReplay.json)
- `./logs/` - Application logs

### Environment Variables
You can customize the container with environment variables:

```yaml
environment:
  - HOST=0.0.0.0:8001          # Server bind address
  - CONFIG=/app/data/MacReplay.json  # Config file path
```

### Port Configuration
The default port is 8001. To use a different port:

```yaml
ports:
  - "9001:8001"  # Maps host port 9001 to container port 8001
```

## Docker Compose Configuration

### Basic Setup
```yaml
version: '3.8'
services:
  macreplay:
    build: .
    ports:
      - "8001:8001"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
```

### Advanced Setup with Networks
```yaml
version: '3.8'
services:
  macreplay:
    build: .
    container_name: macreplay
    ports:
      - "8001:8001"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - HOST=0.0.0.0:8001
    restart: unless-stopped
    networks:
      - media-network

networks:
  media-network:
    external: true
```

## Plex Integration

When using with Plex, use the Docker host's IP address instead of `127.0.0.1`:

1. **Find your Docker host IP:**
   ```bash
   # For Docker Desktop on Windows/Mac
   http://host.docker.internal:8001
   
   # For Linux or custom networks
   http://YOUR_HOST_IP:8001
   ```

2. **Configure Plex:**
   - In Plex settings, go to "Live TV and DVR"
   - Click "Set Up Plex Tuner"
   - Enter: `http://YOUR_HOST_IP:8001/xmltv`
   - Use playlist: `http://YOUR_HOST_IP:8001/playlist.m3u`

## Management Commands

### View Logs
```bash
# Container logs
docker-compose logs -f macreplay

# Application logs
docker exec macreplay cat /app/logs/MacReplay.log
```

### Restart Container
```bash
docker-compose restart macreplay
```

### Update Container
```bash
# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Backup Configuration
```bash
# Backup data directory
tar -czf macreplay-backup-$(date +%Y%m%d).tar.gz data/
```

## Troubleshooting

### Container Won't Start
1. Check logs: `docker-compose logs macreplay`
2. Verify port availability: `netstat -tulpn | grep 8001`
3. Check file permissions on data/logs directories

### Can't Access Web Interface
1. Verify container is running: `docker-compose ps`
2. Check port mapping in docker-compose.yml
3. Test locally: `curl http://localhost:8001`

### Streams Not Working
1. Verify ffmpeg is working: `docker exec macreplay ffmpeg -version`
2. Check network connectivity from container
3. Review application logs for specific errors

### Performance Issues
1. Adjust ffmpeg threads in settings
2. Monitor container resources: `docker stats macreplay`
3. Consider resource limits in docker-compose.yml

## Security Notes

1. **Change default credentials** in the application settings
2. **Use reverse proxy** for external access (nginx, Traefik)
3. **Enable authentication** in MacReplay settings
4. **Keep Docker images updated**

## Differences from Windows Version

### Advantages of Docker Version
- ✅ Cross-platform compatibility
- ✅ Easy updates and rollbacks
- ✅ Better resource management
- ✅ Integrated with container ecosystems
- ✅ System-level ffmpeg (always up-to-date)

### Limitations
- ⚠️ Requires Docker knowledge
- ⚠️ Network configuration may be more complex
- ⚠️ No single executable file

## Support

If you encounter issues:
1. Check the logs first
2. Verify your Docker setup
3. Test with a minimal configuration
4. Create an issue with relevant logs and configuration 