"""
Environment Plugin Utilities

This module provides common utilities and mixins for environment plugins.
"""

import logging
from typing import Any
from pathlib import Path

from panther.core.utils.logging_mixin import LoggerMixin

logger = logging.getLogger(__name__)


class EnvironmentUtilities:
    """Common utility methods for environment plugins."""

    @staticmethod
    def standardize_environment_initialization(
        logger: logging.Logger, env_type: str, env_sub_type: str
    ) -> None:
        """
        Standardize initialization logging for environment plugins.

        Args:
            logger: Logger instance
            env_type: Type of environment (execution, network)
            env_sub_type: Sub-type of environment (docker_compose, strace, etc.)
        """
        logger.debug("Initializing %s environment plugin: %s", env_type, env_sub_type)

    @staticmethod
    def setup_output_directories(
        output_dir: str, env_sub_type: str, test_name: str | None = None
    ) -> dict[str, Path]:
        """
        Set up standard output directories for environment plugins.

        Args:
            output_dir: Base output directory
            env_sub_type: Environment sub-type
            test_name: Optional test name for nested directories

        Returns:
            dict: Dictionary of directory paths
        """
        base_path = Path(output_dir)

        if test_name:
            env_output_dir = base_path / test_name / env_sub_type
        else:
            env_output_dir = base_path / env_sub_type

        directories = {
            "base": base_path,
            "env_output": env_output_dir,
            "logs": env_output_dir / "logs",
            "results": env_output_dir / "results",
            "artifacts": env_output_dir / "artifacts",
        }

        # Ensure directories exist
        for dir_path in directories.values():
            dir_path.mkdir(parents=True, exist_ok=True)

        return directories


class EnvironmentPluginMixin(LoggerMixin):
    """
    Base mixin for environment plugins providing common functionality.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._environment_initialized = False
        self._output_directories = {}
        self._environment_state = "uninitialized"

    def standardized_environment_initialization(
        self,
        env_config_to_test: Any,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager=None,
    ) -> None:
        """
        Perform standardized environment plugin initialization.

        Args:
            env_config_to_test: Environment configuration
            output_dir: Output directory
            env_type: Environment type
            env_sub_type: Environment sub-type
            event_manager: Event manager instance
        """
        # Store basic attributes
        self.env_config_to_test = env_config_to_test
        self.output_dir = output_dir
        self.env_type = env_type
        self.env_sub_type = env_sub_type
        self.event_manager = event_manager

        # Set up output directories
        self._output_directories = EnvironmentUtilities.setup_output_directories(
            output_dir, env_sub_type
        )

        # Standard logging
        EnvironmentUtilities.standardize_environment_initialization(
            self.logger, env_type, env_sub_type
        )

        self._environment_initialized = True
        self._environment_state = "initialized"

    @property
    def environment_state(self) -> str:
        """Get the current environment state."""
        return self._environment_state

    @property
    def output_directories(self) -> dict[str, Path]:
        """Get the output directories."""
        return self._output_directories

    def get_logs_directory(self) -> Path:
        """Get the logs directory path."""
        return self._output_directories.get("logs", Path(self.output_dir) / "logs")

    def get_results_directory(self) -> Path:
        """Get the results directory path."""
        return self._output_directories.get("results", Path(self.output_dir) / "results")

    def get_artifacts_directory(self) -> Path:
        """Get the artifacts directory path."""
        return self._output_directories.get("artifacts", Path(self.output_dir) / "artifacts")

    def update_environment_state(self, new_state: str) -> None:
        """
        Update the environment state.

        Args:
            new_state: New state value
        """
        old_state = self._environment_state
        self._environment_state = new_state
        self.logger.debug(f"Environment state changed: {old_state} -> {new_state}")


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
        services_managers: list[Any],
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
        self.logger.info(f"Setting up execution environment with {len(services_managers)} services")
        self.log_operation_start(
            "execution environment setup", service_count=len(services_managers)
        )

    def get_service_managers(self) -> list[Any]:
        """Get the list of service managers."""
        return self.services_managers

    def get_service_manager_by_name(self, name: str) -> Any | None:
        """
        Get a service manager by name.

        Args:
            name: Service manager name

        Returns:
            Service manager instance or None
        """
        for service_manager in self.services_managers:
            if hasattr(service_manager, "service_name") and service_manager.service_name == name:
                return service_manager
            elif (
                hasattr(service_manager, "implementation_name")
                and service_manager.implementation_name == name
            ):
                return service_manager
        return None


class NetworkEnvironmentMixin(EnvironmentPluginMixin):
    """
    Specialized mixin for network environment plugins.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._network_config = {}
        self._deployment_artifacts = []

    def setup_network_environment(self, network_config: dict[str, Any]) -> None:
        """
        Set up network environment with network configuration.

        Args:
            network_config: Network configuration parameters
        """
        self._network_config = network_config
        self.update_environment_state("network_setup_in_progress")

        self.logger.info("Setting up network environment")
        self.log_operation_start(
            "network environment setup", config_keys=list(network_config.keys())
        )

    @property
    def network_config(self) -> dict[str, Any]:
        """Get the network configuration."""
        return self._network_config

    def add_deployment_artifact(self, artifact_path: str, artifact_type: str = "file") -> None:
        """
        Add a deployment artifact for tracking.

        Args:
            artifact_path: Path to the artifact
            artifact_type: Type of artifact (file, directory, etc.)
        """
        self._deployment_artifacts.append(
            {
                "path": artifact_path,
                "type": artifact_type,
                "created_at": self.timestamp if hasattr(self, "timestamp") else None,
            }
        )

    def get_deployment_artifacts(self) -> list[dict[str, Any]]:
        """Get the list of deployment artifacts."""
        return self._deployment_artifacts.copy()

    def cleanup_deployment_artifacts(self) -> None:
        """Clean up deployment artifacts."""
        cleaned_count = 0
        for artifact in self._deployment_artifacts:
            try:
                artifact_path = Path(artifact["path"])
                if artifact_path.exists():
                    if artifact["type"] == "directory":
                        import shutil

                        shutil.rmtree(artifact_path)
                    else:
                        artifact_path.unlink()
                    cleaned_count += 1
            except Exception as e:
                self.logger.warning(f"Failed to cleanup artifact {artifact['path']}: {e}")

        self.logger.info(f"Cleaned up {cleaned_count} deployment artifacts")
        self._deployment_artifacts.clear()


class DockerEnvironmentMixin(NetworkEnvironmentMixin):
    """
    Specialized mixin for Docker-based environment plugins.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._docker_compose_file = None
        self._container_names = []
        self._volumes = []
        self._networks = []

    def setup_docker_environment(
        self,
        compose_file_path: str | None = None,
        containers: list[str] | None = None,
        volumes: list[str] | None = None,
        networks: list[str] | None = None,
    ) -> None:
        """
        Set up Docker-specific environment attributes.

        Args:
            compose_file_path: Path to docker-compose file
            containers: List of container names
            volumes: List of volume names
            networks: List of network names
        """
        self._docker_compose_file = compose_file_path
        self._container_names = containers or []
        self._volumes = volumes or []
        self._networks = networks or []

        self.update_environment_state("docker_setup_in_progress")

        self.logger.info(
            f"Setting up Docker environment with {len(self._container_names)} containers"
        )

    @property
    def docker_compose_file(self) -> str | None:
        """Get the Docker Compose file path."""
        return self._docker_compose_file

    @property
    def container_names(self) -> list[str]:
        """Get the list of container names."""
        return self._container_names.copy()

    @property
    def volumes(self) -> list[str]:
        """Get the list of volume names."""
        return self._volumes.copy()

    @property
    def networks(self) -> list[str]:
        """Get the list of network names."""
        return self._networks.copy()

    def add_container(self, container_name: str) -> None:
        """Add a container name to tracking."""
        if container_name not in self._container_names:
            self._container_names.append(container_name)

    def add_volume(self, volume_name: str) -> None:
        """Add a volume name to tracking."""
        if volume_name not in self._volumes:
            self._volumes.append(volume_name)

    def add_network(self, network_name: str) -> None:
        """Add a network name to tracking."""
        if network_name not in self._networks:
            self._networks.append(network_name)
