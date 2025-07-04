#!/bin/bash
# ATLAS MCP Quick Fix Script
# Automated fixes for common MCP integration issues

set -e

CONTAINER_NAME="${1:-atlas-commands-mcp}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔧 ATLAS MCP Quick Fix Procedure"
echo "Container: $CONTAINER_NAME"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to check container status
check_container_status() {
    log_info "Checking container status..."
    
    if docker ps --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        STATUS=$(docker ps --filter "name=${CONTAINER_NAME}" --format "{{.Status}}")
        log_success "Container is running: $STATUS"
        
        # Check if healthy
        if echo "$STATUS" | grep -q "healthy"; then
            log_success "Container is healthy"
            return 0
        else
            log_warning "Container is not healthy"
            return 1
        fi
    else
        log_error "Container not found or not running"
        return 2
    fi
}

# Function to restart container
restart_container() {
    log_info "Restarting ATLAS container..."
    
    if docker ps -a --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        docker restart "$CONTAINER_NAME"
        log_success "Container restarted"
        
        # Wait for health check
        log_info "Waiting for health check..."
        sleep 15
        
        if check_container_status; then
            log_success "Container is now healthy"
            return 0
        else
            log_warning "Container may need more time to become healthy"
            return 1
        fi
    else
        log_error "Container does not exist"
        return 1
    fi
}

# Function to start container via docker-compose
start_with_compose() {
    log_info "Starting container with docker-compose..."
    
    if [ -f "docker-compose.yml" ]; then
        docker-compose up -d atlas-commands
        sleep 10
        log_success "Container started via docker-compose"
        return 0
    else
        log_error "docker-compose.yml not found"
        return 1
    fi
}

# Function to clear caches
clear_caches() {
    log_info "Clearing caches..."
    
    # Try to clear cache via MCP tool
    if python3 mcp-client-working.py call clear_all_cache '{}' 2>/dev/null; then
        log_success "Cache cleared via MCP tool"
    else
        log_warning "Could not clear cache via MCP tool"
        
        # Try direct Python call
        if docker exec "$CONTAINER_NAME" python -c "
try:
    from atlas_commands.caching.cache_manager import CacheManager
    CacheManager.clear_all_cache()
    print('Cache cleared successfully')
except Exception as e:
    print(f'Cache clear failed: {e}')
" 2>/dev/null; then
            log_success "Cache cleared via direct Python call"
        else
            log_warning "Could not clear cache directly"
        fi
    fi
}

# Function to validate storage permissions
check_storage_permissions() {
    log_info "Checking storage permissions..."
    
    # Check if REPOS directory is accessible
    if docker exec "$CONTAINER_NAME" ls -la /app/REPOS >/dev/null 2>&1; then
        log_success "Storage directory is accessible"
        
        # Check specific permissions
        PERMS=$(docker exec "$CONTAINER_NAME" stat -c "%a %U:%G" /app/REPOS 2>/dev/null || echo "unknown")
        log_info "REPOS permissions: $PERMS"
        
        return 0
    else
        log_error "Storage directory is not accessible"
        return 1
    fi
}

# Function to test basic MCP connectivity
test_mcp_connectivity() {
    log_info "Testing MCP connectivity..."
    
    if [ -f "mcp-client-working.py" ]; then
        if timeout 30s python3 mcp-client-working.py test >/tmp/mcp-test.log 2>&1; then
            log_success "MCP connectivity test passed"
            return 0
        else
            log_error "MCP connectivity test failed"
            log_info "Check /tmp/mcp-test.log for details"
            return 1
        fi
    else
        log_warning "MCP test client not found, skipping connectivity test"
        return 0
    fi
}

# Function to check Docker daemon
check_docker_daemon() {
    log_info "Checking Docker daemon..."
    
    if docker info >/dev/null 2>&1; then
        log_success "Docker daemon is running"
        return 0
    else
        log_error "Docker daemon is not accessible"
        log_info "Try: sudo systemctl start docker"
        return 1
    fi
}

# Function to cleanup stale containers
cleanup_stale_containers() {
    log_info "Checking for stale containers..."
    
    # Find all containers with similar names
    SIMILAR_CONTAINERS=$(docker ps -a --format "{{.Names}}" | grep -E "(atlas|mcp)" | grep -v "^${CONTAINER_NAME}$" || true)
    
    if [ -n "$SIMILAR_CONTAINERS" ]; then
        log_warning "Found similar containers:"
        echo "$SIMILAR_CONTAINERS"
        
        read -p "Remove stale containers? (y/N): " -r
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "$SIMILAR_CONTAINERS" | xargs -I {} docker rm -f {}
            log_success "Stale containers removed"
        fi
    else
        log_success "No stale containers found"
    fi
}

# Function to validate environment variables
check_environment() {
    log_info "Checking environment variables..."
    
    # Check key environment variables in container
    ENV_VARS="PYTHONUNBUFFERED LOG_LEVEL PROJECT_NAME ATLAS_STORAGE_PATH ATLAS_STARTUP_MODE"
    
    for var in $ENV_VARS; do
        VALUE=$(docker exec "$CONTAINER_NAME" printenv "$var" 2>/dev/null || echo "NOT_SET")
        if [ "$VALUE" = "NOT_SET" ]; then
            log_warning "Environment variable $var is not set"
        else
            log_info "$var=$VALUE"
        fi
    done
}

# Function to generate diagnostic report
generate_diagnostic_report() {
    log_info "Generating diagnostic report..."
    
    REPORT_FILE="/tmp/atlas-mcp-diagnostic-$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "ATLAS MCP Diagnostic Report"
        echo "Generated: $(date)"
        echo "Container: $CONTAINER_NAME"
        echo "=========================="
        echo
        
        echo "Docker Info:"
        docker info 2>&1 | head -20
        echo
        
        echo "Container Status:"
        docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        echo
        
        echo "Container Logs (last 50 lines):"
        docker logs --tail 50 "$CONTAINER_NAME" 2>&1
        echo
        
        echo "Storage Mount Info:"
        docker exec "$CONTAINER_NAME" df -h /app/REPOS 2>&1 || echo "Storage not accessible"
        echo
        
        echo "Process List:"
        docker exec "$CONTAINER_NAME" ps aux 2>&1 || echo "Process list not accessible"
        
    } > "$REPORT_FILE"
    
    log_success "Diagnostic report saved to: $REPORT_FILE"
}

# Main execution flow
main() {
    log_info "Starting ATLAS MCP diagnostic and fix procedure..."
    
    # Step 1: Check Docker daemon
    if ! check_docker_daemon; then
        log_error "Docker daemon issues detected. Please fix Docker first."
        exit 1
    fi
    
    # Step 2: Check container status
    CONTAINER_STATUS_CODE=0
    check_container_status || CONTAINER_STATUS_CODE=$?
    
    case $CONTAINER_STATUS_CODE in
        0)
            log_success "Container is healthy, proceeding with tests..."
            ;;
        1)
            log_warning "Container is unhealthy, attempting restart..."
            restart_container || {
                log_error "Container restart failed"
                generate_diagnostic_report
                exit 1
            }
            ;;
        2)
            log_warning "Container not running, attempting to start..."
            start_with_compose || restart_container || {
                log_error "Could not start container"
                exit 1
            }
            ;;
    esac
    
    # Step 3: Wait for container to be ready
    log_info "Waiting for container to be ready..."
    sleep 5
    
    # Step 4: Check storage permissions
    check_storage_permissions || log_warning "Storage issues detected"
    
    # Step 5: Check environment
    check_environment
    
    # Step 6: Clear caches
    clear_caches
    
    # Step 7: Test MCP connectivity
    if test_mcp_connectivity; then
        log_success "All systems operational!"
    else
        log_warning "MCP connectivity issues detected"
        generate_diagnostic_report
    fi
    
    # Optional: Cleanup
    if [ "$2" = "--cleanup" ]; then
        cleanup_stale_containers
    fi
    
    log_success "Quick fix procedure completed!"
}

# Trap to ensure cleanup on exit
trap 'log_info "Quick fix script interrupted"' INT TERM

# Check for help flag
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "ATLAS MCP Quick Fix Script"
    echo "Usage: $0 [CONTAINER_NAME] [--cleanup]"
    echo ""
    echo "Options:"
    echo "  CONTAINER_NAME    Name of the ATLAS container (default: atlas-commands-mcp)"
    echo "  --cleanup         Also cleanup stale containers"
    echo "  --help, -h        Show this help message"
    echo ""
    echo "This script will:"
    echo "  ✓ Check Docker daemon status"
    echo "  ✓ Verify container health"
    echo "  ✓ Restart container if needed"
    echo "  ✓ Clear caches"
    echo "  ✓ Validate storage permissions"
    echo "  ✓ Test MCP connectivity"
    echo "  ✓ Generate diagnostic report if issues found"
    exit 0
fi

# Run main function
main "$@"