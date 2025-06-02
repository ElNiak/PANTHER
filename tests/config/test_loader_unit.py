"""
Unit tests for ConfigLoader class in config_manager.py

Tests focus on white-box testing with extensive mocking to ensure
no side effects and deterministic behavior.
"""

import pytest
import os
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from omegaconf import OmegaConf
import yaml

from panther.config.config_manager import ConfigLoader
from panther.config.config_global_schema import GlobalConfig, LoggingLevel


class TestConfigLoader:
    """Unit tests for ConfigLoader functionality."""

    @pytest.fixture
    def config_loader(self, tmp_path):
        """Create ConfigLoader instance with temporary paths."""
        experiment_file = str(tmp_path / "experiment.yaml")
        return ConfigLoader(
            experiment_file=experiment_file,
            output_dir=str(tmp_path / "output"),
            exec_env_dir=str(tmp_path / "exec_env"),
            net_env_dir=str(tmp_path / "net_env"),
            iut_dir=str(tmp_path / "iut"),
            testers_dir=str(tmp_path / "testers"),
        )

    def test_init_sets_attributes_correctly(self, tmp_path):
        """Test ConfigLoader initialization sets all attributes."""
        experiment_file = str(tmp_path / "test.yaml")
        output_dir = str(tmp_path / "output")

        loader = ConfigLoader(
            experiment_file=experiment_file,
            output_dir=output_dir,
            exec_env_dir="exec",
            net_env_dir="net",
            iut_dir="iut",
            testers_dir="testers",
        )

        assert loader.experiment_file == experiment_file
        assert loader.output_dir == output_dir
        assert loader.exec_env_dir == "exec"
        assert loader.net_env_dir == "net"
        assert loader.iut_dir == "iut"
        assert loader.testers_dir == "testers"
        assert loader.global_config is None
        assert (
            loader._panther_dir
            == Path(os.path.dirname(__file__)).parent.parent / "panther"
        )

    def test_construct_global_config_complete(self, config_loader, valid_cfg_dict):
        """Test construct_global_config with complete configuration."""
        loaded_config = OmegaConf.create(valid_cfg_dict)

        with patch("panther.config.config_manager.OmegaConf.merge") as mock_merge:
            result = config_loader.construct_global_config(loaded_config)

            assert isinstance(result, GlobalConfig)
            assert result.logging.level == LoggingLevel.DEBUG
            assert result.logging.format == valid_cfg_dict["logging"]["format"]
            assert (
                result.paths.output_dir == config_loader.output_dir
            )  # Should use override
            assert (
                result.docker.build_docker_image
                == valid_cfg_dict["docker"]["build_docker_image"]
            )
            assert result.features.fast_fail == valid_cfg_dict["features"]["fast_fail"]

            # Verify OmegaConf.merge was called for each config section
            assert mock_merge.call_count >= 4

    def test_construct_global_config_minimal(self, config_loader):
        """Test construct_global_config with minimal configuration."""
        minimal_config = OmegaConf.create(
            {
                "logging": {"level": "INFO"},
                "paths": {"output_dir": "outputs"},
                "docker": {"build_docker_image": False},
            }
        )

        with patch("panther.config.config_manager.OmegaConf.merge"):
            result = config_loader.construct_global_config(minimal_config)

            assert isinstance(result, GlobalConfig)
            assert result.logging.level == LoggingLevel.INFO
            assert result.paths.output_dir == config_loader.output_dir
            assert result.docker.build_docker_image is False
            # Should use defaults for missing features section
            assert result.features.logger_observer is True
            assert result.features.storage_handler is True
            assert result.features.fast_fail is True

    def test_construct_global_config_missing_features_section(self, config_loader):
        """Test construct_global_config when features section is missing."""
        config_without_features = OmegaConf.create(
            {
                "logging": {"level": "DEBUG"},
                "paths": {"output_dir": "outputs"},
                "docker": {"build_docker_image": True},
            }
        )

        with patch("panther.config.config_manager.OmegaConf.merge"):
            result = config_loader.construct_global_config(config_without_features)

            assert isinstance(result, GlobalConfig)
            # Should create default FeatureConfig
            assert result.features.logger_observer is True
            assert result.features.storage_handler is True
            assert result.features.fast_fail is True

    @patch("panther.config.config_manager.ConfigLoader.copy_plugin_files")
    def test_add_plugin_tester_service_with_directory(
        self, mock_copy, config_loader, tmp_path
    ):
        """Test add_plugin_tester_service when testers_dir is set."""
        testers_dir = tmp_path / "custom_testers"
        testers_dir.mkdir()
        config_loader.testers_dir = str(testers_dir)

        expected_target = os.path.join(
            config_loader._panther_dir,
            "plugins",
            "services",
            "testers",
            testers_dir.name,
        )

        with patch("builtins.print") as mock_print:
            config_loader.add_plugin_tester_service()

            mock_print.assert_called_once_with(f"Copying testers from {testers_dir}")
            mock_copy.assert_called_once_with(expected_target)
            assert isinstance(config_loader.testers_dir, Path)

    def test_add_plugin_tester_service_no_directory(self, config_loader):
        """Test add_plugin_tester_service when testers_dir is not set."""
        config_loader.testers_dir = ""

        with patch(
            "panther.config.config_manager.ConfigLoader.copy_plugin_files"
        ) as mock_copy:
            config_loader.add_plugin_tester_service()

            mock_copy.assert_not_called()

    @patch("os.makedirs")
    @patch("os.path.exists")
    @patch("os.listdir")
    @patch("shutil.copytree")
    @patch("shutil.copy2")
    @patch("shutil.rmtree")
    def test_copy_plugin_files_directory_structure(
        self,
        mock_rmtree,
        mock_copy2,
        mock_copytree,
        mock_listdir,
        mock_exists,
        mock_makedirs,
        config_loader,
        tmp_path,
    ):
        """Test copy_plugin_files with mixed directory and file structure."""
        source_dir = tmp_path / "source"
        target_dir = str(tmp_path / "target")

        config_loader.testers_dir = source_dir

        # Mock file system structure
        mock_exists.side_effect = (
            lambda path: path != target_dir
        )  # Target doesn't exist initially
        mock_listdir.return_value = ["subdir", "file.py", "config.yaml"]

        def isdir_side_effect(path):
            return "subdir" in str(path)

        with patch("os.path.isdir", side_effect=isdir_side_effect):
            with patch("os.path.join", side_effect=os.path.join):
                config_loader.copy_plugin_files(target_dir)

        # Verify directory creation
        mock_makedirs.assert_called_once_with(target_dir)

        # Verify copying operations
        mock_copytree.assert_called_once()
        assert mock_copy2.call_count == 2  # Two files

    @patch("shutil.rmtree")
    @patch("os.path.exists")
    def test_remove_plugin_tester_service_with_directory(
        self, mock_exists, mock_rmtree, config_loader, tmp_path
    ):
        """Test remove_plugin_tester_service when directory exists."""
        testers_dir = tmp_path / "test_testers"
        config_loader.testers_dir = str(testers_dir)

        target_path = os.path.join(
            config_loader._panther_dir,
            "plugins",
            "services",
            "testers",
            testers_dir.name,
        )

        mock_exists.return_value = True

        with patch("builtins.print") as mock_print:
            config_loader.remove_plugin_tester_service()

            mock_print.assert_called_once_with(f"Removing testers {testers_dir}")
            mock_rmtree.assert_called_once_with(target_path)

    def test_remove_plugin_tester_service_no_directory(self, config_loader):
        """Test remove_plugin_tester_service when testers_dir is not set."""
        config_loader.testers_dir = ""

        with patch("shutil.rmtree") as mock_rmtree:
            config_loader.remove_plugin_tester_service()

            mock_rmtree.assert_not_called()

    @patch("panther.config.config_manager.ConfigLoader.copy_plugin_files")
    def test_add_plugin_iut_service(self, mock_copy, config_loader, tmp_path):
        """Test add_plugin_iut_service functionality."""
        iut_dir = tmp_path / "custom_iut"
        iut_dir.mkdir()
        config_loader.iut_dir = str(iut_dir)

        expected_target = os.path.join(
            config_loader._panther_dir, "plugins", "services", "iut", iut_dir.name
        )

        config_loader.add_plugin_iut_service()

        mock_copy.assert_called_once_with(expected_target)

    def test_add_plugin_iut_service_no_directory(self, config_loader):
        """Test add_plugin_iut_service when iut_dir is not set."""
        config_loader.iut_dir = ""

        with patch(
            "panther.config.config_manager.ConfigLoader.copy_plugin_files"
        ) as mock_copy:
            config_loader.add_plugin_iut_service()

            mock_copy.assert_not_called()

    @patch("panther.config.config_manager.ConfigLoader.copy_plugin_files")
    def test_add_plugin_network_environment(self, mock_copy, config_loader, tmp_path):
        """Test add_plugin_network_environment functionality."""
        net_env_dir = tmp_path / "custom_net_env"
        net_env_dir.mkdir()
        config_loader.net_env_dir = str(net_env_dir)

        expected_target = os.path.join(
            config_loader._panther_dir,
            "plugins",
            "environments",
            "network_environment",
            net_env_dir.name,
        )

        config_loader.add_plugin_network_environment()

        mock_copy.assert_called_once_with(expected_target)

    @patch("panther.config.config_manager.ConfigLoader.copy_plugin_files")
    def test_add_plugin_execution_environment(self, mock_copy, config_loader, tmp_path):
        """Test add_plugin_execution_environment functionality."""
        exec_env_dir = tmp_path / "custom_exec_env"
        exec_env_dir.mkdir()
        config_loader.exec_env_dir = str(exec_env_dir)

        expected_target = os.path.join(
            config_loader._panther_dir,
            "plugins",
            "environments",
            "execution_environment",
            exec_env_dir.name,
        )

        config_loader.add_plugin_execution_environment()

        mock_copy.assert_called_once_with(expected_target)

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    def test_load_and_validate_global_config_file_not_found(
        self, mock_exists, mock_file, config_loader
    ):
        """Test load_and_validate_global_config when config file doesn't exist."""
        mock_exists.return_value = False

        with pytest.raises(FileNotFoundError, match="Global configuration file"):
            config_loader.load_and_validate_global_config()

        mock_file.assert_not_called()

    @patch("yaml.safe_load")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    def test_load_and_validate_global_config_yaml_error(
        self, mock_exists, mock_file, mock_yaml, config_loader
    ):
        """Test load_and_validate_global_config with YAML parsing error."""
        mock_exists.return_value = True
        mock_yaml.side_effect = yaml.YAMLError("Invalid YAML")

        with pytest.raises(ValueError, match="Error parsing global configuration"):
            config_loader.load_and_validate_global_config()

    @patch("panther.config.config_manager.ConfigLoader.construct_global_config")
    @patch("yaml.safe_load")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    def test_load_and_validate_global_config_success(
        self,
        mock_exists,
        mock_file,
        mock_yaml,
        mock_construct,
        config_loader,
        valid_cfg_dict,
    ):
        """Test successful load_and_validate_global_config."""
        mock_exists.return_value = True
        mock_yaml.return_value = valid_cfg_dict
        mock_global_config = Mock(spec=GlobalConfig)
        mock_construct.return_value = mock_global_config

        result = config_loader.load_and_validate_global_config()

        assert result == mock_global_config
        mock_file.assert_called_once()
        mock_yaml.assert_called_once()
        mock_construct.assert_called_once()

    @patch("panther.config.config_manager.OmegaConf.load")
    @patch("os.path.exists")
    def test_load_and_validate_experiment_config_file_not_found(
        self, mock_exists, mock_omega_load, config_loader
    ):
        """Test load_and_validate_experiment_config when file doesn't exist."""
        mock_exists.return_value = False

        with pytest.raises(FileNotFoundError, match="Experiment configuration file"):
            config_loader.load_and_validate_experiment_config()

        mock_omega_load.assert_not_called()

    @patch("panther.config.config_manager.OmegaConf.load")
    @patch("os.path.exists")
    def test_load_and_validate_experiment_config_omega_error(
        self, mock_exists, mock_omega_load, config_loader
    ):
        """Test load_and_validate_experiment_config with OmegaConf error."""
        mock_exists.return_value = True
        mock_omega_load.side_effect = Exception("OmegaConf parsing error")

        with pytest.raises(ValueError, match="Error parsing experiment configuration"):
            config_loader.load_and_validate_experiment_config()

    @patch("panther.config.config_manager.ConfigLoader.construct_experiment_config")
    @patch("panther.config.config_manager.OmegaConf.load")
    @patch("os.path.exists")
    def test_load_and_validate_experiment_config_success(
        self,
        mock_exists,
        mock_omega_load,
        mock_construct,
        config_loader,
        valid_experiment_cfg_dict,
    ):
        """Test successful load_and_validate_experiment_config."""
        mock_exists.return_value = True
        mock_omega_config = OmegaConf.create(valid_experiment_cfg_dict)
        mock_omega_load.return_value = mock_omega_config
        mock_experiment_config = Mock()
        mock_construct.return_value = mock_experiment_config

        result = config_loader.load_and_validate_experiment_config()

        assert result == mock_experiment_config
        mock_omega_load.assert_called_once_with(config_loader.experiment_file)
        mock_construct.assert_called_once_with(mock_omega_config)

    def test_construct_experiment_config_basic(
        self, config_loader, valid_experiment_cfg_dict
    ):
        """Test construct_experiment_config with valid configuration."""
        loaded_config = OmegaConf.create(valid_experiment_cfg_dict)

        with patch("panther.config.config_manager.OmegaConf.merge") as mock_merge:
            result = config_loader.construct_experiment_config(loaded_config)

            # Should return the loaded config as-is for now
            # (Implementation may vary based on actual logic)
            assert result is not None
            mock_merge.assert_called()

    def test_config_loader_sets_global_config_attribute(
        self, config_loader, valid_cfg_dict
    ):
        """Test that construct_global_config sets the global_config attribute."""
        loaded_config = OmegaConf.create(valid_cfg_dict)

        assert config_loader.global_config is None

        result = config_loader.construct_global_config(loaded_config)

        assert config_loader.global_config is result
        assert config_loader.global_config is not None
