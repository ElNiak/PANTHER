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
import os
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path


def _rmtree_onerror(func, path, exc_info):
    """Handle permission errors during shutil.rmtree (e.g. macOS extended attributes)."""
    try:
        os.chmod(path, stat.S_IRWXU)
        func(path)
    except PermissionError:
        # On macOS, com.apple.provenance xattr can block deletion.
        # Strip extended attributes and retry.
        import subprocess as _sp

        _sp.run(["xattr", "-c", path], capture_output=True)
        os.chmod(path, stat.S_IRWXU)
        func(path)


def _copy_md_as_utf8(src, dst):
    """Copy a markdown file, re-encoding to UTF-8 if needed."""
    raw = src.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    dst.write_text(text, encoding="utf-8")


try:
    import docker

    docker_available = True
except ImportError:
    docker_available = False

# Import new metrics system
try:
    from panther.core.metrics.metrics_collector import MetricsCollector
    from panther.core.metrics.metrics_exporter import MetricsExporter
    from panther.core.metrics.resource_monitor import ResourceMonitor

    # Legacy compatibility for existing build system
    _build_collector = None

    def record(name, value, tags=None):
        global _build_collector
        if _build_collector is None:
            import tempfile
            from pathlib import Path

            output_dir = Path(tempfile.mkdtemp())
            _build_collector = MetricsCollector("build_system", output_dir)

        from panther.core.metrics.enums import MetricType

        _build_collector.record_metric(name, MetricType.PERFORMANCE, value, tags or {})

    def flush(kind, extra=None):
        global _build_collector
        if _build_collector is None:
            return "no-metrics"

        # Simple export for build system
        return f"build-{int(time.time())}"

    class ResourceSampler:
        def __init__(self):
            import tempfile
            from pathlib import Path

            from panther.core.metrics.metrics_collector import MetricsCollector

            # Create temporary metrics collection for build system
            output_dir = Path(tempfile.mkdtemp())
            self.collector = MetricsCollector("build_system", output_dir)
            self.monitor = ResourceMonitor(self.collector)

        def start(self):
            self.monitor.start()

        def stop(self):
            self.monitor.stop()
            # Return a simple dict for compatibility
            return {"status": "completed"}

    # Utility functions for build system
    def get_directory_size_mb(path):
        import os

        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
        return total_size / (1024 * 1024)  # Convert to MB

    def get_docker_image_size_mb(name):
        try:
            # Use the singleton DockerBuilder for cached operations
            from panther.core.docker_builder.docker_builder import DockerBuilder

            builder = DockerBuilder.get_instance()

            # First check if image exists using cache
            if not builder.image_exists(name):
                return None

            # Get size from cache if available
            cached_image = builder.image_cache.get_image_by_tag(name)
            if cached_image and cached_image.size > 0:
                return cached_image.size / (1024 * 1024)  # Convert to MB

            # Fallback to direct API call if cache doesn't have size
            if builder.client:
                image = builder.client.images.get(name)
                return image.attrs["Size"] / (1024 * 1024)  # Convert to MB

            return None
        except Exception as e:
            # Log the error for debugging but don't fail the build
            try:
                from panther.core.docker_builder.docker_builder import DockerBuilder

                builder = DockerBuilder.get_instance()
                builder.logger.warning(
                    f"Failed to get Docker image size for '{name}': {e}"
                )
            except:
                pass  # Avoid nested errors
            return None

    def find_latest_wheel(dist_dir, package_name):
        from pathlib import Path

        dist_path = Path(dist_dir)
        wheels = list(dist_path.glob(f"{package_name}*.whl"))
        if not wheels:
            return None
        latest = max(wheels, key=lambda p: p.stat().st_mtime)
        size_mb = latest.stat().st_size / (1024 * 1024)
        return latest, size_mb

    def cleanup_build_artifacts(path):
        return {"cleaned": True}

    METRICS_AVAILABLE = True
    print("New metrics system available.")
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
        self.package_name = "panther-net"
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

    def run_command(self, cmd, cwd=None):
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
                shutil.rmtree(dir_path, onerror=_rmtree_onerror)

        for dir_name in self.tests_gen_dir:
            dir_path = self.project_root / dir_name
            if dir_path.exists():
                print(f"Removing {dir_path}")
                shutil.rmtree(dir_path, onerror=_rmtree_onerror)

        # Remove build directories
        for dir_name in self.build_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists():
                print(f"Removing {dir_path}")
                shutil.rmtree(dir_path, onerror=_rmtree_onerror)

        # Remove egg-info directories
        for egg_info in self.project_root.glob("*.egg-info"):
            print(f"Removing {egg_info}")
            shutil.rmtree(egg_info, onerror=_rmtree_onerror)

        # Remove __pycache__ directories (skip .git and submodule paths)
        for pycache in self.project_root.rglob("__pycache__"):
            if ".git" in pycache.parts:
                continue
            print(f"Removing {pycache}")
            shutil.rmtree(pycache, onerror=_rmtree_onerror)

        # Remove .pyc files (skip .git and submodule paths)
        for pyc_file in self.project_root.rglob("*.pyc"):
            if ".git" in pyc_file.parts:
                continue
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

    # Note: install_slim moved to CLI tools command

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
                        # Note: New metrics system doesn't require pytest plugin
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
                backup_file = (
                    self.project_root
                    / "panther"
                    / "tools"
                    / "docs_gen"
                    / "mkdocs.yml.bak"
                )
                if backup_file.exists():
                    print(f"Restoring backup of mkdocs.yml from {backup_file}")
                    shutil.copy2(backup_file, mkdocs_file)
                print(f"Creating backup of mkdocs.yml -> {backup_file}")
                shutil.copy2(mkdocs_file, backup_file)
            else:
                print("Warning: mkdocs.yml not found, no backup created")

            print("Building documentation...")

            # Phase 1 Automated Documentation Discovery (replaces 85+ manual mappings)
            print("🔍 Generating automated build_dict...")
            try:
                from panther.tools.docs_gen.generate_build_mapping import (
                    get_automated_build_dict,
                )

                build_dict = get_automated_build_dict()
                print(
                    f"📚 Generated {len(build_dict)} documentation mappings automatically"
                )
            except Exception as e:
                print(f"⚠️  Automated discovery failed: {e}")
                print("🔄 Falling back to emergency mappings...")
                # Emergency fallback with core mappings only
                build_dict = {
                    "README.md": "docs/index.md",
                    "QUICK_START.md": "docs/QUICK_START.md",
                    "INSTALL.md": "docs/INSTALL.md",
                    "CONTRIBUTING.md": "docs/contributing.md",
                    "panther/config/README.md": "docs/configuration.md",
                    "panther/core/README.md": "docs/core.md",
                    "panther/plugins/README.md": "docs/plugins_overview.md",
                    "CHANGELOG.md": "docs/changelog.md",
                    "LICENSE.md": "docs/license.md",
                }
                print(f"📋 Using {len(build_dict)} emergency mappings")

            # Clean only docs-related build artifacts (not wheel/dist)
            print("Cleaning documentation build artifacts...")
            for dir_name in ["docs", "site"]:
                dir_path = self.project_root / dir_name
                if dir_path.exists():
                    print(f"Removing {dir_path}")
                    shutil.rmtree(dir_path, onerror=_rmtree_onerror)

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
                self.project_root
                / "panther"
                / "tools"
                / "docs_gen"
                / "mkdocs"
                / "automate_mkdocs.py"
            )
            if mkdocs_script.exists():
                result = self.run_command([sys.executable, str(mkdocs_script)])
                if result != 0:
                    print("Warning: MkDocs automation script failed")
            else:
                print(f"Warning: MkDocs automation script not found at {mkdocs_script}")

            # Generate plugin inventory
            print("Generating plugin inventory...")
            inventory_script = (
                self.project_root
                / "panther"
                / "tools"
                / "docs_gen"
                / "generate_plugin_inventory.py"
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
                    _copy_md_as_utf8(source_path, dest_path)
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
                    _copy_md_as_utf8(md_file, dest_path)

            # Build documentation with MkDocs
            print("Building documentation with MkDocs...")
            result = self.run_command(
                ["mkdocs", "build", "--strict", "--verbose", "--config-file", "mkdocs.yml"]
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

    # Note: check_code_quality moved to CLI check command

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

    # Note: install_precommit moved to CLI tools command

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

    # Note: metrics commands moved to CLI metrics command


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
    python panther_builder.py zip-outputs       # Archive outputs directory

Note: The following commands have been moved to the CLI:
    panther check --all                         # Run code quality checks
    panther metrics list                        # List available metrics
    panther tools install-slim                  # Install Docker optimization tool
    panther tools install-precommit             # Install pre-commit hooks
    panther admin docker --images-all           # Remove Docker images
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
            "zip-outputs",
            "help",
            # Moved commands (for migration messages)
            "check",
            "install-precommit",
            "install-slim",
            "metrics-ls",
            "metrics-show",
            "metrics-export",
            "remove-images-all",
            "remove-images-services",
            "remove-system-all",
            "remove-system-services",
            "remove-volume",
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
        "zip-outputs": build_manager.zip_outputs,
    }

    # Check for moved commands
    moved_commands = {
        "check": "panther check --all",
        "install-precommit": "panther tools install-precommit",
        "install-slim": "panther tools install-slim",
        "metrics-ls": "panther metrics list",
        "metrics-show": "panther metrics show",
        "metrics-export": "panther metrics export",
        "remove-images-all": "panther admin docker --images-all",
        "remove-images-services": "panther admin docker --images-services",
        "remove-system-all": "panther admin docker --system-all",
        "remove-system-services": "panther admin docker --system-services",
        "remove-volume": "panther admin docker --volumes",
    }

    if args.command in moved_commands:
        print(f"ℹ️  The '{args.command}' command has been moved to the PANTHER CLI.")
        print(f"   Please use: {moved_commands[args.command]}")
        print("\nMake sure PANTHER is installed in development mode:")
        print("   python panther_builder.py package-dev")
        return 0

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
