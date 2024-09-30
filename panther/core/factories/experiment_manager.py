from abc import ABC, abstractmethod

from core.experiment import Experiment

class ExperimentFactory(ABC):
    @abstractmethod
    def create_experiment(self, config: dict) -> Experiment:
        pass
