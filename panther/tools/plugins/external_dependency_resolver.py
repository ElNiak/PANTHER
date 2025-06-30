from typing import Any, Dict, List, Optional, Union

"""
External Dependency Resolver

This module handles validation and checking of non-plugin dependencies
such as Docker, system packages, and external tools.
"""

import logging
import re
import subprocess
from typing import List, Optional, Tuple, Union

from packaging import version


class ExternalDependencyResolver:
    """Handle non-plugin dependencies."""

    def __init__(self):
        self.logger = logging.getLogger("ExternalDependencyResolver")
        self.checkers = {
            "docker": self._check_docker,
            "docker-compose": self._check_docker_compose,
            "cmake": self._check_cmake,
            "z3": self._check_z3,
            "strace": self._check_strace,
            "gperf": self._check_gperf,
            "valgrind": self._check_valgrind,
            "python": self._check_python,
            "rust": self._check_rust,
            "cargo": self._check_cargo,
            "git": self._check_git,
            "gcc": self._check_gcc,
            "g++": self._check_gpp,
            "clang": self._check_clang,
            "make": self._check_make,
        }

    def check_dependency(self, dep_spec: str) -> Tuple[bool, str]:
        """
        Check if external dependency is satisfied.

        Args:
            dep_spec: Dependency specification (e.g., "docker>=20.0", "cmake")

        Returns:
            Tuple of (is_satisfied, message)
        """
        name, version_spec = self._parse_spec(dep_spec)

        if name in self.checkers:
            return self.checkers[name](version_spec)

        # Try generic command check
        return self._check_generic_command(name, version_spec)

    def check_all_dependencies(self, dependencies: List[str]) -> Tuple[bool, List[str]]:
        """
        Check multiple dependencies at once.

        Args:
            dependencies: List of dependency specifications

        Returns:
            Tuple of (all_satisfied, list_of_error_messages)
        """
        errors = []

        for dep in dependencies:
            satisfied, message = self.check_dependency(dep)
            if not satisfied:
                errors.append(f"{dep}: {message}")

        return len(errors) == 0, errors

    def _parse_spec(self, dep_spec: str) -> Union[Tuple[str, str, None]]:
        """Parse dependency specification into name and version."""
        # Match patterns like "name>=version", "name==version", etc.
        match = re.match(r"^([a-zA-Z0-9_-]+)([><=]+)?(.*)$", dep_spec)
        if match:
            name = match.group(1)
            operator = match.group(2) or None
            version_str = match.group(3).strip() if match.group(3) else None

            if operator and version_str:
                version_spec = f"{operator}{version_str}"
            else:
                version_spec = None

            return name, version_spec

        return dep_spec, None

    def _run_command(self, cmd: List[str]) -> Tuple[bool, str]:
        """Run a command and return success status and output."""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return result.returncode == 0, result.stdout.strip()
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except FileNotFoundError:
            return False, "Command not found"
        except Exception as e:
            return False, str(e)

    def _extract_version(self, output: str, patterns: List[str]) -> Optional[str]:
        """Extract version from command output using regex patterns."""
        for pattern in patterns:
            match = re.search(pattern, output, re.MULTILINE | re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _check_version_spec(
        self, current_version: str, version_spec: Optional[str]
    ) -> bool:
        """Check if current version satisfies the specification."""
        if not version_spec:
            return True

        try:
            spec = version.SpecifierSet(version_spec)
            return version.Version(current_version) in spec
        except Exception:
            # If we can't parse versions, assume it's satisfied
            return True

    # Individual dependency checkers

    def _check_docker(self, version_spec: Optional[str]) -> Tuple[bool, str]:
        """Check Docker installation."""
        success, output = self._run_command(["docker", "--version"])
        if not success:
            return False, "Docker is not installed or not in PATH"

        version_str = self._extract_version(output, [r"Docker version ([0-9.]+)"])
        if version_str and version_spec:
            if not self._check_version_spec(version_str, version_spec):
                return (
                    False,
                    f"Docker version {version_str} does not satisfy {version_spec}",
                )

        # Check if Docker daemon is running
        success, _ = self._run_command(["docker", "info"])
        if not success:
            return False, "Docker daemon is not running"

        return True, f"Docker {version_str} is available"

    def _check_docker_compose(self, version_spec: Optional[str]) -> Tuple[bool, str]:
        """Check Docker Compose installation."""
        # Try both docker-compose and docker compose commands
        for cmd in [["docker-compose", "--version"], ["docker", "compose", "version"]]:
            success, output = self._run_command(cmd)
            if success:
                version_str = self._extract_version(
                    output,
                    [
                        r"docker-compose version ([0-9.]+)",
                        r"Docker Compose version v?([0-9.]+)",
                    ],
                )
                if version_str and version_spec:
                    if not self._check_version_spec(version_str, version_spec):
                        return (
                            False,
                            f"Docker Compose version {version_str} does not satisfy {version_spec}",
                        )

                return True, f"Docker Compose {version_str} is available"

        return False, "Docker Compose is not installed or not in PATH"

    def _check_cmake(self, version_spec: Optional[str]) -> Tuple[bool, str]:
        """Check CMake installation."""
        success, output = self._run_command(["cmake", "--version"])
        if not success:
            return False, "CMake is not installed or not in PATH"

        version_str = self._extract_version(output, [r"cmake version ([0-9.]+)"])
        if version_str and version_spec:
            if not self._check_version_spec(version_str, version_spec):
                return (
                    False,
                    f"CMake version {version_str} does not satisfy {version_spec}",
                )

        return True, f"CMake {version_str} is available"

    def _check_z3(self, version_spec: Optional[str]) -> Tuple[bool, str]:
        """Check Z3 solver installation."""
        success, output = self._run_command(["z3", "--version"])
        if not success:
            return False, "Z3 is not installed or not in PATH"

        version_str = self._extract_version(output, [r"Z3 version ([0-9.]+)"])
        if version_str and version_spec:
            if not self._check_version_spec(version_str, version_spec):
                return (
                    False,
                    f"Z3 version {version_str} does not satisfy {version_spec}",
                )

        return True, f"Z3 {version_str} is available"

    def _check_strace(self, version_spec: Optional[str]) -> Tuple[bool, str]:
        """Check strace installation."""
        success, output = self._run_command(["strace", "-V"])
        if not success:
            return False, "strace is not installed or not in PATH"

        version_str = self._extract_version(output, [r"strace -- version ([0-9.]+)"])
        if version_str and version_spec:
            if not self._check_version_spec(version_str, version_spec):
                return (
                    False,
                    f"strace version {version_str} does not satisfy {version_spec}",
                )

        return True, f"strace {version_str} is available"

    def _check_gperf(self, version_spec: Optional[str]) -> Tuple[bool, str]:
        """Check Google Performance Tools installation."""
        # Check for gperftools profiler
        success, _ = self._run_command(["pprof", "--help"])
        if not success:
            return (
                False,
                "Google Performance Tools (gperftools) is not installed or not in PATH",
            )

        # Note: gperf tools typically don't have a simple version command
        # so we just check presence regardless of version_spec
        return True, "Google Performance Tools is available"

    def _check_valgrind(self, version_spec: Optional[str]) -> Tuple[bool, str]:
        """Check Valgrind installation."""
        success, output = self._run_command(["valgrind", "--version"])
        if not success:
            return False, "Valgrind is not installed or not in PATH"

        version_str = self._extract_version(output, [r"valgrind-([0-9.]+)"])
        if version_str and version_spec:
            if not self._check_version_spec(version_str, version_spec):
                return (
                    False,
                    f"Valgrind version {version_str} does not satisfy {version_spec}",
                )

        return True, f"Valgrind {version_str} is available"

    def _check_python(self, version_spec: Optional[str]) -> Tuple[bool, str]:
        """Check Python installation."""
        for cmd in [["python3", "--version"], ["python", "--version"]]:
            success, output = self._run_command(cmd)
            if success:
                version_str = self._extract_version(output, [r"Python ([0-9.]+)"])
                if version_str and version_spec:
                    if not self._check_version_spec(version_str, version_spec):
                        continue

                return True, f"Python {version_str} is available"

        return False, "Python is not installed or version requirement not met"

    def _check_rust(self, version_spec: Optional[str]) -> Tuple[bool, str]:
        """Check Rust installation."""
        success, output = self._run_command(["rustc", "--version"])
        if not success:
            return False, "Rust is not installed or not in PATH"

        version_str = self._extract_version(output, [r"rustc ([0-9.]+)"])
        if version_str and version_spec:
            if not self._check_version_spec(version_str, version_spec):
                return (
                    False,
                    f"Rust version {version_str} does not satisfy {version_spec}",
                )

        return True, f"Rust {version_str} is available"

    def _check_cargo(self, version_spec: Optional[str]) -> Tuple[bool, str]:
        """Check Cargo installation."""
        success, output = self._run_command(["cargo", "--version"])
        if not success:
            return False, "Cargo is not installed or not in PATH"

        version_str = self._extract_version(output, [r"cargo ([0-9.]+)"])
        if version_str and version_spec:
            if not self._check_version_spec(version_str, version_spec):
                return (
                    False,
                    f"Cargo version {version_str} does not satisfy {version_spec}",
                )

        return True, f"Cargo {version_str} is available"

    def _check_git(self, version_spec: Optional[str]) -> Tuple[bool, str]:
        """Check Git installation."""
        success, output = self._run_command(["git", "--version"])
        if not success:
            return False, "Git is not installed or not in PATH"

        version_str = self._extract_version(output, [r"git version ([0-9.]+)"])
        if version_str and version_spec:
            if not self._check_version_spec(version_str, version_spec):
                return (
                    False,
                    f"Git version {version_str} does not satisfy {version_spec}",
                )

        return True, f"Git {version_str} is available"

    def _check_gcc(self, version_spec: Optional[str]) -> Tuple[bool, str]:
        """Check GCC installation."""
        success, output = self._run_command(["gcc", "--version"])
        if not success:
            return False, "GCC is not installed or not in PATH"

        version_str = self._extract_version(output, [r"gcc.* ([0-9.]+)"])
        if version_str and version_spec:
            if not self._check_version_spec(version_str, version_spec):
                return (
                    False,
                    f"GCC version {version_str} does not satisfy {version_spec}",
                )

        return True, f"GCC {version_str} is available"

    def _check_gpp(self, version_spec: Optional[str]) -> Tuple[bool, str]:
        """Check G++ installation."""
        success, output = self._run_command(["g++", "--version"])
        if not success:
            return False, "G++ is not installed or not in PATH"

        version_str = self._extract_version(output, [r"g\+\+.* ([0-9.]+)"])
        if version_str and version_spec:
            if not self._check_version_spec(version_str, version_spec):
                return (
                    False,
                    f"G++ version {version_str} does not satisfy {version_spec}",
                )

        return True, f"G++ {version_str} is available"

    def _check_clang(self, version_spec: Optional[str]) -> Tuple[bool, str]:
        """Check Clang installation."""
        success, output = self._run_command(["clang", "--version"])
        if not success:
            return False, "Clang is not installed or not in PATH"

        version_str = self._extract_version(output, [r"clang version ([0-9.]+)"])
        if version_str and version_spec:
            if not self._check_version_spec(version_str, version_spec):
                return (
                    False,
                    f"Clang version {version_str} does not satisfy {version_spec}",
                )

        return True, f"Clang {version_str} is available"

    def _check_make(self, version_spec: Optional[str]) -> Tuple[bool, str]:
        """Check Make installation."""
        success, output = self._run_command(["make", "--version"])
        if not success:
            return False, "Make is not installed or not in PATH"

        version_str = self._extract_version(output, [r"GNU Make ([0-9.]+)"])
        if version_str and version_spec:
            if not self._check_version_spec(version_str, version_spec):
                return (
                    False,
                    f"Make version {version_str} does not satisfy {version_spec}",
                )

        return True, f"Make {version_str} is available"

    def _check_generic_command(
        self, command: str, version_spec: Optional[str]
    ) -> Tuple[bool, str]:
        """Generic command checker."""
        # Try common version flags
        for flag in ["--version", "-version", "-v", "version"]:
            success, output = self._run_command([command, flag])
            if success:
                if version_spec:
                    # Try to extract version
                    version_str = self._extract_version(
                        output,
                        [
                            r"([0-9]+\.[0-9]+\.[0-9]+)",
                            r"v([0-9]+\.[0-9]+\.[0-9]+)",
                            r"version ([0-9]+\.[0-9]+\.[0-9]+)",
                        ],
                    )
                    if version_str:
                        if not self._check_version_spec(version_str, version_spec):
                            return (
                                False,
                                f"{command} version {version_str} does not satisfy {version_spec}",
                            )

                return True, f"{command} is available"

        # Try just running the command
        success, _ = self._run_command([command])
        if success:
            return True, f"{command} is available"

        return False, f"{command} is not installed or not in PATH"
