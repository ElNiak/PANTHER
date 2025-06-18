# Protocol Plugin Architecture - Concrete Implementation Plan

## Executive Summary

This document provides a step-by-step implementation plan to transform PANTHER's protocol system from passive configuration holders into active plugins that manage protocol-specific command building, validation, and environment integration.

## Current Architecture Analysis

### What Exists Now

1. **Protocol Configuration Files**:
   - `/panther/plugins/protocols/client_server/quic/config_schema.py` - Only schemas
   - `/panther/plugins/protocols/client_server/http/config_schema.py` - Only schemas
   - `/panther/plugins/protocols/protocol_interface.py` - Unused IProtocolManager

2. **Protocol Logic Scattered In**:
   - `/panther/plugins/services/base/quic_service_base.py` - QUIC command building
   - `/panther/plugins/services/base/http_service_base.py` - HTTP command building
   - `/panther/plugins/services/base/service_command_builder.py` - Generic protocol params

3. **Integration Points**:
   - `test_case_impl.py:989` - Protocol passed to service creation
   - `services_interface.py:61` - Protocol stored as service_protocol
   - `docker_compose.yml.jinja:6` - Protocol version used in image naming

### Key Findings

1. **Protocols are used for**:
   - Directory organization (services/iut/{protocol}/{implementation})
   - Plugin filtering (supported_protocols)
   - Command parameter addition (ALPN, version)
   - Docker image tagging

2. **No active protocol behavior** - protocols don't:
   - Build commands
   - Validate configurations
   - Specify environment requirements
   - Handle protocol-specific logic

## Implementation Plan

### Phase 1: Create Active Protocol Plugin System (Week 1)

#### TODO 1.1: Create New Protocol Plugin Interface
**File**: `/panther/plugins/protocols/protocol_plugin_interface.py` (NEW)

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from panther.plugins.protocols.command_builder_interface import IProtocolCommandBuilder

class IProtocolPlugin(ABC):
    """Active protocol plugin that manages protocol-specific behavior."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self._get_protocol_name()
        self.version = config.get('version', 'default')
    
    @abstractmethod
    def _get_protocol_name(self) -> str:
        """Return the protocol name (e.g., 'quic', 'http')."""
        pass
    
    @abstractmethod
    def get_command_builder(self) -> 'IProtocolCommandBuilder':
        """Return protocol-specific command builder."""
        pass
    
    @abstractmethod
    def get_network_requirements(self) -> Dict[str, Any]:
        """Return network environment requirements."""
        # Example: {"ports": {"udp": [443], "tcp": []}, "protocols": ["UDP"]}
        pass
    
    @abstractmethod
    def get_execution_requirements(self) -> Dict[str, Any]:
        """Return execution environment requirements."""
        # Example: {"trace_syscalls": ["sendto", "recvfrom"], "profile_functions": ["crypto_*"]}
        pass
    
    @abstractmethod
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Validate protocol-specific configuration."""
        pass
    
    @abstractmethod
    def get_default_parameters(self, role: str) -> Dict[str, Any]:
        """Return default parameters for given role."""
        pass
    
    def get_docker_image_tag(self, implementation: str, version: str) -> str:
        """Generate Docker image tag for this protocol."""
        return f"{implementation}_{self.name}_{version}:latest"
    
    def get_output_patterns(self) -> List[Tuple[str, str]]:
        """Return expected output file patterns for this protocol."""
        return []
```

#### TODO 1.2: Create Protocol Command Builder Interface
**File**: `/panther/plugins/protocols/command_builder_interface.py` (NEW)

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class IProtocolCommandBuilder(ABC):
    """Interface for protocol-specific command building."""
    
    @abstractmethod
    def build_server_args(self, params: Dict[str, Any]) -> List[str]:
        """Build protocol-specific server arguments."""
        pass
    
    @abstractmethod
    def build_client_args(self, params: Dict[str, Any]) -> List[str]:
        """Build protocol-specific client arguments."""
        pass
    
    @abstractmethod
    def get_required_parameters(self, role: str) -> List[str]:
        """Return required parameters for role."""
        pass
    
    @abstractmethod
    def get_optional_parameters(self, role: str) -> List[str]:
        """Return optional parameters for role."""
        pass
    
    def validate_parameters(self, params: Dict[str, Any], role: str) -> bool:
        """Validate that all required parameters are present."""
        required = self.get_required_parameters(role)
        return all(param in params for param in required)
```

#### TODO 1.3: Update Existing Protocol Interface
**File**: `/panther/plugins/protocols/protocol_interface.py` (MODIFY)

```python
# Mark IProtocolManager as deprecated
import warnings
from panther.plugins.protocols.protocol_plugin_interface import IProtocolPlugin

class IProtocolManager(IPlugin):
    """
    DEPRECATED: Use IProtocolPlugin instead.
    This class is kept for backward compatibility only.
    """
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "IProtocolManager is deprecated. Use IProtocolPlugin instead.",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__(*args, **kwargs)
```

### Phase 2: Implement Protocol Plugins (Week 2)

#### TODO 2.1: Implement QUIC Protocol Plugin
**File**: `/panther/plugins/protocols/client_server/quic/quic_protocol.py` (NEW)

```python
from typing import Dict, Any, List, Tuple
from panther.plugins.protocols.protocol_plugin_interface import IProtocolPlugin
from panther.plugins.protocols.client_server.quic.quic_command_builder import QUICCommandBuilder

class QUICProtocolPlugin(IProtocolPlugin):
    """QUIC protocol plugin implementation."""
    
    def _get_protocol_name(self) -> str:
        return "quic"
    
    def get_command_builder(self) -> QUICCommandBuilder:
        return QUICCommandBuilder()
    
    def get_network_requirements(self) -> Dict[str, Any]:
        return {
            "ports": {
                "udp": [443, 4443],  # QUIC typically uses UDP
                "tcp": []  # No TCP needed
            },
            "protocols": ["UDP"],
            "features": ["nat_traversal", "connection_migration"]
        }
    
    def get_execution_requirements(self) -> Dict[str, Any]:
        return {
            "trace_syscalls": ["sendto", "recvfrom", "sendmsg", "recvmsg"],
            "profile_functions": ["crypto_*", "packet_*"],
            "capture_packets": True,
            "capture_filter": "udp port 443 or udp port 4443"
        }
    
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        # Validate QUIC-specific configuration
        if 'version' in config:
            valid_versions = ['rfc9000', 'draft-29', 'draft-32']
            if config['version'] not in valid_versions:
                return False
        return True
    
    def get_default_parameters(self, role: str) -> Dict[str, Any]:
        defaults = {
            "port": 4443,
            "alpn": "hq-interop",
            "version": "rfc9000",
            "cert_dir": "/opt/certs",
            "log_dir": "/app/logs"
        }
        
        if role == "server":
            defaults.update({
                "key_file": "/opt/certs/key.pem",
                "cert_file": "/opt/certs/cert.pem"
            })
        else:  # client
            defaults.update({
                "host": "localhost",
                "ticket_file": "/opt/ticket/ticket.key"
            })
        
        return defaults
    
    def get_output_patterns(self) -> List[Tuple[str, str]]:
        return [
            ("qlog", "*.qlog"),
            ("keys", "*keys.log"),
            ("sslkeylog", "sslkeylogfile.txt"),
            ("pcap", "{service_name}.pcap"),
            ("congestion", "*congestion*.log")
        ]
```

#### TODO 2.2: Create QUIC Command Builder
**File**: `/panther/plugins/protocols/client_server/quic/quic_command_builder.py` (NEW)

```python
# Move logic from quic_service_base.py
from typing import Dict, Any, List
from panther.plugins.protocols.command_builder_interface import IProtocolCommandBuilder

class QUICCommandBuilder(IProtocolCommandBuilder):
    """QUIC-specific command builder."""
    
    def build_server_args(self, params: Dict[str, Any]) -> List[str]:
        """Build QUIC server arguments."""
        args = []
        
        # Port binding
        args.extend(["-p", str(params.get("port", 4443))])
        
        # Certificates
        if "cert_file" in params:
            args.extend(["-c", params["cert_file"]])
        if "key_file" in params:
            args.extend(["-k", params["key_file"]])
        
        # ALPN
        if "alpn" in params:
            args.extend(["-a", params["alpn"]])
        
        # Version
        if "version" in params:
            args.extend(["-v", params["version"]])
        
        # Logging
        if "log_file" in params:
            args.extend(["-l", params["log_file"]])
        
        return args
    
    def build_client_args(self, params: Dict[str, Any]) -> List[str]:
        """Build QUIC client arguments."""
        args = []
        
        # Target
        host = params.get("host", "localhost")
        port = params.get("port", 4443)
        args.append(f"{host}:{port}")
        
        # ALPN
        if "alpn" in params:
            args.extend(["-a", params["alpn"]])
        
        # Version
        if "version" in params:
            args.extend(["-v", params["version"]])
        
        # 0-RTT
        if "ticket_file" in params:
            args.extend(["-T", params["ticket_file"]])
        
        # Logging
        if "log_file" in params:
            args.extend(["-l", params["log_file"]])
        
        return args
    
    def get_required_parameters(self, role: str) -> List[str]:
        if role == "server":
            return ["port"]
        else:  # client
            return ["host", "port"]
    
    def get_optional_parameters(self, role: str) -> List[str]:
        common = ["alpn", "version", "log_file"]
        if role == "server":
            return common + ["cert_file", "key_file"]
        else:  # client
            return common + ["ticket_file"]
```

#### TODO 2.3: Implement HTTP Protocol Plugin
**File**: `/panther/plugins/protocols/client_server/http/http_protocol.py` (NEW)

```python
# Similar structure to QUIC but for HTTP
from typing import Dict, Any, List, Tuple
from panther.plugins.protocols.protocol_plugin_interface import IProtocolPlugin
from panther.plugins.protocols.client_server.http.http_command_builder import HTTPCommandBuilder

class HTTPProtocolPlugin(IProtocolPlugin):
    """HTTP protocol plugin implementation."""
    
    def _get_protocol_name(self) -> str:
        return "http"
    
    def get_command_builder(self) -> HTTPCommandBuilder:
        return HTTPCommandBuilder()
    
    def get_network_requirements(self) -> Dict[str, Any]:
        return {
            "ports": {
                "tcp": [80, 443, 8080],
                "udp": []  # UDP only for HTTP/3
            },
            "protocols": ["TCP"],
            "features": ["keep_alive", "pipelining"]
        }
    
    def get_execution_requirements(self) -> Dict[str, Any]:
        return {
            "trace_syscalls": ["send", "recv", "connect", "accept"],
            "profile_functions": ["parse_*", "handle_request"],
            "capture_packets": True,
            "capture_filter": "tcp port 80 or tcp port 443"
        }
    
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        if 'version' in config:
            valid_versions = ['1.0', '1.1', '2.0', '3.0']
            if config['version'] not in valid_versions:
                return False
        return True
    
    def get_default_parameters(self, role: str) -> Dict[str, Any]:
        defaults = {
            "port": 80,
            "version": "1.1",
            "timeout": 30,
            "keep_alive": False
        }
        
        if role == "server":
            defaults.update({
                "bind": "0.0.0.0",
                "max_connections": 100
            })
        else:  # client
            defaults.update({
                "host": "localhost",
                "method": "GET",
                "url_path": "/"
            })
        
        return defaults
    
    def get_output_patterns(self) -> List[Tuple[str, str]]:
        return [
            ("access_log", "access.log"),
            ("error_log", "error.log"),
            ("har", "*.har"),
            ("tcpdump", "*.pcap")
        ]
```

### Phase 3: Refactor Service Base Classes (Week 3)

#### TODO 3.1: Create Generic Protocol-Aware Service Base
**File**: `/panther/plugins/services/base/protocol_aware_service_base.py` (NEW)

```python
from typing import Dict, Any, Optional, TYPE_CHECKING
from abc import abstractmethod
from panther.plugins.services.services_interface import IServiceManager

if TYPE_CHECKING:
    from panther.plugins.protocols.protocol_plugin_interface import IProtocolPlugin
    from panther.plugins.plugin_manager import PluginManager

class ProtocolAwareServiceManager(IServiceManager):
    """Base service manager that delegates protocol logic to protocol plugins."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.protocol_plugin: Optional['IProtocolPlugin'] = None
        self.command_builder = None
        self._load_protocol_plugin()
    
    def _load_protocol_plugin(self):
        """Load the protocol plugin for this service."""
        if hasattr(self, 'service_protocol') and self.service_protocol:
            protocol_name = self.service_protocol.name
            # This will be loaded by plugin manager
            # For now, we'll import directly
            self._initialize_protocol_plugin(protocol_name)
    
    def _initialize_protocol_plugin(self, protocol_name: str):
        """Initialize the appropriate protocol plugin."""
        # This will be replaced with plugin manager loading
        if protocol_name == "quic":
            from panther.plugins.protocols.client_server.quic.quic_protocol import QUICProtocolPlugin
            self.protocol_plugin = QUICProtocolPlugin(self.service_protocol.__dict__)
        elif protocol_name == "http":
            from panther.plugins.protocols.client_server.http.http_protocol import HTTPProtocolPlugin
            self.protocol_plugin = HTTPProtocolPlugin(self.service_protocol.__dict__)
        
        if self.protocol_plugin:
            self.command_builder = self.protocol_plugin.get_command_builder()
    
    def generate_run_command(self, **kwargs) -> str:
        """Generate run command using protocol plugin."""
        if not self.protocol_plugin or not self.command_builder:
            # Fallback to old method
            return super().generate_run_command(**kwargs)
        
        # Get default parameters from protocol
        params = self.protocol_plugin.get_default_parameters(kwargs.get("role", "server"))
        
        # Override with provided parameters
        params.update(kwargs)
        
        # Add implementation-specific parameters
        impl_params = self._get_implementation_parameters(**kwargs)
        params.update(impl_params)
        
        # Build command arguments
        if params["role"] == "server":
            args = self.command_builder.build_server_args(params)
        else:
            args = self.command_builder.build_client_args(params)
        
        # Get binary and finalize command
        binary = self._get_binary_path()
        command_parts = [binary] + args
        
        return " ".join(command_parts)
    
    @abstractmethod
    def _get_implementation_parameters(self, **kwargs) -> Dict[str, Any]:
        """Get implementation-specific parameters."""
        pass
    
    @abstractmethod
    def _get_binary_path(self) -> str:
        """Get the binary path for this implementation."""
        pass
    
    def get_output_patterns(self) -> List[Tuple[str, str]]:
        """Get output patterns from protocol plugin."""
        patterns = super().get_output_patterns()
        
        if self.protocol_plugin:
            protocol_patterns = self.protocol_plugin.get_output_patterns()
            patterns.extend(protocol_patterns)
        
        return patterns
```

#### TODO 3.2: Migrate PicoQUIC to Use Protocol Plugin
**File**: `/panther/plugins/services/iut/quic/picoquic/picoquic.py` (MODIFY)

```python
# Simplified version using protocol plugin
from panther.plugins.services.base.protocol_aware_service_base import ProtocolAwareServiceManager

class PicoquicServiceManager(ProtocolAwareServiceManager):
    """Picoquic service manager using protocol plugin."""
    
    def _get_implementation_name(self) -> str:
        return "picoquic"
    
    def _get_binary_name(self) -> str:
        return "picoquicdemo"
    
    def _get_binary_path(self) -> str:
        return f"{self.working_dir}/{self._get_binary_name()}"
    
    def _get_implementation_parameters(self, **kwargs) -> Dict[str, Any]:
        """Get PicoQUIC-specific parameters."""
        params = {}
        
        # PicoQUIC-specific options
        if hasattr(self.service_config_to_test, "implementation"):
            impl_config = self.service_config_to_test.implementation
            # Add any PicoQUIC-specific parameters here
        
        return params
    
    def generate_deployment_commands(self) -> str:
        """Generate deployment commands."""
        # Use protocol plugin to generate command
        return self.generate_run_command(role=self.service_config_to_test.protocol.role)
```

### Phase 4: Integrate with Environments (Week 4)

#### TODO 4.1: Update Network Environment Base
**File**: `/panther/plugins/environments/network_environment/base_network_environment.py` (MODIFY)

```python
def setup_environment(self, services_managers, test_config, global_config, timestamp, plugin_manager, execution_environment):
    """Setup network environment with protocol awareness."""
    # ... existing code ...
    
    # Collect protocol requirements from all services
    network_requirements = self._collect_protocol_requirements(services_managers)
    
    # Apply protocol-specific network configuration
    self._apply_protocol_network_config(network_requirements)
    
    # ... rest of existing code ...

def _collect_protocol_requirements(self, services_managers) -> Dict[str, Any]:
    """Collect network requirements from protocol plugins."""
    all_requirements = {
        "ports": {"tcp": set(), "udp": set()},
        "protocols": set(),
        "features": set()
    }
    
    for service_manager in services_managers:
        if hasattr(service_manager, 'protocol_plugin') and service_manager.protocol_plugin:
            reqs = service_manager.protocol_plugin.get_network_requirements()
            
            # Merge requirements
            for proto in ["tcp", "udp"]:
                if proto in reqs.get("ports", {}):
                    all_requirements["ports"][proto].update(reqs["ports"][proto])
            
            all_requirements["protocols"].update(reqs.get("protocols", []))
            all_requirements["features"].update(reqs.get("features", []))
    
    # Convert sets to lists for serialization
    all_requirements["ports"]["tcp"] = list(all_requirements["ports"]["tcp"])
    all_requirements["ports"]["udp"] = list(all_requirements["ports"]["udp"])
    all_requirements["protocols"] = list(all_requirements["protocols"])
    all_requirements["features"] = list(all_requirements["features"])
    
    return all_requirements

def _apply_protocol_network_config(self, requirements: Dict[str, Any]):
    """Apply protocol-specific network configuration."""
    self.logger.info(f"Applying protocol network requirements: {requirements}")
    
    # This would be implemented by specific network environments
    # For example, docker_compose would add port mappings
    # shadow_ns would configure appropriate network simulation
```

#### TODO 4.2: Update Execution Environment Integration
**File**: `/panther/plugins/environments/execution_environment/base_execution_environment.py` (MODIFY)

```python
def wrap_command(self, command: str, service_name: str, service_manager=None) -> str:
    """Wrap command with execution environment specific settings."""
    # Get protocol-specific execution requirements
    if service_manager and hasattr(service_manager, 'protocol_plugin'):
        exec_reqs = service_manager.protocol_plugin.get_execution_requirements()
        
        # Apply protocol-specific wrapping
        command = self._apply_protocol_requirements(command, exec_reqs)
    
    # Continue with normal wrapping
    return super().wrap_command(command, service_name)

def _apply_protocol_requirements(self, command: str, requirements: Dict[str, Any]) -> str:
    """Apply protocol-specific execution requirements."""
    # This would be implemented by specific execution environments
    # For example:
    # - strace would add syscalls from requirements["trace_syscalls"]
    # - gperf would focus on requirements["profile_functions"]
    return command
```

### Phase 5: Update Configuration Flow

#### TODO 5.1: Create Protocol Factory
**File**: `/panther/plugins/protocols/protocol_factory.py` (NEW)

```python
from typing import Dict, Any, Optional
from panther.plugins.protocols.protocol_plugin_interface import IProtocolPlugin

class ProtocolFactory:
    """Factory for creating protocol plugin instances."""
    
    _protocol_registry: Dict[str, type] = {}
    
    @classmethod
    def register_protocol(cls, name: str, protocol_class: type):
        """Register a protocol plugin class."""
        cls._protocol_registry[name] = protocol_class
    
    @classmethod
    def create_protocol(cls, name: str, config: Dict[str, Any]) -> Optional[IProtocolPlugin]:
        """Create a protocol plugin instance."""
        protocol_class = cls._protocol_registry.get(name)
        if protocol_class:
            return protocol_class(config)
        return None
    
    @classmethod
    def get_available_protocols(cls) -> List[str]:
        """Get list of available protocols."""
        return list(cls._protocol_registry.keys())

# Auto-register protocols
def _auto_register_protocols():
    """Auto-register built-in protocols."""
    from panther.plugins.protocols.client_server.quic.quic_protocol import QUICProtocolPlugin
    from panther.plugins.protocols.client_server.http.http_protocol import HTTPProtocolPlugin
    from panther.plugins.protocols.client_server.minip.minip_protocol import MiniPProtocolPlugin
    
    ProtocolFactory.register_protocol("quic", QUICProtocolPlugin)
    ProtocolFactory.register_protocol("http", HTTPProtocolPlugin)
    ProtocolFactory.register_protocol("minip", MiniPProtocolPlugin)

_auto_register_protocols()
```

#### TODO 5.2: Update Plugin Manager
**File**: `/panther/plugins/plugin_manager.py` (MODIFY)

```python
def create_service_manager(self, protocol, implementation, implementation_dir, service_config_to_test, event_manager=None, emitter_registry=None):
    """Create service manager with protocol plugin support."""
    # ... existing code ...
    
    # Load protocol plugin first
    protocol_plugin = self._load_protocol_plugin(protocol)
    
    # Pass protocol plugin to service manager
    service_manager = service_factory.create_service_manager(
        service_type=service_type_str,
        protocol=protocol,
        protocol_plugin=protocol_plugin,  # NEW
        implementation=implementation_obj,
        implementation_dir=implementation_dir,
        service_config_to_test=service_config_to_test,
        event_manager=event_manager or self.event_manager,
        emitter_registry=emitter_registry
    )
    
    return service_manager

def _load_protocol_plugin(self, protocol_config) -> Optional[IProtocolPlugin]:
    """Load protocol plugin based on configuration."""
    from panther.plugins.protocols.protocol_factory import ProtocolFactory
    
    if not protocol_config:
        return None
    
    protocol_name = protocol_config.name
    protocol_dict = protocol_config.__dict__ if hasattr(protocol_config, '__dict__') else {}
    
    return ProtocolFactory.create_protocol(protocol_name, protocol_dict)
```

### Phase 6: Migration and Cleanup

#### TODO 6.1: Create Migration Script
**File**: `/dev/scripts/migrate_to_protocol_plugins.py` (NEW)

```python
#!/usr/bin/env python3
"""Script to migrate existing service implementations to use protocol plugins."""

import os
import re
from pathlib import Path

def migrate_service_manager(file_path: Path):
    """Migrate a service manager to use protocol plugins."""
    content = file_path.read_text()
    
    # Replace base class inheritance
    content = re.sub(
        r'from panther\.plugins\.services\.base\.quic_service_base import BaseQUICServiceManager',
        'from panther.plugins.services.base.protocol_aware_service_base import ProtocolAwareServiceManager',
        content
    )
    
    content = re.sub(
        r'class (\w+)\(BaseQUICServiceManager\):',
        r'class \1(ProtocolAwareServiceManager):',
        content
    )
    
    # Remove protocol-specific methods that are now in protocol plugin
    methods_to_remove = [
        '_extract_common_params',
        '_build_server_args', 
        '_build_client_args',
        '_build_common_server_args',
        '_build_common_client_args'
    ]
    
    for method in methods_to_remove:
        # Remove method definition
        content = re.sub(
            rf'def {method}\(.*?\):\n(?:.*?\n)*?(?=\n    def|\nclass|\Z)',
            '',
            content,
            flags=re.MULTILINE | re.DOTALL
        )
    
    # Update generate_run_command to use simplified version
    # ... more migration logic ...
    
    # Write back
    file_path.write_text(content)
    print(f"Migrated: {file_path}")

def main():
    """Run migration on all service implementations."""
    services_dir = Path("panther/plugins/services/iut")
    
    for impl_file in services_dir.rglob("*.py"):
        if impl_file.name not in ["__init__.py", "config_schema.py"]:
            try:
                migrate_service_manager(impl_file)
            except Exception as e:
                print(f"Failed to migrate {impl_file}: {e}")

if __name__ == "__main__":
    main()
```

#### TODO 6.2: Remove Legacy Code
**File**: `/dev/scripts/cleanup_legacy_protocol_code.py` (NEW)

```python
#!/usr/bin/env python3
"""Script to remove legacy protocol code after migration."""

from pathlib import Path

# Files to remove
FILES_TO_REMOVE = [
    "panther/plugins/services/base/quic_service_base.py",
    "panther/plugins/services/base/http_service_base.py",
    "panther/plugins/services/base/minip_service_base.py",
    "panther/plugins/protocols/client_server/client_server.py",
    "panther/plugins/protocols/peer_to_peer/peer_to_peer.py"
]

# Files to archive
FILES_TO_ARCHIVE = [
    "panther/plugins/services/base/*_service_base.py"
]

def archive_file(file_path: Path):
    """Archive a file to backup directory."""
    backup_dir = Path("dev/backup/protocol_migration")
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    relative_path = file_path.relative_to(Path.cwd())
    backup_path = backup_dir / relative_path
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    
    file_path.rename(backup_path)
    print(f"Archived: {file_path} -> {backup_path}")

def main():
    """Clean up legacy files."""
    # Archive service base classes
    for pattern in FILES_TO_ARCHIVE:
        for file_path in Path(".").glob(pattern):
            if file_path.exists():
                archive_file(file_path)
    
    # Remove empty protocol files
    for file_name in FILES_TO_REMOVE:
        file_path = Path(file_name)
        if file_path.exists():
            file_path.unlink()
            print(f"Removed: {file_path}")

if __name__ == "__main__":
    main()
```

### Phase 7: Testing Strategy

#### TODO 7.1: Create Protocol Plugin Tests
**File**: `/tests/unit/test_plugins/test_protocols/test_protocol_plugins.py` (NEW)

```python
import pytest
from panther.plugins.protocols.client_server.quic.quic_protocol import QUICProtocolPlugin
from panther.plugins.protocols.protocol_factory import ProtocolFactory

class TestProtocolPlugins:
    """Test protocol plugin functionality."""
    
    def test_quic_protocol_plugin_creation(self):
        """Test QUIC protocol plugin can be created."""
        plugin = QUICProtocolPlugin({"version": "rfc9000"})
        assert plugin._get_protocol_name() == "quic"
        assert plugin.command_builder is not None
    
    def test_quic_command_builder(self):
        """Test QUIC command builder generates correct arguments."""
        plugin = QUICProtocolPlugin({})
        builder = plugin.get_command_builder()
        
        # Test server args
        server_args = builder.build_server_args({
            "port": 4443,
            "cert_file": "/certs/cert.pem",
            "alpn": "hq-interop"
        })
        assert "-p" in server_args
        assert "4443" in server_args
        assert "-a" in server_args
        assert "hq-interop" in server_args
    
    def test_protocol_factory(self):
        """Test protocol factory can create protocols."""
        protocols = ProtocolFactory.get_available_protocols()
        assert "quic" in protocols
        assert "http" in protocols
        
        quic = ProtocolFactory.create_protocol("quic", {})
        assert quic is not None
        assert isinstance(quic, QUICProtocolPlugin)
    
    def test_network_requirements(self):
        """Test protocol returns correct network requirements."""
        plugin = QUICProtocolPlugin({})
        reqs = plugin.get_network_requirements()
        
        assert "ports" in reqs
        assert "udp" in reqs["ports"]
        assert 4443 in reqs["ports"]["udp"]
        assert "UDP" in reqs["protocols"]
```

#### TODO 7.2: Create Integration Tests
**File**: `/tests/integration/test_protocol_service_integration.py` (NEW)

```python
import pytest
from panther.plugins.plugin_manager import PluginManager
from panther.plugins.services.iut.quic.picoquic.picoquic import PicoquicServiceManager

class TestProtocolServiceIntegration:
    """Test integration between protocols and services."""
    
    def test_service_uses_protocol_plugin(self):
        """Test service manager correctly uses protocol plugin."""
        # Create service manager
        service_config = Mock()
        service_config.protocol.name = "quic"
        service_config.protocol.role = "server"
        
        manager = PicoquicServiceManager(
            service_config_to_test=service_config,
            service_type="iut",
            protocol=service_config.protocol,
            implementation_name="picoquic"
        )
        
        # Check protocol plugin loaded
        assert manager.protocol_plugin is not None
        assert manager.command_builder is not None
        
        # Test command generation uses protocol plugin
        command = manager.generate_run_command(role="server", port=4443)
        assert "picoquicdemo" in command
        assert "-p 4443" in command
    
    def test_network_environment_uses_protocol_requirements(self):
        """Test network environment applies protocol requirements."""
        # This would test that docker_compose correctly
        # configures ports based on protocol requirements
        pass
```

## Implementation Timeline

### Week 1: Foundation
- [ ] Create protocol plugin interfaces
- [ ] Create command builder interface
- [ ] Set up protocol factory
- [ ] Write interface documentation

### Week 2: Protocol Implementations
- [ ] Implement QUIC protocol plugin
- [ ] Implement HTTP protocol plugin
- [ ] Implement MiniP protocol plugin
- [ ] Create protocol-specific command builders

### Week 3: Service Refactoring
- [ ] Create protocol-aware base class
- [ ] Migrate one service (PicoQUIC) as proof of concept
- [ ] Test migrated service
- [ ] Create migration script

### Week 4: Environment Integration
- [ ] Update network environment base
- [ ] Update execution environment base
- [ ] Test protocol requirements flow
- [ ] Update docker-compose templates

### Week 5: Full Migration
- [ ] Run migration script on all services
- [ ] Update plugin manager
- [ ] Update service factory
- [ ] Fix any migration issues

### Week 6: Cleanup and Testing
- [ ] Remove legacy code
- [ ] Archive deprecated files
- [ ] Run full test suite
- [ ] Update documentation

## Maintenance Plan

### Version Control
1. **Feature Branch**: `feature/active-protocol-plugins`
2. **Migration Branch**: `migration/protocol-plugins-phase1`
3. **Cleanup Branch**: `cleanup/remove-legacy-protocols`

### Backward Compatibility
1. Keep deprecated classes for 2 releases
2. Add deprecation warnings
3. Provide migration guide
4. Support both old and new systems during transition

### Documentation Updates
1. Update plugin development guide
2. Create protocol plugin tutorial
3. Update API documentation
4. Add migration guide for users

### Monitoring and Metrics
1. Track protocol plugin usage
2. Monitor performance impact
3. Collect migration statistics
4. Track deprecation warnings

## Success Criteria

1. **Code Reduction**: 40% less code in service implementations
2. **Consistency**: All services use same protocol handling
3. **Performance**: No regression in command generation time
4. **Extensibility**: New protocol added in < 4 hours
5. **Test Coverage**: > 95% coverage for protocol system
6. **Migration Success**: All services migrated without breaking changes

## Risk Mitigation

1. **Performance Impact**:
   - Benchmark before/after migration
   - Profile command generation
   - Optimize hot paths

2. **Breaking Changes**:
   - Maintain compatibility layer
   - Gradual migration approach
   - Extensive testing before release

3. **Complexity**:
   - Keep protocol plugins simple
   - Clear separation of concerns
   - Comprehensive documentation

4. **Migration Failures**:
   - Test migration script thoroughly
   - Manual review of changes
   - Rollback plan ready

## Next Steps

1. **Review and Approval**: Get team buy-in on approach
2. **Create Feature Branch**: Start development
3. **Prototype QUIC Plugin**: Validate design
4. **Weekly Progress Reviews**: Track implementation
5. **User Testing**: Get feedback on new system