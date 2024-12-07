import os
from pathlib import Path
import socket
import subprocess
import logging
import traceback
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader
import yaml
from plugins.plugin_loader import PluginLoader
from plugins.environments.network_environment.network_environment_interface import INetworkEnvironment

class VnetSingleContainerEnvironment(INetworkEnvironment):
    def __init__(
        self,
        config_path: str,
        output_dir: str,
        environment_settings: Dict[str,Any],
        network_driver: str = "bridge",
        templates_dir: str = "plugins/environments/network_environment/vnet_single_container",
    ):
        self.logger = logging.getLogger("VnetSingleContainerEnvironment")
        self.services_network_config_file_path = os.path.join(
            os.getcwd(),
            "plugins",
            "environments",
            "network_environment",
            "vnet_single_container",
            "run.generated.sh",
        )
        self.services_docker_config_file_path = os.path.join(
            os.getcwd(),
            "plugins",
            "environments",
            "network_environment",
            "vnet_single_container",
            "Dockerfile.generated",
        )
        self.config_path = config_path
        self.config = self.load_config()
        # TODO: self.validate_config()
        
        self.network_name = "quic_network_dynamic"
        self.network_driver = network_driver
        self.templates_dir = templates_dir
        self.output_dir = output_dir
        self.log_dirs = os.path.join(self.output_dir, "logs")
        
        self.rendered_vnet_conf_path = os.path.join(
            self.output_dir, "run.sh"
        )
        self.vnet_conf_path = Path(self.services_network_config_file_path)
        
        self.rendered_vnet_docker_path = os.path.join(
            self.output_dir, "Dockerfile.experience"
        )
        self.vnet_docker_path = Path(self.services_docker_config_file_path)
        
        self.docker_version = "v1"
        self.environment_settings = environment_settings
        self.docker_name = "vnet_"
        
        self.services = {}
        self.deployment_commands = {}
        self.timeout = 60
        self.jinja_env = Environment(loader=FileSystemLoader(self.templates_dir))
        self.jinja_env.filters['realpath'] = lambda x: os.path.abspath(x)
        self.jinja_env.filters['is_dict']  = lambda x: isinstance(x, dict)
        self.jinja_env.trim_blocks   = True
        self.jinja_env.lstrip_blocks = True
        
        self.plugin_loader = None # TODO ?
        
        self.source_dir = "/opt/panther"
        
        # Define a base subnet for the services
        self.base_subnet = "192.168.1."
        self.ip_counter = 2  # Start from .2 to avoid .1 (usually reserved for gateway)

    def __str__(self):
        attributes = {
            "config_path": self.config_path,
            "output_dir": self.output_dir,
            "network_driver": self.network_driver,
            "templates_dir": self.templates_dir,
            "services_network_config_file_path": self.services_network_config_file_path,
            "network_name": self.network_name,
            "log_dirs": self.log_dirs,
            "rendered_vnet_conf_path": self.rendered_vnet_conf_path,
            "vnet_conf_path": str(self.vnet_conf_path),
            "services": self.services,
            "deployment_commands": self.deployment_commands,
            "timeout": self.timeout,
        }
        return f"VnetSingleContainerEnvironment({attributes})"
    
    def __repr__(self):
        attributes = {
            "config_path": self.config_path,
            "output_dir": self.output_dir,
            "network_driver": self.network_driver,
            "templates_dir": self.templates_dir,
            "services_network_config_file_path": self.services_network_config_file_path,
            "network_name": self.network_name,
            "log_dirs": self.log_dirs,
            "rendered_vnet_conf_path": self.rendered_vnet_conf_path,
            "vnet_conf_path": str(self.vnet_conf_path),
            "services": self.services,
            "deployment_commands": self.deployment_commands,
            "timeout": self.timeout,
        }
        return f"VnetSingleContainerEnvironment({attributes})"
    
    def load_config(self) -> dict:
        """
        Loads the YAML configuration file.
        """
        config_file = Path(self.config_path)
        if not config_file.exists():
            self.logger.error(
                f"Configuration file '{self.config_path}' does not exist."
            )
            return {}
        try:
            with open(config_file, "r") as f:
                config = yaml.safe_load(f)
            self.logger.info(f"Loaded configuration from '{self.config_path}'")
            return config
        except Exception as e:
            self.logger.error(
                f"Failed to load configuration: {e}\n{traceback.format_exc()}"
            )
            return {}
        
    def build_images(self):
        """
        Builds Docker images for all implementations.
        """
        self.logger.info("Building Docker images for all implementations")
        self.logger.info("Docker images built successfully")
        raise NotImplementedError("Method not implemented - In another module FOR NOW")

    def prepare(self,plugin_loader: Optional[PluginLoader] = None):
        """
        Prepare the service manager for use.
        """
        self.logger.info("Preparing Vnet service manager...")
        # Additional setup can be implemented here
        plugin_loader.build_docker_image("vnet_single_container", self.docker_version)
        self.plugin_loader = plugin_loader
        
        
    def is_port_free(self, port: int) -> bool:
        """
        Checks if a given port is free on the host.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("vnet", port)) != 0

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
        self, services: Dict[str, Dict[str, Any]], deployment_info: Dict[str, Dict[str, Any]], 
        paths: Dict[str, str], timestamp: str, plugin_loader: PluginLoader
    ):
        """
        Sets up the Vnet environment by generating the run.sh file with deployment commands.

        :param services: Dictionary of services with their configurations.
        :param deployment_info: Dictionary containing commands and volumes for each service.
        :param paths: Dictionary containing various path configurations.
        :param timestamp: The timestamp string to include in log paths.
        """
        self.services             = services
        self.deployment_info      = deployment_info
        
        self.logger.debug(
            f"Setting up Vnet environment with:\n- services: {services}\n- deployment info: {deployment_info}\n- environment settings: {self.environment_settings}"
        )
        self.prepare(plugin_loader)
        self.generate_vnet_single_container(paths=paths, timestamp=timestamp)
        self.logger.info("Vnet environment setup complete")
    
    def resolve_environment_variables(self, env_vars):
        """
        Resolves environment variables incrementally, ensuring no duplication
        and preserving unresolved tokens. Processes variables in dependency order.

        :param env_vars: dict, environment variables with potential references.
        :return: dict, resolved environment variables.
        """
        resolved_env = {}

        self.logger.debug("Initial environment variables:")
        for k, v in env_vars.items():
            self.logger.debug(f"{k}: {v}")

        for key, value in env_vars.items():
            if isinstance(value, str):
                resolved_value = value
                self.logger.debug(f"Resolving variable: {key} - Original value: {value}")
                for var_name, var_value in resolved_env.items():  # Use already resolved variables
                    if f"${{{var_name}}}" in resolved_value or f"${var_name}" in resolved_value:
                        resolved_value = resolved_value.replace(f"${{{var_name}}}", var_value)
                        resolved_value = resolved_value.replace(f"${var_name}", var_value)
                        self.logger.debug(f"Replaced ${var_name} in {key} with {var_value}")
                resolved_value = resolved_value.replace('$', '$$')
                resolved_env[key] = resolved_value

        self.logger.debug("Final resolved environment variables without duplication:")
        for k, v in resolved_env.items():
            self.logger.debug(f"{k}: {v}")

        return resolved_env


    def deploy_services(self):
        self.logger.info("Deploying services")
        # self.prepare_tester() # TODO
        self.launch_vnet_single_container()
        
    

    def generate_vnet_single_container(self, paths: Dict[str, str], timestamp: str):
        """
        Generates the run.sh file using the provided services and deployment commands.

        :param paths: Dictionary containing various path configurations.
        :param timestamp: The timestamp string to include in log paths.
        """
        # TODO add timeout in the test config
        # TODO check that the implementaion is compatible with vnet (in config file)
        # TODo moodify the vnet template to add the timeout also add folder for each service to be added in the multi stage
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
                
                # Assign a unique IP for the current service
                service_ip = f"{self.base_subnet}{self.ip_counter}"
                service_ip_hex = f"0x{self.ip_counter:02X}"
                self.ip_counter += 1

                # Save the assigned IP to deployment_info
                self.deployment_info[service_name]["ip"] = service_ip
                self.deployment_info[service_name]["ip_hex"] = service_ip_hex
               
                # # Generate unique IP for the service
                # service_ip = f"{self.base_subnet}{self.ip_counter}"
                # peer_ip = f"{self.base_subnet}{self.ip_counter + 1}"
                # self.ip_counter += 2

                # # Store IPs in deployment info
                # self.deployment_info[service_name]["ip"] = f"{service_ip}/24"
                # self.deployment_info[service_name]["ip_peer"] = f"{peer_ip}/24"
                
            for service_name, service in self.services.items():
                if "ivy" in service_name:
                    # Update args for ivy services
                    #self.deployment_info[service_name]["args"] = self.deployment_info[service_name]["args"].replace("eth0", "lo")
                    if service["role"] == "client":
                        target_ip = self.deployment_info[service["target"]]["ip_hex"]
                        self.deployment_info[service_name]["args"] = self.deployment_info[service_name]["args"].replace("$$TARGET_IP_HEX", target_ip)
                        self.deployment_info[service_name]["args"] = self.deployment_info[service_name]["args"].replace("$$IVY_IP_HEX", service_ip_hex)
                    else:
                        target_ip = self.deployment_info[service["target"]]["ip_hex"] if "target" in service else "0x7F000001"
                        self.deployment_info[service_name]["args"] = self.deployment_info[service_name]["args"].replace("$$TARGET_IP_HEX", target_ip)
                        self.deployment_info[service_name]["args"] = self.deployment_info[service_name]["args"].replace("$$IVY_IP_HEX", service_ip_hex)
                else:
                    for other_service_name, other_service in self.services.items():
                        if other_service_name != service_name:
                            target_ip = self.deployment_info[other_service_name]["ip"]
                            self.deployment_info[service_name]["args"] = (
                                self.deployment_info[service_name]["args"]
                                .replace(other_service_name, target_ip)
                                #.replace("eth0", "lo")
                    )
                
            # Log assigned IPs for debugging
            for service_name, service in self.services.items():
                service_ip = self.deployment_info[service_name]["ip"]
                self.logger.debug(f"Assigned IP {service_ip} to service {service_name}")
                        
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
            with open(self.vnet_conf_path, "w") as f:
                f.write(rendered)
                
            with open(self.rendered_vnet_conf_path, "w") as f:
                f.write(rendered)
                
            self.logger.info(
                f"Vnet file generated at '{self.vnet_conf_path}'"
            )
            
            self.logger.info("Vnet based environment manager prepared.")
            # Define docker container for experience 
            template = self.jinja_env.get_template("Dockerfile.experience.jinja")
            rendered = template.render(
                services=self.services,
                paths=paths,
                timestamp=timestamp,
                deployment_info=self.deployment_info,
                vnet_single_container_config_file=self.vnet_conf_path.name,
                log_dir=self.log_dirs,
                additional_command=additional_command,
                experiment_name=self.output_dir.split("/")[-1],
            )
            
            # Write the rendered content to run.generated.sh
            with open(self.vnet_docker_path, "w") as f:
                f.write(rendered)
                
            with open(self.rendered_vnet_docker_path, "w") as f:
                f.write(rendered)
                
            self.logger.info(
                f"Vnet file generated at '{self.vnet_conf_path}'"
            )
            
            self.docker_name = self.plugin_loader.build_docker_image_from_path(self.vnet_docker_path,
                                                            self.docker_name,
                                                            self.docker_version)
            self.docker_name = self.docker_name.split(':')[0]
            
        except Exception as e:
            self.logger.error(
                f"Failed to generate Vnet file: {e}\n{traceback.format_exc()}"
            )
            exit(1)

    def launch_vnet_single_container(self):
        """
        Launches the Vnet environment using the generated run.sh file.
        """
        # TODO use docker_builder module
        try:
            with open(
                os.path.join(self.output_dir, "logs", "vnet.log"), "w"
            ) as log_file:
                with open(
                    os.path.join(self.output_dir, "logs", "vnet.err.log"), "w"
                ) as log_file_err:
                    volumes = []
                    volumes.append("-v")
                    volumes.append(f"{os.path.abspath(self.log_dirs+'/vnet')}:/app/logs/")
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
                    # TODO vnet.data
                self.logger.info("Vnet environment launched successfully.")
        except subprocess.CalledProcessError as e:
            self.logger.error(
                f"Failed to launch Vnet environment: {e.stderr}"
            )
            with open(
                os.path.join(self.output_dir, "logs", "vnet.log"), "w"
            ) as log_file:
                with open(
                    os.path.join(self.output_dir, "logs", "vnet.err.log"), "w"
                ) as log_file_err:
                    log_file.write(e.stdout)
                    log_file_err.write(e.stderr)
            # raise e

    def teardown_environment(self):
        """
        Tears down the Vnet environment by bringing down services.
        """
        # TODO: add a way to retrieve the logs, results, binary
        self.logger.info("Tearing down Vnet environment")
        with open(
            os.path.join(self.output_dir, "logs", "vnet-teardown.log"), "w"
        ) as log_file:
            with open(
                os.path.join(self.output_dir, "logs", "vnet-teardown.err.log"), "w"
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
                    self.logger.info("Vnet environment torn down successfully")
                except subprocess.CalledProcessError as e:
                    self.logger.error(
                        f"Failed to tear down Vnet environment: {e.stderr}"
                    )
                    raise e

    def read_vnet_file(self) -> Dict[str, Any]:
        """
        Reads the generated run.sh file.
        """
        if not os.path.exists(self.services_network_config_file_path):
            self.logger.error(
                f"Vnet file '{self.services_network_config_file_path}' does not exist."
            )
            raise FileNotFoundError(
                f"Vnet file '{self.services_network_config_file_path}' does not exist."
            )

        with open(self.services_network_config_file_path, "r") as compose_file:
            return yaml.safe_load(compose_file)

