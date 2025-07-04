# Atlas Home Migration Guide

## Overview

Atlas MCP now uses a centralized output directory system to organize all files under a configurable `ATLAS_HOME` directory. This improves organization, reduces path management complexity, and provides better isolation between different Atlas deployments.

## What Changed

### Before (Legacy)
```
/app/REPOS/                    # Task storage
/app/REPOS/PROJECT_NAME_TASKS/ # Project tasks
/app/cache/                    # Cache files
~/.atlas/global/               # ML models  
~/.atlas/projects/             # Project cache
```

### After (Centralized)
```
~/.atlas/                      # Atlas home (configurable)
├── projects/                  # Task storage (replaces /app/REPOS)
├── cache/                     # L3 file cache
├── logs/                      # Log files
├── coordination/              # Cross-project coordination
├── models/                    # ML models and embeddings
└── temp/                      # Temporary files
```

## Migration Steps

### 1. Set Atlas Home Environment Variable

```bash
# In your shell profile (.bashrc, .zshrc, etc.)
export ATLAS_HOME="$HOME/.atlas"

# Or for Docker deployment
export ATLAS_HOME="/path/to/your/atlas/directory"
```

### 2. Update Docker Configuration

The new `docker-compose.yml` automatically uses Atlas home:

```yaml
environment:
  - ATLAS_HOME=${ATLAS_HOME:-/app/.atlas}

volumes:
  # Single mount for all Atlas data
  - ${ATLAS_HOME:-~/.atlas}:/app/.atlas:rw
  # Legacy compatibility
  - ${ATLAS_HOME:-~/.atlas}/projects:/app/REPOS:rw
```

### 3. Migrate Existing Data (Optional)

If you have existing data in `/app/REPOS` or scattered locations:

```bash
# Create Atlas home structure
mkdir -p ~/.atlas/{projects,cache,logs,coordination,models,temp}

# Migrate existing project data
if [ -d "/app/REPOS" ]; then
    cp -r /app/REPOS/* ~/.atlas/projects/
fi

# Migrate existing cache data
if [ -d "/app/cache" ]; then
    cp -r /app/cache/* ~/.atlas/cache/
fi
```

### 4. Update Scripts and Configuration

Use Atlas home paths in your scripts:

```bash
# Set Atlas home
ATLAS_HOME="${ATLAS_HOME:-~/.atlas}"

# Use Atlas paths
PROJECTS_DIR="${ATLAS_HOME}/projects"
CACHE_DIR="${ATLAS_HOME}/cache"
```

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ATLAS_HOME` | `~/.atlas` | Base directory for all Atlas outputs |
| `ATLAS_PROJECTS_DIR` | `${ATLAS_HOME}/projects` | Project storage directory |
| `ATLAS_CACHE_DIR` | `${ATLAS_HOME}/cache` | Cache directory |
| `ATLAS_LOGS_DIR` | `${ATLAS_HOME}/logs` | Log directory |

### Clean Architecture

The new system provides a clean, centralized architecture:

- Single `ATLAS_HOME` environment variable controls all paths
- No legacy path handling or redirection complexity
- Simple, predictable directory structure

## Benefits

### Organization
- All Atlas data in one location
- Clear separation of different data types
- Easy backup and migration

### Flexibility
- Configurable base directory
- Support for multiple Atlas installations
- Better container integration

### Maintenance
- Simplified path management
- Reduced configuration complexity
- Centralized cleanup and monitoring

## Troubleshooting

### Permission Issues
```bash
# Ensure proper ownership
sudo chown -R $USER:$USER ~/.atlas
chmod -R 755 ~/.atlas
```

### Docker Mount Issues
```bash
# Verify environment variable
echo $ATLAS_HOME

# Check mount points
docker-compose config | grep volumes -A 10
```

### Data Migration
```bash
# Verify migration
ls -la ~/.atlas/
ls -la ~/.atlas/projects/
```

## Docker Development

For development with Docker:

```bash
# Set Atlas home for development
export ATLAS_HOME="$(pwd)/atlas-data"

# Run with development configuration
docker-compose up
```

This creates a local `atlas-data/` directory for development, keeping your home directory clean.

## Production Deployment

For production:

```bash
# Use dedicated production directory
export ATLAS_HOME="/var/lib/atlas"

# Ensure proper permissions
sudo mkdir -p /var/lib/atlas
sudo chown atlas:atlas /var/lib/atlas
```

