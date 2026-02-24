# Service Plugin Development Guide

This document provides comprehensive guidance for developing service plugins for the PANTHER framework, covering both Implementation Under Test (IUT) services and Tester services.

!!! warning "Prerequisites"
    Before developing service plugins, ensure you understand the PANTHER architecture by reading the [Plugin Development Guide](../development.md) and have a working PANTHER installation.

## Service Plugin Architecture

PANTHER service plugins are organized into two primary categories:

```text
plugins/services/
├── base/                # Base classes for inheritance architecture
│   ├── quic_service_base.py       # BaseQUICServiceManager
│   ├── python_quic_base.py        # Python-specific extensions
│   ├── rust_quic_base.py          # Rust-specific extensions
│   └── docker_build_base.py       # Docker build patterns
├── iut/                 # Implementation Under Test plugins
│   ├── http/
│   ├── quic/            # QUIC implementations inheriting from base classes
│   └── ...
├── testers/             # Tester plugins
│   ├── ivy_tester/
│   └── ...
├── __init__.py
├── config_schema.py
└── services_interface.py
```

## Modern Inheritance-Based Architecture (2024)

!!! success "Significant Code Reduction"
    The new inheritance architecture has achieved a **47.2% average code reduction** across all service implementations by eliminating duplicate command generation logic and providing consistent, well-tested functionality through specialized base classes.

### Base Class Hierarchy for Service Managers

```text
BaseQUICServiceManager              # Core QUIC functionality and template method pattern
├── PythonQUICServiceManager       # Python-specific extensions (async/await patterns)
├── RustQUICServiceManager         # Rust-specific extensions (Cargo integration)
└── Direct inheritance             # C/Go implementations (direct base class usage)

ServiceCommandBuilder              # Command generation utilities
DockerBuilderFactory              # Docker build pattern abstraction
EventEmitterMixin                 # Event-driven communication
```

### Template Method Pattern in Service Development

Modern service plugins use the template method pattern where base classes define the workflow and subclasses implement specific details:

```python
# Modern service manager implementation
from panther.plugins.services.base.quic_service_base import BaseQUICServiceManager

class MyQuicServiceManager(BaseQUICServiceManager):
    """Modern QUIC service manager using inheritance architecture."""

    def _get_implementation_name(self) -> str:
        return "my_quic"

    def _get_binary_name(self) -> str:
        return "my_quic_server"

    def _get_server_specific_args(self, **kwargs) -> List[str]:
        port = kwargs.get("port", 4443)
        cert = kwargs.get("cert_file", "")
        return ["-p", str(port), "-c", cert] if cert else ["-p", str(port)]

    def _get_client_specific_args(self, **kwargs) -> List[str]:
        host = kwargs.get("host", "localhost")
        port = kwargs.get("port", 4443)
        return [host, str(port)]

    def generate_deployment_commands(self) -> str:
        return f"{self._get_binary_name()} -p 4443"

    def _do_prepare(self, plugin_manager=None):
        # Implementation-specific preparation logic
        pass

    # All common functionality inherited automatically:
    # - generate_run_command()
    # - _extract_common_params()
    # - _build_server_args() / _build_client_args()
    # - Event emission and error handling
    # - Docker integration and template rendering
```

<!-- src: /panther/plugins/services/services_interface.py -->

## Service Plugin Interfaces

All service plugins must implement the appropriate interface based on their category:

### Common Service Interface

```python
from panther.plugins.plugin_interface import PluginInterface

class ServiceInterface(PluginInterface):
    """Base interface for all service plugins."""

    def initialize(self, config):
        """Initialize the service with configuration."""
        pass

    def start(self):
        """Start the service."""
        pass

    def stop(self):
        """Stop the service."""
        pass

    def restart(self):
        """Restart the service."""
        pass

    def get_status(self):
        """Get the status of the service."""
        pass

    def execute(self):
        """Execute the service's main functionality."""
        pass

    def cleanup(self):
        """Clean up resources."""
        pass
```

### Implementation Manager Interface

For IUT services:

```python
from panther.plugins.services.services_interface import IServiceManager

class IImplementationManager(IServiceManager):
    """Interface for implementation under test managers."""

    def is_tester(self):
        """Returns False indicating this is not a tester."""
        return False

    def get_implementation_version(self):
        """Get the version of the implementation."""
        pass

    def get_implementation_capabilities(self):
        """Get the capabilities of the implementation."""
        pass
```

### Tester Manager Interface

For tester services:

```python
from panther.plugins.services.services_interface import IServiceManager

class ITesterManager(IServiceManager):
    """Interface for tester service managers."""

    def is_tester(self):
        """Returns True indicating this is a tester."""
        return True

    def run_test(self, test_case):
        """Run a specific test case."""
        pass

    def get_test_results(self):
        """Get the results of the tests."""
        pass
```

### Modern Service Manager Creation Patterns

#### Creating QUIC Service Managers

For QUIC implementations, inherit from the appropriate base class:

```python
# For Python implementations (aioquic)
from panther.plugins.services.base.python_quic_base import PythonQUICServiceManager

class AioquicServiceManager(PythonQUICServiceManager):
    def _get_python_module(self) -> str:
        return "aioquic.quic.server"

    def _get_async_patterns(self) -> Dict[str, str]:
        return {"event_loop": "asyncio", "concurrency": "async/await"}

# For Rust implementations (quiche, quinn)
from panther.plugins.services.base.rust_quic_base import RustQUICServiceManager

class QuicheServiceManager(RustQUICServiceManager):
    def _get_cargo_features(self) -> List[str]:
        return ["boring-sys", "ffi"]

    def _get_rust_patterns(self) -> Dict[str, str]:
        return {"async_runtime": "tokio", "memory_safety": "strict"}

# For C/Go implementations (picoquic, lsquic)
from panther.plugins.services.base.quic_service_base import BaseQUICServiceManager

class PicoquicServiceManager(BaseQUICServiceManager):
    def _get_implementation_name(self) -> str:
        return "picoquic"

    def _get_binary_name(self) -> str:
        return "picoquicdemo"
```

#### Event Integration in Service Managers

All modern service managers automatically integrate with the event system:

```python
class ModernServiceManager(BaseQUICServiceManager):
    def _do_prepare(self, plugin_manager=None):
        # Emit custom preparation event
        self.emit_event(ServicePreparationEvent(
            service_name=self._get_implementation_name(),
            preparation_type="custom_setup"
        ))

        # Custom preparation logic
        self._setup_custom_configuration()

        # Emit completion event
        self.emit_event(ServiceReadyEvent(
            service_name=self._get_implementation_name()
        ))
```

### Modern Testing Patterns with Inheritance Architecture

#### Unit Testing Base Class Functionality

```python
# tests/unit/test_service_managers/test_modern_quic_manager.py
import pytest
from unittest.mock import MagicMock, patch
from panther.plugins.services.base.quic_service_base import BaseQUICServiceManager

class TestQuicServiceManager(BaseQUICServiceManager):
    """Test implementation for unit testing."""

    def _get_implementation_name(self) -> str:
        return "test_quic"

    def _get_binary_name(self) -> str:
        return "test_binary"

    def _get_server_specific_args(self, **kwargs) -> List[str]:
        return ["-p", str(kwargs.get("port", 4443))]

    def _get_client_specific_args(self, **kwargs) -> List[str]:
        return [kwargs.get("host", "localhost"), str(kwargs.get("port", 4443))]

    def generate_deployment_commands(self) -> str:
        return "test_binary -p 4443"

    def _do_prepare(self, plugin_manager=None):
        pass

class TestBaseQUICServiceManager:

    def test_command_generation_inheritance(self):
        """Test that base class provides command generation."""
        manager = TestQuicServiceManager()

        # Test that inherited method works
        command = manager.generate_run_command(role="server", port=8443)
        assert "test_binary" in command
        assert "8443" in command

    def test_event_emission_inheritance(self):
        """Test that base class provides event emission."""
        manager = TestQuicServiceManager()

        with patch.object(manager, 'emit_event') as mock_emit:
            manager.generate_run_command(role="server")
            # Verify events were emitted
            mock_emit.assert_called()

    def test_parameter_extraction_inheritance(self):
        """Test that base class provides parameter extraction."""
        manager = TestQuicServiceManager()

        params = manager._extract_common_params(
            port=9443,
            cert_file="/certs/test.crt",
            host="testhost"
        )

        assert params["port"] == 9443
        assert params["cert_file"] == "/certs/test.crt"
        assert params["host"] == "testhost"

    def test_docker_integration_inheritance(self):
        """Test that Docker integration is provided by base class."""
        manager = TestQuicServiceManager()

        # Test that Docker methods are available
        assert hasattr(manager, 'generate_dockerfile_content')
        assert callable(manager.generate_dockerfile_content)
```

#### Integration Testing with Modern Architecture

```python
# tests/integration/test_inheritance_integration.py
import pytest
from panther.plugins.services.base.quic_service_base import BaseQUICServiceManager
from panther.core.events.service.events import ServiceInitializationEvent

class TestInheritanceIntegration:

    @pytest.mark.integration
    def test_full_service_lifecycle_with_inheritance(self):
        """Test complete service lifecycle using inheritance."""

        class IntegrationTestManager(BaseQUICServiceManager):
            def _get_implementation_name(self) -> str:
                return "integration_test"

            def _get_binary_name(self) -> str:
                return "echo"  # Use echo for testing

            def _get_server_specific_args(self, **kwargs) -> List[str]:
                return ["server_test"]

            def _get_client_specific_args(self, **kwargs) -> List[str]:
                return ["client_test"]

            def generate_deployment_commands(self) -> str:
                return "echo deployment"

            def _do_prepare(self, plugin_manager=None):
                pass

        manager = IntegrationTestManager()
        events_captured = []

        def capture_event(event):
            events_captured.append(event)

        # Mock event emission
        manager.emit_event = capture_event

        # Test command generation
        server_cmd = manager.generate_run_command(role="server", port=4443)
        client_cmd = manager.generate_run_command(role="client", host="localhost", port=4443)

        # Verify commands were generated
        assert "echo" in server_cmd
        assert "server_test" in server_cmd
        assert "echo" in client_cmd
        assert "client_test" in client_cmd

        # Verify events were emitted
        assert len(events_captured) > 0

    @pytest.mark.integration
    def test_specialized_base_class_integration(self):
        """Test that specialized base classes work correctly."""
        from panther.plugins.services.base.python_quic_base import PythonQUICServiceManager

        class PythonTestManager(PythonQUICServiceManager):
            def _get_implementation_name(self) -> str:
                return "python_test"

            def _get_binary_name(self) -> str:
                return "python"

            def _get_python_module(self) -> str:
                return "test_module"

        manager = PythonTestManager()

        # Test that Python-specific functionality is available
        command = manager.generate_run_command(role="server")
        assert "python" in command

        # Test that base QUIC functionality is inherited
        assert hasattr(manager, '_extract_common_params')
        assert callable(manager._extract_common_params)
```

## Creating a New Service Plugin

### 1. Choose Service Type

Determine whether your service is an Implementation Under Test (IUT) or a Tester.

### 2. Set Up the Plugin Directory

Create a directory for your service in the appropriate location:

```
# For IUT:
plugins/services/iut/<protocol_name>/<implementation_name>/
├── __init__.py
├── plugin.py           # Main service implementation
├── config_schema.py    # Configuration schema
├── README.md           # Service documentation
└── tests/              # Service tests
    └── test_plugin.py

# For Tester:
plugins/services/testers/<tester_name>/
├── __init__.py
├── plugin.py
├── config_schema.py
├── README.md
└── tests/
```

### 3. Implement the Service Interface

#### For IUT Service

```python
# plugins/services/iut/<protocol>/<implementation>/plugin.py
from panther.plugins.services.iut.implementation_interface import IImplementationManager

class MyImplementation(IImplementationManager):
    """My custom implementation under test."""

    def initialize(self, config):
        """Initialize the implementation with configuration."""
        self.config = config
        # Implementation initialization

    def start(self):
        """Start the implementation."""
        # Service startup logic
        pass

    def stop(self):
        """Stop the implementation."""
        # Service shutdown logic
        pass

    def execute(self):
        """Execute the implementation's main functionality."""
        # Implementation execution logic
        pass

    def cleanup(self):
        """Clean up resources."""
        # Release resources
        pass
```

#### For Tester Service

```python
# plugins/services/testers/<tester_name>/plugin.py
from panther.plugins.services.testers.tester_interface import ITesterManager

class MyTester(ITesterManager):
    """My custom tester service."""

    def initialize(self, config):
        """Initialize the tester with configuration."""
        self.config = config
        self.test_results = {}
        # Tester initialization

    def run_test(self, test_case):
        """Run a specific test case."""
        # Test execution logic
        pass

    def get_test_results(self):
        """Get the test results."""
        return self.test_results

    def execute(self):
        """Execute the tester's main functionality."""
        # Tester execution logic
        pass

    def cleanup(self):
        """Clean up resources."""
        # Release resources
        pass
```

### 4. Define Configuration Schema

#### For IUT Service

```python
# plugins/services/iut/<protocol>/<implementation>/config_schema.py
from dataclasses import dataclass, field
from panther.config.core.models import ImplementationConfig, ImplementationType

@dataclass
class MyImplementationConfig(ImplementationConfig):
    """Configuration for my implementation."""
    name: str = "my_implementation"  # Implementation name
    type: ImplementationType = ImplementationType.iut
    # Implementation-specific parameters
    port: int = 8080
    log_level: str = "info"
    extra_args: list[str] = field(default_factory=list)
```

#### For Tester Service

```python
# plugins/services/testers/<tester_name>/config_schema.py
from dataclasses import dataclass, field
from panther.plugins.services.testers.config_schema import TesterConfig, TesterType

@dataclass
class MyTesterConfig(TesterConfig):
    """Configuration for my tester."""
    name: str = "my_tester"  # Tester name
    type: TesterType = TesterType.tester
    # Tester-specific parameters
    test_suite: str = "default"
    timeout_seconds: int = 60
    verbose: bool = False
```

### 5. Register Your Service Plugin

Make your service discoverable by updating your `__init__.py`:

```python
# plugins/services/iut/<protocol>/<implementation>/__init__.py
# or
# plugins/services/testers/<tester_name>/__init__.py
from .plugin import MyImplementation  # or MyTester

__all__ = ["MyImplementation"]  # or ["MyTester"]
```

### 6. Create Tests

Write tests to verify your service functions correctly:

```python
# plugins/services/iut/<protocol>/<implementation>/tests/test_plugin.py
# or
# plugins/services/testers/<tester_name>/tests/test_plugin.py
import pytest
from panther.plugins.services.iut.<protocol>.<implementation>.plugin import MyImplementation

def test_service_initialization():
    service = MyImplementation()
    config = {"port": 8080}
    service.initialize(config)
    # Assert expected initialization behavior

def test_service_execution():
    service = MyImplementation()
    service.initialize({"port": 8080})
    service.start()
    # Assert service started correctly
    service.stop()
    service.cleanup()
```

### 7. Document Your Service

Create a README.md file using the [plugin template](panther/plugins/plugin_template.md) that includes:

- Service purpose and capabilities
- Configuration options and examples
- Integration with protocols and environments
- Testing and troubleshooting guidance

## Best Practices for Service Plugins

1. **Separation of Concerns**: Keep service logic separate from protocol and environment specifics
2. **Resource Management**: Properly release all resources in the cleanup method
3. **Error Handling**: Provide clear error messages and graceful failure handling
4. **Configuration Validation**: Thoroughly validate all input parameters
5. **Logging**: Include adequate logging for debugging and monitoring
6. **Documentation**: Document all configuration options and usage examples

## Service Integration

Services need to integrate with other PANTHER components:

1. **Protocol Integration**: Connect services to appropriate protocols
2. **Environment Integration**: Ensure services work in different execution and network environments
3. **Test Framework Integration**: Provide proper metrics and results collection

## Documentation Verification

Ensure all service documentation includes source references:

```markdown
This service implements the QUIC protocol according to RFC9000.
<!-- src: /panther/plugins/services/iut/quic/picoquic/plugin.py -->
```
