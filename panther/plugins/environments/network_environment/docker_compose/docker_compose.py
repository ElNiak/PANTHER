import os
from pathlib import Path
import subprocess
from panther.core.observer.management.event_manager import EventManager
from panther.config.config_experiment_schema import TestConfig
from panther.config.config_global_schema import GlobalConfig
from panther.plugins.services.services_interface import IServiceManager
from panther.plugins.environments.config_schema import EnvironmentConfig
from panther.plugins.environments.execution_environment.execution_environment_interface import (
    IExecutionEnvironment,
)
from panther.plugins.plugin_loader import PluginLoader
import traceback
from panther.plugins.environments.network_environment.network_environment_interface import (
    INetworkEnvironment,
)
from panther.plugins.plugin_decorators import register_plugin


@register_plugin(
    plugin_type="environment",
    name="docker_compose",
    version="1.0.0",
    description="Docker Compose network environment for container orchestration",
    author="PANTHER Team",
    capabilities=["container_orchestration", "network_isolation", "service_discovery"],
    external_dependencies=["docker", "docker-compose>=2.0"],
)
class DockerComposeEnvironment(INetworkEnvironment):
    """
    DockerComposeEnvironment is a class that manages the setup, deployment, monitoring, and teardown of a
    Docker Compose environment.

    Attributes:
        services_network_config_file_path (Path): Path to the generated Docker Compose configuration file.
        rendered_services_network_config_file_path (Path): Path to the rendered Docker Compose configuration file.
    Methods:
        __init__(env_config_to_test, output_dir, env_type, env_sub_type, event_manager):
            Initializes the DockerComposeEnvironment with the given configuration and paths.
        __str__():
            Returns a string representation of the DockerComposeEnvironment instance.
        __repr__():
            Returns a string representation of the DockerComposeEnvironment instance.
        initialize(test_config, output_dir, event_manager, global_config):
            Initializes the environment with configuration and resources.
        setup_environment(services_managers, test_config, global_config, timestamp, plugin_loader, execution_environment):
        prepare_environment():
            Prepares the environment (currently not implemented).
        deploy_services():
            Deploys the services defined in the Docker Compose environment.
        generate_environment_services(paths, timestamp):
        launch_environment_services():
        monitor_environment():
        teardown_environment():
        is_network_environment():
            Returns True to indicate this is a network environment.
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
        self.name: str = f"docker_compose_{env_sub_type}"
        self.env_name: str = self.name

        # Store initialization details for future reference
        self.initialization_details: dict = {}

        self.services_network_config_file_path: Path = Path(
            os.path.join(
                self._plugin_dir,
                env_type,
                env_sub_type,
                f"{env_sub_type}.generated.yml",
            )
        )
        self.rendered_services_network_config_file_path: Path = Path(
            os.path.join(self.output_dir, f"{env_sub_type}.yml")
        )

        self.services_network_script_file_path: Path = Path(
            os.path.join(
                self._plugin_dir,
                env_type,
                env_sub_type,
                "entrypoint.generated.sh",
            )
        )
        self.rendered_services_network_script_file_path: Path = Path(
            os.path.join(self.output_dir, "entrypoint.sh")
        )

    def __str__(self):
        return f"DockerComposeEnvironment({self.__dict__})"

    def __repr__(self):
        return f"DockerComposeEnvironment({self.__dict__})"

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
        self.logger.debug("Initializing Docker Compose environment")
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
                # event_emitter is already initialized in parent class IEnvironmentPlugin
                self.logger.debug("Event system initialized for Docker Compose environment")

            # Ensure required directories exist
            os.makedirs(self.output_dir, exist_ok=True)
            os.makedirs(os.path.join(self.output_dir, "logs"), exist_ok=True)

            # Update log directories
            self.log_dirs = os.path.join(self.output_dir, "logs")

            # Update docker compose file paths
            self.rendered_services_network_config_file_path = Path(
                os.path.join(self.output_dir, f"{self.env_sub_type}.yml")
            )

            self.rendered_services_network_script_file_path = Path(
                os.path.join(self.output_dir, "entrypoint.sh")
            )

            # Set the name property if not already set
            if not hasattr(self, "name") or not self.name:
                self.name = f"docker_compose_{self.network_name}"
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
            self.logger.debug("Docker Compose environment initialized successfully")
            self.notify_environment_initialized(details=details)

            return True
        except Exception as e:
            self.logger.error(
                f"Failed to initialize Docker Compose environment: {e}", exc_info=True
            )
            return False

    def _setup_environment(self) -> bool:
        """
        Sets up the Docker Compose environment by preparing directories and configuration files.

        Returns:
            bool: True if setup was successful, False otherwise
        """
        self.logger.info("Setting up Docker Compose environment")
        try:
            # Ensure the output directory exists
            os.makedirs(self.output_dir, exist_ok=True)
            os.makedirs(os.path.join(self.output_dir, "logs"), exist_ok=True)
            self.logger.debug("Output directories created at %s", self.output_dir)

            # Log successful setup
            self.logger.info("Docker Compose environment setup complete")

            # Mark plugin as successfully set up
            self.plugin_setup = True
            return True
        except Exception as e:
            self.logger.error(
                "Failed to set up Docker Compose environment: %s\n%s", e, traceback.format_exc()
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
        Sets up the Docker Compose environment by generating the docker-compose.yml file with deployment commands.

        Args:
            services_managers: List of service manager instances
            test_config: Test configuration
            global_config: Global configuration
            timestamp: Timestamp string for file naming
            plugin_loader: Plugin loader instance
            execution_environment: List of execution environment plugins

        Raises:
            RuntimeError: If the setup fails or Docker Compose file cannot be generated
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
                        "environment_type": "docker_compose",
                        "test_case": test_case_name,
                    }
                )

            # First ensure base environment setup is complete
            if not self._setup_environment():
                self.logger.error("Base environment setup failed")
                raise RuntimeError("Base environment setup failed")

            # Then generate Docker Compose file and verify it exists
            success = self._setup_environment_and_verify_files(timestamp)

            # Check if the setup was not successful
            if not success:
                error_msg = f"Failed to set up Docker Compose environment: Docker Compose file not found at {os.path.abspath(str(self.rendered_services_network_config_file_path))}"
                self.logger.error(error_msg)

                # Notify about environment setup failure
                if hasattr(self, "event_emitter") and self.event_emitter:
                    self.notify_environment_setup_completed(
                        success=False,
                        details={
                            "environment_type": "docker_compose",
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
                        "docker_compose_file": os.path.abspath(
                            str(self.rendered_services_network_config_file_path)
                        ),
                        "environment_type": "docker_compose",
                        "test_case": test_case_name,
                    },
                )

        except Exception as e:
            self.logger.error("Failed to set up Docker Compose environment: %s", e, exc_info=True)

            # Notify about environment setup failure
            if hasattr(self, "event_emitter") and self.event_emitter:
                self.notify_environment_setup_completed(
                    success=False,
                    details={
                        "environment_type": "docker_compose",
                        "test_case": test_case_name,
                        "error": str(e),
                    },
                )

            # Propagate the error
            raise RuntimeError(f"Docker Compose environment setup failed: {str(e)}")

    def prepare_environment(self):
        pass

    def deploy_services(self, service_managers=None):
        """
        Deploy services in the Docker Compose environment.

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
        Generates the docker-compose.yml file using the provided services and deployment commands.

        Args:
            paths: Dictionary containing various path configurations
            timestamp: The timestamp string to include in log paths

        Raises:
            RuntimeError: If there's an error in generating the Docker Compose file
        """
        try:
            self.logger.info("Generating Docker Compose environment services")

            # Ensure the log directory for each service exists
            self.setup_execution_plugins(timestamp)

            for service in self.services_managers:
                # Create log directories for each service
                self.create_log_dir(service)
                self.logger.debug("Generating Docker Compose file for %s", service.service_name)

                if "ivy" in service.service_name:
                    self.logger.debug(
                        "Adding wait for Ivy testers to be ready for %s", service.service_name
                    )
                    for other_service in self.services_managers:
                        if other_service.service_name != service.service_name:
                            self.wait_tester_command(other_service)

            for service in self.services_managers:
                self.tshark_command(service)
                self.logger.debug(
                    "Service %s environment: %s", service.service_name, service.environments
                )

            for service in self.services_managers:
                # Add debugging to declared functions in run_cmds (if any)
                for cmd_key, cmds in service.run_cmd.items():
                    self.logger.debug(
                        "Service %s command key: %s - %s", service.service_name, cmd_key, cmds
                    )

            # Generate entrypoint scripts for each service
            for service in self.services_managers:
                self.logger.debug(
                    "Generating entrypoint script for service %s", service.service_name
                )

                entrypoint_script_path = Path(
                    str(self.rendered_services_network_script_file_path).replace(
                        ".sh", f"_{service.service_name}.sh"
                    )
                )

                template_script_path = Path(
                    str(self.services_network_script_file_path).replace(
                        ".sh", f"_{service.service_name}.sh"
                    )
                )

                # Generate entrypoint script
                self.generate_entrypoint_with_structured_args(
                    service, paths, timestamp, entrypoint_script_path, template_script_path
                )

                # Verify entrypoint script was created
                if not os.path.exists(entrypoint_script_path):
                    raise RuntimeError(
                        f"Failed to generate entrypoint script for service {service.service_name}"
                    )

            # Generate main Docker Compose file
            self.logger.info("Generating main Docker Compose file")
            self.generate_from_template(
                "docker-compose-template.jinja",
                paths,
                timestamp,
                self.rendered_services_network_config_file_path,
                self.services_network_config_file_path,
            )

            # Cleanup temporary template files
            if self.services_network_script_file_path.exists():
                self.services_network_script_file_path.unlink()
                self.logger.debug("Deleted the file %s", self.services_network_script_file_path)

            # Verify Docker Compose file exists
            if not os.path.exists(self.rendered_services_network_config_file_path):
                raise RuntimeError(
                    f"Docker Compose file was not generated at expected location: {self.rendered_services_network_config_file_path}"
                )

            self.logger.info(
                "Docker Compose file successfully generated at '%s'",
                self.rendered_services_network_config_file_path,
            )
        except Exception as e:
            self.logger.error(
                "Failed to generate Docker Compose file: %s\n%s", e, traceback.format_exc()
            )
            # Raise a meaningful error that includes the original exception
            raise RuntimeError(f"Failed to generate Docker Compose environment services: {str(e)}")

    def tshark_command(self, service: IServiceManager):
        service.run_cmd["post_compile_cmds"] = service.run_cmd["post_compile_cmds"] + [
            "(touch /app/logs/"
            + service.service_name
            + ".pcap; tshark -a duration:"
            + str(service.service_config_to_test.timeout)
            + " -i any -w /app/logs/"
            + service.service_name
            + ".pcap;) & "
        ]

    def wait_tester_command(self, other_service: IServiceManager):
        other_service.volumes.append("shared_logs:/app/sync_logs")
        other_service.run_cmd["post_compile_cmds"] = other_service.run_cmd["post_compile_cmds"] + [
            "while [ ! -f /app/sync_logs/ivy_ready.log ]; do",
            '\techo "Waiting for Ivy testers to be ready..." >> /app/logs/tester_ready.log;',
            "\tsleep 2;",
            "done;",
            'echo "Ivy testers is ready, starting '
            + other_service.service_name
            + '..." >> /app/logs/tester_ready.log;',
        ]

    def _combine_shell_constructs(self, command_list):
        """
        Combine consecutive elements in a command list that form a single shell construct.

        This functionality has been moved to the global combine_shell_constructs() function
        in panther.core.command_processor.command. This method now serves as a wrapper around that function.

        Args:
            command_list: List of command strings or ShellCommand objects to process

        Returns:
            A new list with combined shell constructs as multiline strings or ShellCommand objects.
        """
        from panther.core.command_processor.command import combine_shell_constructs

        return combine_shell_constructs(command_list)

    def generate_entrypoint_with_structured_args(
        self,
        service: IServiceManager,
        paths: dict[str, str],
        timestamp: str,
        output_path: Path,
        template_path: Path,
    ):
        """
        Generates an entrypoint script with properly structured and quoted command arguments.

        This method uses a command processor to handle command arguments and environment variables,
        ensuring proper escaping of special characters in shell commands.

        Args:
            service: The service manager instance
            paths: Dictionary of path configurations
            timestamp: Timestamp string
            output_path: Path where the generated entrypoint script will be written
            template_path: Path to the template file (not used directly)
        """
        self.logger.debug(
            "Generating entrypoint script for %s with structured arguments", service.service_name
        )

        # Use the command processor to process the commands
        from panther.core.command_processor import CommandProcessor
        from panther.plugins.environments.network_environment.docker_compose.command_adapter import (
            DockerComposeCommandAdapter,
        )

        # Create instances of the command processor and adapter
        command_processor = CommandProcessor()
        adapter = DockerComposeCommandAdapter()

        # Process commands using the command processor
        processed_commands = command_processor.process_commands(service.run_cmd)

        # Apply Docker Compose specific adaptations
        processed_commands = adapter.adapt_commands(processed_commands)

        # Render entrypoint template with structured arguments
        self.logger.debug(
            "Rendering entrypoint template for service '%s' with structured commands",
            service,
        )
        self.generate_from_template(
            "entrypoint.sh.jinja",
            paths,
            timestamp,
            output_path,
            template_path,
            additional_param=service,
            structured_commands=processed_commands,
        )

    def launch_environment_services(self):
        """
        Launches the Docker Compose environment using the generated docker-compose.yml file.
        """
        try:
            # Ensure we have an absolute path for Docker Compose file
            compose_file_path = os.path.abspath(
                str(self.rendered_services_network_config_file_path)
            )
            self.logger.debug("Using Docker Compose file at absolute path: %s", compose_file_path)

            # Check if the file exists
            if not os.path.exists(compose_file_path):
                error_msg = f"Docker Compose file not found at {compose_file_path}"
                self.logger.error(error_msg)
                if self.event_emitter:
                    # Since we're in an environment plugin, emit an environment error
                    # Generate environment ID
                    env_type = getattr(self, "env_type", "network_environment")
                    env_subtype = getattr(self, "env_sub_type", "docker_compose")
                    environment_type = f"{env_type}_{env_subtype}".rstrip("_")
                    environment_name = getattr(self, "env_name", self.__class__.__name__)
                    environment_id = f"{environment_type}_{environment_name}"

                    self.event_emitter.emit_environment_error(
                        environment_id=environment_id,
                        environment_name=environment_name,
                        environment_type=environment_type,
                        error_message=error_msg,
                        error_type="FileNotFoundError",
                        error_details={"compose_file_path": compose_file_path},
                    )
                raise FileNotFoundError(error_msg)

            # Run Docker Compose
            self._run_docker_compose(compose_file_path)

        except Exception as e:
            self.logger.error("Failed to launch Docker Compose environment: %s", e, exc_info=True)
            if self.event_emitter:
                # Generate environment ID
                env_type = getattr(self, "env_type", "network_environment")
                env_subtype = getattr(self, "env_sub_type", "docker_compose")
                environment_type = f"{env_type}_{env_subtype}".rstrip("_")
                environment_name = getattr(self, "env_name", self.__class__.__name__)
                environment_id = f"{environment_type}_{environment_name}"

                self.event_emitter.emit_environment_error(
                    environment_id=environment_id,
                    environment_name=environment_name,
                    environment_type=environment_type,
                    error_message=f"Failed to launch Docker Compose environment: {str(e)}",
                    error_type=type(e).__name__,
                    error_details={"exception": str(e)},
                )
            raise

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
                            "compose",
                            "-f",
                            str(self.rendered_services_network_config_file_path),
                            "ps",
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
                    if len(std_split) < len(self.services_managers) * 2:
                        self.logger.debug(
                            "Docker Compose environment monitored successfully - Experiment finished earlier"
                        )
                        self.notify_experiment_early_finish(
                            reason="Services finished early",
                            details={
                                "expected_services": len(self.services_managers),
                                "found_services": len(std_split),
                                "message": "Docker Compose experiment finished earlier than expected",
                            },
                        )
                    else:
                        self.logger.info(
                            "Docker Compose environment monitored successfully - All services are running"
                        )

                self.logger.debug("Docker Compose environment monitored successfully.")
        except subprocess.CalledProcessError as e:
            self.logger.error("Failed to monitor Docker Compose environment: %s", e.stderr)
            raise e

    def teardown_environment(self):
        """
        Tears down the Docker Compose environment by bringing down services.
        """
        # TODO: add a way to retrieve the logs, results, binary
        with open(
            os.path.join(self.output_dir, "logs", "docker-compose-teardown.log"), "w"
        ) as log_file:
            with open(
                os.path.join(self.output_dir, "logs", "docker-compose-teardown.err.log"),
                "w",
            ) as log_file_err:
                try:
                    # For other network drivers, use docker-compose
                    result = subprocess.run(
                        [
                            "docker",
                            "compose",
                            "-f",
                            self.services_network_config_file_path,
                            "down",
                        ],
                        check=True,
                        capture_output=True,
                        text=True,  # Ensures that output is in string format
                    )
                    # Write both stdout and stderr to the log file
                    log_file.write(result.stdout)
                    log_file_err.write(result.stderr)
                    os.system("docker volume prune -a -f")
                    self.logger.info("Docker Compose environment torn down successfully")
                    self.notify_environment_teardown(success=True)  # TODO
                except subprocess.CalledProcessError as e:
                    self.logger.error(
                        "Failed to tear down Docker Compose environment: %s", e.stderr
                    )
                    raise e

    def is_network_environment(self):
        """
        Returns True to indicate this is a network environment.
        """
        return True

    def _setup_environment_and_verify_files(self, timestamp) -> bool:
        """
        Helper method to set up environment and verify that required files are generated.

        Args:
            timestamp: The timestamp string for file path generation

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logger.info("Setting up Docker Compose environment and verifying files")

            # Ensure the output directory exists
            output_dir_path = os.path.dirname(str(self.rendered_services_network_config_file_path))
            os.makedirs(output_dir_path, exist_ok=True)

            logs_dir_path = os.path.join(self.output_dir, "logs")
            os.makedirs(logs_dir_path, exist_ok=True)

            self.logger.debug(
                "Output directories created: %s and %s", output_dir_path, logs_dir_path
            )

            # Generate environment services with the template processor
            self.logger.info("Generating Docker Compose configuration file")
            self.generate_environment_services(paths=self.global_config.paths, timestamp=timestamp)

            # Verify the file was created and is valid
            compose_path = os.path.abspath(str(self.rendered_services_network_config_file_path))

            if not os.path.exists(compose_path):
                self.logger.error("Docker Compose file not found at %s", compose_path)
                return False

            if os.path.getsize(compose_path) == 0:
                self.logger.error("Docker Compose file exists but is empty at %s", compose_path)
                return False

            # Additional validation could go here (e.g., parse YAML to verify structure)

            self.logger.info(
                "Docker Compose file successfully verified at %s (%s bytes)",
                compose_path,
                os.path.getsize(compose_path),
            )
            return True

        except Exception as e:
            self.logger.error("Error in _setup_environment_and_verify_files: %s", e, exc_info=True)
            return False

    def _run_docker_compose(self, compose_file_path):
        """
        Run Docker Compose commands with proper logging.

        Args:
            compose_file_path (str): Absolute path to the Docker Compose file

        Raises:
            subprocess.CalledProcessError: If Docker Compose command fails
        """
        # Create log files
        log_dir = os.path.join(self.output_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)

        with (
            open(os.path.join(log_dir, "docker-compose-up.log"), "w") as log_file,
            open(os.path.join(log_dir, "docker-compose-up.err.log"), "w") as log_file_err,
        ):

            # Run Docker Compose up
            docker_compose_cmd = [
                "docker",
                "compose",
                "-f",
                compose_file_path,
                "up",
                "-d",  # Detached mode: Run containers in the background
                "-V",  # Recreate anonymous volumes
                "--remove-orphans",  # Remove orphaned containers
            ]

            result = subprocess.run(
                docker_compose_cmd,
                capture_output=True,
                text=True,
                cwd=os.path.dirname(compose_file_path),
            )

            # Write logs
            log_file.write(result.stdout)
            log_file_err.write(result.stderr)

            # Check for failure and emit detailed error event
            if result.returncode != 0:
                error_details = {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "command": " ".join(docker_compose_cmd),
                    "return_code": result.returncode,
                    "compose_file": compose_file_path,
                    "working_directory": os.path.dirname(compose_file_path),
                }

                # Emit environment error with detailed information
                if hasattr(self, "environment_emitter") and self.environment_emitter:
                    self.environment_emitter.emit_environment_error(
                        environment_id=f"docker_compose_{os.path.basename(compose_file_path)}",
                        error_message=f"Docker compose failed: {result.stderr}",
                        error_type="docker_compose_failure",
                        error_details=error_details,
                    )

                # Also log the detailed error
                self.logger.error(
                    "Docker Compose command failed with return code %d", result.returncode
                )
                self.logger.error("Command: %s", " ".join(docker_compose_cmd))
                self.logger.error("Stdout: %s", result.stdout)
                self.logger.error("Stderr: %s", result.stderr)

                # Raise exception with comprehensive information
                raise subprocess.CalledProcessError(
                    result.returncode,
                    docker_compose_cmd,
                    output=result.stdout,
                    stderr=result.stderr,
                )

        self.logger.info("Docker Compose environment launched successfully.")
        self.notify_environment_setup_started()

        # Get Docker Compose logs
        with (
            open(os.path.join(log_dir, "docker-compose.log"), "w") as log_file,
            open(os.path.join(log_dir, "docker-compose.err.log"), "w") as log_file_err,
        ):

            docker_logs_cmd = [
                "docker",
                "compose",
                "-f",
                compose_file_path,
                "logs",
                "--no-color",
            ]

            result_exp = subprocess.run(
                docker_logs_cmd,
                capture_output=True,
                text=True,
                cwd=os.path.dirname(compose_file_path),
            )

            # Write logs
            log_file.write(result_exp.stdout)
            log_file_err.write(result_exp.stderr)

            # Check for failure in logs command (non-critical)
            if result_exp.returncode != 0:
                self.logger.warning(
                    "Docker Compose logs command failed with return code %d", result_exp.returncode
                )
                self.logger.warning("Command: %s", " ".join(docker_logs_cmd))
                self.logger.warning("Stderr: %s", result_exp.stderr)
                # Don't raise exception for logs failure as it's not critical

        self.logger.info("Docker Compose environment logs captured successfully.")
