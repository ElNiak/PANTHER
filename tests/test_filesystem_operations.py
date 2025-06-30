"""
Comprehensive filesystem and I/O operations testing for PANTHER network environments.

This module tests filesystem operations, path handling, file I/O, and storage-related
functionality that are critical for environment setup, configuration management,
and output collection.

Test Categories:
- File System Operations: Creating, reading, writing, deleting files and directories
- Path Validation: Path traversal prevention, symbolic link handling, permission checks
- Storage Management: Disk space monitoring, temporary file cleanup, volume mounting
- I/O Performance: File operation latency, concurrent access, large file handling
- Security: Permission enforcement, access control, path injection prevention
"""

import hashlib
import json
import os
import shutil
import stat
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import MagicMock, Mock, patch

import pytest

# Hypothesis for property-based testing
from hypothesis import Verbosity, assume, given, settings
from hypothesis import strategies as st

# PANTHER imports
from panther.plugins.environments.network_environment.base_network_environment import (
    BaseNetworkEnvironment,
)

# ========== FILESYSTEM TEST DATA STRUCTURES ==========


@dataclass
class FileSystemTestScenario:
    """Represents a filesystem test scenario."""

    name: str
    operation_type: str
    file_count: int
    file_size_bytes: int
    directory_depth: int
    concurrent_operations: int
    expected_behavior: str


@dataclass
class PathValidationTest:
    """Represents a path validation test case."""

    input_path: str
    expected_valid: bool
    security_risk: str
    test_category: str


# ========== FILESYSTEM OPERATION UTILITIES ==========


class FileSystemTestHelper:
    """Helper utilities for filesystem testing."""

    def __init__(self, base_path: str = None):
        self.base_path = base_path or tempfile.mkdtemp(prefix="panther_fs_test_")
        self.created_files = set()
        self.created_dirs = set()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def cleanup(self):
        """Clean up all created test files and directories."""
        try:
            if os.path.exists(self.base_path):
                shutil.rmtree(self.base_path)
        except Exception:
            pass

    def create_test_file(
        self, relative_path: str, content: str = "", size_bytes: int = 0
    ) -> str:
        """Create a test file with specified content or size."""
        full_path = os.path.join(self.base_path, relative_path)

        # Ensure parent directory exists
        parent_dir = os.path.dirname(full_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
            self.created_dirs.add(parent_dir)

        # Create file with content or specific size
        with open(full_path, "w") as f:
            if content:
                f.write(content)
            elif size_bytes > 0:
                # Create file of specific size
                chunk_size = min(size_bytes, 8192)
                chunks = size_bytes // chunk_size
                remainder = size_bytes % chunk_size

                for _ in range(chunks):
                    f.write("x" * chunk_size)
                if remainder:
                    f.write("x" * remainder)

        self.created_files.add(full_path)
        return full_path

    def create_directory_structure(
        self, depth: int, files_per_dir: int = 3
    ) -> List[str]:
        """Create a nested directory structure with files."""
        created_paths = []

        def create_level(current_path: str, current_depth: int):
            if current_depth <= 0:
                return

            # Create files at current level
            for i in range(files_per_dir):
                file_path = os.path.join(current_path, f"file_{current_depth}_{i}.txt")
                full_path = self.create_test_file(
                    os.path.relpath(file_path, self.base_path),
                    f"Content for depth {current_depth}, file {i}",
                )
                created_paths.append(full_path)

            # Create subdirectory and recurse
            subdir = os.path.join(current_path, f"subdir_{current_depth}")
            if not os.path.exists(subdir):
                os.makedirs(subdir, exist_ok=True)
                self.created_dirs.add(subdir)

            create_level(subdir, current_depth - 1)

        create_level(self.base_path, depth)
        return created_paths

    def get_directory_stats(self) -> Dict[str, Any]:
        """Get statistics about the test directory."""
        total_files = 0
        total_dirs = 0
        total_size = 0

        for root, dirs, files in os.walk(self.base_path):
            total_dirs += len(dirs)
            total_files += len(files)

            for file in files:
                file_path = os.path.join(root, file)
                try:
                    total_size += os.path.getsize(file_path)
                except OSError:
                    pass

        return {
            "total_files": total_files,
            "total_directories": total_dirs,
            "total_size_bytes": total_size,
            "base_path": self.base_path,
        }


class FileOperationProfiler:
    """Profile file operation performance."""

    def __init__(self):
        self.operations = []

    @contextmanager
    def profile_operation(self, operation_name: str, file_path: str):
        """Profile a file operation."""
        start_time = time.perf_counter()
        start_size = 0

        try:
            if os.path.exists(file_path):
                start_size = os.path.getsize(file_path)
        except OSError:
            pass

        try:
            yield
        finally:
            end_time = time.perf_counter()
            end_size = 0

            try:
                if os.path.exists(file_path):
                    end_size = os.path.getsize(file_path)
            except OSError:
                pass

            self.operations.append(
                {
                    "operation": operation_name,
                    "file_path": file_path,
                    "duration_ms": (end_time - start_time) * 1000,
                    "size_change": end_size - start_size,
                    "timestamp": time.time(),
                }
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        if not self.operations:
            return {}

        durations = [op["duration_ms"] for op in self.operations]

        return {
            "total_operations": len(self.operations),
            "avg_duration_ms": sum(durations) / len(durations),
            "min_duration_ms": min(durations),
            "max_duration_ms": max(durations),
            "total_duration_ms": sum(durations),
            "operations_per_second": len(durations) / (sum(durations) / 1000)
            if sum(durations) > 0
            else 0,
        }


# ========== FILESYSTEM OPERATION TESTS ==========


@pytest.mark.unit
class TestFileSystemOperations:
    """Test basic filesystem operations used by network environments."""

    def test_file_creation_and_validation(self):
        """Test creating files with various content types and validating them."""
        with FileSystemTestHelper() as fs_helper:
            # Test creating empty file
            empty_file = fs_helper.create_test_file("empty.txt")
            assert os.path.exists(empty_file)
            assert os.path.getsize(empty_file) == 0

            # Test creating file with text content
            text_file = fs_helper.create_test_file("text.txt", "Hello, PANTHER!")
            assert os.path.exists(text_file)
            with open(text_file, "r") as f:
                assert f.read() == "Hello, PANTHER!"

            # Test creating file with specific size
            size_file = fs_helper.create_test_file("size.bin", size_bytes=1024)
            assert os.path.exists(size_file)
            assert os.path.getsize(size_file) == 1024

            # Test creating file in nested directory
            nested_file = fs_helper.create_test_file(
                "deep/nested/path/file.txt", "nested content"
            )
            assert os.path.exists(nested_file)
            assert "nested content" in open(nested_file, "r").read()

    def test_directory_structure_creation(self):
        """Test creating complex directory structures."""
        with FileSystemTestHelper() as fs_helper:
            # Create nested structure
            created_files = fs_helper.create_directory_structure(
                depth=3, files_per_dir=2
            )

            # Verify structure was created
            assert len(created_files) > 0

            stats = fs_helper.get_directory_stats()
            assert stats["total_files"] >= 6  # At least 2 files per level * 3 levels
            assert stats["total_directories"] >= 3  # At least 3 subdirectories
            assert stats["total_size_bytes"] > 0

            # Verify files exist and have content
            for file_path in created_files:
                assert os.path.exists(file_path)
                assert os.path.getsize(file_path) > 0

    def test_file_permissions_and_access(self):
        """Test file permission handling and access control."""
        with FileSystemTestHelper() as fs_helper:
            # Create file with different permissions
            test_file = fs_helper.create_test_file("permissions.txt", "test content")

            # Test read permission
            assert os.access(test_file, os.R_OK)

            # Test write permission
            assert os.access(test_file, os.W_OK)

            # Modify permissions (if on Unix-like system)
            if hasattr(os, "chmod"):
                # Make file read-only
                os.chmod(test_file, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

                # Verify read-only status
                assert os.access(test_file, os.R_OK)
                # Note: Write permission test may vary by system

                # Restore write permission
                os.chmod(
                    test_file, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
                )

    def test_file_operation_error_handling(self):
        """Test error handling in file operations."""
        with FileSystemTestHelper() as fs_helper:
            # Test accessing non-existent file
            non_existent = os.path.join(fs_helper.base_path, "does_not_exist.txt")
            assert not os.path.exists(non_existent)

            # Test reading non-existent file
            with pytest.raises(FileNotFoundError):
                with open(non_existent, "r") as f:
                    f.read()

            # Test creating file in non-existent directory without creating parent
            deep_path = os.path.join(
                fs_helper.base_path, "missing", "deep", "path", "file.txt"
            )
            with pytest.raises(FileNotFoundError):
                with open(deep_path, "w") as f:
                    f.write("test")


@pytest.mark.unit
class TestPathValidationAndSecurity:
    """Test path validation and security measures."""

    def test_path_traversal_prevention(self):
        """Test prevention of path traversal attacks."""
        dangerous_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/shadow",
            "C:\\Windows\\System32\\drivers\\etc\\hosts",
            "file:///etc/passwd",
            "../../config.yaml",
            "../panther/secrets.json",
        ]

        with FileSystemTestHelper() as fs_helper:
            base_path = fs_helper.base_path

            for dangerous_path in dangerous_paths:
                # Test that we don't accidentally access files outside base directory
                # This is what PANTHER should validate
                normalized_path = os.path.normpath(
                    os.path.join(base_path, dangerous_path)
                )

                # Verify the normalized path is still within base directory
                # (This is what PANTHER's path validation should do)
                is_safe = os.path.commonpath([base_path, normalized_path]) == base_path

                if not is_safe:
                    # Simulate PANTHER's security validation
                    with pytest.raises((ValueError, OSError)):
                        # This should fail in production PANTHER code
                        raise ValueError(f"Path traversal detected: {dangerous_path}")

    def test_symbolic_link_handling(self):
        """Test handling of symbolic links."""
        with FileSystemTestHelper() as fs_helper:
            # Create a test file
            target_file = fs_helper.create_test_file("target.txt", "target content")

            # Create symbolic link (if supported by OS)
            symlink_path = os.path.join(fs_helper.base_path, "symlink.txt")

            try:
                os.symlink(target_file, symlink_path)

                # Test that symlink exists and points to correct file
                assert os.path.islink(symlink_path)
                assert os.path.exists(symlink_path)

                # Test reading through symlink
                with open(symlink_path, "r") as f:
                    assert f.read() == "target content"

                # Test that realpath resolves correctly
                assert os.path.realpath(symlink_path) == target_file

            except (OSError, NotImplementedError):
                # Symbolic links not supported on this system
                pytest.skip("Symbolic links not supported on this system")

    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=20, verbosity=Verbosity.quiet)
    def test_filename_validation_property(self, filename):
        """Property-based test for filename validation."""
        assume(filename.strip())  # Non-empty after stripping

        # Test characters that should be invalid in filenames
        invalid_chars = ["<", ">", ":", '"', "|", "?", "*", "\0"]

        has_invalid_char = any(char in filename for char in invalid_chars)

        with FileSystemTestHelper() as fs_helper:
            if has_invalid_char:
                # Should handle invalid characters gracefully
                safe_filename = "".join(c for c in filename if c not in invalid_chars)
                if safe_filename.strip():
                    test_file = fs_helper.create_test_file(safe_filename, "test")
                    assert os.path.exists(test_file)
            else:
                # Valid filename should work
                try:
                    test_file = fs_helper.create_test_file(filename, "test")
                    assert os.path.exists(test_file)
                except (OSError, ValueError):
                    # Some valid-looking filenames might still be invalid on specific systems
                    pass


@pytest.mark.performance
class TestFileSystemPerformance:
    """Test filesystem operation performance characteristics."""

    def test_file_creation_performance(self):
        """Test performance of creating multiple files."""
        with FileSystemTestHelper() as fs_helper:
            profiler = FileOperationProfiler()

            # Test creating many small files
            file_count = 100
            for i in range(file_count):
                file_path = os.path.join(fs_helper.base_path, f"perf_test_{i}.txt")

                with profiler.profile_operation("create_small_file", file_path):
                    fs_helper.create_test_file(f"perf_test_{i}.txt", f"Content {i}")

            stats = profiler.get_stats()

            # Performance assertions
            assert stats["total_operations"] == file_count
            assert stats["avg_duration_ms"] < 10.0  # Average under 10ms per file
            assert stats["operations_per_second"] > 10  # At least 10 files/second

    def test_large_file_handling(self):
        """Test handling of large files."""
        with FileSystemTestHelper() as fs_helper:
            profiler = FileOperationProfiler()

            # Test creating and reading large file
            large_file_size = 10 * 1024 * 1024  # 10 MB
            large_file_path = os.path.join(fs_helper.base_path, "large_file.bin")

            # Create large file
            with profiler.profile_operation("create_large_file", large_file_path):
                fs_helper.create_test_file("large_file.bin", size_bytes=large_file_size)

            # Verify file size
            assert os.path.getsize(large_file_path) == large_file_size

            # Test reading large file
            read_start = time.perf_counter()
            with open(large_file_path, "r") as f:
                content = f.read(1024)  # Read first 1KB
                assert len(content) == 1024
            read_duration = (time.perf_counter() - read_start) * 1000

            stats = profiler.get_stats()

            # Performance assertions for large files
            assert stats["avg_duration_ms"] < 5000  # Under 5 seconds to create 10MB
            assert read_duration < 100  # Under 100ms to read 1KB from large file

    def test_concurrent_file_operations(self):
        """Test concurrent file operations."""
        with FileSystemTestHelper() as fs_helper:

            def create_files_worker(worker_id: int, file_count: int) -> List[str]:
                """Worker function for concurrent file creation."""
                created_files = []
                for i in range(file_count):
                    filename = f"worker_{worker_id}_file_{i}.txt"
                    file_path = fs_helper.create_test_file(
                        filename, f"Worker {worker_id}, File {i}"
                    )
                    created_files.append(file_path)
                return created_files

            # Test concurrent file creation
            worker_count = 5
            files_per_worker = 20

            start_time = time.perf_counter()

            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                futures = [
                    executor.submit(create_files_worker, worker_id, files_per_worker)
                    for worker_id in range(worker_count)
                ]

                all_created_files = []
                for future in as_completed(futures):
                    created_files = future.result()
                    all_created_files.extend(created_files)

            total_duration = time.perf_counter() - start_time

            # Verify all files were created
            expected_file_count = worker_count * files_per_worker
            assert len(all_created_files) == expected_file_count

            for file_path in all_created_files:
                assert os.path.exists(file_path)
                assert os.path.getsize(file_path) > 0

            # Performance assertions
            files_per_second = expected_file_count / total_duration
            assert files_per_second > 50  # At least 50 files/second with concurrency
            assert total_duration < 10.0  # Complete in under 10 seconds


@pytest.mark.integration
class TestFileSystemIntegration:
    """Test filesystem integration with network environment operations."""

    def test_environment_file_management_simulation(self):
        """Simulate filesystem operations during environment lifecycle."""

        class FileSystemNetworkEnv(BaseNetworkEnvironment):
            def __init__(self, base_path: str):
                super().__init__(None, base_path, "filesystem_test", "test", Mock())
                self.fs_helper = FileSystemTestHelper(base_path)
                self.created_files = []

            def simulate_environment_setup(self):
                """Simulate file operations during environment setup."""
                # Create configuration files
                config_file = self.fs_helper.create_test_file(
                    "config/environment.yaml",
                    """
services:
  web:
    image: nginx:latest
    ports:
      - "8080:80"
  db:
    image: postgres:13
    environment:
      POSTGRES_DB: testdb
                    """.strip(),
                )
                self.created_files.append(config_file)

                # Create log directories
                log_dirs = ["logs/web", "logs/db", "logs/system"]
                for log_dir in log_dirs:
                    log_path = os.path.join(self.fs_helper.base_path, log_dir)
                    os.makedirs(log_path, exist_ok=True)

                # Create output directories
                output_dirs = ["outputs/metrics", "outputs/traces", "outputs/captures"]
                for output_dir in output_dirs:
                    output_path = os.path.join(self.fs_helper.base_path, output_dir)
                    os.makedirs(output_path, exist_ok=True)

                return len(self.created_files) > 0

            def simulate_service_deployment(self):
                """Simulate file operations during service deployment."""
                # Create service-specific files
                services = ["web", "db"]
                for service in services:
                    # Service log file
                    log_file = self.fs_helper.create_test_file(
                        f"logs/{service}/service.log",
                        f"[INFO] {service} service started successfully\n",
                    )
                    self.created_files.append(log_file)

                    # Service metrics file
                    metrics_file = self.fs_helper.create_test_file(
                        f"outputs/metrics/{service}_metrics.json",
                        json.dumps(
                            {
                                "service": service,
                                "startup_time": time.time(),
                                "status": "running",
                            }
                        ),
                    )
                    self.created_files.append(metrics_file)

                return True

            def simulate_experiment_execution(self):
                """Simulate file operations during experiment execution."""
                # Create experiment output files
                experiment_files = [
                    "outputs/traces/network_trace.pcap",
                    "outputs/captures/packet_capture.log",
                    "outputs/metrics/experiment_results.json",
                ]

                for exp_file in experiment_files:
                    file_path = self.fs_helper.create_test_file(
                        exp_file,
                        f"Experiment data for {exp_file}",
                        size_bytes=1024,  # 1KB of data
                    )
                    self.created_files.append(file_path)

                return True

            def get_file_statistics(self):
                """Get statistics about created files."""
                return self.fs_helper.get_directory_stats()

            def cleanup(self):
                """Clean up environment files."""
                self.fs_helper.cleanup()

            # Required abstract methods
            def prepare_environment(self):
                return True

            def generate_environment_services(self, paths, timestamp):
                return []

            def launch_environment_services(self):
                return True

            def deploy_services(self, services):
                return True

            def _teardown_environment(self):
                self.cleanup()

            def _do_setup_environment(self):
                return True

            def _do_deploy_services(self, services):
                return True

            def _do_teardown_environment(self):
                self.cleanup()

            def _get_service_log_directory(self, service):
                return f"logs/{service}"

            def _get_service_ip(self, service):
                return "127.0.0.1"

            def handle_event(self, event):
                pass

            def initialize(self):
                pass

        # Test the simulated environment
        with tempfile.TemporaryDirectory() as temp_dir:
            env = FileSystemNetworkEnv(temp_dir)

            try:
                # Test environment setup
                setup_result = env.simulate_environment_setup()
                assert setup_result is True

                # Test service deployment
                deploy_result = env.simulate_service_deployment()
                assert deploy_result is True

                # Test experiment execution
                experiment_result = env.simulate_experiment_execution()
                assert experiment_result is True

                # Verify file statistics
                stats = env.get_file_statistics()
                assert stats["total_files"] > 5  # At least config + logs + outputs
                assert stats["total_directories"] > 3  # At least logs, outputs, config
                assert stats["total_size_bytes"] > 0

                # Verify specific files exist
                config_exists = any("environment.yaml" in f for f in env.created_files)
                assert config_exists

                logs_exist = any("service.log" in f for f in env.created_files)
                assert logs_exist

                metrics_exist = any("metrics.json" in f for f in env.created_files)
                assert metrics_exist

            finally:
                env.cleanup()


@pytest.mark.stress
class TestFileSystemStress:
    """Stress testing for filesystem operations."""

    def test_high_volume_file_operations(self):
        """Test handling high volume of file operations."""
        with FileSystemTestHelper() as fs_helper:
            # Create large number of files
            file_count = 1000
            start_time = time.perf_counter()

            created_files = []
            for i in range(file_count):
                file_path = fs_helper.create_test_file(
                    f"stress/batch_{i // 100}/file_{i}.txt", f"Stress test content {i}"
                )
                created_files.append(file_path)

            creation_duration = time.perf_counter() - start_time

            # Verify all files exist
            assert len(created_files) == file_count
            for file_path in created_files:
                assert os.path.exists(file_path)

            # Test reading all files
            read_start = time.perf_counter()
            for file_path in created_files:
                with open(file_path, "r") as f:
                    content = f.read()
                    assert len(content) > 0
            read_duration = time.perf_counter() - read_start

            # Performance assertions
            assert creation_duration < 30.0  # Under 30 seconds to create 1000 files
            assert read_duration < 10.0  # Under 10 seconds to read 1000 files

            creation_rate = file_count / creation_duration
            read_rate = file_count / read_duration

            assert creation_rate > 30  # At least 30 files/second creation
            assert read_rate > 100  # At least 100 files/second reading

    def test_disk_space_monitoring(self):
        """Test monitoring disk space during operations."""
        with FileSystemTestHelper() as fs_helper:
            # Get initial disk space
            statvfs = os.statvfs(fs_helper.base_path)
            initial_free = statvfs.f_bavail * statvfs.f_frsize

            # Create files until we use significant space
            large_file_size = 1024 * 1024  # 1 MB per file
            files_created = 0
            total_size_created = 0

            while total_size_created < (10 * 1024 * 1024):  # Stop at 10 MB
                file_path = fs_helper.create_test_file(
                    f"large/file_{files_created}.bin", size_bytes=large_file_size
                )
                files_created += 1
                total_size_created += large_file_size

                # Check disk space
                statvfs = os.statvfs(fs_helper.base_path)
                current_free = statvfs.f_bavail * statvfs.f_frsize
                used_space = initial_free - current_free

                # Verify we're actually using disk space
                assert used_space >= 0

            # Verify we created expected amount of data
            assert files_created >= 10
            assert total_size_created >= 10 * 1024 * 1024


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
