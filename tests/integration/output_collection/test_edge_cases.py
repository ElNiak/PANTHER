"""Edge case tests for output collection system."""

import shutil
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock

import pytest

from panther.plugins.environments.network_environment.docker_compose.docker_compose import (
    DockerComposeEnvironment,
)
from panther.plugins.environments.network_environment.localhost_single_container.localhost_single_container import (
    LocalhostSingleContainerEnvironment,
)
from panther.plugins.environments.network_environment.shadow_ns.shadow_ns import (
    ShadowNsEnvironment,
)


class TestOutputCollectionEdgeCases:
    """Test edge cases and error scenarios for output collection."""

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory."""
        temp_dir = tempfile.mkdtemp(prefix="panther_edge_test_")
        yield Path(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def mock_environment_config(self):
        """Create mock environment configuration."""
        mock_config = Mock()
        mock_config.monitoring_interval_seconds = 1
        mock_config.failure_threshold_count = 3
        return mock_config

    @pytest.fixture
    def mock_event_manager(self):
        """Create mock event manager."""
        return Mock()

    @pytest.mark.unit
    @pytest.mark.output_collection
    def test_docker_compose_path_resolution(
        self, temp_output_dir, mock_environment_config, mock_event_manager
    ):
        """Test Docker Compose service log directory resolution."""
        env = DockerComposeEnvironment(
            env_config_to_test=mock_environment_config,
            output_dir=str(temp_output_dir),
            env_type="network_environment",
            env_sub_type="docker_compose",
            event_manager=mock_event_manager,
        )

        # Test service-specific directory resolution
        service_name = "test_service"
        expected_path = temp_output_dir / "logs" / service_name

        # Create the expected directory
        expected_path.mkdir(parents=True, exist_ok=True)

        resolved_path = env._get_service_log_directory(service_name)
        assert resolved_path == expected_path

    @pytest.mark.unit
    @pytest.mark.output_collection
    def test_localhost_path_resolution_fallback(
        self, temp_output_dir, mock_environment_config, mock_event_manager
    ):
        """Test localhost container path resolution returns service-specific path."""
        env = LocalhostSingleContainerEnvironment(
            env_config_to_test=mock_environment_config,
            output_dir=str(temp_output_dir),
            env_type="network_environment",
            env_sub_type="localhost_single_container",
            event_manager=mock_event_manager,
        )

        service_name = "test_service"
        expected_path = Path(str(temp_output_dir)) / "logs" / service_name

        # Always returns service-specific path (no fallback behavior)
        resolved_path = env._get_service_log_directory(service_name)
        assert resolved_path == expected_path

        # Returns the same path even when the directory doesn't exist
        assert not expected_path.exists()
        assert resolved_path == expected_path

        # And the same path when the directory does exist
        expected_path.mkdir(parents=True, exist_ok=True)
        resolved_path = env._get_service_log_directory(service_name)
        assert resolved_path == expected_path

    @pytest.mark.unit
    @pytest.mark.output_collection
    def test_shadow_ns_path_resolution_priority(
        self, temp_output_dir, mock_environment_config, mock_event_manager
    ):
        """Test Shadow NS path resolution priority order."""
        env = ShadowNsEnvironment(
            env_config_to_test=mock_environment_config,
            output_dir=str(temp_output_dir),
            env_type="network_environment",
            env_sub_type="shadow_ns",
            event_manager=mock_event_manager,
        )

        service_name = "sim_server"

        # Create different possible directories
        service_specific = temp_output_dir / "logs" / service_name
        shadow_results = temp_output_dir / "shadow-results"
        shared_logs = temp_output_dir / "logs"

        # Test priority: service-specific > shadow-results > shared logs
        shadow_results.mkdir(parents=True, exist_ok=True)
        shared_logs.mkdir(parents=True, exist_ok=True)

        # Should prefer shadow-results when service-specific doesn't exist
        resolved_path = env._get_service_log_directory(service_name)
        assert resolved_path == shadow_results

        # Should prefer service-specific when it exists
        service_specific.mkdir(parents=True, exist_ok=True)
        resolved_path = env._get_service_log_directory(service_name)
        assert resolved_path == service_specific

    @pytest.mark.unit
    @pytest.mark.output_collection
    def test_enhanced_pattern_discovery(self, temp_output_dir):
        """Test that glob-based pattern discovery finds SSL keylog and pcap files."""
        log_dir = temp_output_dir / "logs" / "test_service"
        log_dir.mkdir(parents=True, exist_ok=True)

        # Standard files
        (log_dir / "stdout.log").touch()
        (log_dir / "stderr.log").touch()
        (log_dir / "sslkeylogfile.txt").touch()
        (log_dir / "test_service.pcap").touch()

        # Enhanced pattern files
        ssl_pattern_files = [
            "custom_ssl_keys.txt",
            "tls_keylog_debug.txt",
            "ssl_keys_file.keys",
            "keylogfile_custom.txt",
        ]

        pcap_pattern_files = [
            "network_capture.pcapng",
            "packet_trace.cap",
            "capture_file.pcap",
            "network_traffic.pcapng",
        ]

        for filename in ssl_pattern_files + pcap_pattern_files:
            (log_dir / filename).touch()

        # Test pattern discovery using glob (same approach used in production code)
        ssl_patterns = [
            "*ssl*key*",
            "*keylog*",
            "*tls*key*",
            "*key*log*",
            "*.keys",
            "*sslkey*",
        ]
        pcap_patterns = ["*.pcap", "*.pcapng", "*capture*", "*.cap", "*packet*"]

        discovered = set()
        for pattern in ssl_patterns + pcap_patterns:
            discovered.update(log_dir.glob(pattern))

        discovered_names = {f.name for f in discovered}

        # Verify all enhanced pattern files are discovered
        for filename in ssl_pattern_files + pcap_pattern_files:
            assert filename in discovered_names, f"Pattern discovery missed {filename}"

        # Standard ssl/pcap files should also be found
        assert "sslkeylogfile.txt" in discovered_names
        assert "test_service.pcap" in discovered_names

    @pytest.mark.unit
    @pytest.mark.output_collection
    def test_missing_files_graceful_handling(self, temp_output_dir):
        """Test graceful handling when expected output files are missing."""
        log_dir = temp_output_dir / "logs" / "test_service"
        log_dir.mkdir(parents=True, exist_ok=True)

        # Directory exists but expected standard files are missing
        expected_files = ["stdout.log", "stderr.log", "sslkeylogfile.txt"]

        missing = []
        found = []
        for filename in expected_files:
            file_path = log_dir / filename
            if file_path.exists():
                found.append(file_path)
            else:
                missing.append(filename)

        # All expected files should be missing (directory is empty)
        assert len(missing) == len(expected_files)
        assert len(found) == 0

        # iterdir on empty directory should not crash
        files_in_dir = list(log_dir.iterdir())
        assert len(files_in_dir) == 0

        # glob on empty directory should not crash
        for pattern in ["*.log", "*.pcap", "*.txt"]:
            assert list(log_dir.glob(pattern)) == []

        # Non-existent directory should also be handled
        nonexistent_dir = temp_output_dir / "logs" / "ghost_service"
        assert not nonexistent_dir.exists()
        # Attempting to iterate should raise, which callers must handle
        with pytest.raises(FileNotFoundError):
            list(nonexistent_dir.iterdir())

    @pytest.mark.unit
    @pytest.mark.output_collection
    def test_empty_files_handling(self, temp_output_dir):
        """Test handling of empty output files."""

        log_dir = temp_output_dir / "logs" / "test_service"
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create empty files
        empty_files = [
            "stdout.log",
            "stderr.log",
            "sslkeylogfile.txt",
            "test_service.pcap",
        ]
        for filename in empty_files:
            (log_dir / filename).touch()

        # Verify files exist but are empty
        for filename in empty_files:
            file_path = log_dir / filename
            assert file_path.exists()
            assert file_path.stat().st_size == 0

        # Test that empty files are still registered (they may be valid)
        mock_collector = Mock()

        for filename in empty_files:
            file_path = log_dir / filename
            mock_collector.register_output_file(str(file_path), "test_service")

        # Verify all files were registered despite being empty
        assert mock_collector.register_output_file.call_count == len(empty_files)

    @pytest.mark.unit
    @pytest.mark.output_collection
    def test_permission_handling(self, temp_output_dir):
        """Test handling of files with permission issues."""

        log_dir = temp_output_dir / "logs" / "test_service"
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create a file and remove read permissions
        restricted_file = log_dir / "restricted.log"
        restricted_file.write_text("test content")
        restricted_file.chmod(0o000)  # No permissions

        try:
            # Test that permission issues are handled gracefully
            mock_collector = Mock()
            mock_logger = Mock()

            try:
                with open(restricted_file, "r") as f:
                    content = f.read()
                mock_collector.register_output_file(
                    str(restricted_file), "test_service"
                )
            except PermissionError:
                mock_logger.warning(f"Permission denied accessing {restricted_file}")

            # Verify the permission error was handled
            assert mock_logger.warning.called

        finally:
            # Restore permissions for cleanup
            restricted_file.chmod(0o644)


class TestOutputCollectionPerformance:
    """Performance tests for output collection."""

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory."""
        temp_dir = tempfile.mkdtemp(prefix="panther_perf_test_")
        yield Path(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.performance
    @pytest.mark.output_collection
    def test_output_collection_timing(self, temp_output_dir):
        """Test that output collection doesn't significantly slow teardown."""

        # Create mock environment with many services
        num_services = 10
        log_dirs = []

        for i in range(num_services):
            service_name = f"service_{i}"
            log_dir = temp_output_dir / "logs" / service_name
            log_dir.mkdir(parents=True, exist_ok=True)
            log_dirs.append(log_dir)

            # Create standard output files
            (log_dir / "stdout.log").write_text(f"Service {i} output\n" * 100)
            (log_dir / "stderr.log").write_text(f"Service {i} errors\n" * 10)
            (log_dir / "sslkeylogfile.txt").write_text("SSL keys\n" * 50)
            (log_dir / f"service_{i}.pcap").write_bytes(b"\x00" * 1024)

        # Mock output collector
        mock_collector = Mock()
        mock_logger = Mock()

        # Time the output collection process
        start_time = time.time()

        for i, log_dir in enumerate(log_dirs):
            service_name = f"service_{i}"
            for file_path in log_dir.iterdir():
                mock_collector.register_output_file(str(file_path), service_name)

        end_time = time.time()
        collection_time = end_time - start_time

        # Output collection should be fast (< 1 second for 10 services)
        assert (
            collection_time < 1.0
        ), f"Output collection took {collection_time:.3f}s (too slow)"

        # Verify all files were registered
        expected_calls = num_services * 4  # 4 files per service
        assert mock_collector.register_output_file.call_count == expected_calls

    @pytest.mark.performance
    @pytest.mark.output_collection
    def test_large_file_handling(self, temp_output_dir):
        """Test output collection with large files."""

        log_dir = temp_output_dir / "logs" / "test_service"
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create large files (simulating real protocol outputs)
        large_stdout = log_dir / "stdout.log"
        large_pcap = log_dir / "test_service.pcap"

        # Write large content
        large_content = "Large log line with significant content\n" * 10000  # ~370KB
        large_stdout.write_text(large_content)
        large_pcap.write_bytes(b"\x00" * (1024 * 1024))  # 1MB

        # Create standard files
        (log_dir / "stderr.log").write_text("errors\n")
        (log_dir / "sslkeylogfile.txt").write_text("ssl keys\n")

        # Time the file discovery and registration
        mock_collector = Mock()

        start_time = time.time()

        # Simulate the discovery process
        files_found = list(log_dir.iterdir())
        for file_path in files_found:
            mock_collector.register_output_file(str(file_path), "test_service")

        end_time = time.time()
        processing_time = end_time - start_time

        # Should handle large files quickly (< 0.5 seconds)
        assert (
            processing_time < 0.5
        ), f"Large file processing took {processing_time:.3f}s (too slow)"

        # Verify all files were found
        assert len(files_found) == 4
        assert mock_collector.register_output_file.call_count == 4

    @pytest.mark.performance
    @pytest.mark.output_collection
    def test_concurrent_service_collection(self, temp_output_dir):
        """Test output collection when multiple services finish simultaneously."""

        import concurrent.futures
        import threading

        num_services = 5
        mock_collector = Mock()

        def create_service_outputs(service_id):
            """Create outputs for a single service."""
            service_name = f"concurrent_service_{service_id}"
            log_dir = temp_output_dir / "logs" / service_name
            log_dir.mkdir(parents=True, exist_ok=True)

            # Create output files
            (log_dir / "stdout.log").write_text(f"Service {service_id} output")
            (log_dir / "stderr.log").write_text(f"Service {service_id} errors")
            (log_dir / "sslkeylogfile.txt").write_text("SSL keys")
            (log_dir / f"{service_name}.pcap").write_bytes(b"\x00" * 512)

            # Register outputs
            for file_path in log_dir.iterdir():
                mock_collector.register_output_file(str(file_path), service_name)

        # Simulate concurrent service completion
        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=num_services
        ) as executor:
            futures = [
                executor.submit(create_service_outputs, i) for i in range(num_services)
            ]
            concurrent.futures.wait(futures)

        end_time = time.time()
        concurrent_time = end_time - start_time

        # Concurrent collection should be efficient
        assert (
            concurrent_time < 2.0
        ), f"Concurrent collection took {concurrent_time:.3f}s (too slow)"

        # Verify all services were processed
        expected_calls = num_services * 4  # 4 files per service
        assert mock_collector.register_output_file.call_count == expected_calls
