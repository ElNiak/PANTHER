# core/observer/event_manager.py

from abc import ABC
import logging
from typing import List
from core.observer.event import Event
from core.interfaces.observer_interface import IObserver

class EventManager(ABC):
    def __init__(self):
        self.logger = logging.getLogger("EventManager")
        self.observers: List[IObserver] = []

    def register_observer(self, observer: IObserver):
        """
        Registers an observer to receive events.

        :param observer: The observer instance to register.
        """
        self.observers.append(observer)
        self.logger.debug(f"Registered observer '{observer.__class__.__name__}'")

    def unregister_observer(self, observer: IObserver):
        """
        Unregisters an observer from receiving events.

        :param observer: The observer instance to unregister.
        """
        self.observers.remove(observer)
        self.logger.debug(f"Unregistered observer '{observer.__class__.__name__}'")

    def notify(self, event: Event):
        """
        Notifies all registered observers about an event.

        :param event: The event to notify observers about.
        """
        self.logger.debug(f"Notifying observers about event '{event.name}' with data {event.data}")
        for observer in self.observers:
            try:
                observer.on_event(event)
            except Exception as e:
                self.logger.error(f"Error notifying observer '{observer.__class__.__name__}': {e}")
