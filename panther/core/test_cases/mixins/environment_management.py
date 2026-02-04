"""Environment management functionality for test cases."""

import time
from typing import Any, Dict, List, Optional

from panther.plugins.environments.execution_environment.execution_environment_interface import (
    IExecutionEnvironment,
)
from panther.plugins.environments.network_environment.network_environment_interface import (
    INetworkEnvironment,
)


class EnvironmentManagementMixin:
    """Mixin providing environment management capabilities for test cases."""

    def setup_environment(self) -> None:
        """Set up test environment using configured plugins."""
        # Prevent duplicate setup calls
        if (
            hasattr(self, "_environment_setup_complete")
            and self._environment_setup_complete
        ):
            self.logger.debug("Environment setup already completed, skipping")
            return

        self.logger.info("Setting up test environment")

        try:
            # Get environment emitter from registry
            env_emitter = None
            env_id = f"{self.test_config.network_environment.type}_{self.test_name}"
            if self.emitter_registry:
                env_emitter = self.emitter_registry.environment_emitter

            # Emit environment setup started event
            if env_emitter:
                env_emitter.emit_environment_setup_started(
                    environment_id=env_id,
                    environment_name=self.test_name,
                    environment_type=self.test_config.network_environment.type,
                    setup_config={"test_case": self.test_name},
                )

            # Setup network environment
            network_plugin: Optional[INetworkEnvironment] = None
            network_env_config = self.test_config.network_environment
            if network_env_config:
                network_plugin = self._setup_network_environment(network_env_config)

            if not network_plugin:
                raise ValueError(
                    f"Network environment plugin not found for type: {self.test_config.network_environment.type}"
                )

            # Setup execution environments
            exec_env_configs = self.test_config.execution_environment or []
            for exec_env_config in exec_env_configs:
                self._setup_execution_environment(exec_env_config)

            if isinstance(network_plugin, INetworkEnvironment):
                # Initialize network environment
                self.logger.info(
                    f"Initializing network environment: {network_plugin.name}"
                )

                network_plugin.setup_environment(
                    services_managers=self.service_managers,
                    test_config=self.test_config,
                    global_config=self.global_config,
                    timestamp=time.strftime("%Y%m%d_%H%M%S"),
                    plugin_manager=self.plugin_manager,
                    execution_environment=self.execution_environment_plugins,
                )

                # Add to environment managers
                self.environment_plugin_manager.append(network_plugin)
            else:
                raise RuntimeError(
                    f"Network environment plugin is not of type INetworkEnvironment: {network_plugin}"
                )

            # Emit environment setup completed event
            if env_emitter:
                env_emitter.emit_environment_setup_completed(
                    environment_id=f"{self.test_config.network_environment.type}_{self.test_name}",
                    environment_name=self.test_name,
                    environment_type=self.test_config.network_environment.type,
                    setup_details={
                        "network_environment": network_env_config,
                        "execution_environment": exec_env_configs,
                        "test_case": self.test_name,  # Add test case name to setup details
                    },
                )

            self.logger.info("Environment setup completed")

            # Mark setup as complete to prevent duplicate calls
            self._environment_setup_complete = True

        except Exception as e:
            self.logger.error(f"Failed to setup environment: {e}")
            # Emit environment setup failed event
            if env_emitter:
                env_emitter.emit_environment_setup_failed(
                    environment_id=f"{self.test_config.network_environment.type}_{self.test_name}",
                    environment_name=self.test_name,
                    environment_type=self.test_config.network_environment.type,
                    error_message=str(e),
                    error_type=type(e).__name__,
                )
            raise

    def _setup_network_environment(self, config: Dict[str, Any]) -> None:
        """Set up network environment plugin."""
        env_type = config.type
        self.logger.info(f"Setting up network environment: {env_type}")

        try:
            # Create network environment instance directly
            network_plugin_class = self.plugin_manager.create_environment_manager(
                environment=self.test_config.network_environment.type,
                test_config=self.test_config,
                environment_dir=self.test_experiment_dir,
                output_dir=self.test_experiment_dir,
                event_manager=self.event_manager,
            )

            # network_plugin_class is already the instance from create_environment_manager
            network_plugin = network_plugin_class

            # Configure the plugin
            network_plugin.service_managers = self.service_managers
            network_plugin.config = self.test_config

            # Prepare the environment
            network_plugin.initialize(
                self.test_config,
                self.test_experiment_dir,
                self.event_manager,
                self.global_config,
            )

            # Add to environment managers
            self.environment_plugin_manager.append(network_plugin)
            self.logger.info(
                f"Added network plugin to environment_plugin_manager. Current count: {len(self.environment_plugin_manager)}"
            )

            self.logger.info(f"Network environment {env_type} set up successfully")
            return network_plugin

        except Exception as e:
            self.logger.error(f"Failed to setup network environment: {e}")
            raise

    def _setup_execution_environment(self, config: Any) -> None:
        """Set up execution environment plugin."""
        env_type = config.type
        self.logger.info(f"Setting up execution environment: {env_type}")

        try:
            # Get execution environment plugin class
            exec_plugin_class = self.plugin_manager.create_environment_manager(
                environment=config.type,
                test_config=self.test_config,
                environment_dir=self.test_experiment_dir,
                output_dir=self.test_experiment_dir,
                event_manager=self.event_manager,
            )

            if exec_plugin_class and isinstance(
                exec_plugin_class, IExecutionEnvironment
            ):
                # exec_plugin_class is already the instance from create_environment_manager
                exec_plugin = exec_plugin_class

                # Configure the plugin
                exec_plugin.service_managers = self.service_managers
                exec_plugin.config = self.test_config

                # Add to execution environments
                self.environment_plugin_manager.append(exec_plugin)
                self.execution_environment_plugins.append(exec_plugin)

                self.logger.info(
                    f"Execution environment {env_type} set up successfully"
                )
            else:
                self.logger.warning(
                    f"Could not create execution environment plugin: {env_type}"
                )

        except Exception as e:
            self.logger.error(f"Failed to setup execution environment: {e}")
            # Continue with other environments

    def teardown_environment(self) -> None:
        """Tear down test environment using configured plugins."""
        # Prevent duplicate teardown calls
        if (
            hasattr(self, "_environment_teardown_complete")
            and self._environment_teardown_complete
        ):
            self.logger.debug("Environment teardown already completed, skipping")
            return

        self.logger.info("Tearing down test environment")

        try:
            for env_manager in self.environment_plugin_manager:
                try:
                    # Check if this specific environment manager is already torn down
                    if (
                        hasattr(env_manager, "teardown_complete")
                        and env_manager.teardown_complete
                    ):
                        self.logger.debug(
                            "Environment '%s' already torn down, skipping",
                            env_manager.__class__.__name__,
                        )
                        continue

                    env_manager.teardown_environment()
                    self.logger.info(
                        "Test environment torn down via '%s'",
                        env_manager.__class__.__name__,
                    )
                except Exception as e:
                    self.logger.error(
                        "Failed to tear down test environment via '%s': %s",
                        env_manager.__class__.__name__,
                        e,
                        exc_info=True,
                    )

            # Store environment type before clearing
            env_type = "unknown"
            if self.environment_plugin_manager:
                # Get the last environment manager's type
                env_type = (
                    self.environment_plugin_manager[-1].__class__.__name__
                    if self.environment_plugin_manager
                    else "unknown"
                )

            # Clear environment managers
            self.environment_plugin_manager.clear()
            self.execution_environment_plugins.clear()

            env_emitter = None
            if self.emitter_registry:
                env_emitter = self.emitter_registry.environment_emitter
            # Emit teardown completed event
            if env_emitter:
                env_emitter.emit_environment_teardown_completed(
                    environment_id=f"{env_type}_{self.test_name}",
                    environment_name=self.test_name,
                    environment_type=env_type,
                    cleanup_details={"test_name": self.test_config.name},
                )

            self.logger.info("Environment teardown completed")

            # Mark teardown as complete to prevent duplicate calls
            self._environment_teardown_complete = True

        except Exception as e:
            self.logger.error(f"Environment teardown failed: {e}")

    def deploy_services(self) -> None:
        """Deploy services through environment managers."""
        self.logger.info("Deploying services")

        # Initialize variables outside try block to ensure they're always available
        service_names = {}
        env_emitter = None
        env_plugin = None

        try:
            # Get environment emitter if available
            if self.emitter_registry:
                env_emitter = self.emitter_registry.environment_emitter

            service_names = self.get_service_names_and_metadata()
            self.logger.debug("Emitted service_setup_started event")

            successful_deployment = False
            # Deploy through each environment plugin
            for env_plugin in self.environment_plugin_manager:
                self.logger.debug(
                    f"Processing environment plugin: {type(env_plugin)} - {env_plugin.__class__.__name__}"
                )
                self.logger.debug(
                    f"Plugin MRO: {[cls.__name__ for cls in env_plugin.__class__.__mro__]}"
                )
                self.logger.debug(
                    f"is_network_environment(): {env_plugin.is_network_environment() if hasattr(env_plugin, 'is_network_environment') else 'method not found'}"
                )
                self.logger.debug(
                    f"isinstance(env_plugin, INetworkEnvironment): {isinstance(env_plugin, INetworkEnvironment)}"
                )
                if isinstance(env_plugin, INetworkEnvironment):
                    # Emit deployment started event
                    if env_emitter:
                        env_emitter.emit_environment_deployment_started(
                            environment_id=env_plugin.name,
                            environment_name=self.test_name,
                            environment_type=env_plugin.__class__.__name__,
                            services=service_names,
                            deployment_config={"test_case": self.test_name},
                        )
                    self.logger.info(
                        f"Deploying services with {env_plugin.__class__.__name__}"
                    )

                    try:
                        deployment_start_time = time.time()

                        # Run the services
                        env_plugin.run()

                        deployment_duration = time.time() - deployment_start_time

                        deployed_services_dict = {
                            name: "deployed" for name in service_names
                        }
                        self.logger.info("Services deployed successfully")

                        # Emit deployment completed event immediately after successful deployment
                        if env_emitter:
                            self.logger.debug(
                                f"Emitting deployment_completed event for {env_plugin.__class__.__name__}"
                            )
                            env_emitter.emit_environment_deployment_completed(
                                environment_id=env_plugin.name,
                                environment_name=self.test_name,
                                environment_type=env_plugin.__class__.__name__,
                                success=True,
                                deployed_services=deployed_services_dict,
                                duration=deployment_duration,
                                deployment_details={
                                    "service_count": len(self.service_managers)
                                },
                            )
                            self.logger.debug(
                                f"deployment_completed event emitted successfully"
                            )
                        else:
                            self.logger.warning(
                                "No environment emitter available to emit deployment_completed event"
                            )

                    except Exception as e:
                        self.logger.error(f"Failed to deploy services: {e}")
                        raise

        except Exception as e:
            self.logger.error(f"Service deployment failed: {e}")
            # Emit deployment failed event
            if env_emitter and env_plugin:
                failed_services = list(service_names.keys()) if service_names else []
                env_emitter.emit_environment_deployment_failed(
                    environment_id=env_plugin.name,
                    environment_name=self.test_name,
                    environment_type=env_plugin.__class__.__name__,
                    error_message=str(e),
                    error_type="Exception",
                    failed_services=failed_services,
                    error_details={"file_path": str(e)},
                )
            raise

    def get_service_names_and_metadata(self) -> Dict[str, Dict[str, Any]]:
        """
        Get service names and metadata for deployment.

        Returns:
            Dict mapping service names to metadata
        """
        service_metadata = {}

        for s in self.service_managers:
            service_name = s.service_name

            # Safely get service type - handle both enum and string cases
            service_type = None
            if hasattr(s, "get_service_type"):
                service_type = s.get_service_type()
            elif hasattr(s, "service_config_to_test") and hasattr(
                s.service_config_to_test, "implementation"
            ):
                impl_type = s.service_config_to_test.implementation.type
                # Handle both enum (with .value) and string cases
                if hasattr(impl_type, "value"):
                    service_type = impl_type.value
                else:
                    service_type = str(impl_type)
            else:
                service_type = "unknown"

            # Safely get implementation name
            implementation = None
            if hasattr(s, "get_implementation_name"):
                implementation = s.get_implementation_name()
            elif hasattr(s, "service_config_to_test") and hasattr(
                s.service_config_to_test, "implementation"
            ):
                implementation = s.service_config_to_test.implementation.name
            else:
                implementation = "unknown"

            service_metadata[service_name] = {
                "service_type": service_type,
                "implementation": implementation,
                "config": {
                    "test_case": self.test_name,
                    "protocol": (
                        s.service_config_to_test.protocol.name
                        if hasattr(s.service_config_to_test, "protocol")
                        else "unknown"
                    ),
                },
            }

        return service_metadata
