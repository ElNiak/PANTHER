#!/usr/bin/env python3
"""
PANTHER Build Script

This script replaces the Makefile and provides a more portable,
Python-based build system for the PANTHER project.

Usage:
    python build.py [command] [options]

Commands:
    package        - Build and install the package
    package-dev    - Build and install in development mode
    package-test   - Run tests after building
    clean          - Clean build artifacts
    install-local  - Install locally in editable mode
    docs           - Build documentation
    check          - Run code quality checks
    help           - Show this help message
"""

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

try:
    import docker

    docker_available = True
except ImportError:
    docker_available = False

# Import metrics system
try:
    from panther.metrics import record, flush, ResourceSampler
    from panther.metrics.utils import (
        get_directory_size_mb,
        get_docker_image_size_mb,
        find_latest_wheel,
        cleanup_build_artifacts,
    )

    METRICS_AVAILABLE = True
    print("Metrics system available.")
except ImportError:
    # Metrics not available, create dummy functions
    print("Metrics system not available. Using dummy functions.")

    def record(name, value, tags=None):
        pass

    def flush(kind, extra=None):
        return "no-metrics"

    class ResourceSampler:
        def start(self):
            pass

        def stop(self):
            return {}

    def get_directory_size_mb(path):
        return 0.0

    def get_docker_image_size_mb(name):
        return None

    def find_latest_wheel(dist_dir, package_name):
        return None

    def cleanup_build_artifacts(path):
        return {}

    METRICS_AVAILABLE = False


class BuildManager:
    """Manages the build process for PANTHER."""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.build_dirs = ["build", "dist"]
        self.docs_dir = ["docs", "site"]
        self.tests_gen_dir = ["htmlcov"]
        self.package_name = "panther_net"
        # Check Python version and virtual environment
        self.min_python_version = (3, 10)
        self.is_venv = hasattr(sys, "real_prefix") or (
            hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
        )

        # Initialize metrics tracking
        self.resource_sampler = ResourceSampler() if METRICS_AVAILABLE else None
        self.build_start_time = None

        if sys.version_info < self.min_python_version:
            print(
                f"Error: Python {'.'.join(map(str, self.min_python_version))} or higher is required."
            )
            print(f"Current Python version: {sys.version.split()[0]}")
            sys.exit(1)

        if not self.is_venv:
            print(
                "Warning: It is recommended to run this script in a Python virtual environment."
            )

        # Check if Docker is available and running
        if docker_available:
            self.docker_available = False
            try:
                client = docker.from_env()
                client.ping()
                self.docker_available = True
                # Check Docker version
                self._check_docker_version(client)
                print("Docker is available and running.")
            except (ImportError, ModuleNotFoundError):
                print(
                    "Warning: Docker Python package not installed. Docker-dependent features will not work."
                )
            except Exception:
                print(
                    "Warning: Docker daemon is not running or not accessible. Docker-dependent features will not work."
                )

    def _check_docker_version(self, client) -> None:
        """Check if Docker version meets minimum requirements."""
        try:
            version_info = client.version()
            version = version_info.get("Version", "0.0.0")

            # Parse version (e.g., "27.1.1" -> [27, 1, 1])
            version_parts = [int(x) for x in version.split(".")]
            min_version = [27, 0, 0]  # Minimum Docker version 27.0.0

            if version_parts < min_version:
                print(
                    f"Warning: Docker version {version} is below recommended minimum 27.0.0"
                )
                print(
                    "Some features may not work correctly with older Docker versions."
                )
            else:
                print(f"Docker version {version} meets requirements (≥27.0.0)")

        except Exception as e:
            print(f"Warning: Could not determine Docker version: {e}")

    def run_command(self, cmd: list[str], cwd: Path | None = None) -> int:
        """Run a command and return the exit code."""
        if not cmd:
            print("Error: Empty command provided")
            return 1

        print(f"Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd, cwd=cwd or self.project_root, check=True, capture_output=False
            )
            return result.returncode
        except subprocess.CalledProcessError as e:
            print(f"Error: Command failed with exit code {e.returncode}")
            return e.returncode
        except FileNotFoundError:
            print(f"Error: Command not found: {cmd[0]}")
            return 1
        except OSError as e:
            print(f"Error: System error occurred: {e}")
            return 1

    def clean(self) -> int:
        """Clean build artifacts."""
        print("Cleaning build artifacts...")

        for dir_name in self.docs_dir:
            dir_path = self.project_root / dir_name
            if dir_path.exists():
                print(f"Removing {dir_path}")
                shutil.rmtree(dir_path)

        for dir_name in self.tests_gen_dir:
            dir_path = self.project_root / dir_name
            if dir_path.exists():
                print(f"Removing {dir_path}")
                shutil.rmtree(dir_path)

        # Remove build directories
        for dir_name in self.build_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists():
                print(f"Removing {dir_path}")
                shutil.rmtree(dir_path)

        # Remove egg-info directories
        for egg_info in self.project_root.glob("*.egg-info"):
            print(f"Removing {egg_info}")
            shutil.rmtree(egg_info)

        # Remove __pycache__ directories
        for pycache in self.project_root.rglob("__pycache__"):
            print(f"Removing {pycache}")
            shutil.rmtree(pycache)

        # Remove .pyc files
        for pyc_file in self.project_root.rglob("*.pyc"):
            print(f"Removing {pyc_file}")
            pyc_file.unlink()

        print("Clean completed.")
        return 0

    def install_dependencies(self) -> int:
        """Install build dependencies."""
        print("Installing build dependencies...")
        return (
            self.run_command(
                [sys.executable, "-m", "pip", "install", "build", "wheel", "setuptools"]
            )
            + self.run_command(
                [sys.executable, "-m", "pip", "install", "--upgrade", "pip"]
            )
            + self.run_command([sys.executable, "-m", "pip", "install", "."])
        )

    def uninstall_package(self) -> int:
        """Uninstall existing package."""
        print(f"Uninstalling existing {self.package_name}...")
        return self.run_command(
            [sys.executable, "-m", "pip", "uninstall", "--yes", self.package_name]
        )

    def build_wheel(self) -> int:
        """Build the wheel package."""
        print("Building wheel...")

        # Start metrics collection
        self.start_metrics_collection("build_wheel")

        try:
            result = self.run_command(
                [sys.executable, "-m", "build", "--wheel", "--no-isolation"]
            )

            # Record build success/failure
            if METRICS_AVAILABLE:
                record(
                    "build.wheel_success",
                    1.0 if result == 0 else 0.0,
                    {"stage": "build_wheel"},
                )

            return result
        finally:
            # Always flush metrics, even on failure
            self.stop_metrics_collection_and_flush(
                "build_wheel",
                {
                    "command": "build_wheel",
                    "success": result == 0 if "result" in locals() else False,
                },
            )

    def install_wheel(self) -> int:
        """Install the built wheel."""
        print("Installing wheel...")
        dist_dir = self.project_root / "dist"
        wheel_files = list(dist_dir.glob(f"{self.package_name}-*.whl"))

        if not wheel_files:
            print("Error: No wheel file found in dist/")
            return 1

        wheel_file = wheel_files[0]  # Use the first (should be only) wheel file
        return self.run_command(
            [sys.executable, "-m", "pip", "install", str(wheel_file)]
        )

    def install_editable(self) -> int:
        """Install in editable/development mode."""
        print("Installing in editable mode...")
        return self.run_command(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--force-reinstall",
                "--editable",
                ".",
            ]
        )

    def install_slim(self) -> int:
        """Install slim tool for Docker image optimization."""
        print("Installing slim tool for Docker image optimization...")

        # Check if slim is already installed
        result = subprocess.run(["which", "slim"], capture_output=True)

        if result.returncode == 0:
            print("✅ slim is already installed at: " + result.stdout.decode().strip())
            return 0

        # Install slim using the official installation script
        print("Downloading and installing slim...")
        try:
            # Use curl to download and pipe to bash
            install_cmd = [
                "curl",
                "-sL",
                "https://raw.githubusercontent.com/slimtoolkit/slim/master/scripts/install-slim.sh",
                "|",
                "sudo",
                "-E",
                "bash",
                "-",
            ]

            # We can't use pipe (|) directly with subprocess, so we need to use shell=True
            shell_cmd = " ".join(install_cmd)
            result = subprocess.run(shell_cmd, shell=True, check=True)

            # Verify installation was successful
            verify_result = subprocess.run(["which", "slim"], capture_output=True)

            if verify_result.returncode == 0:
                print(
                    "✅ slim installed successfully at: "
                    + verify_result.stdout.decode().strip()
                )
                return 0
            else:
                print("❌ slim installation failed. Could not find slim in PATH.")
                return 1

        except subprocess.CalledProcessError as e:
            print(f"❌ Error installing slim: {e}")
            return 1
        except Exception as e:
            print(f"❌ Unexpected error during slim installation: {e}")
            return 1

    def run_tests(self) -> int:
        """Run the test suite."""
        print("Running tests...")

        # Start metrics collection
        self.start_metrics_collection("run_tests")

        try:
            # Install test dependencies
            result = self.run_command(
                [sys.executable, "-m", "pip", "install", ".[tests]"]
            )
            if result != 0:
                return result

            # Run pytest with metrics plugin
            pytest_cmd = [sys.executable, "-m", "pytest", "tests/"]
            if METRICS_AVAILABLE:
                # Add coverage and metrics plugins
                pytest_cmd.extend(
                    [
                        "--cov=panther",
                        "--cov-report=xml",
                        "--cov-report=html",
                        "-p",
                        "panther.metrics.pytest_plugin",
                    ]
                )

            result = self.run_command(pytest_cmd)

            # Record test success/failure
            if METRICS_AVAILABLE:
                record(
                    "test.suite_success",
                    1.0 if result == 0 else 0.0,
                    {"stage": "run_tests"},
                )

            return result
        finally:
            # Always flush metrics, even on failure
            self.stop_metrics_collection_and_flush(
                "run_tests",
                {
                    "command": "run_tests",
                    "success": result == 0 if "result" in locals() else False,
                },
            )

    def build_docs(self) -> int:
        """Build documentation."""

        # Start metrics collection
        self.start_metrics_collection("build_docs")

        try:
            # Create a backup of mkdocs.yml
            mkdocs_file = self.project_root / "mkdocs.yml"
            if mkdocs_file.exists():
                backup_file = self.project_root / "dev" / "docs-gen" / "mkdocs.yml.bak"
                if backup_file.exists():
                    print(f"Restoring backup of mkdocs.yml from {backup_file}")
                    shutil.copy2(backup_file, mkdocs_file)
                print(f"Creating backup of mkdocs.yml -> {backup_file}")
                shutil.copy2(mkdocs_file, backup_file)
            else:
                print("Warning: mkdocs.yml not found, no backup created")

            print("Building documentation...")

            # ...existing build_dict and documentation build logic...

            build_dict = {
                # Home
                "README.md": "docs/index.md",
                # Getting Started
                "QUICK_START.md": "docs/QUICK_START.md",
                "INSTALL.md": "docs/INSTALL.md",
                "panther/config/README.md": "docs/configuration.md",
                "panther/core/README.md": "docs/core.md",
                "WORKFLOW.md": "docs/experimental_workflows.md",
                "panther/core/README.md": "docs/core_workflows.md",
                "panther/webapp/README.md": "docs/web_application_workflows.md",
                # Plugins Overview
                "panther/plugins/README.md": "docs/plugins_overview.md",
                "panther/plugins/plugins_inventory.md": "docs/plugins_inventory.md",
                # Developer Guide
                "CONTRIBUTING.md": "docs/contributing.md",
                "panther/plugins/development.md": "docs/plugin_development.md",
                # Environment Plugins
                "panther/plugins/environments/README.md": "docs/environment_plugins.md",
                "panther/plugins/environments/development.md": "docs/plugin_development_environment.md",
                "panther/plugins/environments/network_environment/README.md": "docs/network_environment.md",
                "panther/plugins/environments/network_environment/development.md": "docs/plugin_development_network.md",
                "panther/plugins/environments/network_environment/docker_compose/README.md": "docs/network_docker_compose.md",
                "panther/plugins/environments/network_environment/localhost_single_container/README.md": "docs/network_localhost_container.md",
                "panther/plugins/environments/network_environment/shadow_ns/README.md": "docs/network_shadow_ns.md",
                # Execution Environment Plugins
                "panther/plugins/environments/execution_environment/README.md": "docs/execution_environment.md",
                "panther/plugins/environments/execution_environment/development.md": "docs/plugin_development_execution.md",
                "panther/plugins/environments/execution_environment/gperf_cpu/README.md": "docs/execution_gperf_cpu.md",
                "panther/plugins/environments/execution_environment/gperf_heap/README.md": "docs/execution_gperf_heap.md",
                "panther/plugins/environments/execution_environment/helgrind/README.md": "docs/execution_helgrind.md",
                "panther/plugins/environments/execution_environment/iterations/README.md": "docs/execution_iterations.md",
                "panther/plugins/environments/execution_environment/memcheck/README.md": "docs/execution_memcheck.md",
                "panther/plugins/environments/execution_environment/strace/README.md": "docs/execution_strace.md",
                # Protocol Plugins
                "panther/plugins/protocols/README.md": "docs/protocol_plugins.md",
                "panther/plugins/protocols/development.md": "docs/protocol_development.md",
                # Client-Server Protocol Plugins
                "panther/plugins/protocols/client_server/README.md": "docs/client_server_protocols.md",
                "panther/plugins/protocols/client_server/index.md": "docs/client_server_index.md",
                "panther/plugins/protocols/client_server/http/README.md": "docs/protocol_http.md",
                "panther/plugins/protocols/client_server/minip/README.md": "docs/protocol_minip.md",
                "panther/plugins/protocols/client_server/quic/README.md": "docs/protocol_quic.md",
                # Peer-to-Peer Protocol Plugins
                "panther/plugins/protocols/peer_to_peer/README.md": "docs/peer_to_peer_protocols.md",
                "panther/plugins/protocols/peer_to_peer/index.md": "docs/peer_to_peer_index.md",
                "panther/plugins/protocols/peer_to_peer/bittorrent/README.md": "docs/protocol_bittorrent.md",
                # Service Plugins
                "panther/plugins/services/README.md": "docs/service_plugins.md",
                "panther/plugins/services/development.md": "docs/service_development.md",
                # IUT (Implementation Under Test) Plugins
                "panther/plugins/services/iut/README.md": "docs/iut_plugins.md",
                "panther/plugins/services/iut/development.md": "docs/iut_development.md",
                "panther/plugins/services/iut/http/README.md": "docs/iut_http.md",
                "panther/plugins/services/iut/minip/README.md": "docs/iut_minip.md",
                "panther/plugins/services/iut/minip/ping_pong/README.md": "docs/iut_minip_ping_pong.md",
                # QUIC IUT Plugins
                "panther/plugins/services/iut/quic/README.md": "docs/iut_quic_overview.md",
                "panther/plugins/services/iut/quic/aioquic/README.md": "docs/iut_quic_aioquic.md",
                "panther/plugins/services/iut/quic/lsquic/README.md": "docs/iut_quic_lsquic.md",
                "panther/plugins/services/iut/quic/mvfst/README.md": "docs/iut_quic_mvfst.md",
                "panther/plugins/services/iut/quic/picoquic/README.md": "docs/iut_quic_picoquic.md",
                "panther/plugins/services/iut/quic/picoquic_shadow/README.md": "docs/iut_quic_picoquic_shadow.md",
                "panther/plugins/services/iut/quic/quant/README.md": "docs/iut_quic_quant.md",
                "panther/plugins/services/iut/quic/quic_go/README.md": "docs/iut_quic_go.md",
                "panther/plugins/services/iut/quic/quiche/README.md": "docs/iut_quic_quiche.md",
                "panther/plugins/services/iut/quic/quinn/README.md": "docs/iut_quic_quinn.md",
                # Tester Service Plugins
                "panther/plugins/services/testers/README.md": "docs/testing_services.md",
                "panther/plugins/services/testers/development.md": "docs/testers_development.md",
                "panther/plugins/services/testers/panther_ivy/README.md": "docs/tester_panther_ivy.md",
                # Documentation
                "dev/docs-gen/README.md": "docs/documentation_readme.md",
                "dev/docs-gen/documentation_WORKFLOW.md": "docs/documentation_WORKFLOW.md",
                "dev/docs-gen/style_guide.md": "docs/style_guide.md",
                "dev/docs-gen/documentation_integration.md": "docs/documentation_integration.md",
                "dev/docs-gen/documentation_links.md": "docs/documentation_links.md",
                "dev/docs-gen/documentation_enhancements.md": "docs/documentation_enhancements.md",
                # Project Information
                "CHANGELOG.md": "docs/changelog.md",
                "LICENSE.md": "docs/license.md",
            }

            self.clean()  # Clean before building docs

            # Clean documentation build artifacts
            print("Cleaning documentation build artifacts...")
            doc_artifacts = ["site"]  # MkDocs default output directory
            for artifact in doc_artifacts:
                artifact_path = self.project_root / artifact
                if artifact_path.exists():
                    print(f"Removing {artifact_path}")
                    shutil.rmtree(artifact_path)

            # Install documentation dependencies
            print("Installing documentation dependencies...")
            result = self.run_command(
                [sys.executable, "-m", "pip", "install", ".[doc]"]
            )
            if result != 0:
                print("Warning: Could not install documentation dependencies")

            # Ensure docs directory exists and is empty
            docs_dir = self.project_root / "docs"
            if docs_dir.exists():
                print(f"Clearing {docs_dir} directory...")
                shutil.rmtree(docs_dir)
            docs_dir.mkdir(exist_ok=True)

            # Run the MkDocs automation script
            print("Running MkDocs automation script...")
            mkdocs_script = (
                self.project_root / "dev" / "docs-gen" / "mkdocs" / "automate_mkdocs.py"
            )
            if mkdocs_script.exists():
                result = self.run_command([sys.executable, str(mkdocs_script)])
                if result != 0:
                    print("Warning: MkDocs automation script failed")
            else:
                print(f"Warning: MkDocs automation script not found at {mkdocs_script}")

            # Run gendocs with the mkgendocs.yml config
            print("Running gendocs with custom configuration...")
            result = self.run_command(["gendocs", "--config", "mkgendocs.yml"])
            if result != 0:
                print("Warning: gendocs command failed")

            # Generate plugin inventory
            print("Generating plugin inventory...")
            inventory_script = (
                self.project_root / "dev" / "docs-gen" / "generate_plugin_inventory.py"
            )
            if inventory_script.exists():
                result = self.run_command(
                    [
                        sys.executable,
                        str(inventory_script),
                        "--format",
                        "markdown",
                        "--output",
                        "panther/plugins/plugins_inventory.md",
                    ]
                )
                if result != 0:
                    print("Warning: Plugin inventory generation failed")

            # Copy files according to build_dict
            print("Copying documentation files...")
            for source, destination in build_dict.items():
                source_path = self.project_root / source
                dest_path = self.project_root / destination

                # Create destination directory if it doesn't exist
                dest_path.parent.mkdir(parents=True, exist_ok=True)

                if source_path.exists():
                    print(f"Copying {source} -> {destination}")
                    shutil.copy2(source_path, dest_path)
                else:
                    print(
                        f"Warning: Source file {source} not found, creating placeholder"
                    )
                    # Create a placeholder file
                    with open(dest_path, "w") as f:
                        f.write(f"# {dest_path.stem.replace('_', ' ').title()}\n\n")
                        f.write("This documentation is under development.\n")

            # Copy all markdown files from panther to docs/panther
            panther_docs_dir = self.project_root / "docs" / "panther"
            panther_src_dir = self.project_root / "panther"
            if not panther_docs_dir.exists():
                print(f"Creating directory {panther_docs_dir}")
                panther_docs_dir.mkdir(parents=True, exist_ok=True)
            for md_file in panther_src_dir.rglob("*.md"):
                if md_file.is_file():
                    relative_path = md_file.relative_to(panther_src_dir)
                    dest_path = panther_docs_dir / relative_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    print(f"Copying {md_file} to {dest_path}")
                    shutil.copy2(md_file, dest_path)


            # Build documentation with MkDocs
            print("Building documentation with MkDocs...")
            result = self.run_command(
                ["mkdocs", "build", "--verbose", "--config-file", "mkdocs.yml"]
            )

            # Record documentation build success/failure
            if METRICS_AVAILABLE:
                record(
                    "docs.build_success",
                    1.0 if result == 0 else 0.0,
                    {"stage": "build_docs"},
                )

            return result
        finally:
            # Always flush metrics, even on failure
            self.stop_metrics_collection_and_flush(
                "build_docs",
                {
                    "command": "build_docs",
                    "success": result == 0 if "result" in locals() else False,
                },
            )

    def serve_docs(self) -> int:
        """Serve the documentation locally."""
        self.build_docs()  # Ensure docs are built first
        print("Serving documentation locally...")

        # Ensure MkDocs is installed
        result = self.run_command(["mkdocs", "--version"])
        if result != 0:
            print("Installing MkDocs...")
            self.run_command(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "mkdocs",
                    "mkdocs-material",
                    "mkdocstrings",
                ]
            )

        # Serve the documentation
        return self.run_command(["mkdocs", "serve", "--config-file", "mkdocs.yml"])

    def deploy_docs(self) -> int:
        """Deploy documentation to GitHub Pages."""
        self.build_docs()  # Ensure docs are built first
        print("Deploying documentation to GitHub Pages...")

        # Deploy the documentation to GitHub Pages
        return self.run_command(
            ["mkdocs", "gh-deploy", "--force", "--clean", "--config-file", "mkdocs.yml"]
        )

    def check_code_quality(self) -> int:
        """Run code quality checks."""
        print("Running code quality checks...")

        # Install check dependencies
        result = self.run_command(
            [sys.executable, "-m", "pip", "install", "flake8", "black", "isort", "mypy"]
        )
        if result != 0:
            print("Warning: Could not install quality check tools")

        # Run checks
        checks = [
            # Check formatting with black
            ([sys.executable, "-m", "black", "--check", "."], "Black formatting check"),
            # Check imports with isort
            (
                [sys.executable, "-m", "isort", "--check-only", "."],
                "Import sorting check",
            ),
            # Check with flake8
            ([sys.executable, "-m", "flake8", "panther/"], "Flake8 linting"),
        ]

        total_errors = 0
        for cmd, description in checks:
            print(f"\n{description}...")
            result = self.run_command(cmd)
            if result != 0:
                total_errors += 1
                print(f"❌ {description} failed")
            else:
                print(f"✅ {description} passed")

        return total_errors

    def zip_outputs(self) -> int:
        """Create a zip archive of outputs directory and clean it."""
        from datetime import datetime

        outputs_dir = self.project_root / "outputs"
        if not outputs_dir.exists() or not any(outputs_dir.iterdir()):
            print("No outputs directory found or it's empty. Nothing to zip.")
            return 0

        # Create timestamp for zip file
        timestamp = datetime.now().strftime("%Y%m%d")
        zip_filename = f"outputs_{timestamp}.zip"
        zip_path = self.project_root / zip_filename

        print(f"Creating zip archive: {zip_filename}")
        result = self.run_command(["zip", "-r", str(zip_path), "outputs"])

        if result == 0:
            print("Removing contents of outputs directory...")
            shutil.rmtree(outputs_dir)
            outputs_dir.mkdir(exist_ok=True)
            print(f"✅ Outputs archived to {zip_filename} and directory cleaned")
        else:
            print("❌ Failed to create zip archive")

        return result

    def remove_images_all(self) -> int:
        """Remove Docker images related to 'panther' and dangling images."""
        if not self.docker_available:
            print("❌ Docker is not available. Cannot remove Docker images.")
            return 1

        print("Removing Docker images with 'panther' in the name...")

        # Get images with "panther" in the name
        result1 = self.run_command(
            [
                "docker",
                "images",
                "--format",
                "{{.Repository}}:{{.Tag}}",
                "|",
                "grep",
                "panther",
                "|",
                "xargs",
                "-r",
                "docker",
                "rmi",
            ]
        )

        # Remove dangling images
        print("Removing dangling Docker images...")
        result2 = self.run_command(
            [
                "docker",
                "images",
                "--filter",
                "dangling=true",
                "-q",
                "|",
                "xargs",
                "-r",
                "docker",
                "rmi",
            ]
        )

        return max(result1, result2)

    def remove_images_services(self) -> int:
        """Remove Docker images related to '_panther' and dangling images."""
        if not self.docker_available:
            print("❌ Docker is not available. Cannot remove Docker images.")
            return 1

        print("Removing Docker images with '_panther' in the name...")

        # Get images with "_panther" in the name
        result1 = self.run_command(
            [
                "docker",
                "images",
                "--format",
                "{{.Repository}}:{{.Tag}}",
                "|",
                "grep",
                "_panther",
                "|",
                "xargs",
                "-r",
                "docker",
                "rmi",
            ]
        )

        # Remove dangling images
        print("Removing dangling Docker images...")
        result2 = self.run_command(
            [
                "docker",
                "images",
                "--filter",
                "dangling=true",
                "-q",
                "|",
                "xargs",
                "-r",
                "docker",
                "rmi",
            ]
        )

        return max(result1, result2)

    def remove_system_all(self) -> int:
        """Remove Docker images with 'panther' and prune system data."""
        if not self.docker_available:
            print("❌ Docker is not available. Cannot remove Docker images.")
            return 1

        print("Removing unused Docker images with 'panther' in the name...")

        # Get images with "panther" in the name
        result1 = self.run_command(
            [
                "docker",
                "images",
                "--format",
                "{{.Repository}}:{{.Tag}}",
                "|",
                "grep",
                "panther",
                "|",
                "xargs",
                "-r",
                "docker",
                "rmi",
            ]
        )

        # Remove dangling images
        print("Removing dangling Docker images...")
        result2 = self.run_command(
            [
                "docker",
                "images",
                "--filter",
                "dangling=true",
                "-q",
                "|",
                "xargs",
                "-r",
                "docker",
                "rmi",
            ]
        )

        # Prune system data
        print("Pruning Docker system data with 'panther' label...")
        result3 = self.run_command(
            ["docker", "system", "prune", "--filter", "label=panther", "-f"]
        )

        return max(result1, result2, result3)

    def remove_system_services(self) -> int:
        """Remove Docker images with '_panther' and prune system data."""
        if not self.docker_available:
            print("❌ Docker is not available. Cannot remove Docker images.")
            return 1

        print("Removing unused Docker images with '_panther' in the name...")

        # Get images with "_panther" in the name
        result1 = self.run_command(
            [
                "docker",
                "images",
                "--format",
                "{{.Repository}}:{{.Tag}}",
                "|",
                "grep",
                "_panther",
                "|",
                "xargs",
                "-r",
                "docker",
                "rmi",
            ]
        )

        # Remove dangling images
        print("Removing dangling Docker images...")
        result2 = self.run_command(
            [
                "docker",
                "images",
                "--filter",
                "dangling=true",
                "-q",
                "|",
                "xargs",
                "-r",
                "docker",
                "rmi",
            ]
        )

        # Prune system data
        print("Pruning Docker system data with '_panther' label...")
        result3 = self.run_command(
            ["docker", "system", "prune", "--filter", "label=_panther", "-f"]
        )

        return max(result1, result2, result3)

    def remove_volume(self) -> int:
        """Remove Docker volumes related to 'panther'."""
        if not self.docker_available:
            print("❌ Docker is not available. Cannot remove Docker volumes.")
            return 1

        print("Removing Docker volumes with 'panther' in the name...")

        return self.run_command(
            [
                "docker",
                "volume",
                "ls",
                "--format",
                "{{.Name}}",
                "|",
                "grep",
                "panther",
                "|",
                "xargs",
                "-r",
                "docker",
                "volume",
                "rm",
            ]
        )

    def install_precommit(self) -> int:
        """Install and configure pre-commit hooks."""
        print("Installing and configuring pre-commit hooks...")

        # Install pre-commit
        print("Installing pre-commit package...")
        result = self.run_command(
            [sys.executable, "-m", "pip", "install", "pre-commit"]
        )
        if result != 0:
            print("❌ Failed to install pre-commit package")
            return result

        # Check if .pre-commit-config.yaml exists in root
        precommit_config = self.project_root / ".pre-commit-config.yaml"

        if not precommit_config.exists():
            print("No .pre-commit-config.yaml found in root. Creating one...")

            # Check if we should use the comprehensive config from dev/ci or the simple one
            ci_config = (
                self.project_root / "dev" / "ci" / ".pre-commit-config-template.yaml"
            )
            workflows_config = (
                self.project_root / ".github" / "workflows" / ".pre-commit-config.yaml"
            )

            if ci_config.exists():
                print(f"Copying comprehensive pre-commit config from {ci_config}")
                shutil.copy2(ci_config, precommit_config)
            elif workflows_config.exists():
                print(f"Copying basic pre-commit config from {workflows_config}")
                shutil.copy2(workflows_config, precommit_config)
            else:
                print("Creating a basic .pre-commit-config.yaml file...")
                # Create a basic pre-commit config
                basic_config = """# See https://pre-commit.com for more information
# See https://pre-commit.com/hooks.html for more hooks
repos:
-   repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
    -   id: trailing-whitespace
    -   id: end-of-file-fixer
    -   id: check-yaml
    -   id: check-added-large-files
    -   id: check-ast
    -   id: check-json
    -   id: check-merge-conflict
    -   id: check-toml
    -   id: pretty-format-json
        args: ["--autofix", "--no-sort-keys"]

-   repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
    -   id: black

-   repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
    -   id: isort

-   repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
    -   id: flake8
        args: [--max-line-length=88, --extend-ignore=E203]
"""
                with open(precommit_config, "w") as f:
                    f.write(basic_config)
                print("✅ Created basic .pre-commit-config.yaml")
        else:
            print("✅ .pre-commit-config.yaml already exists in root")

        # Install the pre-commit hooks
        print("Installing pre-commit hooks into .git/hooks/...")
        result = self.run_command(["pre-commit", "install"])
        if result != 0:
            print("❌ Failed to install pre-commit hooks")
            return result

        # Update hooks to latest versions
        print("Updating pre-commit hooks to latest versions...")
        result = self.run_command(["pre-commit", "autoupdate"])
        if result != 0:
            print(
                "⚠️  Warning: Failed to update pre-commit hooks, but installation was successful"
            )

        print("✅ Pre-commit hooks installed and configured successfully!")
        print("💡 To run pre-commit on all files: pre-commit run --all-files")

        return 0

    def start_metrics_collection(self, operation: str) -> None:
        """Start metrics collection for a build operation."""
        if not METRICS_AVAILABLE:
            return

        self.build_start_time = time.perf_counter()
        if self.resource_sampler:
            self.resource_sampler.start()

        print(f"Starting metrics collection for: {operation}")

    def stop_metrics_collection_and_flush(
        self, operation: str, extra_data: dict = None
    ) -> str:
        """Stop metrics collection and flush results."""
        if not METRICS_AVAILABLE or self.build_start_time is None:
            return "no-metrics"

        # Calculate total operation time
        total_time = time.perf_counter() - self.build_start_time
        record(f"{operation}.total_seconds", total_time, {"stage": operation})

        # Get resource metrics
        resource_metrics = {}
        if self.resource_sampler:
            resource_metrics = self.resource_sampler.stop()
            for metric_name, value in resource_metrics.items():
                record(metric_name, value, {"stage": operation})

        # Add size metrics
        self._record_artifact_sizes(operation)

        # Prepare extra data
        flush_data = {
            "operation": operation,
            "duration": total_time,
            **(extra_data or {}),
        }

        # Flush metrics
        run_id = flush(operation, flush_data)
        print(f"Metrics collection completed. Run ID: {run_id}")

        # Reset for next operation
        self.build_start_time = None

        return run_id

    def _record_artifact_sizes(self, operation: str) -> None:
        """Record sizes of build artifacts."""
        if not METRICS_AVAILABLE:
            return

        # Record dist directory size
        dist_dir = self.project_root / "dist"
        if dist_dir.exists():
            dist_size = get_directory_size_mb(dist_dir)
            record("artifact.dist_mb", dist_size, {"stage": operation})

            # Record individual wheel size if available
            wheel_info = find_latest_wheel(dist_dir, self.package_name)
            if wheel_info:
                wheel_path, wheel_size = wheel_info
                record(
                    "artifact.wheel_mb",
                    wheel_size,
                    {"stage": operation, "file": wheel_path.name},
                )

        # Record build directory size
        build_dir = self.project_root / "build"
        if build_dir.exists():
            build_size = get_directory_size_mb(build_dir)
            record("artifact.build_mb", build_size, {"stage": operation})

        # Record documentation size if relevant
        if operation in ["docs", "build_docs"]:
            docs_dir = self.project_root / "docs"
            site_dir = self.project_root / "site"

            if docs_dir.exists():
                docs_size = get_directory_size_mb(docs_dir)
                record("artifact.docs_mb", docs_size, {"stage": operation})

            if site_dir.exists():
                site_size = get_directory_size_mb(site_dir)
                record("artifact.site_mb", site_size, {"stage": operation})

    def metrics_ls(self) -> int:
        """List available metrics collected during build operations."""
        print("Listing available metrics...")

        if not METRICS_AVAILABLE:
            print("❌ Metrics system is not available. Cannot list metrics.")
            print("Make sure the panther.metrics module is installed and configured.")
            return 1

        try:
            from panther.metrics import list_available_metrics

            metrics = list_available_metrics()
            if not metrics:
                print("No metrics have been collected yet.")
                return 0

            print(f"Found {len(metrics)} available metrics:")
            for i, metric in enumerate(metrics, 1):
                print(f"{i}. {metric}")

            return 0
        except Exception as e:
            print(f"❌ Error listing metrics: {e}")
            return 1

    def metrics_show(self) -> int:
        """Display specific metrics with their values."""
        print("Showing metrics data...")

        if not METRICS_AVAILABLE:
            print("❌ Metrics system is not available. Cannot show metrics.")
            print("Make sure the panther.metrics module is installed and configured.")
            return 1

        try:
            from panther.metrics import get_metrics_data

            metrics_data = get_metrics_data()
            if not metrics_data:
                print("No metrics data available to show.")
                return 0

            print(f"Metrics data summary ({len(metrics_data)} entries):")
            for name, values in metrics_data.items():
                print(f"\n{name}:")
                if isinstance(values, list):
                    for i, value in enumerate(values[:5], 1):  # Show first 5 values
                        print(f"  {i}: {value}")
                    if len(values) > 5:
                        print(f"  ... and {len(values) - 5} more values")
                else:
                    print(f"  Value: {values}")

            return 0
        except Exception as e:
            print(f"❌ Error showing metrics: {e}")
            return 1

    def metrics_export(self) -> int:
        """Export collected metrics to a file."""
        print("Exporting metrics data...")

        if not METRICS_AVAILABLE:
            print("❌ Metrics system is not available. Cannot export metrics.")
            print("Make sure the panther.metrics module is installed and configured.")
            return 1

        try:
            from panther.metrics import export_metrics
            from datetime import datetime

            # Create timestamp for export file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_file = self.project_root / f"metrics_export_{timestamp}.json"

            result = export_metrics(export_file)

            if result:
                print(f"✅ Metrics data exported successfully to {export_file}")
                return 0
            else:
                print("❌ No metrics data available to export.")
                return 1
        except Exception as e:
            print(f"❌ Error exporting metrics: {e}")
            return 1


def main():
    """Main entry point for the build script."""
    parser = argparse.ArgumentParser(
        description="PANTHER Build Script - A portable Python-based build system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python panther_builder.py package           # Build and install package
    python panther_builder.py package-dev       # Install in development mode
    python panther_builder.py clean             # Clean build artifacts
    python panther_builder.py docs              # Build documentation
    python panther_builder.py serve-docs        # Serve documentation locally
    python panther_builder.py deploy-docs       # Deploy documentation to GitHub Pages
    python panther_builder.py check             # Run code quality checks
    python panther_builder.py zip-outputs       # Archive outputs directory
    python panther_builder.py remove-images-all # Remove all Docker images with 'panther'
        """,
    )

    parser.add_argument(
        "command",
        nargs="?",
        default="help",
        choices=[
            "package",
            "package-dev",
            "package-test",
            "clean",
            "install-local",
            "docs",
            "serve-docs",
            "deploy-docs",
            "check",
            "install-precommit",
            "zip-outputs",
            "remove-images-all",
            "remove-images-services",
            "remove-system-all",
            "remove-system-services",
            "remove-volume",
            "help",
        ],
        help="Command to execute",
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )

    args = parser.parse_args()

    if args.command == "help":
        parser.print_help()
        return 0

    # Create build manager
    try:
        build_manager = BuildManager()
    except SystemExit as e:
        return e.code

    # Map commands to methods
    command_map = {
        "package": lambda: (
            build_manager.clean()
            + build_manager.install_dependencies()
            + build_manager.uninstall_package()
            + build_manager.build_wheel()
            + build_manager.install_wheel()
        ),
        "package-dev": lambda: (
            build_manager.clean()
            + build_manager.install_dependencies()
            + build_manager.uninstall_package()
            + build_manager.install_editable()
        ),
        "package-test": lambda: (
            build_manager.clean()
            + build_manager.install_dependencies()
            + build_manager.uninstall_package()
            + build_manager.build_wheel()
            + build_manager.install_wheel()
            + build_manager.run_tests()
        ),
        "clean": build_manager.clean,
        "install-local": lambda: (
            build_manager.install_dependencies() + build_manager.install_editable()
        ),
        "docs": build_manager.build_docs,
        "serve-docs": build_manager.serve_docs,
        "deploy-docs": build_manager.deploy_docs,
        "check": build_manager.check_code_quality,
        "install-precommit": build_manager.install_precommit,
        "zip-outputs": build_manager.zip_outputs,
        "remove-images-all": build_manager.remove_images_all,
        "remove-images-services": build_manager.remove_images_services,
        "remove-system-all": build_manager.remove_system_all,
        "remove-system-services": build_manager.remove_system_services,
        "remove-volume": build_manager.remove_volume,
        "metrics-ls": build_manager.metrics_ls,
        "metrics-show": build_manager.metrics_show,
        "metrics-export": build_manager.metrics_export,
    }

    if args.command not in command_map:
        print(f"Error: Unknown command '{args.command}'")
        parser.print_help()
        return 1

    try:
        result = command_map[args.command]()
        if result is None:
            result = 0
        return result
    except KeyboardInterrupt:
        print("\nBuild interrupted by user")
        return 130
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
