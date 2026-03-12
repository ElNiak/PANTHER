"""Result serialization utilities for PANTHER experiments.

Standalone functions for persisting experiment and test results as YAML files
and implementation logs. Extracted from the legacy results module's StorageHandler.

Usage::

    from panther.core.reporting.result_serialization import (
        save_experiment_result,
        save_test_result,
        save_implementation_logs,
    )

    save_experiment_result(output_dir, result_data)
    save_test_result(output_dir, "test_quic_handshake", test_data)
    save_implementation_logs(output_dir, "test_quic_handshake", log_text)
"""

import logging
import os
from typing import Any, Dict

import yaml

logger = logging.getLogger(__name__)


def save_experiment_result(output_dir: str, result_data: Dict[str, Any]) -> str:
    """Save overall experiment result data to a YAML file.

    Args:
        output_dir: Directory to write the result file into.
        result_data: Experiment result dictionary.

    Returns:
        Path to the written YAML file.
    """
    os.makedirs(output_dir, exist_ok=True)
    results_file = os.path.join(output_dir, "experiment_result.yaml")
    with open(results_file, "w") as f:
        yaml.dump(result_data, f)
    logger.info("Experiment results saved to %s.", results_file)
    return results_file


def save_test_result(
    output_dir: str, test_name: str, result_data: Dict[str, Any]
) -> str:
    """Save result data for a specific test case to a YAML file.

    Args:
        output_dir: Base output directory for the experiment.
        test_name: Name of the test case.
        result_data: Test result dictionary.

    Returns:
        Path to the written YAML file.
    """
    test_output_dir = os.path.join(output_dir, test_name)
    os.makedirs(test_output_dir, exist_ok=True)
    results_file = os.path.join(test_output_dir, f"{test_name}_result.yaml")
    with open(results_file, "w") as f:
        yaml.dump(result_data, f)
    logger.info("Test results saved to %s.", results_file)
    return results_file


def save_implementation_logs(output_dir: str, test_name: str, log_data: str) -> str:
    """Save implementation logs for a specific test case.

    Args:
        output_dir: Base output directory for the experiment.
        test_name: Name of the test case.
        log_data: Raw log text to persist.

    Returns:
        Path to the written log file.
    """
    test_output_dir = os.path.join(output_dir, test_name)
    os.makedirs(test_output_dir, exist_ok=True)
    log_file = os.path.join(test_output_dir, f"{test_name}_implementation.log")
    with open(log_file, "w") as f:
        f.write(log_data)
    logger.info("Implementation logs saved to %s.", log_file)
    return log_file
