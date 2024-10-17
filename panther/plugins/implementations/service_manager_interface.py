from abc import ABC, abstractmethod
from typing import Any, Dict

class IServiceManager(ABC):
    def __init__(self):
        pass
    
    @abstractmethod
    def get_base_url(self, service_name: str) -> str:
        """
        Returns the base URL for the given service.
        """
        raise NotImplementedError("Method 'get_base_url' must be implemented in subclasses.")
    
    @abstractmethod
    def get_implementation_name(self) -> str:
        """
        Returns the name of the implementation.

        :return: Implementation name as a string.
        """
        pass
    
    @abstractmethod
    def build_image(self, environment: str):
        """
        Builds the Docker image for the implementation based on the environment.
        
        :param environment: The name of the environment (e.g., 'docker_compose', 'shadow_ns').
        """
        pass 
    
    @abstractmethod
    def generate_deployment_commands(self, service_params: Dict[str, Any], environment:str) -> Dict[str, str]:
        """
        Generates deployment commands based on service parameters.

        :param service_params: Parameters specific to the service.
        :return: A dictionary mapping service names to their respective command strings.
        """
        pass
    
    @abstractmethod
    def start_service(self, service_name: str, command: str):
        """
        Starts the service using the provided command.

        :param service_name: Name of the service.
        :param command: Command string to start the service.
        """
        pass

    @abstractmethod
    def stop_service(self, service_name: str):
        """
        Stops the service gracefully.

        :param service_name: Name of the service.
        """
        pass