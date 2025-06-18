"""Experiment configuration builder."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

from omegaconf import DictConfig

from panther.config.builders.base_builder import (
    AbstractConfigBuilder,
    BuildContext,
    FluentConfigBuilder,
)
from panther.config.loaders import (
    ExperimentYAMLLoader,
    VersionConfigLoader,
    YAMLConfigLoader,
)
from panther.config.models.experiment import ExperimentConfigModel, TestConfigModel
from panther.config.models.service import ServiceConfigModel
from panther.config.validators import BusinessRulesValidator, PydanticValidator


class ExperimentConfigBuilder(FluentConfigBuilder):
    """Builder for experiment configurations with enhanced capabilities."""
    
    def __init__(self, plugin_dir: Optional[Union[str, Path]] = None):
        super().__init__("ExperimentConfigBuilder")
        
        # Initialize loaders
        self.experiment_loader = ExperimentYAMLLoader()
        self.version_loader = VersionConfigLoader(plugin_dir)
        
        # Set up default loaders and validators
        self.with_loader(self.experiment_loader)
        self.with_validator(PydanticValidator(ExperimentConfigModel))
        self.with_validator(BusinessRulesValidator())
        
        # Builder-specific state
        self._auto_fix_services = True
        self._resolve_version_configs = True
        self._validate_plugin_compatibility = True
    
    def get_target_model_class(self) -> Type[ExperimentConfigModel]:
        """Get the target model class."""
        return ExperimentConfigModel
    
    def with_auto_fix(self, enabled: bool = True) -> "ExperimentConfigBuilder":
        """Enable or disable automatic service configuration fixes.
        
        Args:
            enabled: Whether to enable auto-fix
            
        Returns:
            Self for method chaining
        """
        self._auto_fix_services = enabled
        return self
    
    def with_version_resolution(self, enabled: bool = True) -> "ExperimentConfigBuilder":
        """Enable or disable automatic version configuration resolution.
        
        Args:
            enabled: Whether to enable version resolution
            
        Returns:
            Self for method chaining
        """
        self._resolve_version_configs = enabled
        return self
    
    def with_plugin_validation(self, enabled: bool = True) -> "ExperimentConfigBuilder":
        """Enable or disable plugin compatibility validation.
        
        Args:
            enabled: Whether to enable plugin validation
            
        Returns:
            Self for method chaining
        """
        self._validate_plugin_compatibility = enabled
        return self
    
    def add_test(
        self, 
        name: str, 
        services: Dict[str, Dict[str, Any]], 
        network_environment: Dict[str, Any],
        **kwargs
    ) -> "ExperimentConfigBuilder":
        """Add a test configuration programmatically.
        
        Args:
            name: Test name
            services: Service configurations
            network_environment: Network environment configuration
            **kwargs: Additional test parameters
            
        Returns:
            Self for method chaining
        """
        test_config = {
            "name": name,
            "services": services,
            "network_environment": network_environment,
            **kwargs
        }
        
        if not hasattr(self, '_additional_tests'):
            self._additional_tests = []
        self._additional_tests.append(test_config)
        
        return self
    
    def generate_test_matrix(
        self,
        implementations: List[str],
        protocols: List[str],
        network_environments: List[Dict[str, Any]],
        base_test_name: str = "generated_test"
    ) -> "ExperimentConfigBuilder":
        """Generate a matrix of tests from combinations of parameters.
        
        Args:
            implementations: List of implementation names
            protocols: List of protocol names
            network_environments: List of network environment configs
            base_test_name: Base name for generated tests
            
        Returns:
            Self for method chaining
        """
        test_counter = 0
        
        for impl in implementations:
            for protocol in protocols:
                for net_env in network_environments:
                    test_counter += 1
                    test_name = f"{base_test_name}_{impl}_{protocol}_{test_counter}"
                    
                    # Generate basic client-server test
                    services = {
                        "server": {
                            "implementation": {"name": impl, "type": "iut"},
                            "protocol": {"name": protocol, "role": "server"},
                            "ports": ["4443:4443"]
                        },
                        "client": {
                            "implementation": {"name": impl, "type": "iut"},
                            "protocol": {"name": protocol, "role": "client", "target": "server"}
                        }
                    }
                    
                    self.add_test(test_name, services, net_env)
        
        self.logger.info(f"Generated {test_counter} tests from matrix")
        return self
    
    def build(self) -> ExperimentConfigModel:
        """Build experiment configuration with enhancements.
        
        Returns:
            Built and validated experiment configuration
        """
        # Build base configuration
        experiment_config = super().build()
        
        # Apply enhancements
        if self._auto_fix_services:
            experiment_config = self._auto_fix_service_configs(experiment_config)
        
        if self._resolve_version_configs:
            experiment_config = self._resolve_version_configurations(experiment_config)
        
        # Add programmatically generated tests
        if hasattr(self, '_additional_tests'):
            for test_config in self._additional_tests:
                test_model = TestConfigModel.from_dict(test_config)
                experiment_config.tests.append(test_model)
        
        # Final validation
        final_validation = self.validate(experiment_config)
        if not final_validation.is_valid:
            error_summary = final_validation.format_errors()
            raise ValueError(f"Final experiment validation failed:\n{error_summary}")
        
        return experiment_config
    
    def _auto_fix_service_configs(
        self, 
        experiment_config: ExperimentConfigModel
    ) -> ExperimentConfigModel:
        """Automatically fix common service configuration issues.
        
        Args:
            experiment_config: Experiment configuration to fix
            
        Returns:
            Fixed experiment configuration
        """
        fixes_applied = 0
        
        for test in experiment_config.tests:
            for service_name, service in test.services.items():
                # Auto-assign ports to servers
                if not service.ports and service.protocol.requires_server_port():
                    default_port = service.get_protocol_default_port()
                    if default_port:
                        service.ports = [default_port]
                        fixes_applied += 1
                        self._context.add_warning(
                            f"Auto-assigned port {default_port} to server {service_name}"
                        )
                
                # Auto-set certificate generation for QUIC/TLS protocols
                if service.protocol.name.lower() in ["quic", "https"] and not service.generate_new_certificates:
                    service.generate_new_certificates = True
                    fixes_applied += 1
                    self._context.add_warning(
                        f"Auto-enabled certificate generation for {service_name}"
                    )
        
        if fixes_applied > 0:
            self.logger.info(f"Applied {fixes_applied} automatic service configuration fixes")
        
        return experiment_config
    
    def _resolve_version_configurations(
        self, 
        experiment_config: ExperimentConfigModel
    ) -> ExperimentConfigModel:
        """Resolve version-specific configurations for services.
        
        Args:
            experiment_config: Experiment configuration
            
        Returns:
            Configuration with version configs resolved
        """
        version_configs_loaded = 0
        
        for test in experiment_config.tests:
            for service_name, service in test.services.items():
                if service.protocol.version:
                    # Load version configuration
                    version_config = self.version_loader.load_version_config(
                        service.implementation.name,
                        service.implementation.type,
                        service.protocol.name,
                        service.protocol.version
                    )
                    
                    if version_config:
                        # Merge version-specific parameters
                        service.parameters.update(version_config.parameters)
                        service.environment.update(version_config.environment)
                        
                        # Add build args if present
                        if version_config.build_args:
                            service.parameters["build_args"] = version_config.build_args
                        
                        version_configs_loaded += 1
                        self.logger.debug(
                            f"Loaded version config for {service_name}: "
                            f"{service.protocol.name} {service.protocol.version}"
                        )
        
        if version_configs_loaded > 0:
            self.logger.info(f"Loaded {version_configs_loaded} version configurations")
            self._context.set_metadata("version_configs_loaded", version_configs_loaded)
        
        return experiment_config
    
    def _validate_plugin_compatibility(
        self, 
        experiment_config: ExperimentConfigModel
    ) -> None:
        """Validate plugin compatibility for all services.
        
        Args:
            experiment_config: Experiment configuration to validate
        """
        if not self._validate_plugin_compatibility:
            return
        
        compatibility_issues = []
        
        for test in experiment_config.tests:
            # Check network environment compatibility
            net_env_type = test.network_environment.get("type")
            
            for service_name, service in test.services.items():
                # Check Shadow NS compatibility
                if net_env_type == "shadow_ns" and not service.implementation.shadow_compatible:
                    compatibility_issues.append(
                        f"Service {service_name} may not be compatible with Shadow NS"
                    )
                
                # Check execution environment compatibility
                for exec_env in test.execution_environments:
                    exec_env_type = exec_env.get("type")
                    
                    if exec_env_type in ["gperf_cpu", "gperf_heap"]:
                        if not service.implementation.gperf_compatible:
                            compatibility_issues.append(
                                f"Service {service_name} may not support {exec_env_type} profiling"
                            )
        
        if compatibility_issues:
            for issue in compatibility_issues:
                self._context.add_warning(issue)
            self.logger.warning(f"Found {len(compatibility_issues)} compatibility concerns")


class TestConfigBuilder(AbstractConfigBuilder):
    """Builder for individual test configurations."""
    
    def __init__(self):
        super().__init__("TestConfigBuilder")
        
        # Set up validators
        self.with_validator(PydanticValidator(TestConfigModel))
        self.with_validator(BusinessRulesValidator())
        
        # Test building state
        self._services: Dict[str, Dict[str, Any]] = {}
        self._network_environment: Optional[Dict[str, Any]] = None
        self._execution_environments: List[Dict[str, Any]] = []
    
    def get_target_model_class(self) -> Type[TestConfigModel]:
        """Get the target model class."""
        return TestConfigModel
    
    def with_name(self, name: str) -> "TestConfigBuilder":
        """Set test name.
        
        Args:
            name: Test name
            
        Returns:
            Self for method chaining
        """
        self._overrides["name"] = name
        return self
    
    def with_description(self, description: str) -> "TestConfigBuilder":
        """Set test description.
        
        Args:
            description: Test description
            
        Returns:
            Self for method chaining
        """
        self._overrides["description"] = description
        return self
    
    def add_service(
        self, 
        name: str, 
        implementation: str, 
        protocol: str, 
        role: str,
        **kwargs
    ) -> "TestConfigBuilder":
        """Add a service to the test.
        
        Args:
            name: Service name
            implementation: Implementation name
            protocol: Protocol name
            role: Protocol role (server/client)
            **kwargs: Additional service parameters
            
        Returns:
            Self for method chaining
        """
        service_config = {
            "implementation": {"name": implementation, "type": "iut"},
            "protocol": {"name": protocol, "role": role},
            **kwargs
        }
        
        self._services[name] = service_config
        return self
    
    def with_network_environment(
        self, 
        env_type: str, 
        **kwargs
    ) -> "TestConfigBuilder":
        """Set network environment.
        
        Args:
            env_type: Environment type (docker_compose, shadow_ns, etc.)
            **kwargs: Environment-specific parameters
            
        Returns:
            Self for method chaining
        """
        self._network_environment = {"type": env_type, **kwargs}
        return self
    
    def add_execution_environment(
        self, 
        env_type: str, 
        **kwargs
    ) -> "TestConfigBuilder":
        """Add an execution environment.
        
        Args:
            env_type: Environment type (strace, gperf_cpu, etc.)
            **kwargs: Environment-specific parameters
            
        Returns:
            Self for method chaining
        """
        self._execution_environments.append({"type": env_type, **kwargs})
        return self
    
    def build(self) -> TestConfigModel:
        """Build the test configuration.
        
        Returns:
            Built and validated test configuration
        """
        if not self._services:
            raise ValueError("Test must have at least one service")
        
        if not self._network_environment:
            # Default to docker_compose
            self._network_environment = {"type": "docker_compose"}
            self._context.add_warning("No network environment specified, defaulting to docker_compose")
        
        # Build configuration dictionary
        config_dict = {
            "services": self._services,
            "network_environment": self._network_environment,
            "execution_environments": self._execution_environments,
        }
        
        # Apply overrides
        config_dict.update(self._overrides)
        
        # Apply defaults
        if self._defaults:
            merged_config = self._merge_configurations(self._defaults, config_dict)
        else:
            merged_config = DictConfig(config_dict)
        
        # Build model
        model = self._build_model(merged_config)
        
        # Validate
        validation_result = self.validate(model)
        if not validation_result.is_valid:
            error_summary = validation_result.format_errors()
            raise ValueError(f"Test configuration validation failed:\n{error_summary}")
        
        return model