
from panther.core.interfaces.observer_interface import IObserver
from core.experiment import Experiment


class GUIObserver(IObserver):
    """
    GUIObserver is a concrete implementation of the Observer interface that is intended to update the GUI based on changes in the Experiment subject.

    Methods:
        update(subject: Experiment) -> None:
            Raises a NotImplementedError. This method should be overridden to define how the GUI should be updated when the Experiment subject changes.
    """
    def update(self, subject: Experiment) -> None:
        raise NotImplementedError