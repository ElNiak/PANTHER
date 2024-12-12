from enum import Enum
from dataclasses import dataclass

# Logging Configuration
LoggingLevel = Enum("LoggingLevel", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])


@dataclass
class LoggingConfig:
    level: LoggingLevel = LoggingLevel.DEBUG  # Limited valid values
    format: str = "%(asctime)s [%(levelname)s] - %(module)s - %(message)s"


# Paths Configuration
@dataclass
class PathsConfig:
    output_dir: str = "panther/outputs"
    log_dir: str = "panther/outputs/logs"
    config_dir: str = "panther/configs"
    plugin_dir: str = "panther/plugins"
    services_dir: str = "services"
    iut_dir: str = "iut"
    testers_dir: str = "testers"


@dataclass
class AdditionalPathsConfig:
    exec_env_dir: str = ""
    net_env_dir: str = ""
    iut_dir: str = ""
    testers_dir: str = ""


# Docker Configuration
@dataclass
class DockerConfig:
    build_docker_image: bool = True
    remove_docker_image: bool = True
    remove_docker_container: bool = True
    remove_docker_network: bool = True
    remove_docker_volume: bool = True


# Feature Configuration
@dataclass
class FeatureConfig:
    logger_observer: bool = True
    storage_handler: bool = True


@dataclass
class GlobalConfig:
    logging: LoggingConfig = LoggingConfig()
    paths: PathsConfig = PathsConfig()
    optional_paths: AdditionalPathsConfig = AdditionalPathsConfig()
    docker: DockerConfig = DockerConfig()
    features: FeatureConfig = FeatureConfig()
