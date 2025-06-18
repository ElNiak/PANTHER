#!/bin/bash
# scripts/dev-test-runner.sh
# Optimized test runner for development workflow

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
FAST_TESTS_TIMEOUT=60
INTEGRATION_TESTS_TIMEOUT=300
DEFAULT_MARKERS="not (slow or requires_docker or requires_network)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_environment() {
    log_info "Checking environment..."
    
    # Check if we're in project root
    if [[ ! -f "pyproject.toml" ]]; then
        log_error "Not in PANTHER project root directory"
        exit 1
    fi
    
    # Check virtual environment
    if [[ -f ".venv/bin/activate" ]]; then
        source .venv/bin/activate
        log_info "Activated virtual environment"
    else
        log_warning "Virtual environment not found at .venv/"
    fi
    
    # Check if PANTHER is installed
    if ! python -c "import panther" 2>/dev/null; then
        log_warning "PANTHER not installed. Installing in development mode..."
        pip install -e .
    fi
}

run_fast_tests() {
    log_info "Running fast unit tests..."
    timeout $FAST_TESTS_TIMEOUT pytest tests/unit/ \
        -m "$DEFAULT_MARKERS" \
        --tb=short \
        -q \
        -p no:panther_metrics || {
        log_error "Fast tests failed or timed out"
        return 1
    }
    log_success "Fast tests completed successfully"
}

run_integration_tests() {
    log_info "Running integration tests..."
    
    # Check if Docker is available for integration tests
    if command -v docker &> /dev/null && docker info &> /dev/null; then
        log_info "Docker available - running full integration tests"
        timeout $INTEGRATION_TESTS_TIMEOUT pytest tests/integration/ \
            -m "not requires_network" \
            --tb=short \
            -v \
            -p no:panther_metrics || {
            log_error "Integration tests failed or timed out"
            return 1
        }
    else
        log_warning "Docker not available - running basic integration tests only"
        timeout $INTEGRATION_TESTS_TIMEOUT pytest tests/integration/ \
            -m "not (requires_docker or requires_network)" \
            --tb=short \
            -v \
            -p no:panther_metrics || {
            log_error "Integration tests failed or timed out"
            return 1
        }
    fi
    log_success "Integration tests completed successfully"
}

run_property_tests() {
    log_info "Running property-based tests..."
    pytest tests/property_based/ \
        --hypothesis-profile=dev \
        --tb=short \
        -v \
        -p no:panther_metrics || {
        log_error "Property-based tests failed"
        return 1
    }
    log_success "Property-based tests completed successfully"
}

run_specific_test() {
    local test_path="$1"
    log_info "Running specific test: $test_path"
    
    if [[ ! -f "$test_path" ]]; then
        log_error "Test file not found: $test_path"
        return 1
    fi
    
    pytest "$test_path" \
        --tb=short \
        -v \
        -p no:panther_metrics || {
        log_error "Test failed: $test_path"
        return 1
    }
    log_success "Test completed successfully: $test_path"
}

run_quality_check() {
    log_info "Running quality checks..."
    
    # Install quality tools if not available
    pip install black isort flake8 > /dev/null 2>&1 || true
    
    # Code formatting
    log_info "Checking code formatting..."
    if black --check tests/ panther/ &> /dev/null; then
        log_success "Code formatting OK"
    else
        log_warning "Code formatting issues found. Run: black tests/ panther/"
    fi
    
    # Import sorting
    log_info "Checking import sorting..."
    if isort --check-only tests/ panther/ &> /dev/null; then
        log_success "Import sorting OK"
    else
        log_warning "Import sorting issues found. Run: isort tests/ panther/"
    fi
    
    # Linting
    log_info "Running linting..."
    if flake8 tests/ panther/ --max-line-length=88 --exclude=tests/tests_ressources/ &> /dev/null; then
        log_success "Linting OK"
    else
        log_warning "Linting issues found. Run: flake8 tests/ panther/ --max-line-length=88"
    fi
    
    # Static analysis with Codacy (if available)
    if command -v codacy-analysis-cli &> /dev/null; then
        log_info "Running Codacy analysis..."
        codacy-analysis-cli analyze --directory tests/ --format json > /tmp/codacy-results.json 2>/dev/null || {
            log_warning "Codacy analysis failed or skipped"
        }
        
        if [[ -f "/tmp/codacy-results.json" ]] && [[ -f "scripts/validate_quality_gates.py" ]]; then
            python scripts/validate_quality_gates.py /tmp/codacy-results.json || {
                log_error "Quality gates failed"
                return 1
            }
        fi
    else
        log_warning "Codacy CLI not found - skipping static analysis"
    fi
    
    log_success "Quality checks completed"
}

run_coverage() {
    log_info "Running test coverage analysis..."
    
    pip install pytest-cov > /dev/null 2>&1 || true
    
    pytest tests/unit/ \
        --cov=panther \
        --cov-report=html \
        --cov-report=term \
        -m "$DEFAULT_MARKERS" \
        -p no:panther_metrics || {
        log_error "Coverage analysis failed"
        return 1
    }
    
    log_success "Coverage analysis completed - see htmlcov/index.html"
}

show_test_status() {
    log_info "Test suite status:"
    echo ""
    
    # Count test files
    local unit_tests=$(find tests/unit -name "test_*.py" | wc -l)
    local integration_tests=$(find tests/integration -name "test_*.py" 2>/dev/null | wc -l || echo "0")
    local property_tests=$(find tests/property_based -name "test_*.py" 2>/dev/null | wc -l || echo "0")
    
    echo "📊 Test Files:"
    echo "   Unit tests: $unit_tests"
    echo "   Integration tests: $integration_tests"
    echo "   Property-based tests: $property_tests"
    echo ""
    
    # Recent test results (if available)
    if [[ -f ".pytest_cache/README.md" ]]; then
        echo "📈 Recent test cache found"
    fi
    
    # Check for common issues
    local broken_imports=$(find tests/ -name "*.py" -exec python -m py_compile {} \; 2>&1 | wc -l)
    if [[ $broken_imports -gt 0 ]]; then
        echo "⚠️  Syntax/import issues detected"
    else
        echo "✅ No syntax/import issues detected"
    fi
}

show_usage() {
    echo "PANTHER Development Test Runner"
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  fast              Run fast unit tests only (default)"
    echo "  integration       Run integration tests"
    echo "  property          Run property-based tests"
    echo "  all               Run all test categories"
    echo "  quality           Run quality checks (linting, formatting)"
    echo "  coverage          Run unit tests with coverage analysis"
    echo "  pre-commit        Run pre-commit validation (fast + quality)"
    echo "  status            Show test suite status"
    echo "  test <file>       Run specific test file"
    echo ""
    echo "Options:"
    echo "  -h, --help        Show this help message"
    echo "  -v, --verbose     Enable verbose output"
    echo "  -q, --quiet       Quiet mode"
    echo ""
    echo "Examples:"
    echo "  $0 fast                                    # Quick development feedback"
    echo "  $0 all                                     # Full test suite"
    echo "  $0 quality                                 # Code quality validation"
    echo "  $0 pre-commit                              # Pre-commit checks"
    echo "  $0 test tests/unit/test_plugins/test_*.py  # Specific test file"
    echo "  $0 coverage                                # Coverage analysis"
    echo "  $0 status                                  # Test suite overview"
}

# Main execution
main() {
    cd "$PROJECT_ROOT"
    
    local command="${1:-fast}"
    local start_time=$(date +%s)
    
    # Parse options
    case "$command" in
        "-h"|"--help")
            show_usage
            exit 0
            ;;
        "-v"|"--verbose")
            set -x
            command="${2:-fast}"
            ;;
        "-q"|"--quiet")
            exec > /dev/null 2>&1
            command="${2:-fast}"
            ;;
    esac
    
    # Check environment first
    check_environment
    
    # Execute command
    case "$command" in
        "fast")
            run_fast_tests
            ;;
        "integration")
            run_integration_tests
            ;;
        "property")
            run_property_tests
            ;;
        "all")
            run_fast_tests && run_integration_tests && run_property_tests
            ;;
        "quality")
            run_quality_check
            ;;
        "coverage")
            run_coverage
            ;;
        "pre-commit")
            run_fast_tests && run_quality_check
            ;;
        "status")
            show_test_status
            ;;
        "test")
            if [[ -z "$2" ]]; then
                log_error "Please specify a test file"
                show_usage
                exit 1
            fi
            run_specific_test "$2"
            ;;
        *)
            log_error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    log_success "Total execution time: ${duration}s"
}

# Execute main function with all arguments
main "$@"