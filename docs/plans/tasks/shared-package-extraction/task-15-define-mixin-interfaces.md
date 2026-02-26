# Task 15: Define Mixin Protocol + ABC Interfaces

## Goal
Define 9 Protocol + ABC interface pairs in `panther_types/interfaces/` that describe the contracts for PANTHER's cross-project mixin classes.

## Prerequisites
- Task 14 completed (Phase 2 verified)

## Context
PANTHER uses a mixin-based architecture where plugins (like panther_ivy) compose multiple mixins. These mixins have public APIs that cross project boundaries. Rather than extracting the concrete implementations (which have deep panther internal deps), we define lightweight interfaces.

Each interface has two forms:
1. **Protocol** (structural typing, `@runtime_checkable`) - for duck-typed checking
2. **ABC** (nominal typing) - for explicit inheritance when desired

## Source Mixins to Read

Before writing each interface, read the actual mixin implementation to extract accurate method signatures:

| Interface | Source Mixin | Source File |
|-----------|-------------|-------------|
| ServiceManagerProtocol | ServiceManagerMixin | `panther/plugins/services/mixins/service_manager_mixin.py` |
| EventEmitterProtocol | ServiceManagerEventMixin | `panther/plugins/services/mixins/service_manager_event_mixin.py` |
| PluginDirectoryProtocol | PluginDirectoryMixin | `panther/plugins/services/mixins/plugin_directory_mixin.py` |
| TesterManagerProtocol | TesterServiceManagerMixin | `panther/plugins/services/testers/mixins/tester_service_manager_mixin.py` |
| CommandBuilderProtocol | ServiceCommandBuilder | `panther/core/command_processor/service_command_builder.py` |
| DockerManagerProtocol | ServiceManagerDockerMixin | `panther/plugins/services/mixins/service_manager_docker_mixin.py` |
| LoggerProtocol | LoggerMixin | `panther/core/utils/logger_mixin.py` (or similar) |
| ErrorHandlerProtocol | ErrorHandlerMixin | `panther/plugins/services/mixins/error_handler_mixin.py` |

## Steps

### Step 1: Read each source mixin

For each mixin listed above, read the source file and extract:
- Public method names
- Method signatures (parameters and return types)
- Any abstract methods

### Step 2: Create interface files

For each interface category, create a file in `panther_types/interfaces/`:

#### service_manager.py
```python
# packages/panther-types/panther_types/interfaces/service_manager.py
"""Service manager interface contracts."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class ServiceManagerProtocol(Protocol):
    """Structural type for service management. No inheritance required."""

    def get_commands(self, phase: str, **kwargs: Any) -> List[str]: ...
    def build_docker_image(self, **kwargs: Any) -> bool: ...
    def cleanup(self) -> None: ...
    def get_service_config(self) -> Any: ...


class ServiceManagerBase(ABC):
    """Abstract base for classes that want explicit enforcement."""

    @abstractmethod
    def get_commands(self, phase: str, **kwargs: Any) -> List[str]: ...

    @abstractmethod
    def build_docker_image(self, **kwargs: Any) -> bool: ...

    @abstractmethod
    def cleanup(self) -> None: ...

    @abstractmethod
    def get_service_config(self) -> Any: ...
```

#### event_emitter.py
```python
# packages/panther-types/panther_types/interfaces/event_emitter.py
"""Event emitter interface contracts."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class EventEmitterProtocol(Protocol):
    """Structural type for event emission."""

    def emit_test_starting(self, test_name: str, **kwargs: Any) -> None: ...
    def emit_test_completed(self, test_name: str, result: Any, **kwargs: Any) -> None: ...
    def emit_test_failed(self, test_name: str, error: Exception, **kwargs: Any) -> None: ...
    def handle_event(self, event: Any) -> None: ...


class EventEmitterBase(ABC):
    @abstractmethod
    def emit_test_starting(self, test_name: str, **kwargs: Any) -> None: ...
    @abstractmethod
    def emit_test_completed(self, test_name: str, result: Any, **kwargs: Any) -> None: ...
    @abstractmethod
    def emit_test_failed(self, test_name: str, error: Exception, **kwargs: Any) -> None: ...
    @abstractmethod
    def handle_event(self, event: Any) -> None: ...
```

#### plugin_directory.py
```python
# packages/panther-types/panther_types/interfaces/plugin_directory.py
"""Plugin directory interface contracts."""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class PluginDirectoryProtocol(Protocol):
    """Structural type for plugin directory management."""

    def get_plugin_dir(self) -> Path: ...
    def get_docker_image_name(self) -> str: ...
    def setup_docker_attributes(self) -> None: ...
```

#### tester_manager.py
```python
# packages/panther-types/panther_types/interfaces/tester_manager.py
"""Tester manager interface contracts."""
from __future__ import annotations

from typing import Any, Dict, List, Protocol, runtime_checkable

from panther_types.interfaces.service_manager import ServiceManagerProtocol


@runtime_checkable
class TesterManagerProtocol(ServiceManagerProtocol, Protocol):
    """Extends ServiceManagerProtocol with tester-specific methods."""

    def analyze_test_output(self, output: str, **kwargs: Any) -> Dict[str, Any]: ...
    def get_test_specifications(self) -> List[str]: ...
```

#### command_builder.py
```python
# packages/panther-types/panther_types/interfaces/command_builder.py
"""Command builder interface contracts."""
from __future__ import annotations

from typing import Any, Dict, List, Protocol, runtime_checkable


@runtime_checkable
class CommandBuilderProtocol(Protocol):
    """Structural type for command building."""

    def build_command(self, phase: str, **kwargs: Any) -> List[str]: ...
    def validate_command(self, command: str) -> bool: ...
    def get_environment(self) -> Dict[str, str]: ...


@runtime_checkable
class CommandEventProtocol(Protocol):
    """Structural type for command event emission."""

    def emit_command_generated(self, command: str, phase: str, **kwargs: Any) -> None: ...
    def emit_command_executed(self, command: str, exit_code: int, **kwargs: Any) -> None: ...
```

#### docker_manager.py
```python
# packages/panther-types/panther_types/interfaces/docker_manager.py
"""Docker manager interface contracts."""
from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class DockerManagerProtocol(Protocol):
    """Structural type for Docker image management."""

    def build_image(self, **kwargs: Any) -> bool: ...
    def ensure_image(self, image_name: str) -> bool: ...
    def get_image_name(self) -> str: ...
```

#### logger.py
```python
# packages/panther-types/panther_types/interfaces/logger.py
"""Logger interface contracts."""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LoggerProtocol(Protocol):
    """Structural type for logging."""

    def log_info(self, message: str, **kwargs: Any) -> None: ...
    def log_debug(self, message: str, **kwargs: Any) -> None: ...
    def log_warning(self, message: str, **kwargs: Any) -> None: ...
    def log_error(self, message: str, **kwargs: Any) -> None: ...
    def log_phase(self, phase: str, message: str, **kwargs: Any) -> None: ...
```

#### error_handler.py
```python
# packages/panther-types/panther_types/interfaces/error_handler.py
"""Error handler interface contracts."""
from __future__ import annotations

from typing import Any, Dict, Optional, Protocol, runtime_checkable


@runtime_checkable
class ErrorHandlerProtocol(Protocol):
    """Structural type for error handling."""

    def handle_error(self, error: Exception, **kwargs: Any) -> None: ...
    def should_fast_fail(self, error: Exception) -> bool: ...
    def create_error_context(self, error: Exception) -> Dict[str, Any]: ...
```

### Step 3: Update interfaces __init__.py

```python
# packages/panther-types/panther_types/interfaces/__init__.py
"""Protocol and ABC interfaces for cross-project contracts."""
from panther_types.interfaces.command_builder import (
    CommandBuilderProtocol,
    CommandEventProtocol,
)
from panther_types.interfaces.docker_manager import DockerManagerProtocol
from panther_types.interfaces.error_handler import ErrorHandlerProtocol
from panther_types.interfaces.event_emitter import EventEmitterBase, EventEmitterProtocol
from panther_types.interfaces.logger import LoggerProtocol
from panther_types.interfaces.plugin_directory import PluginDirectoryProtocol
from panther_types.interfaces.service_manager import (
    ServiceManagerBase,
    ServiceManagerProtocol,
)
from panther_types.interfaces.tester_manager import TesterManagerProtocol

__all__ = [
    "ServiceManagerProtocol",
    "ServiceManagerBase",
    "EventEmitterProtocol",
    "EventEmitterBase",
    "PluginDirectoryProtocol",
    "TesterManagerProtocol",
    "CommandBuilderProtocol",
    "CommandEventProtocol",
    "DockerManagerProtocol",
    "LoggerProtocol",
    "ErrorHandlerProtocol",
]
```

### Step 4: Write tests

```python
# packages/panther-types/tests/test_interfaces.py
"""Tests for mixin interfaces."""
from panther_types.interfaces import (
    ServiceManagerProtocol,
    EventEmitterProtocol,
    PluginDirectoryProtocol,
    DockerManagerProtocol,
    LoggerProtocol,
    ErrorHandlerProtocol,
    CommandBuilderProtocol,
)


class MockServiceManager:
    """Mock that satisfies ServiceManagerProtocol."""

    def get_commands(self, phase, **kwargs):
        return ["echo test"]

    def build_docker_image(self, **kwargs):
        return True

    def cleanup(self):
        pass

    def get_service_config(self):
        return {}


class TestServiceManagerProtocol:
    def test_isinstance_check(self):
        mgr = MockServiceManager()
        assert isinstance(mgr, ServiceManagerProtocol)

    def test_non_conforming(self):
        """An empty class should NOT match the protocol."""

        class Empty:
            pass

        assert not isinstance(Empty(), ServiceManagerProtocol)


class MockEventEmitter:
    def emit_test_starting(self, test_name, **kwargs):
        pass

    def emit_test_completed(self, test_name, result, **kwargs):
        pass

    def emit_test_failed(self, test_name, error, **kwargs):
        pass

    def handle_event(self, event):
        pass


class TestEventEmitterProtocol:
    def test_isinstance_check(self):
        emitter = MockEventEmitter()
        assert isinstance(emitter, EventEmitterProtocol)


class MockLogger:
    def log_info(self, message, **kwargs):
        pass

    def log_debug(self, message, **kwargs):
        pass

    def log_warning(self, message, **kwargs):
        pass

    def log_error(self, message, **kwargs):
        pass

    def log_phase(self, phase, message, **kwargs):
        pass


class TestLoggerProtocol:
    def test_isinstance_check(self):
        logger = MockLogger()
        assert isinstance(logger, LoggerProtocol)
```

## Verification
```bash
cd packages/panther-types
pytest tests/test_interfaces.py -v
```

## Important Notes
- **Read the actual mixin source files** before finalizing method signatures. The signatures above are approximations based on exploration. The actual methods may have different parameter names or types.
- The Protocol definitions use `Any` for types that reference panther internals (like event objects, config objects). This is intentional - the interfaces should not depend on concrete panther types beyond what's in panther-types.
- `@runtime_checkable` enables `isinstance()` checks but only verifies method existence, not signatures. This is a Python limitation.
- The ABC versions provide stronger guarantees but require explicit inheritance.

## Commit Message
```
feat(panther-types): add mixin Protocol and ABC interfaces

Define 9 cross-project interface contracts (ServiceManager, EventEmitter,
PluginDirectory, TesterManager, CommandBuilder, CommandEvent,
DockerManager, Logger, ErrorHandler) as Protocol + ABC pairs.
```

## Files Created
- `packages/panther-types/panther_types/interfaces/service_manager.py`
- `packages/panther-types/panther_types/interfaces/event_emitter.py`
- `packages/panther-types/panther_types/interfaces/plugin_directory.py`
- `packages/panther-types/panther_types/interfaces/tester_manager.py`
- `packages/panther-types/panther_types/interfaces/command_builder.py`
- `packages/panther-types/panther_types/interfaces/docker_manager.py`
- `packages/panther-types/panther_types/interfaces/logger.py`
- `packages/panther-types/panther_types/interfaces/error_handler.py`
- `packages/panther-types/panther_types/interfaces/__init__.py` (updated)
- `packages/panther-types/tests/test_interfaces.py`
