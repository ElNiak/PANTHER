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
import re
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


# ---------------------------------------------------------------------------
# Link-rewriting helpers for documentation copies
# ---------------------------------------------------------------------------
_MD_LINK_RE = re.compile(r"(!?\[([^\]]*)\])\(([^)]+)\)")
_MD_REF_LINK_RE = re.compile(r"^(\s*\[([^\]]+)\]:\s+)(\S+)", re.MULTILINE)
_NON_DOC_EXTS = frozenset(
    {
        ".html",
        ".py",
        ".sh",
        ".txt",
        ".pdf",
        ".yml",
        ".yaml",
        ".json",
        ".toml",
        ".cfg",
        ".ini",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".ico",
        ".c",
        ".h",
        ".cpp",
        ".rs",
        ".go",
        ".java",
    }
)
_URL_PREFIXES = ("http://", "https://", "mailto:", "ftp://", "#")


def _read_md_as_utf8(src):
    """Read a markdown file, decoding to UTF-8."""
    raw = src.read_bytes()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def _strip_non_doc_links(text):
    """Strip links to non-markdown/non-doc targets, keeping display text."""

    def _replace(m):
        display = m.group(2)
        target = m.group(3)
        if any(target.startswith(p) for p in _URL_PREFIXES):
            return m.group(0)
        path_part = target.split("#")[0]
        if not path_part:
            return m.group(0)
        suffix = Path(path_part).suffix.lower()
        # Rewrite .ivy links to .md
        if suffix == ".ivy":
            new_target = str(Path(path_part).with_suffix(".md"))
            if "#" in target:
                new_target += "#" + target.split("#", 1)[1]
            return f"{m.group(1)}({new_target})"
        if suffix in _NON_DOC_EXTS:
            return display
        return m.group(0)

    text = _MD_LINK_RE.sub(_replace, text)

    # Strip reference-style links to non-doc targets
    def _replace_ref(m):
        target = m.group(3)
        if any(target.startswith(p) for p in _URL_PREFIXES):
            return m.group(0)
        suffix = Path(target.split("#")[0]).suffix.lower()
        if suffix in _NON_DOC_EXTS:
            return ""
        return m.group(0)

    text = _MD_REF_LINK_RE.sub(_replace_ref, text)
    return text


# Regex to match single-backtick inline code (not inside code fences).
# Matches `word` but not ``word`` (double-backtick).
_INLINE_CODE_RE = re.compile(r"(?<!`)(`[^`\n]+?`)(?!`)")

# Regex to match [word] patterns that are NOT part of markdown links.
# A markdown link looks like [text](url).  We preserve those and escape
# everything else so autorefs doesn't treat Ivy array syntax as refs.
_MD_LINK_BRACKET_RE = re.compile(r"!?\[([^\]]*)\]\([^)]+\)")
_ALL_BRACKET_RE = re.compile(r"\[([^\]]+)\]")


def _escape_autorefs(text):
    """Escape patterns that mkdocs_autorefs misinterprets in Ivy docs.

    Handles two cases:
    1. Backtick inline code (e.g. ``range``) -> ``<code>range</code>``
    2. Bare square brackets (e.g. ``[packet_number]``) -> ``\\[packet_number\\]``

    Both are only applied outside of fenced code blocks.
    """
    in_fence = False
    lines = text.split("\n")
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            result.append(line)
        elif in_fence:
            result.append(line)
        else:
            line = _INLINE_CODE_RE.sub(_inline_to_html, line)
            line = _escape_bare_brackets(line)
            result.append(line)
    return "\n".join(result)


def _inline_to_html(m):
    """Convert a backtick inline code span to an HTML <code> tag."""
    content = m.group(1)[1:-1]  # strip surrounding backticks
    return f"<code>{content}</code>"


def _escape_bare_brackets(line):
    """Escape square brackets that aren't part of markdown links.

    Uses a placeholder approach: first protect real markdown links
    ``[text](url)`` and ``![alt](url)``, then escape all remaining
    ``[...]`` patterns, then restore the protected links.
    """
    # Collect real markdown links and replace with placeholders
    placeholders = []
    def _protect(m):
        placeholders.append(m.group(0))
        return f"\x00LINK{len(placeholders) - 1}\x00"

    protected = _MD_LINK_BRACKET_RE.sub(_protect, line)
    # Escape all remaining [word] patterns
    escaped = _ALL_BRACKET_RE.sub(lambda m: f"\\[{m.group(1)}\\]", protected)
    # Restore real links
    for i, original in enumerate(placeholders):
        escaped = escaped.replace(f"\x00LINK{i}\x00", original)
    return escaped


def _rewrite_links_flat(text, source_rel_path, build_dict, project_root):
    """Rewrite links for a flat-copied doc file.

    Resolves each relative link against the source file's directory, looks it
    up in *build_dict* to find the flat target name, falls back to hierarchy
    path, or strips the link entirely when the target cannot be resolved.
    """
    source_dir = (project_root / source_rel_path).parent
    flat_lookup = {src: Path(dst).name for src, dst in build_dict.items()}

    def _replace(m):
        prefix = m.group(1)  # e.g. [text] or ![alt]
        display = m.group(2)
        target = m.group(3)
        if any(target.startswith(p) for p in _URL_PREFIXES):
            return m.group(0)
        if "#" in target:
            path_part, fragment = target.split("#", 1)
            fragment = "#" + fragment
        else:
            path_part = target
            fragment = ""
        if not path_part:
            return m.group(0)
        suffix = Path(path_part).suffix.lower()
        # Rewrite .ivy links to .md
        if suffix == ".ivy":
            path_part = str(Path(path_part).with_suffix(".md"))
            suffix = ".md"
        if suffix in _NON_DOC_EXTS:
            return display
        try:
            resolved = (source_dir / path_part).resolve()
            repo_rel = str(resolved.relative_to(project_root))
        except (ValueError, OSError):
            return display
        if repo_rel in flat_lookup:
            return f"{prefix}({flat_lookup[repo_rel]}{fragment})"
        if repo_rel.startswith("panther/") and (project_root / repo_rel).exists():
            return f"{prefix}({repo_rel}{fragment})"
        return display

    text = _MD_LINK_RE.sub(_replace, text)

    # Strip reference-style links to non-doc targets
    def _replace_ref(m):
        target = m.group(3)
        if any(target.startswith(p) for p in _URL_PREFIXES):
            return m.group(0)
        suffix = Path(target.split("#")[0]).suffix.lower()
        if suffix in _NON_DOC_EXTS:
            return ""
        return m.group(0)

    text = _MD_REF_LINK_RE.sub(_replace_ref, text)
    return text


def _copy_md_rewriting_links(
    src, dst, *, source_rel=None, build_dict=None, project_root=None
):
    """Copy markdown file with link rewriting.

    For *flat* copies: provide ``source_rel``, ``build_dict``, ``project_root``
    to resolve links against the build dictionary.
    For *hierarchy* copies: omit those params — only non-doc links are stripped.

    GitHub-style callouts (``> [!NOTE]``) are converted to MkDocs
    admonitions (``!!! note``) automatically so source files stay
    readable on GitHub while MkDocs renders them with proper styling.
    """
    text = _read_md_as_utf8(src)
    if source_rel is not None and build_dict is not None and project_root is not None:
        text = _rewrite_links_flat(text, source_rel, build_dict, project_root)
    else:
        text = _strip_non_doc_links(text)
    # Convert GitHub callouts → MkDocs admonitions
    from panther.tools.docs_gen.convert_admonitions import github_to_mkdocs
    text = github_to_mkdocs(text)
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

    def install_ivy_submodule(self) -> int:
        """Install the panther_ivy submodule in editable mode (if present)."""
        ivy_path = (
            self.project_root
            / "panther"
            / "plugins"
            / "services"
            / "testers"
            / "panther_ivy"
        )
        if not (ivy_path / "setup.py").exists() and not (
            ivy_path / "pyproject.toml"
        ).exists():
            print(
                "Skipping panther_ivy: submodule not initialized"
                " (run 'git submodule update --init')"
            )
            return 0
        print("Installing panther_ivy submodule...")
        old_val = os.environ.get("CMAKE_POLICY_VERSION_MINIMUM")
        os.environ["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        try:
            return self.run_command(
                [sys.executable, "-m", "pip", "install", "--editable", str(ivy_path)]
            )
        finally:
            if old_val is None:
                os.environ.pop("CMAKE_POLICY_VERSION_MINIMUM", None)
            else:
                os.environ["CMAKE_POLICY_VERSION_MINIMUM"] = old_val

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
                raise e

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

            # Copy files according to build_dict (flat copies with link rewriting)
            print("Copying documentation files...")
            for source, destination in build_dict.items():
                source_path = self.project_root / source
                dest_path = self.project_root / destination

                # Create destination directory if it doesn't exist
                dest_path.parent.mkdir(parents=True, exist_ok=True)

                if source_path.exists():
                    print(f"Copying {source} -> {destination}")
                    _copy_md_rewriting_links(
                        source_path,
                        dest_path,
                        source_rel=source,
                        build_dict=build_dict,
                        project_root=self.project_root,
                    )
                else:
                    print(
                        f"Warning: Source file {source} not found, creating placeholder"
                    )
                    # Create a placeholder file
                    with open(dest_path, "w") as f:
                        f.write(f"# {dest_path.stem.replace('_', ' ').title()}\n\n")
                        f.write("This documentation is under development.\n")

            # Copy all markdown files from panther to docs/panther (hierarchy)
            panther_docs_dir = self.project_root / "docs" / "panther"
            panther_src_dir = self.project_root / "panther"
            if not panther_docs_dir.exists():
                print(f"Creating directory {panther_docs_dir}")
                panther_docs_dir.mkdir(parents=True, exist_ok=True)
            # Directories to skip when copying panther/ markdown to docs/
            _skip_dirs = {
                "submodules",  # third-party submodule content (z3, picotls, abc)
                "template",  # mkdocs template files
                "adr",  # architecture decision records (removed from docs)
            }
            for md_file in panther_src_dir.rglob("*.md"):
                if md_file.is_file():
                    # Skip files under excluded directories
                    if any(part in _skip_dirs for part in md_file.parts):
                        continue
                    # Skip README.md when index.md exists in same dir (conflict)
                    if md_file.name == "README.md" and (md_file.parent / "index.md").exists():
                        print(f"Skipping {md_file} (index.md exists in same directory)")
                        continue
                    relative_path = md_file.relative_to(panther_src_dir)
                    dest_path = panther_docs_dir / relative_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    print(f"Copying {md_file} to {dest_path}")
                    _copy_md_rewriting_links(md_file, dest_path)
                    # Escape backtick inline code in panther_ivy docs so
                    # autorefs doesn't try to resolve Ivy identifiers.
                    if "panther_ivy" in md_file.parts:
                        text = dest_path.read_text(encoding="utf-8")
                        dest_path.write_text(
                            _escape_autorefs(text), encoding="utf-8"
                        )

            # Install ivy and convert .ivy files to .md for documentation
            ivy_setup = (
                self.project_root
                / "panther"
                / "plugins"
                / "services"
                / "testers"
                / "panther_ivy"
            )
            if ivy_setup.exists():
                print("Installing ivy for documentation conversion...")
                self.run_command(
                    [sys.executable, "-m", "pip", "install", "-e", str(ivy_setup)]
                )

                # Convert .ivy files to .md using ivy_to_md
                ivy_to_md_script = ivy_setup / "ivy" / "ivy_to_md.py"
                panther_ivy_docs = (
                    self.project_root
                    / "docs"
                    / "panther"
                    / "plugins"
                    / "services"
                    / "testers"
                    / "panther_ivy"
                )
                if ivy_to_md_script.exists():
                    print("Converting .ivy files to .md...")
                    for ivy_file in ivy_setup.rglob("*.ivy"):
                        if "submodules" in ivy_file.parts:
                            continue
                        rel = ivy_file.relative_to(ivy_setup)
                        dest_md = panther_ivy_docs / rel.with_suffix(".md")
                        dest_md.parent.mkdir(parents=True, exist_ok=True)
                        print(f"  Converting {ivy_file.name}...")
                        # ivy_to_md.py defines main() but has no
                        # if __name__ == "__main__" guard, so we must
                        # import and call main() explicitly.
                        self.run_command(
                            [
                                sys.executable,
                                "-c",
                                (
                                    "import sys; "
                                    f"sys.argv = ['ivy_to_md', r'{ivy_file}']; "
                                    "from ivy.ivy_to_md import main; main()"
                                ),
                            ]
                        )
                        # ivy_to_md creates .md next to the .ivy file
                        generated_md = ivy_file.with_suffix(".md")
                        if generated_md.exists():
                            _copy_md_rewriting_links(generated_md, dest_md)
                            # Escape backtick inline code so autorefs
                            # doesn't try to resolve Ivy identifiers.
                            text = dest_md.read_text(encoding="utf-8")
                            dest_md.write_text(
                                _escape_autorefs(text), encoding="utf-8"
                            )
                            print(f"  OK: {ivy_file.name} -> {dest_md}")
                        else:
                            print(
                                f"  WARN: ivy_to_md did not generate {generated_md}"
                            )

            # Generate coverage report for mkdocs-coverage plugin
            htmlcov_dir = self.project_root / "htmlcov"
            placeholder = htmlcov_dir / "index.html"
            has_real_coverage = htmlcov_dir.exists() and not (
                placeholder.exists()
                and "Coverage report not available" in placeholder.read_text()
            )
            if not has_real_coverage:
                result = subprocess.run(
                    [sys.executable, "-c", "import pytest; import pytest_cov"],
                    capture_output=True,
                )
                if result.returncode == 0:
                    print("Generating coverage report...")
                    self.run_command(
                        [
                            sys.executable,
                            "-m",
                            "pytest",
                            "tests/",
                            "-m",
                            "unit",
                            "--cov=panther",
                            "--cov-report=html",
                            "-q",
                            "--no-header",
                        ]
                    )
                else:
                    print(
                        "Skipping coverage report: pytest/pytest-cov not installed"
                        " (install with pip install -e '.[tests]')"
                    )
                    htmlcov_dir.mkdir(exist_ok=True)
                    if not placeholder.exists():
                        placeholder.write_text(
                            "<html><body><p>Coverage report not available."
                            " Install test dependencies to generate."
                            "</p></body></html>"
                        )

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
        return self.run_command(["mkdocs", "serve", "--verbose", "--config-file", "mkdocs.yml"])

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
            + build_manager.install_ivy_submodule()
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
            build_manager.install_dependencies()
            + build_manager.install_editable()
            + build_manager.install_ivy_submodule()
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
