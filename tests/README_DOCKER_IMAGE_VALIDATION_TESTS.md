# Docker Image Validation Tests

This document describes the comprehensive test suite for Docker image validation in PANTHER, designed to prevent deployment failures like `unknown (ceacda77-b5b4-56d6-a95f-ec764bb37357)`.

## Test Structure

### 1. Unit Tests (`tests/unit/test_core/test_docker_image_validation.py`)

**Purpose**: Test core Docker image validation functionality in isolation.

**Key Test Classes**:
- `TestDockerImageExistenceValidation`: Core image existence checking
- `TestEnvironmentManagerImageValidation`: Environment manager validation
- `TestMissingImageFailureScenarios`: Specific failure scenarios
- `TestImageValidationIntegration`: Component integration
- `TestImageValidationPerformance`: Performance characteristics

**Critical Test Cases**:
- `test_image_exists_validation_success()`: Validates existing images correctly
- `test_image_exists_validation_failure()`: Handles missing images properly
- `test_image_exists_with_uuid_tags()`: Catches UUID-like problematic images
- `test_image_validation_with_cache_fallback()`: Cache-based validation when Docker unavailable

**Example Usage**:
```bash
pytest tests/unit/test_core/test_docker_image_validation.py -v
```

### 2. Integration Tests (`tests/integration/test_docker_image_validation_integration.py`)

**Purpose**: Test image validation across multiple PANTHER components.

**Key Test Classes**:
- `TestLocalhostEnvironmentImageValidation`: Localhost environment validation
- `TestEnvironmentManagerDockerMixinValidation`: Docker mixin validation patterns
- `TestDockerComposeEnvironmentValidation`: Docker Compose service validation
- `TestServiceManagerImageBuildValidation`: Build-then-validate workflows
- `TestEndToEndImageValidationWorkflow`: Complete workflow testing

**Critical Test Cases**:
- `test_localhost_validates_image_before_launch()`: Prevents deployment of missing images
- `test_fixed_behavior_fails_fast()`: Tests improved validation that fails immediately
- `test_service_manager_build_succeeds_validation_fails()`: Catches build inconsistencies
- `test_complete_workflow_with_build_validation_failure()`: End-to-end failure handling

**Example Usage**:
```bash
pytest tests/integration/test_docker_image_validation_integration.py -v
```

### 3. Functional Tests (`tests/functional/test_docker_image_failure_scenarios.py`)

**Purpose**: Test specific failure patterns that occur in production.

**Key Test Classes**:
- `TestSpecificDockerImageFailures`: Exact error reproduction
- `TestDeploymentFailureScenarios`: Deployment-time failures
- `TestServiceLifecycleFailureScenarios`: Service lifecycle issues
- `TestRecoveryAndDiagnosticScenarios`: Recovery and diagnosis

**Critical Test Cases**:
- `test_unknown_uuid_image_error_exact_reproduction()`: Reproduces the exact user error
- `test_build_process_creates_intermediate_images()`: Tests intermediate image issues
- `test_docker_build_silent_failure()`: Catches silent build failures
- `test_deployment_fails_early_with_validation()`: Tests early failure detection

**Example Usage**:
```bash
pytest tests/functional/test_docker_image_failure_scenarios.py -v
```

### 4. End-to-End Tests (`tests/e2e/test_docker_image_lifecycle.py`)

**Purpose**: Test complete Docker image lifecycle from configuration to deployment.

**Key Test Classes**:
- `TestCompleteDockerImageLifecycle`: Full service lifecycle
- `TestDockerImageValidationWorkflows`: Validation workflow patterns
- `TestImageLifecycleRecoveryScenarios`: Recovery and resilience

**Critical Test Cases**:
- `test_successful_complete_lifecycle()`: Validates entire successful flow
- `test_lifecycle_fails_at_validation_step()`: Tests validation failure detection
- `test_prevent_uuid_image_deployment_workflow()`: Prevents problematic deployments
- `test_automated_recovery_workflow()`: Tests recovery mechanisms

**Example Usage**:
```bash
pytest tests/e2e/test_docker_image_lifecycle.py -v
```

## Running All Image Validation Tests

### Quick Test Run
```bash
# Run all Docker image validation tests
pytest tests/ -k "docker_image" -v

# Run specific test types
pytest tests/ -m "docker_validation" -v
pytest tests/ -m "docker_failures" -v
pytest tests/ -m "docker_lifecycle" -v
```

### Comprehensive Test Run
```bash
# Run with coverage
pytest tests/ -k "docker_image" --cov=panther.core.docker_builder --cov-report=html

# Run with detailed output
pytest tests/ -k "docker_image" -v --tb=long

# Run specific problematic scenario tests
pytest tests/ -k "uuid" -v
pytest tests/ -k "unknown" -v
```

## Test Categories and Markers

The tests use pytest markers for organization:

- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.functional`: Functional tests
- `@pytest.mark.e2e`: End-to-end tests
- `@pytest.mark.docker_validation`: Docker validation specific
- `@pytest.mark.docker_failures`: Docker failure scenarios
- `@pytest.mark.docker_lifecycle`: Docker lifecycle tests

## Key Test Scenarios Covered

### 1. The Specific Error Case
Tests specifically address: `unknown (ceacda77-b5b4-56d6-a95f-ec764bb37357)`

- **Root Cause**: Build process claims success but image doesn't exist
- **Detection**: Validation step catches missing images
- **Prevention**: Early validation prevents deployment attempts

### 2. Build vs. Validation Inconsistencies
- Build reports success but image missing
- Intermediate images exist but final tagged image missing
- Silent build failures that report success

### 3. Environment Manager Validation Gaps
- Current: Warning-only approach in `environment_manager_docker_mixing.py:124`
- Fixed: Fail-fast validation that prevents deployment
- Integration: Proper validation before container launch

### 4. Service Lifecycle Validation
- Pre-build validation
- Post-build image existence verification
- Pre-deployment readiness checks
- Deployment-time validation

## Test Data and Fixtures

### Mock Docker Builders
Tests include comprehensive mock Docker builders that simulate:
- Successful builds with existing images
- Failed builds
- Silent failures (build success but no image)
- Cache-based validation
- Docker daemon unavailability

### Service Configurations
Test configurations cover various PANTHER service types:
- QUIC services (picoquic, quiche)
- HTTP services
- Custom protocol implementations
- Multi-service environments

### Error Scenarios
Tests simulate realistic error conditions:
- Network failures
- Disk space issues
- Permission problems
- Registry unavailability
- Malformed Dockerfiles

## Integration with Existing Tests

These Docker image validation tests integrate with PANTHER's existing test infrastructure:

- **Fixtures**: Uses existing `conftest.py` fixtures where applicable
- **Mocks**: Builds on established mocking patterns
- **CI/CD**: Compatible with existing pytest configuration
- **Coverage**: Integrates with coverage reporting

## Best Practices for New Tests

When adding new Docker image validation tests:

1. **Use Appropriate Test Level**:
   - Unit: Single component testing
   - Integration: Multi-component interactions
   - Functional: Specific user scenarios
   - E2E: Complete workflows

2. **Include Failure Scenarios**:
   - Always test both success and failure paths
   - Include edge cases and error conditions
   - Test recovery mechanisms

3. **Mock External Dependencies**:
   - Docker daemon interactions
   - Registry communications
   - File system operations
   - Network calls

4. **Use Descriptive Names**:
   - Test names should clearly indicate what's being tested
   - Include the expected outcome
   - Reference specific error conditions when applicable

5. **Validate State Changes**:
   - Verify system state before and after operations
   - Check that side effects occur as expected
   - Ensure cleanup happens properly

## Troubleshooting Test Issues

### Common Test Failures

1. **Docker System Not Available**:
   ```
   # Tests skip automatically when Docker unavailable
   if not DOCKER_SYSTEM_AVAILABLE:
       pytest.skip("Docker system not available")
   ```

2. **Mock Configuration Issues**:
   ```python
   # Ensure mocks are properly configured
   mock_builder.image_exists.return_value = True
   mock_builder.image_exists.assert_called_with(expected_image)
   ```

3. **Fixture Conflicts**:
   ```python
   # Use unique fixture names and proper cleanup
   @pytest.fixture
   def unique_fixture_name():
       # Setup
       yield resource
       # Cleanup
   ```

### Running Tests in CI/CD

The tests are designed to run in CI/CD environments:
- No external Docker daemon required (uses mocks)
- No network dependencies
- Fast execution (< 30 seconds for full suite)
- Clear failure messages for debugging

## Coverage Goals

The test suite aims for comprehensive coverage:

- **Functional Coverage**: All Docker image validation paths
- **Error Coverage**: All failure scenarios and edge cases
- **Integration Coverage**: All component interactions
- **Performance Coverage**: Validation performance characteristics

Target coverage metrics:
- Line coverage: > 95%
- Branch coverage: > 90%
- Function coverage: 100%

## Future Enhancements

Planned test improvements:

1. **Property-Based Testing**: Use Hypothesis for image name validation
2. **Performance Benchmarks**: Automated performance regression testing
3. **Security Testing**: Image vulnerability scanning validation
4. **Chaos Testing**: Random failure injection during validation
5. **Real Docker Integration**: Optional tests with real Docker daemon
