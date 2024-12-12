import logging
from panther.core.observer.observer_interface import IObserver
from panther.core.observer.event import Event


class ExperimentObserver(IObserver):
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
        self.environment = None
        self.logger = logging.getLogger("ExperimentObserver")
        self.experiment_finished_early = False

    def on_event(self, event: Event):
        """
        Handles an event.

        :param event: The event to handle.
        """
        if event.name == "experiment_finished_early":
            if event.data["action"] == "notify":
                self.logger.debug("Experiment finished early")
                self.experiment_finished_early = True
            return self.experiment_finished_early

        if event.name == "step_progress":
            self.logger.debug(f"Monitoring environment: {self.environment}")
            if hasattr(self.environment, "monitor_environment"):
                self.environment.monitor_environment()
            else:
                self.logger.debug("Environment does not support monitoring")

        if event.name == "services_deployed":
            self.environment = event.data["environment"]
