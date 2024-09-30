# PANTHER-SCP/panther/plugins/implementations/picoquic_rfc9000/service_manager.py

import subprocess
import logging
import os
from typing import Any, Dict, Optional
import yaml
from core.interfaces.service_manager_interface import IServiceManager
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, Template

class PicoquicServiceManager(IServiceManager):
    def __init__(self,implementation_config_path: str, protocol_templates_dir: str):
        self.process = None
        self.logger = logging.getLogger("PicoquicServiceManager")
        self.config_path = implementation_config_path
        self.config = self.load_config()
        self.templates_dir = protocol_templates_dir
        self.jinja_env = Environment(loader=FileSystemLoader(self.templates_dir))
        
    def build_image(self):
        """
        Builds the Picoquic Docker image.
        """
        self.logger.info("Building Picoquic Docker image...")
        try:
            subprocess.run(
                "docker build -t picoquic .",
                shell=True,
                cwd="/opt/picoquic",  # Ensure this matches your Dockerfile's location
                check=True
            )
            self.logger.info("Picoquic Docker image built successfully.")
        except Exception as e:
            self.logger.error(f"Failed to build Picoquic Docker image: {e}")

    def load_config(self) -> dict:
        """
        Loads the YAML configuration file.
        """
        config_file = Path(self.config_path)
        if not config_file.exists():
            self.logger.error(f"Configuration file '{self.config_path}' does not exist.")
            return {}
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            self.logger.info(f"Loaded configuration from '{self.config_path}'")
            return config
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            return {}

    def generate_deployment_commands(self, service_params: Dict[str, Any]) -> Dict[str, str]:
        """
        Generates deployment commands based on service parameters using the protocol-specific template.

        :param service_params: Parameters specific to the service.
        :return: A dictionary mapping service names to their respective command strings.
        """
        service_name = service_params.get("name")
        role = service_params.get("parameters", {}).get("role")

        if role not in ["client", "server"]:
            self.logger.error(f"Unknown role '{role}' for service '{service_name}'.")
            raise ValueError(f"Unknown role '{role}' for service '{service_name}'.")

        # Select the appropriate template
        template_file = f"{role}_command.j2"
        try:
            template = self.jinja_env.get_template(template_file)
        except Exception as e:
            self.logger.error(f"Failed to load template '{template_file}': {e}")
            raise e

        # Extract and prepare parameters
        version_config = self.config["picoquic"]["versions"]["rfc9000"]
        client_config = version_config.get(role, {})
        
        # Replace environment variables in paths
        implem_dir = os.getenv("IMPLEM_DIR", ".")
        binary_dir = client_config["binary"]["dir"].replace("$IMPLEM_DIR", implem_dir)
        binary_name = client_config["binary"]["name"]
        binary_path = Path(binary_dir) / binary_name

        cert_file = client_config["certificates"]["cert_file"].replace("$IMPLEM_DIR", implem_dir)
        key_file = client_config["certificates"]["key_file"].replace("$IMPLEM_DIR", implem_dir)

        # Prepare context for template rendering
        context = {
            "binary": {
                "dir": binary_dir,
                "name": binary_name
            },
            "ticket_file": service_params.get("parameters", {}).get("ticket-file", ""),
            "initial_version": service_params.get("parameters", {}).get("initial-version", ""),
            "certificates": {
                "cert_param": client_config["certificates"]["cert_param"],
                "cert_file": cert_file,
                "key_file": key_file
            },
            "protocol": {
                "alpn_param": client_config["protocol"]["alpn_param"],
                "alpn_value": client_config["protocol"]["alpn_value"],
                "additional_parameters": client_config["protocol"]["additional_parameters"]
            },
            "network": {
                "interface_param": client_config["network"]["interface_param"],
                "interface_value": client_config["network"]["interface_value"],
                "port_value": service_params.get("parameters", {}).get("port-value", ""),
                "destination_value": service_params.get("parameters", {}).get("destination-value", ""),
                "source_value": service_params.get("parameters", {}).get("source-value", "")
            },
            "qlog_file": service_params.get("parameters", {}).get("qlog-file", ""),
            "log_path": client_config.get("log_path", "")
        }

        # Render the command
        command = template.render(context)
        self.logger.debug(f"Generated command for '{service_name}': {command}")
        return {service_name: command}

    def start_service(self, parameters: dict):
        """
        Starts the Picoquic server or client based on the role.
        Parameters should include 'role'.
        """
        role = parameters.get("role")
        if role not in ['server', 'client']:
            self.logger.error(f"Unknown role '{role}'. Cannot start service.")
            return

        cmd = self.generate_command(role)
        if not cmd:
            self.logger.error(f"Failed to generate command for role '{role}'.")
            return

        log_path = self.config.get(role, {}).get("log_path", f"/app/logs/{role}.log")
        self.logger.info(f"Starting Picoquic {role} with command: {cmd}")
        try:
            self.process = subprocess.Popen(
                cmd,
                shell=True,
                cwd="/opt/picoquic",  # Ensure this matches your Dockerfile's WORKDIR
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )
            self.logger.info(f"Picoquic {role} started with PID {self.process.pid}")
        except Exception as e:
            self.logger.error(f"Failed to start Picoquic {role}: {e}")

    def stop_service(self):
        """
        Stops the Picoquic service gracefully.
        """
        if self.process:
            self.logger.info(f"Stopping Picoquic service with PID {self.process.pid}")
            try:
                os.killpg(os.getpgid(self.process.pid), 15)  # SIGTERM
                self.process.wait(timeout=10)
                self.logger.info("Picoquic service stopped successfully.")
            except Exception as e:
                self.logger.error(f"Failed to stop Picoquic service: {e}")

    def __str__(self) -> str:
        return super().__str__() + f" (Picoquic Service Manager - {self.config_path})"