#!/bin/bash
#
# ATLAS MCP Multi-Project Deployment Script
# 
# This script sets up multi-project ATLAS MCP containers with complete isolation
# while reusing existing task management components following DRY, SOLID, and KISS principles.
#
# Usage:
#   ./deploy-multi-project.sh setup                    # Full setup
#   ./deploy-multi-project.sh add-project <name> <path> # Add single project
#   ./deploy-multi-project.sh cleanup                  # Clean old containers
#   ./deploy-multi-project.sh status                   # Show status

set -e

# Configuration
ATLAS_CACHE_ROOT="${HOME}/.atlas-cache"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/atlas-project-config.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# Check dependencies
check_dependencies() {
    log_info "Checking dependencies..."
    
    local deps=("docker" "jq")
    local missing_deps=()
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing_deps+=("$dep")
        fi
    done
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing dependencies: ${missing_deps[*]}"
        log_error "Please install: ${missing_deps[*]}"
        exit 1
    fi
    
    # Check Docker is running
    if ! docker info &> /dev/null; then
        log_error "Docker is not running. Please start Docker."
        exit 1
    fi
    
    log_info "✓ All dependencies satisfied"
}

# Setup global cache directory
setup_global_cache() {
    log_info "Setting up global Atlas cache directory..."
    
    mkdir -p "${ATLAS_CACHE_ROOT}/shared/ml-models"
    mkdir -p "${ATLAS_CACHE_ROOT}/shared/global-cache"
    
    # Set proper permissions
    chmod -R 755 "${ATLAS_CACHE_ROOT}"
    
    log_info "✓ Global cache directory created: ${ATLAS_CACHE_ROOT}"
}

# Build container if needed
ensure_atlas_container() {
    log_info "Checking ATLAS MCP container..."
    
    # Check if atlas-commands-mcp:fast exists
    if ! docker images | grep -q "atlas-commands-mcp.*fast"; then
        log_warn "ATLAS MCP container not found. Please build it first:"
        log_warn "  cd ${SCRIPT_DIR} && docker build -t atlas-commands-mcp:fast ."
        exit 1
    fi
    
    log_info "✓ ATLAS MCP container available"
}

# Create project configuration
create_project_config() {
    if [[ -f "$CONFIG_FILE" ]]; then
        log_info "Project configuration already exists: $CONFIG_FILE"
        return
    fi
    
    log_info "Creating default project configuration..."
    
    cat > "$CONFIG_FILE" << 'EOF'
{
  "projects": {},
  "global_settings": {
    "cache_root": "",
    "shared_models": true,
    "max_concurrent_containers": 5,
    "health_check_interval": 30,
    "default_container_type": "fast",
    "default_log_level": "INFO"
  }
}
EOF
    
    # Update cache root in config
    jq --arg cache_root "$ATLAS_CACHE_ROOT" '.global_settings.cache_root = $cache_root' "$CONFIG_FILE" > "$CONFIG_FILE.tmp" && mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"
    
    log_info "✓ Default project configuration created"
}

# Add project to configuration
add_project_to_config() {
    local project_name="$1"
    local project_path="$2"
    local container_type="${3:-fast}"
    local tools_enabled="${4:-task_management,memory_management,workflow_intelligence}"
    
    log_info "Adding project to configuration: $project_name"
    
    # Validate project path
    if [[ ! -d "$project_path" ]]; then
        log_error "Project path does not exist: $project_path"
        return 1
    fi
    
    # Add project to config
    local project_config=$(cat << EOF
{
  "path": "$project_path",
  "container_type": "$container_type", 
  "profile": "full",
  "tools_enabled": ["$(echo $tools_enabled | sed 's/,/", "/g')"],
  "cache_strategy": "project_isolated",
  "log_level": "INFO",
  "workspace_isolation": true
}
EOF
)
    
    # Update configuration file
    jq --arg name "$project_name" --argjson config "$project_config" '.projects[$name] = $config' "$CONFIG_FILE" > "$CONFIG_FILE.tmp" && mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"
    
    log_info "✓ Project added to configuration: $project_name"
}

# Setup single project
setup_project() {
    local project_name="$1"
    local project_path="$2"
    local container_type="${3:-fast}"
    
    log_info "Setting up project: $project_name"
    
    # Validate project path
    if [[ ! -d "$project_path" ]]; then
        log_error "Project path does not exist: $project_path"
        return 1
    fi
    
    # Create project-specific cache directory
    local project_cache_dir="${ATLAS_CACHE_ROOT}/${project_name}"
    mkdir -p "$project_cache_dir"/{memory,tasks,cache,logs,artifacts,backups}
    
    # Generate project-specific MCP config
    local mcp_config_file=".mcp.${project_name}.json"
    
    cat > "$mcp_config_file" << EOF
{
  "mcpServers": {
    "atlas-${project_name}": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm", 
        "--name", "atlas-${project_name}",
        "-v", "${project_path}:/app/workspace",
        "-v", "${project_cache_dir}:/app/cache",
        "-v", "${ATLAS_CACHE_ROOT}/shared:/app/shared:ro",
        "-e", "ATLAS_PROJECT_ID=${project_name}",
        "-e", "ATLAS_PROJECT_ROOT=/app/workspace",
        "-e", "ATLAS_WORKSPACE_ISOLATION=true",
        "-e", "ATLAS_CONTAINER_TYPE=${container_type}",
        "-e", "ATLAS_LOG_LEVEL=INFO",
        "atlas-commands-mcp:${container_type}"
      ],
      "env": {
        "ATLAS_PROJECT_ID": "${project_name}",
        "ATLAS_ENV": "production"
      }
    }
  }
}
EOF
    
    # Set proper permissions
    chmod 644 "$mcp_config_file"
    chmod -R 755 "$project_cache_dir"
    
    log_info "✓ Created MCP config: $mcp_config_file"
    log_info "✓ Created cache directory: $project_cache_dir"
}

# Load projects from configuration
setup_all_projects() {
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_error "Project configuration file not found: $CONFIG_FILE"
        exit 1
    fi
    
    log_info "Setting up all projects from configuration..."
    
    # Extract project names
    local projects=($(jq -r '.projects | keys[]' "$CONFIG_FILE"))
    
    if [[ ${#projects[@]} -eq 0 ]]; then
        log_warn "No projects configured in $CONFIG_FILE"
        return
    fi
    
    # Setup each project
    for project_name in "${projects[@]}"; do
        local project_path=$(jq -r ".projects[\"$project_name\"].path" "$CONFIG_FILE")
        local container_type=$(jq -r ".projects[\"$project_name\"].container_type" "$CONFIG_FILE")
        
        setup_project "$project_name" "$project_path" "$container_type"
    done
    
    log_info "✓ All projects setup completed"
}

# Cleanup old containers
cleanup_old_containers() {
    log_info "Cleaning up old ATLAS containers..."
    
    # Stop running atlas containers
    local running_containers=$(docker ps --format "{{.Names}}" | grep "^atlas-" || true)
    if [[ -n "$running_containers" ]]; then
        log_info "Stopping running containers: $running_containers"
        echo "$running_containers" | xargs docker stop
    fi
    
    # Remove stopped atlas containers
    local stopped_containers=$(docker ps -a --format "{{.Names}}" | grep "^atlas-" || true)
    if [[ -n "$stopped_containers" ]]; then
        log_info "Removing stopped containers: $stopped_containers"
        echo "$stopped_containers" | xargs docker rm
    fi
    
    log_info "✓ Container cleanup completed"
}

# Show deployment status
show_status() {
    log_info "ATLAS MCP Multi-Project Status"
    echo "=================================="
    
    # Check cache directory
    if [[ -d "$ATLAS_CACHE_ROOT" ]]; then
        echo "✓ Cache directory: $ATLAS_CACHE_ROOT"
        echo "  Size: $(du -sh "$ATLAS_CACHE_ROOT" 2>/dev/null | cut -f1 || echo "unknown")"
    else
        echo "✗ Cache directory missing: $ATLAS_CACHE_ROOT"
    fi
    
    # Check container images
    echo ""
    echo "Container Images:"
    if docker images | grep -q "atlas-commands-mcp"; then
        docker images | grep "atlas-commands-mcp" | while read -r line; do
            echo "  ✓ $line"
        done
    else
        echo "  ✗ No ATLAS container images found"
    fi
    
    # Check running containers
    echo ""
    echo "Running Containers:"
    local running=$(docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" | grep "atlas-" || echo "  ℹ️ No ATLAS containers running")
    echo "$running"
    
    # Check project configurations
    echo ""
    echo "Project Configurations:"
    if [[ -f "$CONFIG_FILE" ]]; then
        local project_count=$(jq '.projects | length' "$CONFIG_FILE")
        echo "  ✓ Configuration file: $CONFIG_FILE"
        echo "  ✓ Configured projects: $project_count"
        
        if [[ $project_count -gt 0 ]]; then
            jq -r '.projects | keys[]' "$CONFIG_FILE" | while read -r project; do
                local mcp_file=".mcp.${project}.json"
                local cache_dir="${ATLAS_CACHE_ROOT}/${project}"
                
                if [[ -f "$mcp_file" && -d "$cache_dir" ]]; then
                    echo "    ✓ $project"
                else
                    echo "    ✗ $project (incomplete setup)"
                fi
            done
        fi
    else
        echo "  ✗ No configuration file found"
    fi
    
    # Check MCP config files
    echo ""
    echo "MCP Configuration Files:"
    local mcp_files=($(ls .mcp.*.json 2>/dev/null || true))
    if [[ ${#mcp_files[@]} -gt 0 ]]; then
        for file in "${mcp_files[@]}"; do
            echo "  ✓ $file"
        done
    else
        echo "  ℹ️ No MCP configuration files found"
    fi
}

# Test project setup
test_project_setup() {
    local project_name="$1"
    
    if [[ -z "$project_name" ]]; then
        log_error "Project name required for testing"
        return 1
    fi
    
    log_info "Testing project setup: $project_name"
    
    local mcp_file=".mcp.${project_name}.json"
    if [[ ! -f "$mcp_file" ]]; then
        log_error "MCP configuration not found: $mcp_file"
        return 1
    fi
    
    # Test container startup
    log_info "Testing container startup..."
    local container_name="atlas-${project_name}-test"
    
    # Extract docker command from MCP config
    local project_path=$(jq -r ".mcpServers[\"atlas-${project_name}\"].args[5]" "$mcp_file" | cut -d: -f1)
    local cache_path=$(jq -r ".mcpServers[\"atlas-${project_name}\"].args[7]" "$mcp_file" | cut -d: -f1)
    
    # Test basic container functionality
    docker run --rm \
        --name "$container_name" \
        -v "${project_path}:/app/workspace" \
        -v "${cache_path}:/app/cache" \
        -e "ATLAS_PROJECT_ID=${project_name}" \
        -e "ATLAS_PROJECT_ROOT=/app/workspace" \
        -e "ATLAS_WORKSPACE_ISOLATION=true" \
        atlas-commands-mcp:fast \
        python -c "
from atlas_commands.project.context_manager import get_project_context_manager
context = get_project_context_manager()
print(f'✓ Project context initialized: {context.project_id}')
print(f'✓ Project isolation: {context.workspace_isolation}')
print(f'✓ Cache directory: {context.cache_root}')
"
    
    log_info "✓ Project setup test completed successfully"
}

# Main function
main() {
    local command="${1:-help}"
    
    case "$command" in
        "setup")
            log_info "Starting ATLAS MCP Multi-Project Setup..."
            check_dependencies
            setup_global_cache
            ensure_atlas_container
            create_project_config
            setup_all_projects
            log_info "✅ Setup completed successfully!"
            ;;
        "add-project")
            if [[ $# -lt 3 ]]; then
                log_error "Usage: $0 add-project <project_name> <project_path> [container_type]"
                exit 1
            fi
            check_dependencies
            setup_global_cache
            ensure_atlas_container
            create_project_config
            add_project_to_config "$2" "$3" "${4:-fast}"
            setup_project "$2" "$3" "${4:-fast}"
            log_info "✅ Project added successfully: $2"
            ;;
        "cleanup")
            cleanup_old_containers
            ;;
        "status")
            show_status
            ;;
        "test")
            if [[ $# -lt 2 ]]; then
                log_error "Usage: $0 test <project_name>"
                exit 1
            fi
            test_project_setup "$2"
            ;;
        "help"|*)
            echo "ATLAS MCP Multi-Project Deployment Script"
            echo ""
            echo "Usage: $0 <command> [options]"
            echo ""
            echo "Commands:"
            echo "  setup                           - Complete multi-project setup"
            echo "  add-project <name> <path> [type] - Add single project"
            echo "  cleanup                         - Clean up old containers"
            echo "  status                          - Show deployment status"
            echo "  test <project_name>            - Test project setup"
            echo "  help                           - Show this help"
            echo ""
            echo "Container Types:"
            echo "  fast  - Fast startup with async ML loading (default)"
            echo "  full  - Full startup with all features"
            echo ""
            echo "Examples:"
            echo "  $0 setup"
            echo "  $0 add-project panther /path/to/panther-project fast"
            echo "  $0 test panther"
            echo "  $0 status"
            ;;
    esac
}

# Run main function with all arguments
main "$@"