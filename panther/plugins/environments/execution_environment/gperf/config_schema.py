from dataclasses import dataclass

from config.config_experiment_schema import ExecutionEnvironmentConfig


@dataclass
class GperfConfig(ExecutionEnvironmentConfig):
    sampling_rate: int = 1000
    output_dir: str = "/perf_data"
