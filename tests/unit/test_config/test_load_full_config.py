"""Tests for ConfigLoadingMixin.load_full_config()."""

import pytest
import yaml

from panther.config.core.mixins.config_loading import ConfigLoadingMixin

pytestmark = [pytest.mark.unit]


class StubManager(ConfigLoadingMixin):
    """Minimal stub that satisfies ConfigLoadingMixin's dependencies."""

    def __init__(self):
        super().__init__()
        self.panther_dir = None
        self.current_global_config = None
        self.current_experiment_config = None


class TestLoadFullConfig:
    """Test the unified load_full_config() entry point."""

    @pytest.fixture
    def manager(self):
        return StubManager()

    @pytest.fixture
    def minimal_config_file(self, tmp_path):
        """Create a minimal valid experiment config file."""
        config = {
            "logging": {"level": "DEBUG"},
            "tests": [
                {
                    "name": "test1",
                    "network_environment": {"type": "docker_compose"},
                    "services": {
                        "server": {
                            "implementation": {"name": "picoquic", "type": "iut"},
                            "protocol": {
                                "name": "quic",
                                "version": "rfc9000",
                                "role": "server",
                            },
                        }
                    },
                }
            ],
        }
        config_path = tmp_path / "test_config.yaml"
        config_path.write_text(yaml.dump(config))
        return str(config_path)

    def test_raises_on_missing_file(self, manager):
        with pytest.raises(FileNotFoundError):
            manager.load_full_config("/nonexistent/path.yaml")

    def test_returns_global_and_experiment_tuple(self, manager, minimal_config_file):
        global_config, experiment_config = manager.load_full_config(minimal_config_file)

        from panther.config.core.models.experiment import ExperimentConfig
        from panther.config.core.models.global_config import GlobalConfig

        assert isinstance(global_config, GlobalConfig)
        assert isinstance(experiment_config, ExperimentConfig)

    def test_splits_global_sections(self, manager, minimal_config_file):
        """Global sections (like 'logging') go to GlobalConfig."""
        global_config, _ = manager.load_full_config(minimal_config_file)
        assert global_config.logging.level == "DEBUG"

    def test_splits_experiment_sections(self, manager, minimal_config_file):
        """Non-global sections (like 'tests') go to ExperimentConfig."""
        _, experiment_config = manager.load_full_config(minimal_config_file)
        assert len(experiment_config.tests) == 1
        assert experiment_config.tests[0].name == "test1"

    def test_cli_overrides_applied(self, manager, minimal_config_file):
        """CLI overrides should take precedence over YAML values."""
        global_config, _ = manager.load_full_config(
            minimal_config_file,
            cli_overrides={"logging.level": "ERROR"},
        )
        assert global_config.logging.level == "ERROR"

    def test_stores_configs_on_manager(self, manager, minimal_config_file):
        global_config, experiment_config = manager.load_full_config(minimal_config_file)
        assert manager.current_global_config is global_config
        assert manager.current_experiment_config is experiment_config

    def test_empty_yaml_raises_for_missing_tests(self, manager, tmp_path):
        """An empty YAML file should raise because ExperimentConfig requires tests."""
        config_path = tmp_path / "empty.yaml"
        config_path.write_text("")

        with pytest.raises(ValueError, match="At least one test"):
            manager.load_full_config(str(config_path))
