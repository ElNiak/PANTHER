"""Service configuration builder."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

from panther.config.builders.base_builder import (
    AbstractConfigBuilder,
    BuildContext,
    FluentConfigBuilder,
)
from panther.config.loaders import VersionConfigLoader
from panther.config.models.implementation import (
    ImplementationModel,
    ImplementationType,
    ProtocolModel,
    ProtocolRole,
)
from panther.config.models.service import ServiceConfigModel
from panther.config.validators import BusinessRulesValidator, PydanticValidator


class ServiceConfigBuilder(FluentConfigBuilder):
    """Builder for service configurations with plugin integration."""
    
    def __init__(self, plugin_dir: Optional[Union[str, Path]] = None):
        super().__init__("ServiceConfigBuilder")
        
        # Initialize version loader for plugin configs
        self.version_loader = VersionConfigLoader(plugin_dir)
        
        # Set up validators
        self.with_validator(PydanticValidator(ServiceConfigModel))
        self.with_validator(BusinessRulesValidator())
        
        # Service building state
        self._service_name: Optional[str] = None
        self._implementation: Optional[Dict[str, Any]] = None
        self._protocol: Optional[Dict[str, Any]] = None
        self._auto_configure = True
    
    def get_target_model_class(self) -> Type[ServiceConfigModel]:
        """Get the target model class."""
        return ServiceConfigModel
    
    def with_name(self, name: str) -> "ServiceConfigBuilder":
        """Set service name.
        
        Args:
            name: Service name
            
        Returns:
            Self for method chaining
        """
        self._service_name = name
        return self
    
    def with_implementation(
        self, 
        name: str, 
        implementation_type: Union[str, ImplementationType] = ImplementationType.IUT,
        test: Optional[str] = None,
        **kwargs
    ) -> "ServiceConfigBuilder":
        """Set implementation configuration.
        
        Args:
            name: Implementation name
            implementation_type: Implementation type (iut or testers)
            test: Test name for tester implementations
            **kwargs: Additional implementation parameters
            
        Returns:
            Self for method chaining
        """
        if isinstance(implementation_type, str):
            implementation_type = ImplementationType(implementation_type)
        
        self._implementation = {
            "name": name,
            "type": implementation_type,
            **kwargs
        }
        
        if test and implementation_type == ImplementationType.TESTERS:
            self._implementation["test"] = test
        
        return self
    
    def with_protocol(
        self, 
        name: str, 
        role: Union[str, ProtocolRole] = ProtocolRole.SERVER,
        version: Optional[str] = None,
        target: Optional[str] = None,
        **kwargs
    ) -> "ServiceConfigBuilder":
        """Set protocol configuration.
        
        Args:
            name: Protocol name
            role: Protocol role (server, client, peer)
            version: Protocol version
            target: Target service name (for clients)
            **kwargs: Additional protocol parameters
            
        Returns:
            Self for method chaining
        """
        if isinstance(role, str):
            role = ProtocolRole(role)
        
        self._protocol = {
            "name": name,
            "role": role,
            **kwargs
        }
        
        if version:
            self._protocol["version"] = version
        
        if target:
            self._protocol["target"] = target
        
        return self
    
    def with_ports(self, *ports: str) -> "ServiceConfigBuilder":
        """Set port mappings.
        
        Args:
            *ports: Port mappings in format 'host:container' or just 'port'
            
        Returns:
            Self for method chaining
        """
        self._overrides["ports"] = list(ports)
        return self
    
    def with_timeout(self, timeout: int) -> "ServiceConfigBuilder":
        """Set service timeout.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Self for method chaining
        """
        self._overrides["timeout"] = timeout
        return self
    
    def with_certificates(
        self, 
        generate_new: bool = True, 
        certificate_path: Optional[str] = None
    ) -> "ServiceConfigBuilder":
        """Configure certificate settings.
        
        Args:
            generate_new: Whether to generate new certificates
            certificate_path: Path to existing certificates
            
        Returns:
            Self for method chaining
        """
        self._overrides["generate_new_certificates"] = generate_new
        if certificate_path:
            self._overrides["certificate_path"] = certificate_path
        return self
    
    def with_environment(self, **env_vars: str) -> "ServiceConfigBuilder":
        """Set environment variables.
        
        Args:
            **env_vars: Environment variables as key-value pairs
            
        Returns:
            Self for method chaining
        """
        if "environment" not in self._overrides:
            self._overrides["environment"] = {}
        self._overrides["environment"].update(env_vars)
        return self
    
    def with_volumes(self, *volumes: str) -> "ServiceConfigBuilder":
        """Set volume mappings.
        
        Args:
            *volumes: Volume mappings in Docker format
            
        Returns:
            Self for method chaining
        """
        self._overrides["volumes"] = list(volumes)
        return self
    
    def with_auto_configuration(self, enabled: bool = True) -> "ServiceConfigBuilder":
        """Enable or disable automatic configuration.
        
        Args:
            enabled: Whether to enable auto-configuration
            
        Returns:
            Self for method chaining
        """
        self._auto_configure = enabled
        return self
    
    def build(self) -> ServiceConfigModel:
        """Build service configuration with plugin integration.
        
        Returns:
            Built and validated service configuration
        """
        if not self._service_name:
            raise ValueError("Service name must be set")
        
        if not self._implementation:
            raise ValueError("Implementation must be set")
        
        if not self._protocol:
            raise ValueError("Protocol must be set")
        
        # Build base configuration
        config_dict = {
            "name": self._service_name,
            "implementation": self._implementation,
            "protocol": self._protocol,
        }
        
        # Apply overrides
        config_dict.update(self._overrides)
        
        # Apply defaults if available
        if self._defaults:
            merged_config = self._merge_configurations(self._defaults, config_dict)
        else:
            merged_config = self._merge_configurations(config_dict)
        
        # Build model
        service_model = self._build_model(merged_config)
        
        # Apply enhancements
        if self._auto_configure:
            service_model = self._auto_configure_service(service_model)
        
        # Load version-specific configuration
        service_model = self._load_version_configuration(service_model)
        
        # Final validation
        validation_result = self.validate(service_model)
        if not validation_result.is_valid:
            error_summary = validation_result.format_errors()
            raise ValueError(f"Service configuration validation failed:\n{error_summary}")
        
        return service_model
    
    def _auto_configure_service(self, service: ServiceConfigModel) -> ServiceConfigModel:
        """Apply automatic configuration based on protocol and implementation.
        
        Args:
            service: Service configuration to auto-configure
            
        Returns:
            Auto-configured service
        """
        auto_configs_applied = 0
        
        # Auto-assign ports for servers
        if not service.ports and service.protocol.requires_server_port():
            default_port = service.get_protocol_default_port()
            if default_port:
                service.ports = [default_port]
                auto_configs_applied += 1
                self._context.add_warning(f"Auto-assigned port {default_port}")
        
        # Auto-enable certificate generation for secure protocols
        if service.protocol.name.lower() in ["quic", "https", "tls"]:
            if not service.generate_new_certificates and not service.certificate_path:
                service.generate_new_certificates = True
                auto_configs_applied += 1
                self._context.add_warning("Auto-enabled certificate generation")
        
        # Set protocol-specific environment variables
        protocol_env = {
            "PANTHER_PROTOCOL": service.protocol.name,
            "PANTHER_ROLE": service.protocol.role,
        }
        
        if service.protocol.version:
            protocol_env["PANTHER_PROTOCOL_VERSION"] = service.protocol.version
        
        if service.protocol.target:
            protocol_env["PANTHER_TARGET"] = service.protocol.target
        
        service.environment.update(protocol_env)
        auto_configs_applied += len(protocol_env)
        
        if auto_configs_applied > 0:
            self.logger.debug(f"Applied {auto_configs_applied} automatic configurations")
        
        return service
    
    def _load_version_configuration(self, service: ServiceConfigModel) -> ServiceConfigModel:
        """Load version-specific configuration for the service.
        
        Args:
            service: Service configuration
            
        Returns:
            Service with version configuration applied
        """
        if not service.protocol.version:
            return service
        
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
            
            # Add build arguments if present
            if version_config.build_args:
                service.parameters["build_args"] = version_config.build_args
            
            # Add protocol features if present
            if version_config.protocol_features:
                service.parameters["protocol_features"] = version_config.protocol_features
            
            self.logger.debug(
                f"Loaded version config for {service.name}: "
                f"{service.protocol.name} {service.protocol.version}"
            )
            
            self._context.set_metadata("version_config_loaded", True)
            self._context.set_metadata("version_config_path", version_config.version)
        else:
            self._context.add_warning(
                f"No version configuration found for {service.implementation.name} "
                f"{service.protocol.name} {service.protocol.version}"
            )
        
        return service


class QuickServiceBuilder:
    """Quick builder for common service configurations."""
    
    def __init__(self, plugin_dir: Optional[Union[str, Path]] = None):
        self.plugin_dir = plugin_dir
    
    def quic_server(
        self, 
        implementation: str, 
        name: str = "quic_server",
        version: str = "rfc9000",
        port: str = "4443:4443"
    ) -> ServiceConfigModel:
        """Create a QUIC server configuration.
        
        Args:
            implementation: Implementation name (e.g., picoquic, aioquic)
            name: Service name
            version: QUIC version
            port: Port mapping
            
        Returns:
            Configured QUIC server
        """
        return (ServiceConfigBuilder(self.plugin_dir)
                .with_name(name)
                .with_implementation(implementation, ImplementationType.IUT)
                .with_protocol("quic", ProtocolRole.SERVER, version=version)
                .with_ports(port)
                .with_certificates(generate_new=True)
                .build())
    
    def quic_client(
        self, 
        implementation: str, 
        target: str,
        name: str = "quic_client",
        version: str = "rfc9000"
    ) -> ServiceConfigModel:
        """Create a QUIC client configuration.
        
        Args:
            implementation: Implementation name
            target: Target server service name
            name: Service name
            version: QUIC version
            
        Returns:
            Configured QUIC client
        """
        return (ServiceConfigBuilder(self.plugin_dir)
                .with_name(name)
                .with_implementation(implementation, ImplementationType.IUT)
                .with_protocol("quic", ProtocolRole.CLIENT, version=version, target=target)
                .with_certificates(generate_new=True)
                .build())
    
    def ivy_tester(
        self, 
        test_name: str,
        protocol: str = "quic",
        version: str = "rfc9000",
        name: str = "ivy_tester",
        ports: List[str] = None
    ) -> ServiceConfigModel:
        """Create an Ivy tester configuration.
        
        Args:
            test_name: Ivy test name
            protocol: Protocol to test
            version: Protocol version
            name: Service name
            ports: Port mappings
            
        Returns:
            Configured Ivy tester
        """
        if ports is None:
            ports = ["4443:4443", "4987:4987"]
        
        return (ServiceConfigBuilder(self.plugin_dir)
                .with_name(name)
                .with_implementation("panther_ivy", ImplementationType.TESTERS, test=test_name)
                .with_protocol(protocol, ProtocolRole.SERVER, version=version)
                .with_ports(*ports)
                .build())
    
    def http_server(
        self, 
        implementation: str = "nginx",
        name: str = "http_server",
        port: str = "80:80"
    ) -> ServiceConfigModel:
        """Create an HTTP server configuration.
        
        Args:
            implementation: Implementation name
            name: Service name
            port: Port mapping
            
        Returns:
            Configured HTTP server
        """
        return (ServiceConfigBuilder(self.plugin_dir)
                .with_name(name)
                .with_implementation(implementation, ImplementationType.IUT)
                .with_protocol("http", ProtocolRole.SERVER)
                .with_ports(port)
                .build())
    
    def service_pair(
        self, 
        implementation: str,
        protocol: str = "quic",
        version: Optional[str] = None,
        server_port: str = "4443:4443"
    ) -> tuple[ServiceConfigModel, ServiceConfigModel]:
        """Create a matched server-client pair.
        
        Args:
            implementation: Implementation name for both services
            protocol: Protocol name
            version: Protocol version
            server_port: Server port mapping
            
        Returns:
            Tuple of (server, client) configurations
        """
        server = (ServiceConfigBuilder(self.plugin_dir)
                  .with_name(f"{implementation}_server")
                  .with_implementation(implementation, ImplementationType.IUT)
                  .with_protocol(protocol, ProtocolRole.SERVER, version=version)
                  .with_ports(server_port)
                  .build())
        
        client = (ServiceConfigBuilder(self.plugin_dir)
                  .with_name(f"{implementation}_client")
                  .with_implementation(implementation, ImplementationType.IUT)
                  .with_protocol(protocol, ProtocolRole.CLIENT, version=version, target=server.name)
                  .build())
        
        return server, client