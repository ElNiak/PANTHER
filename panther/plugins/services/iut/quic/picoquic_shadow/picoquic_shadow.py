# PANTHER-SCP/panther/plugins/services/implementations/picoquic_rfc9000/service_manager.py

import subprocess
import logging
import os
from typing import Any, Dict, Optional
import yaml
import traceback    
from config.config_experiment_schema import ServiceConfig
from plugins.services.iut.quic.picoquic_shadow.config_schema import PicoquicShadowConfig
from plugins.plugin_loader import PluginLoader
from plugins.services.iut.implementation_interface import IImplementationManager
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, Template

# TODO Tom create test template for QUIC implementations new users

class PicoquicShadowServiceManager(IImplementationManager):
    def __init__(
        self,
        service_config_to_test: PicoquicShadowConfig,
        service_type: str,
        protocol: str,
        implementation_name: str,
    ):
        super().__init__(service_config_to_test, service_type, protocol,implementation_name)
        
            
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
        return "picoquic_shadow"
    
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

        if not self.service_master_config:
            self.logger.error("Implementation configuration is empty.")
            raise ValueError("Empty implementation configuration.")
        # Additional validation can be implemented here
        # For example, check required keys are present
        required_keys = [['picoquic_shadow'], ['picoquic_shadow','versions']]
        for key in required_keys:
            if not keys_exists(self.service_master_config, key):
                self.logger.error(f"Missing required key '{key}' in configuration.")
                raise KeyError(f"Missing required key '{key}' in configuration.")
            
    def prepare(self,plugin_loader: Optional[PluginLoader] = None):
        """
        Prepare the service manager for use.
        """
        self.logger.info("Preparing picoquic_shadow service manager...")
        # Additional setup can be implemented here
        plugin_loader.build_docker_image(self.get_implementation_name())
        self.logger.info("PicoquicShadow service manager prepared.")

    def load_config(self) -> dict:
        """
        Loads the YAML configuration file.
        """
        config_file = Path(self.service_master_config_path)
        if not config_file.exists():
            self.logger.error(f"Configuration file '{self.service_master_config_path}' does not exist.")
            return {}
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            self.logger.info(f"Loaded configuration from '{self.service_master_config_path}'")
            return config
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}\n{traceback.format_exc()}")
            return {}

    def generate_deployment_commands(self, service_params: ServiceConfig, environment: str) -> Dict[str, Any]:
        """
        Generates deployment commands and collects volume mappings based on service parameters.

        :param service_params: Parameters specific to the service.
        :param environment: The environment in which the services are being deployed.
        :return: A dictionary with service name as key and a dictionary containing command and volumes.
        """
        self.logger.debug(f"Generating deployment commands for service: {service_params}")
        role =  service_params.protocol.role
        version =  service_params.protocol.version
        version_config = self.service_master_config.get("picoquic_shadow", {}).get("versions", {}).get(version, {})

        # Determine if network interface parameters should be included based on environment
        # TODO
        # include_interface = environment not in ["docker_compose"]
        include_interface = True

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
                "destination":  service_params.protocol.target,
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
        if not service_params.generate_new_certificates:
            # Certificates
            volumes.append({
                "local": os.path.abspath(params["certificates"]["cert_local_file"]),
                "container": params["certificates"]["cert_file"]
            })
            volumes.append({
                "local": os.path.abspath(params["certificates"]["key_local_file"]),
                "container": params["certificates"]["key_file"]
            })
        else:
            subprocess.run(["bash", 'generate_certificates.sh'])
        
        # Ticket file (if applicable)
        if params["ticket_file"]["local_file"]:
            volumes.append({
                "local": os.path.abspath(params["ticket_file"]["local_file"]),
                "container": params["ticket_file"]["file"]
            })


        # Render the appropriate template
        try:
            template_name = f"{role}_command.jinja"
            self.logger.debug(
                f"Rendering command using template '{template_name}' with parameters: {params}"
            )
            template = self.jinja_env.get_template(template_name)
            command = template.render(**params)

            # Clean up the command string
            command_str = command.replace("\t", " ").replace("\n", " ").strip()

            # Create the command list
            working_dir = (
                version_config.get(role, {})
                .get("binary", {})
                .get("dir", "/opt/picoquic")
            )

            ending_command = "cp /opt/picoquic/picoquicdemo /app/logs/picoquicdemo"

            service_name = service_params.get("name")
            self.logger.debug(f"Generated command for '{service_name}': {command_str}")
            return {
                service_name: {
                    "command_binary": version_config.get(role, {})
                                .get("binary", {})
                                .get("name", "./picoquicdemo"),
                    "args": command_str,
                    "volumes": volumes,
                    "working_dir": working_dir,
                    "environment": self.environments,
                    "ending_command": ending_command,
                }
            }
        except Exception as e:
            self.logger.error(
                f"Failed to render command for service '{service_params.get('name', 'unknown')}': {e}\n{traceback.format_exc()}"
            )
            raise e

    def __str__(self) -> str:
        return  f" (PicoquicShadow Service Manager - {self.service_master_config_path})"
    
    def __repr__(self):
        return super().__repr__() + f" (PicoquicShadow Service Manager - {self.service_master_config_path})"