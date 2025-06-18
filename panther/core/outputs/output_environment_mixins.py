"""
Execution Environment Mixins

This module provides standardized mixins for execution environment plugins
to ensure consistent behavior across all environments.
"""

import os
import time
from abc import ABC
from pathlib import Path
from typing import Any, Dict, List, Tuple

from panther.core.outputs.output_collector import IOutputCollector


class StandardOutputCollectorMixin(IOutputCollector, ABC):
    """
    Standardized output collection for execution environments.

    This mixin provides a consistent way to register, collect, and manage
    outputs from execution environments. It handles container path mapping
    and provides metadata about collected outputs.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.output_files = {}
        if hasattr(self, "logger"):
            self.logger.debug(f"StandardOutputCollectorMixin initialized for {self.__class__.__name__}, output_files created")

    # Protocol-specific patterns
    PROTOCOL_OUTPUT_PATTERNS = { # TODO use protocol plugins to get this
        "quic": [
            ("qlog", "*.qlog"),
            ("keys", "*keys.log"),
            ("congestion", "*congestion*.log")
        ],
        "tcp": [
            ("tcpdump", "*.pcap"),
            ("netstat", "*netstat*.log")
        ],
        "http": [
            ("access_log", "access.log"),
            ("error_log", "error.log"),
            ("har", "*.har")
        ]
    }

    def register_service_outputs(self, services_managers, get_log_directory_func):
        """Register outputs with service-specific and protocol-aware patterns."""
        self.logger.debug(f"Starting register_service_outputs for {len(services_managers)} services")
        self.logger.debug(f"Current output_files count: {len(self.output_files)}")
        
        for service_manager in services_managers:
            service_name = getattr(service_manager, 'service_name', 'unknown')
            log_dir = get_log_directory_func(service_name)
            
            # Check if log directory exists
            if not log_dir.exists():
                self.logger.warning(f"Log directory not found for {service_name}: {log_dir}")
                continue
            
            # Get service-specific output patterns if available (Option 2)
            if hasattr(service_manager, 'get_output_patterns'):
                output_patterns = service_manager.get_output_patterns()
                self.logger.debug(f"Using service-specific patterns for {service_name}: {output_patterns}")
            else:
                # Fall back to default patterns with protocol awareness (Option 4)
                output_patterns = self._get_default_patterns_for_service(service_manager)
                self.logger.debug(f"Using default patterns for {service_name}: {output_patterns}")
            
            # Register outputs based on patterns
            for output_type, filename_pattern in output_patterns:
                # Support {service_name} placeholder
                if '{service_name}' in filename_pattern:
                    filename = filename_pattern.format(service_name=service_name)
                    file_path = log_dir / filename
                    
                    if file_path.exists():
                        self.register_output_file(output_type, str(file_path), service_name)
                        self.logger.debug(f"Registered {output_type}: {file_path}")
                elif '*' in filename_pattern:
                    # It's a glob pattern
                    self._register_pattern_outputs(service_name, log_dir, output_type, filename_pattern)
                else:
                    # Regular filename
                    file_path = log_dir / filename_pattern
                    if file_path.exists():
                        self.register_output_file(output_type, str(file_path), service_name)
                        self.logger.debug(f"Registered {output_type}: {file_path}")
            
            # Additional discovery if service provides custom patterns
            if hasattr(service_manager, 'get_additional_output_discovery_patterns'):
                discovery_patterns = service_manager.get_additional_output_discovery_patterns()
                for output_type, patterns in discovery_patterns.items():
                    for pattern in patterns:
                        self._register_pattern_outputs(service_name, log_dir, output_type, pattern)
                        
        self.logger.info(f"Completed register_service_outputs. Total registered files: {len(self.output_files)}")
                    
    def _get_default_patterns_for_service(self, service_manager) -> List[Tuple[str, str]]:
        """Get default output patterns for a service when it doesn't provide its own."""
        # Base patterns
        patterns = [
            ("stdout", "stdout.log"),
            ("stderr", "stderr.log"),
            ("logs", "{service_name}.log")
        ]
        
        # Add protocol-specific patterns
        protocol = None
        if hasattr(service_manager, 'service_config_to_test'):
            protocol = getattr(service_manager.service_config_to_test.protocol, 'name', None)
        
        if protocol and protocol in self.PROTOCOL_OUTPUT_PATTERNS:
            patterns.extend(self.PROTOCOL_OUTPUT_PATTERNS[protocol])
        
        # Add service type specific patterns
        if hasattr(service_manager, 'is_tester') and service_manager.is_tester:
            patterns.extend([
                ("test_results", "test_results.json"),
                ("test_log", "test_{service_name}.log"),
                ("analysis", "analysis_{service_name}.json")
            ])
        
        return patterns
    
    def _register_pattern_outputs(self, service_name: str, log_dir: Path, output_type: str, pattern: str):
        """Register outputs matching a glob pattern."""
        try:
            for matching_file in log_dir.glob(pattern):
                if matching_file.is_file():
                    self.register_output_file(output_type, str(matching_file), service_name)
                    self.logger.debug(f"Registered {output_type} from pattern: {matching_file}")
        except Exception as e:
            self.logger.error(f"Error registering pattern outputs for {pattern}: {e}")
    
    def register_output_file(
        self, output_type: str, file_path: str, service_name: str = None
    ) -> None:
        """
        Register an output file for collection.

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
            self.logger.debug(f"Registered output file: {key} -> {file_path}")
            self.logger.debug(f"Total output files now: {len(self.output_files)}")

    def collect_outputs(self) -> Dict[str, str]:
        """
        Collect all registered outputs with environment-aware path resolution and deferred discovery.

        Returns:
            Dictionary mapping output type to file path
        """
        outputs = {}
        
        self.logger.info(f"collect_outputs called for {self.__class__.__name__}")
        self.logger.debug(f"Instance ID: {id(self)}")
        self.logger.debug(f"Environment type: {getattr(self, 'env_sub_type', 'unknown')}")

        self.logger.debug(
            "Output directory: %s", getattr(self, "output_dir", "not set")
        )
        self.logger.debug("Registered output files: %s", self.output_files)
        self.logger.info(f"Number of registered output files: {len(self.output_files)}")

        # First, try to collect from registered files
        registered_outputs = self._collect_registered_outputs()
        outputs.update(registered_outputs)
        
        # Then, perform deferred discovery to find additional files
        discovered_outputs = self._perform_deferred_discovery()
        
        # Merge discovered outputs (don't overwrite registered ones)
        for key, path in discovered_outputs.items():
            if key not in outputs:
                outputs[key] = path
                self.logger.info(f"Added discovered output: {key} -> {path}")

        self.logger.info(f"Total collected outputs: {len(outputs)} ({len(registered_outputs)} registered + {len(discovered_outputs) - len(set(discovered_outputs.keys()) & set(registered_outputs.keys()))} discovered)")
        return outputs

    def _collect_registered_outputs(self) -> Dict[str, str]:
        """Collect outputs from registered file patterns."""
        outputs = {}
        
        for key, info in self.output_files.items():
            file_path = info["path"]
            service_name = info["service"]

            # Use environment-aware path resolution
            host_path = self._resolve_container_path_to_host(file_path, service_name)

            if os.path.exists(host_path):
                outputs[key] = host_path
                self.logger.debug(f"Collected registered {info['type']} output: {host_path}")
            else:
                self._log_missing_file_diagnostics(host_path, file_path, service_name)

        return outputs

    def _resolve_container_path_to_host(self, container_path: str, service_name: str) -> str:
        """
        Resolve container path to host path using environment-aware mapping.
        
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
        env_type = getattr(self, 'env_sub_type', 'unknown')
        
        if env_type == 'docker_compose':
            # Docker Compose: each service has its own mounted directory
            # Volume mount: {output_dir}/logs/{service_name}:/app/logs
            if service_name:
                host_path = container_path.replace(
                    "/app/logs/", f"{self.output_dir}/logs/{service_name}/"
                )
            else:
                # Fallback if no service name
                host_path = container_path.replace(
                    "/app/logs/", f"{self.output_dir}/logs/"
                )
        
        elif env_type == 'localhost_single_container':
            # Localhost single container: might have different mounting strategy
            # Check if service-specific directory exists, otherwise use shared
            if service_name and os.path.exists(f"{self.output_dir}/logs/{service_name}"):
                host_path = container_path.replace(
                    "/app/logs/", f"{self.output_dir}/logs/{service_name}/"
                )
            else:
                host_path = container_path.replace(
                    "/app/logs/", f"{self.output_dir}/logs/"
                )
        
        elif env_type == 'shadow_ns':
            # Shadow NS: files might be in simulation-specific directories
            simulation_dirs = [
                f"{self.output_dir}/shadow-results",
                f"{self.output_dir}/logs/{service_name}" if service_name else None,
                f"{self.output_dir}/logs"
            ]
            
            # Try to find the file in possible directories
            filename = os.path.basename(container_path)
            for sim_dir in simulation_dirs:
                if sim_dir and os.path.exists(f"{sim_dir}/{filename}"):
                    host_path = f"{sim_dir}/{filename}"
                    break
            else:
                # Default fallback
                host_path = container_path.replace(
                    "/app/logs/", f"{self.output_dir}/logs/{service_name}/" if service_name else f"{self.output_dir}/logs/"
                )
        
        else:
            # Unknown environment, use service-specific if available
            if service_name:
                host_path = container_path.replace(
                    "/app/logs/", f"{self.output_dir}/logs/{service_name}/"
                )
            else:
                host_path = container_path.replace(
                    "/app/logs/", f"{self.output_dir}/logs/"
                )

        self.logger.debug(f"Path resolution: {container_path} -> {host_path} (env: {env_type}, service: {service_name})")
        return host_path

    def _perform_deferred_discovery(self) -> Dict[str, str]:
        """
        Perform deferred discovery to find output files that weren't registered.
        
        This scans actual directories for files matching expected patterns.
        """
        discovered = {}
        
        if not hasattr(self, "output_dir") or not hasattr(self, "services_managers"):
            self.logger.debug("Cannot perform deferred discovery: missing output_dir or services_managers")
            return discovered

        self.logger.debug("Performing deferred output discovery...")
        
        # Scan service directories for actual files
        for service_manager in getattr(self, "services_managers", []):
            service_name = getattr(service_manager, 'service_name', None)
            if not service_name:
                continue
                
            # Get expected log directory for this service
            service_log_dir = self._get_service_log_directory_for_discovery(service_name)
            
            if not os.path.exists(service_log_dir):
                self.logger.debug(f"Service log directory does not exist: {service_log_dir}")
                continue
            
            self.logger.debug(f"Scanning directory for {service_name}: {service_log_dir}")
            
            # Get output patterns for this service
            patterns = []
            if hasattr(service_manager, 'get_output_patterns'):
                patterns = service_manager.get_output_patterns()
            else:
                patterns = self._get_default_patterns_for_service(service_manager)
            
            # Scan for files matching patterns
            for output_type, pattern in patterns:
                discovered_files = self._scan_pattern_in_directory(service_log_dir, pattern, service_name)
                for file_path in discovered_files:
                    key = f"{output_type}_{service_name}" if service_name else output_type
                    if key not in discovered:  # Don't overwrite existing
                        discovered[key] = file_path
                        self.logger.debug(f"Discovered {output_type} file: {file_path}")

        self.logger.info(f"Deferred discovery found {len(discovered)} additional output files")
        return discovered

    def _get_service_log_directory_for_discovery(self, service_name: str) -> str:
        """Get the service log directory for discovery purposes."""
        env_type = getattr(self, 'env_sub_type', 'unknown')
        
        if env_type == 'docker_compose':
            return f"{self.output_dir}/logs/{service_name}"
        elif env_type == 'localhost_single_container':
            # Try service-specific first, then shared
            service_specific = f"{self.output_dir}/logs/{service_name}"
            if os.path.exists(service_specific):
                return service_specific
            return f"{self.output_dir}/logs"
        elif env_type == 'shadow_ns':
            # Try multiple possible locations
            for possible_dir in [
                f"{self.output_dir}/shadow-results",
                f"{self.output_dir}/logs/{service_name}",
                f"{self.output_dir}/logs"
            ]:
                if os.path.exists(possible_dir):
                    return possible_dir
            return f"{self.output_dir}/logs/{service_name}"
        else:
            return f"{self.output_dir}/logs/{service_name}"

    def _scan_pattern_in_directory(self, directory: str, pattern: str, service_name: str) -> List[str]:
        """Scan directory for files matching a pattern."""
        import glob
        
        try:
            # Handle {service_name} placeholder
            if '{service_name}' in pattern:
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

    def _log_missing_file_diagnostics(self, host_path: str, container_path: str, service_name: str):
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
                similar_files = [f for f in actual_files if filename.lower() in f.lower() or f.lower() in filename.lower()]
                if similar_files:
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
                try:
                    dirs_in_parent = [d for d in os.listdir(parent_parent) if os.path.isdir(os.path.join(parent_parent, d))]
                    self.logger.info(f"Available directories in {parent_parent}: {dirs_in_parent}")
                except OSError:
                    pass

    def get_output_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about collected outputs.

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
        """
        Get the format for a given output type.

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


