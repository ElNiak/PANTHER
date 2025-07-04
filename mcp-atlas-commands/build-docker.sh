#!/bin/bash

# Build script for atlas-commands MCP server Docker image

set -e

echo "Starting the build for redis and atlas-commands MCP server Docker image..."

# Check if redis_data volume exists, create if it doesn't
if ! docker volume inspect redis_data >/dev/null 2>&1; then
    echo "Creating redis_data volume..."
    docker volume create redis_data
else
    echo "Using existing redis_data volume"
fi

# Check if redis container is already running
if ! docker ps -q --filter "name=atlas-redis" | grep -q .; then
    # Check if container exists but is stopped
    if docker ps -aq --filter "name=atlas-redis" | grep -q .; then
        echo "Starting existing atlas-redis container..."
        docker start atlas-redis
    else
        echo "Creating and starting atlas-redis container..."
        # Run Redis container
        docker run -d \
                --name atlas-redis \
                --restart unless-stopped \
                -p 6379:6379 \
                -v redis_data:/data \
                redis:7-alpine \
                redis-server --appendonly yes
    fi
else
    echo "atlas-redis container is already running"
fi

echo "Building atlas-commands MCP server Docker image..."

# Build the Docker image
docker build -t atlas-commands-mcp:latest .

echo "✅ Docker image built successfully: atlas-commands-mcp:latest"

# Optional: Test the image
echo "Testing the Docker image..."
docker run --rm atlas-commands-mcp:latest python -c "import atlas_commands.server; print('✅ Server module imports successfully')"

echo "🚀 Ready to use! The MCP server can now be started via Claude's MCP interface."