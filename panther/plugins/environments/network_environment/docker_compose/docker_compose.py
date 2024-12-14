import os
from pathlib import Path
import subprocess
from panther.core.observer.event_manager import EventManager
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
import traceback
from panther.core.observer.event import Event


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
        setup_environment(services_managers, test_config, global_config, timestamp, plugin_loader, execution_environment):
        prepare_environment():
            Prepares the environment (currently not implemented).
        deploy_services():
            Deploys the services defined in the Docker Compose environment.
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
        super().__init__(
            env_config_to_test, output_dir, env_type, env_sub_type, event_manager
        )
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

    def __str__(self):
        return f"DockerComposeEnvironment({self.__dict__})"

    def __repr__(self):
        return f"DockerComposeEnvironment({self.__dict__})"

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
        """
        self.update_environment(
            execution_environment,
            global_config,
            plugin_loader,
            services_managers,
            test_config,
        )
        self.generate_environment_services(
            paths=self.global_config.paths, timestamp=timestamp
        )
        self.logger.info("Docker Compose environment setup complete")

    def prepare_environment(self):
        pass

    def deploy_services(self):
        self.logger.info("Deploying services")
        self.launch_environment_services()

    def generate_environment_services(self, paths: dict[str, str], timestamp: str):
        """
        Generates the docker-compose.yml file using the provided services and deployment commands.

        :param paths: Dictionary containing various path configurations.
        :param timestamp: The timestamp string to include in log paths.
        """
        try:
            # Ensure the log directory for each service exists
            self.setup_execution_plugins(timestamp)

            for service in self.services_managers:
                self.create_log_dir(service)
                self.logger.debug(
                    f"Generating Docker Compose file for {service.service_name}"
                )

                if "ivy" in service.service_name:
                    self.logger.debug(
                        f"Adding wait for Ivy testers to be ready for {service.service_name}"
                    )
                    for other_service in self.services_managers:
                        if other_service.service_name != service.service_name:
                            other_service.volumes.append("shared_logs:/app/sync_logs")
                            other_service.run_cmd[
                                "post_compile_cmds"
                            ] = other_service.run_cmd["post_compile_cmds"] + [
                                "while [ ! -f /app/sync_logs/ivy_ready.log ]; do",
                                '\techo "Waiting for Ivy testers to be ready..." >> /app/logs/tester_ready.log;',
                                "\tsleep 2;",
                                "done;",
                                'echo "Ivy testers is ready, starting '
                                + other_service.service_name
                                + '..." >> /app/logs/tester_ready.log;',
                            ]

            for service in self.services_managers:
                service.run_cmd["post_compile_cmds"] = service.run_cmd[
                    "post_compile_cmds"
                ] + [
                    "(touch /app/logs/"
                    + service.service_name
                    + ".pcap; tshark -a duration:"
                    + str(service.service_config_to_test.timeout)
                    + " -i any -w /app/logs/"
                    + service.service_name
                    + ".pcap;) & "
                ]

            for service in self.services_managers:
                service.environments = self.resolve_environment_variables(
                    service.environments
                )
                self.logger.debug(
                    f"Service {service.service_name} environment: {service.environments}"
                )

            self.generate_from_template(
                "docker-compose-template.jinja",
                paths,
                timestamp,
                self.rendered_services_network_config_file_path,
                self.services_network_config_file_path,
            )

            self.logger.info(
                f"Docker Compose file generated at '{self.rendered_services_network_config_file_path}'"
            )
        except Exception as e:
            self.logger.error(
                f"Failed to generate Docker Compose file: {e}\n{traceback.format_exc()}"
            )
            exit(1)

    def launch_environment_services(self):
        """
        Launches the Docker Compose environment using the generated docker-compose.yml file.
        """
        try:
            with open(
                os.path.join(self.output_dir, "logs", "docker-compose-up.log"), "w"
            ) as log_file:
                with open(
                    os.path.join(self.output_dir, "logs", "docker-compose-up.err.log"),
                    "w",
                ) as log_file_err:
                    result = subprocess.run(
                        [
                            "docker",
                            "compose",
                            "-f",
                            str(self.rendered_services_network_config_file_path),
                            "up",
                            "-d",  # Detached mode: Run containers in the background
                            "-V",  # Recreate anonymous volumes instead of retrieving data from the previous containers
                        ],
                        check=True,
                        capture_output=True,
                        text=True,  # Ensures that output is in string format
                    )
                    # Write both stdout and stderr to the log file
                    log_file.write(result.stdout)
                    log_file_err.write(result.stderr)
                self.logger.info("Docker Compose environment launched successfully.")
            with open(
                os.path.join(self.output_dir, "logs", "docker-compose.log"), "w"
            ) as log_file:
                with open(
                    os.path.join(self.output_dir, "logs", "docker-compose.err.log"), "w"
                ) as log_file_err:
                    result_exp = subprocess.run(
                        [
                            "docker",
                            "compose",
                            "-f",
                            str(self.rendered_services_network_config_file_path),
                            "logs",
                            "--no-color",
                        ],
                        check=True,
                        capture_output=True,
                        text=True,  # Ensures that output is in string format
                    )
                    # Write both stdout and stderr to the log file
                    log_file.write(result_exp.stdout)
                    log_file_err.write(result_exp.stderr)
                self.logger.info("Docker Compose environment logs successfully.")
        except subprocess.CalledProcessError as e:
            self.logger.error(
                f"Failed to launch Docker Compose environment: {e.stderr}"
            )
            raise e

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
                        f"docker-compose ps: {result.stdout} - {result.stderr} - {len(self.services_managers)}  - {len(std_split)}"
                    )
                    if len(std_split) < len(self.services_managers) * 2:
                        self.logger.debug(
                            "Docker Compose environment monitored successfully - Experiment finished earlier"
                        )
                        self.event_manager.notify(
                            Event(name="experiment_finished_early", data={})
                        )

                self.logger.debug("Docker Compose environment monitored successfully.")
        except subprocess.CalledProcessError as e:
            self.logger.error(
                f"Failed to monitor Docker Compose environment: {e.stderr}"
            )
            raise e

    def teardown_environment(self):
        """
        Tears down the Docker Compose environment by bringing down services.
        """
        # TODO: add a way to retrieve the logs, results, binary
        self.logger.info("Tearing down Docker Compose environment")
        with open(
            os.path.join(self.output_dir, "logs", "docker-compose-teardown.log"), "w"
        ) as log_file:
            with open(
                os.path.join(
                    self.output_dir, "logs", "docker-compose-teardown.err.log"
                ),
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
                    self.logger.info(
                        "Docker Compose environment torn down successfully"
                    )
                except subprocess.CalledProcessError as e:
                    self.logger.error(
                        f"Failed to tear down Docker Compose environment: {e.stderr}"
                    )
                    raise e
