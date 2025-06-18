"""Experiment configuration models."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Field, validator

from panther.config.models.base import ConfigModel
from panther.config.models.service import ServiceConfigModel


class AssertionType(str, Enum):
    """Types of assertions supported in experiments."""
    
    SERVICE_RESPONSIVE = "service_responsive"
    DATA_INTEGRITY = "data_integrity"
    PERFORMANCE_THRESHOLD = "performance_threshold"
    PROTOCOL_COMPLIANCE = "protocol_compliance"


class StepConfigModel(ConfigModel):
    """Configuration for experiment steps."""
    
    wait: int = Field(
        60,
        ge=1,
        le=3600,
        description="Wait time in seconds (1-3600)"
    )
    record_pcap: bool = Field(
        False,
        description="Whether to record packet capture during this step"
    )
    
    # Additional step parameters
    checkpoint: Optional[str] = Field(
        None,
        description="Optional checkpoint name for this step"
    )
    actions: List[str] = Field(
        default_factory=list,
        description="List of actions to perform during this step"
    )


class AssertionConfigModel(ConfigModel):
    """Configuration for test assertions."""
    
    type: AssertionType = Field(
        ...,
        description="Type of assertion to perform"
    )
    service: str = Field(
        ...,
        description="Service name to assert against"
    )
    
    # Assertion-specific fields
    endpoint: Optional[str] = Field(
        None,
        description="Endpoint to assert (for service_responsive)"
    )
    expected_status: Optional[int] = Field(
        None,
        ge=100,
        le=599,
        description="Expected HTTP status code"
    )
    threshold: Optional[float] = Field(
        None,
        description="Performance threshold value"
    )
    metric: Optional[str] = Field(
        None,
        description="Metric name for performance assertions"
    )
    
    @validator("endpoint")
    def validate_endpoint_requirement(cls, v, values):
        """Validate endpoint is provided for service_responsive assertions."""
        if values.get("type") == AssertionType.SERVICE_RESPONSIVE and not v:
            raise ValueError("Endpoint is required for service_responsive assertions")
        return v
    
    @validator("threshold")
    def validate_threshold_requirement(cls, v, values):
        """Validate threshold is provided for performance assertions."""
        if values.get("type") == AssertionType.PERFORMANCE_THRESHOLD and v is None:
            raise ValueError("Threshold is required for performance_threshold assertions")
        return v


class TestConfigModel(ConfigModel):
    """Configuration for a single test within an experiment."""
    
    # Test identification
    name: str = Field(
        ...,
        description="Unique test name",
        regex="^[a-zA-Z][a-zA-Z0-9_-]*$"
    )
    description: str = Field(
        "",
        description="Test description"
    )
    
    # Test configuration
    iterations: int = Field(
        1,
        ge=1,
        le=1000,
        description="Number of test iterations (1-1000)"
    )
    
    # Environment configuration
    network_environment: Dict[str, Any] = Field(
        ...,
        description="Network environment configuration"
    )
    execution_environments: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Execution environment configurations (profilers, etc.)"
    )
    
    # Service configuration
    services: Dict[str, ServiceConfigModel] = Field(
        ...,
        description="Service configurations keyed by service name"
    )
    
    # Test execution
    steps: Optional[StepConfigModel] = Field(
        None,
        description="Step configuration for the test"
    )
    assertions: List[AssertionConfigModel] = Field(
        default_factory=list,
        description="Assertions to validate during/after the test"
    )
    
    # Fast-fail configuration
    fast_fail_enabled: Optional[bool] = Field(
        None,
        description="Override global fast-fail setting for this test"
    )
    
    # Additional test parameters
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional test-specific parameters"
    )
    
    @validator("services")
    def validate_service_names(cls, v):
        """Validate that service names match dictionary keys."""
        for name, service in v.items():
            if service.name != name:
                raise ValueError(
                    f"Service name mismatch: key '{name}' != service.name '{service.name}'"
                )
        return v
    
    @validator("services")
    def validate_service_relationships(cls, v):
        """Validate service relationships (client-server targets)."""
        service_names = list(v.keys())
        
        for name, service in v.items():
            try:
                service.validate_relationship_target(service_names)
            except ValueError as e:
                raise ValueError(f"Service relationship error: {e}")
                
        return v
    
    @validator("assertions")
    def validate_assertion_services(cls, v, values):
        """Validate that assertions reference existing services."""
        services = values.get("services", {})
        if not services:
            return v
            
        for assertion in v:
            if assertion.service not in services:
                raise ValueError(
                    f"Assertion references non-existent service: {assertion.service}"
                )
        return v

    def get_service_dependencies(self) -> Dict[str, List[str]]:
        """Get service dependency graph.
        
        Returns a dictionary mapping service names to their dependencies.
        """
        dependencies = {}
        
        for name, service in self.services.items():
            target = service.get_connection_target()
            dependencies[name] = [target] if target else []
            
        return dependencies

    def get_execution_order(self) -> List[str]:
        """Get the order in which services should be started.
        
        Returns services in dependency order (servers before clients).
        """
        # Simple topological sort
        dependencies = self.get_service_dependencies()
        order = []
        visited = set()
        
        def visit(service: str):
            if service in visited:
                return
            visited.add(service)
            
            for dep in dependencies.get(service, []):
                visit(dep)
                
            order.append(service)
        
        for service in self.services:
            visit(service)
            
        return order


class ExperimentConfigModel(ConfigModel):
    """Root configuration model for experiments."""
    
    # Experiment metadata
    name: Optional[str] = Field(
        None,
        description="Experiment name"
    )
    description: Optional[str] = Field(
        None,
        description="Experiment description"
    )
    
    # Test configurations
    tests: List[TestConfigModel] = Field(
        ...,
        min_items=1,
        description="List of tests to run in this experiment"
    )
    
    # Experiment-wide settings
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for categorizing the experiment"
    )
    
    @validator("tests")
    def validate_unique_test_names(cls, v):
        """Ensure all test names are unique within the experiment."""
        names = [test.name for test in v]
        if len(names) != len(set(names)):
            duplicates = [name for name in names if names.count(name) > 1]
            raise ValueError(f"Duplicate test names found: {duplicates}")
        return v

    def get_all_services(self) -> List[ServiceConfigModel]:
        """Get all services across all tests."""
        services = []
        for test in self.tests:
            services.extend(test.services.values())
        return services

    def get_all_ports(self) -> List[str]:
        """Get all port mappings across all tests."""
        ports = []
        for service in self.get_all_services():
            ports.extend(service.ports)
        return ports

    def validate_port_conflicts(self) -> None:
        """Validate that there are no port conflicts across tests."""
        # Get all host ports
        host_ports = []
        for port_mapping in self.get_all_ports():
            host_port = port_mapping.split(":")[0]
            host_ports.append(int(host_port))
            
        # Check for duplicates
        if len(host_ports) != len(set(host_ports)):
            duplicates = [p for p in host_ports if host_ports.count(p) > 1]
            raise ValueError(f"Port conflicts detected: {duplicates}")