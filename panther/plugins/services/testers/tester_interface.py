from abc import abstractmethod
from typing import Any

from panther.config.config_experiment_schema import ServiceConfig
from panther.plugins.protocols.config_schema import ProtocolConfig
from panther.core.observer.management.event_manager import EventManager
from panther.plugins.services.services_interface import IServiceManager
from panther.plugins.services.testers.tester_event_methods import TesterManagerEventMixin


class ITesterManager(IServiceManager, TesterManagerEventMixin):
    """
    Interface for tester service managers.

    Extends ServiceBase (which already includes TesterManagerEventMixin) with standardized
    test run reporting and monitoring capabilities.
    """

    def __init__(
        self,
        service_config_to_test: ServiceConfig,
        service_type: str,
        protocol: ProtocolConfig,
        implementation_name: str,
        event_manager: EventManager | None = None,
    ):
        super().__init__(
            service_config_to_test, service_type, protocol, implementation_name, event_manager
        )
        self._status = {
            "state": "created",
            "details": {},
        }
        self.test_results = {}
        self.collected_outputs = {}

    def run_tests(self):
        """
        Run tests with proper event notifications.

        Returns:
            Dict: Test results
        """
        try:
            # Notify test run started
            test_name = getattr(self, "test_to_compile", "unknown")
            self.notify_test_started(
                test_name=test_name,
                details={
                    "service_name": self.service_name,
                    "service_type": self.service_type,
                },
            )

            # Run the tests
            results = self._do_run_tests()

            # Notify test run completed
            self.emit_test_completed(
                test_name=test_name, success=results.get("success", False), results=results
            )

            return results
        except Exception as e:  # pylint: disable=broad-except
            # Notify test run failed
            self.emit_test_completed(
                test_name=getattr(self, "test_to_compile", "unknown"),
                success=False,
                results={"error": str(e), "error_type": type(e).__name__},
            )
            raise

    @abstractmethod
    def _do_run_tests(self):
        """
        Actual implementation of test running, to be overridden by subclasses.

        Returns:
            Dict: Test results containing at minimum a 'success' key with boolean value
        """
        pass

    def set_collected_outputs(self, outputs: dict[str, dict[str, str]]) -> None:
        """
        Set the outputs collected from execution environments for analysis.

        Args:
            outputs: Dictionary organized by output type, then by environment
                    Example: {
                        "trace": {"strace": "/path/to/trace.out"},
                        "cpu_profile": {"gperf_cpu": "/path/to/profile.data"}
                    }
        """
        self.collected_outputs = outputs
        self.logger.info(
            f"Received {len(outputs)} output types for analysis: {list(outputs.keys())}"
        )

    @abstractmethod
    def analyze_outputs(self) -> dict[str, Any]:
        """
        Analyze the collected outputs from execution environments.

        This method should examine the outputs provided via set_collected_outputs()
        and perform tester-specific analysis to determine test outcomes.

        Returns:
            dict[str, Any]: Analysis results including:
                - passed: bool - Whether analysis passed
                - failed_checks: list[str] - List of failed checks
                - warnings: list[str] - List of warnings
                - detailed_results: dict - Detailed analysis results
                - analysis_summary: str - Human-readable summary
        """
        pass

    @abstractmethod
    def get_test_results(self) -> dict[str, Any]:
        """
        Get the final test results after analysis.

        This method should return the results of both the test execution
        and the analysis of collected outputs.

        Returns:
            dict[str, Any]: Complete test results including:
                - passed: bool - Overall test success
                - execution_results: dict - Results from test execution
                - analysis_results: dict - Results from output analysis
                - summary: str - Overall summary
        """
        pass
