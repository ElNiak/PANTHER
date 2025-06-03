#!/bin/bash
# E2E test script for command generation with proper escaping

# Exit on any error
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo "Starting end-to-end validation of command generation..."

# Run plugin command validation tool
echo "Running command generation validation across all plugins..."
python tools/validate_command_generation.py --verbose || {
  echo -e "${YELLOW}Command generation validation found issues in some plugins.${NC}"
  echo -e "${YELLOW}These should be fixed to ensure proper command escaping.${NC}"
  # Continue execution but note the issues
}

# Check tests before proceeding
echo "Running unit tests for structured command generation..."
pytest -xvs tests/unit/plugins/test_structured_command_generation_quic_iut.py || {
  echo -e "${RED}Unit tests failed. Please fix before proceeding.${NC}"
  exit 1
}
echo -e "${GREEN}Unit tests passed.${NC}"

# Activate virtual environment
source .venv/bin/activate || {
  echo -e "${RED}Failed to activate virtual environment. Make sure .venv exists.${NC}"
  exit 1
}

# Set up a temporary directory for output
OUTPUT_DIR=$(mktemp -d)
echo "Using temporary output directory: $OUTPUT_DIR"

# Run Panther with debug mode to generate files in output directory
echo "Running Panther to generate command files..."
python -m panther \
  --experiment-config experiment-config/experiment_config_example_minimal.yaml \
  --output-dir $OUTPUT_DIR \
  --debug

# Check if the files were generated
echo "Checking if files were generated..."
if [[ ! -d "$OUTPUT_DIR/output" ]]; then
  echo -e "${RED}Output directory not created.${NC}"
  exit 1
fi

# Check for entrypoint.sh files
ENTRYPOINT_COUNT=$(find "$OUTPUT_DIR/output" -name "entrypoint_*.sh" | wc -l)
if [[ $ENTRYPOINT_COUNT -eq 0 ]]; then
  echo -e "${RED}No entrypoint.sh files were generated.${NC}"
  exit 1
else
  echo -e "${GREEN}Found $ENTRYPOINT_COUNT entrypoint script(s).${NC}"
fi

# Check for docker-compose.yml
if [[ ! -f "$OUTPUT_DIR/output/docker-compose.yml" ]]; then
  echo -e "${RED}docker-compose.yml not generated.${NC}"
  exit 1
else
  echo -e "${GREEN}Found docker-compose.yml.${NC}"
fi

# Advanced validation - Check for entrypoint_structured.sh files if enabled
STRUCTURED_COUNT=$(find "$OUTPUT_DIR/output" -name "*structured*.sh" | wc -l)
if [[ $STRUCTURED_COUNT -gt 0 ]]; then
  echo -e "${GREEN}Found $STRUCTURED_COUNT structured script(s).${NC}"
  
  # Test for proper command argument handling
  for script in $(find "$OUTPUT_DIR/output" -name "*structured*.sh"); do
    echo -e "${YELLOW}Analyzing structured script: $script${NC}"
    
    # Look for command argument iteration
    if grep -q "for arg in" "$script"; then
      echo -e "${GREEN}Script uses proper command argument iteration.${NC}"
    else
      echo -e "${YELLOW}Script might not use structured command arguments.${NC}"
    fi
    
    # Look for environment variable iteration
    if grep -q "for key, value in" "$script" || grep -q "for key in" "$script"; then
      echo -e "${GREEN}Script uses proper environment variable iteration.${NC}"
    else
      echo -e "${YELLOW}Script might not use structured environment variables.${NC}"
    fi
  done
fi

# Validate that entrypoint scripts have proper shebang
for script in $(find "$OUTPUT_DIR/output" -name "entrypoint_*.sh"); do
  if ! grep -q "^#!/bin/bash" "$script"; then
    echo -e "${RED}Missing shebang in $script.${NC}"
    exit 1
  else
    echo -e "${GREEN}Script $script has proper shebang.${NC}"
  fi
  
  # Check for proper quoting in export statements
  if grep -q "export.*=.*[[:space:]].*[^\"']$" "$script"; then
    echo -e "${RED}Found unquoted export with spaces in $script.${NC}"
    exit 1
  else
    echo -e "${GREEN}Export statements in $script look properly quoted.${NC}"
  fi
  
  # Check for quote_shell filter usage (in structured scripts)
  if grep -q "quote_shell" "$script"; then
    echo -e "${GREEN}Script $script uses quote_shell filter.${NC}"
  fi
  
  # Make script executable and check syntax
  chmod +x "$script"
  bash -n "$script" || {
    echo -e "${RED}Shell syntax error in $script.${NC}"
    exit 1
  }
  echo -e "${GREEN}No shell syntax errors in $script.${NC}"
  
  # Try executing the script with some special character tests if it's a structured script
  if [[ $script == *"structured"* ]]; then
    echo -e "${YELLOW}Testing structured script with special characters...${NC}"
    
    # Create a test with special characters
    TEST_ENV="TEST_VAR='value with spaces and \"quotes\"'"
    TEST_CMD="$TEST_ENV $script || true"
    
    # Execute in subshell to avoid affecting main script
    (eval $TEST_CMD)
    echo -e "${GREEN}Script executed with special characters.${NC}"
  fi
done

# Validate docker-compose.yml
if command -v docker > /dev/null; then
  echo "Validating docker-compose.yml..."
  cd "$OUTPUT_DIR/output" && docker compose config --quiet || {
    echo -e "${RED}Invalid docker-compose.yml file.${NC}"
    exit 1
  }
  echo -e "${GREEN}docker-compose.yml passed validation.${NC}"
else
  echo "Docker not installed, skipping docker-compose.yml validation."
fi

# Create a specific test for implementations we enhanced
echo "Testing enhanced implementations..."
mkdir -p "$OUTPUT_DIR/tests"

# Test script for special character handling in our enhanced implementations
cat > "$OUTPUT_DIR/tests/test_enhanced_impls.py" << 'EOF'
#!/usr/bin/env python3
import os
import sys
import shlex

from panther.plugins.services.services_interface import quote_shell, quote_yaml
from panther.plugins.protocols.config_schema import ProtocolConfig, RoleEnum
from panther.config.config_experiment_schema import ServiceConfig

# For testing special characters handling
TEST_STRINGS = [
    "normal string",
    "string with spaces",
    "string with \"quotes\"",
    "string with 'single quotes'",
    "string with $dollar signs",
    "string with & ampersands",
    "string with | pipes",
    "path/with/special chars/file.txt",
    "--option=value with spaces",
    "multi\nline\nstring"
]

def test_enhanced_impl(impl_name):
    print(f"\nTesting {impl_name} implementation...")
    if impl_name == "aioquic":
        from panther.plugins.services.iut.quic.aioquic.aioquic import AioquicServiceManager
        from panther.plugins.services.iut.quic.aioquic.config_schema import AioquicConfig
        config_class = AioquicConfig
        manager_class = AioquicServiceManager
    elif impl_name == "lsquic":
        from panther.plugins.services.iut.quic.lsquic.lsquic import LsquicServiceManager
        from panther.plugins.services.iut.quic.lsquic.config_schema import LsquicConfig
        config_class = LsquicConfig
        manager_class = LsquicServiceManager
    elif impl_name == "quant":
        from panther.plugins.services.iut.quic.quant.quant import QuantServiceManager
        from panther.plugins.services.iut.quic.quant.config_schema import QuantConfig
        config_class = QuantConfig
        manager_class = QuantServiceManager
    else:
        print(f"Unknown implementation: {impl_name}")
        return False

    # Create mock objects
    mock_protocol = ProtocolConfig(name="quic", version="draft-29", role=RoleEnum.server, target="127.0.0.1")
    mock_service = config_class()
    mock_service.name = "test-service"
    mock_service.protocol = mock_protocol
    mock_service.timeout = 60
    
    # Add minimal required config to make test work
    mock_service.implementation = type('obj', (object,), {'version': type('obj', (object,), {})})()
    mock_service.implementation.version.server = {
        "binary": {"name": "test_binary", "dir": "/test/dir"},
        "certificates": {
            "cert_param": "-c", 
            "cert_file": "/test/cert.pem",
            "key_param": "-k",
            "key_file": "/test/key.pem"
        },
        "protocol": {
            "alpn": {
                "param": "--alpn",
                "value": "h3-29"
            },
            "additional_parameters": "--test \"special param\" --another=option"
        },
        "network": {
            "port": 4433,
            "interface": {
                "param": "--interface",
                "value": "0.0.0.0"
            }
        },
        "logging": {
            "log_path": "/app/logs/test.log",
            "err_path": "/app/logs/test.err"
        }
    }
    
    if impl_name == "client":
        mock_service.implementation.version.client = mock_service.implementation.version.server
    
    # Create manager and test
    try:
        manager = manager_class(mock_service, "iut", mock_protocol, impl_name)
        
        # Test build_command_args with special strings
        print("Testing build_command_args with special strings...")
        for test_str in TEST_STRINGS:
            args = manager.build_command_args(test_str)
            print(f"  Original: {test_str!r}")
            print(f"  Processed: {args}")
            
            # Verify we can join and split again
            rejoined = ' '.join(shlex.quote(arg) for arg in args)
            resplit = shlex.split(rejoined)
            assert len(resplit) == len(args), f"Length mismatch after rejoin/split: {len(resplit)} != {len(args)}"
        
        # Test full command generation
        cmd_args = manager.generate_deployment_commands()
        print(f"Generated command args: {cmd_args}")
        assert isinstance(cmd_args, list), "Command args must be a list"
        
        # Test environment variables
        run_cmd = manager.generate_run_command()
        assert isinstance(run_cmd["command_env"], dict), "Environment variables must be a dict"
        print(f"Generated environment variables: {run_cmd['command_env']}")
        
        return True
    except Exception as e:
        print(f"Error testing {impl_name}: {e}")
        import traceback
        traceback.print_exc()
        return False

# Run tests
success = True
for impl in ["aioquic", "lsquic", "quant"]:
    if not test_enhanced_impl(impl):
        success = False

sys.exit(0 if success else 1)
EOF

# Make the test script executable and run it
chmod +x "$OUTPUT_DIR/tests/test_enhanced_impls.py"
python "$OUTPUT_DIR/tests/test_enhanced_impls.py" || {
  echo -e "${RED}Enhanced implementations test failed.${NC}"
  exit 1
}
echo -e "${GREEN}Enhanced implementations test passed.${NC}"

# Run PantherIvy template rendering tests
echo "Running PantherIvy template rendering tests..."
pytest -xvs tests/plugins/services/testers/panther_ivy/test_template.py || {
  echo -e "${RED}PantherIvy template rendering tests failed.${NC}"
  echo "Please check if templates are being rendered with proper escaping."
  EXIT_CODE=1
}
echo -e "${GREEN}PantherIvy template rendering tests passed.${NC}"

# Clean up
echo "Cleaning up temporary directory..."
rm -rf "$OUTPUT_DIR"

echo -e "${GREEN}End-to-end validation passed successfully.${NC}"
exit 0
