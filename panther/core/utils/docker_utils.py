"""
Docker Utilities

This module provides common Docker operations used throughout PANTHER.
"""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class DockerOperationError(Exception):
    """Exception raised when Docker operations fail."""

    pass


class DockerUtils:
    """Utility class for common Docker operations."""

    @staticmethod
    def is_docker_available() -> bool:
        """
        Check if Docker is available and running.

        Returns:
            bool: True if Docker is available
        """
        try:
            result = subprocess.run(
                ["docker", "version"], capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    @staticmethod
    def image_exists(image_name: str) -> bool:
        """
        Check if a Docker image exists locally.

        Args:
            image_name: Name of the Docker image

        Returns:
            bool: True if image exists
        """
        try:
            result = subprocess.run(
                ["docker", "image", "inspect", image_name],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout checking if image {image_name} exists")
            return False

    @staticmethod
    def build_image(
        dockerfile_path: str | Path,
        image_name: str,
        build_context: str | Path = ".",
        build_args: dict[str, str] | None = None,
        no_cache: bool = False,
    ) -> bool:
        """
        Build a Docker image.

        Args:
            dockerfile_path: Path to the Dockerfile
            image_name: Name to tag the built image
            build_context: Build context directory
            build_args: Build arguments to pass to Docker
            no_cache: Whether to disable build cache

        Returns:
            bool: True if build succeeded

        Raises:
            DockerOperationError: If build fails
        """
        if not DockerUtils.is_docker_available():
            raise DockerOperationError("Docker is not available")

        dockerfile_path = Path(dockerfile_path)
        build_context = Path(build_context)

        if not dockerfile_path.exists():
            raise DockerOperationError(f"Dockerfile not found: {dockerfile_path}")

        if not build_context.exists():
            raise DockerOperationError(f"Build context not found: {build_context}")

        cmd = ["docker", "build", "-f", str(dockerfile_path), "-t", image_name]

        if no_cache:
            cmd.append("--no-cache")

        if build_args:
            for key, value in build_args.items():
                cmd.extend(["--build-arg", f"{key}={value}"])

        cmd.append(str(build_context))

        try:
            logger.info(f"Building Docker image: {image_name}")
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=1800  # 30 minutes timeout
            )

            if result.returncode == 0:
                logger.info(f"Successfully built Docker image: {image_name}")
                return True
            else:
                logger.error(f"Failed to build Docker image {image_name}: {result.stderr}")
                raise DockerOperationError(f"Build failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            raise DockerOperationError(f"Build timeout for image: {image_name}")

    @staticmethod
    def remove_image(image_name: str, force: bool = False) -> bool:
        """
        Remove a Docker image.

        Args:
            image_name: Name of the image to remove
            force: Whether to force removal

        Returns:
            bool: True if removal succeeded
        """
        if not DockerUtils.image_exists(image_name):
            logger.debug(f"Image {image_name} does not exist, skipping removal")
            return True

        cmd = ["docker", "rmi"]
        if force:
            cmd.append("-f")
        cmd.append(image_name)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                logger.info(f"Successfully removed Docker image: {image_name}")
                return True
            else:
                logger.error(f"Failed to remove Docker image {image_name}: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout removing Docker image: {image_name}")
            return False

    @staticmethod
    def list_images(filter_pattern: str | None = None) -> list[str]:
        """
        List Docker images.

        Args:
            filter_pattern: Optional pattern to filter images

        Returns:
            list: List of image names
        """
        cmd = ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"]
        if filter_pattern:
            cmd.extend(["--filter", f"reference={filter_pattern}"])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return [line.strip() for line in result.stdout.splitlines() if line.strip()]
            else:
                logger.error(f"Failed to list Docker images: {result.stderr}")
                return []
        except subprocess.TimeoutExpired:
            logger.error("Timeout listing Docker images")
            return []

    @staticmethod
    def container_exists(container_name: str) -> bool:
        """
        Check if a Docker container exists.

        Args:
            container_name: Name of the container

        Returns:
            bool: True if container exists
        """
        try:
            result = subprocess.run(
                ["docker", "container", "inspect", container_name],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout checking if container {container_name} exists")
            return False

    @staticmethod
    def stop_container(container_name: str, timeout: int = 10) -> bool:
        """
        Stop a Docker container.

        Args:
            container_name: Name of the container to stop
            timeout: Timeout for stopping the container

        Returns:
            bool: True if container was stopped successfully
        """
        if not DockerUtils.container_exists(container_name):
            logger.debug(f"Container {container_name} does not exist")
            return True

        try:
            result = subprocess.run(
                ["docker", "stop", "-t", str(timeout), container_name],
                capture_output=True,
                text=True,
                timeout=timeout + 30,
            )

            if result.returncode == 0:
                logger.info(f"Successfully stopped container: {container_name}")
                return True
            else:
                logger.error(f"Failed to stop container {container_name}: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout stopping container: {container_name}")
            return False

    @staticmethod
    def remove_container(container_name: str, force: bool = False) -> bool:
        """
        Remove a Docker container.

        Args:
            container_name: Name of the container to remove
            force: Whether to force removal

        Returns:
            bool: True if container was removed successfully
        """
        if not DockerUtils.container_exists(container_name):
            logger.debug(f"Container {container_name} does not exist")
            return True

        cmd = ["docker", "rm"]
        if force:
            cmd.append("-f")
        cmd.append(container_name)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                logger.info(f"Successfully removed container: {container_name}")
                return True
            else:
                logger.error(f"Failed to remove container {container_name}: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout removing container: {container_name}")
            return False

    @staticmethod
    def get_container_logs(container_name: str, tail: int | None = None) -> str:
        """
        Get logs from a Docker container.

        Args:
            container_name: Name of the container
            tail: Number of lines to tail (optional)

        Returns:
            str: Container logs
        """
        cmd = ["docker", "logs", container_name]
        if tail is not None:
            cmd.extend(["--tail", str(tail)])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                return result.stdout
            else:
                logger.error(f"Failed to get logs for container {container_name}: {result.stderr}")
                return ""
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout getting logs for container: {container_name}")
            return ""

    @staticmethod
    def cleanup_containers_by_pattern(pattern: str) -> int:
        """
        Stop and remove containers matching a pattern.

        Args:
            pattern: Pattern to match container names

        Returns:
            int: Number of containers cleaned up
        """
        try:
            # List containers matching pattern
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", f"name={pattern}", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                logger.error(f"Failed to list containers: {result.stderr}")
                return 0

            container_names = [name.strip() for name in result.stdout.splitlines() if name.strip()]
            cleaned_count = 0

            for container_name in container_names:
                if DockerUtils.stop_container(container_name):
                    if DockerUtils.remove_container(container_name):
                        cleaned_count += 1

            return cleaned_count

        except subprocess.TimeoutExpired:
            logger.error("Timeout cleaning up containers")
            return 0


class DockerComposeUtils:
    """Utility class for Docker Compose operations."""

    @staticmethod
    def is_compose_available() -> bool:
        """
        Check if Docker Compose is available.

        Returns:
            bool: True if Docker Compose is available
        """
        try:
            result = subprocess.run(
                ["docker-compose", "--version"], capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # Try the newer docker compose command
            try:
                result = subprocess.run(
                    ["docker", "compose", "version"], capture_output=True, text=True, timeout=10
                )
                return result.returncode == 0
            except (subprocess.TimeoutExpired, FileNotFoundError):
                return False

    @staticmethod
    def get_compose_command() -> list[str]:
        """
        Get the appropriate Docker Compose command.

        Returns:
            list: Command to use for Docker Compose
        """
        # Try docker-compose first (legacy)
        try:
            result = subprocess.run(
                ["docker-compose", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return ["docker-compose"]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Try docker compose (new)
        try:
            result = subprocess.run(
                ["docker", "compose", "version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return ["docker", "compose"]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Default to docker-compose if nothing works
        return ["docker-compose"]

    @staticmethod
    def up(compose_file: str | Path, detach: bool = True, build: bool = False) -> bool:
        """
        Run docker-compose up.

        Args:
            compose_file: Path to docker-compose.yml file
            detach: Whether to run in detached mode
            build: Whether to build images before starting

        Returns:
            bool: True if command succeeded
        """
        compose_file = Path(compose_file)
        if not compose_file.exists():
            raise DockerOperationError(f"Docker Compose file not found: {compose_file}")

        cmd = DockerComposeUtils.get_compose_command()
        cmd.extend(["-f", str(compose_file), "up"])

        if detach:
            cmd.append("-d")
        if build:
            cmd.append("--build")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                logger.info(f"Successfully started Docker Compose services from {compose_file}")
                return True
            else:
                logger.error(f"Failed to start Docker Compose services: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            logger.error("Timeout starting Docker Compose services")
            return False

    @staticmethod
    def down(compose_file: str | Path, remove_volumes: bool = False) -> bool:
        """
        Run docker-compose down.

        Args:
            compose_file: Path to docker-compose.yml file
            remove_volumes: Whether to remove volumes

        Returns:
            bool: True if command succeeded
        """
        compose_file = Path(compose_file)
        if not compose_file.exists():
            logger.warning(f"Docker Compose file not found: {compose_file}")
            return True

        cmd = DockerComposeUtils.get_compose_command()
        cmd.extend(["-f", str(compose_file), "down"])

        if remove_volumes:
            cmd.append("-v")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                logger.info(f"Successfully stopped Docker Compose services from {compose_file}")
                return True
            else:
                logger.error(f"Failed to stop Docker Compose services: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            logger.error("Timeout stopping Docker Compose services")
            return False
