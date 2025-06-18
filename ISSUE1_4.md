# ISSUE 1+4: Service Manager Architecture Consolidation

## Executive Summary

This merged issue combines the tactical fix from ISSUE1 (90 lines of `_do_prepare()` stubs) with the strategic transformation from ISSUE4 (4,730+ lines of service manager duplication). By implementing in phases, we achieve immediate wins while building toward a comprehensive architectural solution.

**Total Impact**: 4,730+ lines removed | **Risk**: Low → Medium | **Timeline**: 3-4 weeks

## Problem Overview

### Current State
1. **Immediate Duplication** (ISSUE1):
   - 90 lines of identical `_do_prepare()` stubs across 9 QUIC implementations
   - Simple pass-through methods that could use inheritance

2. **Systemic Duplication** (ISSUE4):
   - 4,730+ lines across 25+ service managers
   - Repeated patterns: initialization (600), events (800), commands (400), QUIC logic (1,200)
   - Monolithic classes violating SOLID principles

### Why Merge?
- ISSUE1's fix is a subset of ISSUE4's solution
- Implementing separately causes rework
- Phased approach validates architecture incrementally
- Quick wins build confidence for larger changes

## Implementation Strategy

### Phase 1: Quick Win - Stub Consolidation (Days 1-2)

**Goal**: Remove 90 lines of `_do_prepare()` stubs as proof of concept

#### 1.1 Update Base Classes

**File**: `panther/plugins/services/base/quic_service_base.py`

**ADD** after line ~370:
```python
def _do_prepare(self, plugin_manager: Optional["PluginManager"] = None):
    """Default preparation implementation for QUIC services.
    
    This provides a safe default implementation that can be overridden
    by services that need specific preparation logic.
    
    Args:
        plugin_manager: Plugin manager for Docker operations
    """
    # Default implementation - most QUIC services don't need special preparation
    self.logger.debug(f"Using default preparation for {self._get_implementation_name()}")
    pass
```

#### 1.2 Remove Stub Implementations

**Files to modify** (remove `_do_prepare` methods):
- `panther/plugins/services/iut/quic/aioquic/aioquic.py`
- `panther/plugins/services/iut/quic/lsquic/lsquic.py`
- `panther/plugins/services/iut/quic/mvfst/mvfst.py`
- `panther/plugins/services/iut/quic/quant/quant.py`
- `panther/plugins/services/iut/quic/quinn/quinn.py`
- `panther/plugins/services/iut/quic/quiche/quiche.py`
- `panther/plugins/services/iut/quic/quic_go/quic_go.py`
- `panther/plugins/services/iut/quic/picoquic_shadow/picoquic_shadow.py`

**Special case** - `picoquic/picoquic.py` (keep but modify):
```python
def _do_prepare(self, plugin_manager: Optional["PluginManager"] = None):
    """Prepare the PicoQUIC service with Docker mixin support."""
    # Call base QUIC preparation first
    super()._do_prepare(plugin_manager)
    
    # Delegate to Docker mixin for image building
    if hasattr(super(), "prepare"):
        super().prepare(plugin_manager)
```

#### 1.3 Validation
```bash
# Test each implementation
python -m pytest tests/unit/test_plugins/test_services/test_iut/test_quic/ -v

# Verify behavior unchanged
grep "_do_prepare" outputs/*/experiment.log
```

**Success Metrics**:
- ✅ 90 lines removed
- ✅ All tests pass
- ✅ PicoQUIC Docker functionality preserved

### Phase 2: Mixin Architecture Foundation (Days 3-7)

**Goal**: Build reusable mixin components without breaking existing code

#### 2.1 Core Base Service Manager

**File**: `panther/plugins/services/base/base_service_manager.py` (NEW)

```python
"""
Core Base Service Manager - Foundation for all service implementations.
Implements template method pattern for consistent lifecycle management.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional

from panther.core.utils.logging_mixin import LoggerMixin
from panther.plugins.services.services_interface import IServiceManager


class ServicePhase(Enum):
    """Service lifecycle phases."""
    PRE_COMPILE = "pre_compile"
    COMPILE = "compile"
    POST_COMPILE = "post_compile"
    PRE_RUN = "pre_run"
    RUN = "run"
    POST_RUN = "post_run"


class BaseServiceManager(IServiceManager, LoggerMixin, ABC):
    """
    Base service manager implementing core interface contract.
    
    Provides fundamental functionality that all service managers need,
    following the Template Method pattern for consistent lifecycle management.
    """
    
    def __init__(self, service_config_to_test, service_type, protocol, 
                 implementation_name: str, event_manager=None, **kwargs):
        super().__init__()
        
        # Core attributes
        self.service_config_to_test = service_config_to_test
        self.service_type = service_type
        self.protocol = protocol
        self.implementation_name = implementation_name
        self.event_manager = event_manager
        
        # Service state
        self._prepared = False
        self._deployed = False
        self._running = False
        
        # Caches
        self._config_cache: Dict[str, Any] = {}
        self._command_cache: Dict[ServicePhase, str] = {}
    
    def generate_run_command(self, **kwargs) -> str:
        """Generate run command using template method pattern."""
        try:
            # Template method implementation
            validated_params = self._validate_parameters(**kwargs)
            processed_params = self._process_parameters(validated_params)
            command = self._build_command(processed_params)
            final_command = self._finalize_command(command, processed_params)
            
            self.logger.info(f"Generated command: {final_command[:100]}...")
            return final_command
            
        except Exception as e:
            self.logger.error(f"Failed to generate command: {e}")
            raise
    
    # Abstract methods for subclasses
    @abstractmethod
    def _validate_parameters(self, **kwargs) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def _process_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def _build_command(self, params: Dict[str, Any]) -> str:
        pass
    
    def _finalize_command(self, command: str, params: Dict[str, Any]) -> str:
        """Default post-processing implementation."""
        return " ".join(command.split())  # Clean whitespace
```

#### 2.2 Essential Mixins

**File**: `panther/plugins/services/base/service_initialization_mixin.py` (NEW)

```python
"""
Service Initialization Mixin - Consolidates 600 lines of initialization patterns.
"""

from pathlib import Path
from typing import Optional

from panther.core.utils.logging_mixin import LoggerMixin


class ServiceInitializationMixin(LoggerMixin):
    """Standardized service initialization patterns."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Initialize common attributes
        self._initialize_common_attributes()
        self._setup_plugin_directories()
        self._configure_docker_settings()
    
    def _initialize_common_attributes(self):
        """Initialize common service attributes."""
        self.plugin_dir = None
        self.template_dir = None
        self.docker_image_name = None
        self.docker_volumes = []
        self.docker_environment = {}
        
        self.service_name = getattr(self, 'implementation_name', 'unknown')
        self.service_version = getattr(self, 'version', 'latest')
    
    def _setup_plugin_directories(self):
        """Setup and validate plugin directories."""
        try:
            plugin_base = self._find_plugin_base_directory()
            if plugin_base:
                self.plugin_dir = plugin_base
                self.template_dir = plugin_base / "templates"
                self.logger.debug(f"Plugin directories setup: {self.plugin_dir}")
        except Exception as e:
            self.logger.error(f"Failed to setup plugin directories: {e}")
    
    def _find_plugin_base_directory(self) -> Optional[Path]:
        """Find the base plugin directory for this service."""
        # Implementation to locate plugin directory
        pass
```

**File**: `panther/plugins/services/base/parameter_extraction_mixin.py` (NEW)

```python
"""
Parameter Extraction Mixin - Consolidates 360 lines of parameter processing.
"""

from typing import Any, Dict

from panther.core.utils.logging_mixin import LoggerMixin


class ParameterExtractionMixin(LoggerMixin):
    """Standardized parameter extraction patterns."""
    
    def _extract_common_params(self, **kwargs) -> Dict[str, Any]:
        """Extract common parameters used across all service types."""
        params = {}
        
        # Network parameters
        params.update(self._extract_network_params(**kwargs))
        
        # Certificate parameters
        params.update(self._extract_certificate_params(**kwargs))
        
        # Role parameters
        params.update(self._extract_role_params(**kwargs))
        
        return params
    
    def _extract_network_params(self, **kwargs) -> Dict[str, Any]:
        """Extract network-related parameters."""
        params = {}
        
        # Host binding
        params["host"] = kwargs.get("host", "0.0.0.0")
        
        # Port configuration
        if "port" in kwargs:
            params["port"] = int(kwargs["port"])
        elif hasattr(self, 'service_config_to_test'):
            # Extract from config
            pass
            
        return params
```

### Phase 3: QUIC Service Consolidation (Week 2)

**Goal**: Apply mixin architecture to QUIC implementations

#### 3.1 QUIC-Specific Mixin

**File**: `panther/plugins/services/base/quic_service_mixin.py` (NEW)

```python
"""
QUIC Service Mixin - Consolidates 1,200 lines of QUIC-specific patterns.
"""

from typing import Any, Dict, List

from panther.core.utils.logging_mixin import LoggerMixin
from panther.plugins.services.base.parameter_extraction_mixin import ParameterExtractionMixin


class QUICServiceMixin(ParameterExtractionMixin, LoggerMixin):
    """QUIC protocol-specific functionality."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # QUIC configuration
        self.quic_version = "rfc9000"
        self.alpn_protocols = ["h3", "h3-29", "h3-32"]
        self.congestion_control = "cubic"
        
        # Initialize features
        self.supported_features = {"rfc9000", "tls13", "connection_migration"}
        self._add_implementation_features()
    
    def _extract_quic_params(self, **kwargs) -> Dict[str, Any]:
        """Extract QUIC-specific parameters."""
        params = self._extract_common_params(**kwargs)
        
        # QUIC parameters
        params.update({
            "quic_version": kwargs.get("quic_version", self.quic_version),
            "alpn": kwargs.get("alpn", self.alpn_protocols[0]),
            "congestion_control": kwargs.get("cc", self.congestion_control),
        })
        
        return params
    
    def _build_quic_server_args(self, params: Dict[str, Any]) -> List[str]:
        """Build common QUIC server arguments."""
        args = []
        
        if "port" in params:
            args.extend(["-p", str(params["port"])])
            
        if "cert_file" in params:
            args.extend(["--cert", params["cert_file"]])
            
        # Add implementation-specific args
        args.extend(self._get_server_specific_args(**params))
        
        return args
```

#### 3.2 Streamlined QUIC Implementation Example

**File**: `panther/plugins/services/iut/quic/picoquic/picoquic.py` (REPLACE)

```python
"""
PicoQUIC Service Manager - Streamlined with mixins.
Reduced from 250+ lines to ~85 lines.
"""

from panther.plugins.services.base.base_service_manager import BaseServiceManager
from panther.plugins.services.base.service_initialization_mixin import ServiceInitializationMixin
from panther.plugins.services.base.quic_service_mixin import QUICServiceMixin
from panther.core.docker_builder.service_manager_docker_mixin import ServiceManagerDockerMixin
from panther.plugins.plugin_decorators import register_plugin


@register_plugin(
    plugin_type="iut",
    name="picoquic",
    version="1.0.0",
    description="PicoQUIC QUIC implementation",
    supported_protocols=["quic"],
    capabilities=["rfc9000", "h3", "connection_migration"]
)
class PicoquicServiceManager(
    BaseServiceManager,
    ServiceInitializationMixin,
    QUICServiceMixin,
    ServiceManagerDockerMixin
):
    """PicoQUIC service manager using mixin composition."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.picoquic_binary = "picoquic_demo"
    
    def _get_implementation_name(self) -> str:
        return "picoquic"
    
    def _get_binary_name(self) -> str:
        role = getattr(self.service_config_to_test.protocol, 'role', None)
        return "picoquic_server" if role and role.value.lower() == 'server' else "picoquic_client"
    
    def _add_implementation_features(self):
        """Add PicoQUIC-specific features."""
        self.supported_features.update({"multipath", "bbr", "cubic", "pacing"})
    
    def _get_server_specific_args(self, **kwargs) -> List[str]:
        """PicoQUIC server-specific arguments."""
        args = []
        if kwargs.get("log_file"):
            args.extend(["-l", kwargs["log_file"]])
        if kwargs.get("qlog_dir"):
            args.extend(["-q", kwargs["qlog_dir"]])
        return args
    
    def _validate_parameters(self, **kwargs) -> Dict[str, Any]:
        return self._extract_quic_params(**kwargs)
    
    def _process_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return params
    
    def _build_command(self, params: Dict[str, Any]) -> str:
        return self._build_run_command()
```

### Phase 4: Full Service Manager Migration (Weeks 3-4)

**Goal**: Extend architecture to all 25+ service implementations

#### 4.1 Additional Protocol Mixins

- **HTTPServiceMixin**: HTTP-specific patterns (~400 lines)
- **MiniPServiceMixin**: MiniP protocol patterns (~300 lines)
- **ServiceEventMixin**: Event emission patterns (~800 lines)
- **CommandGenerationMixin**: Command lifecycle (~400 lines)

#### 4.2 Migration Order

1. **Week 3.1**: Remaining QUIC implementations (8 files)
2. **Week 3.2**: HTTP implementations (5 files)
3. **Week 3.3**: MiniP implementations (3 files)
4. **Week 3.4**: Tester implementations (5 files)
5. **Week 4**: Testing, documentation, cleanup

## Migration Guide

### Pre-Migration Checklist
- [ ] Full test suite passes
- [ ] Backup original implementations
- [ ] Document current command generation behavior
- [ ] Create rollback plan

### Migration Steps

1. **Phase 1 Implementation** (Immediate)
   ```bash
   # Apply base class changes
   git checkout -b feature/service-consolidation-phase1
   
   # Run tests after each file change
   python -m pytest tests/unit/test_plugins/test_services/ -v
   ```

2. **Phase 2-3 Implementation** (Incremental)
   ```bash
   # Add mixins one at a time
   # Test after each mixin addition
   # Migrate one implementation as proof of concept
   ```

3. **Phase 4 Implementation** (Systematic)
   ```bash
   # Use migration script for bulk updates
   python migrate_service_managers.py --validate
   ```

### Validation Strategy

**Unit Tests**:
```python
def test_mixin_composition():
    """Verify all mixins compose correctly."""
    assert hasattr(manager, 'generate_run_command')  # Base
    assert hasattr(manager, 'plugin_dir')  # Initialization
    assert hasattr(manager, '_extract_quic_params')  # QUIC
    
def test_backward_compatibility():
    """Ensure API compatibility maintained."""
    old_command = legacy_manager.generate_run_command(**params)
    new_command = mixin_manager.generate_run_command(**params)
    assert old_command == new_command
```

**Integration Tests**:
```bash
# Run actual QUIC experiments
python -m panther run --config experiment-config/test_quic_all.yaml
```

## Risk Mitigation

### Phase 1 Risks (Low)
- **Risk**: Breaking PicoQUIC Docker functionality
- **Mitigation**: Special case handling, extensive testing

### Phase 2-3 Risks (Medium)
- **Risk**: Complex mixin inheritance issues
- **Mitigation**: Clear MRO documentation, composition over inheritance

### Phase 4 Risks (Medium-High)
- **Risk**: Behavioral changes in command generation
- **Mitigation**: Comprehensive test coverage, gradual rollout

## Expected Outcomes

### Metrics
| Phase | Lines Removed | Files Modified | Risk | Timeline |
|-------|--------------|----------------|------|----------|
| 1 | 90 | 9 | Low | 2 days |
| 2 | 0 (adding) | 4 new | Low | 5 days |
| 3 | 1,200 | 9 | Medium | 5 days |
| 4 | 3,440 | 16 | Medium | 10 days |
| **Total** | **4,730** | **38** | **Medium** | **22 days** |

### Benefits
1. **Immediate**: 90-line reduction validates approach
2. **Short-term**: Consistent QUIC implementations
3. **Long-term**: Maintainable service architecture following SOLID principles

### Success Criteria
- [ ] Phase 1: All QUIC tests pass with stub consolidation
- [ ] Phase 2: Mixins integrate without breaking changes
- [ ] Phase 3: QUIC implementations reduced by 60-70%
- [ ] Phase 4: All services migrated, 4,730+ lines removed
- [ ] Final: Performance benchmarks show improvement

## Implementation Priority

**Recommended Sequence**:
1. **Day 1-2**: Phase 1 - Quick win with `_do_prepare()` consolidation
2. **Day 3-7**: Phase 2 - Build mixin foundation
3. **Week 2**: Phase 3 - QUIC consolidation (highest duplication)
4. **Week 3-4**: Phase 4 - Complete migration

This phased approach provides:
- Immediate validation of concept
- Incremental risk management
- Clear rollback points
- Continuous value delivery

---

*Combined from ISSUE1 (90 lines) and ISSUE4 (4,730 lines)*
*Estimated Total Effort: 3-4 weeks*
*Risk Level: Low → Medium (phased approach)*