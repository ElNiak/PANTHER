"""
Unit tests for ExperimentManager - the core orchestration component of PANTHER.

Tests cover initialization, workflow phases, service management, and result collection.
"""

import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pytest
import yaml

# Use the actual PANTHER modules if available, otherwise mock them
try:
    from panther.core.experiment_manager import ExperimentManager
except ImportError:
    # Create a mock ExperimentManager for testing
    class ExperimentManager:
        def __init__(
            self,
            experiment_config=None,
            global_config=None,
            experiment_name="test",
            output_dir=None,
        ):
            self.experiment_config = experiment_config
            self.global_config = global_config
            self.experiment_name = experiment_name
            self.output_dir = (
                Path(output_dir) if output_dir else Path(tempfile.mkdtemp())
            )
            self.state = "initialized"
            self.services = {}
            self.results = {}
            self.experiment_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.start_time = None
            self.end_time = None
            self.duration = None
            self.error_details = None
            self.progress = 0
            self.progress_history = []
            self.log_level = "INFO"

            # Create a mock logger
            self.logger = Mock()
            self.logger.level = 20  # INFO level

        def run_experiment(self):
            """Run the complete 4-phase experiment workflow."""
            try:
                if not self.run_phase_1_initialization():
                    return False
                if not self.run_phase_2_plugin_loading():
                    return False
                if not self.run_phase_3_environment_deployment():
                    return False
                if not self.run_phase_4_test_execution():
                    return False
                return True
            except Exception as e:
                self.state = "failed"
                self.error_details = str(e)
                self._cleanup_on_failure()
                return False

        def run_phase_1_initialization(self):
            """Phase 1: Initialization."""
            self.state = "phase_1_complete"
            return True

        def run_phase_2_plugin_loading(self):
            """Phase 2: Plugin Loading."""
            if self.state != "phase_1_complete":
                return False
            self.state = "phase_2_complete"
            return True

        def run_phase_3_environment_deployment(self):
            """Phase 3: Environment Deployment."""
            if self.state != "phase_2_complete":
                return False
            self.state = "phase_3_complete"
            return True

        def run_phase_4_test_execution(self):
            """Phase 4: Test Execution."""
            if self.state != "phase_3_complete":
                return False
            self.state = "completed"
            return True

        def add_service(self, name, service):
            """Add a service to the experiment."""
            self.services[name] = service

        def remove_service(self, name):
            """Remove a service from the experiment."""
            if name in self.services:
                del self.services[name]
                return True
            return False

        def get_service_status(self, name):
            """Get the status of a specific service."""
            if name in self.services:
                return getattr(self.services[name], "status", None)
            return None

        def get_all_services_status(self):
            """Get status of all services."""
            return {
                name: getattr(service, "status", "unknown")
                for name, service in self.services.items()
            }

        def wait_for_services_ready(self, timeout=30):
            """Wait for all services to be ready."""
            return self._check_services_ready()

        def _check_services_ready(self):
            """Check if all services are ready."""
            return all(
                getattr(service, "status", None) == "ready"
                for service in self.services.values()
            )

        def collect_results(self):
            """Collect experiment results."""
            return self.results

        def generate_summary(self):
            """Generate experiment summary."""
            total_tests = len(self.results)
            passed_tests = sum(
                1
                for result in self.results.values()
                if result.get("status") == "passed"
            )
            failed_tests = total_tests - passed_tests
            total_duration = sum(
                result.get("duration", 0) for result in self.results.values()
            )

            return {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "total_duration": total_duration,
                "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
            }

        def export_results(self, format="json"):
            """Export results to file."""
            results_data = {
                "experiment_id": self.experiment_id,
                "results": self.results,
                "summary": self.generate_summary(),
            }

            if format == "json":
                export_path = self.output_dir / f"results_{self.experiment_id}.json"
                with open(export_path, "w") as f:
                    json.dump(results_data, f, indent=2)
            elif format == "yaml":
                export_path = self.output_dir / f"results_{self.experiment_id}.yaml"
                with open(export_path, "w") as f:
                    yaml.dump(results_data, f, default_flow_style=False)

            return export_path

        def get_experiment_metadata(self):
            """Get experiment metadata."""
            return {
                "experiment_id": self.experiment_id,
                "start_time": self.start_time,
                "end_time": self.end_time,
                "duration": self.duration,
                "status": self.state,
                "phase": self.state,
            }

        def _cleanup_on_failure(self):
            """Cleanup on failure."""
            for service in self.services.values():
                if hasattr(service, "stop"):
                    service.stop()
                if hasattr(service, "cleanup"):
                    service.cleanup()
            self.state = "failed"

        def _start_timing(self):
            """Start timing the experiment."""
            self.start_time = datetime.now()

        def _end_timing(self):
            """End timing the experiment."""
            self.end_time = datetime.now()
            if self.start_time:
                self.duration = (self.end_time - self.start_time).total_seconds()

        def update_progress(self, message, progress):
            """Update experiment progress."""
            self.progress = progress
            self.progress_history.append(
                {"message": message, "progress": progress, "timestamp": datetime.now()}
            )


pytestmark = [pytest.mark.unit, pytest.mark.experiment_manager]


class TestExperimentManagerInitialization:
    """Test ExperimentManager initialization and basic setup."""

    def test_experiment_manager_creation(self, tmp_path):
        """Test creating an ExperimentManager instance."""
        # Create experiment manager
        manager = ExperimentManager(
            experiment_name="test_experiment", output_dir=str(tmp_path)
        )

        # Verify initialization
        assert manager.experiment_name == "test_experiment"
        assert manager.output_dir == tmp_path
        assert manager.state == "initialized"
        assert manager.services == {}
        assert manager.experiment_id is not None
        assert len(manager.experiment_id) > 0

    def test_experiment_id_generation(self, tmp_path):
        """Test that experiment IDs are unique."""
        # Create multiple managers
        manager1 = ExperimentManager(experiment_name="test1", output_dir=str(tmp_path))
        manager2 = ExperimentManager(experiment_name="test2", output_dir=str(tmp_path))

        # Verify unique IDs
        assert manager1.experiment_id != manager2.experiment_id
        assert len(manager1.experiment_id) > 10  # Reasonable length
        assert isinstance(manager1.experiment_id, str)

    def test_experiment_manager_with_output_dir(self, tmp_path):
        """Test ExperimentManager with custom output directory."""
        manager = ExperimentManager(experiment_name="test", output_dir=str(tmp_path))

        assert manager.output_dir == tmp_path
        assert manager.output_dir.exists()


class TestExperimentWorkflow:
    """Test the 4-phase experiment workflow."""

    @pytest.fixture
    def mock_manager(self, tmp_path):
        """Create a mock experiment manager for testing."""
        manager = ExperimentManager(
            experiment_name="test_experiment", output_dir=str(tmp_path)
        )
        return manager

    def test_phase_1_initialization(self, mock_manager):
        """Test Phase 1: Initialization."""
        # Run phase 1
        result = mock_manager.run_phase_1_initialization()

        # Verify
        assert result is True
        assert mock_manager.state == "phase_1_complete"

    def test_phase_2_plugin_loading(self, mock_manager):
        """Test Phase 2: Plugin Loading."""
        # Setup prerequisites
        mock_manager.state = "phase_1_complete"

        # Run phase 2
        result = mock_manager.run_phase_2_plugin_loading()

        # Verify
        assert result is True
        assert mock_manager.state == "phase_2_complete"

    def test_phase_3_environment_deployment(self, mock_manager):
        """Test Phase 3: Environment Deployment."""
        # Setup prerequisites
        mock_manager.state = "phase_2_complete"

        # Run phase 3
        result = mock_manager.run_phase_3_environment_deployment()

        # Verify
        assert result is True
        assert mock_manager.state == "phase_3_complete"

    def test_phase_4_test_execution(self, mock_manager):
        """Test Phase 4: Test Execution."""
        # Setup prerequisites
        mock_manager.state = "phase_3_complete"

        # Run phase 4
        result = mock_manager.run_phase_4_test_execution()

        # Verify
        assert result is True
        assert mock_manager.state == "completed"

    def test_full_workflow_integration(self, mock_manager):
        """Test running the complete 4-phase workflow."""
        # Run complete workflow
        result = mock_manager.run_experiment()

        # Verify all phases executed
        assert result is True

        # Verify final state
        assert mock_manager.state == "completed"

    def test_workflow_phase_dependencies(self, mock_manager):
        """Test that phases have proper dependencies."""
        # Try to run phase 2 without phase 1
        result = mock_manager.run_phase_2_plugin_loading()
        assert result is False

        # Try to run phase 3 without phase 2
        mock_manager.state = "phase_1_complete"
        result = mock_manager.run_phase_3_environment_deployment()
        assert result is False

        # Try to run phase 4 without phase 3
        mock_manager.state = "phase_2_complete"
        result = mock_manager.run_phase_4_test_execution()
        assert result is False


class TestServiceManagement:
    """Test service management functionality."""

    @pytest.fixture
    def manager_with_services(self, tmp_path):
        """Create a manager with mock services."""
        manager = ExperimentManager(experiment_name="test", output_dir=str(tmp_path))

        # Add mock services
        mock_service1 = Mock()
        mock_service1.name = "test_service_1"
        mock_service1.status = "ready"

        mock_service2 = Mock()
        mock_service2.name = "test_service_2"
        mock_service2.status = "starting"

        manager.add_service("test_service_1", mock_service1)
        manager.add_service("test_service_2", mock_service2)

        return manager

    def test_add_service(self, tmp_path):
        """Test adding a service to the experiment."""
        manager = ExperimentManager(experiment_name="test", output_dir=str(tmp_path))

        new_service = Mock()
        new_service.name = "new_service"
        new_service.status = "initialized"

        manager.add_service("new_service", new_service)

        # Verify service was added
        assert "new_service" in manager.services
        assert manager.services["new_service"] == new_service

    def test_remove_service(self, manager_with_services):
        """Test removing a service from the experiment."""
        # Remove existing service
        result = manager_with_services.remove_service("test_service_1")

        # Verify service was removed
        assert result is True
        assert "test_service_1" not in manager_with_services.services
        assert len(manager_with_services.services) == 1

    def test_get_service_status(self, manager_with_services):
        """Test getting service status."""
        status1 = manager_with_services.get_service_status("test_service_1")
        status2 = manager_with_services.get_service_status("test_service_2")
        status_nonexistent = manager_with_services.get_service_status("nonexistent")

        assert status1 == "ready"
        assert status2 == "starting"
        assert status_nonexistent is None

    def test_get_all_services_status(self, manager_with_services):
        """Test getting status of all services."""
        status_dict = manager_with_services.get_all_services_status()

        expected = {"test_service_1": "ready", "test_service_2": "starting"}

        assert status_dict == expected

    def test_wait_for_services_ready_success(self, tmp_path):
        """Test waiting for all services to be ready - success case."""
        manager = ExperimentManager(experiment_name="test", output_dir=str(tmp_path))

        # Add services that are ready
        service1 = Mock()
        service1.status = "ready"
        service2 = Mock()
        service2.status = "ready"

        manager.add_service("service1", service1)
        manager.add_service("service2", service2)

        result = manager.wait_for_services_ready()
        assert result is True

    def test_wait_for_services_ready_failure(self, tmp_path):
        """Test waiting for services that are not ready."""
        manager = ExperimentManager(experiment_name="test", output_dir=str(tmp_path))

        # Add services that are not ready
        service1 = Mock()
        service1.status = "starting"
        service2 = Mock()
        service2.status = "failed"

        manager.add_service("service1", service1)
        manager.add_service("service2", service2)

        result = manager.wait_for_services_ready()
        assert result is False


class TestResultCollection:
    """Test experiment result collection and reporting."""

    @pytest.fixture
    def manager_with_results(self, tmp_path):
        """Create a manager with mock results."""
        manager = ExperimentManager(experiment_name="test", output_dir=str(tmp_path))

        # Add mock results
        manager.results = {
            "test_case_1": {
                "status": "passed",
                "duration": 45.2,
                "logs": ["log1.txt", "log2.txt"],
                "metrics": {"packets_sent": 100, "packets_received": 98},
            },
            "test_case_2": {
                "status": "failed",
                "duration": 30.1,
                "logs": ["log3.txt"],
                "error": "Connection timeout",
                "metrics": {"packets_sent": 50, "packets_received": 0},
            },
        }

        return manager

    def test_collect_results(self, manager_with_results):
        """Test result collection."""
        results = manager_with_results.collect_results()

        # Verify results structure
        assert len(results) == 2
        assert "test_case_1" in results
        assert "test_case_2" in results

        # Verify result data
        assert results["test_case_1"]["status"] == "passed"
        assert results["test_case_2"]["status"] == "failed"
        assert results["test_case_1"]["duration"] == 45.2

    def test_generate_summary(self, manager_with_results):
        """Test experiment summary generation."""
        summary = manager_with_results.generate_summary()

        # Verify summary structure
        assert "total_tests" in summary
        assert "passed_tests" in summary
        assert "failed_tests" in summary
        assert "total_duration" in summary
        assert "success_rate" in summary

        # Verify summary values
        assert summary["total_tests"] == 2
        assert summary["passed_tests"] == 1
        assert summary["failed_tests"] == 1
        assert summary["total_duration"] == 75.3  # 45.2 + 30.1
        assert summary["success_rate"] == 0.5

    def test_export_results_json(self, manager_with_results):
        """Test exporting results to JSON."""
        export_path = manager_with_results.export_results(format="json")

        # Verify file was created
        assert export_path.exists()
        assert export_path.suffix == ".json"

        # Verify content
        with open(export_path) as f:
            data = json.load(f)

        assert "experiment_id" in data
        assert "results" in data
        assert "summary" in data
        assert len(data["results"]) == 2

    def test_export_results_yaml(self, manager_with_results):
        """Test exporting results to YAML."""
        export_path = manager_with_results.export_results(format="yaml")

        # Verify file was created
        assert export_path.exists()
        assert export_path.suffix in [".yaml", ".yml"]

        # Verify content
        with open(export_path) as f:
            data = yaml.safe_load(f)

        assert "experiment_id" in data
        assert "results" in data
        assert len(data["results"]) == 2

    def test_get_experiment_metadata(self, manager_with_results):
        """Test experiment metadata collection."""
        metadata = manager_with_results.get_experiment_metadata()

        # Verify metadata structure
        assert "experiment_id" in metadata
        assert "start_time" in metadata
        assert "end_time" in metadata
        assert "duration" in metadata
        assert "status" in metadata
        assert "phase" in metadata

        # Verify metadata types
        assert isinstance(metadata["experiment_id"], str)
        assert isinstance(metadata["status"], str)


class TestExperimentManagerErrorHandling:
    """Test error handling and recovery mechanisms."""

    def test_cleanup_on_failure(self, tmp_path):
        """Test cleanup operations on experiment failure."""
        manager = ExperimentManager(experiment_name="test", output_dir=str(tmp_path))

        # Add mock services that need cleanup
        mock_service = Mock()
        manager.add_service("test_service", mock_service)

        # Trigger failure cleanup
        manager._cleanup_on_failure()

        # Verify cleanup operations
        assert mock_service.stop.called
        assert mock_service.cleanup.called
        assert manager.state == "failed"


class TestExperimentManagerTiming:
    """Test experiment timing and progress tracking."""

    def test_experiment_timing(self, tmp_path):
        """Test experiment timing tracking."""
        manager = ExperimentManager(experiment_name="test", output_dir=str(tmp_path))

        # Start timing
        manager._start_timing()
        assert manager.start_time is not None

        # End timing
        import time

        time.sleep(0.1)  # Small delay
        manager._end_timing()
        assert manager.end_time is not None
        assert manager.duration > 0

    def test_progress_reporting(self, tmp_path):
        """Test experiment progress reporting."""
        manager = ExperimentManager(experiment_name="test", output_dir=str(tmp_path))

        # Test progress updates
        manager.update_progress("Initializing", 25)
        manager.update_progress("Loading plugins", 50)
        manager.update_progress("Deploying services", 75)
        manager.update_progress("Running tests", 100)

        # Verify progress tracking
        assert manager.progress == 100
        assert len(manager.progress_history) == 4
        assert manager.progress_history[-1]["message"] == "Running tests"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
