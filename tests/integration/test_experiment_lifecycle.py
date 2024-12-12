import datetime
import logging
from pathlib import Path
from panther.core.experiment_manager import ExperimentManager
from panther.plugins.plugin_loader import PluginLoader
from panther.plugins.plugin_manager import PluginManager


def test_experiment_manager_initialization_with_defaults(global_config):
    manager = ExperimentManager(global_config=global_config)
    assert manager.global_config == global_config
    assert manager.experiment_name.startswith(datetime.now().strftime("%Y-%m-%d"))
    assert manager.experiment_dir.exists()
    assert manager.logger.name == "ExperimentManager"
    assert manager.plugin_dir == Path("panther/plugins/")
    assert isinstance(manager.plugin_loader, PluginLoader)
    assert isinstance(manager.plugin_manager, PluginManager)
    assert manager.test_cases == []


def test_experiment_manager_initialization_with_custom_values(global_config):
    custom_logger = logging.getLogger("CustomLogger")
    manager = ExperimentManager(
        global_config=global_config,
        experiment_name="custom_experiment",
        plugin_dir="custom/plugins/",
        logger=custom_logger,
    )
    assert manager.global_config == global_config
    assert manager.experiment_name.startswith(datetime.now().strftime("%Y-%m-%d"))
    assert "custom_experiment" in manager.experiment_name
    assert manager.experiment_dir.exists()
    assert manager.logger == custom_logger
    assert manager.plugin_dir == Path("custom/plugins/")
    assert isinstance(manager.plugin_loader, PluginLoader)
    assert isinstance(manager.plugin_manager, PluginManager)
    assert manager.test_cases == []


def test_experiment_manager_logging_configuration(global_config):
    manager = ExperimentManager(global_config=global_config)
    log_file = manager.logs_dir / "experiment.log"
    assert log_file.exists()
    with open(log_file) as f:
        log_content = f.read()
    assert "ExperimentManager" in log_content
