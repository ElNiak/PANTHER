# ISSUE 4: Streamline Service Manager Patterns

## Overview

The service manager implementations in PANTHER contain extensive code duplication across different service types and protocol implementations. This creates maintenance overhead, inconsistent behavior, and violates DRY principles.

## Problem Analysis

### Current Service Manager Duplication

1. **4,730+ lines of duplicate code** across service manager implementations
2. **9 QUIC implementations** with 60-80% identical code patterns
3. **Monolithic base classes** that violate Single Responsibility Principle
4. **Inconsistent API patterns** across different service types
5. **Duplicate event emission and lifecycle management** in every service

### Quantified Duplication Categories

| Category | Estimated Lines | Implementations Affected |
|----------|-----------------|-------------------------|
| QUIC Implementation Patterns | 1,200 | 9 QUIC services |
| Event Emission Logic | 800 | All service managers |
| Service Initialization | 600 | All service managers |
| Role-Based Logic | 480 | 12+ services |
| Command Generation Lifecycle | 400 | All service managers |
| Docker Integration | 350 | All IUT services |
| Template Rendering | 300 | Most services |
| **Total Duplication** | **4,730** | **25+ services** |

### SOLID Principle Violations

1. **Single Responsibility Principle**: `IServiceManager` (1,060 lines) handles too many concerns
2. **Open/Closed Principle**: Adding new features requires modifying existing service managers
3. **Liskov Substitution Principle**: Service managers can't be used interchangeably due to inconsistent APIs
4. **Interface Segregation Principle**: Services forced to implement unused methods
5. **Dependency Inversion Principle**: Concrete implementations depend on other concrete implementations

## Solution Architecture

### New Mixin-Based Architecture

Following SOLID principles, the new architecture uses composition and specialized mixins:

```
BaseServiceManager (Core Interface)
├── ServiceInitializationMixin (Initialization patterns)
├── CommandGenerationMixin (Standardized command lifecycle)
├── ParameterExtractionMixin (Common parameter processing)
├── ServiceEventMixin (Enhanced event handling)
├── ServiceLifecycleMixin (Prepare/deploy/cleanup)
├── ProtocolServiceMixin (Protocol-specific functionality)
│   ├── QUICServiceMixin
│   ├── HTTPServiceMixin
│   └── MiniPServiceMixin
└── RoleSpecificMixin (Server/Client specialization)
    ├── ServerServiceMixin
    └── ClientServiceMixin
```

### Design Principles Applied

1. **Single Responsibility**: Each mixin handles one specific concern
2. **Open/Closed**: New functionality can be added through new mixins
3. **Liskov Substitution**: All service managers implement consistent interface
4. **Interface Segregation**: Services compose only needed functionality
5. **Dependency Inversion**: Depend on abstract mixins, not concrete implementations

## Implementation Plan

### Phase 1: Create Core Base Classes

**File**: `/panther/plugins/services/base/base_service_manager.py`

**ADD (New File - 280 lines)**:
```python
"""
Core Base Service Manager

Provides the fundamental interface and contract for all service managers
following SOLID principles and DRY patterns.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Union

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
    
    Principles Applied:
    - Single Responsibility: Core service management only
    - Open/Closed: Extensible through composition with mixins
    - Liskov Substitution: Consistent interface for all service types
    """
    
    def __init__(
        self,
        service_config_to_test,
        service_type,
        protocol,
        implementation_name: str,
        event_manager=None,
        **kwargs
    ):
        """
        Initialize base service manager.
        
        Args:
            service_config_to_test: Service configuration
            service_type: Type of service (IUT, tester)
            protocol: Protocol configuration
            implementation_name: Name of implementation
            event_manager: Event manager for notifications
            **kwargs: Additional configuration
        """
        super().__init__()
        
        # Core service attributes
        self.service_config_to_test = service_config_to_test
        self.service_type = service_type
        self.protocol = protocol
        self.implementation_name = implementation_name
        self.event_manager = event_manager
        
        # Service state
        self._prepared = False
        self._deployed = False
        self._running = False
        
        # Configuration cache
        self._config_cache: Dict[str, Any] = {}
        self._command_cache: Dict[ServicePhase, str] = {}
        
        self.logger.info(f"Initialized {self.__class__.__name__} for {implementation_name}")
    
    # === Core Interface Implementation ===
    
    def generate_run_command(self, **kwargs) -> str:
        """
        Generate run command using template method pattern.
        
        This method defines the algorithm structure while allowing
        subclasses to customize specific steps.
        """
        self.logger.debug(f"Generating run command for {self.implementation_name}")
        
        try:
            # Validate input parameters
            validated_params = self._validate_parameters(**kwargs)
            
            # Extract and normalize parameters
            processed_params = self._process_parameters(validated_params)
            
            # Build command using protocol-specific logic
            command = self._build_command(processed_params)
            
            # Apply post-processing and validation
            final_command = self._finalize_command(command, processed_params)
            
            self.logger.info(f"Generated run command: {final_command[:100]}...")
            return final_command
            
        except Exception as e:
            self.logger.error(f"Failed to generate run command: {e}")
            raise
    
    def generate_deployment_commands(self) -> str:
        """Generate deployment commands using template method."""
        try:
            deployment_commands = []
            
            # Generate each phase
            for phase in ServicePhase:
                if phase != ServicePhase.RUN:  # RUN handled separately
                    command = self._generate_phase_command(phase)
                    if command:
                        deployment_commands.append(command)
            
            return "\n".join(deployment_commands)
            
        except Exception as e:
            self.logger.error(f"Failed to generate deployment commands: {e}")
            raise
    
    # === Template Methods (Subclasses Override) ===
    
    @abstractmethod
    def _validate_parameters(self, **kwargs) -> Dict[str, Any]:
        """Validate input parameters. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def _process_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Process and normalize parameters. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def _build_command(self, params: Dict[str, Any]) -> str:
        """Build command string. Must be implemented by subclasses."""
        pass
    
    def _finalize_command(self, command: str, params: Dict[str, Any]) -> str:
        """
        Finalize command with post-processing.
        Default implementation applies common formatting.
        """
        # Remove excessive whitespace
        command = " ".join(command.split())
        
        # Apply command wrapping if needed
        if params.get("wrap_command", False):
            command = f"sh -c '{command}'"
        
        return command
    
    def _generate_phase_command(self, phase: ServicePhase) -> Optional[str]:
        """
        Generate command for specific phase.
        Default implementation delegates to phase-specific methods.
        """
        if phase in self._command_cache:
            return self._command_cache[phase]
        
        method_name = f"generate_{phase.value}_commands"
        if hasattr(self, method_name):
            command = getattr(self, method_name)()
            self._command_cache[phase] = command
            return command
        
        return None
    
    # === Lifecycle Management ===
    
    def prepare(self, plugin_manager=None) -> None:
        """Prepare service for deployment."""
        if self._prepared:
            self.logger.debug(f"Service {self.implementation_name} already prepared")
            return
        
        self.logger.info(f"Preparing service {self.implementation_name}")
        
        try:
            self._do_prepare(plugin_manager)
            self._prepared = True
            self.logger.info(f"Service {self.implementation_name} prepared successfully")
        except Exception as e:
            self.logger.error(f"Failed to prepare service {self.implementation_name}: {e}")
            raise
    
    def deploy(self) -> bool:
        """Deploy service."""
        if not self._prepared:
            raise RuntimeError(f"Service {self.implementation_name} not prepared")
        
        if self._deployed:
            self.logger.debug(f"Service {self.implementation_name} already deployed")
            return True
        
        self.logger.info(f"Deploying service {self.implementation_name}")
        
        try:
            success = self._do_deploy()
            if success:
                self._deployed = True
                self.logger.info(f"Service {self.implementation_name} deployed successfully")
            return success
        except Exception as e:
            self.logger.error(f"Failed to deploy service {self.implementation_name}: {e}")
            return False
    
    def cleanup(self) -> None:
        """Clean up service resources."""
        self.logger.info(f"Cleaning up service {self.implementation_name}")
        
        try:
            self._do_cleanup()
            self._reset_state()
            self.logger.info(f"Service {self.implementation_name} cleaned up successfully")
        except Exception as e:
            self.logger.error(f"Failed to cleanup service {self.implementation_name}: {e}")
    
    # === Abstract Lifecycle Methods ===
    
    @abstractmethod
    def _do_prepare(self, plugin_manager=None) -> None:
        """Perform service-specific preparation."""
        pass
    
    def _do_deploy(self) -> bool:
        """
        Perform service-specific deployment.
        Default implementation returns True (no deployment needed).
        """
        return True
    
    def _do_cleanup(self) -> None:
        """
        Perform service-specific cleanup.
        Default implementation does nothing.
        """
        pass
    
    # === State Management ===
    
    def _reset_state(self) -> None:
        """Reset service state."""
        self._prepared = False
        self._deployed = False
        self._running = False
        self._config_cache.clear()
        self._command_cache.clear()
    
    def is_prepared(self) -> bool:
        """Check if service is prepared."""
        return self._prepared
    
    def is_deployed(self) -> bool:
        """Check if service is deployed."""
        return self._deployed
    
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._running
    
    # === Configuration Management ===
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value with caching."""
        if key in self._config_cache:
            return self._config_cache[key]
        
        # Extract from service config
        value = getattr(self.service_config_to_test, key, default)
        self._config_cache[key] = value
        return value
    
    def set_config_value(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self._config_cache[key] = value
    
    # === Command Phase Methods (Default Implementations) ===
    
    def generate_pre_compile_commands(self) -> str:
        """Generate pre-compilation commands."""
        return ""
    
    def generate_compile_commands(self) -> str:
        """Generate compilation commands."""
        return ""
    
    def generate_post_compile_commands(self) -> str:
        """Generate post-compilation commands."""
        return ""
    
    def generate_pre_run_commands(self) -> str:
        """Generate pre-run commands."""
        return ""
    
    def generate_post_run_commands(self) -> str:
        """Generate post-run commands."""
        return ""
    
    # === Utility Methods ===
    
    def get_implementation_info(self) -> Dict[str, Any]:
        """Get implementation information."""
        return {
            "name": self.implementation_name,
            "type": self.service_type,
            "protocol": self.protocol.name if hasattr(self.protocol, 'name') else str(self.protocol),
            "prepared": self._prepared,
            "deployed": self._deployed,
            "running": self._running
        }
    
    def __repr__(self) -> str:
        """String representation."""
        return f"{self.__class__.__name__}(implementation={self.implementation_name})"
```

### Phase 2: Create Specialized Mixins

**File**: `/panther/plugins/services/base/service_initialization_mixin.py`

**ADD (New File - 180 lines)**:
```python
"""
Service Initialization Mixin

Consolidates common service initialization patterns to eliminate duplication
across all service manager implementations.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

from panther.core.utils.logging_mixin import LoggerMixin


class ServiceInitializationMixin(LoggerMixin):
    """
    Mixin providing standardized service initialization patterns.
    
    Eliminates ~600 lines of duplicate initialization code across service managers.
    
    Responsibilities:
    - Plugin directory setup and validation
    - Docker image configuration
    - Template renderer initialization
    - Common attribute standardization
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Initialize common attributes with defaults
        self._initialize_common_attributes()
        
        # Setup plugin directories
        self._setup_plugin_directories()
        
        # Configure Docker settings
        self._configure_docker_settings()
        
        # Initialize template renderer
        self._initialize_template_renderer()
    
    def _initialize_common_attributes(self) -> None:
        """Initialize common service attributes with standardized defaults."""
        # Plugin paths
        self.plugin_dir = None
        self.template_dir = None
        self.dockerfile_path = None
        
        # Docker configuration
        self.docker_image_name = None
        self.docker_volumes = []
        self.docker_environment = {}
        
        # Template rendering
        self.template_renderer = None
        self.template_params = {}
        
        # Service metadata
        self.service_name = getattr(self, 'implementation_name', 'unknown')
        self.service_version = getattr(self, 'version', 'latest')
        
        self.logger.debug(f"Initialized common attributes for {self.service_name}")
    
    def _setup_plugin_directories(self) -> None:
        """
        Setup and validate plugin directories.
        
        Standardizes plugin directory discovery across all service types.
        """
        try:
            # Determine plugin base directory
            plugin_base = self._find_plugin_base_directory()
            
            if plugin_base:
                self.plugin_dir = plugin_base
                self.template_dir = plugin_base / "templates"
                self.dockerfile_path = plugin_base / "Dockerfile"
                
                # Validate critical directories exist
                self._validate_plugin_structure()
                
                self.logger.debug(f"Plugin directories setup: {self.plugin_dir}")
            else:
                self.logger.warning(f"Plugin directory not found for {self.service_name}")
                
        except Exception as e:
            self.logger.error(f"Failed to setup plugin directories: {e}")
            # Set fallback values
            self.plugin_dir = Path.cwd()
            self.template_dir = self.plugin_dir / "templates"
    
    def _find_plugin_base_directory(self) -> Optional[Path]:
        """
        Find the base plugin directory for this service.
        
        Returns:
            Path to plugin directory or None if not found
        """
        # Start from current file location
        current_file = Path(__file__).parent
        
        # Common plugin directory patterns
        search_patterns = [
            # For IUT services: panther/plugins/services/iut/{protocol}/{implementation}
            current_file.parent.parent / "services" / "iut" / getattr(self.protocol, 'name', 'unknown') / self.service_name,
            # For testers: panther/plugins/services/testers/{implementation}
            current_file.parent.parent / "services" / "testers" / self.service_name,
            # Direct service directory
            current_file.parent / self.service_name,
            # Fallback to implementation directory
            Path(os.getcwd()) / "panther" / "plugins" / "services" / "iut" / getattr(self.protocol, 'name', 'unknown') / self.service_name
        ]
        
        for pattern in search_patterns:
            if pattern.exists() and pattern.is_dir():
                return pattern
        
        return None
    
    def _validate_plugin_structure(self) -> None:
        """Validate plugin directory structure."""
        if not self.plugin_dir:
            return
        
        # Check for required files/directories
        required_items = {
            "config_schema.py": "Configuration schema",
            "templates": "Template directory"
        }
        
        missing_items = []
        for item, description in required_items.items():
            item_path = self.plugin_dir / item
            if not item_path.exists():
                missing_items.append(f"{description} ({item})")
        
        if missing_items:
            self.logger.warning(
                f"Plugin {self.service_name} missing: {', '.join(missing_items)}"
            )
    
    def _configure_docker_settings(self) -> None:
        """Configure Docker-related settings."""
        if not hasattr(self, 'service_type') or not hasattr(self, 'protocol'):
            return
        
        try:
            # Generate standardized Docker image name
            protocol_name = getattr(self.protocol, 'name', 'unknown')
            service_version = getattr(self, 'service_version', 'latest')
            
            self.docker_image_name = f"{self.service_name}_{service_version}:latest"
            
            # Setup common Docker volumes
            self.docker_volumes = [
                "/tmp:/tmp",  # Temporary files
                "/var/log:/var/log"  # Logging
            ]
            
            # Setup common environment variables
            self.docker_environment = {
                "SERVICE_NAME": self.service_name,
                "PROTOCOL": protocol_name,
                "SERVICE_TYPE": str(self.service_type)
            }
            
            self.logger.debug(f"Docker settings configured: {self.docker_image_name}")
            
        except Exception as e:
            self.logger.warning(f"Failed to configure Docker settings: {e}")
    
    def _initialize_template_renderer(self) -> None:
        """Initialize template renderer with common parameters."""
        try:
            from panther.core.template.template_renderer import TemplateRenderer
            
            if self.template_dir and self.template_dir.exists():
                self.template_renderer = TemplateRenderer(str(self.template_dir))
                
                # Setup common template parameters
                self.template_params = {
                    "service_name": self.service_name,
                    "implementation_name": self.service_name,
                    "protocol": getattr(self.protocol, 'name', 'unknown'),
                    "service_type": str(self.service_type),
                    "docker_image": self.docker_image_name,
                    "plugin_dir": str(self.plugin_dir) if self.plugin_dir else "",
                }
                
                self.logger.debug(f"Template renderer initialized for {self.service_name}")
            else:
                self.logger.debug(f"No template directory found, skipping template renderer")
                
        except Exception as e:
            self.logger.warning(f"Failed to initialize template renderer: {e}")
            self.template_renderer = None
    
    def get_plugin_file_path(self, filename: str) -> Optional[Path]:
        """
        Get path to a file within the plugin directory.
        
        Args:
            filename: Name of file to find
            
        Returns:
            Path to file or None if not found
        """
        if not self.plugin_dir:
            return None
        
        file_path = self.plugin_dir / filename
        return file_path if file_path.exists() else None
    
    def get_template_path(self, template_name: str) -> Optional[Path]:
        """
        Get path to a template file.
        
        Args:
            template_name: Name of template file
            
        Returns:
            Path to template or None if not found
        """
        if not self.template_dir:
            return None
        
        template_path = self.template_dir / template_name
        return template_path if template_path.exists() else None
    
    def add_docker_volume(self, volume_mapping: str) -> None:
        """
        Add Docker volume mapping.
        
        Args:
            volume_mapping: Volume mapping in format "host:container"
        """
        if volume_mapping not in self.docker_volumes:
            self.docker_volumes.append(volume_mapping)
            self.logger.debug(f"Added Docker volume: {volume_mapping}")
    
    def set_docker_environment(self, key: str, value: str) -> None:
        """
        Set Docker environment variable.
        
        Args:
            key: Environment variable name
            value: Environment variable value
        """
        self.docker_environment[key] = value
        self.logger.debug(f"Set Docker environment: {key}={value}")
    
    def get_service_metadata(self) -> Dict[str, Any]:
        """
        Get standardized service metadata.
        
        Returns:
            Dictionary containing service metadata
        """
        return {
            "name": self.service_name,
            "implementation": self.service_name,
            "version": self.service_version,
            "protocol": getattr(self.protocol, 'name', 'unknown'),
            "service_type": str(self.service_type),
            "plugin_dir": str(self.plugin_dir) if self.plugin_dir else None,
            "docker_image": self.docker_image_name,
            "has_templates": self.template_renderer is not None,
            "has_dockerfile": self.dockerfile_path and self.dockerfile_path.exists()
        }
```

**File**: `/panther/plugins/services/base/command_generation_mixin.py`

**ADD (New File - 220 lines)**:
```python
"""
Command Generation Mixin

Standardizes command generation lifecycle across all service managers,
eliminating ~400 lines of duplicate command structure logic.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from panther.core.utils.logging_mixin import LoggerMixin


class CommandPhase(Enum):
    """Command generation phases."""
    PRE_COMPILE = "pre_compile"
    COMPILE = "compile"
    POST_COMPILE = "post_compile"
    PRE_RUN = "pre_run"
    RUN = "run"
    POST_RUN = "post_run"


class CommandGenerationMixin(LoggerMixin):
    """
    Mixin providing standardized command generation patterns.
    
    Eliminates command generation duplication across service managers by
    providing a consistent lifecycle and execution framework.
    
    Responsibilities:
    - Standardized command generation lifecycle
    - Command validation and formatting
    - Phase-based command organization
    - Template-based command building
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Command generation state
        self._command_cache: Dict[CommandPhase, str] = {}
        self._generation_context: Dict[str, Any] = {}
        
        # Command building configuration
        self.command_separator = " && "
        self.command_prefix = ""
        self.command_suffix = ""
        self.enable_command_validation = True
    
    def generate_full_lifecycle_commands(self, **kwargs) -> Dict[str, str]:
        """
        Generate commands for all lifecycle phases.
        
        Args:
            **kwargs: Parameters for command generation
            
        Returns:
            Dictionary mapping phase names to command strings
        """
        self.logger.debug(f"Generating full lifecycle commands for {self.service_name}")
        
        # Clear cache for fresh generation
        self._command_cache.clear()
        
        # Update generation context
        self._generation_context.update(kwargs)
        
        # Generate commands for each phase
        commands = {}
        for phase in CommandPhase:
            try:
                command = self._generate_phase_command(phase)
                if command:
                    commands[phase.value] = command
                    self.logger.debug(f"Generated {phase.value}: {command[:100]}...")
            except Exception as e:
                self.logger.error(f"Failed to generate {phase.value} command: {e}")
                commands[phase.value] = ""
        
        return commands
    
    def _generate_phase_command(self, phase: CommandPhase) -> str:
        """
        Generate command for a specific phase.
        
        Args:
            phase: Command phase to generate
            
        Returns:
            Generated command string
        """
        # Check cache first
        if phase in self._command_cache:
            return self._command_cache[phase]
        
        # Generate command using phase-specific logic
        command = self._build_phase_command(phase)
        
        # Apply post-processing
        if command:
            command = self._post_process_command(command, phase)
            
            # Validate if enabled
            if self.enable_command_validation:
                self._validate_command(command, phase)
            
            # Cache the result
            self._command_cache[phase] = command
        
        return command
    
    def _build_phase_command(self, phase: CommandPhase) -> str:
        """
        Build command for specific phase using method dispatch.
        
        Args:
            phase: Command phase to build
            
        Returns:
            Raw command string
        """
        # Try specific phase method first
        method_name = f"_build_{phase.value}_command"
        if hasattr(self, method_name):
            return getattr(self, method_name)()
        
        # Fall back to generic method
        return self._build_generic_command(phase)
    
    def _build_generic_command(self, phase: CommandPhase) -> str:
        """
        Build generic command using template if available.
        
        Args:
            phase: Command phase to build
            
        Returns:
            Command string or empty string
        """
        if not hasattr(self, 'template_renderer') or not self.template_renderer:
            return ""
        
        try:
            # Look for phase-specific template
            template_name = f"{phase.value}_command.jinja"
            template_path = self.get_template_path(template_name)
            
            if template_path:
                # Render template with generation context
                context = self._build_template_context(phase)
                return self.template_renderer.render_template(template_name, **context)
            
        except Exception as e:
            self.logger.warning(f"Failed to render template for {phase.value}: {e}")
        
        return ""
    
    def _build_template_context(self, phase: CommandPhase) -> Dict[str, Any]:
        """
        Build template context for command generation.
        
        Args:
            phase: Command phase being generated
            
        Returns:
            Template context dictionary
        """
        context = {
            "phase": phase.value,
            "service_name": getattr(self, 'service_name', 'unknown'),
            "implementation_name": getattr(self, 'implementation_name', 'unknown'),
            "protocol": getattr(self.protocol, 'name', 'unknown') if hasattr(self, 'protocol') else 'unknown',
        }
        
        # Add generation context
        context.update(self._generation_context)
        
        # Add template parameters if available
        if hasattr(self, 'template_params'):
            context.update(self.template_params)
        
        return context
    
    def _post_process_command(self, command: str, phase: CommandPhase) -> str:
        """
        Post-process generated command.
        
        Args:
            command: Raw command string
            phase: Command phase
            
        Returns:
            Post-processed command string
        """
        if not command:
            return ""
        
        # Clean up whitespace
        command = " ".join(command.split())
        
        # Apply prefix/suffix if configured
        if self.command_prefix:
            command = f"{self.command_prefix} {command}"
        
        if self.command_suffix:
            command = f"{command} {self.command_suffix}"
        
        # Apply phase-specific post-processing
        return self._apply_phase_post_processing(command, phase)
    
    def _apply_phase_post_processing(self, command: str, phase: CommandPhase) -> str:
        """
        Apply phase-specific post-processing.
        
        Args:
            command: Command string
            phase: Command phase
            
        Returns:
            Post-processed command
        """
        # Phase-specific logic can be added here
        if phase == CommandPhase.RUN:
            # Add backgrounding for run commands if needed
            if self._generation_context.get("background", False):
                command = f"({command}) &"
        
        return command
    
    def _validate_command(self, command: str, phase: CommandPhase) -> None:
        """
        Validate generated command.
        
        Args:
            command: Command to validate
            phase: Command phase
            
        Raises:
            ValueError: If command is invalid
        """
        if not command.strip():
            return  # Empty commands are valid
        
        # Basic validation rules
        if len(command) > 10000:  # Reasonable length limit
            raise ValueError(f"Command too long for {phase.value}: {len(command)} characters")
        
        # Check for dangerous patterns
        dangerous_patterns = [";", "&&", "||", "|", ">", ">>", "<"]
        if phase == CommandPhase.RUN:
            # Allow shell operators in run commands
            dangerous_patterns = []
        
        for pattern in dangerous_patterns:
            if pattern in command and not self._is_safe_pattern(command, pattern):
                self.logger.warning(f"Potentially dangerous pattern '{pattern}' in {phase.value} command")
    
    def _is_safe_pattern(self, command: str, pattern: str) -> bool:
        """
        Check if a potentially dangerous pattern is used safely.
        
        Args:
            command: Full command string
            pattern: Pattern to check
            
        Returns:
            True if pattern usage appears safe
        """
        # Simple heuristics for safe usage
        # Could be enhanced with more sophisticated analysis
        
        if pattern in ["&&", "||"]:
            # Allow command chaining
            return True
        
        if pattern in [">", ">>"]:
            # Allow output redirection to /dev/null or log files
            return "/dev/null" in command or ".log" in command
        
        return False
    
    # === Phase-specific command builders (to be overridden) ===
    
    def _build_pre_compile_command(self) -> str:
        """Build pre-compilation command."""
        return ""
    
    def _build_compile_command(self) -> str:
        """Build compilation command."""
        return ""
    
    def _build_post_compile_command(self) -> str:
        """Build post-compilation command."""
        return ""
    
    def _build_pre_run_command(self) -> str:
        """Build pre-run command."""
        return ""
    
    def _build_run_command(self) -> str:
        """Build run command."""
        # This should be overridden by concrete implementations
        raise NotImplementedError("_build_run_command must be implemented by subclasses")
    
    def _build_post_run_command(self) -> str:
        """Build post-run command."""
        return ""
    
    # === Utility methods ===
    
    def combine_commands(self, commands: List[str], separator: Optional[str] = None) -> str:
        """
        Combine multiple commands into a single command string.
        
        Args:
            commands: List of command strings
            separator: Command separator (uses default if None)
            
        Returns:
            Combined command string
        """
        if not commands:
            return ""
        
        # Filter out empty commands
        valid_commands = [cmd.strip() for cmd in commands if cmd.strip()]
        
        if not valid_commands:
            return ""
        
        # Use provided separator or default
        sep = separator if separator is not None else self.command_separator
        
        return sep.join(valid_commands)
    
    def get_cached_command(self, phase: CommandPhase) -> Optional[str]:
        """
        Get cached command for a phase.
        
        Args:
            phase: Command phase
            
        Returns:
            Cached command or None if not cached
        """
        return self._command_cache.get(phase)
    
    def clear_command_cache(self) -> None:
        """Clear command cache."""
        self._command_cache.clear()
        self.logger.debug("Command cache cleared")
    
    def get_generation_stats(self) -> Dict[str, Any]:
        """
        Get command generation statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            "cached_commands": len(self._command_cache),
            "phases_generated": list(self._command_cache.keys()),
            "context_size": len(self._generation_context),
            "validation_enabled": self.enable_command_validation
        }
```

**File**: `/panther/plugins/services/base/service_event_mixin.py`

**ADD (New File - 200 lines)**:
```python
"""
Service Event Mixin

Consolidates event emission patterns across all service managers,
eliminating ~800 lines of duplicate event handling code.
"""

import time
import uuid
from typing import Any, Dict, Optional, TYPE_CHECKING

from panther.core.utils.logging_mixin import LoggerMixin

if TYPE_CHECKING:
    from panther.core.observer.management.event_manager import EventManager


class ServiceEventMixin(LoggerMixin):
    """
    Mixin providing standardized service event emission patterns.
    
    Eliminates event emission duplication across service managers by
    providing consistent event handling and notification methods.
    
    Responsibilities:
    - Standardized service lifecycle event emission
    - Command generation event tracking
    - Error and status event handling
    - Event context management
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Event tracking
        self._service_id = self._generate_service_id()
        self._event_sequence = 0
        self._event_context: Dict[str, Any] = {}
        
        # Event emitter validation
        self._validate_event_manager()
    
    def _generate_service_id(self) -> str:
        """Generate unique service identifier for event tracking."""
        service_name = getattr(self, 'service_name', 'unknown')
        impl_name = getattr(self, 'implementation_name', 'unknown')
        timestamp = int(time.time() * 1000)
        return f"{service_name}_{impl_name}_{timestamp}"
    
    def _validate_event_manager(self) -> None:
        """Validate event manager availability."""
        if not hasattr(self, 'event_manager'):
            self.logger.debug("No event manager available for service events")
            self.event_manager = None
        elif self.event_manager is None:
            self.logger.debug("Event manager is None, events will be logged only")
    
    # === Service Lifecycle Events ===
    
    def notify_service_started(self, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Notify that service has started.
        
        Args:
            details: Additional event details
        """
        event_data = {
            "service_id": self._service_id,
            "implementation": getattr(self, 'implementation_name', 'unknown'),
            "protocol": getattr(self.protocol, 'name', 'unknown') if hasattr(self, 'protocol') else 'unknown',
            "service_type": str(getattr(self, 'service_type', 'unknown')),
            "timestamp": time.time(),
            "sequence": self._get_next_sequence()
        }
        
        if details:
            event_data.update(details)
        
        self._emit_service_event("service_started", event_data)
        self.logger.info(f"Service {self.implementation_name} started")
    
    def notify_service_stopped(self, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Notify that service has stopped.
        
        Args:
            details: Additional event details
        """
        event_data = {
            "service_id": self._service_id,
            "implementation": getattr(self, 'implementation_name', 'unknown'),
            "timestamp": time.time(),
            "sequence": self._get_next_sequence()
        }
        
        if details:
            event_data.update(details)
        
        self._emit_service_event("service_stopped", event_data)
        self.logger.info(f"Service {self.implementation_name} stopped")
    
    def notify_service_error(self, error: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Notify that service encountered an error.
        
        Args:
            error: Error description
            details: Additional event details
        """
        event_data = {
            "service_id": self._service_id,
            "implementation": getattr(self, 'implementation_name', 'unknown'),
            "error": error,
            "timestamp": time.time(),
            "sequence": self._get_next_sequence()
        }
        
        if details:
            event_data.update(details)
        
        self._emit_service_event("service_error", event_data)
        self.logger.error(f"Service {self.implementation_name} error: {error}")
    
    def notify_service_event(self, event_type: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Notify generic service event.
        
        Args:
            event_type: Type of event
            details: Event details
        """
        event_data = {
            "service_id": self._service_id,
            "implementation": getattr(self, 'implementation_name', 'unknown'),
            "event_type": event_type,
            "timestamp": time.time(),
            "sequence": self._get_next_sequence()
        }
        
        if details:
            event_data.update(details)
        
        self._emit_service_event("service_event", event_data)
        self.logger.debug(f"Service {self.implementation_name} event: {event_type}")
    
    # === Command Generation Events ===
    
    def emit_command_generation_started(self, phase: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Emit command generation started event.
        
        Args:
            phase: Command generation phase
            details: Additional event details
        """
        event_data = {
            "service_id": self._service_id,
            "phase": phase,
            "timestamp": time.time(),
            "sequence": self._get_next_sequence()
        }
        
        if details:
            event_data.update(details)
        
        self._emit_service_event("command_generation_started", event_data)
        self.logger.debug(f"Command generation started for phase: {phase}")
    
    def emit_command_generated(self, phase: str, command: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Emit command generated event.
        
        Args:
            phase: Command generation phase
            command: Generated command
            details: Additional event details
        """
        event_data = {
            "service_id": self._service_id,
            "phase": phase,
            "command_length": len(command),
            "command_preview": command[:100] if command else "",
            "timestamp": time.time(),
            "sequence": self._get_next_sequence()
        }
        
        if details:
            event_data.update(details)
        
        self._emit_service_event("command_generated", event_data)
        self.logger.debug(f"Command generated for phase {phase}: {len(command)} chars")
    
    def emit_command_execution_started(self, command: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Emit command execution started event.
        
        Args:
            command: Command being executed
            details: Additional event details
        """
        event_data = {
            "service_id": self._service_id,
            "command_length": len(command),
            "command_preview": command[:100] if command else "",
            "timestamp": time.time(),
            "sequence": self._get_next_sequence()
        }
        
        if details:
            event_data.update(details)
        
        self._emit_service_event("command_execution_started", event_data)
    
    def emit_command_execution_completed(self, command: str, success: bool, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Emit command execution completed event.
        
        Args:
            command: Command that was executed
            success: Whether execution was successful
            details: Additional event details
        """
        event_data = {
            "service_id": self._service_id,
            "command_length": len(command),
            "success": success,
            "timestamp": time.time(),
            "sequence": self._get_next_sequence()
        }
        
        if details:
            event_data.update(details)
        
        self._emit_service_event("command_execution_completed", event_data)
    
    # === Docker Events ===
    
    def emit_docker_build_started(self, dockerfile: str, image_name: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Emit Docker build started event.
        
        Args:
            dockerfile: Path to Dockerfile
            image_name: Name of image being built
            details: Additional event details
        """
        event_data = {
            "service_id": self._service_id,
            "dockerfile": dockerfile,
            "image_name": image_name,
            "timestamp": time.time(),
            "sequence": self._get_next_sequence()
        }
        
        if details:
            event_data.update(details)
        
        self._emit_service_event("docker_build_started", event_data)
    
    def emit_docker_build_completed(self, image_name: str, success: bool, error: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Emit Docker build completed event.
        
        Args:
            image_name: Name of image that was built
            success: Whether build was successful
            error: Error message if build failed
            details: Additional event details
        """
        event_data = {
            "service_id": self._service_id,
            "image_name": image_name,
            "success": success,
            "timestamp": time.time(),
            "sequence": self._get_next_sequence()
        }
        
        if error:
            event_data["error"] = error
        
        if details:
            event_data.update(details)
        
        self._emit_service_event("docker_build_completed", event_data)
    
    # === Event Emission Infrastructure ===
    
    def _emit_service_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """
        Emit service event through event manager or log fallback.
        
        Args:
            event_type: Type of event
            event_data: Event data
        """
        # Add common context
        event_data.update(self._event_context)
        
        try:
            if self.event_manager:
                # Try to emit through event manager
                self._emit_through_event_manager(event_type, event_data)
            else:
                # Fallback to logging
                self._log_event_fallback(event_type, event_data)
                
        except Exception as e:
            self.logger.warning(f"Failed to emit event {event_type}: {e}")
            # Always fall back to logging
            self._log_event_fallback(event_type, event_data)
    
    def _emit_through_event_manager(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """
        Emit event through event manager.
        
        Args:
            event_type: Event type
            event_data: Event data
        """
        # Different event managers may have different interfaces
        if hasattr(self.event_manager, 'emit_service_event'):
            self.event_manager.emit_service_event(event_type, event_data)
        elif hasattr(self.event_manager, 'emit'):
            self.event_manager.emit(f"service.{event_type}", event_data)
        else:
            # Generic emit method
            self.event_manager.emit_event(event_type, event_data)
    
    def _log_event_fallback(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """
        Log event as fallback when event manager not available.
        
        Args:
            event_type: Event type
            event_data: Event data
        """
        service_name = event_data.get("implementation", "unknown")
        sequence = event_data.get("sequence", 0)
        self.logger.info(f"[EVENT:{sequence}] {service_name} - {event_type}: {event_data}")
    
    def _get_next_sequence(self) -> int:
        """Get next event sequence number."""
        self._event_sequence += 1
        return self._event_sequence
    
    def set_event_context(self, key: str, value: Any) -> None:
        """
        Set event context value.
        
        Args:
            key: Context key
            value: Context value
        """
        self._event_context[key] = value
    
    def get_event_context(self) -> Dict[str, Any]:
        """
        Get current event context.
        
        Returns:
            Event context dictionary
        """
        return self._event_context.copy()
    
    def clear_event_context(self) -> None:
        """Clear event context."""
        self._event_context.clear()
    
    def get_service_id(self) -> str:
        """
        Get service identifier.
        
        Returns:
            Service ID
        """
        return self._service_id
```

### Phase 3: Create Protocol-Specific Mixins

**File**: `/panther/plugins/services/base/quic_service_mixin.py`

**ADD (New File - 280 lines)**:
```python
"""
QUIC Service Mixin

Consolidates QUIC-specific functionality from all QUIC implementations,
eliminating ~1,200 lines of duplicate QUIC handling code.
"""

from typing import Any, Dict, List, Optional

from panther.core.utils.logging_mixin import LoggerMixin
from panther.plugins.services.base.parameter_extraction_mixin import ParameterExtractionMixin


class QUICServiceMixin(ParameterExtractionMixin, LoggerMixin):
    """
    Mixin providing QUIC protocol-specific functionality.
    
    Consolidates common QUIC patterns from all implementations:
    - Common QUIC parameter extraction and validation
    - Standard QUIC command argument building
    - QUIC-specific certificate handling
    - Common QUIC feature detection
    
    Eliminates ~1,200 lines of duplication across 9 QUIC implementations.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # QUIC-specific configuration
        self.quic_version = "rfc9000"  # Default QUIC version
        self.alpn_protocols = ["h3", "h3-29", "h3-32"]
        self.congestion_control = "cubic"
        self.max_stream_data = 1048576  # 1MB
        self.max_data = 16777216  # 16MB
        
        # QUIC implementation capabilities
        self.supported_features = set()
        self._initialize_quic_features()
    
    def _initialize_quic_features(self) -> None:
        """Initialize QUIC implementation features."""
        # Common QUIC features that most implementations support
        default_features = {
            "rfc9000",
            "connection_migration", 
            "stream_multiplexing",
            "flow_control",
            "loss_recovery",
            "tls13"
        }
        
        self.supported_features.update(default_features)
        
        # Implementation-specific features can be added by subclasses
        self._add_implementation_features()
    
    def _add_implementation_features(self) -> None:
        """Add implementation-specific QUIC features. Override in subclasses."""
        pass
    
    # === QUIC Parameter Extraction ===
    
    def _extract_quic_params(self, **kwargs) -> Dict[str, Any]:
        """
        Extract and validate QUIC-specific parameters.
        
        Args:
            **kwargs: Input parameters
            
        Returns:
            Validated QUIC parameters
        """
        params = self._extract_common_params(**kwargs)
        
        # QUIC-specific parameters
        params.update({
            "quic_version": kwargs.get("quic_version", self.quic_version),
            "alpn": kwargs.get("alpn", self.alpn_protocols[0]),
            "congestion_control": kwargs.get("cc", self.congestion_control),
            "max_stream_data": kwargs.get("max_stream_data", self.max_stream_data),
            "max_data": kwargs.get("max_data", self.max_data),
            "initial_rtt": kwargs.get("initial_rtt", "100ms"),
            "idle_timeout": kwargs.get("idle_timeout", "30s"),
        })
        
        # Validate QUIC version
        self._validate_quic_version(params["quic_version"])
        
        return params
    
    def _validate_quic_version(self, version: str) -> None:
        """
        Validate QUIC version.
        
        Args:
            version: QUIC version to validate
            
        Raises:
            ValueError: If version is not supported
        """
        supported_versions = {
            "rfc9000", "draft-34", "draft-32", "draft-29", 
            "draft-28", "draft-27", "v1", "h3"
        }
        
        if version not in supported_versions:
            self.logger.warning(f"QUIC version {version} may not be supported")
    
    # === QUIC Command Building ===
    
    def _build_quic_server_args(self, params: Dict[str, Any]) -> List[str]:
        """
        Build common QUIC server arguments.
        
        Args:
            params: QUIC parameters
            
        Returns:
            List of server arguments
        """
        args = []
        
        # Basic server arguments
        if "port" in params:
            args.extend(self._get_port_args(params["port"]))
        
        if "host" in params:
            args.extend(self._get_host_args(params["host"]))
        
        # QUIC-specific server arguments
        args.extend(self._get_certificate_args(params))
        args.extend(self._get_alpn_args(params))
        args.extend(self._get_congestion_control_args(params))
        args.extend(self._get_flow_control_args(params))
        
        # Add implementation-specific server arguments
        args.extend(self._get_server_specific_args(**params))
        
        return args
    
    def _build_quic_client_args(self, params: Dict[str, Any]) -> List[str]:
        """
        Build common QUIC client arguments.
        
        Args:
            params: QUIC parameters
            
        Returns:
            List of client arguments
        """
        args = []
        
        # Basic client arguments
        if "target_host" in params and "target_port" in params:
            args.extend(self._get_target_args(params["target_host"], params["target_port"]))
        
        # QUIC-specific client arguments
        args.extend(self._get_alpn_args(params))
        args.extend(self._get_congestion_control_args(params))
        args.extend(self._get_verification_args(params))
        
        # Add implementation-specific client arguments
        args.extend(self._get_client_specific_args(**params))
        
        return args
    
    # === QUIC Argument Builders ===
    
    def _get_port_args(self, port: int) -> List[str]:
        """Get port arguments. Override in subclasses for implementation-specific format."""
        return ["-p", str(port)]
    
    def _get_host_args(self, host: str) -> List[str]:
        """Get host arguments. Override in subclasses for implementation-specific format."""
        return ["-H", host]
    
    def _get_target_args(self, host: str, port: int) -> List[str]:
        """Get target arguments. Override in subclasses for implementation-specific format."""
        return [f"{host}:{port}"]
    
    def _get_certificate_args(self, params: Dict[str, Any]) -> List[str]:
        """
        Get certificate arguments for QUIC server.
        
        Args:
            params: Parameters including certificate paths
            
        Returns:
            Certificate arguments
        """
        args = []
        
        if "cert_file" in params:
            args.extend(["--cert", params["cert_file"]])
        
        if "key_file" in params:
            args.extend(["--key", params["key_file"]])
        
        if "ca_file" in params:
            args.extend(["--ca", params["ca_file"]])
        
        return args
    
    def _get_alpn_args(self, params: Dict[str, Any]) -> List[str]:
        """
        Get ALPN arguments.
        
        Args:
            params: Parameters including ALPN protocol
            
        Returns:
            ALPN arguments
        """
        if "alpn" in params:
            return ["--alpn", params["alpn"]]
        return []
    
    def _get_congestion_control_args(self, params: Dict[str, Any]) -> List[str]:
        """
        Get congestion control arguments.
        
        Args:
            params: Parameters including congestion control algorithm
            
        Returns:
            Congestion control arguments
        """
        if "congestion_control" in params and params["congestion_control"] != "cubic":
            return ["--cc", params["congestion_control"]]
        return []
    
    def _get_flow_control_args(self, params: Dict[str, Any]) -> List[str]:
        """
        Get flow control arguments.
        
        Args:
            params: Parameters including flow control settings
            
        Returns:
            Flow control arguments
        """
        args = []
        
        if "max_stream_data" in params:
            args.extend(["--max-stream-data", str(params["max_stream_data"])])
        
        if "max_data" in params:
            args.extend(["--max-data", str(params["max_data"])])
        
        return args
    
    def _get_verification_args(self, params: Dict[str, Any]) -> List[str]:
        """
        Get certificate verification arguments for client.
        
        Args:
            params: Parameters including verification settings
            
        Returns:
            Verification arguments
        """
        args = []
        
        # Most QUIC clients disable verification by default for testing
        if params.get("verify_certificates", False):
            args.append("--verify")
        else:
            args.append("--no-verify")
        
        return args
    
    # === Abstract Methods (Implementation-Specific) ===
    
    def _get_server_specific_args(self, **kwargs) -> List[str]:
        """
        Get implementation-specific server arguments.
        Must be implemented by concrete QUIC implementations.
        
        Returns:
            Implementation-specific server arguments
        """
        return []
    
    def _get_client_specific_args(self, **kwargs) -> List[str]:
        """
        Get implementation-specific client arguments.
        Must be implemented by concrete QUIC implementations.
        
        Returns:
            Implementation-specific client arguments
        """
        return []
    
    # === QUIC Feature Management ===
    
    def supports_feature(self, feature: str) -> bool:
        """
        Check if implementation supports a QUIC feature.
        
        Args:
            feature: Feature name to check
            
        Returns:
            True if feature is supported
        """
        return feature in self.supported_features
    
    def add_feature(self, feature: str) -> None:
        """
        Add supported feature.
        
        Args:
            feature: Feature to add
        """
        self.supported_features.add(feature)
        self.logger.debug(f"Added QUIC feature: {feature}")
    
    def remove_feature(self, feature: str) -> None:
        """
        Remove supported feature.
        
        Args:
            feature: Feature to remove
        """
        self.supported_features.discard(feature)
        self.logger.debug(f"Removed QUIC feature: {feature}")
    
    def get_supported_features(self) -> List[str]:
        """
        Get list of supported features.
        
        Returns:
            List of supported feature names
        """
        return sorted(list(self.supported_features))
    
    # === QUIC-Specific Command Generation ===
    
    def _build_run_command(self) -> str:
        """
        Build QUIC run command using template method pattern.
        
        Returns:
            QUIC run command
        """
        # Extract parameters from generation context
        params = self._extract_quic_params(**self._generation_context)
        
        # Get role-specific arguments
        role = getattr(self.service_config_to_test.protocol, 'role', None)
        
        if role and role.value.lower() == 'server':
            args = self._build_quic_server_args(params)
        else:
            args = self._build_quic_client_args(params)
        
        # Build command with binary name and arguments
        binary = self._get_binary_name()
        command_parts = [binary] + args
        
        return " ".join(command_parts)
    
    def _get_binary_name(self) -> str:
        """
        Get QUIC implementation binary name.
        Must be implemented by concrete implementations.
        
        Returns:
            Binary name
        """
        return getattr(self, 'implementation_name', 'quic_implementation')
    
    # === QUIC Utility Methods ===
    
    def get_quic_info(self) -> Dict[str, Any]:
        """
        Get QUIC implementation information.
        
        Returns:
            Dictionary with QUIC implementation details
        """
        return {
            "implementation": getattr(self, 'implementation_name', 'unknown'),
            "quic_version": self.quic_version,
            "supported_features": self.get_supported_features(),
            "alpn_protocols": self.alpn_protocols,
            "congestion_control": self.congestion_control,
            "max_stream_data": self.max_stream_data,
            "max_data": self.max_data
        }
```

### Phase 4: Update QUIC Implementation Example

**File**: `/panther/plugins/services/iut/quic/picoquic/picoquic.py`

**REMOVE**: Lines 1-200+ (most of current implementation)

**ADD (Replace with streamlined version - 85 lines)**:
```python
"""
PicoQUIC Service Manager

Streamlined implementation using consolidated service manager mixins.
Reduces from 250+ lines to ~85 lines through mixin composition.
"""

from pathlib import Path
from typing import Any, Dict, List

from panther.plugins.services.base.base_service_manager import BaseServiceManager
from panther.plugins.services.base.service_initialization_mixin import ServiceInitializationMixin
from panther.plugins.services.base.command_generation_mixin import CommandGenerationMixin
from panther.plugins.services.base.service_event_mixin import ServiceEventMixin
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
    CommandGenerationMixin,
    ServiceEventMixin,
    QUICServiceMixin,
    ServiceManagerDockerMixin
):
    """
    PicoQUIC service manager using mixin composition.
    
    Composition of mixins provides:
    - BaseServiceManager: Core service interface and lifecycle
    - ServiceInitializationMixin: Common initialization patterns  
    - CommandGenerationMixin: Standardized command generation
    - ServiceEventMixin: Event emission and tracking
    - QUICServiceMixin: QUIC-specific functionality
    - ServiceManagerDockerMixin: Docker integration
    
    Only implementation-specific logic remains in this class.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # PicoQUIC-specific configuration
        self.picoquic_binary = "picoquic_demo"
        self.picoquic_server_binary = "picoquic_server"
        self.picoquic_client_binary = "picoquic_client"
        
    # === Implementation-Specific Methods ===
    
    def _get_implementation_name(self) -> str:
        """Get implementation name."""
        return "picoquic"
    
    def _get_binary_name(self) -> str:
        """Get PicoQUIC binary name based on role."""
        role = getattr(self.service_config_to_test.protocol, 'role', None)
        
        if role and role.value.lower() == 'server':
            return self.picoquic_server_binary
        else:
            return self.picoquic_client_binary
    
    def _add_implementation_features(self) -> None:
        """Add PicoQUIC-specific features."""
        picoquic_features = {
            "connection_migration",
            "multipath", 
            "bbr",
            "cubic",
            "newreno",
            "pacing"
        }
        self.supported_features.update(picoquic_features)
    
    def _get_server_specific_args(self, **kwargs) -> List[str]:
        """Get PicoQUIC server-specific arguments."""
        args = []
        
        # PicoQUIC server arguments
        if kwargs.get("log_file"):
            args.extend(["-l", kwargs["log_file"]])
        
        if kwargs.get("qlog_dir"):
            args.extend(["-q", kwargs["qlog_dir"]])
        
        if kwargs.get("www_dir"):
            args.extend(["-w", kwargs["www_dir"]])
        
        # Performance tuning
        if kwargs.get("cc_algo"):
            args.extend(["-G", kwargs["cc_algo"]])
        
        return args
    
    def _get_client_specific_args(self, **kwargs) -> List[str]:
        """Get PicoQUIC client-specific arguments."""
        args = []
        
        # PicoQUIC client arguments
        if kwargs.get("output_file"):
            args.extend(["-o", kwargs["output_file"]])
        
        if kwargs.get("request_path"):
            args.append(kwargs["request_path"])
        else:
            args.append("/")  # Default request path
        
        # Client-specific performance options
        if kwargs.get("repeat_count"):
            args.extend(["-R", str(kwargs["repeat_count"])])
        
        return args
    
    # === Lifecycle Implementation ===
    
    def _validate_parameters(self, **kwargs) -> Dict[str, Any]:
        """Validate PicoQUIC-specific parameters."""
        # Use QUIC mixin for common validation
        params = self._extract_quic_params(**kwargs)
        
        # Add PicoQUIC-specific validation
        if "cc_algo" in kwargs:
            valid_algos = ["reno", "cubic", "bbr", "bbr2"]
            if kwargs["cc_algo"] not in valid_algos:
                raise ValueError(f"Invalid congestion control algorithm: {kwargs['cc_algo']}")
        
        return params
    
    def _process_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Process parameters for PicoQUIC."""
        # Apply PicoQUIC-specific parameter processing
        processed = params.copy()
        
        # Set default paths if not provided
        if "cert_file" not in processed:
            processed["cert_file"] = "/tmp/cert.pem"
        
        if "key_file" not in processed:
            processed["key_file"] = "/tmp/key.pem"
        
        return processed
    
    def _build_command(self, params: Dict[str, Any]) -> str:
        """Build PicoQUIC command using QUIC mixin."""
        # Delegate to QUIC mixin for common command building
        return self._build_run_command()
    
    def generate_deployment_commands(self) -> str:
        """Generate PicoQUIC deployment commands."""
        return self._build_picoquic_deployment()
    
    def _build_picoquic_deployment(self) -> str:
        """Build PicoQUIC-specific deployment commands."""
        commands = [
            "# PicoQUIC deployment",
            "mkdir -p /tmp/picoquic",
            "mkdir -p /tmp/qlog"
        ]
        
        return "\n".join(commands)
```

### Phase 5: Update All QUIC Implementations

Apply similar pattern to all QUIC implementations:

**Files to Update** (8 remaining QUIC implementations):
- `/panther/plugins/services/iut/quic/aioquic/aioquic.py`
- `/panther/plugins/services/iut/quic/lsquic/lsquic.py`
- `/panther/plugins/services/iut/quic/mvfst/mvfst.py`
- `/panther/plugins/services/iut/quic/quant/quant.py`
- `/panther/plugins/services/iut/quic/quic_go/quic_go.py`
- `/panther/plugins/services/iut/quic/quiche/quiche.py`
- `/panther/plugins/services/iut/quic/quinn/quinn.py`
- `/panther/plugins/services/iut/quic/picoquic_shadow/picoquic_shadow.py`

**For each file - REPLACE entire implementation with streamlined version**:

```python
# Similar pattern to PicoQUIC but with implementation-specific:
# - Binary names (_get_binary_name)
# - Specific arguments (_get_server_specific_args, _get_client_specific_args)  
# - Implementation features (_add_implementation_features)
# - Deployment commands (generate_deployment_commands)

# Result: Each implementation reduces from 200-300 lines to 60-85 lines
```

### Phase 6: Create Parameter Extraction Mixin

**File**: `/panther/plugins/services/base/parameter_extraction_mixin.py`

**ADD (New File - 150 lines)**:
```python
"""
Parameter Extraction Mixin

Consolidates common parameter extraction patterns across service managers,
eliminating ~360 lines of duplicate parameter processing code.
"""

from typing import Any, Dict, Optional

from panther.core.utils.logging_mixin import LoggerMixin


class ParameterExtractionMixin(LoggerMixin):
    """
    Mixin providing standardized parameter extraction patterns.
    
    Consolidates common parameter processing from all service managers:
    - Host/port extraction and validation
    - Certificate path handling
    - Role-based parameter extraction
    - Configuration normalization
    """
    
    def _extract_common_params(self, **kwargs) -> Dict[str, Any]:
        """
        Extract common parameters used across all service types.
        
        Args:
            **kwargs: Input parameters
            
        Returns:
            Dictionary with standardized parameter names and values
        """
        params = {}
        
        # Network parameters
        params.update(self._extract_network_params(**kwargs))
        
        # Certificate parameters
        params.update(self._extract_certificate_params(**kwargs))
        
        # Service role parameters
        params.update(self._extract_role_params(**kwargs))
        
        # Logging and debugging parameters
        params.update(self._extract_logging_params(**kwargs))
        
        # Timeout and performance parameters
        params.update(self._extract_performance_params(**kwargs))
        
        return params
    
    def _extract_network_params(self, **kwargs) -> Dict[str, Any]:
        """Extract network-related parameters."""
        params = {}
        
        # Host binding
        if "host" in kwargs:
            params["host"] = kwargs["host"]
        elif hasattr(self, 'service_config_to_test'):
            # Try to extract from service config
            config = self.service_config_to_test
            if hasattr(config, 'host'):
                params["host"] = config.host
            else:
                params["host"] = "0.0.0.0"  # Default bind to all interfaces
        
        # Port configuration
        if "port" in kwargs:
            params["port"] = int(kwargs["port"])
        elif hasattr(self, 'service_config_to_test'):
            config = self.service_config_to_test
            if hasattr(config, 'ports') and config.ports:
                # Extract port from port mapping (e.g., "4443:4443" -> 4443)
                port_str = config.ports[0].split(":")[1] if ":" in config.ports[0] else config.ports[0]
                params["port"] = int(port_str)
            else:
                params["port"] = self._get_default_port()
        
        # Target configuration (for clients)
        if "target" in kwargs:
            target = kwargs["target"]
            if isinstance(target, str):
                if ":" in target:
                    host, port = target.split(":", 1)
                    params["target_host"] = host
                    params["target_port"] = int(port)
                else:
                    params["target_host"] = target
                    params["target_port"] = params.get("port", self._get_default_port())
            
        # Extract target from service config
        elif hasattr(self, 'service_config_to_test'):
            config = self.service_config_to_test
            if hasattr(config.protocol, 'target'):
                target = config.protocol.target
                params["target_host"] = target
                params["target_port"] = params.get("port", self._get_default_port())
        
        return params
    
    def _extract_certificate_params(self, **kwargs) -> Dict[str, Any]:
        """Extract certificate-related parameters."""
        params = {}
        
        # Certificate file paths
        cert_mappings = {
            "cert_file": ["cert", "certificate", "cert_file"],
            "key_file": ["key", "private_key", "key_file"], 
            "ca_file": ["ca", "ca_cert", "ca_file"],
            "crl_file": ["crl", "crl_file"]
        }
        
        for param_name, possible_keys in cert_mappings.items():
            for key in possible_keys:
                if key in kwargs:
                    params[param_name] = kwargs[key]
                    break
        
        # Generate certificates flag
        if "generate_new_certificates" in kwargs:
            params["generate_certificates"] = kwargs["generate_new_certificates"]
        elif hasattr(self, 'service_config_to_test'):
            config = self.service_config_to_test
            if hasattr(config, 'generate_new_certificates'):
                params["generate_certificates"] = config.generate_new_certificates
        
        # Certificate verification
        params["verify_certificates"] = kwargs.get("verify", False)
        
        return params
    
    def _extract_role_params(self, **kwargs) -> Dict[str, Any]:
        """Extract role-based parameters."""
        params = {}
        
        # Service role
        if hasattr(self, 'service_config_to_test'):
            config = self.service_config_to_test
            if hasattr(config.protocol, 'role'):
                params["role"] = config.protocol.role.value.lower()
            else:
                params["role"] = "client"  # Default role
        
        # Role-specific timeout
        if "timeout" in kwargs:
            params["timeout"] = int(kwargs["timeout"])
        elif hasattr(self, 'service_config_to_test'):
            config = self.service_config_to_test
            if hasattr(config, 'timeout'):
                params["timeout"] = config.timeout
            else:
                params["timeout"] = 30  # Default timeout
        
        return params
    
    def _extract_logging_params(self, **kwargs) -> Dict[str, Any]:
        """Extract logging and debugging parameters."""
        params = {}
        
        # Logging configuration
        params["log_level"] = kwargs.get("log_level", "INFO")
        params["log_file"] = kwargs.get("log_file")
        params["debug"] = kwargs.get("debug", False)
        params["verbose"] = kwargs.get("verbose", False)
        
        # QLog and tracing
        params["qlog_dir"] = kwargs.get("qlog_dir")
        params["trace_file"] = kwargs.get("trace_file")
        
        return params
    
    def _extract_performance_params(self, **kwargs) -> Dict[str, Any]:
        """Extract performance-related parameters."""
        params = {}
        
        # Connection limits
        params["max_connections"] = kwargs.get("max_connections", 100)
        params["max_streams"] = kwargs.get("max_streams", 1000)
        
        # Buffer sizes
        params["buffer_size"] = kwargs.get("buffer_size", 65536)
        params["send_buffer"] = kwargs.get("send_buffer", params["buffer_size"])
        params["recv_buffer"] = kwargs.get("recv_buffer", params["buffer_size"])
        
        # Performance tuning
        params["nodelay"] = kwargs.get("nodelay", True)
        params["keepalive"] = kwargs.get("keepalive", False)
        
        return params
    
    def _get_default_port(self) -> int:
        """
        Get default port for the protocol.
        Override in protocol-specific mixins.
        """
        # Default HTTPS port
        return 443
    
    def _normalize_boolean_param(self, value: Any) -> bool:
        """
        Normalize parameter to boolean value.
        
        Args:
            value: Value to normalize
            
        Returns:
            Boolean value
        """
        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            return value.lower() in ["true", "yes", "1", "on", "enabled"]
        elif isinstance(value, int):
            return value != 0
        else:
            return bool(value)
    
    def _normalize_path_param(self, path: Any) -> Optional[str]:
        """
        Normalize path parameter.
        
        Args:
            path: Path value to normalize
            
        Returns:
            Normalized path string or None
        """
        if not path:
            return None
        
        path_str = str(path)
        
        # Expand user home directory
        if path_str.startswith("~"):
            import os
            path_str = os.path.expanduser(path_str)
        
        # Convert to absolute path if relative
        if not path_str.startswith("/"):
            import os
            path_str = os.path.abspath(path_str)
        
        return path_str
    
    def _validate_required_params(self, params: Dict[str, Any], required: List[str]) -> None:
        """
        Validate that required parameters are present.
        
        Args:
            params: Parameters to validate
            required: List of required parameter names
            
        Raises:
            ValueError: If required parameter is missing
        """
        missing = [param for param in required if param not in params or params[param] is None]
        
        if missing:
            raise ValueError(f"Missing required parameters: {', '.join(missing)}")
    
    def get_parameter_summary(self, **kwargs) -> Dict[str, Any]:
        """
        Get summary of extracted parameters for debugging.
        
        Returns:
            Parameter summary
        """
        params = self._extract_common_params(**kwargs)
        
        # Create summary without sensitive information
        summary = {}
        for key, value in params.items():
            if "password" in key.lower() or "secret" in key.lower():
                summary[key] = "***"
            elif "file" in key.lower() and value:
                summary[key] = f".../{value.split('/')[-1]}" if "/" in str(value) else value
            else:
                summary[key] = value
        
        return summary
```

## Testing Strategy

### Unit Tests

**File**: `/tests/unit/test_plugins/test_services/test_base/test_service_manager_consolidation.py`

**ADD (New File - 200 lines)**:
```python
"""Tests for service manager consolidation."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from panther.plugins.services.base.base_service_manager import BaseServiceManager, ServicePhase
from panther.plugins.services.base.service_initialization_mixin import ServiceInitializationMixin
from panther.plugins.services.base.command_generation_mixin import CommandGenerationMixin
from panther.plugins.services.base.service_event_mixin import ServiceEventMixin
from panther.plugins.services.base.quic_service_mixin import QUICServiceMixin


class TestServiceManagerConsolidation:
    """Test service manager consolidation mixins."""
    
    @pytest.fixture
    def mock_service_config(self):
        """Mock service configuration."""
        config = Mock()
        config.protocol = Mock()
        config.protocol.name = "quic"
        config.protocol.role = Mock()
        config.protocol.role.value = "server"
        config.timeout = 30
        config.ports = ["4443:4443"]
        return config
    
    @pytest.fixture
    def test_service_manager(self, mock_service_config):
        """Create test service manager with all mixins."""
        
        class TestServiceManager(
            BaseServiceManager,
            ServiceInitializationMixin,
            CommandGenerationMixin,
            ServiceEventMixin,
            QUICServiceMixin
        ):
            def _validate_parameters(self, **kwargs):
                return self._extract_quic_params(**kwargs)
            
            def _process_parameters(self, params):
                return params
            
            def _build_command(self, params):
                return self._build_run_command()
            
            def _do_prepare(self, plugin_manager=None):
                pass
        
        return TestServiceManager(
            service_config_to_test=mock_service_config,
            service_type="iut",
            protocol=mock_service_config.protocol,
            implementation_name="test_impl"
        )
    
    def test_mixin_composition(self, test_service_manager):
        """Test that all mixins compose correctly."""
        # Verify all mixin functionality is available
        assert hasattr(test_service_manager, 'generate_run_command')  # BaseServiceManager
        assert hasattr(test_service_manager, 'plugin_dir')  # ServiceInitializationMixin
        assert hasattr(test_service_manager, 'generate_full_lifecycle_commands')  # CommandGenerationMixin
        assert hasattr(test_service_manager, 'notify_service_started')  # ServiceEventMixin
        assert hasattr(test_service_manager, 'supports_feature')  # QUICServiceMixin
    
    def test_service_initialization(self, test_service_manager):
        """Test service initialization through mixin."""
        # Check initialization completed
        assert test_service_manager.service_name == "test_impl"
        assert test_service_manager.docker_image_name == "test_impl_latest:latest"
        assert len(test_service_manager.docker_volumes) >= 2
    
    def test_command_generation_lifecycle(self, test_service_manager):
        """Test command generation through mixin."""
        commands = test_service_manager.generate_full_lifecycle_commands(
            host="localhost",
            port=4443
        )
        
        assert isinstance(commands, dict)
        # Should have run command at minimum
        assert "run" in commands or len(commands) > 0
    
    def test_event_emission(self, test_service_manager):
        """Test event emission through mixin."""
        # Mock event manager
        test_service_manager.event_manager = Mock()
        
        # Test service started event
        test_service_manager.notify_service_started({"test": "data"})
        
        # Verify event was emitted (through mock)
        assert test_service_manager.event_manager.emit_service_event.called or \
               test_service_manager.event_manager.emit.called
    
    def test_quic_functionality(self, test_service_manager):
        """Test QUIC-specific functionality."""
        # Test feature support
        assert test_service_manager.supports_feature("rfc9000")
        
        # Test parameter extraction
        params = test_service_manager._extract_quic_params(
            host="localhost",
            port=4443,
            quic_version="rfc9000"
        )
        
        assert params["host"] == "localhost"
        assert params["port"] == 4443
        assert params["quic_version"] == "rfc9000"
    
    def test_parameter_extraction(self, test_service_manager):
        """Test parameter extraction consolidation."""
        params = test_service_manager._extract_common_params(
            host="example.com",
            port=8443,
            cert="/path/to/cert.pem",
            debug=True
        )
        
        assert params["host"] == "example.com"
        assert params["port"] == 8443
        assert params["cert_file"] == "/path/to/cert.pem"
        assert params["debug"] is True
    
    def test_lifecycle_management(self, test_service_manager):
        """Test service lifecycle management."""
        # Initial state
        assert not test_service_manager.is_prepared()
        assert not test_service_manager.is_deployed()
        
        # Test preparation
        test_service_manager.prepare()
        assert test_service_manager.is_prepared()
        
        # Test deployment
        result = test_service_manager.deploy()
        assert result is True
        assert test_service_manager.is_deployed()
        
        # Test cleanup
        test_service_manager.cleanup()
        assert not test_service_manager.is_prepared()
        assert not test_service_manager.is_deployed()


class TestQUICImplementationConsolidation:
    """Test QUIC implementation consolidation."""
    
    def test_picoquic_streamlined(self):
        """Test streamlined PicoQUIC implementation."""
        from panther.plugins.services.iut.quic.picoquic.picoquic import PicoquicServiceManager
        
        # Mock dependencies
        config = Mock()
        config.protocol = Mock()
        config.protocol.name = "quic"
        config.protocol.role = Mock()
        config.protocol.role.value = "server"
        
        # Create manager
        manager = PicoquicServiceManager(
            service_config_to_test=config,
            service_type="iut",
            protocol=config.protocol,
            implementation_name="picoquic"
        )
        
        # Verify core functionality
        assert manager._get_implementation_name() == "picoquic"
        assert manager._get_binary_name() == "picoquic_server"  # Server role
        assert manager.supports_feature("rfc9000")
        assert manager.supports_feature("connection_migration")  # PicoQUIC-specific
    
    def test_command_generation_consolidation(self):
        """Test that command generation is consolidated."""
        # This would test that QUIC implementations generate similar command structures
        # and use the same underlying logic through mixins
        pass
```

## Migration Guide

### Step 1: Install Base Classes and Mixins

1. Add all new base classes and mixins to the codebase
2. Update imports in existing service managers
3. Run tests to ensure no breaking changes

### Step 2: Migrate QUIC Implementations

**For each QUIC implementation:**

1. **Backup original file**:
   ```bash
   cp panther/plugins/services/iut/quic/picoquic/picoquic.py panther/plugins/services/iut/quic/picoquic/picoquic_original.py
   ```

2. **Replace with streamlined version** using mixin composition

3. **Test implementation**:
   ```bash
   python -m pytest tests/unit/test_plugins/test_services/test_iut/test_quic/test_picoquic.py
   ```

4. **Verify command generation** matches original behavior

### Step 3: Update Other Service Types

Apply similar consolidation to:
- HTTP service implementations
- MiniP service implementations  
- Tester service implementations

### Step 4: Remove Deprecated Code

**After all implementations are migrated:**
1. Remove original backup files
2. Update documentation
3. Run full test suite

## Expected Outcomes

### Immediate Benefits

1. **4,730+ lines of duplicate code eliminated** across service managers
2. **60-70% reduction** in QUIC implementation code size
3. **Consistent behavior** across all service implementations
4. **SOLID principles applied** throughout service management

### Code Quality Improvements

1. **Single Responsibility**: Each mixin handles one specific concern
2. **Open/Closed**: Easy to extend functionality through new mixins
3. **Liskov Substitution**: All service managers implement consistent interface
4. **Interface Segregation**: Services compose only needed functionality
5. **Dependency Inversion**: Depend on abstract mixins, not concrete implementations

### Maintenance Benefits

1. **Bug fixes applied once** affect all implementations
2. **New features added to base classes** benefit all services
3. **Testing simplified** through mixin-level unit tests
4. **Documentation consolidated** for common patterns

### Performance Impact

- **Memory usage**: 15-20% reduction through shared mixin code
- **Initialization time**: 10-15% improvement through optimized patterns
- **Command generation**: Consistent performance across implementations

## Risk Assessment

### Low Risk
- Mixin composition maintains existing API compatibility
- Comprehensive test coverage validates behavior preservation
- Gradual migration allows rollback if issues occur

### Medium Risk
- Complex mixin inheritance chains may be harder to debug
- Method resolution order (MRO) needs careful management

### Mitigation Strategies
1. **Comprehensive documentation** of mixin composition patterns
2. **Clear inheritance hierarchies** with explicit MRO validation
3. **Thorough testing** at both mixin and composed class levels
4. **Monitoring** during migration to catch any behavioral changes

## Completion Criteria

- [ ] All base classes and mixins implemented and tested
- [ ] 9 QUIC implementations migrated to mixin composition
- [ ] 4,730+ lines of duplicate code eliminated
- [ ] All existing functionality preserved and tested
- [ ] SOLID principles validated through design review
- [ ] Performance benchmarks show improvement
- [ ] Documentation updated to reflect new architecture
- [ ] Migration guide validated with actual implementation

This consolidation represents the largest code reduction opportunity in the PANTHER codebase, eliminating nearly 5,000 lines of duplication while establishing a solid foundation for future service implementations following SOLID principles and DRY patterns.