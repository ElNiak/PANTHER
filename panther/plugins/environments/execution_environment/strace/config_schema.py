from dataclasses import dataclass


@dataclass
class StraceConfig:
    sampling_rate: int = 1000
    output_dir: str = "/perf_data"
