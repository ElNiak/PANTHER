# Output Collection Testing Suite

This directory contains a comprehensive **End-to-End (E2E) testing suite** for PANTHER's unified output collection system. The tests use **real PANTHER code with minimal mocking** to validate the complete system.

## E2E Testing Philosophy

✅ **Real PANTHER CLI execution** - Tests run actual `python -m panther` commands  
✅ **Real plugin system** - Uses actual PANTHER service plugins, not mocks  
✅ **Real Docker containers** - Tests actual container orchestration and volume mounting  
✅ **Real packet capture** - Tests actual tshark injection and pcap file generation  
✅ **Real environment workflows** - Tests complete setup → deploy → teardown → collection cycle  

## Overview

The testing suite validates that output collection works correctly across:
- **Docker Compose Environment** - Multi-container orchestration  
- **Localhost Single Container** - Single container with multiple processes
- **Shadow NS Environment** - Network simulation environment

## Test Structure

```
tests/integration/output_collection/
├── README.md                           # This file
├── conftest.py                         # Test fixtures and utilities
├── test_unified_output_collection.py   # Main integration tests
├── test_edge_cases.py                  # Edge case and performance tests
├── test_services/                      # Test service implementations
│   └── universal_test_service.py       # Mock service that generates outputs
├── test_configs/                       # Test experiment configurations
│   ├── docker_compose_minimal.yaml     # Docker Compose test config
│   ├── localhost_minimal.yaml          # Localhost container test config
│   └── shadow_ns_minimal.yaml          # Shadow NS test config
└── validate_e2e_setup.py               # Validation script for E2E setup
```

## Test Categories

### 1. Integration Tests (`test_unified_output_collection.py`)

**Purpose**: Validate end-to-end output collection functionality

**Tests**:
- `test_docker_compose_output_collection()` - Docker Compose environment
- `test_localhost_output_collection()` - Localhost single container
- `test_shadow_ns_output_collection()` - Shadow NS simulation

**Validation**:
- Standard output files (stdout.log, stderr.log, sslkeylogfile.txt)
- Packet capture files (*.pcap, *.pcapng)
- Enhanced pattern matching for additional files
- Proper file content and non-zero sizes

### 2. Edge Cases and Performance (`test_edge_cases.py`)

**Edge Cases**:
- Missing output files graceful handling
- Empty output files processing
- Permission-denied file handling
- Path resolution across environments

**Performance Tests**:
- Output collection timing (< 1 second for 10 services)
- Large file handling (1MB+ files)
- Concurrent service collection

## Test Service Architecture

### Real PANTHER Test Service

The tests use a **real PANTHER service plugin** (`test_output_service`) that:

- **Follows PANTHER architecture** - Inherits from `BaseQUICServiceManager`
- **Uses real command generation** - Leverages PANTHER's command building system  
- **Gets real packet capture** - PANTHER automatically injects tshark commands
- **Creates realistic outputs** - Generates the same files as real protocol implementations

**Generated files:**

```python
# Standard outputs that all PANTHER services generate
- stdout.log          # Service output
- stderr.log          # Service errors
- sslkeylogfile.txt   # SSL/TLS key logging
- {service_name}.pcap # Packet capture

# Enhanced pattern files (when CREATE_ADDITIONAL_FILES=true)
- tls_keylog_custom.txt     # Additional SSL patterns
- ssl_keys_debug.keys       # More SSL patterns
- packet_capture_extra.pcapng  # Additional pcap patterns
- network_trace.cap         # More pcap patterns
```

### Test Configuration

Each test environment has minimal configurations:

- **Docker Compose**: 2 services (server + client), 10 second runtime
- **Localhost**: 1 combined service, 8 second runtime  
- **Shadow NS**: 2 simulation services, 20 second runtime

## Running Tests

### Prerequisites

```bash
# Ensure Docker is running
docker --version

# Ensure PANTHER is installed in development mode
python -m pip install -e .

# Verify pytest is available
pytest --version

# Validate E2E setup (recommended first step)
python tests/integration/output_collection/validate_e2e_setup.py
```

### Run All Output Collection Tests

```bash
# Run all output collection tests
pytest tests/integration/output_collection/ -v -m "output_collection"

# Run with Docker requirement
pytest tests/integration/output_collection/ -v -m "requires_docker"
```

### Run Specific Environment Tests

```bash
# Docker Compose only
pytest tests/integration/output_collection/ -v -m "docker_compose"

# Localhost container only
pytest tests/integration/output_collection/ -v -m "localhost"

# Shadow NS only  
pytest tests/integration/output_collection/ -v -m "shadow_ns"
```

### Run Performance Tests

```bash
# Performance and timing tests
pytest tests/integration/output_collection/ -v -m "performance"
```

### Run Edge Case Tests

```bash
# Edge cases and error handling
pytest tests/integration/output_collection/test_edge_cases.py -v
```

## Test Execution Timeline

| Test Category | Estimated Time | Description |
|---------------|----------------|-------------|
| Docker Compose | 45 seconds | Container build + run + collection |
| Localhost Single | 30 seconds | Single container + collection |
| Shadow NS | 60 seconds | Simulation + collection |
| Edge Cases | 30 seconds | Path resolution, missing files |
| Performance | 45 seconds | Timing and large file tests |
| **Total** | **~3.5 minutes** | Complete test suite |

## Expected Output Files

After successful tests, output files are collected in temporary directories:

```
test_outputs/
├── logs/
│   ├── test_server/
│   │   ├── stdout.log              ✓ Service output
│   │   ├── stderr.log              ✓ Service errors  
│   │   ├── sslkeylogfile.txt       ✓ SSL key logging
│   │   ├── test_server.pcap        ✓ Packet capture
│   │   ├── tls_keylog_custom.txt   ✓ Enhanced SSL pattern
│   │   └── packet_capture_extra.pcapng ✓ Enhanced pcap pattern
│   └── test_client/
│       ├── stdout.log              ✓ Client output
│       ├── stderr.log              ✓ Client errors
│       ├── sslkeylogfile.txt       ✓ SSL key logging
│       └── test_client.pcap        ✓ Client packet capture
└── experiment.log                  ✓ Experiment log
```

## Troubleshooting

### Common Issues

**1. Docker Permission Errors**
```bash
# Add user to docker group
sudo usermod -aG docker $USER
# Log out and back in, or:
newgrp docker
```

**2. Test Timeouts**
```bash
# Increase timeout for slow systems
pytest tests/integration/output_collection/ -v --timeout=600
```

**3. Missing Output Files**
```bash
# Check Docker logs for service issues
docker logs <container_name>

# Verify test service execution
pytest tests/integration/output_collection/ -v -s --log-cli-level=DEBUG
```

**4. Port Conflicts**
```bash
# Clean up existing containers
docker container prune -f
docker system prune -f
```

### Debug Mode

Run tests with maximum verbosity:

```bash
pytest tests/integration/output_collection/ \
  -v -s \
  --log-cli-level=DEBUG \
  --tb=long \
  --capture=no
```

## Test Validation Criteria

### Success Criteria

**✅ Functional Requirements**:
- All three environments collect standard outputs
- Enhanced pattern matching discovers additional files  
- Missing files handled gracefully without crashes
- Path resolution works correctly for each environment

**✅ Performance Requirements**:
- Output collection adds <5 seconds to teardown time
- Large files (>1MB) processed without memory issues
- Test suite completes in <5 minutes

**✅ Quality Requirements**:
- 100% test pass rate on clean Docker environment
- No false positives in output validation
- Clear error messages for debugging

### Test Markers

Tests use pytest markers for categorization:

```python
@pytest.mark.requires_docker     # Needs Docker daemon
@pytest.mark.integration         # Integration test
@pytest.mark.output_collection   # Output collection specific
@pytest.mark.docker_compose      # Docker Compose environment
@pytest.mark.localhost           # Localhost container environment  
@pytest.mark.shadow_ns           # Shadow NS environment
@pytest.mark.performance         # Performance test
@pytest.mark.unit                # Unit test
```

## Integration with CI/CD

This test suite is designed for CI/CD integration:

```yaml
# Example GitHub Actions
name: Output Collection Tests
on: [push, pull_request]

jobs:
  output-collection:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-docker
      - name: Run output collection tests
        run: |
          pytest tests/integration/output_collection/ \
            -v -m "requires_docker" \
            --timeout=300
```

## Contributing

When adding new tests:

1. **Follow existing patterns** - Use the same fixtures and utilities
2. **Add appropriate markers** - Tag tests with correct pytest markers
3. **Update documentation** - Add test descriptions to this README
4. **Validate all environments** - Ensure tests work across Docker Compose, localhost, and Shadow NS
5. **Check performance** - Ensure tests complete within reasonable time limits

## Related Files

- `/panther/plugins/environments/network_environment/base_network_environment.py` - Base output collection implementation
- `/panther/plugins/environments/network_environment/*/` - Environment-specific implementations
- `/tests/pytest.ini` - Pytest configuration with markers
- `/OUTPUT_COLLECTION_TESTING_PLAN.md` - Detailed testing strategy document