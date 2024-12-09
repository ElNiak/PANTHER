import os
from pathlib import Path
import socket
import subprocess
import logging
from typing import Dict, Any, List
import yaml
from jinja2 import Environment, FileSystemLoader
from core.observer.event_manager import EventManager
from plugins.environments.execution_environment.execution_environment_interface import IExecutionEnvironment
from plugins.plugin_loader import PluginLoader
from plugins.environments.network_environment.network_environment_interface import (
    INetworkEnvironment,
)
import traceback
from core.observer.event import Event


class DockerComposeEnvironment(INetworkEnvironment):
    def __init__(
        self,
        output_dir: str,
        environment_settings: Dict[str,Any],
        env_type: str,
        env_sub_type: str,
        event_manager: EventManager,
    ):
        super().__init__(output_dir, environment_settings, env_type, env_sub_type, event_manager)
        self.services_network_config_file_path = Path(os.path.join(
            os.getcwd(),
            "plugins",
            "environments",
            env_type,
            env_sub_type,
            f"{env_sub_type}.generated.yml",
        ))
        self.rendered_services_network_config_file_path = Path(os.path.join(
            self.output_dir, f"{env_sub_type}.yml"
        ))
        
    def __str__(self):
        attributes = {
            "config_path": self.config_path,
            "output_dir": self.output_dir,
            "templates_dir": self.templates_dir,
            "services_network_config_file_path": self.services_network_config_file_path,
            "network_name": self.network_name,
            "log_dirs": self.log_dirs,
            "rendered_services_network_config_file_path": self.rendered_services_network_config_file_path,
            "rendered_services_network_config_file_path": str(self.rendered_services_network_config_file_path),
            "services": self.services,
            "deployment_commands": self.deployment_commands,
            "timeout": self.timeout,
        }
        return f"DockerComposeEnvironment({attributes})"
    
    def __repr__(self):
        attributes = {
            "config_path": self.config_path,
            "output_dir": self.output_dir,
            "templates_dir": self.templates_dir,
            "services_network_config_file_path": self.services_network_config_file_path,
            "network_name": self.network_name,
            "log_dirs": self.log_dirs,
            "rendered_services_network_config_file_path": self.rendered_services_network_config_file_path,
            "rendered_services_network_config_file_path": str(self.rendered_services_network_config_file_path),
            "services": self.services,
            "deployment_commands": self.deployment_commands,
            "timeout": self.timeout,
        }
        return f"DockerComposeEnvironment({attributes})"
    
    def prepare_environment(self):
        """
        Builds Docker images for all implementations.
        """
        pass

    def setup_environment(
        self, services: Dict[str, Dict[str, Any]], deployment_info: Dict[str, Dict[str, Any]], 
        paths: Dict[str, str], timestamp: str, plugin_loader: PluginLoader, execution_environment: List[IExecutionEnvironment], 
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
        self.execution_environment = execution_environment
        self.plugin_loader = plugin_loader
        self.logger.debug( f"Setting up Docker Compose environment with services: {services} and deployment info: {deployment_info}")
        self.generate_environment_services(paths=paths, timestamp=timestamp)
        self.logger.info("Docker Compose environment setup complete")
    
    
    def deploy_services(self):
        self.logger.info("Deploying services")
        self.launch_environment_services()
        

    def generate_environment_services(self, paths: Dict[str, str], timestamp: str):
        """
        Generates the docker-compose.yml file using the provided services and deployment commands.

        :param paths: Dictionary containing various path configurations.
        :param timestamp: The timestamp string to include in log paths.
        """
        # TODO add timeout in the test config
        try:
            # Ensure the log directory for each service exists
            for service_name , service in self.services.items():
                log_dir = os.path.join(self.log_dirs, service_name)
                if not os.path.exists(log_dir):
                    os.makedirs(log_dir)
                    self.logger.info(f"Created log directory: {log_dir}")
                
                additional_command = ""
                if "ivy" in service_name:
                    # update other service so they wait for ivy to be ready
                    self.logger.debug(f"Adding wait for Ivy testers to be ready for {service_name}")
                    for other_service_name, other_service in self.services.items():
                        if other_service_name != service_name:
                            additional_command = f"""
                            while [ ! -f /app/sync_logs/ivy_ready ]; do
                                echo "Waiting for Ivy testers to be ready..." >> /app/logs/tester_ready;
                                sleep 2;
                            done;
                            echo "Ivy testers is ready, starting {other_service_name}..." >> /app/logs/tester_ready;   
                            """.strip()
                            self.deployment_info[other_service_name]["volumes"].append("shared_logs:/app/sync_logs")
            
            
            for service_name, service in self.services.items():
                if "environment" in self.deployment_info[service_name]:
                    self.deployment_info[service_name]["environment"] = self.resolve_environment_variables(self.deployment_info[service_name]["environment"])
            
            template = self.jinja_env.get_template("docker-compose-template.jinja")
            rendered = template.render(
                services=self.services,
                deployment_info=self.deployment_info,
                paths=paths,
                timestamp=timestamp,
                log_dir=self.log_dirs,
                additional_command=additional_command,
                experiment_name=self.output_dir.split("/")[-1],
                environment_settings=self.environment_settings,
            )
            
            # Write the rendered content to docker-compose.generated.yml
            with open(self.services_network_config_file_path, "w") as f:
                f.write(rendered)
                
            with open(self.rendered_services_network_config_file_path, "w") as f:
                f.write(rendered)
                
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
                    os.path.join(self.output_dir, "logs", "docker-compose-up.err.log"), "w"
                ) as log_file_err:
                    result = subprocess.run(
                        [
                            "docker",
                            "compose",
                            "-f",
                            str(self.rendered_services_network_config_file_path),
                            "up",
                            "-d", # Detached mode: Run containers in the background
                            "-V", # Recreate anonymous volumes instead of retrieving data from the previous containers
                        ],
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
                    log_file.write(result_exp.stdout)
                    log_file_err.write(result_exp.stderr)
                self.logger.info("Docker Compose environment logs successfully.")
                # self.event_manager.notify(Event("experiment_finished_early", {}))
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
                    os.path.join(self.output_dir, "logs", "docker-compose-ps.err.log"), "w"
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
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,  # Ensures that output is in string format
                    )
                    # Write both stdout and stderr to the log file
                    log_file.write(result.stdout)
                    log_file_err.write(result.stderr)
                    # NAME      IMAGE     COMMAND   SERVICE   CREATED   STATUS    PORTS
                    #
                    self.logger.debug(f"docker-compose ps: {result.stdout}")
                    if len(result.stdout.split("\n")) == 2:
                        self.logger.info("Docker Compose environment monitored successfully - experiment_finished_early")
                        self.event_manager.notify(Event(name="experiment_finished_early", data={}))
                    
                self.logger.info("Docker Compose environment monitored successfully.")
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
                os.path.join(self.output_dir, "logs", "docker-compose-teardown.err.log"), "w"
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
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,  # Ensures that output is in string format
                    )
                    # Write both stdout and stderr to the log file
                    log_file.write(result.stdout)
                    log_file_err.write(result.stderr)
                    os.system(f"docker volume prune -a -f")
                    self.logger.info("Docker Compose environment torn down successfully")
                except subprocess.CalledProcessError as e:
                    self.logger.error(
                        f"Failed to tear down Docker Compose environment: {e.stderr}"
                    )
                    raise e

