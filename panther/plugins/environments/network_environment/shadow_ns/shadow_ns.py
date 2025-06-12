import os
from pathlib import Path
import subprocess
import traceback
from typing import Any
import yaml
from panther.core.observer.management.event_manager import EventManager
from panther.config.config_experiment_schema import TestConfig
from panther.config.config_global_schema import GlobalConfig
from panther.plugins.services.services_interface import IServiceManager
from panther.plugins.environments.config_schema import EnvironmentConfig
from panther.plugins.environments.execution_environment.execution_environment_interface import (
    IExecutionEnvironment,
)
from panther.plugins.plugin_loader import PluginLoader
from panther.plugins.environments.network_environment.network_environment_interface import (
    INetworkEnvironment,
)
from panther.plugins.plugin_decorators import register_plugin


@register_plugin(
    plugin_type="environment",
    name="shadow_ns",
    version="1.0.0",
    description="Shadow Network Simulator - Deterministic network simulation environment",
    author="PANTHER Team",
    capabilities=["network_simulation", "deterministic", "time_control", "topology_modeling"],
    external_dependencies=["docker", "shadow>=2.0"],
)
class ShadowNsEnvironment(INetworkEnvironment):
    """
    ShadowNsEnvironment is a class that manages the Shadow NS environment for testing purposes.
    It extends the INetworkEnvironment interface and provides methods to prepare, set up, deploy,
    monitor, and tear down the environment.

    - Real Applications:
      Shadow directly executes real, unmodified application binaries natively in Linux as standard OS
      processes and co-opts them into a discrete-event simulation.

    - Simulated Networks:
      Shadow intercepts and emulates system calls made by the co-opted processes, connecting them through
      an internal network using simulated implementations of common network protocols (e.g., TCP and UDP).
      (Reproducible experiments)

    - High Performance:
      Shadow focuses on high performance simulation, efficiently simulating both small client/server networks
      and large distributed systems. Shadow has been used to simulate real-world peer-to-peer networks such
      as Tor and Bitcoin.

    <!> Not all IUTs are compatible with Shadow (missing system calls, etc.)

    This network environment encapsulates the Shadow NS and all the services in a *single* Docker container.

    See: https://shadow.github.io/

    Attributes:
        docker_version (str): The version of the Docker image.
        docker_name (str): The name of the Docker container.
        services_network_config_file_path (Path): Path to the generated services network configuration file.
        rendered_services_network_config_file_path (Path): Path to the rendered services network configuration file.
        services_network_docker_file_path (Path): Path to the generated Dockerfile for services network.
        rendered_services_network_docker_file_path (Path): Path to the rendered Dockerfile for services network.

    Methods:
        __init__(self, env_config_to_test: EnvironmentConfig, output_dir: str, env_type: str, env_sub_type: str, event_manager: EventManager):
            Initializes the ShadowNsEnvironment with the given configuration.

        __str__(self):
            Returns a string representation of the ShadowNsEnvironment instance.

        __repr__(self):
            Returns a string representation of the ShadowNsEnvironment instance.

        prepare_environment(self):
            Prepares the service manager for use by building the Docker image.

        setup_environment(self, services_managers: List[IServiceManager], test_config: TestConfig, global_config: GlobalConfig, timestamp: str, plugin_loader: PluginLoader, execution_environment: List[IExecutionEnvironment]):

        deploy_services(self):
            Deploys the services in the Shadow NS environment.

        generate_environment_services(self, paths: Dict[str, str], timestamp: str):

        launch_environment_services(self):

        monitor_environment(self):

        teardown_environment(self):

        read_shadow_file(self) -> Dict[str, Any]:
            Reads the generated shadow.yml file and returns its contents as a dictionary.
    """

    def __init__(
        self,
        env_config_to_test: EnvironmentConfig,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager: EventManager,
    ):
        super().__init__(env_config_to_test, output_dir, env_type, env_sub_type, event_manager)

        # Set the name attribute required for event emission
        self.name: str = f"shadow_ns_{env_sub_type}"
        self.env_name: str = self.name

        # Store initialization details for future reference
        self.initialization_details: dict = {}

        self.docker_version = "v1"
        self.docker_name = "shadow_"

        self.services_network_config_file_path = Path(
            os.path.join(
                self._plugin_dir,
                env_type,
                env_sub_type,
                f"{env_sub_type}.generated.yml",
            )
        )
        self.rendered_services_network_config_file_path = Path(
            os.path.join(self.output_dir, f"{env_sub_type}.yml")
        )

        self.services_network_docker_file_path = Path(
            os.path.join(
                self._plugin_dir,
                env_type,
                env_sub_type,
                "Dockerfile.generated",
            )
        )
        self.rendered_services_network_docker_file_path = Path(
            os.path.join(self.output_dir, "Dockerfile.experience")
        )

    def __str__(self):
        return f"ShadowNsEnvironment({self.__dict__})"

    def __repr__(self):
        return f"ShadowNsEnvironment({self.__dict__})"

    def prepare_environment(self):
        """
        Prepare the service manager for use.
        """
        self.logger.info("Preparing Shadow NS service manager...")
        self.plugin_loader.build_docker_image_from_path(
            Path(
                os.path.join(
                    self._plugin_dir,
                    "network_environment",
                    "shadow_ns",
                    "Dockerfile",
                )
            ),
            "shadow_ns",
            self.docker_version,
        )

    def initialize(self, test_config, output_dir, event_manager, global_config):
        """
        Initializes the environment with configuration settings.

        Args:
            test_config: Test configuration to use for this environment
            output_dir: Directory to write environment files
            event_manager: Shared event manager instance for emitting events
            global_config: Global configuration settings

        Returns:
            bool: True if initialization succeeded, False otherwise
        """
        self.logger.debug("Initializing Shadow NS environment")
        try:
            # Set up essential parameters
            if isinstance(output_dir, Path):
                # Convert Path to string if needed
                output_dir = str(output_dir)

            self.output_dir: Path = Path(output_dir)
            self.test_config: TestConfig = test_config
            self.global_config: GlobalConfig = global_config

            # Ensure event system is properly set up
            if event_manager:
                self.event_manager = event_manager
                self.logger.debug("Event system initialized for Shadow NS environment")

            # Ensure required directories exist
            os.makedirs(self.output_dir, exist_ok=True)
            os.makedirs(os.path.join(self.output_dir, "logs"), exist_ok=True)

            # Update log directories
            self.log_dirs = os.path.join(self.output_dir, "logs")

            # Update file paths
            self.rendered_services_network_config_file_path = Path(
                os.path.join(self.output_dir, f"{self.env_sub_type}.yml")
            )
            self.rendered_services_network_docker_file_path = Path(
                os.path.join(self.output_dir, "Dockerfile.experience")
            )

            # Set the name property if not already set
            if not hasattr(self, "name") or not self.name:
                self.name = f"shadow_ns_{self.network_name}"
                self.env_name = self.name

            # Store initialization details
            details = {
                "environment_name": self.name,
                "output_dir": self.output_dir,
                "network_name": self.network_name,
            }

            # Store details in object for reference
            self.initialization_details = details

            # Emit environment initialization event
            self.logger.debug("Shadow NS environment initialized successfully")
            self.notify_environment_initialized(details=details)

            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize Shadow NS environment: {e}", exc_info=True)
            return False

    def _setup_environment(self) -> bool:
        """
        Sets up the Shadow NS environment by preparing directories and configuration files.

        Returns:
            bool: True if setup was successful, False otherwise
        """
        self.logger.info("Setting up Shadow NS environment")
        try:
            # Ensure the output directory exists
            os.makedirs(self.output_dir, exist_ok=True)
            os.makedirs(os.path.join(self.output_dir, "logs"), exist_ok=True)
            self.logger.debug("Output directories created at %s", self.output_dir)

            # Log successful setup
            self.logger.info("Shadow NS environment setup complete")

            # Mark plugin as successfully set up
            self.plugin_setup = True
            return True
        except Exception as e:
            self.logger.error(
                "Failed to set up Shadow NS environment: %s\n%s", e, traceback.format_exc()
            )
            return False

    def setup_environment(
        self,
        services_managers: list[IServiceManager],
        test_config: TestConfig,
        global_config: GlobalConfig,
        timestamp: str,
        plugin_loader: PluginLoader,
        execution_environment: list[IExecutionEnvironment],
    ):
        """
        Sets up the Shadow NS environment by generating the shadow.yml file with deployment commands.

        Args:
            services_managers: List of service manager instances
            test_config: Test configuration
            global_config: Global configuration
            timestamp: Timestamp string for file naming
            plugin_loader: Plugin loader instance
            execution_environment: List of execution environment plugins

        Raises:
            RuntimeError: If the setup fails or shadow.yml file cannot be generated
        """
        self.update_environment(
            execution_environment,
            global_config,
            plugin_loader,
            services_managers,
            test_config,
        )

        # Get test case name for events
        test_case_name = test_config.name if hasattr(test_config, "name") else "unknown_test"

        try:
            # Notify environment setup started
            if hasattr(self, "event_emitter") and self.event_emitter:
                self.notify_environment_setup_started(
                    details={
                        "environment_instance": self.__class__.__name__,
                        "environment_type": "shadow_ns",
                        "test_case": test_case_name,
                    }
                )

            # First ensure base environment setup is complete
            if not self._setup_environment():
                self.logger.error("Base environment setup failed")
                raise RuntimeError("Base environment setup failed")

            # Prepare the environment
            self.prepare_environment()

            # Generate environment services
            self.generate_environment_services(paths=self.global_config.paths, timestamp=timestamp)

            # Verify files were generated
            if not os.path.exists(self.rendered_services_network_config_file_path):
                error_msg = f"Failed to set up Shadow NS environment: shadow.yml file not found at {os.path.abspath(str(self.rendered_services_network_config_file_path))}"
                self.logger.error(error_msg)

                # Notify about environment setup failure
                if hasattr(self, "event_emitter") and self.event_emitter:
                    self.notify_environment_setup_completed(
                        success=False,
                        details={
                            "environment_type": "shadow_ns",
                            "test_case": test_case_name,
                            "error": error_msg,
                        },
                    )

                raise RuntimeError(error_msg)

            # Notify about successful environment setup
            if hasattr(self, "event_emitter") and self.event_emitter:
                self.notify_environment_setup_completed(
                    success=True,
                    details={
                        "shadow_config": os.path.abspath(
                            str(self.rendered_services_network_config_file_path)
                        ),
                        "dockerfile": os.path.abspath(
                            str(self.rendered_services_network_docker_file_path)
                        ),
                        "environment_type": "shadow_ns",
                        "test_case": test_case_name,
                    },
                )

            self.logger.info("Shadow NS environment setup complete")

        except Exception as e:
            self.logger.error("Failed to set up Shadow NS environment: %s", e, exc_info=True)

            # Notify about environment setup failure
            if hasattr(self, "event_emitter") and self.event_emitter:
                self.notify_environment_setup_completed(
                    success=False,
                    details={
                        "environment_type": "shadow_ns",
                        "test_case": test_case_name,
                        "error": str(e),
                    },
                )

            # Propagate the error
            raise RuntimeError(f"Shadow NS environment setup failed: {str(e)}")

    def deploy_services(self, service_managers=None):
        """
        Deploy services in the Shadow NS environment.

        Args:
            service_managers: Optional list of service managers to deploy.
                              If provided, updates the internal services_managers list.
        """
        self.logger.info("Deploying services")

        # Update services_managers if provided
        if service_managers is not None:
            self.services_managers = service_managers

        self.launch_environment_services()

    def generate_environment_services(self, paths: dict[str, str], timestamp: str):
        """
        Generates the shadow.yml file using the provided services and deployment commands.

        :param paths: Dictionary containing various path configurations.
        :param timestamp: The timestamp string to include in log paths.
        """
        # TODO add timeout in the test config
        # TODO check that the implementaion is compatible with shadow (in config file)
        # TODo moodify the shadow template to add the timeout also add folder for each service to be added in the multi stage
        try:
            # Ensure the log directory for each service exists
            for service in self.services_managers:
                assert (
                    service.service_config_to_test.implementation.shadow_compatible
                ), f"Service {service.service_name} is not compatible with Shadow NS. Please check the service configuration."
                self.create_log_dir(service)

                self.logger.debug("Generating Docker Compose file for %s", service.service_name)

                self.docker_name = self.docker_name + service.service_name + "_"

                service.run_cmd["run_cmd"]["command_args"] = service.run_cmd["run_cmd"][
                    "command_args"
                ].replace("eth0", "lo")
                # TODO make this more general
                if service.role.name == "client":
                    service.run_cmd["run_cmd"]["command_args"] = service.run_cmd["run_cmd"][
                        "command_args"
                    ].replace("$$TARGET_IP_HEX", "184549377")
                    service.run_cmd["run_cmd"]["command_args"] = service.run_cmd["run_cmd"][
                        "command_args"
                    ].replace("$$IVY_IP_HEX", "184549378")
                else:
                    service.run_cmd["run_cmd"]["command_args"] = service.run_cmd["run_cmd"][
                        "command_args"
                    ].replace("$$TARGET_IP_HEX", "184549378")
                    service.run_cmd["run_cmd"]["command_args"] = service.run_cmd["run_cmd"][
                        "command_args"
                    ].replace("$$IVY_IP_HEX", "184549377")
                for other_service_name in self.services_managers:
                    if other_service_name.service_name != service.service_name:
                        # Shadow does not suport the _ in the service name -> replace by .
                        # TODO use "." in the service name for all plugins
                        if "ivy" not in service.service_name:
                            # TODO
                            service.run_cmd["run_cmd"]["command_args"] = service.run_cmd["run_cmd"][
                                "command_args"
                            ].replace("_", ".")

            for service in self.services_managers:
                service.environments = self.resolve_environment_variables(service.environments)
                service.environments["SHADOW_TEST"] = "1"
                self.logger.debug(
                    "Service %s environment: %s", service.service_name, service.environments
                )

            self.generate_from_template(
                "shadow-template.jinja",
                paths,
                timestamp,
                self.rendered_services_network_config_file_path,
                self.services_network_config_file_path,
            )

            self.logger.info(
                "Shadow NS file generated at '%s'", self.services_network_config_file_path
            )

            self.logger.info("Shadow NS based environment manager prepared.")
            # Define docker container for experience
            self.generate_from_template(
                "Dockerfile.experience.jinja",
                paths,
                timestamp,
                self.rendered_services_network_docker_file_path,
                self.services_network_docker_file_path,
                str(self.services_network_config_file_path.name),
            )

            self.logger.info(
                "Shadow NS file Dockerfile generated at '%s'",
                self.services_network_docker_file_path,
            )

            self.get_docker_name()

        except Exception as e:
            self.logger.error(
                "Failed to generate Shadow NS file: %s\n%s", e, traceback.format_exc()
            )
            exit(1)

    def launch_environment_services(self):
        """
        Launches the Shadow NS environment using the generated shadow.yml file.
        """
        # TODO use docker_builder module
        try:
            with open(os.path.join(self.output_dir, "logs", "shadow.log"), "w") as log_file:
                with open(
                    os.path.join(self.output_dir, "logs", "shadow.err.log"), "w"
                ) as log_file_err:
                    volumes = [
                        "-v",
                        f"{os.path.abspath(self.log_dirs + '/shadow')}:/app/logs/",
                    ]
                    for service in self.services:
                        for volume in service.volumes:
                            volumes.append("-v")
                            if isinstance(volume, dict):
                                volumes.append(
                                    f"{os.path.abspath(volume['local'])}:{volume['container']}"
                                )
                            else:
                                volumes.append(f"{volume}")

                    command = [
                        "docker",
                        "run",
                        "--rm",
                        "-d",
                        "--platform=linux/amd64",
                        "--sysctl",
                        "net.ipv6.conf.all.disable_ipv6=1",
                        "--security-opt",
                        "seccomp=unconfined",
                        "--shm-size=1024g",
                        "--privileged",
                        "--name",
                        self.docker_name,
                        *volumes,
                        self.docker_name,
                    ]
                    self.logger.debug("Executing command: %s", " ".join(command))
                    result = subprocess.run(
                        command,
                        check=True,
                        capture_output=True,
                        text=True,  # Ensures that output is in string format
                    )
                    # Write both stdout and stderr to the log file
                    log_file.write(result.stdout)
                    log_file_err.write(result.stderr)
                    # TODO shadow.data
                self.logger.info("Shadow NS environment launched successfully.")
        except subprocess.CalledProcessError as e:
            self.logger.error("Failed to launch Shadow NS environment: %s", e.stderr)
            with open(os.path.join(self.output_dir, "logs", "shadow.log"), "w") as log_file:
                with open(
                    os.path.join(self.output_dir, "logs", "shadow.err.log"), "w"
                ) as log_file_err:
                    log_file.write(e.stdout)
                    log_file_err.write(e.stderr)

    def monitor_environment(self):
        """
        Monitors the Docker Compose environment by checking the status of services.
        """
        try:
            with open(
                os.path.join(self.output_dir, "logs", "docker-compose-ps.log"), "w"
            ) as log_file:
                with open(
                    os.path.join(self.output_dir, "logs", "docker-compose-ps.err.log"),
                    "w",
                ) as log_file_err:
                    result = subprocess.run(
                        [
                            "docker",
                            "ps",
                            "-f",
                            f"name={self.docker_name}",
                        ],
                        check=True,
                        capture_output=True,
                        text=True,  # Ensures that output is in string format
                    )
                    # Write both stdout and stderr to the log file
                    log_file.write(result.stdout)
                    log_file_err.write(result.stderr)
                    # NAME      IMAGE     COMMAND   SERVICE   CREATED   STATUS    PORTS
                    #
                    std_split = result.stdout.split("\n")
                    self.logger.debug(
                        "docker-compose ps: %s - %s - %s  - %s",
                        result.stdout,
                        result.stderr,
                        len(self.services_managers),
                        len(std_split),
                    )
                    if len(std_split) < len(self.services_managers) + 1:
                        self.logger.debug(
                            "Docker Compose environment monitored successfully - Experiment finished earlier"
                        )

                        # Use the mixin method instead of directly notifying
                        reason = "Services finished early"
                        self.notify_experiment_early_finish(
                            reason=reason,
                            details={
                                "expected_services": len(self.services_managers),
                                "found_services": len(std_split) - 1,  # One line for header
                                "docker_output": result.stdout.strip(),
                            },
                        )

                self.logger.debug("Docker Compose environment monitored successfully.")
        except subprocess.CalledProcessError as e:
            self.logger.error("Failed to monitor Docker Compose environment: %s", e.stderr)
            raise e

    def teardown_environment(self):
        """
        Tears down the Shadow NS environment by bringing down services.
        """
        # TODO: add a way to retrieve the logs, results, binary
        with open(os.path.join(self.output_dir, "logs", "shadow-teardown.log"), "w") as log_file:
            with open(
                os.path.join(self.output_dir, "logs", "shadow-teardown.err.log"), "w"
            ) as log_file_err:
                try:
                    # Remove the docker image after execution
                    remove_image_command = [
                        "docker",
                        "rmi",
                        f"{self.docker_name}:latest",
                    ]
                    self.logger.debug("Executing remove image command: %s", remove_image_command)
                    result = subprocess.run(
                        remove_image_command,
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    self.logger.debug("Executing command: %s", remove_image_command)

                    log_file.write(result.stdout)
                    log_file_err.write(result.stderr)
                    self.logger.info("Shadow NS environment torn down successfully")

                    # Notify teardown completed with success
                    self.notify_environment_teardown(
                        success=True,
                        details={
                            "container_count": (
                                len(self.services_managers)
                                if hasattr(self, "services_managers")
                                else 0
                            )
                        },
                    )
                except subprocess.CalledProcessError as e:
                    self.logger.error("Failed to tear down Shadow NS environment: %s", e.stderr)

                    # Notify teardown completed with failure
                    self.notify_environment_teardown(
                        success=False, details={"error": str(e), "error_type": type(e).__name__}
                    )

                    raise e

    def read_shadow_file(self) -> dict[str, Any]:
        """
        Reads the generated shadow.yml file.
        """
        if not os.path.exists(self.services_network_config_file_path):
            self.logger.error(
                "Shadow NS file '%s' does not exist.", self.services_network_config_file_path
            )
            raise FileNotFoundError(
                f"Shadow NS file '{self.services_network_config_file_path}' does not exist."
            )

        with open(self.services_network_config_file_path) as compose_file:
            return yaml.safe_load(compose_file)

    def _do_setup_environment(
        self,
        services_managers: list["IServiceManager"],
        test_config: "TestConfig",
        global_config: "GlobalConfig",
        timestamp: str,
        plugin_loader: PluginLoader,
        execution_environment: list["IExecutionEnvironment"],
    ) -> None:
        """
        Implementation of environment setup for Shadow NS.

        This method is called by the base class setup_environment after emitting
        the appropriate start events.
        """
        # Store configuration
        self.update_environment(
            execution_environment,
            global_config,
            plugin_loader,
            services_managers,
            test_config,
        )

        # Prepare the environment
        self.prepare_environment()

        # Generate environment services
        self.generate_environment_services(paths=global_config.paths, timestamp=timestamp)

        # Verify files were generated
        if not os.path.exists(self.rendered_services_network_config_file_path):
            raise RuntimeError("Shadow NS environment setup failed: shadow.yml file not generated")

        # Mark setup as complete
        self.plugin_setup = True

    def _do_deploy_services(self) -> None:
        """
        Implementation of service deployment for Shadow NS.

        This method is called by the base class deploy_services after emitting
        the appropriate start events.
        """
        # Launch the shadow services
        self.launch_environment_services()

    def _do_teardown_environment(self) -> None:
        """
        Implementation of environment teardown for Shadow NS.

        This method is called by the base class teardown_environment after emitting
        the appropriate start events.
        """
        # Perform the actual teardown operations
        log_dir = os.path.join(self.output_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)

        with open(os.path.join(log_dir, "shadow-teardown.log"), "w") as log_file:
            with open(os.path.join(log_dir, "shadow-teardown.err.log"), "w") as log_file_err:
                try:
                    # Stop the running docker container
                    stop_container_command = ["docker", "stop", self.docker_name]
                    self.logger.debug(
                        "Executing stop container command: %s", stop_container_command
                    )
                    result = subprocess.run(
                        stop_container_command,
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    log_file.write(result.stdout)
                    log_file_err.write(result.stderr)

                    # Remove the docker container after execution
                    remove_container_command = [
                        "docker",
                        "rm",
                        "--force",
                        f"{self.docker_name}",
                    ]
                    self.logger.debug(
                        "Executing remove container command: %s", remove_container_command
                    )
                    result = subprocess.run(
                        remove_container_command,
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    log_file.write(result.stdout)
                    log_file_err.write(result.stderr)

                    # Remove the docker image after execution
                    remove_image_command = [
                        "docker",
                        "rmi",
                        f"{self.docker_name}:latest",
                    ]
                    self.logger.debug("Executing remove image command: %s", remove_image_command)
                    result = subprocess.run(
                        remove_image_command,
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    log_file.write(result.stdout)
                    log_file_err.write(result.stderr)
                    self.logger.info("Shadow NS environment torn down successfully")
                    # Note: Event notification is handled by the base class
                except subprocess.CalledProcessError as e:
                    self.logger.error("Failed to tear down Shadow NS environment: %s", e.stderr)
                    raise e

    def handle_event(self, event) -> None:
        """
        Handle events sent to this plugin.

        The Shadow NS environment doesn't need to handle specific events,
        so this is a no-op implementation.

        Args:
            event: The event to handle
        """
        # Shadow NS environment doesn't handle events
        pass
