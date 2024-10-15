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
        self.service_name = None
        self.validate_config()
        self.templates_dir = protocol_templates_dir
        self.jinja_env = Environment(loader=FileSystemLoader(self.templates_dir))
        # Debugging: List files in templates_dir
        if not os.path.isdir(self.templates_dir):
            self.logger.error(f"Templates directory '{self.templates_dir}' does not exist.")
        else:
            templates = os.listdir(self.templates_dir)
            self.logger.debug(f"Available templates in '{self.templates_dir}': {templates}")
    
    def get_base_url(self, service_name: str) -> str:
        """
        Returns the base URL for the given service.
        """
        # Assuming services are accessible via localhost and mapped ports
        # You might need to adjust this based on your actual setup
        port_mappings = {
            'picoquic_server': 8080,
            'picoquic_client': 8081,
        }
        port = port_mappings.get(service_name, None)
        if port:
            return f"http://localhost:{port}/"
        else:
            self.logger.error(f"No port mapping found for service '{service_name}'")
            return ""
        
    def get_implementation_name(self) -> str:
        return "picoquic"
    
    def get_service_name(self) -> str:
        return self.service_name
    
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

    def generate_deployment_commands(self, service_params: Dict[str, Any], environment: str) -> Dict[str, Any]:
        """
        Generates deployment commands and collects volume mappings based on service parameters.

        :param service_params: Parameters specific to the service.
        :param environment: The environment in which the services are being deployed.
        :return: A dictionary with service name as key and a dictionary containing command and volumes.
        """
        self.logger.debug(f"Generating deployment commands for service: {service_params}")
        role = service_params.get("role")
        version = service_params.get("version", "rfc9000")
        version_config = self.config.get("picoquic", {}).get("versions", {}).get(version, {})

        # Determine if network interface parameters should be included based on environment
        include_interface = environment not in ["docker_compose"]

        # Build parameters for the command template
        params = {
            "binary": {
                "dir": version_config.get(role, {}).get("binary", {}).get("dir", "/opt/picoquic"),
                "name": version_config.get(role, {}).get("binary", {}).get("name", "./picoquicdemo"),
            },
            "initial_version": version_config.get(role, {}).get("initial_version", "00000001"),
            "protocol": {
                "alpn": version_config.get(role, {}).get("protocol", {}).get("alpn", {}),
                "additional_parameters": version_config.get(role, {}).get("protocol", {}).get("additional_parameters", ""),
            },
            "network": {
                "interface": version_config.get(role, {}).get("network", {}).get("interface", {}),
                "port": version_config.get(role, {}).get("network", {}).get("port", 4443),
                "destination": service_params.get("target", version_config.get(role, {}).get("network", {}).get("destination", "picoquic_server")),
            },
            "certificates": {
                "cert_param": version_config.get(role, {}).get("certificates", {}).get("cert", {}).get("param"),
                "cert_file": version_config.get(role, {}).get("certificates", {}).get("cert", {}).get("file"),
                "cert_local_file": version_config.get(role, {}).get("certificates", {}).get("cert", {}).get("local_file"),
                "key_param": version_config.get(role, {}).get("certificates", {}).get("key", {}).get("param"),
                "key_file": version_config.get(role, {}).get("certificates", {}).get("key", {}).get("file"),
                "key_local_file": version_config.get(role, {}).get("certificates", {}).get("key", {}).get("local_file"),
            },
            "ticket_file": {
                "param": version_config.get(role, {}).get("ticket_file", {}).get("param"),
                "file": version_config.get(role, {}).get("ticket_file", {}).get("file"),
                "local_file": version_config.get(role, {}).get("ticket_file", {}).get("local_file"),
            },
            "logging": version_config.get(role, {}).get("logging", {}),
        }

        # For the client, include target and message if available
        if role == "client":
            params["target"] = service_params.get("target")
            params["message"] = service_params.get("message")

        # Conditionally include network interface parameters
        if not include_interface:
            params["network"].pop("interface", None)

        # Collect volume mappings
        volumes = []
        # Only add certificate volumes if the user doesn't want to generate new certificates
        if not service_params.get('generate_new_certificates', False):
            # Certificates
            volumes.append({
                "local": os.path.abspath(params["certificates"]["cert_local_file"]),
                "container": params["certificates"]["cert_file"]
            })
            volumes.append({
                "local": os.path.abspath(params["certificates"]["key_local_file"]),
                "container": params["certificates"]["key_file"]
            })
        # Ticket file (if applicable)
        if params["ticket_file"]["local_file"]:
            volumes.append({
                "local": os.path.abspath(params["ticket_file"]["local_file"]),
                "container": params["ticket_file"]["file"]
            })


        # Render the appropriate template
        try:
            template_name = f"{role}_command.j2"
            self.logger.debug(f"Rendering command using template '{template_name}' with parameters: {params}")
            template = self.jinja_env.get_template(template_name)
            command = template.render(**params)

            # Clean up the command string
            command_str = command.replace('\t', ' ').replace('\n', ' ').strip()
            
            command_str = '"' + command_str + '"'

            # Create the command list
            working_dir = version_config.get(role, {}).get("binary", {}).get("dir", "/opt/picoquic")

            service_name = service_params.get("name")
            self.logger.debug(f"Generated command for '{service_name}': {command_str}")
            return {service_name: {"command": command_str, "volumes": volumes, "working_dir": working_dir}}
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