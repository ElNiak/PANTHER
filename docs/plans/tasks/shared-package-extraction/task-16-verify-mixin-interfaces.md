# Task 16: Verify Mixin Interfaces Match Concrete Implementations

## Goal
Write tests that verify existing concrete mixin implementations satisfy the Protocol interfaces defined in task 15.

## Prerequisites
- Task 15 completed (interfaces defined)

## Context
The Protocol interfaces were defined based on exploration of the mixin source files. This task verifies that the actual concrete mixins match the protocols using `isinstance()` checks. If they don't, either the interface or the test needs adjustment.

## Steps

### Step 1: Write conformance tests

```python
# packages/panther-types/tests/test_interface_conformance.py
"""Tests verifying concrete mixins satisfy Protocol interfaces.

These tests require the full panther package to be installed since they
import concrete mixin implementations. They are integration tests.
"""
import pytest

# Skip entire module if panther is not installed
pytest.importorskip("panther")

from panther_types.interfaces import (
    ServiceManagerProtocol,
    EventEmitterProtocol,
    PluginDirectoryProtocol,
    DockerManagerProtocol,
    ErrorHandlerProtocol,
)


class TestConcreteConformance:
    """Verify concrete mixins satisfy their Protocol interfaces.

    Note: These use isinstance() with @runtime_checkable Protocols,
    which only checks method existence, not signatures.
    """

    def test_service_manager_event_mixin(self):
        """ServiceManagerEventMixin should satisfy EventEmitterProtocol."""
        try:
            from panther.plugins.services.mixins.service_manager_event_mixin import (
                ServiceManagerEventMixin,
            )
            # Can't isinstance check on a mixin class directly (no instance),
            # but we can check the class has the required methods
            required = ["emit_test_starting", "emit_test_completed", "emit_test_failed", "handle_event"]
            for method in required:
                assert hasattr(ServiceManagerEventMixin, method), (
                    f"ServiceManagerEventMixin missing {method}"
                )
        except ImportError:
            pytest.skip("ServiceManagerEventMixin not importable")

    def test_plugin_directory_mixin(self):
        """PluginDirectoryMixin should have directory-related methods."""
        try:
            from panther.plugins.services.mixins.plugin_directory_mixin import (
                PluginDirectoryMixin,
            )
            # Check for required methods - names may differ from interface
            # The interface says get_plugin_dir, but the mixin may use _get_plugin_dir
            # This test documents the actual mapping
            has_public = hasattr(PluginDirectoryMixin, "get_plugin_dir")
            has_private = hasattr(PluginDirectoryMixin, "_get_plugin_dir")
            assert has_public or has_private, (
                "PluginDirectoryMixin missing plugin dir method"
            )
        except ImportError:
            pytest.skip("PluginDirectoryMixin not importable")

    def test_error_handler_mixin(self):
        """ErrorHandlerMixin should have error handling methods."""
        try:
            from panther.plugins.services.mixins.error_handler_mixin import (
                ErrorHandlerMixin,
            )
            assert hasattr(ErrorHandlerMixin, "handle_error"), (
                "ErrorHandlerMixin missing handle_error"
            )
        except ImportError:
            pytest.skip("ErrorHandlerMixin not importable")

    def test_panther_ivy_satisfies_tester_methods(self):
        """PantherIvyServiceManager should have tester-specific methods."""
        try:
            from panther_ivy.panther_ivy import PantherIvyServiceManager
            instance_methods = dir(PantherIvyServiceManager)
            # Should have command generation, analysis, and cleanup methods
            assert "cleanup" in instance_methods or "_cleanup" in instance_methods
        except ImportError:
            pytest.skip("PantherIvyServiceManager not importable")
```

### Step 2: Document any discrepancies

If a concrete mixin's methods don't match the Protocol interface (e.g., uses `_get_plugin_dir` instead of `get_plugin_dir`), document the mapping:

```python
# packages/panther-types/panther_types/interfaces/CONFORMANCE_NOTES.md
# (create this file to document actual method name mappings)
```

### Step 3: Adjust interfaces if needed

If the conformance tests reveal that the Protocol method names don't match the actual mixin methods, update the Protocol definitions to match reality.

For example, if `PluginDirectoryMixin` uses `_get_plugin_dir` (private), the Protocol should either:
- Use `_get_plugin_dir` (matching the actual convention), OR
- Document that the Protocol defines the PUBLIC contract while the mixin uses a private convention

## Verification
```bash
cd packages/panther-types
# Run only conformance tests (requires panther installed)
pytest tests/test_interface_conformance.py -v

# Run all interface tests
pytest tests/test_interfaces.py tests/test_interface_conformance.py -v
```

## Important Notes
- These tests are optional integration tests. They require the full panther package to be installed.
- Use `pytest.importorskip` to gracefully skip when panther is not available.
- The `@runtime_checkable` Protocol check only verifies method NAMES, not signatures. A method with the wrong parameters would still pass `isinstance()`.
- This is informational, not blocking. Discrepancies should be documented, not necessarily fixed immediately.

## Commit Message
```
test(panther-types): add mixin interface conformance tests

Verify that concrete PANTHER mixins satisfy the Protocol interfaces
defined in panther-types. Document any method name discrepancies.
```

## Files Created/Modified
- `packages/panther-types/tests/test_interface_conformance.py` (new)
