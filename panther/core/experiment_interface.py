from abc import ABC, abstractmethod

class Experiment(ABC):
    @abstractmethod
    def configure(self):
        pass

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def collect_results(self):
        pass
