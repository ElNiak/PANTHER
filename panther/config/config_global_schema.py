from enum import Enum
from dataclasses import dataclass

# Logging Configuration
LoggingLevel = Enum("LoggingLevel", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])


@dataclass
class LoggingConfig:
    """
    Configuration class for logging settings.

    Attributes:
        level (LoggingLevel): The logging level, with limited valid values.
        format (str): The format string for log messages.
    """

    level: LoggingLevel = LoggingLevel.DEBUG  # Limited valid values
    format: str = "%(asctime)s [%(levelname)s] - %(module)s - %(message)s"


# Paths Configuration
@dataclass
class PathsConfig:
    """
    PathsConfig is a configuration class that defines various directory paths used in the application.

    Attributes:
        output_dir (str): Directory path where output files are stored. Default is "panther/outputs".
        log_dir (str): Directory path where log files are stored. Default is "panther/outputs/logs".
        config_dir (str): Directory path where configuration files are stored. Default is "panther/configs".
        plugin_dir (str): Directory path where plugin files are stored. Default is "panther/plugins".
        services_dir (str): Directory path where service files are stored. Default is "services".
        iut_dir (str): Directory path where IUT (Implementation Under Test) files are stored. Default is "iut".
        testers_dir (str): Directory path where tester files are stored. Default is "testers".
    """

    output_dir: str = "panther/outputs"
    log_dir: str = "panther/outputs/logs"
    config_dir: str = "panther/configs"
    plugin_dir: str = "panther/plugins"
    services_dir: str = "services"
    iut_dir: str = "iut"
    testers_dir: str = "testers"


@dataclass
class AdditionalPathsConfig:
    """
    AdditionalPathsConfig is a configuration class that holds directory paths for various environments.

    Attributes:
        exec_env_dir (str): Path to the execution environment directory.
        net_env_dir (str): Path to the network environment directory.
        iut_dir (str): Path to the IUT (Implementation Under Test) directory.
        testers_dir (str): Path to the testers directory.
    """

    exec_env_dir: str = ""
    net_env_dir: str = ""
    iut_dir: str = ""
    testers_dir: str = ""


# Docker Configuration
@dataclass
class DockerConfig:
    """
    Configuration settings for Docker operations.

    Attributes:
        build_docker_image (bool): Flag to determine if the Docker image should be built.
        remove_docker_image (bool): Flag to determine if the Docker image should be removed.
        remove_docker_container (bool): Flag to determine if the Docker container should be removed.
        remove_docker_network (bool): Flag to determine if the Docker network should be removed.
        remove_docker_volume (bool): Flag to determine if the Docker volume should be removed.
    """

    build_docker_image: bool = True
    remove_docker_image: bool = True
    remove_docker_container: bool = True
    remove_docker_network: bool = True
    remove_docker_volume: bool = True


# Feature Configuration
@dataclass
class FeatureConfig:
    """
    FeatureConfig class is used to configure global features for the application.

    Attributes:
        logger_observer (bool): Indicates whether the logger observer feature is enabled. Default is True.
        storage_handler (bool): Indicates whether the storage handler feature is enabled. Default is True.
    """
    logger_observer: bool = True
    storage_handler: bool = True
    fast_fail: bool = True


@dataclass
class GlobalConfig:
    """
    GlobalConfig class holds the configuration settings for the application.

    Attributes:
        logging (LoggingConfig): Configuration for logging.
        paths (PathsConfig): Configuration for paths.
        optional_paths (AdditionalPathsConfig): Configuration for optional paths.
        docker (DockerConfig): Configuration for Docker.
        features (FeatureConfig): Configuration for features.
    """
    logging: LoggingConfig = LoggingConfig()
    paths: PathsConfig = PathsConfig()
    optional_paths: AdditionalPathsConfig = AdditionalPathsConfig()
    docker: DockerConfig = DockerConfig()
    features: FeatureConfig = FeatureConfig()
