"""Test execution functionality for test cases."""

from typing import Any, Dict, List

from panther.core.test_cases.analysis.output_analyzer import OutputAnalyzer
from panther.core.test_cases.execution.test_executor import TestExecutor


class TestExecutionMixin:
    """Mixin providing test execution capabilities for test cases."""

    def __init__(self, *args, **kwargs):
        """Initialize the mixin."""
        super().__init__(*args, **kwargs)
        # Initialize attributes if not already set
        if not hasattr(self, "_test_executor"):
            self._test_executor = None
        if not hasattr(self, "_output_analyzer"):
            self._output_analyzer = None

    @property
    def test_executor(self) -> TestExecutor:
        """Get or create the test executor instance."""
        if self._test_executor is None:
            self._test_executor = TestExecutor(self)
        return self._test_executor

    @property
    def output_analyzer(self) -> OutputAnalyzer:
        """Get or create the output analyzer instance."""
        if self._output_analyzer is None:
            self._output_analyzer = OutputAnalyzer(self)
        return self._output_analyzer

    def execute_steps(self) -> None:
        """Execute the defined steps of a test case."""
        self.logger.info("Executing test steps")

        # Delegate to test executor
        self.test_executor.execute_steps()

    def validate_assertions(self) -> None:
        """Validate assertions defined in test configuration."""
        self.logger.info("Validating assertions")

        # Delegate to test executor
        self.test_executor.validate_assertions()

    def check_service_responsiveness(
        self, service_name: str, endpoint: str, expected_status: int = 200
    ) -> bool:
        """
        Check if a service's endpoint is responsive and returns the expected status code.

        Args:
            service_name: Name of the service
            endpoint: Endpoint URL to check
            expected_status: Expected HTTP status code

        Returns:
            bool: True if service is responsive, False otherwise
        """
        import requests

        try:
            response = requests.get(endpoint, timeout=5)
            is_responsive = response.status_code == expected_status

            if is_responsive:
                self.logger.info(
                    f"Service '{service_name}' is responsive at {endpoint}"
                )
            else:
                self.logger.warning(
                    f"Service '{service_name}' returned unexpected status {response.status_code} at {endpoint}"
                )

            return is_responsive

        except requests.RequestException as e:
            self.logger.error(
                f"Service '{service_name}' is not responsive at {endpoint}: {e}"
            )
            return False

    def execute_custom_step(self, step_name: str, step_config: Dict[str, Any]) -> None:
        """
        Execute a custom step type.

        This method can be overridden in subclasses to support custom step types.

        Args:
            step_name: Name of the step
            step_config: Step configuration dictionary
        """
        self.logger.warning(f"No handler for custom step type: {step_name}")
        # Subclasses can override this to handle custom steps

    def _collect_outputs(self) -> Dict[str, Any]:
        """
        Collect outputs from all execution environments for analysis.

        Delegates to the OutputAnalyzer to handle collection and organization.

        Returns:
            Dict[str, Any]: Collected outputs organized by type
        """
        return self.output_analyzer.collect_outputs()

    def _run_tester_analysis(self) -> bool:
        """
        Run analysis on collected outputs using tester service managers.

        Delegates to the OutputAnalyzer to handle the analysis workflow.

        Returns:
            bool: True if all tester analyses passed, False otherwise
        """
        # First collect outputs
        organized_outputs = self._collect_outputs()

        # Run tester analysis
        analysis_results = self.output_analyzer.run_tester_analysis(organized_outputs)

        # Run service health analysis for all services (IUT + tester)
        try:
            self.service_health = self.output_analyzer.run_service_health_analysis()
        except Exception as e:
            self.logger.warning("Service health analysis skipped: %s", e)
            self.service_health = []

        # Store analysis results for potential later use
        self.analysis_results = analysis_results

        # Check if all analyses passed
        if not analysis_results:
            # FIXED: No testers means no test validation occurred - this should be treated as failure
            self.logger.warning(
                "No tester analysis results available - cannot confirm test success"
            )
            return False

        # Determine overall pass status - require positive confirmation of success
        all_passed = True
        for tester_name, result in analysis_results.items():
            # Check that the tester completed AND actually passed
            if result.get("status") != "completed":
                self.logger.error(
                    f"Tester {tester_name} did not complete successfully: status={result.get('status')}"
                )
                all_passed = False
                break

            # Check that results exist and explicitly indicate success
            results = result.get("results", {})
            if not results:
                self.logger.error(f"Tester {tester_name} produced no results")
                all_passed = False
                break

            if passed := results.get("passed", False):
                self.logger.info(
                    f"Tester {tester_name} passed: {results.get('analysis_summary', 'No summary')}"
                )

            else:
                self.logger.error(
                    f"Tester {tester_name} explicitly failed: {results.get('analysis_summary', 'No summary')}"
                )
                all_passed = False
                break
        return all_passed
