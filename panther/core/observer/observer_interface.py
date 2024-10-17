from abc import ABC, abstractmethod

from core.observer.event import Event


class IObserver(ABC):
    """
    The Observer interface declares the update method, used by subjects.
    """

    @abstractmethod
    def on_event(self, event: Event):
        """
        Handles an event.

        :param event: The event to handle.
        """
        pass