import os
from pathlib import Path
import socket
import subprocess
import logging
import traceback
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader
import yaml
from panther.core.utils.plugin_loader import PluginLoader
from plugins.environments.network_environment.network_environment_interface import INetworkEnvironment

class SingleContainerEnvironment(INetworkEnvironment):
    def __init__(
        self,
        config_path: str,
        output_dir: str,
        network_driver: str = "bridge",
        templates_dir: str = "plugins/environments/network_environment/single_container",
    ):
        self.logger = logging.getLogger("SingleContainerEnvironment")
        self.services_network_config_file_path = os.path.join(
            os.getcwd(),
            "plugins",
            "environments",
            "network_environment",
            "shadow_ns",
            "shadow.generated.yml",
        )
        self.config_path = config_path
        self.network_name = "quic_network_dynamic"
        self.network_driver = network_driver
        self.templates_dir = templates_dir
        self.output_dir = output_dir
        self.log_dirs = os.path.join(self.output_dir, "logs")
        
        self.rendered_shadow_conf_path = os.path.join(
            self.output_dir, "shadow.yml"
        )
        self.shadow_conf_path = Path(self.services_network_config_file_path)
        
        self.rendered_shadow_docker_path = os.path.join(
            self.output_dir, "Dockerfile.experience"
        )
        self.shadow_docker_path = Path(self.services_network_config_file_path)
        
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

    def __str__(self):
        attributes = {
            "config_path": self.config_path,
            "output_dir": self.output_dir,
            "network_driver": self.network_driver,
            "templates_dir": self.templates_dir,
            "services_network_config_file_path": self.services_network_config_file_path,
            "network_name": self.network_name,
            "log_dirs": self.log_dirs,
            "rendered_shadow_conf_path": self.rendered_shadow_conf_path,
            "shadow_conf_path": str(self.shadow_conf_path),
            "services": self.services,
            "deployment_commands": self.deployment_commands,
            "timeout": self.timeout,
        }
        return f"SingleContainerEnvironment({attributes})"
    
    def __repr__(self):
        attributes = {
            "config_path": self.config_path,
            "output_dir": self.output_dir,
            "network_driver": self.network_driver,
            "templates_dir": self.templates_dir,
            "services_network_config_file_path": self.services_network_config_file_path,
            "network_name": self.network_name,
            "log_dirs": self.log_dirs,
            "rendered_shadow_conf_path": self.rendered_shadow_conf_path,
            "shadow_conf_path": str(self.shadow_conf_path),
            "services": self.services,
            "deployment_commands": self.deployment_commands,
            "timeout": self.timeout,
        }
        return f"SingleContainerEnvironment({attributes})"
    
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
        self.logger.info("Preparing Shadow NS service manager...")
        # Additional setup can be implemented here
        plugin_loader.build_docker_image("shadow_ns")
        self.plugin_loader = plugin_loader
        
        
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
        self, services: Dict[str, Dict[str, Any]], deployment_info: Dict[str, Dict[str, Any]], paths: Dict[str, str], timestamp: str, plugin_loader: PluginLoader
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
        self.logger.debug(
            f"Setting up Shadow NS environment with services: {services} and deployment info: {deployment_info}"
        )
        self.prepare()
        self.generate_shadow_ns(paths=paths, timestamp=timestamp)
        self.logger.info("Shadow NS environment setup complete")
    
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
                self.logger.debug(f"\nResolving variable: {key}")
                self.logger.debug(f"Original value: {value}")
                for var_name, var_value in resolved_env.items():  # Use already resolved variables
                    if f"${{{var_name}}}" in resolved_value or f"${var_name}" in resolved_value:
                        resolved_value = resolved_value.replace(f"${{{var_name}}}", var_value)
                        resolved_value = resolved_value.replace(f"${var_name}", var_value)
                        self.logger.debug(f"Replaced ${var_name} in {key} with {var_value}")
                resolved_value = resolved_value.replace('$', '$$')
                resolved_env[key] = resolved_value

        self.logger.debug("\nFinal resolved environment variables without duplication:")
        for k, v in resolved_env.items():
            self.logger.debug(f"{k}: {v}")

        return resolved_env


    def deploy_services(self):
        self.logger.info("Deploying services")
        # self.prepare_tester() # TODO
        self.launch_shadow_ns()
        

    def generate_shadow_ns(self, paths: Dict[str, str], timestamp: str, plugin_loader: PluginLoader):
        """
        Generates the shadow.yml file using the provided services and deployment commands.

        :param paths: Dictionary containing various path configurations.
        :param timestamp: The timestamp string to include in log paths.
        """
        # TODO add timeout in the test config
        try:
            # Ensure the log directory for each service exists
            for service_name in self.services.keys():
                log_dir = os.path.join(self.log_dirs, service_name)
                if not os.path.exists(log_dir):
                    os.makedirs(log_dir)
                    self.logger.info(f"Created log directory: {log_dir}")
                
                additional_command = ""
                if "ivy" in service_name:
                    # update other service so they wait for ivy to be ready
                    self.logger.debug(f"Adding wait for Ivy tester to be ready for {service_name}")
                    for other_service_name in self.services.keys():
                        if other_service_name != service_name:
                            additional_command = f"""
                            while [ ! -f /app/sync_logs/ivy_ready ]; do
                                echo "Waiting for Ivy tester to be ready..." >> /app/logs/tester_ready;
                                sleep 2;
                            done;
                            echo "Ivy tester is ready, starting {other_service_name}..." >> /app/logs/tester_ready;   
                            """.strip()
                            self.deployment_info[other_service_name]["volumes"].append("shared_logs:/app/sync_logs")
            
            
            for service_name, service in self.services.items():
                if "environment" in self.deployment_info[service_name]:
                    self.deployment_info[service_name]["environment"] = self.resolve_environment_variables(self.deployment_info[service_name]["environment"])
            
            template = self.jinja_env.get_template("shadow-template.jinja")
            rendered = template.render(
                services=self.services,
                deployment_info=self.deployment_info,
                paths=paths,
                timestamp=timestamp,
                log_dir=self.log_dirs,
                additional_command=additional_command,
                experiment_name=self.output_dir.split("/")[-1],
            )
            
            # Write the rendered content to shadow.generated.yml
            with open(self.shadow_conf_path, "w") as f:
                f.write(rendered)
                
            with open(self.rendered_shadow_conf_path, "w") as f:
                f.write(rendered)
                
            self.logger.info(
                f"Shadow NS file generated at '{self.shadow_conf_path}'"
            )
            
            self.logger.info("Shadow NS based environment manager prepared.")
            # Define docker container for experience 
            template = self.jinja_env.get_template("Dockerfile.experience.jinja")
            rendered = template.render(
                services=self.services,
                paths=paths,
                timestamp=timestamp,
                log_dir=self.log_dirs,
                additional_command=additional_command,
                experiment_name=self.output_dir.split("/")[-1],
            )
            
            # Write the rendered content to shadow.generated.yml
            with open(self.shadow_docker_path, "w") as f:
                f.write(rendered)
                
            with open(self.rendered_shadow_docker_path, "w") as f:
                f.write(rendered)
                
            self.logger.info(
                f"Shadow NS file generated at '{self.shadow_conf_path}'"
            )
            
            self.plugin_loader.build_docker_image_from_path(Path("plugins/environments/network_environment/shadow_ns/Dockerfile.experience"))
            
        except Exception as e:
            self.logger.error(
                f"Failed to generate Shadow NS file: {e}\n{traceback.format_exc()}"
            )
            exit(1)

    def launch_shadow_ns(self):
        """
        Launches the Shadow NS environment using the generated shadow.yml file.
        """
        try:
            with open(
                os.path.join(self.output_dir, "logs", "shadow.log"), "w"
            ) as log_file:
                with open(
                    os.path.join(self.output_dir, "logs", "shadow.err.log"), "w"
                ) as log_file_err:
                    result = subprocess.run(
                        [
                            "docker",
                            "compose",
                            "-f",
                            str(self.shadow_conf_path),
                            "up",
                            "-d"
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
                self.logger.info("Shadow NS environment launched successfully.")
        except subprocess.CalledProcessError as e:
            self.logger.error(
                f"Failed to launch Shadow NS environment: {e.stderr}"
            )
            raise e

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
                    if self.network_driver == "host":
                        # In host mode, stop containers individually
                        # Assumes service names are the container names
                        compose_dict = self.read_shadow_file()
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
                        # For other network drivers, use shadow
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

