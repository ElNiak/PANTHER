# import os
# import shutil
# import pytest
# from omegaconf import OmegaConf
# from panther.config.config_experiment_schema import ExperimentConfig
# from panther.config.config_manager import ConfigLoader
# from panther.config.config_global_schema import (
#     GlobalConfig,
#     LoggingConfig,
#     PathsConfig,
#     DockerConfig,
# )
# from omegaconf import ValidationError
# import yaml


# @pytest.fixture
# def sample_experiment_file(tmp_path):
#     experiment_path = tmp_path / "experiment.yaml"
#     experiment_path.write_text(
#         """
#     tests:
#       - name: test1
#         description: Test description
#         network_environment:
#           type: valid_plugin
#           config_param: value
#         execution_environment:
#           - type: valid_plugin
#             config_param: value
#         iterations: 10
#         services:
#           service1:
#             name: service1
#             timeout: 100
#             implementation:
#               name: impl1
#               type: iut
#             protocol:
#               name: protocol1
#               version: 1.0
#             ports: [80, 443]
#             generate_new_certificates: False
#         steps: ["step1", "step2"]
#         assertions: ["assertion1", "assertion2"]
#     """
#     )
#     return experiment_path


# @pytest.fixture
# def valid_plugin():
#     return {"type": "valid_plugin", "config_param": "value"}


# @pytest.fixture
# def sample_loaded_config():
#     return OmegaConf.create(
#         {
#             "logging": {
#                 "level": "DEBUG",
#                 "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
#             },
#             "paths": {
#                 "output_dir": "/tmp/output",
#                 "log_dir": "/tmp/logs",
#                 "config_dir": "/tmp/config",
#                 "plugin_dir": "/tmp/plugins",
#             },
#             "docker": {"build_docker_image": True},
#         }
#     )


# @pytest.fixture
# def config_loader():
#     return ConfigLoader(
#         experiment_file="dummy_experiment.yaml", output_dir="custom/output"
#     )


# def test_construct_global_config(config_loader, sample_loaded_config):
#     global_config = config_loader.construct_global_config(sample_loaded_config)

#     assert isinstance(global_config, GlobalConfig)
#     assert global_config.logging.level == "DEBUG"
#     assert (
#         global_config.logging.format
#         == "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
#     )
#     assert global_config.paths.output_dir == "custom/output"
#     assert global_config.paths.log_dir == "/tmp/logs"
#     assert global_config.paths.config_dir == "/tmp/config"
#     assert global_config.paths.plugin_dir == "/tmp/plugins"
#     assert global_config.docker.build_docker_image is True


# def test_validate_plugin_config_valid(config_loader):
#     plugin_type = "network_environment"
#     plugin_name = "valid_plugin"
#     plugin_config = OmegaConf.create({"type": "valid_plugin", "config_param": "value"})

#     config_loader.add_plugin_network_environment(plugin_name, plugin_config)
#     validated_config = config_loader.validate_plugin_config(
#         plugin_type, plugin_name, plugin_config
#     )

#     assert validated_config.type == "valid_plugin"
#     assert validated_config.config_param == "value"


# def test_validate_plugin_config_invalid(config_loader):
#     plugin_type = "network_environment"
#     plugin_name = "invalid_plugin"
#     plugin_config = OmegaConf.create(
#         {"type": "invalid_plugin", "config_param": "value"}
#     )

#     with pytest.raises(ValidationError):
#         config_loader.validate_plugin_config(plugin_type, plugin_name, plugin_config)


# def test_validate_plugin_config_missing_param(config_loader):
#     plugin_type = "network_environment"
#     plugin_name = "valid_plugin"
#     plugin_config = OmegaConf.create({"type": "valid_plugin"})

#     with pytest.raises(ValidationError):
#         config_loader.validate_plugin_config(plugin_type, plugin_name, plugin_config)


# def test_construct_experiment_config(config_loader):
#     loaded_config = OmegaConf.create(
#         {
#             "tests": [
#                 {
#                     "name": "test1",
#                     "description": "Test description",
#                     "network_environment": {
#                         "type": "valid_plugin",
#                         "config_param": "value",
#                     },
#                     "execution_environment": [
#                         {"type": "valid_plugin", "config_param": "value"}
#                     ],
#                     "iterations": 10,
#                     "services": {
#                         "service1": {
#                             "name": "service1",
#                             "timeout": 100,
#                             "implementation": {"name": "impl1", "type": "iut"},
#                             "protocol": {"name": "protocol1", "version": "1.0"},
#                             "ports": [80, 443],
#                             "generate_new_certificates": False,
#                         }
#                     },
#                     "steps": ["step1", "step2"],
#                     "assertions": ["assertion1", "assertion2"],
#                 }
#             ]
#         }
#     )
#     config_loader.add_plugin_network_environment(
#         "valid_plugin",
#         OmegaConf.create({"type": "valid_plugin", "config_param": "value"}),
#     )
#     config_loader.add_plugin_execution_environment(
#         "valid_plugin",
#         OmegaConf.create({"type": "valid_plugin", "config_param": "value"}),
#     )
#     config_loader.add_plugin_iut_service(
#         "impl1", OmegaConf.create({"name": "impl1", "type": "iut"})
#     )
#     config_loader.add_plugin_protocol(
#         "protocol1", OmegaConf.create({"name": "protocol1", "version": "1.0"})
#     )
#     config_loader.add_plugin_service(
#         "service1",
#         OmegaConf.create(
#             {
#                 "name": "service1",
#                 "timeout": 100,
#                 "implementation": "impl1",
#                 "protocol": "protocol1",
#                 "ports": [80, 443],
#                 "generate_new_certificates": False,
#             }
#         ),
#     )
#     experiment_config = config_loader.construct_experiment_config(loaded_config)

#     assert isinstance(experiment_config, ExperimentConfig)
#     assert len(experiment_config.tests) == 1
#     test_config = experiment_config.tests[0]
#     assert test_config.name == "test1"
#     assert test_config.description == "Test description"
#     assert test_config.network_environment.type == "valid_plugin"
#     assert test_config.network_environment.config_param == "value"
#     assert len(test_config.execution_environments) == 1
#     assert test_config.execution_environments[0].type == "valid_plugin"
#     assert test_config.execution_environments[0].config_param == "value"
#     assert test_config.iterations == 10
#     assert "service1" in test_config.services
#     service_config = test_config.services["service1"]
#     assert service_config.name == "service1"
#     assert service_config.timeout == 100
#     assert service_config.implementation.name == "impl1"
#     assert service_config.implementation.type == "iut"
#     assert service_config.protocol.name == "protocol1"
#     assert service_config.protocol.version == "1.0"
#     assert service_config.ports == [80, 443]
#     assert service_config.generate_new_certificates is False
#     assert test_config.steps == ["step1", "step2"]
#     assert test_config.assertions == ["assertion1", "assertion2"]


# def test_load_and_validate_experiment_config_valid(config_loader, mocker):
#     mocker.patch("os.path.exists", return_value=True)
#     mocker.patch(
#         "omegaconf.OmegaConf.load",
#         return_value=OmegaConf.create(
#             {
#                 "tests": [
#                     {
#                         "name": "test1",
#                         "description": "Test description",
#                         "network_environment": {
#                             "type": "valid_plugin",
#                             "config_param": "value",
#                         },
#                         "execution_environment": [
#                             {"type": "valid_plugin", "config_param": "value"}
#                         ],
#                         "iterations": 10,
#                         "services": {
#                             "service1": {
#                                 "name": "service1",
#                                 "timeout": 100,
#                                 "implementation": {"name": "impl1", "type": "iut"},
#                                 "protocol": {"name": "protocol1", "version": "1.0"},
#                                 "ports": [80, 443],
#                                 "generate_new_certificates": False,
#                             }
#                         },
#                         "steps": ["step1", "step2"],
#                         "assertions": ["assertion1", "assertion2"],
#                     }
#                 ]
#             }
#         ),
#     )
#     mocker.patch.object(
#         config_loader,
#         "construct_experiment_config",
#         return_value=ExperimentConfig(tests=[]),
#     )

#     experiment_config = config_loader.load_and_validate_experiment_config()

#     assert isinstance(experiment_config, ExperimentConfig)
#     config_loader.construct_experiment_config.assert_called_once()


# def test_load_and_validate_experiment_config_file_not_found(config_loader, mocker):
#     mocker.patch("os.path.exists", return_value=False)

#     with pytest.raises(FileNotFoundError):
#         config_loader.load_and_validate_experiment_config()


# def test_load_and_validate_experiment_config_validation_error(config_loader, mocker):
#     mocker.patch("os.path.exists", return_value=True)
#     mocker.patch(
#         "omegaconf.OmegaConf.load",
#         return_value=OmegaConf.create(
#             {
#                 "tests": [
#                     {
#                         "name": "test1",
#                         "description": "Test description",
#                         "network_environment": {
#                             "type": "invalid_plugin",
#                             "config_param": "value",
#                         },
#                     }
#                 ]
#             }
#         ),
#     )
#     mocker.patch.object(
#         config_loader,
#         "construct_experiment_config",
#         side_effect=ValidationError("Validation failed"),
#     )

#     with pytest.raises(ValidationError):
#         config_loader.load_and_validate_experiment_config()


# def test_load_and_validate_experiment_config_yaml_parser_error(config_loader, mocker):
#     mocker.patch("os.path.exists", return_value=True)
#     mocker.patch(
#         "omegaconf.OmegaConf.load",
#         side_effect=yaml.parser.ParserError("YAML parsing error"),
#     )

#     with pytest.raises(yaml.parser.ParserError):
#         config_loader.load_and_validate_experiment_config()


# def test_load_and_validate_experiment_config_unexpected_error(config_loader, mocker):
#     mocker.patch("os.path.exists", return_value=True)
#     mocker.patch("omegaconf.OmegaConf.load", side_effect=Exception("Unexpected error"))

#     with pytest.raises(Exception):
#         config_loader.load_and_validate_experiment_config()


# def test_load_and_validate_global_config_valid(config_loader, mocker):
#     mocker.patch("os.path.exists", return_value=True)
#     mocker.patch(
#         "omegaconf.OmegaConf.load",
#         return_value=OmegaConf.create(
#             {
#                 "logging": {
#                     "level": "DEBUG",
#                     "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
#                 },
#                 "paths": {
#                     "output_dir": "/tmp/output",
#                     "log_dir": "/tmp/logs",
#                     "config_dir": "/tmp/config",
#                     "plugin_dir": "/tmp/plugins",
#                 },
#                 "docker": {"build_docker_image": True},
#             }
#         ),
#     )
#     mocker.patch.object(
#         config_loader,
#         "construct_global_config",
#         return_value=GlobalConfig(
#             logging=LoggingConfig(
#                 level="DEBUG",
#                 format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
#             ),
#             paths=PathsConfig(
#                 output_dir="/tmp/output",
#                 log_dir="/tmp/logs",
#                 config_dir="/tmp/config",
#                 plugin_dir="/tmp/plugins",
#             ),
#             docker=DockerConfig(build_docker_image=True),
#         ),
#     )

#     global_config = config_loader.load_and_validate_global_config()

#     assert isinstance(global_config, GlobalConfig)
#     config_loader.construct_global_config.assert_called_once()


# def test_load_and_validate_global_config_file_not_found(config_loader, mocker):
#     mocker.patch("os.path.exists", return_value=False)

#     with pytest.raises(FileNotFoundError):
#         config_loader.load_and_validate_global_config()


# def test_load_and_validate_global_config_validation_error(config_loader, mocker):
#     mocker.patch("os.path.exists", return_value=True)
#     mocker.patch(
#         "omegaconf.OmegaConf.load",
#         return_value=OmegaConf.create(
#             {
#                 "logging": {
#                     "level": "DEBUG",
#                     "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
#                 },
#                 "paths": {
#                     "output_dir": "/tmp/output",
#                     "log_dir": "/tmp/logs",
#                     "config_dir": "/tmp/config",
#                     "plugin_dir": "/tmp/plugins",
#                 },
#                 "docker": {"build_docker_image": True},
#             }
#         ),
#     )
#     mocker.patch.object(
#         config_loader,
#         "construct_global_config",
#         side_effect=ValidationError("Validation failed"),
#     )

#     with pytest.raises(ValidationError):
#         config_loader.load_and_validate_global_config()


# def test_load_and_validate_global_config_yaml_parser_error(config_loader, mocker):
#     mocker.patch("os.path.exists", return_value=True)
#     mocker.patch(
#         "omegaconf.OmegaConf.load",
#         side_effect=yaml.parser.ParserError("YAML parsing error"),
#     )

#     with pytest.raises(yaml.parser.ParserError):
#         config_loader.load_and_validate_global_config()


# def test_load_and_validate_global_config_unexpected_error(config_loader, mocker):
#     mocker.patch("os.path.exists", return_value=True)
#     mocker.patch("omegaconf.OmegaConf.load", side_effect=Exception("Unexpected error"))

#     with pytest.raises(Exception):
#         config_loader.load_and_validate_global_config()


# def test_add_plugin_tester_service(config_loader, tmp_path, mocker):
#     testers_dir = tmp_path / "testers"
#     testers_dir.mkdir()
#     (testers_dir / "tester1.py").write_text("print('tester1')")
#     (testers_dir / "tester2.py").write_text("print('tester2')")

#     config_loader.testers_dir = str(testers_dir)
#     mocker.patch("os.makedirs")
#     mocker.patch("shutil.copy2")
#     mocker.patch("shutil.copytree")

#     config_loader.add_plugin_tester_service()

#     os.makedirs.assert_called()
#     shutil.copy2.assert_called()
#     shutil.copytree.assert_called()


# def test_add_plugin_iut_service(config_loader, tmp_path, mocker):
#     iut_dir = tmp_path / "iut"
#     iut_dir.mkdir()
#     (iut_dir / "iut1.py").write_text("print('iut1')")
#     (iut_dir / "iut2.py").write_text("print('iut2')")

#     config_loader.iut_dir = str(iut_dir)
#     mocker.patch("os.makedirs")
#     mocker.patch("shutil.copy2")
#     mocker.patch("shutil.copytree")

#     config_loader.add_plugin_iut_service()

#     os.makedirs.assert_called()
#     shutil.copy2.assert_called()
#     shutil.copytree.assert_called()


# def test_add_plugin_network_environment(config_loader, tmp_path, mocker):
#     net_env_dir = tmp_path / "net_env"
#     net_env_dir.mkdir()
#     (net_env_dir / "net_env1.py").write_text("print('net_env1')")
#     (net_env_dir / "net_env2.py").write_text("print('net_env2')")

#     config_loader.net_env_dir = str(net_env_dir)
#     mocker.patch("os.makedirs")
#     mocker.patch("shutil.copy2")
#     mocker.patch("shutil.copytree")

#     config_loader.add_plugin_network_environment()

#     os.makedirs.assert_called()
#     shutil.copy2.assert_called()
#     shutil.copytree.assert_called()


# def test_add_plugin_execution_environment(config_loader, tmp_path, mocker):
#     exec_env_dir = tmp_path / "exec_env"
#     exec_env_dir.mkdir()
#     (exec_env_dir / "exec_env1.py").write_text("print('exec_env1')")
#     (exec_env_dir / "exec_env2.py").write_text("print('exec_env2')")

#     config_loader.exec_env_dir = str(exec_env_dir)
#     mocker.patch("os.makedirs")
#     mocker.patch("shutil.copy2")
#     mocker.patch("shutil.copytree")

#     config_loader.add_plugin_execution_environment()

#     os.makedirs.assert_called()
#     shutil.copy2.assert_called()
#     shutil.copytree.assert_called()
