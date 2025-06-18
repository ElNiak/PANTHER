import os
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

from omegaconf import OmegaConf

from panther.core.command_processor.command_event_mixin import CommandEventMixin
from panther.core.docker_builder.docker_compose_operations_mixin import (
    DockerComposeOperationsMixin,
)

if TYPE_CHECKING:
    from panther.plugins.plugin_manager import PluginManager


class ServiceManagerDockerMixin(DockerComposeOperationsMixin, CommandEventMixin):
    """
    Complete Docker mixin for service managers.

    Combines all Docker-related functionality and integrates with
    the service manager patterns in PANTHER.

    Now unified to use only DockerBuilder for all Docker operations,
    eliminating the previous duplication between DockerUtils and DockerBuilder.
    """

    # Class-level tracking for base image to ensure it's built only once per experiment
    _base_image_built = False
    _base_image_lock = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize Docker-related attributes
        self._docker_prepared = False
        # Initialize CommandEventMixin
        CommandEventMixin.__init__(self)

        # Initialize lock if not done yet
        if ServiceManagerDockerMixin._base_image_lock is None:
            import threading

            ServiceManagerDockerMixin._base_image_lock = threading.Lock()

    def prepare(self, plugin_manager: Optional["PluginManager"] = None) -> None:
        """
        Unified prepare method using only DockerBuilder.

        This method now exclusively uses DockerBuilder for all Docker operations,
        eliminating the previous dual-path complexity.

        Args:
            plugin_manager: Optional plugin manager for Docker operations
        """
        if self._docker_prepared:
            self.logger.debug(
                f"Docker image already prepared for {self.__class__.__name__}"
            )
            return

        # Emit preparation started event
        self.notify_service_event("preparation_started", {"operation": "docker_build"})

        try:
            # Ensure Docker is available
            self.ensure_docker_available()

            # Use plugin_manager if available for service-specific builds
            if plugin_manager:
                # Build base image only once per experiment
                self._ensure_base_image_built(plugin_manager)
                # Build service-specific image
                self._build_service_image_with_plugin_manager(plugin_manager)
            else:
                # Use DockerBuilder directly
                self._build_with_docker_builder()

            # Mark as prepared
            self._docker_prepared = True

            # Initialize commands after Docker build if needed
            if hasattr(self, "initialize_commands"):
                self.initialize_commands()

            # Emit preparation completed event
            self.notify_service_event(
                "preparation_completed", {"operation": "docker_build"}
            )

        except Exception as e:
            self.notify_service_event(
                "preparation_failed", {"operation": "docker_build", "error": str(e)}
            )
            raise

    def _ensure_base_image_built(self, plugin_manager: "PluginManager") -> None:
        """
        Build base image only once per experiment session.

        Args:
            plugin_manager: Plugin manager for Docker operations
        """
        with self._base_image_lock:
            if not self._base_image_built:
                self.logger.info("Building base Docker image (once per experiment)")
                self.emit_docker_build_started(
                    "panther/plugins/services/Dockerfile", "panther_base"
                )

                base_dockerfile = Path(
                    os.path.join(
                        os.getcwd(), "panther", "plugins", "services", "Dockerfile"
                    )
                )

                try:
                    plugin_manager.build_docker_image_from_path(
                        base_dockerfile, "panther_base", "service"
                    )
                    self._base_image_built = True
                    self.emit_docker_build_completed("panther_base", True)
                    self.logger.info("Base Docker image built successfully")
                except Exception as e:
                    self.emit_docker_build_completed("panther_base", False, str(e))
                    raise

    def _build_service_image_with_plugin_manager(
        self, plugin_manager: "PluginManager"
    ) -> None:
        """
        Build service-specific image using plugin manager.

        Args:
            plugin_manager: Plugin manager for Docker operations
        """
        if not hasattr(self, "implementation_name"):
            self.logger.warning(
                "No implementation_name attribute, skipping service image build"
            )
            return
        
        

        # Get version from protocol, not implementation
        protocol_version = getattr(
            self.service_config_to_test.protocol, "version", None
        )
        
        # Load version configuration from YAML file
        version_config = None
        commit = "master"
        dependencies = None
        
        if protocol_version:
            try:
                # Construct path to version config file
                # For IUT: version_configs/{protocol_version}.yaml
                # For testers: version_configs/{protocol_name}/{protocol_version}.yaml
                import yaml
                
                service_type = getattr(self, 'service_type', 'iut')
                if isinstance(service_type, str):
                    service_type_lower = service_type.lower()
                else:
                    service_type_lower = service_type.name.lower()
                
                protocol_name = getattr(self.service_config_to_test.protocol, "name", "")
                
                if service_type_lower == "testers":
                    version_config_path = Path(__file__).parent.parent.parent / "plugins" / "services" / service_type_lower / self.implementation_name / "version_configs" / protocol_name / f"{protocol_version}.yaml"
                else:
                    version_config_path = Path(__file__).parent.parent.parent / "plugins" / "services" / service_type_lower / protocol_name / self.implementation_name / "version_configs" / f"{protocol_version}.yaml"
                
                self.logger.debug(f"Looking for version config at: {version_config_path}")
                
                if version_config_path.exists():
                    with open(version_config_path, 'r') as f:
                        loaded_config = yaml.safe_load(f)
                    
                    version_config = loaded_config
                    commit = loaded_config.get("commit", "master")
                    dependencies = loaded_config.get("dependencies", [])
                    
                    self.logger.debug(
                        f"Loaded version config for {self.implementation_name}: "
                        f"version={protocol_version}, commit={commit}, "
                        f"dependencies={dependencies}"
                    )
                else:
                    self.logger.warning(
                        f"Version config file not found: {version_config_path}"
                    )
            except Exception as e:
                self.logger.warning(
                    f"Failed to load version config for {self.implementation_name}: {e}"
                )
        
        # Use protocol version as the version string
        version = protocol_version if protocol_version else "latest"
        
        self.logger.debug(
            f"Preparing service {self.implementation_name} with version {version}"
        )

        # Use correct version for image name in logging and events
        image_name = f"{self.implementation_name}_{version}:latest"
        dockerfile_path = getattr(self, "docker_file_path", "Unknown")

        self.logger.info(f"Building service Docker image: {image_name}")
        self.emit_docker_build_started(str(dockerfile_path), image_name)

        try:
            if dependencies is not None:
                self.logger.debug(
                    f"Building service image {self.implementation_name} with dependencies: {dependencies} and commit: {commit}"
                )
                version_dict = {
                    "dependencies": dependencies,
                    "version": version,
                    "commit": commit,
                }
            else:
                self.logger.debug(
                    f"Building service image {self.implementation_name} with version: {version}"
                )
                version_dict = {"version": version}
            
            plugin_manager.build_docker_image(self.implementation_name, version_dict)
            self.emit_docker_build_completed(image_name, True)
            self.logger.info(f"Service Docker image {image_name} built successfully")
        except Exception as e:
            self.emit_docker_build_completed(image_name, False, str(e))
            raise

    def _build_with_docker_builder(self) -> None:
        """
        Build using DockerBuilder directly (unified approach).
        """
        self.logger.info("Building Docker image using DockerBuilder")
        self.prepare_docker_image()

    @classmethod
    def reset_base_image_flag(cls) -> None:
        """
        Reset base image flag for new experiment.

        This should be called at the start of each experiment to ensure
        the base image is built once for the new experiment.
        """
        cls._base_image_built = False

    def is_docker_prepared(self) -> bool:
        """
        Check if Docker preparation has been completed.

        Returns:
            bool: True if prepared
        """
        return self._docker_prepared

    def reset_docker_preparation(self) -> None:
        """
        Reset the Docker preparation state.

        Useful for forcing rebuild on next prepare() call.
        """
        self._docker_prepared = False

    def get_docker_run_command(
        self,
        command: Optional[str] = None,
        volumes: Optional[List[str]] = None,
        environment: Optional[Dict[str, str]] = None,
        ports: Optional[List[str]] = None,
        network: Optional[str] = None,
        name: Optional[str] = None,
        detach: bool = True,
        remove: bool = True,
    ) -> List[str]:
        """
        Generate a docker run command for this service.

        Args:
            command: Command to run in container
            volumes: Volume mappings
            environment: Environment variables
            ports: Port mappings
            network: Network to connect to
            name: Container name
            detach: Run in background
            remove: Remove container after exit

        Returns:
            list: Docker run command as list of arguments
        """
        if not hasattr(self, "docker_image_name"):
            raise AttributeError("docker_image_name must be set")

        cmd = ["docker", "run"]

        if detach:
            cmd.append("-d")
        if remove:
            cmd.append("--rm")

        if name:
            cmd.extend(["--name", name])
        elif hasattr(self, "service_name"):
            cmd.extend(["--name", self.service_name])

        if network:
            cmd.extend(["--network", network])

        # Add volumes
        for volume in volumes or getattr(self, "volumes", []):
            cmd.extend(["-v", volume])

        # Add environment variables
        env_vars = environment or getattr(self, "environments", {})
        for key, value in env_vars.items():
            cmd.extend(["-e", f"{key}={value}"])

        # Add ports
        for port in ports or getattr(self, "ports", []):
            cmd.extend(["-p", port])

        # Add image
        cmd.append(self.docker_image_name)

        # Add command if provided
        if command:
            cmd.extend(command.split() if isinstance(command, str) else command)

        return cmd
