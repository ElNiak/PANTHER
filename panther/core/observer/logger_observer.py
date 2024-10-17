
import logging
from core.observer.observer_interface import IObserver
from core.observer.event import Event

class LoggerObserver(IObserver):
    """
    LoggerObserver is a concrete implementation of the Observer interface that is used to log updates from the subject.

    Methods:
        update(subject: Experiment) -> None:
            This method is called when the subject's state changes. It should be implemented to handle the update logic.
            Args:
                subject (Experiment): The subject that is being observed.
            Raises:
                NotImplementedError: This method should be overridden in subclasses.
    """
    def __init__(self):
        self.logger = logging.getLogger("LoggingObserver")


    def on_event(self, event: Event):
        """
        Handles an event.

        :param event: The event to handle.
        """
        self.logger.info(f"Received event '{event.name}' with data: {event.data}")