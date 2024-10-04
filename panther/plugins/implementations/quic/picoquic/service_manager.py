# PANTHER-SCP/panther/plugins/implementations/picoquic_rfc9000/service_manager.py

import subprocess
import logging
import os
from typing import Any, Dict, Optional
import yaml
import traceback    
from core.interfaces.service_manager_interface import IServiceManager
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, Template

# TODO Tom create test template for QUIC implementations new users

class PicoquicServiceManager(IServiceManager):
    def __init__(self,implementation_config_path: str = "plugins/implementations/quic/picoquic/", 
                      protocol_templates_dir: str     = "plugins/implementations/quic/picoquic/templates/"):
        self.process = None
        self.logger = logging.getLogger("PicoquicServiceManager")
        self.config_path = implementation_config_path
        self.config = self.load_config()
        self.validate_config()
        self.templates_dir = protocol_templates_dir
        self.jinja_env = Environment(loader=FileSystemLoader(self.templates_dir))
        # Debugging: List files in templates_dir
        if not os.path.isdir(self.templates_dir):
            self.logger.error(f"Templates directory '{self.templates_dir}' does not exist.")
        else:
            templates = os.listdir(self.templates_dir)
            self.logger.debug(f"Available templates in '{self.templates_dir}': {templates}")
    
    def get_implementation_name(self) -> str:
        return "picoquic"
    
    def validate_config(self):
        """
        Validates the loaded implementation configuration.
        """
        def keys_exists(element, keys):
            '''
            Check if *keys (nested) exists in `element` (dict).
            '''
            if not isinstance(element, dict):
                raise AttributeError('keys_exists() expects dict as first argument.')
            if len(keys) == 0:
                raise AttributeError('keys_exists() expects at least two arguments, one given.')

            _element = element
            for key in keys:
                try:
                    _element = _element[key]
                except KeyError:
                    return False
            return True

        if not self.config:
            self.logger.error("Implementation configuration is empty.")
            raise ValueError("Empty implementation configuration.")
        # Additional validation can be implemented here
        # For example, check required keys are present
        required_keys = [['picoquic'], ['picoquic','versions']]
        for key in required_keys:
            if not keys_exists(self.config, key):
                self.logger.error(f"Missing required key '{key}' in configuration.")
                raise KeyError(f"Missing required key '{key}' in configuration.")
            
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
            self.logger.error(f"Failed to build Picoquic Docker image: {e}\n{traceback.format_exc()}")

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
            self.logger.error(f"Failed to load configuration: {e}\n{traceback.format_exc()}")
            return {}

    def generate_deployment_commands(self, service_params: Dict[str, Any]) -> Dict[str, str]:
        """
        Generates deployment commands based on service parameters using the protocol-specific templates.

        :param service_params: Parameters specific to the service.
        :return: A dictionary mapping service names to their respective command strings.
        """
        self.logger.debug(f"Generating deployment commands for service: {service_params}")
        role = service_params.get("parameters").get("role")
        version = service_params.get("version", "rfc9000")
        version_config = self.config.get("picoquic", {}).get("versions", {}).get(version, {})

        self.logger.debug(f"Using version '{version}' configuration: {version_config}")
        # Extract parameters based on role
        if role == "client":
            template_name = "client_command.j2"
            params = {
                "binary": {
                    "dir": self.replace_env_vars(version_config.get("client", {}).get("binary", {}).get("dir", "./picoquic")),
                    "name": version_config.get("client", {}).get("binary", {}).get("name", "./picoquicdemo"),
                },
                "ticket_file": service_params.get("parameters").get("ticket-file"),
                "initial_version": version_config.get("client", {}).get("initial_version"),
                "certificates": {
                    "cert_param": version_config.get("client", {}).get("certificates", {}).get("cert", {}).get("param"),
                    "cert_file": self.replace_env_vars(version_config.get("client", {}).get("certificates", {}).get("cert", {}).get("file")),
                    "key_param": version_config.get("client", {}).get("certificates", {}).get("key", {}).get("param"),
                    "key_file": self.replace_env_vars(version_config.get("client", {}).get("certificates", {}).get("key", {}).get("file")),
                },
                "protocol": {
                    "alpn" : {
                        "param": version_config.get("server", {}).get("protocol", {}).get("alpn", {}).get("param"),
                        "value": version_config.get("server", {}).get("protocol", {}).get("alpn", {}).get("value"),
                    },
                    "additional_parameters": version_config.get("client", {}).get("protocol", {}).get("additional_parameters"),
                },
                "network": {
                    "interface" : {
                        "param": version_config.get("client", {}).get("network", {}).get("interface", {}).get("param"),
                        "value": version_config.get("client", {}).get("network", {}).get("interface", {}).get("value"),
                    },
                    "port": version_config.get("client", {}).get("network", {}).get("port"),
                    "destination": service_params.get("target", version_config.get("client", {}).get("network", {}).get("destination")),
                },
                "logging": {
                    "log_path": version_config.get("client", {}).get("logging", {}).get("log_path"),
                    "qlog": {
                        "param": version_config.get("client", {}).get("logging", {}).get("qlog", {}).get("param"),
                        "path": version_config.get("client", {}).get("logging", {}).get("qlog", {}).get("path"),
                    }
                }
            }
            # Handle missing parameters
            missing_params = self.check_missing_params(params)
            if missing_params:
                self.logger.error(f"Missing parameters for server service: {missing_params}")
                raise KeyError(f"Missing parameters for server service: {missing_params}")

        elif role == "server":
            template_name = "server_command.j2"
            params = {
                "binary": {
                    "dir": self.replace_env_vars(version_config.get("server", {}).get("binary", {}).get("dir", "./picoquic")),
                    "name": version_config.get("server", {}).get("binary", {}).get("name", "./picoquicdemo"),
                },
                "logging": {
                    "log_path": version_config.get("server", {}).get("logging", {}).get("log_path"),
                    "qlog": {
                        "param": version_config.get("server", {}).get("logging", {}).get("qlog", {}).get("param"),
                        "path": version_config.get("server", {}).get("logging", {}).get("qlog", {}).get("path"),
                    }
                },
                 "certificates": {
                    "cert_param": version_config.get("server", {}).get("certificates", {}).get("cert", {}).get("param"),
                    "cert_file": self.replace_env_vars(version_config.get("client", {}).get("certificates", {}).get("cert", {}).get("file")),
                    "key_param": version_config.get("server", {}).get("certificates", {}).get("key", {}).get("param"),
                    "key_file": self.replace_env_vars(version_config.get("client", {}).get("certificates", {}).get("key", {}).get("file")),
                },
                "protocol": {
                    "alpn" : {
                        "param": version_config.get("server", {}).get("protocol", {}).get("alpn", {}).get("param"),
                        "value": version_config.get("server", {}).get("protocol", {}).get("alpn", {}).get("value"),
                    },
                    "additional_parameters": version_config.get("server", {}).get("protocol", {}).get("additional_parameters"),
                },
                "network": {
                    "interface" : {
                        "param": version_config.get("client", {}).get("network", {}).get("interface", {}).get("param"),
                        "value": version_config.get("client", {}).get("network", {}).get("interface", {}).get("value"),
                    },
                    "port": version_config.get("server", {}).get("network", {}).get("port"),
                    "destination": service_params.get("destination-value", version_config.get("server", {}).get("network", {}).get("destination")),
                }
            }
            # Handle missing parameters
            missing_params = self.check_missing_params(params)
            if missing_params:
                self.logger.error(f"Missing parameters for server service: {missing_params}")
                raise KeyError(f"Missing parameters for server service: {missing_params}")
        else:
            self.logger.error(f"Unknown role '{role}' for service.")
            raise ValueError(f"Unknown role '{role}' for service.")

        # Render the appropriate template
        try:
            self.logger.debug(f"Rendering command using template '{template_name}' with parameters: {params}")
            template = self.jinja_env.get_template(template_name)
            command = template.render(**params)
            service_name = service_params.get("name")
            if not service_name:
                service_name = "picoquic_client" if role == "client" else "picoquic_server"
            self.logger.debug(f"Generated command for '{service_name}': {command}")
            return {service_name: command}
        except Exception as e:
            self.logger.error(f"Failed to render command for service '{service_params.get('name', 'unknown')}': {e}\n{traceback.format_exc()}")
            raise e

    def check_missing_params(self, params: Dict[str, Any], required: list = []) -> list:
        """
        Checks for missing parameters in the params dictionary.

        :param params: Dictionary of parameters.
        :param required: List of required top-level keys.
        :return: List of missing parameter keys.
        """
        missing = []
        # Check top-level required keys
        for key in required:
            if not params.get(key):
                missing.append(key)
        # Recursively check nested dictionaries
        def recurse(d, parent_key=''):
            for k, v in d.items():
                full_key = f"{parent_key}.{k}" if parent_key else k
                if isinstance(v, dict):
                    recurse(v, full_key)
                elif v is None:
                    missing.append(full_key)
        recurse(params)
        return missing
    
    def replace_env_vars(self, value: str) -> str:
        """
        Replaces environment variables in the given string with their actual values.

        :param value: String containing environment variables (e.g., $IMPLEM_DIR).
        :return: String with environment variables replaced by their values.
        """
        try:
            self.logger.debug(f"Replacing environment variables in '{value}'")
            return os.path.expandvars(value)
        except Exception as e:
            self.logger.error(f"Failed to replace environment variables in '{value}': {e}\n{traceback.format_exc()}")
            return value
    
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
            self.logger.error(f"Failed to start Picoquic {role}: {e}\n{traceback.format_exc()}")

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