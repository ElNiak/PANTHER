# PANTHER-SCP/panther/core/factories/plugin_manager.py

import importlib.util
import os
import logging
from pathlib import Path
from typing import Dict, Any, List
from plugins.services.testers.tester_interface import ITesterManager
from plugins.services.services_interface import IServiceManager
from plugins.environments.network_environment.network_environment_interface import INetworkEnvironment
from plugins.environments.execution_environment.execution_environment_interface import IExecutionEnvironment
from plugins.services.implementations.implementation_interface import IImplementationManager
from plugins.environments.environment_interface import IEnvironmentPlugin
from plugins.plugin_loader import PluginLoader

class PluginManager:
    def __init__(self, plugins_loader: PluginLoader):
        self.plugins_loader = plugins_loader
        self.logger = logging.getLogger("PluginManager")
        self.protocol_plugins: Dict[str, IServiceManager] = {}
        self.network_environment_plugins: Dict[str, INetworkEnvironment] = {}
        self.execution_environment_plugins: Dict[str, IExecutionEnvironment] = {}

    def create_service_manager(self, protocol: str, implementation: str, 
                               implementation_dir: Path, protocol_templates_dir: Path) -> IServiceManager:
        """
        Creates an instance of a service manager based on the protocol and implementation names.

        :param protocol: Name of the protocol (e.g., 'quic').
        :param implementation: Name of the implementation (e.g., 'picoquic').
        :param implementation_dir: Path to the implementation plugin directory.
        :param protocol_templates_dir: Path to the protocol's templates directory.
        :return: An instance of IImplementationManager.
        """
        service_manager_path = implementation_dir / f"{implementation}.py"
        if not service_manager_path.exists():
            self.logger.error(f"Service manager file '{service_manager_path}' does not exist.")
            raise FileNotFoundError(f"Service manager file '{service_manager_path}' not found.")

        module_name = f"{protocol}.{implementation}.{implementation}"
        spec = importlib.util.spec_from_file_location(module_name, service_manager_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            class_name = f'{implementation.replace("_", " ").title()}ServiceManager'.replace(" ", "")
            service_manager_class = getattr(module, class_name, None)
            if service_manager_class and \
                    (issubclass(service_manager_class, IImplementationManager) or issubclass(service_manager_class, ITesterManager)):
                implementation_config_path = implementation_dir / "config.yaml"
                if not implementation_config_path.exists():
                    self.logger.error(f"Implementation configuration file '{implementation_config_path}' does not exist.")
                    raise FileNotFoundError(f"Configuration file '{implementation_config_path}' not found.")
                instance = service_manager_class(
                    type="implementations" if issubclass(service_manager_class, IImplementationManager) else "testers",
                    protocol=protocol,
                    implementation_name=implementation,
                )
                self.logger.debug(f"Preparing instance of '{class_name}'")
                instance.prepare(self.plugins_loader)
                self.logger.debug(f"Created instance of '{class_name}'")
                return instance
            else:
                self.logger.error(f"Service manager class '{class_name}' not found or does not inherit from IImplementationManager.")
                raise AttributeError(f"Service manager class '{class_name}' not found or invalid.")
        else:
            self.logger.error(f"Cannot load module from '{service_manager_path}'")
            raise ImportError(f"Cannot load module from '{service_manager_path}'")
    
    def create_environment_manager(self, environment: str, environment_settings: Dict[str,Any],
                                   environment_dir: Path, output_dir: Path) -> IEnvironmentPlugin:
        """
        Creates an instance of an environment manager based on the environment name.

        :param environment: Name of the environment (e.g., 'docker_compose').
        :param environment_dir: Path to the environment plugin directory.
        :return: An instance of IEnvironmentPlugin.
        """
        environment_plugin_path = environment_dir / environment / f"{environment}_plugin.py"
        if not environment_plugin_path.exists():
            self.logger.error(f"Environment plugin file '{environment_plugin_path}' does not exist.")
            raise FileNotFoundError(f"Environment plugin file '{environment_plugin_path}' not found.")

        module_name = f"environments.{environment}.environment_plugin"
        spec = importlib.util.spec_from_file_location(module_name, environment_plugin_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            class_name_parts = environment.split("_")
            class_name_parts = [part.capitalize() for part in class_name_parts]
            class_name = "".join(class_name_parts) + "Environment"
            environment_class = getattr(module, class_name, None)
            if environment_class and issubclass(environment_class, IEnvironmentPlugin):
                environment_config_path = environment_dir / environment / "config.yaml"
                if not environment_config_path.exists():
                    self.logger.error(f"Environment configuration file '{environment_config_path}' does not exist.")
                    raise FileNotFoundError(f"Configuration file '{environment_config_path}' not found.")
                instance = environment_class(
                    config_path=str(environment_config_path),
                    output_dir=str(output_dir),
                    environment_settings=environment_settings,
                    type=environment_dir.name,
                    sub_type=environment
                )
                self.logger.debug(f"Created instance of '{class_name}'")
                return instance
            else:
                self.logger.error(f"Environment class '{class_name}' not found or does not inherit from IEnvironmentPlugin.")
                raise AttributeError(f"Environment class '{class_name}' not found or invalid.")
        else:
            self.logger.error(f"Cannot load module from '{environment_plugin_path}'")
            raise ImportError(f"Cannot load module from '{environment_plugin_path}'")
        
    
