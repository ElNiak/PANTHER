# from pathlib import Path

# from panther.config.core.models.experiment import TestConfig
# from panther.config.core.models.global_config import GlobalConfig
# from panther.plugins.plugin_manager import PluginManager

# import unittest
# from unittest.mock import MagicMock, patch
# from panther.core.test_cases.test_case import TestCase


# class TestTestCase(unittest.TestCase):

#     def setUp(self):
#         self.test_config = MagicMock(spec=TestConfig)
#         self.test_config.name = "Test Case"
#         self.test_config.description = "A test case description"
#         self.test_config.network_environment = MagicMock()
#         self.test_config.execution_environment = []
#         self.test_config.services = {}
#         self.test_config.steps = {}
#         self.test_config.assertions = []

#         self.global_config = MagicMock(spec=GlobalConfig)
#         self.plugin_manager = MagicMock(spec=PluginManager)
#         self.experiment_dir = Path("/tmp/experiment")

#         self.test_case = TestCase(
#             self.test_config,
#             self.global_config,
#             self.plugin_manager,
#             self.experiment_dir,
#         )

#     def test_init(self):
#         self.assertEqual(self.test_case.test_name, "Test_Case")
#         self.assertEqual(
#             self.test_case.test_experiment_dir, self.experiment_dir / "Test_Case"
#         )
#         self.assertIsInstance(self.test_case.result_collectors, MagicMock)
#         self.assertEqual(self.test_case.service_managers, [])
#         self.assertEqual(self.test_case.environment_plugin_manager, [])
#         self.assertIsInstance(self.test_case.event_manager, MagicMock)

#     def test_str(self):
#         expected_str = (
#             "TestCase(name=Test Case, "
#             "description=A test case description, "
#             "services={}, "
#             "network_environments=<MagicMock name='mock.network_environment' id='...'>, "
#             "execution_environment=[], "
#             "test_experiment_dir=/tmp/experiment/Test_Case)"
#         )
#         self.assertEqual(str(self.test_case), expected_str)

#     def test_repr(self):
#         expected_repr = (
#             "TestCase(name=Test Case, "
#             "description=A test case description, "
#             "services={}, "
#             "network_environments=<MagicMock name='mock.network_environment' id='...'>, "
#             "execution_environment=[], "
#             "test_experiment_dir=/tmp/experiment/Test_Case)"
#         )
#         self.assertEqual(repr(self.test_case), expected_repr)

#     @patch("panther.core.test_cases.test_case.EventManager")
#     def test_run(self, MockEventManager):
#         self.test_case.logger = MagicMock()
#         self.test_case.register_default_observers = MagicMock()
#         self.test_case.setup_services = MagicMock()
#         self.test_case.setup_environment = MagicMock()
#         self.test_case.deploy_services = MagicMock()
#         self.test_case.execute_steps = MagicMock()
#         self.test_case.validate_assertions = MagicMock()
#         self.test_case.teardown_environment = MagicMock()

#         self.test_case.run()

#         self.test_case.logger.info.assert_called_with("Starting Test: Test Case")
#         self.test_case.register_default_observers.assert_called_once()
#         self.test_case.setup_services.assert_called_once()
#         self.test_case.setup_environment.assert_called_once()
#         self.test_case.deploy_services.assert_called_once()
#         self.test_case.execute_steps.assert_called_once()
#         self.test_case.validate_assertions.assert_called_once()
#         self.test_case.teardown_environment.assert_called_once()

#     def test_setup_testers(self):
#         self.test_case.logger = MagicMock()
#         self.test_case.plugin_manager.plugins_loader.get_testers = MagicMock(
#             return_value=["tester1", "tester2"]
#         )
#         self.test_case.global_config.paths.plugin_dir = "/plugins"
#         self.test_case.global_config.paths.services_dir = "services"
#         self.test_case.global_config.paths.testers_dir = "testers"
#         self.test_case.services = {
#             "service1": MagicMock(
#                 implementation=MagicMock(type="testers", name="tester1")
#             ),
#             "service2": MagicMock(
#                 implementation=MagicMock(type="testers", name="tester2")
#             ),
#         }

#         self.test_case.setup_testers()

#         self.test_case.logger.debug.assert_any_call("Setup Testers plugins ...")
#         self.test_case.logger.debug.assert_any_call(
#             "Looking for testers plugins at '/plugins/services/testers'"
#         )
#         self.test_case.logger.debug.assert_any_call(
#             "Available testers: ['tester1', 'tester2']"
#         )
#         self.test_case.logger.debug.assert_any_call(
#             "Test defined testers: [<MagicMock id='...'>, <MagicMock id='...'>]"
#         )

#     def test_setup_implementations(self):
#         self.test_case.logger = MagicMock()
#         self.test_case.plugin_manager.plugins_loader.get_implementations_for_protocol = MagicMock(
#             return_value=["impl1", "impl2"]
#         )
#         self.test_case.global_config.paths.plugin_dir = "/plugins"
#         self.test_case.global_config.paths.services_dir = "services"
#         self.test_case.global_config.paths.iut_dir = "iut"
#         self.test_case.services = {
#             "service1": MagicMock(implementation=MagicMock(type="iut", name="impl1")),
#             "service2": MagicMock(implementation=MagicMock(type="iut", name="impl2")),
#         }

#         self.test_case.setup_implementations()

#         self.test_case.logger.debug.assert_any_call(
#             "Setup Implementation Under Tests plugins ..."
#         )
#         self.test_case.logger.debug.assert_any_call(
#             "Looking for IUT plugins at '/plugins/services/iut'"
#         )
#         self.test_case.logger.debug.assert_any_call("Available protocols: []")
#         self.test_case.logger.debug.assert_any_call(
#             "Test defined implementations: [<MagicMock id='...'>, <MagicMock id='...'>]"
#         )


# if __name__ == "__main__":
#     unittest.main()
