# Task 11: Extract Exception Hierarchy to panther-types

## Goal
Extract `PantherException`, `ErrorSeverity`, `ErrorCategory` and the exception subclass hierarchies from `fast_fail.py`, `experiment_exceptions.py`, and `network_resolution_exceptions.py`.

## Prerequisites
- Task 06 completed (package scaffolded)

## Source Files
- `panther/core/exceptions/fast_fail.py` (536 lines)
- `panther/core/exceptions/experiment_exceptions.py` (147 lines)
- `panther/core/exceptions/network_resolution_exceptions.py` (140 lines)
- `panther/core/exceptions/EnvironmentPluginNotFound.py`
- `panther/core/exceptions/ServicePluginNotFound.py`
- `panther/core/exceptions/TesterPluginNotFound.py`

## Context

### What to extract
- `ErrorSeverity` enum - severity levels
- `ErrorCategory` enum - error categories
- `PantherException` base class - the root of the hierarchy
- All exception subclasses from fast_fail.py (DockerBuildException, PluginLoadException, etc.)
- `PantherExperimentError` and subclasses from experiment_exceptions.py
- `NetworkResolutionException` and subclasses from network_resolution_exceptions.py
- `EnvironmentPluginNotFound`, `ServicePluginNotFound`, `TesterPluginNotFound`

### What NOT to extract
- `FastFailHandler` (lines 274-535 of fast_fail.py) - this is business logic with error tracking, cascade detection, pattern analysis. It stays in panther.

### Dependency Analysis
- `fast_fail.py`: Only stdlib imports (logging, datetime, enum, typing). Self-contained.
- `experiment_exceptions.py`: Imports `ErrorCategory`, `ErrorSeverity`, `PantherException` from fast_fail. Self-contained within the exception hierarchy.
- `network_resolution_exceptions.py`: Same imports as experiment_exceptions.

## Steps

### Step 1: Create panther_types/exceptions/base.py

Extract from `fast_fail.py` lines 1-271 (everything BEFORE FastFailHandler):

```python
# packages/panther-types/panther_types/exceptions/base.py
"""PANTHER exception hierarchy.

Provides the base exception types with severity and category classification
for structured error handling across the PANTHER framework.
"""
```

This file should contain:
- `ErrorSeverity` enum
- `ErrorCategory` enum
- `PantherException` base class
- `DockerBuildException`
- `PluginLoadException`
- `ServiceStartException`
- `DockerComposeException`
- `NetworkSetupException`
- `PortConflictException`
- `IvyCompilationException`
- `ResourceExhaustionException`
- `CertificateException`
- `ConfigurationException`
- `TimeoutCascadeException`
- `AuthenticationException`
- `CriticalAssertionException`
- `DependencyException`
- `ErrorCascadeException`

### Step 2: Create panther_types/exceptions/experiment.py

Copy from `experiment_exceptions.py`, updating imports to use panther_types:

```python
# packages/panther-types/panther_types/exceptions/experiment.py
"""Experiment-level exception hierarchy."""
from typing import Any, Dict, Optional

from panther_types.exceptions.base import (
    ErrorCategory,
    ErrorSeverity,
    PantherException,
)

# Copy: PantherExperimentError, ExperimentInitializationError,
# TestCaseInitializationError, TestExecutionError, ConfigurationError,
# PluginValidationError
```

### Step 3: Create panther_types/exceptions/network.py

Copy from `network_resolution_exceptions.py`, updating imports:

```python
# packages/panther-types/panther_types/exceptions/network.py
"""Network resolution exception hierarchy."""
from typing import Any, Dict, Optional

from panther_types.exceptions.base import (
    ErrorCategory,
    ErrorSeverity,
    PantherException,
)

# Copy: NetworkResolutionException, PlaceholderParsingException,
# ServiceResolutionException, EnvironmentResolutionException,
# PlaceholderValidationException, NetworkDiscoveryException
```

### Step 4: Create panther_types/exceptions/plugin_not_found.py

Read and extract the PluginNotFound exceptions. These are simple:

```python
# packages/panther-types/panther_types/exceptions/plugin_not_found.py
"""Plugin not found exceptions."""
from panther_types.exceptions.base import PantherException

# Read actual source of EnvironmentPluginNotFound.py, ServicePluginNotFound.py,
# TesterPluginNotFound.py and combine here
```

### Step 5: Update __init__.py

```python
# packages/panther-types/panther_types/exceptions/__init__.py
"""PANTHER exception hierarchy."""
from panther_types.exceptions.base import (
    AuthenticationException,
    CertificateException,
    ConfigurationException,
    CriticalAssertionException,
    DependencyException,
    DockerBuildException,
    DockerComposeException,
    ErrorCascadeException,
    ErrorCategory,
    ErrorSeverity,
    IvyCompilationException,
    NetworkSetupException,
    PantherException,
    PluginLoadException,
    PortConflictException,
    ResourceExhaustionException,
    ServiceStartException,
    TimeoutCascadeException,
)
from panther_types.exceptions.experiment import (
    ConfigurationError,
    ExperimentInitializationError,
    PantherExperimentError,
    PluginValidationError,
    TestCaseInitializationError,
    TestExecutionError,
)
from panther_types.exceptions.network import (
    EnvironmentResolutionException,
    NetworkDiscoveryException,
    NetworkResolutionException,
    PlaceholderParsingException,
    PlaceholderValidationException,
    ServiceResolutionException,
)
from panther_types.exceptions.plugin_not_found import (
    EnvironmentPluginNotFound,
    ServicePluginNotFound,
    TesterPluginNotFound,
)
```

### Step 6: Write tests

```python
# packages/panther-types/tests/test_exceptions.py
"""Tests for exception hierarchy."""
from panther_types.exceptions import (
    ErrorCategory,
    ErrorSeverity,
    PantherException,
    DockerBuildException,
    PluginLoadException,
    ConfigurationException,
    PantherExperimentError,
    TestExecutionError,
    NetworkResolutionException,
    PlaceholderParsingException,
    EnvironmentPluginNotFound,
    ServicePluginNotFound,
    TesterPluginNotFound,
)


class TestErrorEnums:
    def test_severity_values(self):
        assert ErrorSeverity.CRITICAL.value == 4
        assert ErrorSeverity.HIGH.value == 3
        assert ErrorSeverity.MEDIUM.value == 2
        assert ErrorSeverity.LOW.value == 1

    def test_category_values(self):
        assert ErrorCategory.DOCKER_BUILD.value == "docker_build"
        assert ErrorCategory.CONFIGURATION.value == "configuration"
        assert ErrorCategory.TEST_EXECUTION.value == "test_execution"


class TestPantherException:
    def test_create(self):
        e = PantherException(
            message="test error",
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.DOCKER_BUILD,
        )
        assert str(e) == "test error"
        assert e.severity == ErrorSeverity.HIGH
        assert e.category == ErrorCategory.DOCKER_BUILD
        assert e.context == {}
        assert e.timestamp is not None

    def test_should_terminate_critical(self):
        e = PantherException(
            message="critical",
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.DOCKER_BUILD,
        )
        assert e.should_terminate() is True

    def test_should_not_terminate_non_critical(self):
        e = PantherException(
            message="warning",
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.CONFIGURATION,
        )
        assert e.should_terminate() is False


class TestDockerBuildException:
    def test_is_panther_exception(self):
        e = DockerBuildException(
            message="build failed",
            image_name="panther_ivy:latest",
            dockerfile="Dockerfile",
        )
        assert isinstance(e, PantherException)
        assert e.severity == ErrorSeverity.CRITICAL
        assert e.category == ErrorCategory.DOCKER_BUILD
        assert e.context["image_name"] == "panther_ivy:latest"

    def test_with_build_error(self):
        e = DockerBuildException(
            message="build failed",
            image_name="img",
            dockerfile="Dockerfile",
            build_error="apt-get failed",
        )
        assert e.context["build_error"] == "apt-get failed"


class TestPluginLoadException:
    def test_create(self):
        e = PluginLoadException(
            message="plugin not found",
            plugin_name="picoquic",
            plugin_type="iut",
        )
        assert isinstance(e, PantherException)
        assert e.severity == ErrorSeverity.HIGH


class TestExperimentExceptions:
    def test_hierarchy(self):
        # Read actual constructor from experiment_exceptions.py before using
        e = TestExecutionError(message="test failed")
        assert isinstance(e, PantherExperimentError)
        assert isinstance(e, PantherException)


class TestNetworkExceptions:
    def test_hierarchy(self):
        # Read actual constructor from network_resolution_exceptions.py before using
        e = PlaceholderParsingException(message="bad placeholder")
        assert isinstance(e, NetworkResolutionException)
        assert isinstance(e, PantherException)


class TestPluginNotFound:
    def test_environment(self):
        e = EnvironmentPluginNotFound("docker_compose")
        assert isinstance(e, Exception)

    def test_service(self):
        e = ServicePluginNotFound("picoquic")
        assert isinstance(e, Exception)

    def test_tester(self):
        e = TesterPluginNotFound("ivy")
        assert isinstance(e, Exception)
```

**Note**: The `TestExecutionError`, `PlaceholderParsingException`, and `PluginNotFound`
constructors must be verified from their actual source files before finalizing these tests.
The constructors may have additional required parameters beyond `message`.

## Verification
```bash
cd packages/panther-types
pytest tests/test_exceptions.py -v
```

## Important Notes
- `FastFailHandler` (lines 274-535) is NOT extracted. It's business logic that stays in panther.
- The PluginNotFound exceptions may or may not extend PantherException. Read the actual source files to verify their base class.
- Exception `__init__` signatures have specific parameters (message, severity, category, context, details). Preserve these exactly.
- Some exceptions set default severity/category values. Verify these from source.

## Commit Message
```
feat(panther-types): extract exception hierarchy

Move PantherException, ErrorSeverity, ErrorCategory, and all exception
subclasses into panther-types. FastFailHandler (business logic) stays
in panther.
```

## Files Modified
- `packages/panther-types/panther_types/exceptions/base.py` (new)
- `packages/panther-types/panther_types/exceptions/experiment.py` (new)
- `packages/panther-types/panther_types/exceptions/network.py` (new)
- `packages/panther-types/panther_types/exceptions/plugin_not_found.py` (new)
- `packages/panther-types/panther_types/exceptions/__init__.py` (updated)
- `packages/panther-types/tests/test_exceptions.py` (new)
