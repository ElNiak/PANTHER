import shutil
from pathlib import Path
from typing import Any, Dict, List

from panther.plugins.environments.environment_plugin_mixin import EnvironmentPluginMixin


class NetworkEnvironmentMixin(EnvironmentPluginMixin):
    """
    Specialized mixin for network environment plugins.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._network_config = {}
        self._deployment_artifacts = []

    def setup_network_environment(self, network_config: Dict[str, Any]) -> None:
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
    def network_config(self) -> Dict[str, Any]:
        """Get the network configuration."""
        return self._network_config

    def add_deployment_artifact(
        self, artifact_path: str, artifact_type: str = "file"
    ) -> None:
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

    def get_deployment_artifacts(self) -> List[Dict[str, Any]]:
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
                self.logger.warning(
                    f"Failed to cleanup artifact {artifact['path']}: {e}"
                )

        self.logger.info(f"Cleaned up {cleaned_count} deployment artifacts")
        self._deployment_artifacts.clear()
