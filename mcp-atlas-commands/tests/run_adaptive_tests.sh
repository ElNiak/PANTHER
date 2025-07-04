#!/bin/bash
# Comprehensive test runner for Adaptive Command Selection tests

echo "=========================================="
echo "Running Adaptive Command Selection Tests"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test categories
declare -a test_categories=(
    "Unit Tests:test_adaptive_command_selector.py"
    "Integration Tests:test_adaptive_integration.py"
    "Context Classification:test_context_classification_improvements.py"
    "Learning Persistence:test_learning_persistence.py"
    "Performance Tests:test_adaptive_performance.py"
)

# Track results
total_tests=0
passed_tests=0
failed_tests=0

# Function to run a test file
run_test() {
    local category=$1
    local test_file=$2
    
    echo -e "${YELLOW}Running $category${NC}"
    echo "File: $test_file"
    echo "----------------------------------------"
    
    # Run the test with pytest
    if pytest "$test_file" -v --tb=short; then
        echo -e "${GREEN}✓ $category passed${NC}"
        ((passed_tests++))
    else
        echo -e "${RED}✗ $category failed${NC}"
        ((failed_tests++))
    fi
    
    ((total_tests++))
    echo ""
}

# Change to tests directory
cd "$(dirname "$0")"

# Run each test category
for test_spec in "${test_categories[@]}"; do
    IFS=':' read -r category file <<< "$test_spec"
    if [ -f "$file" ]; then
        run_test "$category" "$file"
    else
        echo -e "${RED}Warning: $file not found${NC}"
    fi
done

# Summary
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo "Total test files: $total_tests"
echo -e "Passed: ${GREEN}$passed_tests${NC}"
echo -e "Failed: ${RED}$failed_tests${NC}"

# Generate detailed report
echo ""
echo "Generating detailed test report..."
pytest test_adaptive_*.py test_context_*.py test_learning_*.py \
    --html=adaptive_test_report.html \
    --self-contained-html \
    --cov=atlas_commands.workflow.adaptive_command_selector \
    --cov-report=html:adaptive_coverage \
    --cov-report=term \
    2>/dev/null || true

echo ""
echo "Reports generated:"
echo "- HTML Test Report: adaptive_test_report.html"
echo "- Coverage Report: adaptive_coverage/index.html"

# Exit with appropriate code
if [ $failed_tests -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
fi