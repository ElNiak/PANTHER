
import logging
import os
from typing import Any, Dict
import yaml
from panther.core.results.result_handler import ResultHandler


class StorageHandler(ResultHandler):
    """
    Concrete implementation of ResultHandler for storing results in a database.
    Attributes:
        db (Database): The database to store the results in.
    Methods:
        __init__(db: Database) -> None:
            Initializes the StorageHandler with the given database.
        handle(request) -> None:
            Stores the request in the database.
    """
    
    def handle(self, request) -> None:
        self.save_experiment_result(request)
        for test_name, result_data in request.items():
            if test_name != "experiment_result":
                self.save_test_result(test_name, result_data)
                self.save_implementation_logs(test_name, result_data.get("implementation_logs", ""))
        
    def save_experiment_result(self, result_data: Dict[str, Any]):
        """Saves the overall experiment result data to a YAML file."""
        results_file = os.path.join(self.output_dir, "experiment_result.yaml")
        with open(results_file, "w") as f:
            yaml.dump(result_data, f)
        logging.info(f"Experiment results saved to {results_file}.")

    def save_test_result(self, test_name: str, result_data: Dict[str, Any]):
        """Saves the result data for a specific test case to a YAML file in a subfolder."""
        test_output_dir = os.path.join(self.output_dir, test_name)
        os.makedirs(test_output_dir, exist_ok=True)
        results_file = os.path.join(test_output_dir, f"{test_name}_result.yaml")
        with open(results_file, "w") as f:
            yaml.dump(result_data, f)
        logging.info(f"Test results saved to {results_file}.")

    def save_implementation_logs(self, test_name: str, log_data: str):
        """Saves the implementation logs for a specific test case."""
        test_output_dir = os.path.join(self.output_dir, test_name)
        os.makedirs(test_output_dir, exist_ok=True)
        log_file = os.path.join(test_output_dir, f"{test_name}_implementation.log")
        with open(log_file, "w") as f:
            f.write(log_data)
        logging.info(f"Implementation logs saved to {log_file}.")
