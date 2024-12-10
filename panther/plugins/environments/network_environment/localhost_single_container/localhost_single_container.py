import os
from pathlib import Path
import subprocess
import traceback
from typing import Dict, Any, List
from omegaconf import OmegaConf
import yaml
from core.observer.event_manager import EventManager
from config.config_experiment_schema import TestConfig
from config.config_global_schema import GlobalConfig
from plugins.environments.config_schema import EnvironmentConfig
from plugins.services.services_interface import IServiceManager
from plugins.environments.execution_environment.execution_environment_interface import IExecutionEnvironment
from plugins.plugin_loader import PluginLoader
from plugins.environments.network_environment.network_environment_interface import INetworkEnvironment
from core.observer.event import Event

class LocalhostSingleContainerEnvironment(INetworkEnvironment):
    def __init__(
        self,
        env_config_to_test: EnvironmentConfig,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager: EventManager,
    ):
        super().__init__(env_config_to_test, output_dir, env_type, env_sub_type, event_manager)
        
        self.docker_version = "v1"
        self.docker_name = "localhost_"
        
        self.services_network_config_file_path = Path(os.path.join(
            os.getcwd(),
            "plugins",
            "environments",
            env_type,
            env_sub_type,
            "run.generated.sh",
        ))
        self.rendered_services_network_config_file_path = Path(os.path.join(
            self.output_dir, f"run.sh"
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
        self, 
        services_managers: List[IServiceManager], 
        test_config: TestConfig, 
        global_config: GlobalConfig,
        timestamp: str, 
        plugin_loader: PluginLoader, 
        execution_environment: List[IExecutionEnvironment], 
    ):
        """
        Sets up the Localhost environment by generating the run.sh file with deployment commands.

        :param services: Dictionary of services with their configurations.
        :param deployment_info: Dictionary containing commands and volumes for each service.
        :param paths: Dictionary containing various path configurations.
        :param timestamp: The timestamp string to include in log paths.
        """
        self.services_managers : List[IServiceManager] = services_managers
        self.test_config = test_config
        self.execution_environment = execution_environment
        self.plugin_loader = plugin_loader
        self.global_config = global_config
        self.logger.debug("Setup environment with:")
        for service in self.services_managers:
            self.logger.debug(f"Service: {service}")
        self.logger.debug(f"Test Config: {OmegaConf.to_yaml(self.test_config)}")
        self.logger.debug(f"Global Config: {OmegaConf.to_yaml(self.global_config)}")
        self.prepare_environment()
        self.generate_environment_services(paths=self.global_config.paths, timestamp=timestamp)
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
        # TODO check that the implementaion is compatible with shadow (in config file)
        # TODo moodify the shadow template to add the timeout also add folder for each service to be added in the multi stage
        try:
            # Ensure the log directory for each service exists
            for service in self.services_managers:
                # TODO extract method
                log_dir = os.path.join(self.log_dirs, service.service_name)
                if not os.path.exists(log_dir):
                    os.makedirs(log_dir)
                    self.logger.info(f"Created log directory: {log_dir}")
                
                self.logger.debug(f"Generating Docker Compose file for {service.service_name}")
                
                self.docker_name = self.docker_name + service.service_name + "_"
                
                if "ivy" in service.service_name:
                    service.run_cmd["run_cmd"]["command_args"] = service.run_cmd["run_cmd"]["command_args"].replace("eth0", "lo")
                    # TODO make this more general
                    if service.role.name == "client":
                        service.run_cmd["run_cmd"]["command_args"] = service.run_cmd["run_cmd"]["command_args"].replace("$$TARGET_IP_HEX", "0x7f000001")
                        service.run_cmd["run_cmd"]["command_args"] = service.run_cmd["run_cmd"]["command_args"].replace("$$IVY_IP_HEX", "0x7f000001")
                    else:
                        service.run_cmd["run_cmd"]["command_args"] = service.run_cmd["run_cmd"]["command_args"].replace("$$TARGET_IP_HEX", "0x7f000001")
                        service.run_cmd["run_cmd"]["command_args"] = service.run_cmd["run_cmd"]["command_args"].replace("$$IVY_IP_HEX", "0x7f000001")
                else:
                    for other_service in self.services_managers:
                        if other_service.service_name != service.service_name:
                            # Shadow does not suport the _ in the service name -> replace by .
                            # TODO use "." in the service name for all plugins
                            service.run_cmd["run_cmd"]["command_args"] = service.run_cmd["run_cmd"]["command_args"].replace(other_service.service_name, "127.0.0.1").replace("eth0", "lo")
                            other_service.run_cmd["run_cmd"]["command_args"] = other_service.run_cmd["run_cmd"]["command_args"].replace(service.service_name, "127.0.0.1").replace("eth0", "lo")

            for service in self.services_managers:
                service.environments = self.resolve_environment_variables(service.environments)
                self.logger.debug(f"Service {service.service_name} environment: {service.environments}")
     
            template = self.jinja_env.get_template("run.sh.jinja")
            self.logger.debug(f"Template: {template}")
            self.logger.debug(f"Services: {self.services_managers}")
            self.logger.debug(f"Deployment Info: {self.test_config}")
            rendered = template.render(
                services=self.services_managers,
                test_config=self.test_config,
                paths=paths,
                timestamp=timestamp,
                log_dir=self.log_dirs,
                experiment_name=self.output_dir.split("/")[-1],
            )

            # Write the rendered content to shadow.generated.yml
            with open(self.services_network_config_file_path, "w") as f:
                f.write(rendered)

            with open(self.rendered_services_network_config_file_path, "w") as f:
                f.write(rendered)

            self.logger.info(f"Localhost file generated at '{self.services_network_config_file_path}'")

            self.logger.info("Localhost based environment manager prepared.")
            # Define docker container for experience
            template = self.jinja_env.get_template("Dockerfile.experience.jinja")
            rendered = template.render(
                services=self.services_managers,
                test_config=self.test_config,
                paths=paths,
                timestamp=timestamp,
                log_dir=self.log_dirs,
                localhost_single_container_config_file=self.services_network_config_file_path.name,
                experiment_name=self.output_dir.split("/")[-1],
            )

            # Write the rendered content to shadow.generated.yml
            with open(self.services_network_docker_file_path, "w") as f:
                f.write(rendered)

            with open(self.rendered_services_network_docker_file_path, "w") as f:
                f.write(rendered)

            self.logger.info(f"Localhost file Dockerfile generated at '{self.services_network_docker_file_path}'")

            self.docker_name = self.plugin_loader.build_docker_image_from_path(
                self.services_network_docker_file_path, self.docker_name, self.docker_version
            )
            self.docker_name = self.docker_name.split(":")[0]

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
                            "ps",
                            "-f",
                            f"name={self.docker_name}",
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
                    stdsplit = result.stdout.split("\n")
                    self.logger.debug(f"docker-compose ps: {result.stdout} - {result.stderr} - {len(self.services_managers)}  - {len(stdsplit)}")
                    if len(stdsplit) < len(self.services_managers)+1:
                        self.logger.debug("Docker Compose environment monitored successfully - Experiment finished earlier")
                        self.event_manager.notify(Event(name="experiment_finished_early", data={}))
                    
                self.logger.debug("Docker Compose environment monitored successfully.")
        except subprocess.CalledProcessError as e:
            self.logger.error(
                f"Failed to monitor Docker Compose environment: {e.stderr}"
            )
            raise e
        
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
                    # Stop the running docker container
                    stop_container_command = ["docker", "stop", self.docker_name]
                    self.logger.debug(f"Executing stop container command: {stop_container_command}")
                    result = subprocess.run(
                        stop_container_command,
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                    )
                    log_file.write(result.stdout)
                    log_file_err.write(result.stderr)
                    
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
                    with open(
                        os.path.join(self.output_dir, "logs", "localhost-teardown.log"), "w"
                    ) as log_file:
                        with open(
                            os.path.join(self.output_dir, "logs", "localhost-teardown.err.log"), "w"
                        ) as log_file_err:
                            try:
                                stop_container_command = ["docker", "stop", self.docker_name]
                                self.logger.debug(f"Executing stop container command: {stop_container_command}")
                                result = subprocess.run(
                                    stop_container_command,
                                    check=True,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    text=True,
                                )
                                log_file.write(result.stdout)
                                log_file_err.write(result.stderr)
                                # Remove the docker image after execution
                                remove_image_command = ["docker", "rmi", "--force" f"{self.docker_name}:latest"]
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


