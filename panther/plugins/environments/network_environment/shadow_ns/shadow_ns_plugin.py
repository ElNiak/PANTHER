import os
import subprocess
import logging
from typing import Dict, Any
import yaml
from core.interfaces.environments.network_environment_interface import INetworkEnvironment

class ShadowNSEnvironment(INetworkEnvironment):
    def __init__(self):
        self.logger = logging.getLogger("ShadowNSEnvironment")
        self.services_network_config_file_path = os.path.join(os.getcwd(), "plugins", "environments","network_environment" ,"shadow", "shadow.generated.yml")
        self.network_name = "quic_network_dynamic"
    
    def configure_network(self, services: Dict[str, Dict[str, Any]]):
        """
        Generates a shadow.yml file dynamically based on the provided services.
        :param services: A dictionary mapping service names to their configurations.
        """
        self.logger.info("Generating dynamic shadow.yml")
        shadow_dict = {
            'version': '3.8',
            'services': {},
            'networks': {
                self.network_name: {
                    'driver': 'bridge'
                }
            }
        }
        
        for service_name, config in services.items():
            image = config.get('image')
            ports = config.get('ports', [])
            depends_on = config.get('depends_on', [])
            environment_vars = config.get('environment', {})
            
            service_def = {
                'image': image,
                'container_name': service_name,
                'ports': ports,
                'networks': [self.network_name],
                'logging': {
                    'driver': "json-file",
                    'options': {
                        'max-size': "10m",
                        'max-file': "3"
                    }
                },
                'restart': 'always'
            }
            
            if depends_on:
                service_def['depends_on'] = depends_on
            
            if environment_vars:
                service_def['environment'] = environment_vars
            
            shadow_dict['services'][service_name] = service_def
        
        with open(self.services_network_config_file_path, 'w') as shadow_file:
            yaml.dump(shadow_dict, shadow_file)
        
        self.logger.info(f"Shadow NS file generated at '{self.services_network_config_file_path}'")
    
    def setup_environment(self, services: Dict[str, Dict[str, Any]]):
        """
        Sets up the Shadow NS environment by generating the shadow file and bringing up services.
        :param services: A dictionary mapping service names to their configurations.
        """
        self.configure_network(services)
        
        self.logger.info("Starting Shadow NS services")
        try:
            subprocess.run(
                ["shadow", "-f", self.services_network_config_file_path, "up", "-d"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.logger.info("Shadow NS services started successfully")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to start Shadow NS services: {e.stderr.decode()}")
            raise e
    
    def teardown_environment(self):
        """
        Tears down the Shadow NS environment by bringing down services.
        """
        self.logger.info("Tearing down Shadow NS environment")
        try:
            subprocess.run(
                ["shadow", "-f", self.services_network_config_file_path, "down"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.logger.info("Shadow NS environment torn down successfully")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to tear down Shadow NS environment: {e.stderr.decode()}")
            raise e
