# PANTHER-SCP/panther/core/commands/command.py

from abc import ABC, abstractmethod

class Command(ABC):
    @abstractmethod
    def execute(self, *args, **kwargs):
        """
        Executes the command.
        """
        pass
