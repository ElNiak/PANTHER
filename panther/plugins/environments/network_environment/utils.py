"""Shared utilities for network environment implementations."""

import json
import os
import socket
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml


class NetworkEnvironmentUtils:
    """from typing import Any, Dict, List, Optional, Union, UnionShared utilities for all network environments."""

    @staticmethod
    def generate_compose_file(
        services: Dict[str, Any],
        template_path: str,
        output_path: str,
        additional_params: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate a docker-compose or similar configuration file.

        Args:
            services: Service configurations
            template_path: Path to template file
            output_path: Where to write generated file
            additional_params: Additional template parameters

        Returns:
            Path to generated file
        """
        from jinja2 import Environment, FileSystemLoader

        # Load template
        template_dir = os.path.dirname(template_path)
        template_name = os.path.basename(template_path)

        env = Environment(
            loader=FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        template = env.get_template(template_name)

        # Render template
        params = {
            "services": services,
            "timestamp": time.strftime("%Y%m%d_%H%M%S"),
        }

        if additional_params:
            params.update(additional_params)

        rendered = template.render(**params)

        # Write output
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(rendered)

        return output_path

    @staticmethod
    def wait_for_service_ready(
        service_name: str,
        port: int,
        host: str = "localhost",
        timeout: int = 60,
        check_interval: int = 1,
    ) -> bool:
        """Wait for a service to be ready by checking port availability.

        Args:
            service_name: Name of service (for logging)
            port: Port to check
            host: Host to connect to
            timeout: Maximum wait time
            check_interval: Time between checks

        Returns:
            True if service is ready, False on timeout
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                sock.close()

                if result == 0:
                    return True

            except Exception:
                pass

            time.sleep(check_interval)

        return False

    @staticmethod
    def collect_service_logs(
        service_name: str,
        output_dir: Union[str, Path],
        log_sources: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """Collect logs from various sources for a service.

        Args:
            service_name: Name of the service
            output_dir: Directory to collect logs to
            log_sources: List of log file paths to collect

        Returns:
            Dictionary mapping log type to file path
        """
        output_dir = Path(output_dir)
        service_log_dir = output_dir / "logs" / service_name
        service_log_dir.mkdir(parents=True, exist_ok=True)

        collected_logs = {}

        if log_sources:
            for log_path in log_sources:
                if os.path.exists(log_path):
                    log_name = os.path.basename(log_path)
                    dest_path = service_log_dir / log_name

                    # Copy log file
                    with open(log_path, "r") as src:
                        with open(dest_path, "w") as dst:
                            dst.write(src.read())

                    collected_logs[log_name] = str(dest_path)

        return collected_logs

    @staticmethod
    def parse_service_output(
        output: str, format: str = "text"
    ) -> Union[str, Dict[str, Any], List[Any]]:
        """Parse service output based on expected format.

        Args:
            output: Raw output string
            format: Expected format (text, json, yaml)

        Returns:
            Parsed output in appropriate format
        """
        if format == "json":
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                return output

        elif format == "yaml":
            try:
                return yaml.safe_load(output)
            except yaml.YAMLError:
                return output

        else:
            return output

    @staticmethod
    def create_network_namespace(
        namespace_name: str, ip_range: str = "10.0.0.0/24"
    ) -> bool:
        """Create a network namespace for isolation.

        Args:
            namespace_name: Name for the namespace
            ip_range: IP range for the namespace

        Returns:
            True if successful
        """
        import subprocess

        commands = [
            ["ip", "netns", "add", namespace_name],
            ["ip", "netns", "exec", namespace_name, "ip", "link", "set", "lo", "up"],
        ]

        try:
            for cmd in commands:
                subprocess.run(cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False

    @staticmethod
    def generate_unique_identifier(prefix: str, include_timestamp: bool = True) -> str:
        """Generate a unique identifier for resources.

        Args:
            prefix: Prefix for the identifier
            include_timestamp: Whether to include timestamp

        Returns:
            Unique identifier string
        """
        import uuid

        parts = [prefix]

        if include_timestamp:
            parts.append(time.strftime("%Y%m%d%H%M%S"))

        parts.append(str(uuid.uuid4())[:8])

        return "_".join(parts)

    @staticmethod
    def validate_docker_installation() -> bool:
        """Validate that Docker is installed and accessible.

        Returns:
            True if Docker is available
        """
        import subprocess

        try:
            result = subprocess.run(
                ["docker", "version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    @staticmethod
    def cleanup_docker_resources(
        prefix: str,
        remove_images: bool = True,
        remove_volumes: bool = True,
        remove_networks: bool = True,
    ) -> Dict[str, int]:
        """Clean up Docker resources with a given prefix.

        Args:
            prefix: Prefix to match resources
            remove_images: Whether to remove images
            remove_volumes: Whether to remove volumes
            remove_networks: Whether to remove networks

        Returns:
            Dictionary with counts of removed resources
        """
        import subprocess

        removed = {
            "containers": 0,
            "images": 0,
            "volumes": 0,
            "networks": 0,
        }

        # Remove containers
        try:
            result = subprocess.run(
                ["docker", "ps", "-a", "-q", "--filter", f"name={prefix}"],
                capture_output=True,
                text=True,
            )

            if result.stdout.strip():
                container_ids = result.stdout.strip().split("\n")
                subprocess.run(
                    ["docker", "rm", "-f"] + container_ids,
                    capture_output=True,
                )
                removed["containers"] = len(container_ids)
        except Exception:
            pass

        # Remove images
        if remove_images:
            try:
                result = subprocess.run(
                    ["docker", "images", "-q", f"{prefix}*"],
                    capture_output=True,
                    text=True,
                )

                if result.stdout.strip():
                    image_ids = result.stdout.strip().split("\n")
                    subprocess.run(
                        ["docker", "rmi", "-f"] + image_ids,
                        capture_output=True,
                    )
                    removed["images"] = len(image_ids)
            except Exception:
                pass

        # Remove volumes
        if remove_volumes:
            try:
                result = subprocess.run(
                    ["docker", "volume", "ls", "-q", "--filter", f"name={prefix}"],
                    capture_output=True,
                    text=True,
                )
                if result.stdout.strip():
                    volume_ids = result.stdout.strip().split("\n")
                    subprocess.run(
                        ["docker", "volume", "rm", "-f"] + volume_ids,
                        capture_output=True,
                    )
                    removed["volumes"] = len(volume_ids)
            except Exception:
                pass

        # Remove networks
        if remove_networks:
            try:
                result = subprocess.run(
                    ["docker", "network", "ls", "-q", "--filter", f"name={prefix}"],
                    capture_output=True,
                    text=True,
                )
                if result.stdout.strip():
                    network_ids = result.stdout.strip().split("\n")
                    for nid in network_ids:
                        subprocess.run(
                            ["docker", "network", "rm", nid],
                            capture_output=True,
                        )
                    removed["networks"] = len(network_ids)
            except Exception:
                pass

        return removed

    @staticmethod
    def merge_environment_variables(
        *env_dicts: Dict[str, str],
    ) -> Dict[str, str]:
        """Merge multiple environment variable dictionaries.

        Later dictionaries override earlier ones.

        Args:
            *env_dicts: Variable number of environment dictionaries

        Returns:
            Merged environment variables
        """
        merged = {}

        for env_dict in env_dicts:
            if env_dict:
                merged.update(env_dict)

        return merged
