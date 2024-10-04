import os
from pathlib import Path
import socket
import subprocess
import logging
from typing import Dict, Any
import yaml
from jinja2 import Environment, FileSystemLoader
from core.interfaces.environments.network_environment_interface import (
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
        self.rendered_docker_compose_path = os.path.join(
            self.output_dir, "logs", "docker-compose.yml"
        )
        self.compose_file_path = Path(self.services_network_config_file_path)
        self.services = {}
        self.deployment_commands = {}
        self.jinja_env = Environment(loader=FileSystemLoader(self.templates_dir))

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

    def configure_network(self, services: Dict[str, Dict[str, Any]]):
        """
        Generates a docker-compose.yml file dynamically based on the provided services.
        :param services: A dictionary mapping service names to their configurations.
        """
        self.logger.info("Generating dynamic docker-compose.yml")
        compose_dict = {
            "version": "3.8",
            "services": {},
            "networks": {self.network_name: {"driver": self.network_driver}},
        }

        assigned_ports = set()

        for service_name, config in services.items():
            image = config.get("image")
            ports = config.get("ports", [])
            depends_on = config.get("depends_on", [])
            environment_vars = config.get("environment", {})

            service_type = service_name.split("_")[
                -1
            ].upper()  # Assuming naming convention like 'picoquic_server_rfc9000_panther'
            log_path = config.get("log_path", "/app/logs/service.log")  # Get log path

            # Adjust port assignments to avoid conflicts
            adjusted_ports = []
            for port_mapping in ports:
                try:
                    host_port, container_port = map(int, port_mapping.split(":"))
                except ValueError:
                    self.logger.error(
                        f"Invalid port mapping '{port_mapping}' for service '{service_name}'. Skipping."
                    )
                    continue

                if host_port in assigned_ports or not self.is_port_free(host_port):
                    self.logger.warning(
                        f"Host port {host_port} is in use. Finding an alternative port."
                    )
                    try:
                        new_host_port = self.find_free_port(
                            assigned_ports=assigned_ports
                        )
                        self.logger.info(
                            f"Assigning new host port {new_host_port} for container port {container_port}."
                        )
                        adjusted_ports.append(f"{new_host_port}:{container_port}")
                        assigned_ports.add(new_host_port)
                    except RuntimeError as e:
                        self.logger.error(
                            f"Failed to assign a free port for {service_name}: {e}"
                        )
                        raise e
                else:
                    adjusted_ports.append(port_mapping)
                    assigned_ports.add(host_port)

            service_def = {
                "image": image,
                "container_name": service_name,
                "ports": (
                    adjusted_ports if self.network_driver != "host" else []
                ),  # Ports are not needed in host mode
                "networks": [self.network_name],
                "volumes": [
                    f"{Path(self.services_network_config_file_path).parent}/container_logs/{service_name}:/app/logs"
                ],
                "logging": {
                    "driver": "json-file",
                    "options": {
                        "max-size": "10m",
                        "max-file": "3",
                        "path": f"{Path(self.services_network_config_file_path).parent}/logs/{service_name}.log",
                    },
                },
                "restart": "always",
                "command": compose_command,  # Set the command directly
            }

            if depends_on:
                service_def["depends_on"] = depends_on

            if environment_vars:
                service_def["environment"] = environment_vars

            # Add health checks if specified
            if "healthcheck" in config:
                service_def["healthcheck"] = config["healthcheck"]

            compose_dict["services"][service_name] = service_def

        # Validate unique host ports
        all_host_ports = []
        for service in compose_dict["services"].values():
            for port in service.get("ports", []):
                host_port = int(port.split(":")[0])
                all_host_ports.append(host_port)
        if len(all_host_ports) != len(set(all_host_ports)):
            self.logger.error(
                "Duplicate host ports detected in the Docker Compose configuration."
            )
            raise ValueError(
                "Duplicate host ports detected in the Docker Compose configuration."
            )

        with open(self.services_network_config_file_path, "w") as compose_file:
            self.logger.debug(
                f"Writing Docker Compose file to '{self.services_network_config_file_path}' with contents: {compose_dict}"
            )
            yaml.safe_dump(compose_dict, compose_file, default_flow_style=False)

        self.logger.info(
            f"Docker Compose file generated at '{self.services_network_config_file_path}'"
        )

    # def setup_environment(self, services: Dict[str, Dict[str, Any]]):
    #     """
    #     Sets up the Docker Compose environment by generating the compose file and bringing up services.
    #     :param services: A dictionary mapping service names to their configurations.
    #     """
    #     try:
    #         self.configure_network(services)
    #     except Exception as e:
    #         self.logger.error(f"Failed to generate Docker Compose file: {e}")
    #         raise e

    #     self.logger.info("Starting Docker Compose services")
    #     try:
    #         if self.network_driver == "host":
    #             # In host mode, no need to use 'docker-compose up'
    #             # Instead, run each container with --network host
    #             for service_name, config in services.items():
    #                 image = config.get('image')
    #                 environment_vars = config.get('environment', {})
    #                 env_str = ' '.join([f"-e {key}='{value}'" for key, value in environment_vars.items()])
    #                 cmd = f"docker run -d --name {service_name} --network host {env_str} {image}"
    #                 self.logger.debug(f"Executing command: {cmd}")
    #                 subprocess.run(
    #                     cmd,
    #                     shell=True,
    #                     check=True,
    #                     stdout=subprocess.PIPE,
    #                     stderr=subprocess.PIPE
    #                 )
    #         else:
    #             # For other network drivers, use docker-compose
    #             subprocess.run(
    #                 ["docker", "compose", "-f", self.services_network_config_file_path, "up", "-d"],
    #                 check=True,
    #                 stdout=subprocess.PIPE,
    #                 stderr=subprocess.PIPE
    #             )
    #         self.logger.info("Docker Compose services started successfully")
    #     except subprocess.CalledProcessError as e:
    #         self.logger.error(f"Failed to start Docker Compose services: {e.stderr.decode()}")
    #         subprocess.run(
    #                 ["docker", "compose", "-f", self.services_network_config_file_path, "down"],
    #                 check=True,
    #                 stdout=subprocess.PIPE,
    #                 stderr=subprocess.PIPE
    #         )
    #         raise e

    def setup_environment(
        self, services: Dict[str, Dict[str, Any]], deployment_commands: Dict[str, str]
    ):
        """
        Sets up the Docker Compose environment by generating the docker-compose.yml file with deployment commands.

        :param services: Dictionary of services with their configurations.
        :param deployment_commands: Dictionary of deployment commands generated by service managers.
        """
        self.services = services
        self.deployment_commands = deployment_commands
        self.logger.debug(
            f"Setting up Docker Compose environment with services: {services} with commands {deployment_commands}"
        )
        self.generate_docker_compose()
        self.logger.info("Docker Compose environment setup complete")

    def deploy_services(self):
        self.logger.info("Deploying services")
        self.launch_docker_compose()

    def generate_docker_compose(self):
        """
        Generates the docker-compose.yml file using the provided services and deployment commands.
        """
        try:
            template = self.jinja_env.get_template("docker-compose-template.j2")
            rendered = template.render(
                services=self.services,
                deployment_commands=self.deployment_commands,
                output_dir=self.output_dir,
            )
            with open(self.compose_file_path, "w") as f:
                f.write(rendered)
            self.logger.info(
                f"Docker Compose file generated at '{self.compose_file_path}'"
            )
        except Exception as e:
            self.logger.error(
                f"Failed to generate Docker Compose file: {e}\n{traceback.format_exc()}"
            )

    def launch_docker_compose(self):
        """
        Launches the Docker Compose environment using the generated docker-compose.yml file.
        """
        try:
            with open(
                os.path.join(self.output_dir, "logs", "docker-compose.log"), "w"
            ) as log_file:
                subprocess.run(
                    [
                        "docker",
                        "compose",
                        "-f",
                        str(self.compose_file_path),
                        "up",
                        "-d",
                    ],
                    check=True,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                )
                self.logger.info("Docker Compose environment launched successfully.")
        except subprocess.CalledProcessError as e:
            self.logger.error(
                f"Failed to launch Docker Compose environment: {e.stderr.decode()}"
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
                    subprocess.run(
                        [
                            "docker",
                            "compose",
                            "-f",
                            self.services_network_config_file_path,
                            "down",
                        ],
                        check=True,
                        stdout=log_file,
                        stderr=subprocess.STDOUT,
                    )
                self.logger.info("Docker Compose environment torn down successfully")
            except subprocess.CalledProcessError as e:
                self.logger.error(
                    f"Failed to tear down Docker Compose environment: {e.stderr.decode()}"
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
