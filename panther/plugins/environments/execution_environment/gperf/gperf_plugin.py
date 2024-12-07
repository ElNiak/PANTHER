import os
import logging
from pathlib import Path
from typing import Dict, Any

from jinja2 import Environment, FileSystemLoader
from plugins.environments.execution_environment.execution_environment_interface import IExecutionEnvironment

class GperfEnvironment(IExecutionEnvironment):
    def __init__(
        self,
        config_path: str,
        output_dir: str,
        environment_settings: Dict[str,Any],
        type: str,
        sub_type: str,
    ):
        super().__init__(config_path, output_dir, environment_settings, type, sub_type)
        self.logger = logging.getLogger("GPerfEnvironment")
        self.services_network_config_file_path = os.path.join(
            os.getcwd(),
            "plugins",
            "environments",
            "network_environment",
            "docker_compose",
            "docker-compose.generated.yml",
        )
        self.config_path = config_path
        self.network_name = "quic_network_dynamic"
        self.output_dir = output_dir
        self.log_dirs = os.path.join(self.output_dir, "logs")
        self.rendered_docker_compose_path = os.path.join(
            self.output_dir, "docker-compose.yml"
        )
        self.compose_file_path = Path(self.services_network_config_file_path)
        self.services = {}
        self.deployment_commands = {}
        self.environment_settings = environment_settings
        self.timeout = 60
        self.jinja_env = Environment(loader=FileSystemLoader(self.templates_dir))
        self.jinja_env.filters['realpath'] = lambda x: os.path.abspath(x)
        self.jinja_env.filters['is_dict']  = lambda x: isinstance(x, dict)
        self.jinja_env.trim_blocks   = True
        self.jinja_env.lstrip_blocks = True
        
        self.source_dir = "/opt/panther"
    
    def setup_environment(self, services: Dict[str, Dict[str, Any]]):
        raise NotImplementedError
    
    def teardown_environment(self):
        raise NotImplementedError
