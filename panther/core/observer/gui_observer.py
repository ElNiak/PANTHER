from abc import ABC
from panther.core.observer.event import Event
from panther.core.observer.observer_interface import IObserver


class GUIObserver(IObserver, ABC):
    """
    GUIObserver is a concrete implementation of the Observer interface that is intended to update the GUI based on changes in the Experiment subject.

    Methods:
        update(subject: Experiment) -> None:
            Raises a NotImplementedError. This method should be overridden to define how the GUI should be updated when the Experiment subject changes.
    """

    def on_event(self, event: Event):
        """
        Handles an event.

        :param event: The event to handle.
        """
        pass

    def update(self, subject) -> None:
        raise NotImplementedError
