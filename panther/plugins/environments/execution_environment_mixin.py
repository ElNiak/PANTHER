from typing import Any, List, Optional

from panther.plugins.environments.environment_plugin_mixin import EnvironmentPluginMixin


class ExecutionEnvironmentMixin(EnvironmentPluginMixin):
    """
    Specialized mixin for execution environment plugins.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.services_managers = []
        self.test_config = None
        self.global_config = None
        self.plugin_manager = None
        self.timestamp = None

    def setup_execution_environment(
        self,
        services_managers: List[Any],
        test_config: Any,
        global_config: Any,
        timestamp: str,
        plugin_manager: Any,
    ) -> None:
        """
        Set up execution environment with service managers and configurations.

        Args:
            services_managers: List of service managers
            test_config: Test configuration
            global_config: Global configuration
            timestamp: Execution timestamp
            plugin_manager: Plugin loader instance
        """
        self.services_managers = services_managers
        self.test_config = test_config
        self.global_config = global_config
        self.timestamp = timestamp
        self.plugin_manager = plugin_manager

        self.update_environment_state("setup_in_progress")

        # Log setup information
        self.logger.info(
            f"Setting up execution environment with {len(services_managers)} services"
        )
        self.log_operation_start(
            "execution environment setup", service_count=len(services_managers)
        )

    def get_service_managers(self) -> List[Any]:
        """Get the list of service managers."""
        return self.services_managers

    def get_service_manager_by_name(self, name: str) -> Optional[Any]:
        """
        Get a service manager by name.

        Args:
            name: Service manager name

        Returns:
            Service manager instance or None
        """
        for service_manager in self.services_managers:
            if (
                hasattr(service_manager, "service_name")
                and service_manager.service_name == name
            ):
                return service_manager
            elif (
                hasattr(service_manager, "implementation_name")
                and service_manager.implementation_name == name
            ):
                return service_manager
        return None
