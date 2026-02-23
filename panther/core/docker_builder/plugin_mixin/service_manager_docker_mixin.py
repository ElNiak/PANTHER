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

        # Determine runtime mode for base image
        runtime_mode = self._determine_runtime_mode_from_execution_environment(
            plugin_manager
        )

        self.logger.debug(
            f"Ensuring base Docker image is built with runtime_mode='{runtime_mode}' and global_config='{getattr(self, 'global_config', None)}'"
        )
        # Build base image tag using docker_builder's tag generation logic
        docker_builder = DockerBuilder.get_instance(
            global_config=getattr(self, "global_config", None),
            experiment_context=getattr(plugin_manager, "experiment_context", None),
        )

        # Use docker_builder's tag generation for consistency
        base_image_tag = docker_builder.generate_image_tag(
            impl_name="panther_base_service",
            version="",
            tag_version="latest",
            build_mode="",  # Base image uses default build mode
            runtime_mode=runtime_mode,
            target_platform=docker_builder.get_target_platform(),
        )

        force_build = False
        if (
            hasattr(self, "global_config")
            and self.global_config
            and hasattr(self.global_config, "docker")
            and self.global_config.docker
        ):
            force_build = getattr(
                self.global_config.docker, "force_build_docker_image", False
            )

        if docker_builder.image_exists(base_image_tag) and (
            not force_build or DockerBuilder.was_built_this_session(base_image_tag)
        ):
            # Verify with direct Docker API (same as Fix 7)
            try:
                docker_builder.client.images.get(base_image_tag)
                self.logger.info(
                    f"Base Docker image verified and exists, skipping build: {base_image_tag}"
                )
                self._base_image_built = True
                return
            except Exception:
                self.logger.warning(
                    f"Cache reported base image exists but Docker API verification failed for "
                    f"'{base_image_tag}', proceeding with build"
                )
                docker_builder.image_cache.invalidate_cache()

        self.logger.info(
            f"Building base Docker image with runtime_mode='{runtime_mode}' (once per experiment)"
        )
        self.emit_docker_build_started(
            "panther/plugins/services/Dockerfile",
            f"panther_base_service_{runtime_mode}"
            if runtime_mode != "minimal"
            else "panther_base_service",
        )

        # Select appropriate Dockerfile based on BuildKit availability
        services_dir = Path(os.path.join(os.getcwd(), "panther", "plugins", "services"))
        base_dockerfile = self._select_optimal_dockerfile(services_dir)

        try:
            self.logger.debug(
                f"Using Dockerfile at {base_dockerfile} for base image build with runtime_mode='{runtime_mode}'"
            )

            # Set current dockerfile path for BuildKit detection
            docker_builder._current_dockerfile_path = base_dockerfile

            # Build the base image using correct parameters for build_image with runtime mode
            docker_builder.build_image(
                impl_name="panther_base_service",
                version="",
                dockerfile_path=base_dockerfile,
                context_path=base_dockerfile.parent,
                config={
                    "build_mode": "",  # Base image uses default build mode
                    "runtime_mode": runtime_mode,
                },  # Pass both modes to ensure consistent tag generation
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
            # Use the service's get_build_mode method if available
            build_mode = self.get_build_mode()
            self.logger.debug(f"Using build_mode from get_build_mode: '{build_mode}'")
        else:
            # Service do not implement get_build_mode, use default
            build_mode = ""
            self.logger.debug(
                "No get_build_mode method found, using default build_mode: 'default'"
            )

        # Extract z3_source for Z3 build strategy (local submodule vs pip)
        z3_source = "local"  # Default: build from submodule
        if hasattr(self, "get_z3_source"):
            z3_source = self.get_z3_source()
            self.logger.debug(f"Using z3_source from get_z3_source: '{z3_source}'")

        # Extract runtime_mode for 3-stage architecture support
        # First try to get from execution environment plugin
        runtime_mode = self._determine_runtime_mode_from_execution_environment(
            plugin_manager
        )
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
            if override_mode := getattr(
                self.service_config_to_test, "runtime_mode", None
            ):
                self.logger.debug(
                    f"Overriding auto-detected runtime_mode '{runtime_mode}' with service config: '{override_mode}'"
                )
                runtime_mode = override_mode

        # Use clean version (without build_mode suffix) - Docker builder will handle mode differentiation
        base_version = protocol_version or "latest"
        
        gc = getattr(self, "global_config", None)

        # Resolve per-service docker overrides
        from panther.config.core.models.global_config import resolve_docker_build_config

        service_docker_override = getattr(
            self.service_config_to_test, "docker", None
        )
        resolved_docker = None
        if gc and hasattr(gc, "docker") and gc.docker:
            resolved_docker = resolve_docker_build_config(
                gc.docker, service_docker_override
            )

        self.logger.debug(
            f"Preparing service {self.implementation_name} with version {base_version} (build_mode: '{build_mode}', runtime_mode: '{runtime_mode}' and global config: '{gc}' )"
        )

        dockerfile_path = getattr(self, "docker_file_path", "Unknown")
        docker_builder = DockerBuilder.get_instance(
            global_config=gc,
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
            target_platform=docker_builder.get_target_platform(),
            z3_source=z3_source,
        )

        # Check if we should force build (use resolved per-service config if available)
        force_build = False
        if resolved_docker is not None:
            force_build = resolved_docker.get("force_build_docker_image", False)
        elif (
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
        if docker_builder.image_exists(expected_image_tag) and (
            not force_build or DockerBuilder.was_built_this_session(expected_image_tag)
        ):
            # Verify with direct Docker API to avoid stale cache false positives
            try:
                docker_builder.client.images.get(expected_image_tag)
                self.logger.info(
                    f"Service Docker image verified and exists, skipping build: {expected_image_tag}"
                )
                # Set runtime_mode even when using cached image (for docker-compose template)
                self.runtime_mode = runtime_mode
                self.build_mode = docker_builder.validate_build_mode_for_architecture(
                    build_mode
                )
                self.z3_source = z3_source
                self.docker_image_tag = expected_image_tag
                self.emit_docker_build_completed(expected_image_tag, True)
                return
            except Exception as e:
                self.logger.warning(
                    f"Cache reported image exists but Docker API verification failed for "
                    f"'{expected_image_tag}', proceeding with build: {e}",
                    exc_info=True,
                )
                docker_builder.image_cache.invalidate_cache()

        self.logger.info(f"Building service Docker image: {expected_image_tag}")

        self.emit_docker_build_started(str(dockerfile_path), expected_image_tag)

        try:
            # Determine the correct base image using consistent tag generation
            if dependencies is not None:
                version_dict = {
                    "dependencies": dependencies,
                    "version": base_version,
                    "commit": commit,
                    "build_mode": build_mode,
                    "runtime_mode": runtime_mode,
                    "z3_source": z3_source,
                }
            else:
                version_dict = {
                    "version": base_version,
                    "build_mode": build_mode,
                    "runtime_mode": runtime_mode,
                    "z3_source": z3_source,
                }
            # Pass resolved per-service docker overrides to build_image()
            if resolved_docker is not None:
                version_dict["resolved_docker"] = resolved_docker
            self.runtime_mode = runtime_mode
            self.build_mode = self.docker_builder.validate_build_mode_for_architecture(
                build_mode
            )
            self.z3_source = z3_source
            self.docker_image_tag = expected_image_tag
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

    def _determine_runtime_mode_from_execution_environment(
        self, plugin_manager: Optional["PluginManager"] = None
    ) -> str:
        """
        Automatically determine runtime_mode based on execution environment plugin.

        Args:
            plugin_manager: Plugin manager for accessing plugin metadata

        Returns:
            str: Runtime mode (minimal, debug, profile) based on execution environment
        """
        try:
            execution_env_name = None

            # Debug: List all available attributes
            self.logger.debug(
                f"Available attributes: {[attr for attr in dir(self) if not attr.startswith('_')]}"
            )

            # Pattern 2: service_config_to_test.test_config.execution_environment (legacy)
            self.logger.debug(
                "Attempting to determine runtime_mode from execution environment"
            )
            if (
                not execution_env_name
                and hasattr(self, "service_config_to_test")
                and self.service_config_to_test
                and hasattr(self.service_config_to_test, "test_config")
            ):
                test_config = self.service_config_to_test.test_config
                if (
                    hasattr(test_config, "execution_environment")
                    and test_config.execution_environment
                ):
                    execution_env_name = self._extract_env_name_from_config(
                        test_config.execution_environment
                    )
                    self.logger.debug(
                        f"Found execution_env_name from service_config_to_test: {execution_env_name}"
                    )

            # Pattern 3: test_case.execution_environment or test_case.test_config.execution_environment
            self.logger.debug(
                "Attempting to determine runtime_mode from test_case execution environment"
            )
            self.logger.debug(f"test_case available: {hasattr(self, 'test_case')}")
            if not execution_env_name and hasattr(self, "test_case") and self.test_case:
                self.logger.debug(
                    f"test_case.execution_environment: {getattr(self.test_case, 'execution_environment', 'MISSING')}"
                )
                if (
                    hasattr(self.test_case, "execution_environment")
                    and self.test_case.execution_environment
                ):
                    execution_env_name = self._extract_env_name_from_config(
                        self.test_case.execution_environment
                    )
                    self.logger.debug(
                        f"Found execution_env_name from test_case: {execution_env_name}"
                    )
                # Fallback: TestCaseBase stores it in test_config.execution_environment
                elif (
                    hasattr(self.test_case, "test_config")
                    and self.test_case.test_config
                    and hasattr(self.test_case.test_config, "execution_environment")
                    and self.test_case.test_config.execution_environment
                ):
                    execution_env_name = self._extract_env_name_from_config(
                        self.test_case.test_config.execution_environment
                    )
                    self.logger.debug(
                        f"Found execution_env_name from test_case.test_config: {execution_env_name}"
                    )

            self.logger.debug(
                f"Final execution_env_name detected: {execution_env_name}"
            )

            # Pattern 4: Check plugin_manager for execution environment context
            if not execution_env_name and plugin_manager:
                try:
                    # Check if plugin_manager has experiment_context with execution environment
                    if hasattr(plugin_manager, "experiment_context"):
                        experiment_context = plugin_manager.experiment_context
                        self.logger.debug(
                            f"Plugin manager experiment_context: {experiment_context}"
                        )
                        if experiment_context and hasattr(
                            experiment_context, "execution_environment"
                        ):
                            exec_env_from_context = (
                                experiment_context.execution_environment
                            )
                            self.logger.debug(
                                f"Execution environment from context: {exec_env_from_context}"
                            )
                            self.logger.debug(
                                f"Type: {type(exec_env_from_context)}, Length: {len(exec_env_from_context) if hasattr(exec_env_from_context, '__len__') else 'N/A'}"
                            )

                            # Workaround: If experiment_context.execution_environment is empty but we can see it in the string representation,
                            # try multiple paths to access the execution environment
                            if not exec_env_from_context and (
                                hasattr(experiment_context, "omega_config")
                                and experiment_context.omega_config
                            ):
                                omega_config = experiment_context.omega_config
                                if "execution_environment" in omega_config:
                                    exec_env_from_context = omega_config[
                                        "execution_environment"
                                    ]
                                    self.logger.debug(
                                        f"Retrieved from omega_config: {exec_env_from_context}"
                                    )

                            # Try accessing execution_environment directly from the service's test configuration
                            if not exec_env_from_context and hasattr(
                                self, "service_config_to_test"
                            ):
                                service_config = self.service_config_to_test
                                if (
                                    hasattr(service_config, "test_config")
                                    and service_config.test_config
                                ):
                                    test_config = service_config.test_config
                                    if hasattr(test_config, "execution_environment"):
                                        exec_env_from_context = (
                                            test_config.execution_environment
                                        )
                                        self.logger.debug(
                                            f"Retrieved from service_config test_config: {exec_env_from_context}"
                                        )

                            # Debug: Show all available attributes on experiment_context
                            if not exec_env_from_context:
                                available_attrs = [
                                    attr
                                    for attr in dir(experiment_context)
                                    if not attr.startswith("_")
                                ]
                                self.logger.debug(
                                    f"Available experiment_context attributes: {available_attrs}"
                                )

                                # Try to understand the actual structure
                                for attr in [
                                    "test_config",
                                    "config",
                                    "test_case",
                                    "original_config",
                                ]:
                                    if hasattr(experiment_context, attr):
                                        attr_value = getattr(experiment_context, attr)
                                        self.logger.debug(
                                            f"experiment_context.{attr}: {type(attr_value)} = {attr_value}"
                                        )
                                        if hasattr(attr_value, "execution_environment"):
                                            exec_env_candidate = getattr(
                                                attr_value, "execution_environment"
                                            )
                                            self.logger.debug(
                                                f"Found execution_environment in {attr}: {exec_env_candidate}"
                                            )
                                            if exec_env_candidate:
                                                exec_env_from_context = (
                                                    exec_env_candidate
                                                )
                                                break

                            execution_env_name = self._extract_env_name_from_config(
                                exec_env_from_context
                            )
                            self.logger.debug(
                                f"Found execution_env_name from plugin_manager: {execution_env_name}"
                            )
                except Exception as e:
                    self.logger.debug(
                        f"Error accessing plugin_manager experiment_context: {e}"
                    )

            # Auto-discover runtime mode from execution environment type
            # Check plugin metadata to determine if it's debug, profile, or minimal
            if plugin_manager:
                try:
                    self.logger.debug(
                        f"Auto-discovering runtime_mode for {execution_env_name} using plugin_manager"
                    )
                    plugin_info = plugin_manager.get_plugin(execution_env_name)
                    self.logger.debug(f"Plugin info retrieved: {plugin_info}")
                    if plugin_info and hasattr(plugin_info, "runtime_mode"):
                        runtime_mode = plugin_info.runtime_mode
                        self.logger.debug(
                            f"Plugin {execution_env_name} has runtime_mode attribute: {runtime_mode}"
                        )
                        if runtime_mode:
                            self.logger.debug(
                                f"Auto-discovered runtime_mode '{runtime_mode}' from plugin metadata for {execution_env_name}"
                            )
                            return runtime_mode
                        else:
                            self.logger.debug(
                                f"runtime_mode is None/empty for {execution_env_name}"
                            )
                    else:
                        self.logger.debug(
                            f"No runtime_mode attribute found in plugin metadata for {execution_env_name}"
                        )
                        if plugin_info:
                            self.logger.debug(
                                f"Available plugin_info attributes: {dir(plugin_info)}"
                            )
                except Exception as e:
                    self.logger.debug(
                        f"Exception during plugin metadata lookup for {execution_env_name}: {e}"
                    )
            else:
                self.logger.debug(
                    "No plugin_manager available for runtime_mode detection"
                )

            # Default fallback when plugin metadata unavailable
            self.logger.debug(
                f"No runtime_mode detected for {execution_env_name}, defaulting to minimal"
            )
            return "minimal"

        except Exception as e:
            self.logger.debug(f"Error determining runtime mode: {e}")
            return "minimal"

    def _extract_env_name_from_config(self, exec_env) -> Optional[str]:
        """
        Extract environment name from execution environment config.

        Handles both list and single object formats with multiple field names.

        Args:
            exec_env: Execution environment configuration (list or object)

        Returns:
            Optional[str]: Environment name if found, None otherwise
        """
        self.logger.debug(
            f"Extracting env name from config: {exec_env} (type: {type(exec_env)})"
        )

        if isinstance(exec_env, list) and len(exec_env) > 0:
            # Current format: execution_environment is a list
            first_env = exec_env[0]
            self.logger.debug(
                f"First env in list: {first_env} (type: {type(first_env)})"
            )
            if hasattr(first_env, "get"):
                # Dict-like object
                env_name = first_env.get("type", None)
                self.logger.debug(f"Dict-like extraction result: {env_name}")
                return env_name
            else:
                # Object with attributes - try multiple possible field names
                for field_name in ["type", "env_type", "env_sub_type", "name"]:
                    if hasattr(first_env, field_name):
                        env_name = getattr(first_env, field_name)
                        self.logger.debug(
                            f"Attribute extraction ({field_name}): {env_name}"
                        )
                        if env_name:
                            return env_name
        elif hasattr(exec_env, "get"):
            # Single dict-like object
            env_name = exec_env.get("type", None)
            self.logger.debug(f"Single dict extraction: {env_name}")
            return env_name
        elif hasattr(exec_env, "type"):
            # Single object with type attribute
            env_name = getattr(exec_env, "type", None)
            self.logger.debug(f"Single object extraction: {env_name}")
            return env_name

        self.logger.debug("No env name found, returning None")
        return None

    def _select_optimal_dockerfile(self, services_dir: Path) -> Path:
        """
        Select the optimal Dockerfile based on BuildKit availability and preference.

        Priority order:
        1. Dockerfile.buildkit (if BuildX available and should be used)
        2. Dockerfile (fallback)

        Args:
            services_dir: Directory containing Dockerfile variants

        Returns:
            Path: Path to the selected Dockerfile
        """
        docker_builder = DockerBuilder()

        buildkit_dockerfile = services_dir / "Dockerfile.buildkit"
        regular_dockerfile = services_dir / "Dockerfile"

        # Check if BuildX is available on the system
        if not docker_builder._check_buildx_available():
            self.logger.info("BuildX not available, using standard Dockerfile")
            return (
                regular_dockerfile
                if regular_dockerfile.exists()
                else buildkit_dockerfile
            )

        # Check if use_buildx is enabled in config (use self.global_config, not docker_builder)
        # Default to True only if config is not accessible (backwards compatibility)
        gc = getattr(self, "global_config", None)
        if gc is not None and hasattr(gc, "docker") and gc.docker is not None:
            use_buildx_config = getattr(gc.docker, "use_buildx", True)
            self.logger.debug(f"use_buildx from global_config: {use_buildx_config}")
        else:
            # No config available, default to buildkit for backwards compatibility
            use_buildx_config = True
            self.logger.debug("No global_config.docker available, defaulting use_buildx=True")

        # Prefer Dockerfile.buildkit only if use_buildx is enabled in config
        if use_buildx_config and buildkit_dockerfile.exists():
            self.logger.debug(
                f"Selected BuildKit-optimized Dockerfile: {buildkit_dockerfile}"
            )
            return buildkit_dockerfile
        elif not use_buildx_config and regular_dockerfile.exists():
            self.logger.debug(
                f"Selected standard Dockerfile (use_buildx=False): {regular_dockerfile}"
            )
            return regular_dockerfile

        # Check if regular Dockerfile requires BuildKit features
        if regular_dockerfile.exists():
            # Temporarily set dockerfile path for BuildKit detection
            docker_builder._current_dockerfile_path = regular_dockerfile
            requires_buildkit = docker_builder._dockerfile_requires_buildkit(
                regular_dockerfile
            )

            if requires_buildkit:
                self.logger.warning(
                    f"Dockerfile requires BuildKit features but no Dockerfile.buildkit found. "
                    f"BuildX will be forced for: {regular_dockerfile}"
                )

            self.logger.info(
                f"Selected standard Dockerfile (BuildKit required: {requires_buildkit}): {regular_dockerfile}"
            )
            return regular_dockerfile

        # If neither exists, fall back to regular Dockerfile path (will cause build error)
        self.logger.warning(
            f"No Dockerfile found in {services_dir}, using default path"
        )
        return regular_dockerfile

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
