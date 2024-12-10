import os
from pathlib import Path
import socket
import subprocess
import logging
import traceback
from typing import Dict, Any, List, Optional
from jinja2 import Environment, FileSystemLoader
import yaml
from core.observer.event_manager import EventManager
from plugins.environments.execution_environment.execution_environment_interface import IExecutionEnvironment
from plugins.plugin_loader import PluginLoader
from plugins.environments.network_environment.network_environment_interface import (
    INetworkEnvironment,
)


class ShadowNsEnvironment(INetworkEnvironment):
    def __init__(
        self,
        output_dir: str,
        environment_settings: Dict[str, Any],
        env_type: str,
        env_sub_type: str,
        event_manager: EventManager,
    ):
        super().__init__(env_config_to_test, output_dir, env_type, env_sub_type, event_manager)

        self.docker_version = "v1"
        self.docker_name = "shadow_"
        
        self.services_network_config_file_path = Path(os.path.join(
            os.getcwd(),
            "plugins",
            "environments",
            type,
            env_sub_type,
            f"{env_sub_type}.generated.yml",
        ))
        self.rendered_services_network_config_file_path = Path(os.path.join(
            self.output_dir, f"{env_sub_type}.yml"
        ))
        
        self.services_network_docker_file_path = Path(os.path.join(
            os.getcwd(),
            "plugins",
            "environments",
            env_type,
            env_sub_type,
            "Dockerfile.generated",
        ))
        self.rendered_services_network_docker_file_path = Path(os.path.join(
            self.output_dir, "Dockerfile.experience"
        ))

    def __str__(self):
        attributes = {
            "config_path": self.config_path,
            "output_dir": self.output_dir,
            "templates_dir": self.templates_dir,
            "services_network_config_file_path": self.services_network_config_file_path,
            "network_name": self.network_name,
            "log_dirs": self.log_dirs,
            "rendered_shadow_conf_path": self.rendered_services_network_config_file_path,
            "shadow_conf_path": str(self.services_network_config_file_path),
            "services": self.services,
            "deployment_commands": self.deployment_commands,
            "timeout": self.timeout,
        }
        return f"ShadowNsEnvironment({attributes})"

    def __repr__(self):
        attributes = {
            "config_path": self.config_path,
            "output_dir": self.output_dir,
            "templates_dir": self.templates_dir,
            "services_network_config_file_path": self.services_network_config_file_path,
            "network_name": self.network_name,
            "log_dirs": self.log_dirs,
            "rendered_shadow_conf_path": self.rendered_services_network_config_file_path,
            "shadow_conf_path": str(self.services_network_config_file_path),
            "services": self.services,
            "deployment_commands": self.deployment_commands,
            "timeout": self.timeout,
        }
        return f"ShadowNsEnvironment({attributes})"

    def parse_gml(self, gml_file: str):
        """
        Parses the GML file and returns the graph.
        Future: Try to make that format general ?
        """
        raise NotImplementedError
    
    def prepare_environment(self):
        """
        Prepare the service manager for use.
        """
        self.logger.info("Preparing Shadow NS service manager...")
        self.plugin_loader.build_docker_image("shadow_ns", self.docker_version)
        
    def setup_environment(
        self,
        services: Dict[str, Dict[str, Any]],
        deployment_info: Dict[str, Dict[str, Any]],
        paths: Dict[str, str],
        timestamp: str,
        plugin_loader: PluginLoader,
        execution_environment: List[IExecutionEnvironment],
    ):
        """
        Sets up the Shadow NS environment by generating the shadow.yml file with deployment commands.

        :param services: Dictionary of services with their configurations.
        :param deployment_info: Dictionary containing commands and volumes for each service.
        :param paths: Dictionary containing various path configurations.
        :param timestamp: The timestamp string to include in log paths.
        """
        self.services = services
        self.deployment_info = deployment_info
        self.execution_environments = execution_environment
        self.plugin_loader = plugin_loader

        self.logger.debug(f"Setting up Shadow NS environment with:\n- services: {services}\n- deployment info: {deployment_info}\n- environment settings: {self.environment_settings}")
        self.prepare_environment()
        self.generate_environment_services(paths=paths, timestamp=timestamp)
        self.logger.info("Shadow NS environment setup complete")


    def deploy_services(self):
        self.logger.info("Deploying services")
        # self.prepare_tester() # TODO
        self.launch_environment_services()

    def retrieve_binaries(self):
        self.logger.info("Retrieving binaries")
        raise NotImplementedError("Method not implemented - In another module FOR NOW")

    def generate_environment_services(self, paths: Dict[str, str], timestamp: str):
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
            for service_name, service in self.services.items():
                log_dir = os.path.join(self.log_dirs, service_name)
                if not os.path.exists(log_dir):
                    os.makedirs(log_dir)
                    self.logger.info(f"Created log directory: {log_dir}")
                self.docker_name = self.docker_name + service_name + "_"
                additional_command = ""
                if "ivy" in service_name:
                    # TODO make it more generic
                    self.deployment_info[service_name]["args"] = self.deployment_info[
                        service_name
                    ]["args"].replace("eth0", "lo")
                    if service["role"] == "client":
                        self.deployment_info[service_name]["args"] = (
                            self.deployment_info[service_name]["args"].replace(
                                "$$TARGET_IP_HEX", "184549377"
                            )
                        )
                        self.deployment_info[service_name]["args"] = (
                            self.deployment_info[service_name]["args"].replace(
                                "$$IVY_IP_HEX", "184549378"
                            )
                        )
                    else:
                        self.deployment_info[service_name]["args"] = (
                            self.deployment_info[service_name]["args"].replace(
                                "$$TARGET_IP_HEX", "184549378"
                            )
                        )
                        self.deployment_info[service_name]["args"] = (
                            self.deployment_info[service_name]["args"].replace(
                                "$$IVY_IP_HEX", "184549377"
                            )
                        )
                else:
                    for other_service_name in self.services.keys():
                        if other_service_name != service_name:
                            self.deployment_info[other_service_name][
                                "args"
                            ] = self.deployment_info[other_service_name][
                                "args"
                            ].replace(
                                service_name, service_name.replace("_", ".")
                            )  # .replace("-e eth0", "")
                            # self.deployment_info[other_service_name]["args"] = self.deployment_info[other_service_name]["args"].replace("/opt/certs", "/opt/"+ service_name + "/certs")

            for service_name, service in self.services.items():
                if "environment" in self.deployment_info[service_name]:
                    self.deployment_info[service_name]["environment"] = (
                        self.resolve_environment_variables(
                            self.deployment_info[service_name]["environment"]
                        )
                    )
                    self.deployment_info[service_name]["environment"][
                        "SHADOW_TEST"
                    ] = "1"

            self.logger.debug(
                f"Resolved environment deployment_info: {self.deployment_info}"
            )
            template = self.jinja_env.get_template("shadow-template.jinja")
            rendered = template.render(
                services=self.services,
                deployment_info=self.deployment_info,
                paths=paths,
                timestamp=timestamp,
                log_dir=self.log_dirs,
                experiment_name=self.output_dir.split("/")[-1],
                environment_settings=self.environment_settings,  # TODO
            )

            # Write the rendered content to shadow.generated.yml
            with open(self.services_network_config_file_path, "w") as f:
                f.write(rendered)

            with open(self.rendered_services_network_config_file_path, "w") as f:
                f.write(rendered)

            self.logger.info(f"Shadow NS file generated at '{self.services_network_config_file_path}'")

            self.logger.info("Shadow NS based environment manager prepared.")
            # Define docker container for experience
            template = self.jinja_env.get_template("Dockerfile.experience.jinja")
            rendered = template.render(
                services=self.services,
                paths=paths,
                timestamp=timestamp,
                deployment_info=self.deployment_info,
                shadow_ns_config_file=self.services_network_config_file_path.name,
                log_dir=self.log_dirs,
                additional_command=additional_command,
                experiment_name=self.output_dir.split("/")[-1],
            )

            # Write the rendered content to shadow.generated.yml
            with open(self.services_network_docker_file_path, "w") as f:
                f.write(rendered)

            with open(self.rendered_services_network_docker_file_path, "w") as f:
                f.write(rendered)

            self.logger.info(f"Shadow NS file Dockerfile generated at '{self.services_network_docker_file_path}'")

            self.docker_name = self.plugin_loader.build_docker_image_from_path(
                self.services_network_docker_file_path, self.docker_name, self.docker_version
            )
            self.docker_name = self.docker_name.split(":")[0]

        except Exception as e:
            self.logger.error(
                f"Failed to generate Shadow NS file: {e}\n{traceback.format_exc()}"
            )
            exit(1)

    def launch_environment_services(self):
        """
        Launches the Shadow NS environment using the generated shadow.yml file.
        """
        # TODO use docker_builder module
        try:
            with open(
                os.path.join(self.output_dir, "logs", "shadow.log"), "w"
            ) as log_file:
                with open(
                    os.path.join(self.output_dir, "logs", "shadow.err.log"), "w"
                ) as log_file_err:
                    volumes = []
                    volumes.append("-v")
                    volumes.append(
                        f"{os.path.abspath(self.log_dirs+'/shadow')}:/app/logs/"
                    )
                    for service_name, service in self.services.items():
                        for volume in self.deployment_info[service_name]["volumes"]:
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
                    self.logger.debug(f"Executing command: {' '.join(command)}")

                    result = subprocess.run(
                        command,
                        check=True,
                        # Now in docker build
                        # env={ # TODO is it dangerous ?
                        #     "UID": str(os.getuid()),
                        #     "GID": str(os.getgid()),
                        # },
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,  # Ensures that output is in string format
                    )
                    # Write both stdout and stderr to the log file
                    log_file.write(result.stdout)
                    log_file_err.write(result.stderr)
                    # TODO shadow.data
                self.logger.info("Shadow NS environment launched successfully.")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to launch Shadow NS environment: {e.stderr}")
            with open(
                os.path.join(self.output_dir, "logs", "shadow.log"), "w"
            ) as log_file:
                with open(
                    os.path.join(self.output_dir, "logs", "shadow.err.log"), "w"
                ) as log_file_err:
                    log_file.write(e.stdout)
                    log_file_err.write(e.stderr)
            # raise e

    def teardown_environment(self):
        """
        Tears down the Shadow NS environment by bringing down services.
        """
        # TODO: add a way to retrieve the logs, results, binary
        self.logger.info("Tearing down Shadow NS environment")
        with open(
            os.path.join(self.output_dir, "logs", "shadow-teardown.log"), "w"
        ) as log_file:
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
                    self.logger.debug(
                        f"Executing remove image command: {remove_image_command}"
                    )
                    result = subprocess.run(
                        remove_image_command,
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                    )
                    self.logger.debug(f"Executing command: {remove_image_command}")

                    log_file.write(result.stdout)
                    log_file_err.write(result.stderr)
                    self.logger.info("Shadow NS environment torn down successfully")
                except subprocess.CalledProcessError as e:
                    self.logger.error(
                        f"Failed to tear down Shadow NS environment: {e.stderr}"
                    )
                    raise e

    def read_shadow_file(self) -> Dict[str, Any]:
        """
        Reads the generated shadow.yml file.
        """
        if not os.path.exists(self.services_network_config_file_path):
            self.logger.error(
                f"Shadow NS file '{self.services_network_config_file_path}' does not exist."
            )
            raise FileNotFoundError(
                f"Shadow NS file '{self.services_network_config_file_path}' does not exist."
            )

        with open(self.services_network_config_file_path, "r") as compose_file:
            return yaml.safe_load(compose_file)
