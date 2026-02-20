"""Test execution logic for test cases."""

import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from panther.core.test_cases.test_case_impl import TestCase

from panther.core.events.assertion.emitter import AssertionEventEmitter
from panther.core.events.step.emitter import StepEventEmitter


class TestExecutor:
    """Handles test execution including steps and assertions."""

    def __init__(self, test_case: "TestCase") -> None:
        """Initialize test executor with reference to parent test case."""
        self.test_case = test_case
        self.logger = test_case.logger

    def execute_steps(self) -> None:
        """Execute the defined steps of a test."""
        steps = self.test_case.test_config.steps
        if not steps:
            self.logger.warning("No steps defined for test")
            return

        self.logger.info("Executing test steps")

        try:
            # Get step emitter if available
            step_emitter = None
            if self.test_case.emitter_registry:
                step_emitter = self.test_case.emitter_registry.get_emitter("step")

            # Emit steps execution started
            if step_emitter:
                step_config = {"wait": steps.wait}
                # Only add record_pcap if it exists
                if hasattr(steps, "record_pcap"):
                    step_config["record_pcap"] = steps.record_pcap
                step_emitter.emit_step_execution_started(
                    step_id="execute_steps",
                    step_name="Execute test steps",
                    test_case_id=self.test_case.test_name,
                    step_config=step_config,
                )
            steps_time = time.time()

            # Execute wait step
            if steps.wait > 0:
                self._execute_single_step("wait", steps.wait, step_emitter)

            # Execute record_pcap step if enabled (only if attribute exists)
            if hasattr(steps, "record_pcap") and steps.record_pcap:
                self._execute_single_step(
                    "record_pcap", {"enabled": True}, step_emitter
                )

            # Emit steps execution completed
            result = {
                "completed": True,
                "duration_s": (time.time() - steps_time),
            }
            if step_emitter:
                step_emitter.emit_step_execution_completed(
                    step_id="execute_steps",
                    step_name="Execute test steps",
                    test_case_id=self.test_case.test_name,
                    duration=result.get("duration_s"),
                    result=result,
                )
            self.logger.info("All test steps executed successfully")

        except Exception as e:
            self.logger.error(f"Test step execution failed: {e}")
            # Emit steps execution failed
            if step_emitter:
                step_emitter.emit_step_execution_completed(
                    step_id="execute_steps",
                    step_name="Execute test steps",
                    test_case_id=self.test_case.test_name,
                    result={"completed_steps": ["wait", "record_pcap"]},
                )
            raise

    def _execute_single_step(
        self,
        step_name: str,
        step_details: Dict[str, Any],
        step_emitter: Optional[StepEventEmitter],
    ) -> None:
        """Execute a single test step."""
        self.logger.info(f"Executing step: {step_name}")

        try:
            # Emit step started event
            self.emit_start_step(step_details, step_emitter)
            start_time = time.time()

            # Handle different step types
            if isinstance(step_details, (int, float)):
                # Wait step
                wait_time = step_details
                self.logger.debug(f"Waiting for {wait_time} seconds")
                step_config = {"type": "wait", "duration": wait_time}
                self._check_early_exit(step_config, step_emitter)
            elif isinstance(step_details, dict):
                # Complex step configuration
                self.handle_step_execution(step_details, step_emitter)
            else:
                self.logger.warning(
                    f"Unsupported step configuration type: {type(step)}"
                )
                if step_emitter:
                    step_emitter.emit_step_unsupported(
                        step_id="unsupported_step",
                        step_name=step_name,
                        test_case_id=self.test_case.test_name,
                        reason=f"Unsupported step type: {step_name}",
                    )

            duration = time.time() - start_time

            # Emit step completed event
            if step_emitter:
                step_emitter.emit_step_execution_completed(
                    step_id=step_name,
                    step_name=step_name,
                    test_case_id=self.test_case.test_name,
                    duration=duration,
                    result=None,  # Placeholder for result
                )

            self.logger.info(f"Step {step_name} completed in {duration:.2f}s")

        except Exception as e:
            self.logger.error(f"Step {step_name} failed: {e}")
            # Emit step failed event
            if step_emitter:
                step_emitter.emit_step_execution_completed(
                    step_id="execute_steps",
                    step_name="Execute test steps",
                    test_case_id=self.test_case.test_name,
                    result={"completed_steps": ["wait", "record_pcap"]},
                )
            raise

    def handle_step_execution(self, step_details, step_emitter):
        step_type = step_details.get("type", "unknown")
        if step_type == "wait":
            wait_time = step_details.get("duration", 0)
            self.logger.info(f"Waiting for {wait_time} seconds")
            wait_step_config = {"type": "wait", "duration": wait_time}
            self._check_early_exit(wait_step_config, step_emitter)
        elif step_type == "http_request":
            self._execute_http_request_step(step_details)
        elif step_type == "assertion":
            self._execute_assertion_step(step_details)

        else:
            self.logger.warning(f"Unknown step type: {step_type}")

    def emit_start_step(self, step_details, step_emitter):
        if step_emitter:
            step_emitter.emit_step_execution_started(
                step_id="execute_steps",
                step_name="Execute test steps",
                test_case_id=self.test_case.test_name,
                step_config=step_details,
            )

    def _check_early_exit(self, step_config, step_emitter) -> None:
        """Check if an early exit condition is met."""
        step_name = step_config.get("type", "unknown")
        step_details = step_config.get("duration", 0)
        self.logger.info("Executing wait step for %s seconds", step_details)
        # Emit step progress event before starting using the typed event emitter
        step_emitter.emit_step_progress(
            step_id=step_name,
            step_name=step_name,
            test_case_id=self.test_case.test_name,
            progress_percentage=0.0,
            progress_message=f"Starting wait for {step_details} seconds",
        )

        # Split the wait into smaller intervals to allow checking for early termination
        interval = min(1.0, step_details / 10.0)
        wait_time_remaining = step_details
        while wait_time_remaining > 0:
            # Calculate wait time for this iteration
            iteration_wait = min(interval, wait_time_remaining)
            time.sleep(iteration_wait)
            wait_time_remaining -= iteration_wait

            # Calculate progress percentage
            progress_percentage = (
                (step_details - wait_time_remaining) / step_details
            ) * 100

            # Emit progress event using the typed event emitter
            step_emitter.emit_step_progress(
                step_id=step_name,
                step_name=step_name,
                test_case_id=self.test_case.test_name,
                progress_percentage=progress_percentage,
                progress_message=f"Waiting: {wait_time_remaining:.1f} seconds remaining",
            )

            # Check for early termination
            for env_manager in self.test_case.environment_plugin_manager:
                if (
                    hasattr(env_manager, "should_terminate_early")
                    and callable(env_manager.should_terminate_early)
                    and env_manager.should_terminate_early()
                ):
                    self.logger.info(
                        "Early termination triggered by %s. "
                        "Stopping wait; teardown deferred until after output collection.",
                        env_manager.__class__.__name__,
                    )
                    return

    def _execute_http_request_step(self, config: Dict[str, Any]) -> None:
        """Execute an HTTP request step."""
        import requests

        url = config.get("url")
        method = config.get("method", "GET").upper()
        headers = config.get("headers", {})
        body = config.get("body")
        expected_status = config.get("expected_status", 200)
        timeout = config.get("timeout", 30)

        self.logger.info(f"Executing HTTP {method} request to {url}")

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=body if isinstance(body, dict) else None,
                data=body if isinstance(body, str) else None,
                timeout=timeout,
            )

            self.logger.info(f"Response status: {response.status_code}")

            if expected_status and response.status_code != expected_status:
                raise AssertionError(
                    f"Expected status {expected_status}, got {response.status_code}"
                )

        except requests.RequestException as e:
            self.logger.error(f"HTTP request failed: {e}")
            raise

    def _execute_assertion_step(self, config: Dict[str, Any]) -> None:
        """Execute an assertion step."""
        assertion_type = config.get("assertion_type")
        expected = config.get("expected")
        actual = config.get("actual")

        self.logger.info(f"Executing assertion: {assertion_type}")

        if assertion_type == "equals":
            assert actual == expected, f"Expected {expected}, got {actual}"
        elif assertion_type == "contains":
            assert expected in actual, f"{expected} not found in {actual}"
        elif assertion_type == "greater_than":
            assert actual > expected, f"{actual} not greater than {expected}"
        else:
            self.logger.warning(f"Unknown assertion type: {assertion_type}")

    def validate_assertions(self) -> None:
        """Validate assertions defined in test configuration."""
        # Check if assertions exist in test config
        assertions = getattr(self.test_case.test_config, "assertions", None)
        if not assertions:
            self.logger.info("No assertions defined for test")
            return

        self.logger.info(f"Validating {len(assertions)} assertions")

        try:
            # Get assertion emitter if available
            assertion_emitter: AssertionEventEmitter = None
            if self.test_case.emitter_registry:
                assertion_emitter = self.test_case.emitter_registry.get_emitter(
                    "assertion"
                )

            # Emit assertion validation started
            if assertion_emitter:
                assertion_emitter.emit_assertion_validation_started(
                    test_name=self.test_case.test_name, assertion_count=len(assertions)
                )

            # Validate each assertion
            passed = 0
            failed = 0

            for assertion in assertions:
                try:
                    self._validate_single_assertion(assertion)
                    passed += 1
                except AssertionError as e:
                    failed += 1
                    self.logger.error(f"Assertion failed: {e}")

            # Emit assertion validation completed
            if assertion_emitter:
                assertion_emitter.emit_assertion_validation_completed(
                    test_name=self.test_case.test_name, passed=passed, failed=failed
                )

            if failed > 0:
                raise AssertionError(
                    f"{failed} assertions failed out of {len(assertions)}"
                )

            self.logger.info(f"All {passed} assertions passed")

        except Exception as e:
            self.logger.error(f"Assertion validation failed: {e}")
            # Emit assertion validation failed
            if assertion_emitter:
                assertion_emitter.emit_assertion_validation_failed(
                    test_name=self.test_case.test_name, error=str(e)
                )
            raise

    def _validate_single_assertion(self, assertion: Dict[str, Any]) -> None:
        """Validate a single assertion."""
        # This is a placeholder - actual implementation would depend on
        # the assertion format and what data is available to validate against
        assertion_type = assertion.get("type")
        expected = assertion.get("expected")
        actual = assertion.get("actual")

        if assertion_type == "service_running":
            # Check if service is running
            service_name = assertion.get("service")
            # Would check actual service state
            raise NotImplementedError(
                "Service running assertion validation not implemented"
            )
        elif assertion_type == "output_contains":
            # Check if output contains expected string
            output_key = assertion.get("output")
            # Would check collected outputs
            raise NotImplementedError("Output assertion validation not implemented")
        else:
            self.logger.warning(f"Unknown assertion type: {assertion_type}")
