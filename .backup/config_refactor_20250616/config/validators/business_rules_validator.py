"""Business rules validator for complex configuration validation."""

import re
from typing import Any, Dict, List, Optional, Set

from panther.config.models.experiment import ExperimentConfigModel, TestConfigModel
from panther.config.models.global_config import CompleteConfigModel, GlobalConfigModel
from panther.config.models.implementation import ProtocolRole
from panther.config.models.service import ServiceConfigModel
from panther.config.validators.base_validator import (
    AbstractValidator,
    ValidationContext,
    ValidationResult,
)


class BusinessRulesValidator(AbstractValidator):
    """Validator for business logic and cross-field validation rules."""
    
    def __init__(self, name: Optional[str] = None):
        super().__init__(name or "BusinessRulesValidator")
    
    def validate(
        self, 
        config: Any, 
        context: Optional[ValidationContext] = None
    ) -> ValidationResult:
        """Validate business rules for the configuration.
        
        Args:
            config: Configuration to validate
            context: Optional validation context
            
        Returns:
            Validation result with business rule violations
        """
        result = ValidationResult(context=context)
        
        if isinstance(config, dict):
            config = self._convert_dict_to_models(config)
        
        if isinstance(config, CompleteConfigModel):
            self._validate_complete_config(config, result)
        elif isinstance(config, ExperimentConfigModel):
            self._validate_experiment_config(config, result)
        elif isinstance(config, TestConfigModel):
            self._validate_test_config(config, result)
        elif isinstance(config, ServiceConfigModel):
            self._validate_service_config(config, result)
        elif isinstance(config, GlobalConfigModel):
            self._validate_global_config(config, result)
        else:
            result.add_warning(
                f"Business rules validation not implemented for type: {type(config)}",
                error_code="UNSUPPORTED_TYPE"
            )
        
        return result
    
    def _convert_dict_to_models(self, config: Dict[str, Any]) -> Any:
        """Convert dictionary configuration to appropriate model."""
        if "global_config" in config or "experiment_config" in config:
            return CompleteConfigModel.from_dict(config)
        elif "tests" in config:
            return ExperimentConfigModel.from_dict(config)
        elif "services" in config and "network_environment" in config:
            return TestConfigModel.from_dict(config)
        elif "implementation" in config and "protocol" in config:
            return ServiceConfigModel.from_dict(config)
        else:
            # Try global config
            return GlobalConfigModel.from_dict(config)
    
    def _validate_complete_config(
        self, 
        config: CompleteConfigModel, 
        result: ValidationResult
    ) -> None:
        """Validate complete configuration business rules."""
        # Validate global config
        self._validate_global_config(config.global_config, result)
        
        # Validate experiment config
        self._validate_experiment_config(config.experiment_config, result)
        
        # Cross-validation between global and experiment configs
        self._validate_global_experiment_consistency(config, result)
    
    def _validate_experiment_config(
        self, 
        config: ExperimentConfigModel, 
        result: ValidationResult
    ) -> None:
        """Validate experiment configuration business rules."""
        # Validate each test
        for i, test in enumerate(config.tests):
            test_context = f"tests[{i}]"
            self._validate_test_config(test, result, test_context)
        
        # Validate test name uniqueness (already done in model, but double-check)
        test_names = [test.name for test in config.tests]
        duplicates = [name for name in test_names if test_names.count(name) > 1]
        if duplicates:
            result.add_error(
                f"Duplicate test names found: {set(duplicates)}",
                field_path="tests",
                suggestion="Ensure all test names are unique within the experiment"
            )
        
        # Validate cross-test port conflicts
        self._validate_cross_test_port_conflicts(config.tests, result)
    
    def _validate_test_config(
        self, 
        config: TestConfigModel, 
        result: ValidationResult,
        context_prefix: str = ""
    ) -> None:
        """Validate test configuration business rules."""
        prefix = f"{context_prefix}." if context_prefix else ""
        
        # Validate service relationships
        self._validate_service_relationships(config.services, result, f"{prefix}services")
        
        # Validate port assignments
        self._validate_port_assignments(config.services, result, f"{prefix}services")
        
        # Validate environment compatibility
        self._validate_environment_compatibility(config, result, prefix)
        
        # Validate service configuration consistency
        for service_name, service in config.services.items():
            service_context = f"{prefix}services.{service_name}"
            self._validate_service_config(service, result, service_context)
    
    def _validate_service_config(
        self, 
        config: ServiceConfigModel, 
        result: ValidationResult,
        context_prefix: str = ""
    ) -> None:
        """Validate service configuration business rules."""
        prefix = f"{context_prefix}." if context_prefix else ""
        
        # Validate protocol-implementation compatibility
        self._validate_protocol_implementation_compatibility(config, result, prefix)
        
        # Validate server port requirements
        if config.protocol.role == ProtocolRole.SERVER and not config.ports:
            default_port = config.get_protocol_default_port()
            if default_port:
                result.add_warning(
                    f"Server service '{config.name}' has no ports configured",
                    field_path=f"{prefix}ports",
                    suggestion=f"Add port mapping like '{default_port}' or use auto-configuration"
                )
            else:
                result.add_error(
                    f"Server service '{config.name}' must have at least one port configured",
                    field_path=f"{prefix}ports",
                    suggestion="Add a port mapping in format 'host:container'"
                )
        
        # Validate client target requirements
        if config.protocol.role == ProtocolRole.CLIENT:
            if not config.protocol.target:
                result.add_error(
                    f"Client service '{config.name}' must specify a target service",
                    field_path=f"{prefix}protocol.target",
                    suggestion="Add the name of the server service this client should connect to"
                )
        
        # Validate certificate configuration
        if config.generate_new_certificates and config.certificate_path:
            result.add_warning(
                f"Service '{config.name}' has both generate_new_certificates=true and certificate_path set",
                field_path=f"{prefix}certificate_path",
                suggestion="Use either certificate generation or existing certificates, not both"
            )
    
    def _validate_global_config(
        self, 
        config: GlobalConfigModel, 
        result: ValidationResult
    ) -> None:
        """Validate global configuration business rules."""
        # Validate logging level consistency
        global_level = config.logging.level
        observer_level = config.observers.logger.log_level
        
        # Check if observer level is less restrictive than global
        level_values = {
            "DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50
        }
        
        if level_values[global_level.value] > level_values[observer_level.value]:
            result.add_warning(
                "Logger observer level is less restrictive than global logging level",
                field_path="observers.logger.log_level",
                suggestion=f"Consider setting logger level to '{global_level.value}' or higher"
            )
        
        # Validate Docker user mapping
        user_mapping = config.docker.user_mapping
        if user_mapping.run_as_host_user and (user_mapping.custom_uid or user_mapping.custom_gid):
            result.add_warning(
                "Both run_as_host_user and custom UID/GID are set",
                field_path="docker.user_mapping",
                suggestion="Use either host user mapping or custom UID/GID, not both"
            )
        
        # Validate fast-fail configuration
        if config.fast_fail.enabled and config.fast_fail.grace_period > 300:
            result.add_warning(
                "Fast-fail grace period is quite long (>5 minutes)",
                field_path="fast_fail.grace_period",
                suggestion="Consider a shorter grace period for faster failure detection"
            )
    
    def _validate_service_relationships(
        self, 
        services: Dict[str, ServiceConfigModel], 
        result: ValidationResult,
        context_prefix: str = ""
    ) -> None:
        """Validate service relationship consistency."""
        service_names = set(services.keys())
        
        for service_name, service in services.items():
            if service.protocol.target:
                target_name = service.protocol.target
                
                if target_name not in service_names:
                    result.add_error(
                        f"Service '{service_name}' targets non-existent service '{target_name}'",
                        field_path=f"{context_prefix}.{service_name}.protocol.target",
                        suggestion=f"Available services: {sorted(service_names)}"
                    )
                    continue
                
                target_service = services[target_name]
                
                # Check protocol compatibility
                if not service.is_compatible_with(target_service):
                    result.add_error(
                        f"Service '{service_name}' is not compatible with target '{target_name}'",
                        field_path=f"{context_prefix}.{service_name}.protocol",
                        suggestion="Ensure both services use compatible protocols and versions"
                    )
                
                # Check role compatibility
                if service.protocol.role == target_service.protocol.role:
                    result.add_error(
                        f"Service '{service_name}' and target '{target_name}' have the same role",
                        field_path=f"{context_prefix}.{service_name}.protocol.role",
                        suggestion="Client services should target server services"
                    )
    
    def _validate_port_assignments(
        self, 
        services: Dict[str, ServiceConfigModel], 
        result: ValidationResult,
        context_prefix: str = ""
    ) -> None:
        """Validate port assignment uniqueness and validity."""
        used_host_ports = {}
        
        for service_name, service in services.items():
            for port_mapping in service.ports:
                # Parse port mapping
                if ":" in port_mapping:
                    host_port, container_port = port_mapping.split(":", 1)
                else:
                    host_port = container_port = port_mapping
                
                try:
                    host_port_num = int(host_port)
                    container_port_num = int(container_port)
                except ValueError:
                    result.add_error(
                        f"Invalid port format in service '{service_name}': {port_mapping}",
                        field_path=f"{context_prefix}.{service_name}.ports",
                        suggestion="Use format 'host:container' or just 'port'"
                    )
                    continue
                
                # Check for port conflicts
                if host_port_num in used_host_ports:
                    conflicting_service = used_host_ports[host_port_num]
                    result.add_error(
                        f"Port conflict: services '{service_name}' and '{conflicting_service}' both use host port {host_port_num}",
                        field_path=f"{context_prefix}.{service_name}.ports",
                        suggestion=f"Use a different host port for service '{service_name}'"
                    )
                else:
                    used_host_ports[host_port_num] = service_name
                
                # Check for privileged ports
                if host_port_num < 1024:
                    result.add_warning(
                        f"Service '{service_name}' uses privileged port {host_port_num}",
                        field_path=f"{context_prefix}.{service_name}.ports",
                        suggestion="Consider using non-privileged ports (>= 1024) for better security"
                    )
    
    def _validate_environment_compatibility(
        self, 
        config: TestConfigModel, 
        result: ValidationResult,
        context_prefix: str = ""
    ) -> None:
        """Validate environment compatibility with services."""
        network_env_type = config.network_environment.get("type")
        
        # Check Shadow NS compatibility
        if network_env_type == "shadow_ns":
            for service_name, service in config.services.items():
                if not service.implementation.shadow_compatible:
                    result.add_warning(
                        f"Service '{service_name}' may not be compatible with Shadow NS",
                        field_path=f"{context_prefix}network_environment.type",
                        suggestion="Verify implementation supports Shadow NS or use docker_compose"
                    )
        
        # Check execution environment compatibility
        for exec_env in config.execution_environments:
            env_type = exec_env.get("type")
            
            if env_type in ["gperf_cpu", "gperf_heap"]:
                for service_name, service in config.services.items():
                    if not service.implementation.gperf_compatible:
                        result.add_warning(
                            f"Service '{service_name}' may not support gperf profiling",
                            field_path=f"{context_prefix}execution_environments",
                            suggestion="Verify implementation supports profiling or remove gperf environments"
                        )
    
    def _validate_protocol_implementation_compatibility(
        self, 
        config: ServiceConfigModel, 
        result: ValidationResult,
        context_prefix: str = ""
    ) -> None:
        """Validate protocol and implementation compatibility."""
        protocol_name = config.protocol.name
        impl_name = config.implementation.name
        
        # Basic compatibility checks (can be enhanced with plugin metadata)
        known_incompatibilities = {
            ("quic", "panther_ivy"): "Panther Ivy is a tester, not a QUIC implementation",
            ("http", "picoquic"): "PicoQUIC is a QUIC implementation, not HTTP",
            ("minip", "aioquic"): "AioQUIC is for QUIC protocol, not MiniP",
        }
        
        key = (protocol_name.lower(), impl_name.lower())
        if key in known_incompatibilities:
            result.add_error(
                f"Incompatible protocol-implementation pair: {protocol_name} + {impl_name}",
                field_path=f"{context_prefix}implementation.name",
                suggestion=known_incompatibilities[key]
            )
    
    def _validate_cross_test_port_conflicts(
        self, 
        tests: List[TestConfigModel], 
        result: ValidationResult
    ) -> None:
        """Validate port conflicts across different tests."""
        all_ports = {}
        
        for test_idx, test in enumerate(tests):
            for service_name, service in test.services.items():
                for port_mapping in service.ports:
                    host_port = port_mapping.split(":")[0]
                    try:
                        host_port_num = int(host_port)
                    except ValueError:
                        continue
                    
                    if host_port_num in all_ports:
                        other_test, other_service = all_ports[host_port_num]
                        result.add_warning(
                            f"Port {host_port_num} used in multiple tests: "
                            f"'{test.name}.{service_name}' and '{other_test}.{other_service}'",
                            field_path=f"tests[{test_idx}].services.{service_name}.ports",
                            suggestion="Use different ports for concurrent tests or run tests sequentially"
                        )
                    else:
                        all_ports[host_port_num] = (test.name, service_name)
    
    def _validate_global_experiment_consistency(
        self, 
        config: CompleteConfigModel, 
        result: ValidationResult
    ) -> None:
        """Validate consistency between global and experiment configurations."""
        # Check if fast-fail test-level control is enabled but no tests use it
        if config.global_config.fast_fail.test_level:
            has_test_override = any(
                test.fast_fail_enabled is not None 
                for test in config.experiment_config.tests
            )
            
            if not has_test_override:
                result.add_warning(
                    "Fast-fail test-level control is enabled but no tests override the setting",
                    field_path="global_config.fast_fail.test_level",
                    suggestion="Either disable test-level control or add fast_fail_enabled to some tests"
                )
        
        # Check Docker resource limits vs. service requirements
        docker_memory = config.global_config.docker.memory_limit
        if docker_memory and "M" in docker_memory:
            try:
                memory_mb = int(docker_memory.replace("M", ""))
                service_count = sum(len(test.services) for test in config.experiment_config.tests)
                
                if memory_mb < service_count * 100:  # 100MB per service as rough estimate
                    result.add_warning(
                        f"Docker memory limit ({docker_memory}) may be insufficient for {service_count} services",
                        field_path="global_config.docker.memory_limit",
                        suggestion="Consider increasing memory limit or reducing number of services"
                    )
            except ValueError:
                pass
    
    def supports_config_type(self, config: Any) -> bool:
        """Check if this validator supports the configuration type."""
        return (
            isinstance(config, dict) or
            isinstance(config, (
                CompleteConfigModel, ExperimentConfigModel, TestConfigModel,
                ServiceConfigModel, GlobalConfigModel
            ))
        )