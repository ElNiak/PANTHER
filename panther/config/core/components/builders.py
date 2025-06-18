"""Configuration builders for the unified system."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from omegaconf import DictConfig, OmegaConf

from panther.core.utils.logging_mixin import LoggerMixin

from ..models import (
    ExperimentConfig,
    GlobalConfig,
    NetworkEnvironmentConfig,
    ServiceConfig,
    TestConfig,
)


class BuilderContext:
    """Context for tracking builder operations."""
    
    def __init__(self):
        """Initialize builder context."""
        self.warnings: List[str] = []
        self.fixes_applied: List[str] = []
        self.errors: List[str] = []
    
    def add_warning(self, warning: str):
        """Add a warning message."""
        self.warnings.append(warning)
    
    def add_fix(self, fix: str):
        """Add a fix description."""
        self.fixes_applied.append(fix)
    
    def add_error(self, error: str):
        """Add an error message."""
        self.errors.append(error)
    
    def has_errors(self) -> bool:
        """Check if context has errors."""
        return len(self.errors) > 0
    
    def get_summary(self) -> Dict[str, Any]:
        """Get context summary."""
        return {
            "warnings": self.warnings,
            "fixes_applied": self.fixes_applied,
            "errors": self.errors,
            "has_errors": self.has_errors()
        }


class BaseBuilder(LoggerMixin):
    """Base class for configuration builders."""
    
    def __init__(self, plugin_dir: Optional[Path] = None):
        """Initialize builder.
        
        Args:
            plugin_dir: Plugin directory path
        """
        super().__init__()
        self.plugin_dir = plugin_dir or Path("panther/plugins")
        self.context = BuilderContext()
    
    def reset_context(self):
        """Reset builder context."""
        self.context = BuilderContext()


class ExperimentBuilder(BaseBuilder):
    """Builder for experiment configurations with auto-fix support."""
    
    def build(self, config_dict: Dict[str, Any], auto_fix: bool = True) -> ExperimentConfig:
        """Build experiment configuration with auto-fix.
        
        Args:
            config_dict: Raw configuration dictionary
            auto_fix: Whether to apply automatic fixes
            
        Returns:
            Built ExperimentConfig
        """
        self.reset_context()
        self.logger.info("Building experiment configuration")
        
        # Apply fixes if enabled
        if auto_fix:
            config_dict = self._apply_auto_fixes(config_dict)
        
        # Build tests
        if 'tests' in config_dict:
            config_dict['tests'] = [
                self._build_test(test_dict, auto_fix) for test_dict in config_dict['tests']
            ]
        
        # Create ExperimentConfig
        try:
            experiment_config = ExperimentConfig(**config_dict)
            
            if self.context.warnings:
                self.logger.warning(f"Built with {len(self.context.warnings)} warnings")
            if self.context.fixes_applied:
                self.logger.info(f"Applied {len(self.context.fixes_applied)} fixes")
            
            return experiment_config
        except Exception as e:
            self.context.add_error(str(e))
            raise ValueError(f"Failed to build experiment configuration: {e}")
    
    def _apply_auto_fixes(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Apply automatic fixes to experiment config.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            Fixed configuration
        """
        # Ensure tests array exists
        if 'tests' not in config_dict or not config_dict['tests']:
            self.context.add_error("No tests defined")
            config_dict['tests'] = []
        
        return config_dict
    
    def _build_test(self, test_dict: Dict[str, Any], auto_fix: bool) -> TestConfig:
        """Build test configuration.
        
        Args:
            test_dict: Test configuration dictionary
            auto_fix: Whether to apply fixes
            
        Returns:
            Built TestConfig
        """
        # Apply test-level fixes
        if auto_fix:
            test_dict = self._apply_test_fixes(test_dict)
        
        # Build network environment
        if 'network_environment' in test_dict:
            test_dict['network_environment'] = self._build_network_environment(
                test_dict['network_environment']
            )
        
        # Build services
        if 'services' in test_dict:
            test_dict['services'] = {
                name: self._build_service(service_dict, auto_fix, service_name=name)
                for name, service_dict in test_dict['services'].items()
            }
        
        return TestConfig(**test_dict)
    
    def _apply_test_fixes(self, test_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Apply automatic fixes to test config.
        
        Args:
            test_dict: Test configuration dictionary
            
        Returns:
            Fixed configuration
        """
        # Ensure required fields
        if 'name' not in test_dict:
            test_dict['name'] = "unnamed_test"
            self.context.add_fix("Added default test name")
        
        if 'network_environment' not in test_dict:
            test_dict['network_environment'] = {'type': 'docker_compose'}
            self.context.add_fix("Added default network environment")
        
        if 'services' not in test_dict:
            test_dict['services'] = {}
            self.context.add_warning("Test has no services defined")
        
        return test_dict
    
    def _build_network_environment(self, env_dict: Dict[str, Any]) -> NetworkEnvironmentConfig:
        """Build network environment configuration.
        
        Args:
            env_dict: Environment configuration dictionary
            
        Returns:
            Built NetworkEnvironmentConfig
        """
        env_type = env_dict.get('type', 'docker_compose')
        
        # Dynamically import configs from plugin directories
        try:
            if env_type == 'docker_compose':
                from panther.plugins.environments.network_environment.docker_compose.config_schema import DockerComposeConfig
                config_class = DockerComposeConfig
            elif env_type == 'localhost_single_container':
                from panther.plugins.environments.network_environment.localhost_single_container.config_schema import LocalhostSingleContainerConfig
                config_class = LocalhostSingleContainerConfig
            elif env_type == 'shadow_ns':
                from panther.plugins.environments.network_environment.shadow_ns.config_schema import ShadowNSConfig
                config_class = ShadowNSConfig
            else:
                # Fallback to base class
                config_class = NetworkEnvironmentConfig
                self.context.add_warning(f"Unknown network environment type '{env_type}', using base class")
        except ImportError as e:
            self.logger.error(f"Failed to import config for environment type '{env_type}': {e}")
            config_class = NetworkEnvironmentConfig
            self.context.add_error(f"Could not load config class for '{env_type}'")
        
        return config_class(**env_dict)
    
    def _build_service(self, service_dict: Dict[str, Any], auto_fix: bool, service_name: str = None) -> ServiceConfig:
        """Build service configuration.
        
        Args:
            service_dict: Service configuration dictionary
            auto_fix: Whether to apply fixes
            service_name: Service name from the YAML key
            
        Returns:
            Built ServiceConfig
        """
        service_builder = ServiceBuilder(self.plugin_dir)
        return service_builder.build(service_dict, auto_fix, service_name)


class ServiceBuilder(BaseBuilder):
    """Builder for service configurations with field preservation."""
    
    def build(self, service_dict: Dict[str, Any], auto_fix: bool = True, service_name: str = None) -> ServiceConfig:
        """Build service configuration preserving all fields.
        
        Args:
            service_dict: Service configuration dictionary
            auto_fix: Whether to apply automatic fixes
            service_name: Service name from the YAML key
            
        Returns:
            Built ServiceConfig
        """
        self.reset_context()
        
        # If no explicit name is provided in the service_dict, use the service_name from the YAML key
        if 'name' not in service_dict and service_name:
            service_dict['name'] = service_name
            self.context.add_fix(f"Added service name '{service_name}' from YAML key")
        
        # Apply fixes if enabled
        if auto_fix:
            service_dict = self._apply_auto_fixes(service_dict)
        
        # Build sub-components
        if 'implementation' in service_dict:
            service_dict['implementation'] = self._build_implementation(service_dict['implementation'])
        
        if 'protocol' in service_dict:
            service_dict['protocol'] = self._build_protocol(service_dict['protocol'])
        
        # Create ServiceConfig
        try:
            return ServiceConfig(**service_dict)
        except Exception as e:
            self.context.add_error(str(e))
            raise ValueError(f"Failed to build service configuration: {e}")
    
    def _apply_auto_fixes(self, service_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Apply automatic fixes to service config.
        
        Args:
            service_dict: Service configuration dictionary
            
        Returns:
            Fixed configuration
        """
        # Fix missing implementation
        if 'implementation' not in service_dict:
            self.context.add_error("Missing implementation configuration")
            service_dict['implementation'] = {'name': 'unknown', 'type': 'iut'}
        
        # Fix missing protocol
        if 'protocol' not in service_dict:
            self.context.add_error("Missing protocol configuration")
            service_dict['protocol'] = {'name': 'unknown', 'role': 'server'}
        
        # Fix server port mappings
        protocol = service_dict.get('protocol', {})
        if protocol.get('role') == 'server' and not service_dict.get('ports'):
            # Get default port from protocol
            protocol_name = protocol.get('name', 'unknown')
            default_ports = {
                'quic': '4443:4443',
                'http': '80:80',
                'https': '443:443',
            }
            
            if protocol_name in default_ports:
                service_dict['ports'] = [default_ports[protocol_name]]
                self.context.add_fix(f"Added default port mapping for {protocol_name} server")
        
        return service_dict
    
    def _build_implementation(self, impl_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Build implementation configuration.
        
        Args:
            impl_dict: Implementation dictionary
            
        Returns:
            Built implementation dict
        """
        # Ensure required fields
        if 'name' not in impl_dict:
            impl_dict['name'] = 'unknown'
            self.context.add_warning("Implementation missing name")
        
        if 'type' not in impl_dict:
            impl_dict['type'] = 'iut'
            self.context.add_fix("Added default implementation type")
        
        return impl_dict
    
    def _build_protocol(self, proto_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Build protocol configuration.
        
        Args:
            proto_dict: Protocol dictionary
            
        Returns:
            Built protocol dict
        """
        # Ensure required fields
        if 'name' not in proto_dict:
            proto_dict['name'] = 'unknown'
            self.context.add_warning("Protocol missing name")
        
        if 'role' not in proto_dict:
            proto_dict['role'] = 'server'
            self.context.add_fix("Added default protocol role")
        
        # Fix client target
        if proto_dict.get('role') == 'client' and not proto_dict.get('target'):
            self.context.add_warning("Client service missing target")
        
        return proto_dict


class GlobalConfigBuilder(BaseBuilder):
    """Builder for global configuration with environment variable resolution."""
    
    def build(self, config_dict: Dict[str, Any], resolve_env: bool = True) -> GlobalConfig:
        """Build global configuration.
        
        Args:
            config_dict: Configuration dictionary
            resolve_env: Whether to resolve environment variables
            
        Returns:
            Built GlobalConfig
        """
        self.reset_context()
        self.logger.info("Building global configuration")
        
        # Apply environment variables if requested
        if resolve_env:
            config_dict = self._resolve_environment_variables(config_dict)
        
        # Apply defaults
        config_dict = self._apply_defaults(config_dict)
        
        # Create GlobalConfig
        try:
            global_config = GlobalConfig(**config_dict)
            
            # Resolve paths
            global_config = global_config.resolve_paths()
            
            return global_config
        except Exception as e:
            self.context.add_error(str(e))
            raise ValueError(f"Failed to build global configuration: {e}")
    
    def _resolve_environment_variables(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve environment variables in configuration.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            Configuration with environment variables resolved
        """
        import os
        
        # Environment variable mappings
        env_mappings = {
            'PANTHER_LOG_LEVEL': 'logging.level',
            'PANTHER_OUTPUT_DIR': 'paths.output_dir',
            'PANTHER_PLUGIN_DIR': 'paths.plugin_dir',
            'PANTHER_BUILD_IMAGES': 'docker.build_docker_image',
            'PANTHER_FAST_FAIL': 'fast_fail.enabled',
        }
        
        # Create OmegaConf for easier manipulation
        omega_config = OmegaConf.create(config_dict)
        
        # Apply environment variables
        for env_var, config_path in env_mappings.items():
            env_value = os.environ.get(env_var)
            if env_value is not None:
                try:
                    OmegaConf.update(omega_config, config_path, env_value, merge=False)
                    self.context.add_fix(f"Applied {env_var} to {config_path}")
                except Exception as e:
                    self.context.add_warning(f"Failed to apply {env_var}: {e}")
        
        return OmegaConf.to_container(omega_config, resolve=True)
    
    def _apply_defaults(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Apply default values to global config.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            Configuration with defaults
        """
        # Default structure
        defaults = {
            'version': '1.0',
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s [%(levelname)s] - %(module)s - %(message)s',
                'enable_colors': True,
            },
            'paths': {
                'output_dir': 'outputs',
                'plugin_dir': 'panther/plugins',
            },
            'docker': {
                'build_docker_image': False,
            },
            'progress': {
                'enable_progress_bar': True,
                'redirect_logging': True,
            },
            'fast_fail': {
                'enabled': True,
                'test_level': False,
            },
            'metrics': {
                'enabled': True,
            }
        }
        
        # Merge with defaults
        merged = OmegaConf.merge(
            OmegaConf.create(defaults),
            OmegaConf.create(config_dict)
        )
        
        return OmegaConf.to_container(merged, resolve=False)