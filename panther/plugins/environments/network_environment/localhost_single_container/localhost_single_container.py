import os
from pathlib import Path
import subprocess
import traceback
from panther.core.observer.management.event_manager import EventManager
from panther.config.config_experiment_schema import TestConfig
from panther.config.config_global_schema import GlobalConfig
from panther.plugins.environments.config_schema import EnvironmentConfig
from panther.plugins.services.services_interface import IServiceManager
from panther.plugins.environments.execution_environment.execution_environment_interface import (
    IExecutionEnvironment,
)
from panther.plugins.plugin_loader import PluginLoader
from panther.plugins.environments.network_environment.network_environment_interface import (
    INetworkEnvironment,
)
from panther.core.events import BaseEvent as Event
from panther.plugins.plugin_decorators import register_plugin


@register_plugin(
    plugin_type="environment",
    name="localhost_single_container",
    version="1.0.0",
    description="Single container environment for fast local testing",
    author="PANTHER Team",
    capabilities=["single_container", "fast_deployment", "local_testing"],
    external_dependencies=["docker"],
)
class LocalhostSingleContainerEnvironment(INetworkEnvironment):
    """
       LocalhostSingleContainerEnvironment is a class that manages a single container environment on localhost for testing purposes.
       It extends the INetworkEnvironment interface and provides methods to prepare, set up, deploy, monitor, and tear down the environment.

       Attributes:
            (str): The version of Docker to use.
    docker_version       docker_name (str): The name prefix for the Docker container.
           services_network_config_file_path (Path): Path to the generated run.sh file.
           rendered_services_network_config_file_path (Path): Path to the rendered run.sh file.
           services_network_docker_file_path (Path): Path to the generated Dockerfile.
           rendered_services_network_docker_file_path (Path): Path to the rendered Dockerfile.

       Methods:
           __init__(env_config_to_test, output_dir, env_type, env_sub_type, event_manager):
               Initializes the LocalhostSingleContainerEnvironment with the given configuration.
           __str__():
               Returns a string representation of the LocalhostSingleContainerEnvironment instance.
           __repr__():
               Returns a string representation of the LocalhostSingleContainerEnvironment instance.
           prepare_environment():
               Prepares the service manager for use.
           setup_environment(services_managers, test_config, global_config, timestamp, plugin_loader, execution_environment):
           deploy_services():
               Deploys the services in the Localhost environment.
           generate_environment_services(paths, timestamp):
           launch_environment_services():
           monitor_environment():
           teardown_environment():
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
        self.name: str = f"localhost_single_container_{env_sub_type}"
        self.env_name: str = self.name

        # Store initialization details for future reference
        self.initialization_details: dict = {}

        self.docker_version = "v1"
        self.docker_name = "localhost_"

        self.services_network_config_file_path = Path(
            os.path.join(
                self._plugin_dir,
                env_type,
                env_sub_type,
                "run.generated.sh",
            )
        )
        self.rendered_services_network_config_file_path = Path(
            os.path.join(self.output_dir, "run.sh")
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
        return f"LocalhostSingleContainerEnvironment({self.__dict__})"

    def __repr__(self):
        return f"LocalhostSingleContainerEnvironment({self.__dict__})"

    def prepare_environment(self):
        """
        Prepare the service manager for use.
        """
        self.logger.info("Preparing Localhost service manager...")
        # Additional setup can be implemented here
        self.plugin_loader.build_docker_image_from_path(
            Path(
                os.path.join(
                    self._plugin_dir.parent,
                    "services",
                    "Dockerfile",
                )
            ),
            "localhost_single_container",
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
        self.logger.debug("Initializing Localhost Single Container environment")
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
                self.logger.debug(
                    "Event system initialized for Localhost Single Container environment"
                )

            # Ensure required directories exist
            os.makedirs(self.output_dir, exist_ok=True)
            os.makedirs(os.path.join(self.output_dir, "logs"), exist_ok=True)

            # Update log directories
            self.log_dirs = os.path.join(self.output_dir, "logs")

            # Update file paths
            self.rendered_services_network_config_file_path = Path(
                os.path.join(self.output_dir, "run.sh")
            )
            self.rendered_services_network_docker_file_path = Path(
                os.path.join(self.output_dir, "Dockerfile.experience")
            )

            # Set the name property if not already set
            if not hasattr(self, "name") or not self.name:
                self.name = f"localhost_single_container_{self.network_name}"
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
            self.logger.debug("Localhost Single Container environment initialized successfully")
            self.notify_environment_initialized(details=details)

            return True
        except Exception as e:
            self.logger.error(
                f"Failed to initialize Localhost Single Container environment: {e}", exc_info=True
            )
            return False

    def _setup_environment(self) -> bool:
        """
        Sets up the Localhost Single Container environment by preparing directories and configuration files.

        Returns:
            bool: True if setup was successful, False otherwise
        """
        self.logger.info("Setting up Localhost Single Container environment")
        try:
            # Ensure the output directory exists
            os.makedirs(self.output_dir, exist_ok=True)
            os.makedirs(os.path.join(self.output_dir, "logs"), exist_ok=True)
            self.logger.debug("Output directories created at %s", self.output_dir)

            # Log successful setup
            self.logger.info("Localhost Single Container environment setup complete")

            # Mark plugin as successfully set up
            self.plugin_setup = True
            return True
        except Exception as e:
            self.logger.error(
                "Failed to set up Localhost Single Container environment: %s\n%s",
                e,
                traceback.format_exc(),
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
        Sets up the Localhost Single Container environment by generating the run.sh file with deployment commands.

        Args:
            services_managers: List of service manager instances
            test_config: Test configuration
            global_config: Global configuration
            timestamp: Timestamp string for file naming
            plugin_loader: Plugin loader instance
            execution_environment: List of execution environment plugins

        Raises:
            RuntimeError: If the setup fails or run.sh file cannot be generated
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
                        "environment_type": "localhost_single_container",
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
                error_msg = f"Failed to set up Localhost Single Container environment: run.sh file not found at {os.path.abspath(str(self.rendered_services_network_config_file_path))}"
                self.logger.error(error_msg)

                # Notify about environment setup failure
                if hasattr(self, "event_emitter") and self.event_emitter:
                    self.notify_environment_setup_completed(
                        success=False,
                        details={
                            "environment_type": "localhost_single_container",
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
                        "run_script": os.path.abspath(
                            str(self.rendered_services_network_config_file_path)
                        ),
                        "dockerfile": os.path.abspath(
                            str(self.rendered_services_network_docker_file_path)
                        ),
                        "environment_type": "localhost_single_container",
                        "test_case": test_case_name,
                    },
                )

            self.logger.info("Localhost environment setup complete")

        except Exception as e:
            self.logger.error(
                "Failed to set up Localhost Single Container environment: %s", e, exc_info=True
            )

            # Notify about environment setup failure
            if hasattr(self, "event_emitter") and self.event_emitter:
                self.notify_environment_setup_completed(
                    success=False,
                    details={
                        "environment_type": "localhost_single_container",
                        "test_case": test_case_name,
                        "error": str(e),
                    },
                )

            # Propagate the error
            raise RuntimeError(f"Localhost Single Container environment setup failed: {str(e)}")

    def deploy_services(self, service_managers=None):
        """
        Deploy services in the Localhost Single Container environment.

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
        Generates the run.sh file using the provided services and deployment commands.

        :param paths: Dictionary containing various path configurations.
        :param timestamp: The timestamp string to include in log paths.
        """
        # TODO add timeout in the test config
        # TODO check that the implementaion is compatible with shadow (in config file)
        # TODo moodify the shadow template to add the timeout also add folder for each service to be added in the multi stage
        try:
            self.setup_execution_plugins(timestamp)
            # Ensure the log directory for each service exists
            for service in self.services_managers:
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
                    ].replace("$$TARGET_IP_HEX", "0x7f000001")
                    service.run_cmd["run_cmd"]["command_args"] = service.run_cmd["run_cmd"][
                        "command_args"
                    ].replace("$$IVY_IP_HEX", "0x7f000001")
                else:
                    service.run_cmd["run_cmd"]["command_args"] = service.run_cmd["run_cmd"][
                        "command_args"
                    ].replace("$$TARGET_IP_HEX", "0x7f000001")
                    service.run_cmd["run_cmd"]["command_args"] = service.run_cmd["run_cmd"][
                        "command_args"
                    ].replace("$$IVY_IP_HEX", "0x7f000001")
                for other_service in self.services_managers:
                    if other_service.service_name != service.service_name:
                        # Shadow does not suport the _ in the service name -> replace by .
                        # TODO use "." in the service name for all plugins
                        service.run_cmd["run_cmd"]["command_args"] = (
                            service.run_cmd["run_cmd"]["command_args"]
                            .replace(other_service.service_name, "127.0.0.1")
                            .replace("eth0", "lo")
                        )
                        other_service.run_cmd["run_cmd"]["command_args"] = (
                            other_service.run_cmd["run_cmd"]["command_args"]
                            .replace(service.service_name, "127.0.0.1")
                            .replace("eth0", "lo")
                        )

            for service in self.services_managers:
                service.environments = self.resolve_environment_variables(service.environments)
                self.logger.debug(
                    "Service %s environment: %s", service.service_name, service.environments
                )

            self.generate_from_template(
                "run.sh.jinja",
                paths,
                timestamp,
                self.rendered_services_network_config_file_path,
                self.services_network_config_file_path,
            )

            self.logger.info(
                "Localhost file generated at '%s'", self.services_network_config_file_path
            )

            self.logger.info("Localhost based environment manager prepared.")
            self.generate_from_template(
                "Dockerfile.experience.jinja",
                paths,
                timestamp,
                self.rendered_services_network_docker_file_path,
                self.services_network_docker_file_path,
                self.services_network_config_file_path.name,
            )

            self.logger.info(
                "Localhost file Dockerfile generated at '%s'",
                self.services_network_docker_file_path,
            )

            self.get_docker_name()

        except Exception as e:
            self.logger.error(
                "Failed to generate Localhost file: %s\n%s", e, traceback.format_exc()
            )
            exit(1)

    def launch_environment_services(self):
        """
        Launches the Localhost environment using the generated run.sh file.
        """
        # TODO use docker_builder module
        try:
            with open(os.path.join(self.output_dir, "logs", "localhost.log"), "w") as log_file:
                with open(
                    os.path.join(self.output_dir, "logs", "localhost.err.log"), "w"
                ) as log_file_err:
                    volumes = [
                        "-v",
                        f"{os.path.abspath(self.log_dirs + '/localhost')}:/app/logs/",
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
                        "--privileged",
                        "--sysctl",
                        "net.ipv6.conf.all.disable_ipv6=1",
                        "--platform=linux/amd64",
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
                self.logger.info("Localhost environment launched successfully.")
        except subprocess.CalledProcessError as e:
            self.logger.error("Failed to launch Localhost environment: %s", e.stderr)
            with open(os.path.join(self.output_dir, "logs", "localhost.log"), "w") as log_file:
                with open(
                    os.path.join(self.output_dir, "logs", "localhost.err.log"), "w"
                ) as log_file_err:
                    log_file.write(e.stdout)
                    log_file_err.write(e.stderr)
            # raise e

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
                        self.event_manager.notify(Event(name="experiment_finished_early", data={}))

                self.logger.debug("Docker Compose environment monitored successfully.")
        except subprocess.CalledProcessError as e:
            self.logger.error("Failed to monitor Docker Compose environment: %s", e.stderr)
            raise e

    def teardown_environment(self):
        """
        Tears down the Localhost environment by bringing down services.
        """
        # TODO: add a way to retrieve the logs, results, binary
        with open(os.path.join(self.output_dir, "logs", "localhost-teardown.log"), "w") as log_file:
            with open(
                os.path.join(self.output_dir, "logs", "localhost-teardown.err.log"), "w"
            ) as log_file_err:
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

                    # Remove the docker image after execution
                    remove_image_command = [
                        "docker",
                        "rm",
                        "--force",
                        f"{self.docker_name}",
                    ]
                    self.logger.debug(
                        "Executing remove container command: %s", remove_image_command
                    )
                    result = subprocess.run(
                        remove_image_command,
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    self.logger.debug("Executing command: %s", remove_image_command)

                    log_file.write(result.stdout)
                    log_file_err.write(result.stderr)

                    # Remove the docker image after execution
                    remove_image_command = [
                        "docker",
                        "rmi",
                        "--force",
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
                    self.logger.info("Localhost environment torn down successfully")
                except subprocess.CalledProcessError as e:
                    self.logger.error("Failed to tear down Localhost environment: %s", e.stderr)
                    with open(
                        os.path.join(self.output_dir, "logs", "localhost-teardown.log"),
                        "w",
                    ) as log_file:
                        with open(
                            os.path.join(self.output_dir, "logs", "localhost-teardown.err.log"),
                            "w",
                        ) as log_file_err:
                            try:
                                stop_container_command = [
                                    "docker",
                                    "stop",
                                    self.docker_name,
                                ]
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
                                # Remove the docker image after execution
                                remove_image_command = [
                                    "docker",
                                    "rmi",
                                    f"--force{self.docker_name}:latest",
                                ]
                                self.logger.debug(
                                    "Executing remove image command: %s", remove_image_command
                                )
                                result = subprocess.run(
                                    remove_image_command,
                                    check=True,
                                    capture_output=True,
                                    text=True,
                                )
                                self.logger.debug("Executing command: %s", remove_image_command)

                                log_file.write(result.stdout)
                                log_file_err.write(result.stderr)
                                self.logger.info("Localhost environment torn down successfully")
                            except subprocess.CalledProcessError as e:
                                self.logger.error(
                                    "Failed to tear down Localhost environment: %s", e.stderr
                                )
                                raise e

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
        Implementation of environment setup for Localhost Single Container.

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
            raise RuntimeError(
                "Localhost Single Container environment setup failed: run.sh file not generated"
            )

        # Mark setup as complete
        self.plugin_setup = True

    def _do_deploy_services(self) -> None:
        """
        Implementation of service deployment for Localhost Single Container.

        This method is called by the base class deploy_services after emitting
        the appropriate start events.
        """
        # Launch the localhost services
        self.launch_environment_services()

    def _do_teardown_environment(self) -> None:
        """
        Implementation of environment teardown for Localhost Single Container.

        This method is called by the base class teardown_environment after emitting
        the appropriate start events.
        """
        # Perform the actual teardown operations
        log_dir = os.path.join(self.output_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)

        with open(os.path.join(log_dir, "localhost-teardown.log"), "w") as log_file:
            with open(os.path.join(log_dir, "localhost-teardown.err.log"), "w") as log_file_err:
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
                        "--force",
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
                    self.logger.info("Localhost environment torn down successfully")
                    # Note: Event notification is handled by the base class
                except subprocess.CalledProcessError as e:
                    self.logger.error("Failed to tear down Localhost environment: %s", e.stderr)
                    raise e

    def handle_event(self, event) -> None:
        """
        Handle events sent to this plugin.

        The Localhost Single Container environment doesn't need to handle specific events,
        so this is a no-op implementation.

        Args:
            event: The event to handle
        """
        # Localhost Single Container environment doesn't handle events
        pass
