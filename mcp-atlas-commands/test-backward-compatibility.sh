#!/bin/bash
#
# ATLAS MCP Backward Compatibility Test Suite
# 
# This script tests that existing single-project setups continue working
# unchanged after implementing multi-project support.
#
# Usage: ./test-backward-compatibility.sh

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_test() { echo -e "${BLUE}[TEST]${NC} $1"; }

# Test results
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Test tracking
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    TESTS_RUN=$((TESTS_RUN + 1))
    log_test "Running: $test_name"
    
    if eval "$test_command"; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        log_info "✅ PASSED: $test_name"
        return 0
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        log_error "❌ FAILED: $test_name"
        return 1
    fi
}

# Setup test environment
setup_test_environment() {
    log_info "Setting up test environment..."
    
    # Create temporary test directory
    export TEST_DIR="/tmp/atlas-compat-test-$$"
    mkdir -p "$TEST_DIR"
    cd "$TEST_DIR"
    
    # Create test project structure
    mkdir -p test-project/{src,docs,tests}
    echo '{"name": "test-project"}' > test-project/package.json
    echo "# Test Project" > test-project/README.md
    
    log_info "✓ Test environment created: $TEST_DIR"
}

# Test 1: Original single-project setup without any project environment variables
test_original_single_project() {
    log_test "Testing original single-project setup..."
    
    # Test without any project-specific environment variables
    docker run --rm \
        -v "$TEST_DIR/test-project:/app/REPOS" \
        atlas-commands-mcp:fast \
        python -c "
import os
import sys

# Verify no project environment variables are set
project_vars = [
    'ATLAS_PROJECT_ID',
    'ATLAS_WORKSPACE_ISOLATION', 
    'ATLAS_PROJECT_ROOT'
]

for var in project_vars:
    if os.environ.get(var):
        print(f'FAIL: Environment variable {var} is set: {os.environ[var]}')
        sys.exit(1)

# Test original functionality
try:
    from atlas_commands.storage.task_storage_manager import TaskStorageManager
    
    # Initialize with original path
    manager = TaskStorageManager('/app/REPOS')
    print('✓ TaskStorageManager initialized with original path')
    
    # Test task creation with original API
    task_id = manager.create_task_metadata(
        project_name='default',
        task_id='test-compatibility',
        task_type='compatibility_test',
        description='Testing backward compatibility'
    )
    print(f'✓ Task created: {task_id}')
    
    # Verify task was created in expected location
    import json
    import glob
    
    task_files = glob.glob('/app/REPOS/**/task.json', recursive=True)
    if not task_files:
        print('FAIL: No task files found')
        sys.exit(1)
    
    print(f'✓ Task file created: {task_files[0]}')
    
    # Test memory manager
    from atlas_commands.memory.graph_manager import MemoryGraphManager
    memory_manager = MemoryGraphManager()
    print('✓ MemoryGraphManager initialized')
    
    print('SUCCESS: Original single-project setup working')
    
except Exception as e:
    print(f'FAIL: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
" >/dev/null 2>&1
}

# Test 2: Project context defaults to single-project mode
test_project_context_defaults() {
    log_test "Testing project context defaults..."
    
    docker run --rm \
        -v "$TEST_DIR/test-project:/app/workspace" \
        atlas-commands-mcp:fast \
        python -c "
import sys

try:
    from atlas_commands.project.context_manager import get_project_context_manager
    
    # Get project context without setting environment variables
    context = get_project_context_manager()
    
    # Verify defaults for backward compatibility
    if context.project_id != 'default':
        print(f'FAIL: Expected project_id=default, got {context.project_id}')
        sys.exit(1)
    
    if context.workspace_isolation != False:
        print(f'FAIL: Expected workspace_isolation=False, got {context.workspace_isolation}')
        sys.exit(1)
    
    print(f'✓ Project ID defaults to: {context.project_id}')
    print(f'✓ Workspace isolation defaults to: {context.workspace_isolation}')
    print('SUCCESS: Project context defaults correctly')
    
except Exception as e:
    print(f'FAIL: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
" >/dev/null 2>&1
}

# Test 3: Task IDs remain unscoped in single-project mode
test_task_id_compatibility() {
    log_test "Testing task ID backward compatibility..."
    
    docker run --rm \
        -v "$TEST_DIR/test-project:/app/workspace" \
        -v "$TEST_DIR/cache:/app/cache" \
        atlas-commands-mcp:fast \
        python -c "
import sys

try:
    from atlas_commands.project.context_manager import get_project_context_manager
    from atlas_commands.project.decorators import ProjectAwareTaskManager
    
    # Test in single-project mode (no environment variables)
    context = get_project_context_manager()
    task_manager = ProjectAwareTaskManager(context)
    
    # Create task - should not be scoped in single-project mode
    original_task_id = 'simple-task-id'
    scoped_task_id = context.scope_task_id(original_task_id)
    
    # In single-project mode, task ID should remain unchanged
    if scoped_task_id != original_task_id:
        print(f'FAIL: Task ID was scoped in single-project mode: {original_task_id} -> {scoped_task_id}')
        sys.exit(1)
    
    print(f'✓ Task ID preserved in single-project mode: {scoped_task_id}')
    
    # Test task validation - should accept all tasks in single-project mode
    if not context.validate_task_belongs_to_project('any-task-id'):
        print('FAIL: Task validation rejected task in single-project mode')
        sys.exit(1)
    
    print('✓ Task validation accepts all tasks in single-project mode')
    print('SUCCESS: Task ID compatibility maintained')
    
except Exception as e:
    print(f'FAIL: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
" >/dev/null 2>&1
}

# Test 4: File path validation disabled in single-project mode
test_file_path_compatibility() {
    log_test "Testing file path backward compatibility..."
    
    docker run --rm \
        -v "$TEST_DIR/test-project:/app/workspace" \
        atlas-commands-mcp:fast \
        python -c "
import sys

try:
    from atlas_commands.project.context_manager import get_project_context_manager
    
    context = get_project_context_manager()
    
    # Test file access validation - should be disabled in single-project mode
    test_paths = [
        '/app/workspace/src/main.py',
        '/tmp/some-file.txt',
        '/etc/passwd',
        '../outside-project/file.txt'
    ]
    
    for path in test_paths:
        if not context.validate_file_access(path):
            print(f'FAIL: File access validation rejected path in single-project mode: {path}')
            sys.exit(1)
    
    print('✓ File access validation disabled in single-project mode')
    print('SUCCESS: File path compatibility maintained')
    
except Exception as e:
    print(f'FAIL: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
" >/dev/null 2>&1
}

# Test 5: Memory entity scoping disabled in single-project mode
test_memory_compatibility() {
    log_test "Testing memory backward compatibility..."
    
    docker run --rm \
        -v "$TEST_DIR/test-project:/app/workspace" \
        -v "$TEST_DIR/cache:/app/cache" \
        atlas-commands-mcp:fast \
        python -c "
import sys

try:
    from atlas_commands.project.context_manager import get_project_context_manager
    from atlas_commands.project.decorators import ProjectAwareMemoryManager
    
    context = get_project_context_manager()
    memory_manager = ProjectAwareMemoryManager(context)
    
    # Test entity ID scoping - should be disabled in single-project mode
    original_entity_name = 'test-entity'
    scoped_entity_name = context.scope_entity_id(original_entity_name)
    
    if scoped_entity_name != original_entity_name:
        print(f'FAIL: Entity ID was scoped in single-project mode: {original_entity_name} -> {scoped_entity_name}')
        sys.exit(1)
    
    print(f'✓ Entity ID preserved in single-project mode: {scoped_entity_name}')
    
    # Test entity validation - should accept all entities in single-project mode
    if not context.validate_entity_belongs_to_project('any-entity-id'):
        print('FAIL: Entity validation rejected entity in single-project mode')
        sys.exit(1)
    
    print('✓ Entity validation accepts all entities in single-project mode')
    print('SUCCESS: Memory compatibility maintained')
    
except Exception as e:
    print(f'FAIL: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
" >/dev/null 2>&1
}

# Test 6: Server integration doesn't break existing functionality
test_server_integration() {
    log_test "Testing server integration compatibility..."
    
    docker run --rm \
        -v "$TEST_DIR/test-project:/app/REPOS" \
        atlas-commands-mcp:fast \
        python -c "
import sys
import asyncio
import os

# Set up environment for server testing
os.environ['ATLAS_STORAGE_PATH'] = '/app/REPOS'

try:
    # Test server imports and initialization
    from atlas_commands.server import EnhancedAtlasCommandsServer
    
    # Initialize server (should work without project context)
    server = EnhancedAtlasCommandsServer()
    print('✓ Server initialized successfully')
    
    # Test that storage manager is properly initialized
    if not hasattr(server, 'storage_manager'):
        print('FAIL: Server missing storage_manager')
        sys.exit(1)
    
    print('✓ Storage manager available')
    
    # Test that project context integration doesn't break server
    if hasattr(server, 'project_context_enabled'):
        print(f'✓ Project context integration available: {server.project_context_enabled}')
    else:
        print('✓ Running without project context (expected in compatibility mode)')
    
    print('SUCCESS: Server integration compatible')
    
except Exception as e:
    print(f'FAIL: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
" >/dev/null 2>&1
}

# Test 7: Container startup time hasn't degraded
test_startup_performance() {
    log_test "Testing startup performance..."
    
    # Measure startup time
    start_time=$(date +%s%3N)
    
    docker run --rm \
        -v "$TEST_DIR/test-project:/app/REPOS" \
        atlas-commands-mcp:fast \
        python -c "
from atlas_commands.server import EnhancedAtlasCommandsServer
server = EnhancedAtlasCommandsServer()
print('Server ready')
" >/dev/null 2>&1
    
    end_time=$(date +%s%3N)
    startup_time=$((end_time - start_time))
    
    # Startup should be under 10 seconds for fast mode
    if [ $startup_time -gt 10000 ]; then
        log_error "Startup time too slow: ${startup_time}ms"
        return 1
    fi
    
    log_info "✓ Startup time: ${startup_time}ms (acceptable)"
    return 0
}

# Test 8: Original MCP tool handlers work unchanged
test_mcp_handlers() {
    log_test "Testing MCP handlers compatibility..."
    
    docker run --rm \
        -v "$TEST_DIR/test-project:/app/REPOS" \
        atlas-commands-mcp:fast \
        python -c "
import sys

try:
    from atlas_commands.server import EnhancedAtlasCommandsServer
    
    server = EnhancedAtlasCommandsServer()
    
    # Test that tool registry is available
    if not hasattr(server, '_tool_registry'):
        print('FAIL: Server missing tool registry')
        sys.exit(1)
    
    print('✓ Tool registry available')
    
    # Test tool registration
    registry = server._tool_registry
    categories = registry.get_categories()
    
    expected_categories = [
        'task_management',
        'hierarchical_management', 
        'memory_management',
        'validation'
    ]
    
    for category in expected_categories:
        if category not in categories:
            print(f'FAIL: Missing tool category: {category}')
            sys.exit(1)
    
    print(f'✓ Tool categories available: {len(categories)}')
    
    # Test tool handler retrieval
    task_handler = registry.get_handler('task_management')
    if not task_handler:
        print('FAIL: Task management handler not available')
        sys.exit(1)
    
    print('✓ Task management handler available')
    print('SUCCESS: MCP handlers working')
    
except Exception as e:
    print(f'FAIL: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
" >/dev/null 2>&1
}

# Test 9: Project features only activate when explicitly enabled
test_project_feature_activation() {
    log_test "Testing project feature activation..."
    
    # Test 1: No project features when environment variables not set
    docker run --rm \
        -v "$TEST_DIR/test-project:/app/workspace" \
        atlas-commands-mcp:fast \
        python -c "
import sys
import os

# Ensure no project environment variables
for var in ['ATLAS_PROJECT_ID', 'ATLAS_WORKSPACE_ISOLATION', 'ATLAS_PROJECT_ROOT']:
    if os.environ.get(var):
        print(f'FAIL: Environment variable {var} should not be set')
        sys.exit(1)

try:
    from atlas_commands.project.server_patch import patch_server_for_project_context
    from atlas_commands.server import EnhancedAtlasCommandsServer
    
    server = EnhancedAtlasCommandsServer()
    
    # Project context should not be enabled
    project_enabled = patch_server_for_project_context(server)
    if project_enabled:
        print('FAIL: Project context enabled without environment variables')
        sys.exit(1)
    
    print('✓ Project context correctly disabled without environment variables')
    
except Exception as e:
    print(f'FAIL: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
" >/dev/null 2>&1
    
    if [ $? -ne 0 ]; then
        return 1
    fi
    
    # Test 2: Project features activate when environment variables are set
    docker run --rm \
        -v "$TEST_DIR/test-project:/app/workspace" \
        -v "$TEST_DIR/cache:/app/cache" \
        -e "ATLAS_PROJECT_ID=test-project" \
        -e "ATLAS_WORKSPACE_ISOLATION=true" \
        atlas-commands-mcp:fast \
        python -c "
import sys

try:
    from atlas_commands.project.server_patch import patch_server_for_project_context
    from atlas_commands.server import EnhancedAtlasCommandsServer
    
    server = EnhancedAtlasCommandsServer()
    
    # Project context should be enabled
    project_enabled = patch_server_for_project_context(server)
    if not project_enabled:
        print('FAIL: Project context not enabled with environment variables')
        sys.exit(1)
    
    print('✓ Project context correctly enabled with environment variables')
    
    # Verify project context details
    if not hasattr(server, 'project_context'):
        print('FAIL: Server missing project context')
        sys.exit(1)
    
    context = server.project_context
    if context.project_id != 'test-project':
        print(f'FAIL: Wrong project ID: {context.project_id}')
        sys.exit(1)
    
    if not context.workspace_isolation:
        print('FAIL: Workspace isolation not enabled')
        sys.exit(1)
    
    print('✓ Project context configured correctly')
    
except Exception as e:
    print(f'FAIL: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
" >/dev/null 2>&1
}

# Cleanup test environment
cleanup_test_environment() {
    log_info "Cleaning up test environment..."
    
    if [ -n "$TEST_DIR" ] && [ -d "$TEST_DIR" ]; then
        rm -rf "$TEST_DIR"
        log_info "✓ Test directory removed: $TEST_DIR"
    fi
}

# Main test runner
main() {
    log_info "🧪 ATLAS MCP Backward Compatibility Test Suite"
    log_info "=============================================="
    
    # Check prerequisites
    if ! command -v docker &> /dev/null; then
        log_error "Docker not found. Please install Docker."
        exit 1
    fi
    
    if ! docker images | grep -q "atlas-commands-mcp.*fast"; then
        log_error "ATLAS MCP container not found. Please build atlas-commands-mcp:fast"
        exit 1
    fi
    
    # Setup test environment
    setup_test_environment
    
    # Run tests
    run_test "Original single-project setup" "test_original_single_project"
    run_test "Project context defaults" "test_project_context_defaults"
    run_test "Task ID compatibility" "test_task_id_compatibility"
    run_test "File path compatibility" "test_file_path_compatibility"
    run_test "Memory compatibility" "test_memory_compatibility"
    run_test "Server integration" "test_server_integration"
    run_test "Startup performance" "test_startup_performance"
    run_test "MCP handlers" "test_mcp_handlers"
    run_test "Project feature activation" "test_project_feature_activation"
    
    # Cleanup
    cleanup_test_environment
    
    # Report results
    log_info "=============================================="
    log_info "📊 Test Results:"
    log_info "   Tests run: $TESTS_RUN"
    log_info "   Passed: $TESTS_PASSED"
    log_info "   Failed: $TESTS_FAILED"
    
    if [ $TESTS_FAILED -eq 0 ]; then
        log_info "✅ All backward compatibility tests PASSED!"
        log_info "   Existing single-project setups will continue working unchanged."
        exit 0
    else
        log_error "❌ $TESTS_FAILED tests FAILED!"
        log_error "   Backward compatibility may be broken."
        exit 1
    fi
}

# Run tests
main "$@"