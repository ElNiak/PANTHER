"""
Event Workflow Module

This module defines the standard event workflow for PANTHER experiments.
It provides documentation and utility functions for proper event sequencing.
"""

from typing import Any
from enum import Enum, auto


class ExperimentPhase(Enum):
    """Phases of an experiment execution."""

    INITIALIZATION = auto()
    TEST_SETUP = auto()
    ENVIRONMENT_SETUP = auto()
    SERVICE_DEPLOYMENT = auto()
    TEST_EXECUTION = auto()
    STEP_EXECUTION = auto()
    SERVICE_TEARDOWN = auto()
    ENVIRONMENT_TEARDOWN = auto()
    FINALIZATION = auto()


class EventWorkflow:
    """
    Defines the standard event workflow for PANTHER experiments.

    This class documents the expected event sequence for each phase of an experiment,
    providing a reference for both core framework and plugin developers.
    """

    @staticmethod
    def get_initialization_workflow() -> list[dict[str, Any]]:
        """
        Returns the standard event workflow for experiment initialization.

        Returns:
            List of event descriptions in sequence
        """
        return [
            {
                "event": "ExperimentInitializedEvent",
                "emitter": "ExperimentManager",
                "description": "Emitted when experiment configuration is loaded",
                "parameters": {
                    "experiment_id": "Unique identifier for the experiment",
                    "config": "Dictionary containing experiment configuration details",
                },
            },
            {
                "event": "TestStartedEvent",
                "emitter": "ExperimentManager",
                "description": "Emitted for each test case initialization",
                "parameters": {
                    "test_id": "Test case identifier",
                    "data": {"phase": "initialization", "config": "Test configuration"},
                },
            },
            {
                "event": "TestCompletedEvent",
                "emitter": "ExperimentManager",
                "description": "Emitted after each test case is successfully initialized",
                "parameters": {
                    "test_id": "Test case identifier",
                    "success": "Boolean indicating initialization success",
                    "result": {"phase": "initialization"},
                },
            },
            {
                "event": "TestCaseInitializedEvent",
                "emitter": "ExperimentManager",
                "description": "Summary event emitted after all test cases are initialized",
                "parameters": {
                    "test_count": "Number of test cases initialized",
                    "test_names": "List of test case names",
                },
            },
        ]

    @staticmethod
    def get_test_execution_workflow() -> list[dict[str, Any]]:
        """
        Returns the standard event workflow for test execution.

        Returns:
            List of event descriptions in sequence
        """
        return [
            {
                "event": "TestExecutionStartedEvent",
                "emitter": "ExperimentManager",
                "description": "Emitted at the beginning of test execution",
                "parameters": {"test_id": "Experiment identifier", "test_name": "Experiment name"},
            },
            # Per test case execution
            {
                "event": "TestStartedEvent",
                "emitter": "ExperimentManager",
                "description": "Emitted before running each test case",
                "parameters": {
                    "test_id": "Test case identifier",
                    "data": {"config": {"name": "Test case name"}},
                },
            },
            # Environment setup events - see environment_setup_workflow
            # Service deployment events - see service_deployment_workflow
            # Step execution events - see step_execution_workflow
            {
                "event": "TestCompletedEvent",
                "emitter": "ExperimentManager",
                "description": "Emitted after successful test case execution",
                "parameters": {
                    "test_id": "Test case identifier",
                    "success": "Boolean indicating test success",
                    "result": "Optional result data",
                },
            },
            # Alternative - failure path
            {
                "event": "TestExecutionFailedEvent",
                "emitter": "ExperimentManager",
                "description": "Emitted if test execution fails",
                "parameters": {
                    "test_id": "Test case identifier",
                    "error_type": "Type of error encountered",
                    "error_message": "Error message",
                    "details": "Additional error details",
                },
            },
            # Experiment summary
            {
                "event": "TestExecutionCompletedEvent",
                "emitter": "ExperimentManager",
                "description": "Summary event emitted after all tests complete",
                "parameters": {
                    "test_id": "Experiment identifier",
                    "test_name": "Experiment name",
                    "success": "Boolean indicating overall success",
                    "results": {
                        "success_count": "Number of successful tests",
                        "failure_count": "Number of failed tests",
                        "total_count": "Total number of tests",
                    },
                    "duration_ms": "Total execution duration in milliseconds",
                },
            },
        ]

    @staticmethod
    def get_environment_setup_workflow() -> list[dict[str, Any]]:
        """
        Returns the standard event workflow for environment setup.

        Returns:
            List of event descriptions in sequence
        """
        return [
            {
                "event": "EnvironmentSetupStartedEvent",
                "emitter": "TestCase/IEnvironmentPlugin",
                "description": "Emitted when environment setup begins",
                "parameters": {
                    "environment_type": "Type of environment being set up",
                    "details": "Additional setup details",
                },
            },
            # Plugin-specific events might occur here
            {
                "event": "EnvironmentSetupCompletedEvent",
                "emitter": "TestCase/IEnvironmentPlugin",
                "description": "Emitted when environment setup completes",
                "parameters": {
                    "environment_type": "Type of environment",
                    "success": "Boolean indicating setup success",
                    "details": "Additional completion details",
                },
            },
            {
                "event": "EnvironmentReadyEvent",
                "emitter": "IEnvironmentPlugin",
                "description": "Emitted when environment is ready for use",
                "parameters": {
                    "env_name": "Name of the environment",
                    "env_type": "Type of the environment",
                    "details": "Additional readiness details",
                },
            },
        ]

    @staticmethod
    def get_service_deployment_workflow() -> list[dict[str, Any]]:
        """
        Returns the standard event workflow for service deployment.

        Returns:
            List of event descriptions in sequence
        """
        return [
            {
                "event": "ServiceEvent (services_setup)",
                "emitter": "TestCase",
                "description": "Emitted when service setup begins",
                "parameters": {"name": "service.setup", "data": "Service setup details"},
            },
            {
                "event": "ServiceEvent (services_deployed)",
                "emitter": "TestCase",
                "description": "Emitted when services are deployed",
                "parameters": {"name": "service.deployed", "data": "Service deployment details"},
            },
            {
                "event": "ServiceStartedEvent",
                "emitter": "IServiceManager",
                "description": "Emitted when a specific service starts",
                "parameters": {
                    "service_name": "Name of the service",
                    "service_type": "Type of the service",
                    "details": "Additional service details",
                },
            },
        ]

    @staticmethod
    def get_step_execution_workflow() -> list[dict[str, Any]]:
        """
        Returns the standard event workflow for test step execution.

        Returns:
            List of event descriptions in sequence
        """
        return [
            {
                "event": "StepProgressEvent",
                "emitter": "TestCase",
                "description": "Emitted during step execution to report progress",
                "parameters": {
                    "step_id": "Identifier for the step",
                    "progress": "Progress value (0.0-1.0)",
                    "details": "Additional progress details",
                },
            },
            {
                "event": "MetricCollectedEvent",
                "emitter": "TestCase/MetricsCollector",
                "description": "Emitted when metrics are collected during step execution",
                "parameters": {
                    "metric_type": "Type of metric",
                    "metric_name": "Name of the metric",
                    "value": "Metric value",
                    "step_id": "Step identifier",
                    "test_id": "Test identifier",
                },
            },
            {
                "event": "TimingMetricEvent",
                "emitter": "TestCase",
                "description": "Emitted to record timing information for a step",
                "parameters": {
                    "metric_name": "Name of the timing metric",
                    "duration_ms": "Duration in milliseconds",
                    "step_id": "Step identifier",
                    "test_id": "Test identifier",
                },
            },
            {
                "event": "StepCompletedEvent",
                "emitter": "TestCase",
                "description": "Emitted when a step completes",
                "parameters": {
                    "step_id": "Identifier for the step",
                    "success": "Boolean indicating step success",
                    "result": "Step execution results",
                },
            },
        ]

    @staticmethod
    def get_teardown_workflow() -> list[dict[str, Any]]:
        """
        Returns the standard event workflow for environment and service teardown.

        Returns:
            List of event descriptions in sequence
        """
        return [
            {
                "event": "ServiceEvent (service_teardown)",
                "emitter": "TestCase",
                "description": "Emitted when services are being torn down",
                "parameters": {"name": "service.teardown", "data": "Service teardown details"},
            },
            {
                "event": "ServiceStoppedEvent",
                "emitter": "IServiceManager",
                "description": "Emitted when a specific service stops",
                "parameters": {
                    "service_name": "Name of the service",
                    "service_type": "Type of the service",
                    "success": "Boolean indicating clean shutdown",
                    "details": "Additional service details",
                },
            },
            {
                "event": "EnvironmentTeardownEvent",
                "emitter": "TestCase/IEnvironmentPlugin",
                "description": "Emitted during environment teardown",
                "parameters": {
                    "environment_type": "Type of environment",
                    "success": "Boolean indicating teardown success",
                    "details": "Additional teardown details",
                },
            },
        ]

    @staticmethod
    def get_early_termination_workflow() -> list[dict[str, Any]]:
        """
        Returns the standard event workflow for early experiment termination.

        Returns:
            List of event descriptions in sequence
        """
        return [
            {
                "event": "ExperimentFinishedEarlyEvent",
                "emitter": "Various (plugins, TestCase, etc.)",
                "description": "Emitted to signal that an experiment should finish early",
                "parameters": {
                    "experiment_id": "Experiment identifier",
                    "reason": "Reason for early termination",
                    "details": "Additional details about the termination",
                },
            }
        ]
