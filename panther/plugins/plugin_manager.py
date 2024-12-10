# PANTHER-SCP/panther/core/factories/plugin_manager.py

import importlib.util
import os
import logging
from pathlib import Path
from typing import Dict, Any, List
from core.observer.event_manager import EventManager
from config.config_experiment_schema import ServiceConfig, TestConfig
from plugins.protocols.config_schema import ProtocolConfig
from plugins.services.iut.config_schema import ImplementationConfig
from plugins.services.testers.tester_interface import ITesterManager
from plugins.services.services_interface import IServiceManager
from plugins.environments.network_environment.network_environment_interface import INetworkEnvironment
from plugins.environments.execution_environment.execution_environment_interface import IExecutionEnvironment
from plugins.services.iut.implementation_interface import IImplementationManager
from plugins.environments.environment_interface import IEnvironmentPlugin
from plugins.plugin_loader import PluginLoader

class PluginManager:
    def __init__(self, plugins_loader: PluginLoader):
        self.plugins_loader = plugins_loader
        self.logger = logging.getLogger("PluginManager")
        self.protocol_plugins: Dict[str, IServiceManager] = {}
        self.network_environment_plugins: Dict[str, INetworkEnvironment] = {}
        self.execution_environment_plugins: Dict[str, IExecutionEnvironment] = {}

    def create_service_manager(self, protocol: ProtocolConfig, 
                                     implementation: ImplementationConfig, 
                                     implementation_dir: Path,
                                     service_config_to_test: ServiceConfig) -> IServiceManager:
        """
        Creates an instance of a service manager based on the protocol and implementation names.

        :param protocol: Name of the protocol (e.g., 'quic').
        :param implementation: Name of the implementation (e.g., 'picoquic').
        :param implementation_dir: Path to the implementation plugin directory.
        :param protocol_templates_dir: Path to the protocol's templates directory.
        :return: An instance of IImplementationManager.
        """
        service_manager_path = implementation_dir / f"{implementation.name}.py"
        if not service_manager_path.exists():
            self.logger.error(f"Service manager file '{service_manager_path}' does not exist.")
            raise FileNotFoundError(f"Service manager file '{service_manager_path}' not found.")

        # Here we trying to load the service manager class from the implementation plugin
        service_module_name = f"{protocol.name}.{implementation.name}"
        spec = importlib.util.spec_from_file_location(service_module_name, service_manager_path)
        self.logger.debug(f"Loading module from '{service_manager_path}' as '{service_module_name}' with spec {spec}")
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            # We are trying to load the class from the module
            class_name = PluginLoader.get_class_name(implementation.name,suffix="ServiceManager")
            self.logger.debug(f"Loading class '{class_name}' from module '{module}'")
            service_manager_class = getattr(module, class_name, None)
            if service_manager_class and issubclass(service_manager_class, IServiceManager):
                # Less elegant way (than service_type = service_manager_class.service_type) 
                # to determine the service type BUT it works and no need to define property   
                service_type = "iut" if issubclass(service_manager_class, IImplementationManager) else "testers"       
                instance = service_manager_class(
                    service_config_to_test=service_config_to_test,
                    service_type=service_type,
                    protocol=protocol,
                    implementation_name=implementation.name,
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
    
    def create_environment_manager(self, environment: str, 
                                         service_managers: List[IServiceManager],
                                         test_config: TestConfig,
                                         environment_dir: Path, 
                                         output_dir: Path, 
                                         event_manager: EventManager) -> IEnvironmentPlugin:
        """
        Creates an instance of an environment manager based on the environment name.

        :param environment: Name of the environment (e.g., 'docker_compose').
        :param environment_dir: Path to the environment plugin directory.
        :return: An instance of IEnvironmentPlugin.
        """
        environment_plugin_path = environment_dir / environment / f"{environment}.py"
        if not environment_plugin_path.exists():
            self.logger.error(f"Environment plugin file '{environment_plugin_path}' does not exist.")
            raise FileNotFoundError(f"Environment plugin file '{environment_plugin_path}' not found.")

        # Here we trying to load the environment manager class from the environment plugin
        environment_module_name = f"environments.{environment}"
        spec = importlib.util.spec_from_file_location(environment_module_name, environment_plugin_path)
        self.logger.debug(f"Loading module from '{environment_plugin_path}' as '{environment_module_name}' with spec {spec}")
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            class_name = PluginLoader.get_class_name(environment,suffix="Environment")
            environment_class = getattr(module, class_name, None)
            if environment_class and issubclass(environment_class, IEnvironmentPlugin):
                
                environment_config_path = environment_dir / environment / "config.yaml"
                if not environment_config_path.exists():
                    self.logger.error(f"Environment configuration file '{environment_config_path}' does not exist.")
                    raise FileNotFoundError(f"Configuration file '{environment_config_path}' not found.")
                
                env_config = test_config.execution_environments if environment == "execution_environment" else test_config.network_environment
                instance = environment_class(
                    output_dir=str(output_dir),
                    env_config_to_test=env_config,
                    env_type=environment_dir.name,
                    env_sub_type=environment,
                    event_manager=event_manager,
                )
                self.logger.debug(f"Created instance of '{class_name}'")
                return instance
            else:
                self.logger.error(f"Environment class '{class_name}' not found or does not inherit from IEnvironmentPlugin.")
                raise AttributeError(f"Environment class '{class_name}' not found or invalid.")
        else:
            self.logger.error(f"Cannot load module from '{environment_plugin_path}'")
            raise ImportError(f"Cannot load module from '{environment_plugin_path}'")
        
    
