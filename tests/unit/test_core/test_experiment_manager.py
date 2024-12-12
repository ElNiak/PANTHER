# import unittest
# from unittest.mock import MagicMock, patch
# import pytest
# from panther.core.experiment_manager import ExperimentManager
# from panther.config.config_experiment_schema import ExperimentConfig
# from panther.config.config_global_schema import GlobalConfig
# from panther.core.test_cases.test_case import TestCase


# @pytest.fixture
# def global_config():
#     config = MagicMock(spec=GlobalConfig)
#     config.paths.output_dir = "/tmp"
#     config.logging.level = "INFO"
#     config.logging.format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
#     return config


# @pytest.fixture
# def experiment_config():
#     config = MagicMock(spec=ExperimentConfig)
#     config.tests = []
#     return config


# @pytest.fixture
# def experiment_manager(global_config):
#     return ExperimentManager(
#         global_config=global_config, experiment_name="test_experiment"
#     )


# def test_experiment_manager_initialization(global_config):
#     manager = ExperimentManager(
#         global_config=global_config, experiment_name="test_experiment"
#     )
#     assert manager.global_config == global_config
#     assert manager.experiment_name.startswith("test_experiment_")
#     assert manager.experiment_dir.exists()
#     assert manager.logger.name == "ExperimentManager"


# def test_initialize_experiments(experiment_manager, experiment_config):
#     with patch.object(
#         experiment_manager, "_save_configuration"
#     ) as mock_save_config, patch.object(
#         experiment_manager.plugin_loader, "load_plugins"
#     ) as mock_load_plugins, patch.object(
#         experiment_manager, "_initialize_test_cases"
#     ) as mock_init_test_cases:
#         experiment_manager.initialize_experiments(experiment_config)
#         mock_save_config.assert_called_once()
#         mock_load_plugins.assert_called_once()
#         mock_init_test_cases.assert_called_once()


# def test_run_tests(experiment_manager):
#     test_case_mock = MagicMock(spec=TestCase)
#     experiment_manager.test_cases = [test_case_mock]
#     experiment_manager.run_tests()
#     test_case_mock.run.assert_called_once()


# def test_save_configuration(experiment_manager, experiment_config):
#     experiment_manager.experiment_config = experiment_config
#     with patch("builtins.open", unittest.mock.mock_open()) as mock_file:
#         experiment_manager._save_configuration()
#         mock_file.assert_called_once_with(
#             experiment_manager.experiment_dir / "experiment_config.yaml", "w"
#         )


# def test_initialize_test_cases(experiment_manager, experiment_config):
#     test_config_mock = MagicMock(spec=TestCase)
#     experiment_config.tests = [test_config_mock]
#     experiment_manager.experiment_config = experiment_config
#     with patch("panther.core.test_cases.test_case.TestCase") as mock_test_case:
#         experiment_manager._initialize_test_cases()
#         mock_test_case.assert_called_once_with(
#             test_config=test_config_mock,
#             global_config=experiment_manager.global_config,
#             plugin_manager=experiment_manager.plugin_manager,
#             experiment_dir=experiment_manager.experiment_dir,
#         )
#         assert len(experiment_manager.test_cases) == 1
