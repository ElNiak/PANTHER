"""Integration tests for unified output collection across all network environments."""

import pytest
import tempfile
import shutil
import yaml
import time
from pathlib import Path
from typing import Dict, List, Optional
import subprocess

from panther.config.config_manager import ConfigManager
from panther.core.experiment_manager import ExperimentManager
from panther.core.observer.management.event_manager import EventManager

class TestUnifiedOutputCollection:
    """Test unified output collection across all network environments."""
    
    @pytest.fixture(scope="class")
    def temp_output_dir(self):
        """Create temporary output directory for tests."""
        temp_dir = tempfile.mkdtemp(prefix="panther_output_test_")
        yield Path(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def config_loader(self):
        """Configuration loader for test configs."""
        def load_config(config_file: str):
            config_path = Path(__file__).parent / config_file
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        return load_config
    
    @pytest.mark.requires_docker
    @pytest.mark.integration
    @pytest.mark.docker_compose
    def test_docker_compose_output_collection(self, temp_output_dir, config_loader):
        """Test output collection in Docker Compose environment."""
        self._test_environment_output_collection(
            config_file="test_configs/docker_compose_minimal.yaml",
            output_dir=temp_output_dir,
            expected_services=["test_server", "test_client"],
            config_loader=config_loader
        )
    
    @pytest.mark.requires_docker
    @pytest.mark.integration
    @pytest.mark.localhost
    def test_localhost_output_collection(self, temp_output_dir, config_loader):
        """Test output collection in localhost single container environment."""
        self._test_environment_output_collection(
            config_file="test_configs/localhost_minimal.yaml", 
            output_dir=temp_output_dir,
            expected_services=["test_service"],
            config_loader=config_loader
        )
    
    @pytest.mark.requires_docker
    @pytest.mark.integration
    @pytest.mark.shadow_ns
    def test_shadow_ns_output_collection(self, temp_output_dir, config_loader):
        """Test output collection in Shadow NS environment."""
        self._test_environment_output_collection(
            config_file="test_configs/shadow_ns_minimal.yaml",
            output_dir=temp_output_dir,
            expected_services=["sim_server", "sim_client"],
            config_loader=config_loader
        )
    
    def _test_environment_output_collection(self, config_file: str, output_dir: Path, 
                                          expected_services: List[str], config_loader):
        """Generic test method for environment output collection."""
        
        # Load test configuration
        config_data = config_loader(config_file)
        
        # Update output directory in config
        config_data['paths']['output_dir'] = str(output_dir)
        if 'log_dir' in config_data['paths']:
            config_data['paths']['log_dir'] = str(output_dir / "logs")
        
        # Create temporary config file
        temp_config_file = output_dir / "test_config.yaml"
        temp_config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(temp_config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        try:
            # Run experiment using PANTHER CLI
            success = self._execute_experiment(temp_config_file, output_dir)
            
            if success:
                # Validate output collection
                self._validate_output_collection(output_dir, expected_services)
            else:
                pytest.fail("Experiment execution failed")
                
        except Exception as e:
            pytest.fail(f"Test failed with exception: {e}")
    
    def _execute_experiment(self, config_file: Path, output_dir: Path) -> bool:
        """Execute the test experiment using PANTHER CLI (real E2E test)."""
        try:
            # Use real PANTHER CLI - this tests the complete system
            cmd = [
                "python", "-m", "panther",
                "--experiment-config", str(config_file),
                "--debug"  # Enable debug logging for better test diagnostics
            ]
            
            # Run from PANTHER root directory
            panther_root = Path(__file__).parent.parent.parent.parent
            
            print(f"Executing PANTHER experiment:")
            print(f"  Command: {' '.join(cmd)}")
            print(f"  Working directory: {panther_root}")
            print(f"  Config file: {config_file}")
            print(f"  Output directory: {output_dir}")
            
            result = subprocess.run(
                cmd,
                cwd=panther_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            print(f"PANTHER execution completed with return code: {result.returncode}")
            
            if result.returncode == 0:
                print("✅ Experiment completed successfully")
                if result.stdout:
                    print("STDOUT (last 50 lines):")
                    stdout_lines = result.stdout.split('\n')
                    for line in stdout_lines[-50:]:
                        if line.strip():
                            print(f"  {line}")
                return True
            else:
                print(f"❌ Experiment failed with return code: {result.returncode}")
                print("STDOUT:")
                print(result.stdout)
                print("STDERR:")
                print(result.stderr)
                return False
                
        except subprocess.TimeoutExpired:
            print("⏰ Experiment timed out after 5 minutes")
            return False
        except Exception as e:
            print(f"💥 Error executing experiment: {e}")
            return False
    
    def _validate_output_collection(self, output_dir: Path, expected_services: List[str]):
        """Validate that outputs were collected correctly."""
        
        for service_name in expected_services:
            service_log_dir = self._find_service_log_directory(output_dir, service_name)
            
            # Standard files that should always exist
            standard_files = ["stdout.log", "stderr.log", "sslkeylogfile.txt"]
            for filename in standard_files:
                file_path = service_log_dir / filename
                assert file_path.exists(), f"Missing {filename} for {service_name} in {service_log_dir}"
                assert file_path.stat().st_size > 0, f"Empty {filename} for {service_name}"
            
            # Packet capture files (at least one should exist)
            pcap_files = list(service_log_dir.glob("*.pcap")) + list(service_log_dir.glob("*.pcapng"))
            assert pcap_files, f"No packet capture files found for {service_name} in {service_log_dir}"
            
            # Enhanced pattern files (if CREATE_ADDITIONAL_FILES was true)
            self._verify_enhanced_patterns(service_log_dir, service_name)
    
    def _find_service_log_directory(self, output_dir: Path, service_name: str) -> Path:
        """Find the log directory for a service (environment-specific)."""
        # Try different possible locations based on environment type
        candidates = [
            output_dir / "logs" / service_name,      # Service-specific directory
            output_dir / "logs",                     # Shared logs directory  
            output_dir / "shadow-results",           # Shadow NS results
            output_dir / f"*{service_name}*",        # Pattern match
        ]
        
        for candidate in candidates:
            if candidate.exists() and candidate.is_dir():
                return candidate
                
        # Try globbing for pattern matches
        for pattern_dir in output_dir.glob(f"**/logs"):
            if pattern_dir.is_dir():
                service_dirs = list(pattern_dir.glob(f"*{service_name}*"))
                if service_dirs:
                    return service_dirs[0]
                # If no service-specific dir, use the logs dir itself
                return pattern_dir
                
        pytest.fail(f"Could not find log directory for service {service_name}. Available: {list(output_dir.rglob('*'))}")
    
    def _verify_enhanced_patterns(self, log_dir: Path, service_name: str):
        """Verify enhanced pattern matching found additional files."""
        
        # SSL keylog pattern files
        ssl_patterns = ["*ssl*key*", "*keylog*", "*tls*key*"]
        ssl_files = []
        for pattern in ssl_patterns:
            ssl_files.extend(log_dir.glob(pattern))
        
        # Should find at least the standard sslkeylogfile.txt
        assert ssl_files, f"No SSL keylog files found for {service_name}"
        
        # Packet capture pattern files  
        pcap_patterns = ["*.pcap", "*.pcapng", "*capture*", "*.cap"]
        pcap_files = []
        for pattern in pcap_patterns:
            pcap_files.extend(log_dir.glob(pattern))
            
        assert pcap_files, f"No packet capture files found for {service_name}"

class TestOutputCollectionEdgeCases:
    """Test edge cases and error scenarios for output collection."""
    
    @pytest.mark.requires_docker
    @pytest.mark.integration
    def test_missing_output_files_graceful_handling(self):
        """Test graceful handling when some output files are missing."""
        # This would be implemented to test scenarios where services
        # don't generate all expected files
        pass
    
    @pytest.mark.requires_docker  
    @pytest.mark.integration
    def test_empty_output_files_handling(self):
        """Test handling of empty output files."""
        # This would test scenarios where files exist but are empty
        pass
    
    @pytest.mark.unit
    def test_path_resolution_methods(self):
        """Test _get_service_log_directory methods for all environments."""
        # This would test the path resolution logic for each environment
        pass

class TestOutputCollectionPerformance:
    """Performance tests for output collection."""
    
    @pytest.mark.requires_docker
    @pytest.mark.integration
    @pytest.mark.performance
    def test_output_collection_timing(self):
        """Test that output collection doesn't significantly slow teardown."""
        # This would measure teardown time with and without output collection
        pass
    
    @pytest.mark.requires_docker
    @pytest.mark.integration 
    @pytest.mark.performance
    def test_large_output_files_handling(self):
        """Test output collection with large files."""
        # This would test scenarios with large output files
        pass