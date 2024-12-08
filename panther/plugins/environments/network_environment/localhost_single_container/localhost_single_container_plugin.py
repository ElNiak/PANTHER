import os
from pathlib import Path
import socket
import subprocess
import logging
import traceback
from typing import Dict, Any, List, Optional
from jinja2 import Environment, FileSystemLoader
import yaml
from panther.plugins.environments.execution_environment.execution_environment_interface import IExecutionEnvironment
from plugins.plugin_loader import PluginLoader
from plugins.environments.network_environment.network_environment_interface import INetworkEnvironment

class LocalhostSingleContainerEnvironment(INetworkEnvironment):
    def __init__(
        self,
        config_path: str,
        output_dir: str,
        environment_settings: Dict[str,Any],
        type: str,
        sub_type: str,
    ):
        super().__init__(config_path, output_dir, environment_settings, type, sub_type)
        
        self.docker_version = "v1"
        self.environment_settings = environment_settings
        self.docker_name = "localhost_"
        
        self.services_network_config_file_path = Path(os.path.join(
            os.getcwd(),
            "plugins",
            "environments",
            type,
            sub_type,
            "run.generated.sh",
        ))
        self.rendered_services_network_config_file_path = Path(os.path.join(
            self.output_dir, f"run.sh"
        ))
        
        self.services_network_docker_file_path = Path(os.path.join(
            os.getcwd(),
            "plugins",
            "environments",
            type,
            sub_type,
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
            "rendered_services_network_config_file_path": self.rendered_services_network_config_file_path,
            "services_network_config_file_path": str(self.services_network_config_file_path),
            "services": self.services,
            "deployment_commands": self.deployment_commands,
            "timeout": self.timeout,
        }
        return f"LocalhostSingleContainerEnvironment({attributes})"
    
    def __repr__(self):
        attributes = {
            "config_path": self.config_path,
            "output_dir": self.output_dir,
            "templates_dir": self.templates_dir,
            "services_network_config_file_path": self.services_network_config_file_path,
            "network_name": self.network_name,
            "log_dirs": self.log_dirs,
            "rendered_services_network_config_file_path": self.rendered_services_network_config_file_path,
            "services_network_config_file_path": str(self.services_network_config_file_path),
            "services": self.services,
            "deployment_commands": self.deployment_commands,
            "timeout": self.timeout,
        }
        return f"LocalhostSingleContainerEnvironment({attributes})"
    
    def prepare_environment(self):
        """
        Prepare the service manager for use.
        """
        self.logger.info("Preparing Localhost service manager...")
        # Additional setup can be implemented here
        self.plugin_loader.build_docker_image("localhost_single_container", self.docker_version)
        
    
    def setup_environment(
        self, services: Dict[str, Dict[str, Any]], deployment_info: Dict[str, Dict[str, Any]], 
        paths: Dict[str, str], timestamp: str, plugin_loader: PluginLoader, execution_environment: List[IExecutionEnvironment]
    ):
        """
        Sets up the Localhost environment by generating the run.sh file with deployment commands.

        :param services: Dictionary of services with their configurations.
        :param deployment_info: Dictionary containing commands and volumes for each service.
        :param paths: Dictionary containing various path configurations.
        :param timestamp: The timestamp string to include in log paths.
        """
        self.services             = services
        self.deployment_info      = deployment_info
        self.plugin_loader        = plugin_loader
        self.execution_environment = execution_environment
        
        self.logger.debug(
            f"Setting up Localhost environment with:\n- services: {services}\n- deployment info: {deployment_info}\n- environment settings: {self.environment_settings}"
        )
        self.prepare_environment()
        self.generate_environment_services(paths=paths, timestamp=timestamp)
        self.logger.info("Localhost environment setup complete")
    
    

    def deploy_services(self):
        self.logger.info("Deploying services")
        # self.prepare_tester() # TODO
        self.launch_environment_services()
        

    def generate_environment_services(self, paths: Dict[str, str], timestamp: str):
        """
        Generates the run.sh file using the provided services and deployment commands.

        :param paths: Dictionary containing various path configurations.
        :param timestamp: The timestamp string to include in log paths.
        """
        # TODO add timeout in the test config
        # TODO check that the implementaion is compatible with localhost (in config file)
        # TODo moodify the localhost template to add the timeout also add folder for each service to be added in the multi stage
        try:
            # Ensure the log directory for each service exists
            for service_name, service in self.services.items():
                log_dir = os.path.join(self.log_dirs, service_name)
                if not os.path.exists(log_dir):
                    os.makedirs(log_dir)
                    self.logger.info(f"Created log directory: {log_dir}")
                self.docker_name = self.docker_name + service_name + "_"
                additional_command = ""
                self.deployment_info[service_name]["timeout"] = self.timeout
                if "ivy" in service_name:
                    # TODO make it more generic
                    self.deployment_info[service_name]["args"] = self.deployment_info[service_name]["args"].replace("eth0", "lo")
                    if service["role"] == "client":
                        self.deployment_info[service_name]["args"] = self.deployment_info[service_name]["args"].replace("$$TARGET_IP_HEX", "0x7f000001")
                        self.deployment_info[service_name]["args"] = self.deployment_info[service_name]["args"].replace("$$IVY_IP_HEX", "0x7f000001")
                    else:
                        self.deployment_info[service_name]["args"] = self.deployment_info[service_name]["args"].replace("$$TARGET_IP_HEX", "0x7f000001")
                        self.deployment_info[service_name]["args"] = self.deployment_info[service_name]["args"].replace("$$IVY_IP_HEX", "0x7f000001")
                else:
                    for other_service_name in self.services.keys():
                        if other_service_name != service_name:
                            self.deployment_info[other_service_name]["args"] = self.deployment_info[other_service_name]["args"].replace(service_name, "127.0.0.1").replace("eth0", "lo")
                            self.deployment_info[service_name]["args"]       = self.deployment_info[service_name]["args"].replace(other_service_name, "127.0.0.1").replace("eth0", "lo")
                            # self.deployment_info[other_service_name]["args"] = self.deployment_info[other_service_name]["args"].replace("/opt/certs", "/opt/"+ service_name + "/certs")
            
          
            
            self.logger.debug(f"Resolved environment deployment_info: {self.deployment_info}")
            template = self.jinja_env.get_template("run.sh.jinja")
            rendered = template.render(
                services=self.services,
                deployment_info=self.deployment_info,
                paths=paths,
                timestamp=timestamp,
                log_dir=self.log_dirs,
                experiment_name=self.output_dir.split("/")[-1],
                environment_settings=self.environment_settings # TODO
            )
            
            # Write the rendered content to run.generated.sh
            with open(self.services_network_config_file_path, "w") as f:
                f.write(rendered)
                
            with open(self.rendered_services_network_config_file_path, "w") as f:
                f.write(rendered)
                
            self.logger.info(
                f"Localhost file generated at '{self.services_network_config_file_path}'"
            )
            
            self.logger.info("Localhost based environment manager prepared.")
            # Define docker container for experience 
            template = self.jinja_env.get_template("Dockerfile.experience.jinja")
            rendered = template.render(
                services=self.services,
                paths=paths,
                timestamp=timestamp,
                deployment_info=self.deployment_info,
                localhost_single_container_config_file=self.services_network_config_file_path.name,
                log_dir=self.log_dirs,
                additional_command=additional_command,
                experiment_name=self.output_dir.split("/")[-1],
            )
            
            # Write the rendered content to run.generated.sh
            with open(self.services_network_docker_file_path, "w") as f:
                f.write(rendered)
                
            with open(self.rendered_services_network_docker_file_path, "w") as f:
                f.write(rendered)
                
            self.logger.info(
                f"Localhost file generated at '{self.services_network_config_file_path}'"
            )
            
            self.docker_name = self.plugin_loader.build_docker_image_from_path(self.services_network_docker_file_path,
                                                            self.docker_name,
                                                            self.docker_version)
            self.docker_name = self.docker_name.split(':')[0]
            
        except Exception as e:
            self.logger.error(
                f"Failed to generate Localhost file: {e}\n{traceback.format_exc()}"
            )
            exit(1)

    def launch_environment_services(self):
        """
        Launches the Localhost environment using the generated run.sh file.
        """
        # TODO use docker_builder module
        try:
            with open(
                os.path.join(self.output_dir, "logs", "localhost.log"), "w"
            ) as log_file:
                with open(
                    os.path.join(self.output_dir, "logs", "localhost.err.log"), "w"
                ) as log_file_err:
                    volumes = []
                    volumes.append("-v")
                    volumes.append(f"{os.path.abspath(self.log_dirs+'/localhost')}:/app/logs/")
                    for service_name, service in self.services.items():
                        for volume in self.deployment_info[service_name]['volumes']:
                            volumes.append("-v")
                            if isinstance(volume, dict):
                                volumes.append(f"{os.path.abspath(volume['local'])}:{volume['container']}")
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
                            "--name",
                            self.docker_name,
                            *volumes,
                            self.docker_name
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
                    # TODO localhost.data
                self.logger.info("Localhost environment launched successfully.")
        except subprocess.CalledProcessError as e:
            self.logger.error(
                f"Failed to launch Localhost environment: {e.stderr}"
            )
            with open(
                os.path.join(self.output_dir, "logs", "localhost.log"), "w"
            ) as log_file:
                with open(
                    os.path.join(self.output_dir, "logs", "localhost.err.log"), "w"
                ) as log_file_err:
                    log_file.write(e.stdout)
                    log_file_err.write(e.stderr)
            # raise e

    def teardown_environment(self):
        """
        Tears down the Localhost environment by bringing down services.
        """
        # TODO: add a way to retrieve the logs, results, binary
        self.logger.info("Tearing down Localhost environment")
        with open(
            os.path.join(self.output_dir, "logs", "localhost-teardown.log"), "w"
        ) as log_file:
            with open(
                os.path.join(self.output_dir, "logs", "localhost-teardown.err.log"), "w"
            ) as log_file_err:
                try:
                    # Remove the docker image after execution
                    remove_image_command = ["docker", "rmi", f"{self.docker_name}:latest"]
                    self.logger.debug(f"Executing remove image command: {remove_image_command}")
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
                    self.logger.info("Localhost environment torn down successfully")
                except subprocess.CalledProcessError as e:
                    self.logger.error(
                        f"Failed to tear down Localhost environment: {e.stderr}"
                    )
                    raise e

    def read_localhost_file(self) -> Dict[str, Any]:
        """
        Reads the generated run.sh file.
        """
        if not os.path.exists(self.services_network_config_file_path):
            self.logger.error(
                f"Localhost file '{self.services_network_config_file_path}' does not exist."
            )
            raise FileNotFoundError(
                f"Localhost file '{self.services_network_config_file_path}' does not exist."
            )

        with open(self.services_network_config_file_path, "r") as compose_file:
            return yaml.safe_load(compose_file)

