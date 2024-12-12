from hypothesis import given, strategies as st
from panther.config.config_global_schema import (
    GlobalConfig,
    LoggingConfig,
    PathsConfig,
    AdditionalPathsConfig,
    DockerConfig,
    FeatureConfig,
    LoggingLevel,
)


def test_default_global_config():
    config = GlobalConfig()
    assert config.logging.level == LoggingLevel.DEBUG
    assert (
        config.logging.format
        == "%(asctime)s [%(levelname)s] - %(module)s - %(message)s"
    )
    assert config.paths.output_dir == "panther/outputs"
    assert config.paths.log_dir == "panther/outputs/logs"
    assert config.paths.config_dir == "panther/configs"
    assert config.paths.plugin_dir == "panther/plugins"
    assert config.paths.services_dir == "services"
    assert config.paths.iut_dir == "iut"
    assert config.paths.testers_dir == "testers"
    assert config.optional_paths.exec_env_dir == ""
    assert config.optional_paths.net_env_dir == ""
    assert config.optional_paths.iut_dir == ""
    assert config.optional_paths.testers_dir == ""
    assert config.docker.build_docker_image is True
    assert config.docker.remove_docker_image is True
    assert config.docker.remove_docker_container is True
    assert config.docker.remove_docker_network is True
    assert config.docker.remove_docker_volume is True
    assert config.features.logger_observer is True
    assert config.features.storage_handler is True


@given(st.builds(LoggingConfig))
def test_logging_config(logging_config):
    assert isinstance(logging_config.level, LoggingLevel)
    assert isinstance(logging_config.format, str)


@given(st.builds(PathsConfig))
def test_paths_config(paths_config):
    assert isinstance(paths_config.output_dir, str)
    assert isinstance(paths_config.log_dir, str)
    assert isinstance(paths_config.config_dir, str)
    assert isinstance(paths_config.plugin_dir, str)
    assert isinstance(paths_config.services_dir, str)
    assert isinstance(paths_config.iut_dir, str)
    assert isinstance(paths_config.testers_dir, str)


@given(st.builds(AdditionalPathsConfig))
def test_additional_paths_config(additional_paths_config):
    assert isinstance(additional_paths_config.exec_env_dir, str)
    assert isinstance(additional_paths_config.net_env_dir, str)
    assert isinstance(additional_paths_config.iut_dir, str)
    assert isinstance(additional_paths_config.testers_dir, str)


@given(st.builds(DockerConfig))
def test_docker_config(docker_config):
    assert isinstance(docker_config.build_docker_image, bool)
    assert isinstance(docker_config.remove_docker_image, bool)
    assert isinstance(docker_config.remove_docker_container, bool)
    assert isinstance(docker_config.remove_docker_network, bool)
    assert isinstance(docker_config.remove_docker_volume, bool)


@given(st.builds(FeatureConfig))
def test_feature_config(feature_config):
    assert isinstance(feature_config.logger_observer, bool)
    assert isinstance(feature_config.storage_handler, bool)


@given(st.builds(GlobalConfig))
def test_global_config(global_config):
    assert isinstance(global_config.logging, LoggingConfig)
    assert isinstance(global_config.paths, PathsConfig)
    assert isinstance(global_config.optional_paths, AdditionalPathsConfig)
    assert isinstance(global_config.docker, DockerConfig)
    assert isinstance(global_config.features, FeatureConfig)
