"""Environment management functionality for test cases."""

import time
from typing import Any, Dict, List, Optional

from panther.plugins.environments.network_environment.network_environment_interface import (
    INetworkEnvironment,
)


class EnvironmentManagementMixin:
    """Mixin providing environment management capabilities for test cases."""

    def setup_environment(self) -> None:
        """Set up test environment using configured plugins."""
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
            exec_env_configs = self.test_config.execution_environments or []
            for exec_env_config in exec_env_configs:
                self._setup_execution_environment(exec_env_config)

            
            if isinstance(network_plugin, INetworkEnvironment):
                # Initialize network environment
                network_plugin.setup_environment(
                    services_managers=self.service_managers,
                    test_config=self.test_config,
                    global_config=self.global_config,
                    timestamp=time.strftime("%Y%m%d_%H%M%S"),
                    plugin_manager=self.plugin_manager,
                    execution_environment=self.execution_environment,
                )

                # Add to environment managers
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
                        "execution_environments": exec_env_configs,
                        "test_case": self.test_name,  # Add test case name to setup details
                    },
                )

            self.logger.info("Environment setup completed")

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
            # Get network environment plugin class
            network_plugin_class = (
                self.plugin_manager.get_network_environment_plugin(
                    self.test_config.network_environment.type
                )
            )

            if not network_plugin_class:
                raise ValueError(
                    f"Network environment plugin not found for type: {self.test_config.network_environment.type}"
                )

            # Create environment config from test config
            from panther.config.core.models.environment import EnvironmentConfig
            env_config = EnvironmentConfig(
                type=self.test_config.network_environment.type,
                config=self.test_config.network_environment.dict() if hasattr(self.test_config.network_environment, 'dict') else {}
            )
            
            # Create instance of the plugin with required arguments
            network_plugin = network_plugin_class(
                env_config_to_test=env_config,
                output_dir=str(self.test_experiment_dir),
                env_type="network_environment",
                env_sub_type=self.test_config.network_environment.type,
                event_manager=self.event_manager,
            )
            
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
            exec_plugin_class = (
                self.plugin_manager.get_execution_environment_plugin(
                    env_type,
                    output_dir=str(self.test_experiment_dir),
                    event_manager=self.event_manager,
                    global_config=self.global_config,
                    config=config,
                )
            )

            if exec_plugin_class:
                # Create instance of the plugin
                exec_plugin = exec_plugin_class(
                    output_dir=str(self.test_experiment_dir),
                    event_manager=self.event_manager,
                    global_config=self.global_config,
                    config=config,
                )
                
                # Add to execution environments
                self.environment_plugin_manager.append(exec_plugin)
                self.execution_environment.append(exec_plugin)

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
        self.logger.info("Tearing down test environment")

        try:
            for env_manager in self.environment_plugin_manager:
                try:
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
                env_type = self.environment_plugin_manager[-1].__class__.__name__ if self.environment_plugin_manager else "unknown"
            
            # Clear environment managers
            self.environment_plugin_manager.clear()
            self.execution_environment.clear()
            
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

        except Exception as e:
            self.logger.error(f"Environment teardown failed: {e}")

    def deploy_services(self) -> None:
        """Deploy services through environment managers."""
        self.logger.info("Deploying services")

        try:
            # Get environment emitter if available
            env_emitter = None
            if self.emitter_registry:
                env_emitter = self.emitter_registry.environment_emitter
                
                
            service_names = self.get_service_names_and_metadata()
            self.logger.debug("Emitted service_setup_started event")

            successful_deployment = False
            # Deploy through each environment plugin
            for env_plugin in self.environment_plugin_manager:
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
                        successful_deployment = True

                        # Run the services
                        env_plugin.run()
                        
                        deployment_duration = time.time() - deployment_start_time
                        
                        deployed_services_dict = {
                            name: "deployed" for name in service_names
                        }
                        self.logger.info("Services deployed successfully")
                    except Exception as e:
                        self.logger.error(f"Failed to deploy services: {e}")
                        raise

            # Emit deployment completed event
            if env_emitter:
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

        except Exception as e:
            self.logger.error(f"Service deployment failed: {e}")
            # Emit deployment failed event
            if env_emitter:
                failed_services = [name for name in service_names]
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

    def get_service_names_and_metadata(self):
        service_names = []
        service_metadata = []

        for s in self.service_managers:
                # Get service name
            service_name = (
                    s.service_name
                    if hasattr(s, "service_name")
                    else s.get_implementation_name()
                )
            service_names.append(service_name)

                # Build metadata for each service
            metadata = {
                    "service_type": (
                        s.get_service_type()
                        if hasattr(s, "get_service_type")
                        else s.service_config_to_test.implementation.type.value
                    ),
                    "implementation": (
                        s.get_implementation_name()
                        if hasattr(s, "get_implementation_name")
                        else s.service_config_to_test.implementation.name
                    ),
                    "config": {
                        "test_case": self.test_name,
                        "protocol": (
                            s.service_config_to_test.protocol.name
                            if hasattr(s.service_config_to_test, "protocol")
                            else "unknown"
                        ),
                        "role": (
                            s.service_config_to_test.protocol.role
                            if hasattr(s.service_config_to_test, "protocol")
                            and hasattr(s.service_config_to_test.protocol, "role")
                            else "unknown"
                        ),
                    },
                }
            service_metadata.append(metadata)

        self.service_emitter.emit_service_setup_started(
                test_case=self.test_name,
                service_count=len(self.service_managers),
                service_names=service_names,
                service_metadata=service_metadata,
            )
        
        return service_names
