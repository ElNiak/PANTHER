import os
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

from omegaconf import OmegaConf

from panther.core.command_processor.mixins import CommandEventMixin
from panther.core.docker_builder import DockerBuilder
from panther.core.docker_builder.plugin_mixin.docker_operations_mixin import (
    DockerOperationsMixin,
)

if TYPE_CHECKING:
    from panther.plugins.plugin_manager import PluginManager


class ServiceManagerDockerMixin(DockerOperationsMixin, CommandEventMixin):
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
        self.logger.debug(
            f"Preparing Docker environment for {self.__class__.__name__} with plugin_manager: {plugin_manager}"
        )
        if self._docker_prepared:
            self.logger.debug(
                f"Docker image already prepared for {self.__class__.__name__}"
            )
            return

        # Emit preparation started event
        self.notify_service_event(
            "preparation_started",
            service_id=getattr(self, "implementation_name", "unknown"),
            service_name=getattr(self, "service_name", "unknown"),
            details={
                "operation": "docker_build",
                "test_case": getattr(self, "_test_context", None)
                or getattr(self, "test_context", None)
                or "unknown_test",
            },
        )

        try:
            # Ensure Docker is available
            self.ensure_docker_available()

            # Use plugin_manager if available for service-specific builds
            # Build base image only once per experiment
            self._ensure_base_image_built(plugin_manager)
            # Build service-specific image
            self._generate_service_docker_image(plugin_manager)
            # Mark as prepared
            self._docker_prepared = True

            # # Initialize commands after Docker build if needed
            # if hasattr(self, "initialize_commands"):
            #     self.initialize_commands()

            # Emit preparation completed event
            self.notify_service_event(
                "preparation_completed",
                service_id=getattr(self, "implementation_name", "unknown"),
                service_name=getattr(self, "service_name", "unknown"),
                details={
                    "operation": "docker_build",
                    "test_case": getattr(self, "_test_context", None)
                    or getattr(self, "test_context", None)
                    or "unknown_test",
                },
            )

        except Exception as e:
            self.notify_service_event(
                "preparation_failed",
                service_id=getattr(self, "implementation_name", "unknown"),
                service_name=getattr(self, "service_name", "unknown"),
                details={
                    "operation": "docker_build",
                    "error": str(e),
                    "test_case": getattr(self, "_test_context", None)
                    or getattr(self, "test_context", None)
                    or "unknown_test",
                },
            )
            raise

    def _ensure_base_image_built(self, plugin_manager: "PluginManager") -> None:
        """
        Build base image only once per experiment session.

        Args:
            plugin_manager: Plugin manager for Docker operations
        """
        # with self._base_image_lock:
        #     if not self._base_image_built:
        # Check if base image already exists before building
        base_image_tag = "panther_base_service:latest"

        # Check if image exists using docker_builder
        docker_builder = DockerBuilder.get_instance(
            global_config=getattr(self, "global_config", None),
            experiment_context=getattr(plugin_manager, "experiment_context", None),
        )

        if (
            docker_builder.image_exists(base_image_tag)
            and not getattr(self, "global_config", None)
            or not getattr(self.global_config, "docker", None)
            or not getattr(self.global_config.docker, "force_build_docker_image", False)
        ):
            self.logger.info(
                f"Base Docker image '{base_image_tag}'  already exists, skipping build"
            )
            self._base_image_built = True
            return

        self.logger.info("Building base Docker image (once per experiment)")
        self.emit_docker_build_started(
            "panther/plugins/services/Dockerfile", "panther_base_service"
        )

        base_dockerfile = Path(
            os.path.join(os.getcwd(), "panther", "plugins", "services", "Dockerfile")
        )

        try:
            self.logger.debug(
                f"Using Dockerfile at {base_dockerfile} for base image build"
            )
            # Build the base image using correct parameters for build_image
            docker_builder.build_image(
                impl_name="panther_base_service",
                version="",
                dockerfile_path=base_dockerfile,
                context_path=base_dockerfile.parent,
                config={},
                tag_version="latest",
            )
            self._base_image_built = True
            self.emit_docker_build_completed("panther_base_service", True)
            self.logger.info("Base Docker image built successfully")
        except Exception as e:
            # For error case, emit failed event with proper parameters
            self.emit_docker_build_completed("panther_base_service", False)
            self.logger.error(f"Failed to build base Docker image: {str(e)}")
            raise

    def _generate_service_docker_image(self, plugin_manager: "PluginManager") -> None:
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
        commit = "master"
        dependencies = None

        if protocol_version:
            commit, dependencies = self.load_version_config()

        # Extract build_mode and runtime_mode for 3-stage architecture
        runtime_mode = "minimal"  # Default runtime mode

        if hasattr(self, "get_build_mode"):
            # Use the mixin's get_build_mode method if available (e.g., for IvyBuildModeMixin)
            build_mode = self.get_build_mode()
            self.logger.debug(f"Using build_mode from get_build_mode: '{build_mode}'")
        else:
            # Service do not implement get_build_mode, use default
            build_mode = ""
            self.logger.debug(
                f"No get_build_mode method found, using default build_mode: 'default'"
            )

        # Extract runtime_mode for 3-stage architecture support
        # First try to get from execution environment plugin
        runtime_mode = self._determine_runtime_mode_from_execution_environment()
        self.logger.debug(
            f"Auto-detected runtime_mode from execution environment: '{runtime_mode}'"
        )
        # Allow manual override if specified in config
        if (
            hasattr(self, "service_config_to_test")
            and hasattr(self.service_config_to_test, "plugin_config")
            and isinstance(self.service_config_to_test.plugin_config, dict)
            and "runtime_mode" in self.service_config_to_test.plugin_config
        ):
            override_mode = self.service_config_to_test.plugin_config["runtime_mode"]
            self.logger.debug(
                f"Overriding auto-detected runtime_mode '{runtime_mode}' with manual config: '{override_mode}'"
            )
            runtime_mode = override_mode
        elif (
            hasattr(self, "service_config_to_test")
            and hasattr(self.service_config_to_test, "implementation")
            and hasattr(self.service_config_to_test.implementation, "runtime_mode")
        ):
            if override_mode := getattr(
                self.service_config_to_test.implementation, "runtime_mode", None
            ):
                self.logger.debug(
                    f"Overriding auto-detected runtime_mode '{runtime_mode}' with implementation config: '{override_mode}'"
                )
                runtime_mode = override_mode
        elif hasattr(self, "service_config_to_test") and hasattr(
            self.service_config_to_test, "runtime_mode"
        ):
            override_mode = getattr(self.service_config_to_test, "runtime_mode", None)
            if override_mode:
                self.logger.debug(
                    f"Overriding auto-detected runtime_mode '{runtime_mode}' with service config: '{override_mode}'"
                )
                runtime_mode = override_mode

        # Use clean version (without build_mode suffix) - Docker builder will handle mode differentiation
        base_version = protocol_version or "latest"

        self.logger.debug(
            f"Preparing service {self.implementation_name} with version {base_version} (build_mode: '{build_mode}', runtime_mode: '{runtime_mode}')"
        )

        dockerfile_path = getattr(self, "docker_file_path", "Unknown")
        docker_builder = DockerBuilder.get_instance(
            global_config=getattr(self, "global_config", None),
            experiment_context=getattr(plugin_manager, "experiment_context", None),
        )

        # Generate expected image tag for checking if image exists
        # (Note: Docker builder will generate the actual tag during build)
        expected_image_tag = docker_builder.generate_image_tag(
            impl_name=self.implementation_name,
            version=base_version,
            tag_version="latest",
            build_mode=build_mode,
            runtime_mode=runtime_mode,
        )

        # Check if we should force build
        force_build = False
        if (
            hasattr(self, "global_config")
            and self.global_config
            and (hasattr(self.global_config, "docker") and self.global_config.docker)
        ):
            force_build = getattr(
                self.global_config.docker, "force_build_docker_image", False
            )
        self.logger.debug(
            f"Force build flag is set to {force_build} for service {self.implementation_name}"
        )
        if docker_builder.image_exists(expected_image_tag) and not force_build:
            self.logger.info(
                f"Service Docker image already exists, skipping build: {expected_image_tag}"
            )
            self.emit_docker_build_completed(expected_image_tag, True)
            return

        self.logger.info(f"Building service Docker image: {expected_image_tag}")

        self.emit_docker_build_started(str(dockerfile_path), expected_image_tag)

        try:
            if dependencies is not None:
                self.logger.debug(
                    f"Building service image {self.implementation_name} with dependencies: {dependencies}, commit: {commit}, and build_mode: '{build_mode}'"
                )
                version_dict = {
                    "dependencies": dependencies,
                    "version": base_version,
                    "commit": commit,
                    "build_mode": build_mode,
                    "runtime_mode": runtime_mode,
                }
            else:
                self.logger.debug(
                    f"Building service image {self.implementation_name} with version: {base_version} and build_mode: '{build_mode}'"
                )
                version_dict = {
                    "version": base_version,
                    "build_mode": build_mode,
                    "runtime_mode": runtime_mode,
                }

            self.logger.debug(
                f"Using version configuration for Docker build: {version_dict}"
            )

            # Use docker_builder from plugin_manager if available                # Get plugin information
            plugin_info = plugin_manager.get_plugin(self.implementation_name)
            if (
                not plugin_info
                or not hasattr(plugin_info, "path")
                or not plugin_info.path
            ):
                raise ValueError(
                    f"Could not find plugin directory for {self.implementation_name}"
                )

            plugin_dir = (
                Path(plugin_info.path).parent
                if Path(plugin_info.path).is_file()
                else Path(plugin_info.path)
            )
            dockerfile_path = plugin_dir / "Dockerfile"

            actual_image_tag = docker_builder.build_image(
                impl_name=self.implementation_name,
                version=base_version,
                dockerfile_path=dockerfile_path,
                context_path=plugin_dir,
                config=version_dict,
                tag_version="latest",
            )

            # Use the actual image tag returned by docker_builder (which includes modes)
            final_image_tag = actual_image_tag or expected_image_tag
            self.emit_docker_build_completed(final_image_tag, True)
            self.logger.info(
                f"Service Docker image {final_image_tag} built successfully"
            )
        except Exception as e:
            self.emit_docker_build_completed(expected_image_tag, False)
            self.logger.error(f"Failed to build service image: {str(e)}")
            raise

    def load_version_config(self):
        try:
            # Use direct access to service_config_to_test
            self.logger.debug(
                f"Using direct access to service_config_to_test for {self.implementation_name}"
            )
            if hasattr(self.service_config_to_test, "implementation") and hasattr(
                self.service_config_to_test.implementation, "version_config"
            ):
                if (
                    version_config := self.service_config_to_test.implementation.version_config
                ):
                    # Use summarizer for concise config logging
                    from panther.core.utils import log_omega_config_summary

                    log_omega_config_summary(
                        self.logger,
                        "Found version_config in service_config",
                        version_config,
                    )
                    commit = version_config.get("commit", "master")
                    dependencies = version_config.get("dependencies", [])
                    self.logger.debug(f"Extracted commit: {commit}")
                    self.logger.debug(f"Extracted dependencies: {dependencies}")
            else:
                self.logger.warning(
                    f"No version_config found in service_config_to_test for {self.implementation_name}"
                )
                raise ValueError(
                    f"Version configuration not found for {self.implementation_name}"
                )
        except Exception as e:
            self.logger.warning(
                f"Failed to load version config for {self.implementation_name}: {e}"
            )

        return commit, dependencies

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

    def _determine_runtime_mode_from_execution_environment(self) -> str:
        """
        Automatically determine runtime_mode based on execution environment plugin.

        Returns:
            str: Runtime mode (minimal, debug, profile) based on execution environment
        """
        try:
            # Get execution environment from test config
            execution_env_name = None
            if (
                hasattr(self, "service_config_to_test")
                and self.service_config_to_test
                and hasattr(self.service_config_to_test, "test_config")
            ):
                test_config = self.service_config_to_test.test_config
                if (
                    hasattr(test_config, "execution_environment")
                    and test_config.execution_environment
                ):
                    execution_env_name = getattr(
                        test_config.execution_environment, "env_sub_type", None
                    )

            if not execution_env_name:
                self.logger.debug(
                    "No execution environment found, using minimal runtime mode"
                )
                return "minimal"

            # Map execution environments to runtime modes based on their plugin declarations
            debug_environments = {"gdb", "helgrind", "memcheck"}
            profile_environments = {"gperf_cpu", "gperf_heap"}

            if execution_env_name in debug_environments:
                detected_mode = "debug"
                self.logger.debug(
                    f"Auto-detected runtime_mode '{detected_mode}' for debug environment: {execution_env_name}"
                )
                return detected_mode
            elif execution_env_name in profile_environments:
                detected_mode = "profile"
                self.logger.debug(
                    f"Auto-detected runtime_mode '{detected_mode}' for profiling environment: {execution_env_name}"
                )
                return detected_mode
            else:
                detected_mode = "minimal"
                self.logger.debug(
                    f"Auto-detected runtime_mode '{detected_mode}' for environment: {execution_env_name}"
                )
                return detected_mode

        except Exception as e:
            self.logger.debug(
                f"Error determining runtime mode from execution environment: {e}"
            )
            return "minimal"

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
