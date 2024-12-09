from enum import Enum
from omegaconf import MISSING
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal, Type

# Logging Configuration
LoggingLevel = Enum("LoggingLevel", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
@dataclass
class LoggingConfig:
    level: LoggingLevel = LoggingLevel.DEBUG # Limited valid values
    format: str = "%(asctime)s [%(levelname)s] - %(module)s - %(message)s"


# Paths Configuration
@dataclass
class PathsConfig:
    output_dir: str = "outputs"
    log_dir: str = "outputs/logs"
    config_dir: str = "configs"
    plugin_dir: str = "plugins"
    services_dir: str = "services"
    iut_dir: str = "iut"
    testers_dir: str = "testers"

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
    optional_paths: PathsConfig = PathsConfig()
    docker: DockerConfig = DockerConfig()
    features: FeatureConfig = FeatureConfig()