# PANTHER-SCP/panther/core/experiment.py

from omegaconf import DictConfig

class Experiment:
    def __init__(self, config: DictConfig):
        self.name = config.name
        self.description = config.description
        self.protocol = config.protocol
        self.environment = config.environment
        self.services = config.services
        self.steps = config.steps
        self.assertions = config.assertions
