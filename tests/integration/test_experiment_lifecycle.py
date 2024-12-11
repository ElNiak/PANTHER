import pytest
from core.experiment_manager import ExperimentManager

def test_experiment_lifecycle():
    manager = ExperimentManager()
    experiment_id = manager.create_experiment("test_experiment")
    manager.start_experiment(experiment_id)
    manager.end_experiment(experiment_id)
    assert manager.get_status(experiment_id) == "completed"
