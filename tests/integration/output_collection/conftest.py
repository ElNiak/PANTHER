"""Fixtures and utilities for output collection tests."""

import io
import shutil
import tempfile
from pathlib import Path

import docker
import pytest
import yaml


@pytest.fixture(scope="session")
def docker_client():
    """Docker client for test setup."""
    try:
        return docker.from_env()
    except docker.errors.DockerException:
        pytest.skip("Docker is not available")


@pytest.fixture(scope="session")
def test_service_images(docker_client):
    """Build test service Docker images."""

    images = {}
    test_dir = Path(__file__).parent

    # Build universal test service image
    dockerfile_content = """
FROM python:3.10-slim

RUN apt-get update && apt-get install -y \\
    tshark \\
    netcat-openbsd \\
    && rm -rf /var/lib/apt/lists/*

COPY test_services/universal_test_service.py /app/universal_test_service.py
RUN chmod +x /app/universal_test_service.py

WORKDIR /app
CMD ["python", "/app/universal_test_service.py"]
"""

    # Build the image
    try:
        image, logs = docker_client.images.build(
            fileobj=io.BytesIO(dockerfile_content.encode()),
            tag="panther-test-service:latest",
            rm=True,
            path=str(test_dir),
        )

        images["universal_test_service"] = image

        yield images

    except Exception as e:
        pytest.skip(f"Could not build test service image: {e}")

    finally:
        # Cleanup images
        for image in images.values():
            try:
                docker_client.images.remove(image.id, force=True)
            except:
                pass


@pytest.fixture
def test_config_loader():
    """Configuration loader for test configs."""

    def load_config(config_file: str):
        config_path = Path(__file__).parent / config_file
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    return load_config


@pytest.fixture
def output_validator():
    """Utility for validating output collection results."""

    class OutputValidator:
        @staticmethod
        def validate_standard_outputs(log_dir: Path, service_name: str):
            """Validate standard output files exist."""
            required_files = ["stdout.log", "stderr.log", "sslkeylogfile.txt"]

            for filename in required_files:
                file_path = log_dir / filename
                assert file_path.exists(), f"Missing {filename} for {service_name}"

        @staticmethod
        def validate_pcap_files(log_dir: Path, service_name: str):
            """Validate packet capture files exist."""
            pcap_files = list(log_dir.glob("*.pcap")) + list(log_dir.glob("*.pcapng"))
            assert pcap_files, f"No packet capture files for {service_name}"

        @staticmethod
        def validate_enhanced_patterns(log_dir: Path):
            """Validate enhanced pattern matching."""
            # Check for additional SSL and pcap files
            additional_ssl = [
                f
                for f in log_dir.glob("*")
                if "ssl" in f.name.lower() or "key" in f.name.lower()
            ]
            additional_pcap = [
                f
                for f in log_dir.glob("*")
                if any(ext in f.name for ext in [".cap", "capture", "packet"])
            ]

            return (
                len(additional_ssl) > 1 or len(additional_pcap) > 1
            )  # More than just standard files

    return OutputValidator


@pytest.fixture
def experiment_runner():
    """Utility for running test experiments."""

    class ExperimentRunner:
        def __init__(self, base_dir: Path):
            self.base_dir = base_dir

        def run_experiment(
            self, config_file: Path, output_dir: Path, timeout: int = 300
        ):
            """Run a PANTHER experiment with the given configuration."""
            import subprocess

            cmd = [
                "python",
                "-m",
                "panther",
                "--experiment-config",
                str(config_file),
                "--output-dir",
                str(output_dir),
            ]

            try:
                result = subprocess.run(
                    cmd,
                    cwd=self.base_dir,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )

                return {
                    "success": result.returncode == 0,
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }

            except subprocess.TimeoutExpired:
                return {
                    "success": False,
                    "returncode": -1,
                    "stdout": "",
                    "stderr": "Experiment timed out",
                }

    # Get PANTHER root directory
    panther_root = Path(__file__).parent.parent.parent.parent
    return ExperimentRunner(panther_root)


@pytest.fixture
def temp_experiment_dir():
    """Create temporary directory for experiment outputs."""
    temp_dir = tempfile.mkdtemp(prefix="panther_test_experiment_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def file_monitor():
    """Utility for monitoring file creation and changes."""

    class FileMonitor:
        def __init__(self):
            self.monitored_files = {}

        def add_file(self, file_path: Path):
            """Add a file to monitor."""
            self.monitored_files[str(file_path)] = {
                "exists": file_path.exists(),
                "size": file_path.stat().st_size if file_path.exists() else 0,
                "mtime": file_path.stat().st_mtime if file_path.exists() else 0,
            }

        def check_changes(self):
            """Check for changes in monitored files."""
            changes = {}

            for file_path_str, initial_state in self.monitored_files.items():
                file_path = Path(file_path_str)
                current_state = {
                    "exists": file_path.exists(),
                    "size": file_path.stat().st_size if file_path.exists() else 0,
                    "mtime": file_path.stat().st_mtime if file_path.exists() else 0,
                }

                if current_state != initial_state:
                    changes[file_path_str] = {
                        "initial": initial_state,
                        "current": current_state,
                    }

            return changes

        def wait_for_file(self, file_path: Path, timeout: int = 30):
            """Wait for a file to be created."""
            import time

            start_time = time.time()
            while time.time() - start_time < timeout:
                if file_path.exists():
                    return True
                time.sleep(0.1)
            return False

    return FileMonitor


@pytest.fixture
def cleanup_helper():
    """Helper for cleaning up test resources."""

    cleanup_tasks = []

    class CleanupHelper:
        def add_cleanup(self, cleanup_func, *args, **kwargs):
            """Add a cleanup task to be executed later."""
            cleanup_tasks.append((cleanup_func, args, kwargs))

        def cleanup_docker_containers(self, pattern: str):
            """Clean up Docker containers matching pattern."""
            import subprocess

            try:
                # Stop containers
                subprocess.run(
                    ["docker", "ps", "-q", "-f", f"name={pattern}"],
                    capture_output=True,
                    check=False,
                )
                # Remove containers
                subprocess.run(
                    ["docker", "rm", "-f"] + [], capture_output=True, check=False
                )
            except:
                pass

        def cleanup_docker_images(self, pattern: str):
            """Clean up Docker images matching pattern."""
            import subprocess

            try:
                subprocess.run(
                    ["docker", "rmi", "-f", pattern], capture_output=True, check=False
                )
            except:
                pass

    helper = CleanupHelper()

    yield helper

    # Execute cleanup tasks
    for cleanup_func, args, kwargs in cleanup_tasks:
        try:
            cleanup_func(*args, **kwargs)
        except Exception as e:
            print(f"Cleanup task failed: {e}")
