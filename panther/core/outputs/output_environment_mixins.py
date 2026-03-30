"""Execution Environment Mixins.

This module provides standardized mixins for execution environment plugins
to ensure consistent behavior across all environments.
"""

import contextlib
import logging
import os
import time
from abc import ABC
from pathlib import Path
from typing import Any, Dict, List, Tuple

from panther.core.outputs.output_collector import IOutputCollector
from panther.core.outputs.phase_collection_standard import PhaseCollectionStandard


class StandardOutputCollectorMixin(IOutputCollector, ABC):
    """Standardized output collection for execution environments.

    This mixin provides a consistent way to register, collect, and manage
    outputs from execution environments. It handles container path mapping
    and provides metadata about collected outputs.
    """

    def __init__(self, *args, **kwargs):
        """Initialize output collector with empty output files registry."""
        super().__init__(*args, **kwargs)
        self.output_files = {}
        if hasattr(self, "logger"):
            self.logger.debug(
                "StandardOutputCollectorMixin initialized for %s, output_files created",
                self.__class__.__name__,
            )

    def register_service_outputs(self, services_managers, get_log_directory_func):
        """Register outputs with service-specific and protocol-aware patterns."""
        # Store for deferred discovery
        self.services_managers = services_managers
        self.get_log_directory_func = get_log_directory_func

        self.logger.debug(
            "Starting register_service_outputs for %d services",
            len(services_managers),
        )
        self.logger.debug("Current output_files count: %d", len(self.output_files))

        for service_manager in services_managers:
            service_name = getattr(service_manager, "service_name", "unknown")
            log_dir = get_log_directory_func(service_name)

            # Check if log directory exists
            if not log_dir.exists():
                self.logger.warning(
                    f"Log directory not found for {service_name}: {log_dir}"
                )
                continue

            # Get service-specific output patterns if available (Option 2)
            if hasattr(service_manager, "get_output_patterns"):
                output_patterns = service_manager.get_output_patterns()
                self.logger.debug(
                    "Using service-specific patterns for %s: %s",
                    service_name,
                    output_patterns,
                )
            else:
                # Fall back to default patterns with protocol awareness (Option 4)
                output_patterns = self._get_default_patterns_for_service(
                    service_manager
                )
                self.logger.debug(
                    "Using default patterns for %s: %s",
                    service_name,
                    output_patterns,
                )

            # Register outputs based on patterns
            for output_type, filename_pattern in output_patterns:
                # Support {service_name} placeholder
                if "{service_name}" in filename_pattern:
                    filename = filename_pattern.format(service_name=service_name)
                    file_path = log_dir / filename

                    if file_path.exists():
                        self.register_output_file(
                            output_type, str(file_path), service_name
                        )
                        self.logger.debug("Registered %s: %s", output_type, file_path)
                elif "*" in filename_pattern:
                    # It's a glob pattern
                    self._register_pattern_outputs(
                        service_name, log_dir, output_type, filename_pattern
                    )
                else:
                    # Regular filename
                    file_path = log_dir / filename_pattern
                    if file_path.exists():
                        self.register_output_file(
                            output_type, str(file_path), service_name
                        )
                        self.logger.debug("Registered %s: %s", output_type, file_path)

            # Additional discovery if service provides custom patterns
            if hasattr(service_manager, "get_additional_output_discovery_patterns"):
                discovery_patterns = (
                    service_manager.get_additional_output_discovery_patterns()
                )
                for output_type, patterns in discovery_patterns.items():
                    for pattern in patterns:
                        self._register_pattern_outputs(
                            service_name, log_dir, output_type, pattern
                        )

        self.logger.info(
            f"Completed register_service_outputs. Total registered files: {len(self.output_files)}"
        )

    def _get_default_patterns_for_service(
        self, service_manager
    ) -> List[Tuple[str, str]]:
        """Get default output patterns for a service when it doesn't provide its own.

        This method now uses PhaseCollectionStandard for consistent pattern generation
        while maintaining backward compatibility.
        """
        # Detect service characteristics for pattern generation
        protocol = self._detect_service_protocol(service_manager)
        service_type = self._detect_service_type(service_manager)
        service_name = getattr(service_manager, "service_name", None)
        language = self._detect_service_language(service_manager)

        # Use PhaseCollectionStandard for centralized pattern generation
        patterns = PhaseCollectionStandard.get_patterns_for_service(
            protocol=protocol,
            service_type=service_type,
            service_name=service_name,
            language=language,
        )

        return patterns

    def _detect_service_protocol(self, service_manager) -> str:
        """Detect protocol from service manager."""
        if hasattr(service_manager, "service_config_to_test"):
            protocol = getattr(
                service_manager.service_config_to_test.protocol, "name", None
            )
            if protocol:
                return protocol

        # Fallback to module path detection
        module_path = service_manager.__class__.__module__
        return PhaseCollectionStandard.detect_protocol_from_path(module_path)

    def _detect_service_type(self, service_manager) -> str:
        """Detect service type (tester or iut)."""
        if hasattr(service_manager, "is_tester") and service_manager.is_tester():
            return "tester"

        # Fallback to module path detection
        module_path = service_manager.__class__.__module__
        return PhaseCollectionStandard.detect_service_type_from_path(module_path)

    def _detect_service_language(self, service_manager) -> str:
        """Detect programming language for service."""
        module_path = service_manager.__class__.__module__
        return PhaseCollectionStandard.detect_language_from_path(module_path)

    def _register_pattern_outputs(
        self, service_name: str, log_dir: Path, output_type: str, pattern: str
    ):
        """Register outputs matching a glob pattern."""
        try:
            for matching_file in log_dir.glob(pattern):
                if matching_file.is_file():
                    self.register_output_file(
                        output_type, str(matching_file), service_name
                    )
                    self.logger.debug(
                        "Registered %s from pattern: %s", output_type, matching_file
                    )
        except Exception as e:
            self.logger.error(f"Error registering pattern outputs for {pattern}: {e}")

    def register_output_file(
        self, output_type: str, file_path: str, service_name: str = None
    ) -> None:
        """Register an output file for collection.

        Args:
            output_type: Type of output (e.g., 'trace', 'profile', 'memcheck')
            file_path: Path to the output file
            service_name: Optional service name for multi-service environments
        """
        key = f"{output_type}_{service_name}" if service_name else output_type
        self.output_files[key] = {
            "path": file_path,
            "type": output_type,
            "service": service_name,
            "registered_at": time.time(),
        }

        if hasattr(self, "logger"):
            self.logger.debug("Registered output file: %s -> %s", key, file_path)
            self.logger.debug("Total output files now: %d", len(self.output_files))

    def collect_outputs(self) -> Dict[str, str]:
        """Collect all registered outputs with environment-aware path resolution and deferred discovery.

        Returns:
            Dictionary mapping output type to file path
        """
        outputs = {}

        self.logger.debug("collect_outputs called for %s", self.__class__.__name__)
        self.logger.debug("Instance ID: %s", id(self))
        self.logger.debug(
            "Environment type: %s", getattr(self, "env_sub_type", "unknown")
        )

        self.logger.debug(
            "Output directory: %s", getattr(self, "output_dir", "not set")
        )
        self.logger.debug("Registered output files: %s", self.output_files)
        self.logger.debug(
            "Number of registered output files: %d", len(self.output_files)
        )

        # First, try to collect from registered files
        registered_outputs = self._collect_registered_outputs()
        outputs.update(registered_outputs)

        # Then, perform deferred discovery to find additional files
        discovered_outputs = self._perform_deferred_discovery()

        # Merge discovered outputs (don't overwrite registered ones)
        for key, path in discovered_outputs.items():
            if key not in outputs:
                outputs[key] = path
                self.logger.debug("Added discovered output: %s -> %s", key, path)

        self.logger.info(
            f"Total collected outputs: {len(outputs)} ({len(registered_outputs)} registered + {len(discovered_outputs) - len(set(discovered_outputs.keys()) & set(registered_outputs.keys()))} discovered)"
        )
        return outputs

    def _collect_registered_outputs(self) -> Dict[str, str]:
        """Collect outputs from registered file patterns."""
        outputs = {}

        self.logger.info(
            f"Starting registered output collection with {len(self.output_files)} registered files"
        )

        for key, info in self.output_files.items():
            file_path = info["path"]
            service_name = info["service"]

            # Use environment-aware path resolution
            host_path = self._resolve_container_path_to_host(file_path, service_name)

            self.logger.debug("Checking registered output: %s", key)
            self.logger.debug("  Container path: %s", file_path)
            self.logger.debug("  Service name: %s", service_name)
            self.logger.debug("  Resolved host path: %s", host_path)
            self.logger.debug("  File exists: %s", os.path.exists(host_path))

            if os.path.exists(host_path):
                outputs[key] = host_path
                self.logger.info(
                    f"✅ Collected registered {info['type']} output: {host_path}"
                )
            else:
                self.logger.warning(
                    f"❌ Missing registered {info['type']} output: {host_path}"
                )
                self._log_missing_file_diagnostics(host_path, file_path, service_name)

        return outputs

    def _resolve_container_path_to_host(
        self, container_path: str, service_name: str
    ) -> str:
        """Resolve container path to host path using environment-aware mapping.

        Args:
            container_path: Path inside container (e.g., "/app/logs/stdout.log")
            service_name: Name of the service

        Returns:
            Resolved host path
        """
        # If it's already a host path, return as-is
        if not container_path.startswith("/app/logs/"):
            return container_path

        if not hasattr(self, "output_dir"):
            self.logger.warning("output_dir not set, using container path as-is")
            return container_path

        # Get environment-specific path mapping
        env_type = getattr(self, "env_sub_type", "unknown")

        self.logger.debug("Environment type detected: %s", env_type)

        if env_type == "docker_compose":
            # Docker Compose: each service has its own mounted directory
            # Volume mount: {output_dir}/logs/{service_name}:/app/logs
            # But files are actually stored in subdirectories like runtime/, artifacts/, etc.
            base_host_path = (
                container_path.replace(
                    "/app/logs/", f"{self.output_dir}/logs/{service_name}/"
                )
                if service_name
                else container_path.replace("/app/logs/", f"{self.output_dir}/logs/")
            )

            # If the direct path doesn't exist, search in subdirectories
            if not os.path.exists(base_host_path) and service_name:
                filename = os.path.basename(container_path)
                service_dir = f"{self.output_dir}/logs/{service_name}"

                # Common subdirectories where files might be stored
                subdirs = ["runtime", "artifacts", "compile", "logs", "output", "data"]

                for subdir in subdirs:
                    candidate_path = os.path.join(service_dir, subdir, filename)
                    if os.path.exists(candidate_path):
                        self.logger.debug(
                            "Found file in subdirectory: %s", candidate_path
                        )
                        return candidate_path

                # If not found in common subdirs, do recursive search
                for root, dirs, files in os.walk(service_dir):
                    if filename in files:
                        found_path = os.path.join(root, filename)
                        self.logger.debug(
                            "Found file via recursive search: %s", found_path
                        )
                        return found_path

            host_path = base_host_path

        elif env_type == "localhost_single_container":
            # Localhost single container: might have different mounting strategy
            # Check if service-specific directory exists, otherwise use shared
            if service_name and os.path.exists(
                f"{self.output_dir}/logs/{service_name}"
            ):
                host_path = container_path.replace(
                    "/app/logs/", f"{self.output_dir}/logs/{service_name}/"
                )
            else:
                host_path = container_path.replace(
                    "/app/logs/", f"{self.output_dir}/logs/"
                )

        elif env_type == "shadow_ns":
            # Shadow NS: files might be in simulation-specific directories
            simulation_dirs = [
                f"{self.output_dir}/shadow-results",
                f"{self.output_dir}/logs/{service_name}" if service_name else None,
                f"{self.output_dir}/logs",
            ]

            # Try to find the file in possible directories
            filename = os.path.basename(container_path)
            host_path = next(
                (
                    f"{sim_dir}/{filename}"
                    for sim_dir in simulation_dirs
                    if sim_dir and os.path.exists(f"{sim_dir}/{filename}")
                ),
                container_path.replace(
                    "/app/logs/",
                    (
                        f"{self.output_dir}/logs/{service_name}/"
                        if service_name
                        else f"{self.output_dir}/logs/"
                    ),
                ),
            )
        elif service_name:
            host_path = container_path.replace(
                "/app/logs/", f"{self.output_dir}/logs/{service_name}/"
            )
        else:
            host_path = container_path.replace("/app/logs/", f"{self.output_dir}/logs/")

        self.logger.debug(
            "Path resolution: %s -> %s (env: %s, service: %s)",
            container_path,
            host_path,
            env_type,
            service_name,
        )
        return host_path

    def _perform_deferred_discovery(self) -> Dict[str, str]:
        """Perform deferred discovery to find output files that weren't registered.

        This scans actual directories for files matching expected patterns.
        """
        discovered = {}

        if not hasattr(self, "output_dir") or not hasattr(self, "services_managers"):
            self.logger.debug(
                "Cannot perform deferred discovery: missing output_dir or services_managers"
            )
            return discovered

        self.logger.debug("Performing deferred output discovery...")

        # Scan service directories for actual files
        for service_manager in getattr(self, "services_managers", []):
            service_name = getattr(service_manager, "service_name", None)
            if not service_name:
                continue

            # Get expected log directory for this service
            # Prefer the stored get_log_directory_func (authoritative source)
            if hasattr(self, "get_log_directory_func") and self.get_log_directory_func:
                service_log_dir = str(self.get_log_directory_func(service_name))
            else:
                service_log_dir = self._get_service_log_directory_for_discovery(
                    service_name
                )

            if not os.path.exists(service_log_dir):
                self.logger.debug(
                    "Service log directory does not exist: %s", service_log_dir
                )
                continue

            self.logger.debug(
                "Scanning directory for %s: %s", service_name, service_log_dir
            )

            # Get output patterns for this service
            patterns = []
            if hasattr(service_manager, "get_output_patterns"):
                patterns = service_manager.get_output_patterns()
            else:
                patterns = self._get_default_patterns_for_service(service_manager)

            # Scan for files matching patterns
            for output_type, pattern in patterns:
                discovered_files = self._scan_pattern_in_directory(
                    service_log_dir, pattern, service_name
                )
                for file_path in discovered_files:
                    key = (
                        f"{output_type}_{service_name}" if service_name else output_type
                    )
                    if key not in discovered:  # Don't overwrite existing
                        discovered[key] = file_path
                        self.logger.debug(
                            "Discovered %s file: %s", output_type, file_path
                        )

        self.logger.info(
            f"Deferred discovery found {len(discovered)} additional output files"
        )
        return discovered

    def _get_service_log_directory_for_discovery(self, service_name: str) -> str:
        """Get the service log directory for discovery purposes."""
        env_type = getattr(self, "env_sub_type", "unknown")

        if env_type == "docker_compose":
            return f"{self.output_dir}/logs/{service_name}"
        elif env_type == "localhost_single_container":
            # Try service-specific first, then shared
            service_specific = f"{self.output_dir}/logs/{service_name}"
            if os.path.exists(service_specific):
                return service_specific
            return f"{self.output_dir}/logs"
        elif env_type == "shadow_ns":
            # Try multiple possible locations
            for possible_dir in [
                f"{self.output_dir}/shadow-results",
                f"{self.output_dir}/logs/{service_name}",
                f"{self.output_dir}/logs",
            ]:
                if os.path.exists(possible_dir):
                    return possible_dir
            return f"{self.output_dir}/logs/{service_name}"
        else:
            return f"{self.output_dir}/logs/{service_name}"

    def _scan_pattern_in_directory(
        self, directory: str, pattern: str, service_name: str
    ) -> List[str]:
        """Scan directory for files matching a pattern."""
        import glob

        try:
            # Handle {service_name} placeholder
            if "{service_name}" in pattern:
                pattern = pattern.format(service_name=service_name)

            # Create full path pattern
            full_pattern = os.path.join(directory, pattern)

            # Find matching files
            matching_files = glob.glob(full_pattern)

            # Filter to only existing files
            return [f for f in matching_files if os.path.isfile(f)]

        except Exception as e:
            self.logger.warning(f"Error scanning pattern {pattern} in {directory}: {e}")
            return []

    def _log_missing_file_diagnostics(
        self, host_path: str, container_path: str, service_name: str
    ):
        """Log detailed diagnostics when an output file is missing."""
        parent_dir = os.path.dirname(host_path)

        if os.path.exists(parent_dir):
            try:
                actual_files = os.listdir(parent_dir)
                self.logger.warning(
                    f"Output file not found: {host_path} (container: {container_path}, service: {service_name}). "
                    f"Directory exists but contains: {actual_files[:10]}{'...' if len(actual_files) > 10 else ''}"
                )

                # Look for similar files
                filename = os.path.basename(host_path)
                if similar_files := [
                    f
                    for f in actual_files
                    if filename.lower() in f.lower() or f.lower() in filename.lower()
                ]:
                    self.logger.info(f"Similar files found: {similar_files}")

            except OSError as e:
                self.logger.warning(
                    f"Output file not found: {host_path} (container: {container_path}, service: {service_name}). "
                    f"Directory exists but cannot list contents: {e}"
                )
        else:
            self.logger.warning(
                f"Output file not found: {host_path} (container: {container_path}, service: {service_name}). "
                f"Parent directory {parent_dir} does not exist."
            )

            # Check if parent's parent exists and what it contains
            parent_parent = os.path.dirname(parent_dir)
            if os.path.exists(parent_parent):
                with contextlib.suppress(OSError):
                    dirs_in_parent = [
                        d
                        for d in os.listdir(parent_parent)
                        if os.path.isdir(os.path.join(parent_parent, d))
                    ]
                    self.logger.info(
                        f"Available directories in {parent_parent}: {dirs_in_parent}"
                    )

    def get_output_metadata(self) -> Dict[str, Any]:
        """Get metadata about collected outputs.

        Returns:
            Dictionary with metadata for each output file
        """
        metadata = {}

        for key, info in self.output_files.items():
            file_path = info["path"]
            service_name = info["service"]

            # Handle container path mapping
            if file_path.startswith("/app/logs/"):
                # Map container path to host path using proper service-specific directory
                if hasattr(self, "output_dir") and service_name:
                    # Container /app/logs/ maps to {output_dir}/logs/{service_name}/
                    host_path = file_path.replace(
                        "/app/logs/", f"{self.output_dir}/logs/{service_name}/"
                    )
                elif hasattr(self, "output_dir"):
                    # Fallback to general logs directory if no service name
                    host_path = file_path.replace(
                        "/app/logs/", f"{self.output_dir}/logs/"
                    )
                else:
                    # Fallback if output_dir not set
                    host_path = file_path
            else:
                host_path = file_path

            if os.path.exists(host_path):
                stat_info = os.stat(host_path)
                metadata[key] = {
                    "size_bytes": stat_info.st_size,
                    "format": self._get_output_format(info["type"]),
                    "timestamp": time.ctime(stat_info.st_mtime),
                    "path": host_path,
                    "environment": getattr(self, "env_sub_type", "unknown"),
                    "type": info["type"],
                    "service": info["service"],
                }
            else:
                metadata[key] = {
                    "error": "File not found",
                    "path": host_path,
                    "type": info["type"],
                    "service": info["service"],
                }

        return metadata

    def _get_output_format(self, output_type: str) -> str:
        """Get the format for a given output type.

        Args:
            output_type: Type of output

        Returns:
            Format string for the output type
        """
        format_map = {
            "trace": "strace",
            "cpu_profile": "gperf_cpu_profile",
            "heap_profile": "gperf_heap_profile",
            "memcheck": "valgrind_xml",
            "helgrind": "valgrind_xml",
            "log": "text",
            "profile": "binary",
            "perf": "perf_data",
        }
        return format_map.get(output_type, "unknown")
