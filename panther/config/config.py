# PANTHER-SCP/panther/config/config.py

import os
from omegaconf import OmegaConf

class ConfigLoader:
    def __init__(self, config_dir: str):
        self.config_dir = config_dir
        self.global_config = self.load_global_config()
        self.experiment_config = self.load_experiment_config()

    def load_global_config(self):
        global_config_path = os.path.join(self.config_dir, "global_config.yaml")
        if not os.path.exists(global_config_path):
            raise FileNotFoundError(f"Global configuration file '{global_config_path}' not found.")
        return OmegaConf.load(global_config_path)

    def load_experiment_config(self):
        experiment_config_path = os.path.join(self.config_dir, "experiment_config.yaml")
        if not os.path.exists(experiment_config_path):
            raise FileNotFoundError(f"Experiment configuration file '{experiment_config_path}' not found.")
        return OmegaConf.load(experiment_config_path)
