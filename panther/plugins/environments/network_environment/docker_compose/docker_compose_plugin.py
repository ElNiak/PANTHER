import os
from pathlib import Path
import socket
import subprocess
import logging
from typing import Dict, Any
import yaml
from jinja2 import Environment, FileSystemLoader
from plugins.environments.network_environment.network_environment_interface import (
    INetworkEnvironment,
)
import traceback


class DockerComposeEnvironment(INetworkEnvironment):
    def __init__(
        self,
        config_path: str,
        output_dir: str,
        network_driver: str = "bridge",
        templates_dir: str = "plugins/environments/network_environment/docker_compose",
    ):
        self.logger = logging.getLogger("DockerComposeEnvironment")
        self.services_network_config_file_path = os.path.join(
            os.getcwd(),
            "plugins",
            "environments",
            "network_environment",
            "docker_compose",
            "docker-compose.generated.yml",
        )
        self.network_name = "quic_network_dynamic"
        self.network_driver = network_driver
        self.templates_dir = templates_dir
        self.output_dir = output_dir
        self.log_dirs = os.path.join(self.output_dir, "logs")
        self.rendered_docker_compose_path = os.path.join(
            self.output_dir, "docker-compose.yml"
        )
        self.compose_file_path = Path(self.services_network_config_file_path)
        self.services = {}
        self.deployment_commands = {}
        self.timeout = 60
        self.jinja_env = Environment(loader=FileSystemLoader(self.templates_dir))
        self.jinja_env.filters['realpath'] = lambda x: os.path.abspath(x)

    def build_images(self):
        """
        Builds Docker images for all implementations.
        """
        self.logger.info("Building Docker images for all implementations")
        self.logger.info("Docker images built successfully")
        raise NotImplementedError("Method not implemented - In another module FOR NOW")

    def is_port_free(self, port: int) -> bool:
        """
        Checks if a given port is free on the host.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("localhost", port)) != 0

    def find_free_port(
        self, start_port: int = 5000, end_port: int = 6000, assigned_ports: set = None
    ) -> int:
        """
        Finds a free port within the specified range.
        """
        for port in range(start_port, end_port):
            if self.is_port_free(port) and (
                assigned_ports is None or port not in assigned_ports
            ):
                return port
        raise RuntimeError(f"No free ports available in range {start_port}-{end_port}")

    def setup_environment(
        self, services: Dict[str, Dict[str, Any]], deployment_info: Dict[str, Dict[str, Any]], paths: Dict[str, str], timestamp: str
    ):
        """
        Sets up the Docker Compose environment by generating the docker-compose.yml file with deployment commands.

        :param services: Dictionary of services with their configurations.
        :param deployment_info: Dictionary containing commands and volumes for each service.
        :param paths: Dictionary containing various path configurations.
        :param timestamp: The timestamp string to include in log paths.
        """
        self.services = services
        self.deployment_info = deployment_info
        self.logger.debug(
            f"Setting up Docker Compose environment with services: {services} and deployment info: {deployment_info}"
        )
        self.generate_docker_compose(paths=paths, timestamp=timestamp)
        self.logger.info("Docker Compose environment setup complete")


    def deploy_services(self):
        self.logger.info("Deploying services")
        self.launch_docker_compose()

    def generate_docker_compose(self, paths: Dict[str, str], timestamp: str):
        """
        Generates the docker-compose.yml file using the provided services and deployment commands.

        :param paths: Dictionary containing various path configurations.
        :param timestamp: The timestamp string to include in log paths.
        """
        try:
            # Ensure the log directory for each service exists
            for service_name in self.services.keys():
                log_dir = os.path.join(self.log_dirs, service_name)
                if not os.path.exists(log_dir):
                    os.makedirs(log_dir)
                    self.logger.info(f"Created log directory: {log_dir}")
            
            template = self.jinja_env.get_template("docker-compose-template.j2")
            rendered = template.render(
                services=self.services,
                deployment_info=self.deployment_info,
                paths=paths,
                timestamp=timestamp,
                log_dir=self.log_dirs,
            )
            
            # Write the rendered content to docker-compose.generated.yml
            with open(self.compose_file_path, "w") as f:
                f.write(rendered)
                
            with open(self.rendered_docker_compose_path, "w") as f:
                f.write(rendered)
                
            self.logger.info(
                f"Docker Compose file generated at '{self.compose_file_path}'"
            )
        except Exception as e:
            self.logger.error(
                f"Failed to generate Docker Compose file: {e}\n{traceback.format_exc()}"
            )
            exit(1)

    def launch_docker_compose(self):
        """
        Launches the Docker Compose environment using the generated docker-compose.yml file.
        """
        try:
            with open(
                os.path.join(self.output_dir, "logs", "docker-compose.log"), "w"
            ) as log_file:
                with open(
                    os.path.join(self.output_dir, "logs", "docker-compose.err.log"), "w"
                ) as log_file_err:
                    result = subprocess.run(
                        [
                            "docker",
                            "compose",
                            "-f",
                            str(self.compose_file_path),
                            "up",
                            "-d"
                        ],
                        check=True,
                        # Now in docker build
                        env={ # TODO is it dangerous ?
                            "UID": str(os.getuid()),
                            "GID": str(os.getgid()),
                        },
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,  # Ensures that output is in string format
                    )
                    # Write both stdout and stderr to the log file
                    log_file.write(result.stdout)
                    log_file_err.write(result.stderr)
                self.logger.info("Docker Compose environment launched successfully.")
        except subprocess.CalledProcessError as e:
            self.logger.error(
                f"Failed to launch Docker Compose environment: {e.stderr}"
            )
            raise e

    def teardown_environment(self):
        """
        Tears down the Docker Compose environment by bringing down services.
        """
        self.logger.info("Tearing down Docker Compose environment")
        with open(
            os.path.join(self.output_dir, "logs", "docker-compose-teardown.log"), "w"
        ) as log_file:
            with open(
                os.path.join(self.output_dir, "logs", "docker-compose-teardown.err.log"), "w"
            ) as log_file_err:
                try:
                    if self.network_driver == "host":
                        # In host mode, stop containers individually
                        # Assumes service names are the container names
                        compose_dict = self.read_compose_file()
                        services = compose_dict.get("services", {})
                        for service_name in services.keys():
                            cmd = f"docker stop {service_name}"
                            self.logger.debug(f"Executing command: {cmd}")
                            subprocess.run(
                                cmd,
                                shell=True,
                                check=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                            )
                            cmd_rm = f"docker rm {service_name}"
                            self.logger.debug(f"Executing command: {cmd_rm}")
                            subprocess.run(
                                cmd_rm,
                                shell=True,
                                check=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                            )
                    else:
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
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,  # Ensures that output is in string format
                        )
                        # Write both stdout and stderr to the log file
                        log_file.write(result.stdout)
                        log_file_err.write(result.stderr)
                    self.logger.info("Docker Compose environment torn down successfully")
                except subprocess.CalledProcessError as e:
                    self.logger.error(
                        f"Failed to tear down Docker Compose environment: {e.stderr}"
                    )
                    raise e

    def read_compose_file(self) -> Dict[str, Any]:
        """
        Reads the generated docker-compose.yml file.
        """
        if not os.path.exists(self.services_network_config_file_path):
            self.logger.error(
                f"Docker Compose file '{self.services_network_config_file_path}' does not exist."
            )
            raise FileNotFoundError(
                f"Docker Compose file '{self.services_network_config_file_path}' does not exist."
            )

        with open(self.services_network_config_file_path, "r") as compose_file:
            return yaml.safe_load(compose_file)

    def __str__(self) -> str:
        return (
            super().__str__()
            + f" (network_driver={self.network_driver}, network_name={self.network_name})"
        )
