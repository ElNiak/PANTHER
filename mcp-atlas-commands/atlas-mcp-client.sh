#!/bin/bash

# ATLAS MCP Client - JSON-RPC Communication with Docker Container
# Handles multi-project support, hierarchical caching, and environment variable management

set -e

# Configuration
CONTAINER_NAME="atlas-commands-mcp"
DEFAULT_PROJECT="Software-Engineer-AI-Agent-Atlas"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Help function
show_help() {
    cat << EOF
ATLAS MCP Client - JSON-RPC Communication Tool

Usage: $0 [OPTIONS] COMMAND [ARGS...]

OPTIONS:
    -p, --project NAME      Set project name (default: ${DEFAULT_PROJECT})
    -e, --env FILE          Load additional environment variables from file
    -d, --debug             Enable debug mode
    -h, --help              Show this help message
    --start                 Start the container if not running
    --stop                  Stop the container
    --restart               Restart the container
    --logs                  Show container logs

COMMANDS:
    call TOOL_NAME PARAMS   Call MCP tool with JSON parameters
    list-tools              List available MCP tools
    test                    Test connection with server
    interactive             Start interactive mode

EXAMPLES:
    # List all available tools
    $0 list-tools

    # Create a task
    $0 call create_task_metadata '{
        "project_name": "PANTHER", 
        "task_name": "network-discovery",
        "domain": "networking"
    }'

    # Test connection
    $0 test

    # Interactive mode for multiple commands
    $0 interactive

EOF
}

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" >&2
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Environment setup
setup_environment() {
    local project_name="${1:-$DEFAULT_PROJECT}"
    local env_file="${2:-}"
    
    # Core environment variables for hierarchical cache and multi-project support
    export PROJECT_NAME="$project_name"
    export ATLAS_PROJECT_ID="$project_name"
    export ATLAS_STORAGE_PATH="/app/REPOS"
    export ATLAS_STARTUP_MODE="fast"
    export ATLAS_LAZY_LOADING="true"
    export ATLAS_TOKEN_MODE="auto"
    export ATLAS_COMPRESSION_STRATEGY="adaptive"
    export ATLAS_COMPRESSION_MIN_SIZE="500"
    export ATLAS_COMPRESSION_ENABLE_LEARNING="true"
    export ATLAS_COMPRESSION_DEFAULT_QUALITY="0.85"
    export ATLAS_CACHE_MODE="hierarchical"
    export ATLAS_WORKSPACE_ISOLATION="true"
    export PYTHONUNBUFFERED="1"
    export LOG_LEVEL="${LOG_LEVEL:-INFO}"
    
    # Load additional environment variables if specified
    if [[ -n "$env_file" && -f "$env_file" ]]; then
        log_info "Loading environment from $env_file"
        source "$env_file"
    fi
    
    # Ensure required directories exist
    mkdir -p "${SCRIPT_DIR}/REPOS"
    mkdir -p "${HOME}/.atlas/global/models"
    mkdir -p "${HOME}/.atlas/projects"
    
    log_info "Environment configured for project: $project_name"
}

# Docker management functions
ensure_container_running() {
    if ! docker ps -q --filter "name=${CONTAINER_NAME}" | grep -q .; then
        log_info "Starting ATLAS MCP container..."
        
        # Stop any existing container with the same name
        docker stop "${CONTAINER_NAME}" 2>/dev/null || true
        docker rm "${CONTAINER_NAME}" 2>/dev/null || true
        
        # Start new container with proper environment
        docker run -d \
            --name "${CONTAINER_NAME}" \
            --restart unless-stopped \
            -e "PROJECT_NAME=${PROJECT_NAME}" \
            -e "ATLAS_PROJECT_ID=${ATLAS_PROJECT_ID}" \
            -e "ATLAS_STORAGE_PATH=${ATLAS_STORAGE_PATH}" \
            -e "ATLAS_STARTUP_MODE=${ATLAS_STARTUP_MODE}" \
            -e "ATLAS_LAZY_LOADING=${ATLAS_LAZY_LOADING}" \
            -e "ATLAS_TOKEN_MODE=${ATLAS_TOKEN_MODE}" \
            -e "ATLAS_COMPRESSION_STRATEGY=${ATLAS_COMPRESSION_STRATEGY}" \
            -e "ATLAS_COMPRESSION_MIN_SIZE=${ATLAS_COMPRESSION_MIN_SIZE}" \
            -e "ATLAS_COMPRESSION_ENABLE_LEARNING=${ATLAS_COMPRESSION_ENABLE_LEARNING}" \
            -e "ATLAS_COMPRESSION_DEFAULT_QUALITY=${ATLAS_COMPRESSION_DEFAULT_QUALITY}" \
            -e "ATLAS_CACHE_MODE=${ATLAS_CACHE_MODE}" \
            -e "ATLAS_WORKSPACE_ISOLATION=${ATLAS_WORKSPACE_ISOLATION}" \
            -e "PYTHONUNBUFFERED=${PYTHONUNBUFFERED}" \
            -e "LOG_LEVEL=${LOG_LEVEL}" \
            -v "${SCRIPT_DIR}/REPOS:/app/REPOS" \
            -v "${SCRIPT_DIR}:/app/workspace" \
            -v "/tmp/atlas-memory-control:/app/memory-control" \
            -v "${HOME}/.atlas/global:/app/.atlas/global:ro" \
            -v "${HOME}/.atlas/projects:/app/.atlas/projects:rw" \
            -v "${HOME}/.atlas/global/models:/root/.cache/huggingface:ro" \
            atlas-commands-mcp:latest
        
        # Wait for container to be ready
        log_info "Waiting for container to be ready..."
        sleep 3
        
        # Verify container is running
        if docker ps -q --filter "name=${CONTAINER_NAME}" | grep -q .; then
            log_success "Container started successfully"
        else
            log_error "Failed to start container"
            docker logs "${CONTAINER_NAME}" 2>&1 | tail -20
            exit 1
        fi
    else
        log_info "Container already running"
    fi
}

stop_container() {
    if docker ps -q --filter "name=${CONTAINER_NAME}" | grep -q .; then
        log_info "Stopping ATLAS MCP container..."
        docker stop "${CONTAINER_NAME}"
        docker rm "${CONTAINER_NAME}"
        log_success "Container stopped"
    else
        log_warning "Container not running"
    fi
}

restart_container() {
    stop_container
    ensure_container_running
}

show_logs() {
    if docker ps -aq --filter "name=${CONTAINER_NAME}" | grep -q .; then
        docker logs -f "${CONTAINER_NAME}"
    else
        log_error "Container not found"
        exit 1
    fi
}

# JSON-RPC communication functions
generate_request_id() {
    echo $((RANDOM * RANDOM))
}

format_json_rpc_request() {
    local method="$1"
    local params="$2"
    local request_id
    request_id=$(generate_request_id)
    
    if [[ -z "$params" || "$params" == "{}" || "$params" == "null" ]]; then
        params="{}"
    fi
    
    cat << EOF
{
    "jsonrpc": "2.0",
    "id": ${request_id},
    "method": "tools/call",
    "params": {
        "name": "${method}",
        "arguments": ${params}
    }
}
EOF
}

# MCP Session Management
MCP_SESSION_FILE="/tmp/atlas-mcp-session-$$"

# MCP communication using background process and timeout
send_mcp_request_simple() {
    local json_request="$1"
    local temp_request="/tmp/atlas-mcp-request-$$"
    local temp_output="/tmp/atlas-mcp-output-$$"
    local temp_fifo="/tmp/atlas-mcp-fifo-$$"
    
    if [[ "$DEBUG" == "true" ]]; then
        log_info "Sending request:"
        echo "$json_request" | jq '.' 2>/dev/null || echo "$json_request"
    fi
    
    # Create FIFO for communication
    mkfifo "$temp_fifo" 2>/dev/null || true
    
    # Create complete MCP session with initialization
    {
        echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "atlas-client", "version": "1.0.0"}}}'
        echo '{"jsonrpc": "2.0", "method": "notifications/initialized"}'
        echo "$json_request"
    } > "$temp_request"
    
    # Start MCP server in background and capture output
    (
        cat "$temp_request" | docker exec -i "${CONTAINER_NAME}" python -m atlas_commands.server 2>/dev/null > "$temp_output" &
        local docker_pid=$!
        
        # Wait for output or timeout
        sleep 10
        kill $docker_pid 2>/dev/null || true
        wait $docker_pid 2>/dev/null || true
    ) &
    local bg_pid=$!
    
    # Wait for background process with timeout
    timeout 15s wait $bg_pid 2>/dev/null || kill $bg_pid 2>/dev/null
    
    # Read captured output
    local all_output=""
    if [[ -f "$temp_output" ]]; then
        all_output=$(cat "$temp_output")
    fi
    
    if [[ "$DEBUG" == "true" ]]; then
        log_info "Raw output length: ${#all_output}"
        log_info "Raw output (first 1000 chars):"
        echo "$all_output" | head -c 1000
        if [[ ${#all_output} -gt 1000 ]]; then
            echo "... [truncated]"
        fi
    fi
    
    # Extract the request ID to find the matching response
    local request_id
    request_id=$(echo "$json_request" | jq -r '.id // 2' 2>/dev/null)
    
    # Look for JSON response lines containing our request ID and result
    local response
    response=$(echo "$all_output" | jq -c 'select(.id == '$request_id' and .result != null)' 2>/dev/null | tail -1)
    
    # If jq parsing fails, fall back to grep
    if [[ -z "$response" ]]; then
        response=$(echo "$all_output" | grep -E '^\{.*"id":'$request_id'.*"result".*\}' | tail -1)
    fi
    
    # If still not found, try looking for any response with result (for cases where ID doesn't match)
    if [[ -z "$response" ]]; then
        response=$(echo "$all_output" | jq -c 'select(.result != null)' 2>/dev/null | tail -1)
    fi
    
    if [[ "$DEBUG" == "true" ]]; then
        log_info "Request ID: $request_id"
        log_info "Filtered response:"
        echo "$response" | jq '.' 2>/dev/null || echo "$response"
    fi
    
    # Cleanup
    rm -f "$temp_request" "$temp_output" "$temp_fifo" 2>/dev/null
    
    echo "$response"
}

# Use the simple approach as the main function
send_mcp_request() {
    send_mcp_request_simple "$1"
}

# Cleanup MCP session
cleanup_mcp_session() {
    if [[ -f "${MCP_SESSION_FILE}.pid" ]]; then
        local mcp_pid
        mcp_pid=$(cat "${MCP_SESSION_FILE}.pid" 2>/dev/null)
        if [[ -n "$mcp_pid" ]]; then
            kill "$mcp_pid" 2>/dev/null || true
        fi
    fi
    
    # Create stop signal
    touch "${MCP_SESSION_FILE}.stop"
    
    # Clean up files
    rm -f "${MCP_SESSION_FILE}".* 2>/dev/null || true
}

# Trap to cleanup on exit
trap cleanup_mcp_session EXIT

# MCP command functions
call_tool() {
    local tool_name="$1"
    local params="$2"
    
    if [[ -z "$tool_name" ]]; then
        log_error "Tool name is required"
        exit 1
    fi
    
    local request
    request=$(format_json_rpc_request "$tool_name" "$params")
    
    local response
    response=$(send_mcp_request "$request")
    
    # Parse and display response
    if echo "$response" | jq -e '.result' >/dev/null 2>&1; then
        echo "$response" | jq -r '.result.content[0].text // .result'
        log_success "Tool call completed successfully"
    elif echo "$response" | jq -e '.error' >/dev/null 2>&1; then
        log_error "Tool call failed:"
        echo "$response" | jq -r '.error.message // .error'
        exit 1
    else
        log_warning "Unexpected response format:"
        echo "$response"
    fi
}

list_tools() {
    local request
    request='{"jsonrpc": "2.0", "id": 2, "method": "tools/list"}'
    
    local response
    response=$(send_mcp_request "$request")
    
    if echo "$response" | jq -e '.result.tools' >/dev/null 2>&1; then
        log_success "Available tools:"
        echo "$response" | jq -r '.result.tools[] | "- \(.name): \(.description)"'
    else
        log_error "Failed to list tools"
        echo "$response"
        exit 1
    fi
}

test_connection() {
    log_info "Testing connection to ATLAS MCP server..."
    
    local request
    request='{"jsonrpc": "2.0", "id": 2, "method": "tools/list"}'
    
    local response
    response=$(send_mcp_request "$request")
    
    if echo "$response" | jq -e '.result' >/dev/null 2>&1; then
        local tool_count
        tool_count=$(echo "$response" | jq -r '.result.tools | length')
        log_success "Connection successful! $tool_count tools available."
        return 0
    else
        log_error "Connection failed"
        echo "$response"
        return 1
    fi
}

interactive_mode() {
    log_info "Starting interactive mode. Type 'help' for commands, 'exit' to quit."
    
    while true; do
        printf "\n${BLUE}atlas-mcp>${NC} "
        read -r input
        
        case "$input" in
            "exit"|"quit"|"q")
                log_info "Goodbye!"
                break
                ;;
            "help"|"h")
                cat << EOF
Interactive Mode Commands:
  list                    - List available tools
  call TOOL PARAMS        - Call a tool with JSON parameters
  test                    - Test connection
  logs                    - Show container logs
  restart                 - Restart container
  help, h                 - Show this help
  exit, quit, q           - Exit interactive mode

Examples:
  call create_task_metadata '{"project_name": "TEST", "task_name": "example"}'
  call list_project_tasks '{"project_name": "TEST"}'
EOF
                ;;
            "list")
                list_tools
                ;;
            "test")
                test_connection
                ;;
            "logs")
                show_logs &
                ;;
            "restart")
                restart_container
                ;;
            call*)
                # Parse call command
                if [[ $input =~ ^call[[:space:]]+([^[:space:]]+)[[:space:]]*(.*)$ ]]; then
                    local tool_name="${BASH_REMATCH[1]}"
                    local params="${BASH_REMATCH[2]:-"{}"}"
                    call_tool "$tool_name" "$params"
                else
                    log_error "Invalid call syntax. Use: call TOOL_NAME PARAMS"
                fi
                ;;
            "")
                # Empty input, continue
                ;;
            *)
                log_warning "Unknown command: $input. Type 'help' for available commands."
                ;;
        esac
    done
}

# Main script
main() {
    local project_name="$DEFAULT_PROJECT"
    local env_file=""
    local command=""
    local debug=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -p|--project)
                project_name="$2"
                shift 2
                ;;
            -e|--env)
                env_file="$2"
                shift 2
                ;;
            -d|--debug)
                debug=true
                export DEBUG="true"
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            --start)
                command="start"
                shift
                ;;
            --stop)
                command="stop"
                shift
                ;;
            --restart)
                command="restart"
                shift
                ;;
            --logs)
                command="logs"
                shift
                ;;
            *)
                command="$1"
                shift
                break
                ;;
        esac
    done
    
    # Setup environment
    setup_environment "$project_name" "$env_file"
    
    # Handle container management commands
    case "$command" in
        "start")
            ensure_container_running
            exit 0
            ;;
        "stop")
            stop_container
            exit 0
            ;;
        "restart")
            restart_container
            exit 0
            ;;
        "logs")
            show_logs
            exit 0
            ;;
    esac
    
    # Ensure container is running for MCP commands
    ensure_container_running
    
    # Handle MCP commands
    case "$command" in
        "call")
            if [[ $# -lt 1 ]]; then
                log_error "Tool name is required for call command"
                exit 1
            fi
            local tool_name="$1"
            local params="${2:-"{}"}"
            call_tool "$tool_name" "$params"
            ;;
        "list-tools")
            list_tools
            ;;
        "test")
            test_connection
            ;;
        "interactive")
            interactive_mode
            ;;
        "")
            log_warning "No command specified. Use --help for usage information."
            interactive_mode
            ;;
        *)
            log_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Check dependencies
check_dependencies() {
    local missing_deps=()
    
    if ! command -v docker &> /dev/null; then
        missing_deps+=("docker")
    fi
    
    if ! command -v jq &> /dev/null; then
        log_warning "jq not found - JSON output may not be formatted"
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        exit 1
    fi
}

# Run main function with dependency check
check_dependencies
main "$@"