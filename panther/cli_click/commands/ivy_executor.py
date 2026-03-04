"""Execution layer for panther ivy CLI commands.

Manages Docker, host, and Docker Compose execution of ivy compilation
and test commands.
"""

import json
import os
import shutil
import subprocess
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from panther.plugins.services.testers.panther_ivy.api.types import (
    CommandResult,
    CompileResult,
    ExecutionResult,
    TestRunResult,
)

DOCKER_IMAGE_BASE = "panther_ivy"
CONTAINER_BASE_PATH = "/opt/panther_ivy/protocol-testing"


class ExecutionTarget(Enum):
    DOCKER = "docker"
    HOST = "host"
    COMPOSE = "compose"


class IvyExecutor:
    """Executes CommandResult objects in Docker, Compose, or on host."""

    def __init__(self, target: str = "auto"):
        self._target_preference = target
        self._resolved_target: Optional[ExecutionTarget] = None
        self._ivy_file: Optional[Path] = None
        self._docker_image: Optional[str] = None
        self._compose_service: Optional[str] = None

    def resolve_target(self) -> ExecutionTarget:
        """Resolve execution target based on preference and availability."""
        if self._resolved_target:
            return self._resolved_target

        if self._target_preference == "docker":
            self._resolved_target = ExecutionTarget.DOCKER
            return self._resolved_target

        if self._target_preference == "host":
            self._resolved_target = ExecutionTarget.HOST
            return self._resolved_target

        if self._target_preference == "compose":
            self._resolved_target = ExecutionTarget.COMPOSE
            return self._resolved_target

        # Auto-detect: check Docker image first, then Compose, then host
        if self._docker_image_exists():
            self._resolved_target = ExecutionTarget.DOCKER
            return self._resolved_target

        try:
            self._find_compose_service()
            self._resolved_target = ExecutionTarget.COMPOSE
            return self._resolved_target
        except RuntimeError:
            pass

        if shutil.which("ivyc"):
            self._resolved_target = ExecutionTarget.HOST
            return self._resolved_target

        raise RuntimeError(
            "No execution target available. "
            "Either build the panther_ivy Docker image with 'panther ivy build', "
            "start a Docker Compose stack with an ivy service, "
            "or install ivyc locally."
        )

    def _docker_image_exists(self, image: Optional[str] = None) -> bool:
        """Check if a Docker image exists locally."""
        img = image or f"{DOCKER_IMAGE_BASE}:latest"
        try:
            result = subprocess.run(
                ["docker", "image", "inspect", img],
                capture_output=True,
                timeout=10,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def ensure_docker_image(self, build_mode: str = "", force: bool = False) -> str:
        """Build or find existing panther_ivy Docker image.

        Returns:
            Docker image name:tag string.
        """
        tag = build_mode if build_mode else "latest"
        image = f"{DOCKER_IMAGE_BASE}:{tag}"

        if not force and self._docker_image_exists(image):
            self._docker_image = image
            return image

        # Find Dockerfile in panther_ivy submodule
        import panther_ivy

        submodule_dir = Path(panther_ivy.__file__).parent
        dockerfile = submodule_dir / "Dockerfile"

        if not dockerfile.exists():
            for candidate in [
                submodule_dir / "docker" / "Dockerfile",
                submodule_dir.parent / "Dockerfile",
            ]:
                if candidate.exists():
                    dockerfile = candidate
                    break

        build_args = []
        if build_mode:
            build_args.extend(["--build-arg", f"BUILD_MODE={build_mode}"])

        result = subprocess.run(
            ["docker", "build", *build_args, "-t", image, str(submodule_dir)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Docker build failed:\n{result.stderr}")

        self._docker_image = image
        return image

    def _compute_volume_mounts(self, ivy_file: Path) -> Dict[str, str]:
        """Compute Docker volume mounts to map host paths into container.

        Returns:
            Dict mapping host_path -> container_path.
        """
        ivy_path = ivy_file.resolve() if ivy_file.is_absolute() else ivy_file
        path_str = str(ivy_path)

        # Find protocol-testing root in path
        marker = "protocol-testing"
        idx = path_str.find(marker)
        if idx >= 0:
            host_root = path_str[: idx + len(marker)]
            return {host_root: CONTAINER_BASE_PATH}

        # Fallback: mount the ivy file's grandparent
        return {str(ivy_path.parent.parent): CONTAINER_BASE_PATH}

    def _host_to_container_path(self, host_path: Path) -> str:
        """Translate a host file path to its container equivalent."""
        path_str = str(host_path)
        marker = "protocol-testing"
        idx = path_str.find(marker)
        if idx >= 0:
            relative = path_str[idx + len(marker) :]
            return f"{CONTAINER_BASE_PATH}{relative}"
        return str(host_path)

    def get_base_path(self) -> str:
        """Return the correct protocol-testing base path for the resolved target.

        - Docker/Compose: container path /opt/panther_ivy/protocol-testing
        - Host: auto-detect from panther_ivy submodule location
        """
        target = self.resolve_target()

        if target == ExecutionTarget.HOST:
            import panther_ivy

            submodule_root = Path(panther_ivy.__file__).resolve().parent
            host_path = submodule_root / "protocol-testing"
            return str(host_path)

        # Docker and Compose both run inside the container
        return CONTAINER_BASE_PATH

    def execute(self, cmd: CommandResult) -> ExecutionResult:
        """Execute a CommandResult in the resolved target environment."""
        target = self.resolve_target()

        if target == ExecutionTarget.HOST:
            return self._execute_host(cmd)
        if target == ExecutionTarget.COMPOSE:
            return self._execute_compose(cmd)
        return self._execute_docker(cmd)

    def _execute_host(self, cmd: CommandResult) -> ExecutionResult:
        """Execute commands directly on host."""
        env = os.environ.copy()
        env.update(cmd.environment)

        full_cmd = " && ".join(cmd.commands)
        result = subprocess.run(
            full_cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=cmd.working_dir if os.path.isdir(cmd.working_dir) else None,
            env=env,
        )
        return ExecutionResult(
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            target="host",
        )

    def _execute_docker(self, cmd: CommandResult) -> ExecutionResult:
        """Execute commands inside a Docker container."""
        image = self._docker_image or f"{DOCKER_IMAGE_BASE}:latest"

        # Build docker run command
        docker_cmd = ["docker", "run", "--rm"]

        # Add volume mounts
        if self._ivy_file:
            mounts = self._compute_volume_mounts(self._ivy_file)
            for host_path, container_path in mounts.items():
                docker_cmd.extend(["-v", f"{host_path}:{container_path}"])

        # Add environment variables
        for key, value in cmd.environment.items():
            docker_cmd.extend(["-e", f"{key}={value}"])

        # Set working directory
        docker_cmd.extend(["-w", cmd.working_dir])

        # Image and command
        full_cmd = " && ".join(cmd.commands)
        docker_cmd.extend([image, "bash", "-c", full_cmd])

        result = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
        )
        return ExecutionResult(
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            target="docker",
        )

    def _execute_compose(self, cmd: CommandResult) -> ExecutionResult:
        """Execute commands inside a running Docker Compose service."""
        service = self._compose_service or self._find_compose_service()

        docker_cmd = ["docker", "compose", "exec", "-T"]

        # Add environment variables
        for key, value in cmd.environment.items():
            docker_cmd.extend(["-e", f"{key}={value}"])

        # Set working directory
        docker_cmd.extend(["-w", cmd.working_dir])

        # Service name and command
        full_cmd = " && ".join(cmd.commands)
        docker_cmd.extend([service, "bash", "-c", full_cmd])

        result = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
        )
        return ExecutionResult(
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            target="compose",
        )

    def _find_compose_service(self) -> str:
        """Find a running Docker Compose service with 'ivy' in its name.

        Raises:
            RuntimeError: If no ivy service is found.
        """
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            raise RuntimeError("No running ivy service found in Docker Compose")

        try:
            services = json.loads(result.stdout)
        except json.JSONDecodeError:
            raise RuntimeError("No running ivy service found in Docker Compose")

        for svc in services:
            service_name = svc.get("Service", "")
            if "ivy" in service_name.lower():
                return service_name

        raise RuntimeError(
            "No running ivy service found in Docker Compose. "
            "Use --compose-service to specify the service name."
        )

    def execute_compile(self, compile_result: CompileResult) -> ExecutionResult:
        """Execute setup + compile phases sequentially."""
        # Run setup
        setup_result = self.execute(compile_result.setup_commands)
        if setup_result.exit_code != 0:
            return setup_result

        # Run compilation
        return self.execute(compile_result.compile_commands)

    def execute_test(self, test_result: TestRunResult) -> ExecutionResult:
        """Execute compile + run phases sequentially."""
        compile_exec = self.execute_compile(test_result.compile)
        if compile_exec.exit_code != 0:
            return compile_exec

        return self.execute(test_result.run_commands)
