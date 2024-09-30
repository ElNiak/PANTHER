from abc import ABC, abstractmethod

class IProtocolPlugin(ABC):
    @abstractmethod
    def get_service_manager(self, implementation_name: str):
        """
        Returns an instance of the ServiceManager for the specified implementation.
        """
        pass
