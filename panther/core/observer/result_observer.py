# PANTHER-SCP/panther/core/observer/result_observer.py

import logging
from core.observer.observer_interface import IObserver
from core.observer.event import Event

class ResultObserver(IObserver):
    def __init__(self):
        self.logger = logging.getLogger("ResultObserver")

    def on_event(self, event: Event):
        """
        Handles an event.

        :param event: The event to handle.
        """
        pass
