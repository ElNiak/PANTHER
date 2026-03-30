"""Abstract interface for tester service managers."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from panther.config.core.models import ProtocolConfig
from panther.config.core.models.service import ServiceConfig
from panther.core.observer.management.event_manager import EventManager
from panther.plugins.services.services_interface import IServiceManager


class ITesterManager(IServiceManager, ABC):
    """Interface for tester service managers.

    Extends ServiceBase (which already includes TesterManagerEventMixin) with standardized
    test run reporting and monitoring capabilities.
    """

    def __init__(
        self,
        service_config_to_test: ServiceConfig,
        service_type: str,
        protocol: ProtocolConfig,
        implementation_name: str,
        event_manager: Optional[EventManager] = None,
        test_case: Optional[
            Any
        ] = None,  # Reference to parent test case for execution environment access
    ):
        """Initialize the tester manager with service and protocol configuration."""
        super().__init__(
            service_config_to_test,
            service_type,
            protocol,
            implementation_name,
            event_manager,
            test_case=test_case,
        )
        self._status = {
            "state": "created",
            "details": {},
        }
        self.test_results = {}
        self.collected_outputs = {}

    def is_tester(self) -> bool:
        """Check if this service manager is a tester.

        Returns:
            bool: True if this is a tester service manager, False otherwise.
        """
        return True

    def run_tests(self):
        """Run tests with proper event notifications.

        Returns:
            Dict: Test results
        """
        try:
            self.logger.info(
                "Running tests for service: %s (%s)",
                self.service_name,
                self.service_type,
            )
            # Notify test run started
            test_name = getattr(self, "test_to_compile", "unknown")
            self.emit_test_starting(
                test_id=test_name,
                test_type=self.service_type,
                details={
                    "service_name": self.service_name,
                    "service_type": self.service_type,
                },
            )

            # Run the tests
            results = self._do_run_tests()

            # Notify test run completed
            self.emit_test_completed(
                test_id=test_name, success=results.get("success", False), result=results
            )

            return results
        except Exception as e:  # pylint: disable=broad-except
            # Notify test run failed
            self.emit_test_completed(
                test_id=getattr(self, "test_to_compile", "unknown"),
                success=False,
                result={"error": str(e), "error_type": type(e).__name__},
            )
            raise

    @abstractmethod
    def _do_run_tests(self):
        """Actual implementation of test running, to be overridden by subclasses.

        Returns:
            Dict: Test results containing at minimum a 'success' key with boolean value
        """
        pass

    @abstractmethod
    def set_collected_outputs(self, outputs: Dict[str, Dict[str, str]]) -> None:
        """Set the outputs collected from execution environments for analysis.

        Args:
            outputs: Dictionary organized by output type, then by environment
                    Example: {
                        "trace": {"strace": "/path/to/trace.out"},
                        "cpu_profile": {"gperf_cpu": "/path/to/profile.data"}
                    }
        """
        pass

    @abstractmethod
    def analyze_outputs(self) -> Dict[str, Any]:
        """Analyze the collected outputs from execution environments.

        This method should examine the outputs provided via set_collected_outputs()
        and perform tester-specific analysis to determine test outcomes.

        Returns:
            Dict[str, Any]: Analysis results including:
                - passed: bool - Whether analysis passed
                - failed_checks: List[str] - List of failed checks
                - warnings: List[str] - List of warnings
                - detailed_results: dict - Detailed analysis results
                - analysis_summary: str - Human-readable summary
        """
        pass

    @abstractmethod
    def get_test_results(self) -> Dict[str, Any]:
        """Get the final test results after analysis.

        This method should return the results of both the test execution
        and the analysis of collected outputs.

        Returns:
            Dict[str, Any]: Complete test results including:
                - passed: bool - Overall test success
                - execution_results: dict - Results from test execution
                - analysis_results: dict - Results from output analysis
                - summary: str - Overall summary
        """
        pass
