# Protocol Plugin Architecture Improvement Plan

## Overview
This document outlines a comprehensive plan to improve the Protocol Plugin architecture in PANTHER, making protocols first-class citizens in the system rather than passive configuration holders.

## Current State Analysis

### Problems Identified
1. **Protocol plugins are passive** - Only contain configuration schemas, no active behavior
2. **Protocol logic scattered** - Command generation and protocol-specific logic spread across service base classes
3. **Legacy code exists** - IProtocolManager interface unused, redundant directory structures
4. **Weak integration** - Protocols don't actively participate in network/execution environment configuration
5. **Code duplication** - Similar protocol handling logic repeated in multiple service implementations

### Current Architecture
```
Protocol Flow:
Experiment Config → Service Config (contains protocol) → Service Manager → Command Generation
                                                                ↓
                                                    Protocol-specific logic embedded in services
```

## Proposed Architecture

### New Protocol Plugin Architecture
```
Protocol Flow:
Experiment Config → Protocol Plugin Manager → Protocol Instance
                           ↓                          ↓
                    Service Manager ←──── Provides command builders, validators, environment configs
                           ↓
                    Network Environment ←─── Protocol-aware configuration
                           ↓
                    Execution Environment ←── Protocol-specific wrapping
```

## Implementation Plan

### Phase 1: Create Active Protocol Plugin System

#### 1.1 Define New Protocol Plugin Interface
**File**: `panther/plugins/protocols/protocol_interface.py`

```python
class IProtocolPlugin(IPlugin):
    """Active protocol plugin interface."""
    
    @abstractmethod
    def get_command_builder(self) -> 'IProtocolCommandBuilder':
        """Return protocol-specific command builder."""
        pass
    
    @abstractmethod
    def get_network_requirements(self) -> Dict[str, Any]:
        """Return network environment requirements."""
        pass
    
    @abstractmethod
    def get_execution_requirements(self) -> Dict[str, Any]:
        """Return execution environment requirements."""
        pass
    
    @abstractmethod
    def validate_configuration(self, config: Dict) -> bool:
        """Validate protocol-specific configuration."""
        pass
    
    @abstractmethod
    def get_default_parameters(self, role: str) -> Dict[str, Any]:
        """Return default parameters for given role."""
        pass
```

#### 1.2 Create Protocol Command Builder Interface
**File**: `panther/plugins/protocols/command_builder_interface.py`

```python
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
```

### Phase 2: Implement Protocol Plugins

#### 2.1 QUIC Protocol Plugin
**File**: `panther/plugins/protocols/client_server/quic/quic_protocol.py`

- Move QUIC-specific logic from `quic_service_base.py`
- Implement certificate handling
- Define QUIC-specific network requirements (UDP ports, etc.)
- Implement QUIC command builder with ALPN, version negotiation, etc.

#### 2.2 HTTP Protocol Plugin  
**File**: `panther/plugins/protocols/client_server/http/http_protocol.py`

- Move HTTP-specific logic from `http_service_base.py`
- Implement HTTP/1.1, HTTP/2, HTTP/3 handling
- Define HTTP-specific parameters (methods, headers, etc.)
- Implement HTTP command builder

#### 2.3 MiniP Protocol Plugin
**File**: `panther/plugins/protocols/client_server/minip/minip_protocol.py`

- Move MiniP-specific logic from `minip_service_base.py`
- Define minimal protocol requirements
- Implement simple command builder

### Phase 3: Refactor Service Base Classes

#### 3.1 Create Generic Service Base
**File**: `panther/plugins/services/base/service_base.py`

```python
class BaseServiceManager(IServiceManager):
    """Generic service manager that delegates to protocol plugins."""
    
    def __init__(self, ...):
        # Load protocol plugin
        self.protocol_plugin = self._load_protocol_plugin()
        self.command_builder = self.protocol_plugin.get_command_builder()
    
    def generate_run_command(self, **kwargs) -> str:
        # Delegate to protocol's command builder
        if kwargs.get("role") == "server":
            args = self.command_builder.build_server_args(kwargs)
        else:
            args = self.command_builder.build_client_args(kwargs)
        
        return self._finalize_command(args, **kwargs)
```

#### 3.2 Simplify Implementation-Specific Classes
- Remove protocol-specific logic from implementations
- Focus only on implementation-specific details
- Inherit from generic base class

### Phase 4: Integrate with Environments

#### 4.1 Network Environment Integration
**Updates to**: `panther/plugins/environments/network_environment/base_network_environment.py`

- Query protocol plugin for network requirements
- Apply protocol-specific network configuration
- Handle protocol-specific port mappings

#### 4.2 Execution Environment Integration  
**Updates to**: `panther/plugins/environments/execution_environment/base_execution_environment.py`

- Query protocol plugin for execution requirements
- Apply protocol-specific wrapping (e.g., system calls to trace)
- Handle protocol-specific performance considerations

### Phase 5: Update Configuration Flow

#### 5.1 Enhance Configuration Manager
**Updates to**: `panther/config/config_manager.py`

- Load protocol plugins early in configuration
- Validate protocol configurations using plugin validators
- Merge protocol defaults with user configuration

#### 5.2 Update Service Factory
**Updates to**: `panther/plugins/service_factory.py`

- Load protocol plugin before creating service manager
- Pass protocol plugin to service manager constructor
- Validate service/protocol compatibility

### Phase 6: Clean Up Legacy Code

#### 6.1 Remove Legacy Files
- [ ] Delete unused `IProtocolManager` from `protocol_interface.py`
- [ ] Remove empty protocol implementation files (`client_server.py`, `peer_to_peer.py`)
- [ ] Clean up redundant protocol configuration schemas

#### 6.2 Simplify Directory Structure
```
Current:
panther/plugins/services/iut/quic/picoquic/
panther/plugins/services/iut/http/nginx/

Proposed:
panther/plugins/services/iut/picoquic/  # Protocol determined by plugin metadata
panther/plugins/services/iut/nginx/
```

#### 6.3 Remove Protocol-Specific Service Base Classes
- [ ] Deprecate `quic_service_base.py` (logic moved to QUIC protocol plugin)
- [ ] Deprecate `http_service_base.py` (logic moved to HTTP protocol plugin)
- [ ] Deprecate `minip_service_base.py` (logic moved to MiniP protocol plugin)
- [ ] Create migration guide for existing implementations

### Phase 7: Create Protocol Plugin Registry

#### 7.1 Protocol Discovery
**File**: `panther/plugins/protocols/protocol_registry.py`

- Automatic discovery of protocol plugins
- Protocol capability registration
- Protocol compatibility matrix

#### 7.2 Protocol Factory
**File**: `panther/plugins/protocols/protocol_factory.py`

- Create protocol instances based on configuration
- Handle protocol version negotiation
- Manage protocol plugin lifecycle

### Phase 8: Testing and Migration

#### 8.1 Create Test Suite
- [ ] Unit tests for new protocol plugin system
- [ ] Integration tests for protocol/service interaction
- [ ] Integration tests for protocol/environment interaction
- [ ] Migration tests to ensure backward compatibility

#### 8.2 Migration Tools
- [ ] Create script to migrate existing service implementations
- [ ] Update existing experiment configurations
- [ ] Create compatibility layer for gradual migration

## Benefits of New Architecture

1. **Separation of Concerns**: Protocol logic separated from implementation logic
2. **Reusability**: Protocol plugins can be shared across implementations
3. **Extensibility**: Easy to add new protocols without modifying core
4. **Consistency**: Standardized protocol handling across all implementations
5. **Integration**: Better integration with network and execution environments
6. **Maintainability**: Protocol updates in one place affect all implementations

## Migration Strategy

### Step 1: Parallel Implementation (Month 1)
- Implement new protocol plugin system alongside existing
- Create adapters for backward compatibility
- No breaking changes

### Step 2: Gradual Migration (Month 2)
- Migrate one protocol at a time (start with QUIC)
- Update implementations to use new system
- Maintain backward compatibility

### Step 3: Deprecation (Month 3)
- Mark old system as deprecated
- Update all documentation
- Provide migration tools

### Step 4: Removal (Month 4)
- Remove legacy code
- Clean up directory structure
- Final optimization

## Implementation Checklist

### Core Protocol System
- [ ] Create IProtocolPlugin interface
- [ ] Create IProtocolCommandBuilder interface
- [ ] Implement protocol plugin discovery
- [ ] Create protocol factory
- [ ] Update plugin manager to load protocol plugins

### Protocol Implementations
- [ ] Implement QUIC protocol plugin
- [ ] Implement HTTP protocol plugin
- [ ] Implement MiniP protocol plugin
- [ ] Create protocol plugin tests

### Service Refactoring
- [ ] Create generic service base class
- [ ] Refactor QUIC implementations to use protocol plugin
- [ ] Refactor HTTP implementations to use protocol plugin
- [ ] Refactor MiniP implementations to use protocol plugin
- [ ] Update service factory

### Environment Integration
- [ ] Update network environments to query protocol requirements
- [ ] Update execution environments to apply protocol-specific configuration
- [ ] Create environment/protocol integration tests

### Configuration Updates
- [ ] Update configuration manager for protocol plugins
- [ ] Update configuration schemas
- [ ] Create configuration migration tools

### Documentation
- [ ] Update protocol plugin development guide
- [ ] Create migration guide for service implementations
- [ ] Update experiment configuration documentation
- [ ] Create protocol plugin API reference

### Testing
- [ ] Unit tests for protocol plugins
- [ ] Integration tests for protocol/service interaction
- [ ] Integration tests for protocol/environment interaction
- [ ] End-to-end tests with new architecture
- [ ] Performance benchmarks

### Cleanup
- [ ] Remove legacy IProtocolManager
- [ ] Remove protocol-specific service base classes
- [ ] Simplify directory structure
- [ ] Remove redundant configuration files
- [ ] Archive deprecated code

## Success Metrics

1. **Code Reduction**: 30-40% reduction in service implementation code
2. **Consistency**: All implementations use same protocol handling
3. **Performance**: No regression in command generation time
4. **Extensibility**: New protocol can be added in < 1 day
5. **Test Coverage**: > 90% coverage for protocol system

## Risk Mitigation

1. **Backward Compatibility**: Maintain adapter layer during migration
2. **Performance**: Benchmark each phase to ensure no regression
3. **Complexity**: Keep protocol plugins simple and focused
4. **Migration Effort**: Provide automated migration tools
5. **Documentation**: Comprehensive guides for developers

## Next Steps

1. Review and approve this plan
2. Create feature branch for protocol plugin development
3. Start with Phase 1: Core protocol plugin interface
4. Implement QUIC protocol plugin as proof of concept
5. Gather feedback and iterate