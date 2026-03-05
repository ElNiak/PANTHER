"""Test Cases Module - Mixin-Based Test Execution for PANTHER.

Provides the ``TestCase`` framework that assembles test execution from
composable mixins, each contributing a distinct capability.

Architecture::

    TestCase
        │
        ├── ServiceManagementMixin       ── Docker service orchestration,
        │                                   image builds, service lifecycle
        ├── EnvironmentManagementMixin   ── network environment setup,
        │                                   deployment coordination
        ├── TestExecutionMixin           ── command execution, output
        │                                   collection, assertion validation
        ├── MetricsMixin                 ── performance timing, resource
        │                                   monitoring, metrics emission
        └── ObserverManagementMixin      ── event observer lifecycle,
                                            notification management

State Machine::

    PENDING ──> RUNNING ──> COLLECTING ──> DONE
                   │                        │
                   └──────> ERROR <─────────┘

Module Layout::

    test_cases/
    ├── test_case_impl.py        # TestCase class with mixin composition
    ├── test_interface_impl.py   # ITestCase abstract interface
    ├── base/                    # Base test case utilities
    ├── mixins/                  # Composable capability mixins
    ├── execution/               # Execution engine internals
    └── analysis/                # Post-run analysis helpers

See Also:
    `panther.core.experiment_manager` -- orchestrates test case execution
    `panther.core.events` -- events emitted during state transitions
"""

# Import key modules for easier access
from . import test_case_impl as test_case
from . import test_interface_impl as test_interface

# Define the public API
__all__ = ["test_case", "test_interface"]
