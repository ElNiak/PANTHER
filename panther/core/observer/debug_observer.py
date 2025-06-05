"""
Debug observer for monitoring events in the system.
"""

import logging
from datetime import datetime

from panther.core.observer.events import Event
from panther.core.observer.core.observer_interface import IObserver


class EventDebugObserver(IObserver):
    """
    Observer that logs all events for debugging purposes.

    This observer tracks event flow, timing, and relationships between events,
    making it useful for debugging complex event interactions and timing issues.

    Attributes:
        events (List[Dict]): List of tracked events with timestamps and data
        logger (logging.Logger): Logger for the observer
    """

    def __init__(self, output_file: str | None = None, log_level: int = logging.DEBUG):
        """
        Initialize the debug observer.

        Args:
            output_file: Optional file path to write event logs
            log_level: Logging level for the observer
        """
        self.logger = logging.getLogger("EventDebugObserver")
        self.logger.setLevel(log_level)
        self.events = []

        # Setup log file for event debugging
        if output_file:
            handler = logging.FileHandler(output_file)
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def on_event(self, event: Event) -> None:
        """
        Log every event with detailed information.

        Args:
            event: The event to log
        """
        event_type = event.name if hasattr(event, "name") else type(event).__name__
        event_data = event.data if hasattr(event, "data") else {}

        # Store event for analysis
        event_entry = {
            "timestamp": datetime.now(),
            "event_type": event_type,
            "event_data": event_data,
        }
        self.events.append(event_entry)

        # Log event details
        self.logger.debug("Event: %s - Data: %s", event_type, event_data)

    def get_event_history(
        self, event_type: str | None = None, limit: int | None = None
    ) -> list[dict]:
        """
        Get history of events, optionally filtered by type.

        Args:
            event_type: Optional event type to filter by
            limit: Optional maximum number of events to return

        Returns:
            List of event entries
        """
        if event_type:
            filtered = [e for e in self.events if e["event_type"] == event_type]
            return filtered[-limit:] if limit else filtered

        return self.events[-limit:] if limit else self.events

    def analyze_event_flow(self) -> list[dict]:
        """
        Analyze event flow for anomalies or bottlenecks.

        Returns:
            List of analysis results
        """
        if len(self.events) < 2:
            return []

        analysis = []
        prev_event = self.events[0]

        for i, event in enumerate(self.events[1:], 1):
            time_diff = (event["timestamp"] - prev_event["timestamp"]).total_seconds()

            # Identify slow transitions (more than 5 seconds)
            if time_diff > 5:
                analysis.append(
                    {
                        "type": "slow_transition",
                        "from_event": prev_event["event_type"],
                        "to_event": event["event_type"],
                        "duration_seconds": time_diff,
                    }
                )

            prev_event = event

        return analysis
