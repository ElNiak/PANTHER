from abc import ABC, abstractmethod
import logging
import os
from pathlib import Path
import traceback
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader
from omegaconf import OmegaConf
import yaml

from config.config_experiment_schema import ServiceConfig
from plugins.protocols.config_schema import ProtocolConfig
from plugins.plugin_loader import PluginLoader
from plugins.plugin_interface import IPlugin


class IServiceManager(IPlugin):
    def __init__(
        self,
        service_config_to_test: ServiceConfig,
        service_type: str,
        protocol: ProtocolConfig,
        implementation_name: str,
    ):
        super().__init__()

        self.available_types = ["testers", "iut"]
        self.service_type = service_type
        assert (
            self.service_type in self.available_types
        ), f"Invalid service type: {self.service_type}"

        if self.service_type == "testers":
            self.service_config_to_test_path = (
                f"plugins/services/{service_type}/{implementation_name}/config.yaml"
            )
            self.templates_dir = (
                f"plugins/services/{service_type}/{implementation_name}/templates/"
            )
            self.config_versions_dir = f"plugins/services/{service_type}/{implementation_name}/version_configs/"
        else:
            self.service_config_to_test_path = f"plugins/services/{service_type}/{protocol.name}/{implementation_name}/config.yaml"
            self.templates_dir = f"plugins/services/{service_type}/{protocol.name}/{implementation_name}/templates/"
            self.config_versions_dir = f"plugins/services/{service_type}/{protocol.name}/{implementation_name}/version_configs/"

        if not os.path.isdir(self.templates_dir):
            self.logger.error(
                f"Templates directory '{self.templates_dir}' does not exist."
            )
        else:
            templates = os.listdir(self.templates_dir)
            self.logger.debug(
                f"Available templates in '{self.templates_dir}': {templates}"
            )

        self.plugin_loader = None

        # The service master configuration represents the configuration file for the service defined by the plugin itself
        self.service_config_to_test = service_config_to_test

        self.jinja_env = Environment(loader=FileSystemLoader(self.templates_dir))
        self.jinja_env.filters["realpath"] = lambda x: os.path.abspath(x)
        self.jinja_env.filters["is_dict"]  = lambda x: isinstance(x, dict)
        self.jinja_env.trim_blocks = True
        self.jinja_env.lstrip_blocks = True

        # Service-specific attributes
        # Some attributes are set by the plugin loader, others are set by the plugin itself and the experiment manager
        self.implementation_name = implementation_name
        self.service_name     = service_config_to_test.name
        self.service_protocol = protocol
        self.service_targets = "" if not self.service_config_to_test.protocol.target else self.service_config_to_test.protocol.target
        self.service_version = self.service_config_to_test.protocol.version
        self.working_dir = None
        self.process = None
        self.available_roles = []
        self.volumes = []
        self.role = self.service_config_to_test.protocol.role
        self.environments = {}

        self.run_cmd = {
            "pre_compile_cmds": [],
            "compile_cmds": [],
            "pre_run_cmds": [],
            "run_cmd": {"command_binary": "", "command_args": "", "timeout": 60},
            "post_run_cmds": [],
        }

    def initialize_commands(self):
        """
        Initializes the commands to be executed
        """
        self.run_cmd = {
            "pre_compile_cmds": self.generate_pre_compile_commands(),
            "compile_cmds": self.generate_compile_commands(),
            "pre_run_cmds": self.generate_pre_run_commands(),
            "run_cmd": self.generate_run_command(),
            "post_run_cmds": self.generate_post_run_commands(),
        }
        self.logger.debug(f"Run commands: {self.run_cmd}")

    def generate_pre_compile_commands(self):
        """
        Generates pre-compile commands. (Not installation requirements <!> This part is handled by the Dockerfile)
        """
        return [
            "set -x;",
            "export PATH=$$PATH:$$ADDITIONAL_PATH;",
            "export PYTHONPATH=$$PYTHONPATH:$$ADDITIONAL_PYTHONPATH;",
            "env >> /app/logs/ivy_setup.log;",
        ]

    def generate_compile_commands(self):
        """
        Generates compile commands.
        """
        return []

    def generate_pre_run_commands(self):
        """
        Generates pre-run commands.
        """
        return []

    def generate_run_command(self):
        """
        Generates the run command.
        Must be in the form:
        {
            "command_binary": "",
            "command_args":   "",
            "timeout": 60
        }
        """
        return {
            "command_binary": "",
            "command_args": "",
            "timeout": self.service_config_to_test.timeout,
        }

    def generate_post_run_commands(self):
        """
        Generates post-run commands.
        """
        return []
    
    def get_implementation_name(self) -> str:
        return self.implementation_name

    def is_tester(self):
        """
        Returns True if the plugin is a network service.
        """
        return self.service_type == "testers"

    @abstractmethod
    def get_base_url(self, service_name: str) -> str:
        """
        Returns the base URL for the given service.
        """
        raise NotImplementedError(
            "Method 'get_base_url' must be implemented in subclasses."
        )

    @abstractmethod
    def prepare(self, plugin_loader: Optional[PluginLoader] = None):
        """
        Builds the Docker image for the implementation based on the environment.

        :param environment: The name of the environment (e.g., 'docker_compose', 'shadow_ns').
        """
        pass

    @abstractmethod
    def generate_deployment_commands(
        self, service_params: ServiceConfig, environment: str
    ) -> Dict[str, str]:
        """
        Generates deployment commands based on service parameters.

        :param service_params: Parameters specific to the service.
        :return: A dictionary mapping service names to their respective command strings.
        """
        pass
    
    
