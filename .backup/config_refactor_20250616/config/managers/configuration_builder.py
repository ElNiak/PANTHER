"""Configuration assembly and building functionality."""

import copy
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from panther.config.config_experiment_schema import ExperimentConfig, TestConfig
from panther.config.config_global_schema import GlobalConfig
from panther.core.exceptions.error_handler_mixin import ErrorHandlerMixin


class ConfigurationBuilder(ErrorHandlerMixin):
    """Handles assembly and building of configurations from various sources."""

    def __init__(self):
        """Initialize configuration builder."""
        super().__init__()
        self.base_config = None
        self.overrides = {}
        self.environment_variables = {}
        self.command_line_args = {}

    def set_base_config(
        self, config: Union[Dict[str, Any], ExperimentConfig, GlobalConfig]
    ) -> None:
        """Set the base configuration.

        Args:
            config: Base configuration to start with
        """
        if isinstance(config, (ExperimentConfig, GlobalConfig)):
            self.base_config = config.dict()
        else:
            self.base_config = copy.deepcopy(config)

        self.logger.debug("Base configuration set")

    def add_overrides(self, overrides: Dict[str, Any]) -> None:
        """Add configuration overrides.

        Args:
            overrides: Dictionary of override values
        """
        self.overrides.update(overrides)
        self.logger.debug(f"Added {len(overrides)} configuration overrides")

    def add_environment_variables(self, env_mapping: Dict[str, str]) -> None:
        """Add environment variable mappings.

        Args:
            env_mapping: Mapping of config keys to environment variable names
        """
        import os

        for config_key, env_var in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                self.environment_variables[config_key] = value

        self.logger.debug(
            f"Added {len(self.environment_variables)} environment variables"
        )

    def add_command_line_args(self, args: Dict[str, Any]) -> None:
        """Add command line argument overrides.

        Args:
            args: Dictionary of command line arguments
        """
        # Filter out None values and internal arguments
        filtered_args = {
            k: v for k, v in args.items() if v is not None and not k.startswith("_")
        }

        self.command_line_args.update(filtered_args)
        self.logger.debug(f"Added {len(filtered_args)} command line arguments")

    def build_experiment_config(self) -> ExperimentConfig:
        """Build final experiment configuration.

        Returns:
            Assembled ExperimentConfig object

        Raises:
            ValueError: If base configuration is not set or invalid
        """
        if self.base_config is None:
            raise ValueError("Base configuration must be set before building")

        try:
            # Start with base configuration
            final_config = copy.deepcopy(self.base_config)

            # Apply overrides in priority order:
            # 1. Environment variables (lowest priority)
            # 2. Configuration file overrides
            # 3. Command line arguments (highest priority)

            self._apply_overrides(final_config, self.environment_variables)
            self._apply_overrides(final_config, self.overrides)
            self._apply_overrides(final_config, self.command_line_args)

            # Convert nested dictionaries to proper dataclass objects
            if "tests" in final_config:
                from panther.config.config_experiment_schema import TestConfig

                test_configs = []
                for test_data in final_config["tests"]:
                    if isinstance(test_data, dict):
                        # Handle field name mapping and conversion
                        test_dict = test_data.copy()

                        # Map execution_environment to execution_environments if needed
                        if "execution_environment" in test_dict:
                            test_dict["execution_environments"] = test_dict.pop(
                                "execution_environment"
                            )

                        # Map debug_environment to debug_environments if present
                        if "debug_environment" in test_dict:
                            test_dict.pop("debug_environment")  # Remove for now

                        # Ensure execution_environments is a list
                        if "execution_environments" in test_dict and not isinstance(
                            test_dict["execution_environments"], list
                        ):
                            test_dict["execution_environments"] = [
                                test_dict["execution_environments"]
                            ]

                        try:
                            # Convert nested config objects
                            test_dict = self._convert_nested_configs(test_dict)

                            # Convert dict to TestConfig object
                            test_config = TestConfig(**test_dict)
                            test_configs.append(test_config)
                        except Exception as e:
                            self.logger.warning(
                                f"Failed to convert test config, using dict: {e}"
                            )
                            # If conversion fails, keep as dict for now
                            test_configs.append(test_data)
                    else:
                        test_configs.append(test_data)
                final_config["tests"] = test_configs

            # Convert to ExperimentConfig object
            experiment_config = ExperimentConfig(**final_config)

            self.logger.info("Successfully built experiment configuration")
            return experiment_config

        except Exception as e:
            self.handle_error(e, "building experiment configuration")
            raise

    def build_global_config(self) -> GlobalConfig:
        """Build final global configuration.

        Returns:
            Assembled GlobalConfig object

        Raises:
            ValueError: If base configuration is not set or invalid
        """
        if self.base_config is None:
            raise ValueError("Base configuration must be set before building")

        try:
            print(f"DEBUG: build_global_config called")
            # Start with base configuration
            final_config = copy.deepcopy(self.base_config)
            print(f"DEBUG: Base config keys: {list(final_config.keys())}")

            # Apply overrides in priority order
            self._apply_overrides(final_config, self.environment_variables)
            self._apply_overrides(final_config, self.overrides)
            self._apply_overrides(final_config, self.command_line_args)
            
            # Check if feature_levels exist in final_config before conversion
            if "logging" in final_config and "feature_levels" in final_config["logging"]:
                print(f"DEBUG: feature_levels found before conversion: {[(k, v) for k, v in list(final_config['logging']['feature_levels'].items())[:3]]}")
            else:
                print(f"DEBUG: No feature_levels found in final_config before conversion")

            # Convert feature_levels from strings to enum values if present
            print(f"DEBUG: About to call _convert_feature_levels")
            self._convert_feature_levels(final_config)
            print(f"DEBUG: _convert_feature_levels completed")
            
            # Check feature_levels after conversion
            if "logging" in final_config and "feature_levels" in final_config["logging"]:
                print(f"DEBUG: feature_levels after conversion: {[(k, v) for k, v in list(final_config['logging']['feature_levels'].items())[:3]]}")

            # Remove version field if present (not part of GlobalConfig)
            final_config.pop("version", None)
            
            # Convert to GlobalConfig object
            print(f"DEBUG: About to create GlobalConfig object")
            global_config = GlobalConfig(**final_config)
            print(f"DEBUG: GlobalConfig created successfully")

            self.logger.info("Successfully built global configuration")
            return global_config

        except Exception as e:
            print(f"DEBUG: Exception in build_global_config: {e}")
            self.handle_error(e, "building global configuration")
            raise

    def build_test_configs(self, tests_data: List[Dict[str, Any]]) -> List[TestConfig]:
        """Build test configurations from raw data.

        Args:
            tests_data: List of test configuration dictionaries

        Returns:
            List of TestConfig objects
        """
        test_configs = []

        for i, test_data in enumerate(tests_data):
            try:
                # Apply any test-level overrides
                final_test_data = copy.deepcopy(test_data)

                # Apply global overrides to test configuration
                test_overrides = self._extract_test_overrides(i)
                self._apply_overrides(final_test_data, test_overrides)

                # Create TestConfig object
                test_config = TestConfig(**final_test_data)
                test_configs.append(test_config)

            except Exception as e:
                self.logger.error(f"Failed to build test config {i}: {e}")
                raise

        self.logger.info(f"Successfully built {len(test_configs)} test configurations")
        return test_configs

    def _apply_overrides(
        self, config: Dict[str, Any], overrides: Dict[str, Any]
    ) -> None:
        """Apply configuration overrides using dot notation.

        Args:
            config: Configuration dictionary to modify
            overrides: Override values to apply
        """
        for key, value in overrides.items():
            self._set_nested_value(config, key, value)

    def _set_nested_value(self, config: Dict[str, Any], key: str, value: Any) -> None:
        """Set a nested configuration value using dot notation.

        Args:
            config: Configuration dictionary to modify
            key: Dot-separated key path
            value: Value to set
        """
        if "." not in key:
            config[key] = value
            return

        # Split key into parts
        parts = key.split(".")
        current = config

        # Navigate to the parent of the target key
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            elif not isinstance(current[part], dict):
                # Key path conflicts with existing non-dict value
                self.logger.warning(f"Key path conflict at '{part}' in '{key}'")
                return
            current = current[part]

        # Set the final value
        current[parts[-1]] = value

    def _extract_test_overrides(self, test_index: int) -> Dict[str, Any]:
        """Extract test-specific overrides from global overrides.

        Args:
            test_index: Index of the test configuration

        Returns:
            Dictionary of test-specific overrides
        """
        test_overrides = {}

        # Look for test-specific overrides in the format: tests.0.key
        test_prefix = f"tests.{test_index}."

        for key, value in {**self.overrides, **self.command_line_args}.items():
            if key.startswith(test_prefix):
                # Remove the test prefix to get the relative key
                relative_key = key[len(test_prefix) :]
                test_overrides[relative_key] = value

        return test_overrides

    def validate_build_inputs(self) -> bool:
        """Validate that all required inputs for building are present.

        Returns:
            True if inputs are valid, False otherwise
        """
        if self.base_config is None:
            self.logger.error("Base configuration is required for building")
            return False

        # Check that base config has required fields
        if isinstance(self.base_config, dict):
            required_fields = ["version", "logging"]  # Minimal required fields
            missing_fields = [
                field for field in required_fields if field not in self.base_config
            ]

            if missing_fields:
                self.logger.error(
                    f"Base configuration missing required fields: {missing_fields}"
                )
                return False

        return True

    def get_effective_config(self) -> Dict[str, Any]:
        """Get the effective configuration after all overrides.

        Returns:
            Dictionary representing the final configuration
        """
        if not self.validate_build_inputs():
            raise ValueError("Invalid build inputs")

        # Start with base configuration
        effective_config = copy.deepcopy(self.base_config)

        # Apply all overrides
        self._apply_overrides(effective_config, self.environment_variables)
        self._apply_overrides(effective_config, self.overrides)
        self._apply_overrides(effective_config, self.command_line_args)

        return effective_config

    def reset(self) -> None:
        """Reset the builder to initial state."""
        self.base_config = None
        self.overrides.clear()
        self.environment_variables.clear()
        self.command_line_args.clear()

        self.logger.debug("Configuration builder reset")

    def get_override_summary(self) -> Dict[str, int]:
        """Get a summary of applied overrides.

        Returns:
            Dictionary with counts of different override types
        """
        return {
            "environment_variables": len(self.environment_variables),
            "config_overrides": len(self.overrides),
            "command_line_args": len(self.command_line_args),
            "total_overrides": len(self.environment_variables)
            + len(self.overrides)
            + len(self.command_line_args),
        }

    def _convert_nested_configs(self, test_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Convert nested configuration dictionaries to proper dataclass objects.

        Args:
            test_dict: Test configuration dictionary

        Returns:
            Test configuration with converted nested objects
        """
        # Convert network_environment
        if "network_environment" in test_dict and isinstance(
            test_dict["network_environment"], dict
        ):
            from panther.plugins.environments.network_environment.config_schema import (
                NetworkEnvironmentConfig,
            )

            try:
                net_env_dict = self._clean_network_env_config(
                    test_dict["network_environment"]
                )
                network_config = NetworkEnvironmentConfig(**net_env_dict)
                test_dict["network_environment"] = network_config
            except Exception as e:
                self.logger.warning(
                    f"Failed to convert network_environment config: {e}"
                )
                # Try with just the type field as fallback
                try:
                    minimal_net_env = NetworkEnvironmentConfig(
                        type=test_dict["network_environment"].get(
                            "type", "docker_compose"
                        )
                    )
                    test_dict["network_environment"] = minimal_net_env
                except:
                    pass  # Keep original dict

        # Convert execution_environments
        if "execution_environments" in test_dict and isinstance(
            test_dict["execution_environments"], list
        ):
            from panther.plugins.environments.execution_environment.config_schema import (
                ExecutionEnvironmentConfig,
            )

            converted_exec_envs = []
            for exec_env in test_dict["execution_environments"]:
                if isinstance(exec_env, dict):
                    try:
                        exec_config = ExecutionEnvironmentConfig(**exec_env)
                        converted_exec_envs.append(exec_config)
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to convert execution_environment config: {e}"
                        )
                        converted_exec_envs.append(exec_env)
                else:
                    converted_exec_envs.append(exec_env)
            test_dict["execution_environments"] = converted_exec_envs

        # Convert services
        if "services" in test_dict and isinstance(test_dict["services"], dict):
            from panther.plugins.services.config_schema import ServiceConfig

            converted_services = {}
            for service_name, service_data in test_dict["services"].items():
                if isinstance(service_data, dict):
                    try:
                        # Clean service data - remove unknown fields
                        clean_service_data = self._clean_service_config(service_data)
                        service_config = ServiceConfig(**clean_service_data)
                        converted_services[service_name] = service_config
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to convert service config for {service_name}: {e}"
                        )
                        # Don't fall back to dict - keep trying to create a minimal ServiceConfig
                        try:
                            minimal_service = ServiceConfig(
                                name=service_data.get("name", service_name),
                                timeout=service_data.get("timeout", 100),
                            )
                            converted_services[service_name] = minimal_service
                        except:
                            converted_services[service_name] = service_data
                else:
                    converted_services[service_name] = service_data
            test_dict["services"] = converted_services

        # Convert steps
        if "steps" in test_dict and isinstance(test_dict["steps"], dict):
            from panther.config.config_experiment_schema import StepConfig

            try:
                step_config = StepConfig(**test_dict["steps"])
                test_dict["steps"] = step_config
            except Exception as e:
                self.logger.warning(f"Failed to convert steps config: {e}")

        return test_dict

    def _clean_service_config(self, service_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean service configuration data by removing unknown fields and converting nested configs.

        Args:
            service_data: Raw service configuration data

        Returns:
            Cleaned service configuration data with converted nested objects
        """
        # Known ServiceConfig fields
        known_fields = {
            "name",
            "timeout",
            "implementation",
            "protocol",
            "ports",
            "generate_new_certificates",
            "volumes",
            "environment",
            "command",
            "entrypoint",
            "depends_on",
            "health_check",
        }

        cleaned_data = {}
        for key, value in service_data.items():
            if key in known_fields:
                cleaned_data[key] = value
            else:
                self.logger.debug(f"Skipping unknown service field: {key}")

        # Convert nested implementation config
        if "implementation" in cleaned_data and isinstance(
            cleaned_data["implementation"], dict
        ):
            try:
                impl_data = self._clean_implementation_config(
                    cleaned_data["implementation"]
                )
                
                # Use implementation-specific config class if available
                impl_config = self._create_implementation_config(impl_data)
                cleaned_data["implementation"] = impl_config
            except Exception as e:
                self.logger.warning(f"Failed to convert implementation config: {e}")

        # Convert nested protocol config
        if "protocol" in cleaned_data and isinstance(cleaned_data["protocol"], dict):
            try:
                from panther.plugins.services.config_schema import ProtocolConfig

                proto_data = self._clean_protocol_config(cleaned_data["protocol"])
                proto_config = ProtocolConfig(**proto_data)
                cleaned_data["protocol"] = proto_config
            except Exception as e:
                self.logger.warning(f"Failed to convert protocol config: {e}")

        return cleaned_data

    def _clean_network_env_config(self, net_env_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean network environment configuration data.

        Args:
            net_env_data: Raw network environment data

        Returns:
            Cleaned network environment data
        """
        # Known NetworkEnvironmentConfig fields
        known_fields = {"type", "version", "network_name", "environment"}

        cleaned_data = {}
        for key, value in net_env_data.items():
            if key in known_fields:
                cleaned_data[key] = value
            else:
                self.logger.debug(f"Skipping unknown network environment field: {key}")

        return cleaned_data

    def _clean_implementation_config(self, impl_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean implementation configuration data.

        Args:
            impl_data: Raw implementation data

        Returns:
            Cleaned implementation data
        """
        # Base ImplementationConfig fields that are always allowed
        base_fields = {"name", "type", "shadow_compatible", "gperf_compatible"}
        
        # Implementation-specific fields that should be preserved
        # These are needed for specialized implementations like panther_ivy
        implementation_specific_fields = {
            "test",  # For panther_ivy and other tester implementations
            "protocol",  # For implementations that specify protocols
            "use_system_models",  # For panther_ivy
            "version",  # For version-specific configurations
            "environment",  # For environment configurations
            "parameters"  # For parameter configurations
        }
        
        # Allow all base fields plus implementation-specific fields
        allowed_fields = base_fields | implementation_specific_fields

        cleaned_data = {}
        for key, value in impl_data.items():
            if key in allowed_fields:
                cleaned_data[key] = value
            else:
                # Log as debug but still preserve the field for forward compatibility
                self.logger.debug(f"Preserving unknown implementation field: {key}")
                cleaned_data[key] = value

        return cleaned_data

    def _create_implementation_config(self, impl_data: Dict[str, Any]):
        """Create the appropriate implementation config object based on implementation name and type.
        
        Args:
            impl_data: Implementation configuration data
            
        Returns:
            Appropriate implementation config object (ImplementationConfig or specialized subclass)
        """
        impl_name = impl_data.get("name", "")
        impl_type = impl_data.get("type", "")
        
        try:
            # Check for implementation-specific config classes first
            if impl_name == "panther_ivy" and impl_type in ["TESTERS", "testers"]:
                # Use PantherIvyConfig for panther_ivy implementations
                try:
                    from panther.plugins.services.testers.panther_ivy.config_schema import PantherIvyConfig
                    self.logger.debug(f"Using PantherIvyConfig for {impl_name}")
                    
                    # Create PantherIvyConfig with proper defaults
                    ivy_config = PantherIvyConfig()
                    
                    # Override with provided data while preserving defaults
                    for key, value in impl_data.items():
                        if hasattr(ivy_config, key):
                            setattr(ivy_config, key, value)
                        else:
                            self.logger.debug(f"Skipping unknown PantherIvyConfig field: {key}")
                    
                    return ivy_config
                    
                except (ImportError, Exception) as e:
                    self.logger.warning(f"Could not create PantherIvyConfig: {e}")
                    # Fall through to unified mock config below
            
            # For all other implementations, create a unified implementation config with version support
            from panther.plugins.services.config_schema import ImplementationConfig
            
            # Create a unified config that has the version structure all service managers expect
            class UnifiedImplementationConfig(ImplementationConfig):
                def __init__(self, **kwargs):
                    # Extract name and type for parent constructor
                    name = kwargs.get("name", impl_name)
                    impl_type_value = kwargs.get("type", impl_type)
                    
                    # Convert string to enum if needed
                    if isinstance(impl_type_value, str):
                        from panther.plugins.services.iut.config_schema import ImplementationType
                        if impl_type_value.upper() == "TESTERS":
                            impl_type_value = ImplementationType.TESTERS
                        else:
                            impl_type_value = ImplementationType.IUT
                    
                    # Set defaults for base ImplementationConfig
                    super().__init__(name=name, type=impl_type_value)
                    
                    # Additional attributes are set below
                    
                    # Create a unified version object with the expected structure
                    # This satisfies both panther_ivy and regular IUT service managers
                    class MockVersion:
                        def __init__(self):
                            # Basic structure that service managers expect
                            self.version = "latest"  # String version for Docker images
                            
                            # Structure for panther_ivy and other testers
                            self.server = {
                                "tests": {},
                                "protocol": MockProtocol(),
                                "network": {"port": 4443},
                                "binary": {"dir": "/opt"}
                            }
                            self.client = {
                                "tests": {},
                                "protocol": MockProtocol(), 
                                "network": {"port": 4443},
                                "binary": {"dir": "/opt"},
                                "ticket_file": MockTicketFile(),
                                "initial_version": "1"
                            }
                    
                    class MockProtocol:
                        def __init__(self):
                            self.additional_parameters = ""
                    
                    class MockTicketFile:
                        def __init__(self):
                            self.param = "-T"
                            self.file = "/opt/ticket/ticket.key"
                    
                    self.version = MockVersion()
                    
                    # Add implementation-specific attributes for panther_ivy
                    if impl_name == "panther_ivy":
                        self.test = kwargs.get("test", "")
                        self.use_system_models = kwargs.get("use_system_models", False)
                        self.protocol = kwargs.get("protocol", "quic")
                    
                    # Set any other provided attributes
                    for key, value in kwargs.items():
                        if not hasattr(self, key):
                            setattr(self, key, value)
            
            self.logger.info(f"Creating UnifiedImplementationConfig for {impl_name} with data: {impl_data}")
            unified_config = UnifiedImplementationConfig(**impl_data)
            self.logger.info(f"Successfully created UnifiedImplementationConfig with version: {type(unified_config.version)}")
            return unified_config
            
        except Exception as e:
            self.logger.error(f"Failed to create implementation config for {impl_name}: {e}")
            # Final fallback to basic ImplementationConfig with minimal data
            from panther.plugins.services.config_schema import ImplementationConfig
            basic_data = {"name": impl_data.get("name", ""), "type": impl_data.get("type", "")}
            return ImplementationConfig(**basic_data)

    def _clean_protocol_config(self, proto_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean protocol configuration data.

        Args:
            proto_data: Raw protocol data

        Returns:
            Cleaned protocol data
        """
        # Known ProtocolConfig fields
        known_fields = {"name", "version", "role", "target"}

        cleaned_data = {}
        for key, value in proto_data.items():
            if key in known_fields:
                cleaned_data[key] = value
            else:
                self.logger.debug(f"Skipping unknown protocol field: {key}")

        return cleaned_data

    def _convert_feature_levels(self, config: Dict[str, Any]) -> None:
        """
        Convert feature_levels from string values to LoggingLevel enum values.
        
        Args:
            config: Configuration dictionary to modify in-place
        """
        print(f"DEBUG: _convert_feature_levels called")
        if "logging" not in config or "feature_levels" not in config["logging"]:
            print(f"DEBUG: No logging or feature_levels in config")
            return
            
        feature_levels = config["logging"]["feature_levels"]
        if not isinstance(feature_levels, dict):
            print(f"DEBUG: feature_levels is not a dict: {type(feature_levels)}")
            return
            
        print(f"DEBUG: Converting feature_levels: {[(k, v) for k, v in list(feature_levels.items())[:3]]}")
            
        # Import LoggingLevel enum
        from panther.config.config_global_schema import LoggingLevel
        
        # Convert string values to enum values
        converted_levels = {}
        for feature_name, level_value in feature_levels.items():
            if isinstance(level_value, str):
                try:
                    # Convert string to LoggingLevel enum
                    converted_levels[feature_name] = LoggingLevel[level_value.upper()]
                    print(f"DEBUG: Converted {feature_name}: {level_value} -> {LoggingLevel[level_value.upper()]}")
                except KeyError:
                    self.logger.warning(f"Invalid logging level '{level_value}' for feature '{feature_name}', using INFO")
                    converted_levels[feature_name] = LoggingLevel.INFO
            else:
                # Already an enum or other type, keep as-is
                converted_levels[feature_name] = level_value
        
        # Replace the feature_levels with converted values
        config["logging"]["feature_levels"] = converted_levels
        print(f"DEBUG: Conversion complete: {[(k, v) for k, v in list(converted_levels.items())[:3]]}")
