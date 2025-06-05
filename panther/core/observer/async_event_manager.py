import logging
import threading
import queue
import concurrent.futures
import time
from collections import defaultdict
from typing import Any, NamedTuple
from concurrent.futures import Future

from panther.core.observer.events import Event
from panther.core.observer.core.observer_interface import IObserver


class PrioritizedEvent(NamedTuple):
    """Prioritized event entry for the event queue."""

    priority: int  # Higher numbers = higher priority
    timestamp: float  # Used as tiebreaker for same priority events
    sequence: int  # Used as tiebreaker for same timestamp events
    event: Event  # The actual event
    future: Future  # Future for tracking completion


class BufferingStrategy:
    """Base class for event buffering strategies."""

    def __init__(self):
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    def should_buffer(self, event: Event) -> bool:
        """Determine if an event should be buffered."""
        return False

    def get_buffer_key(self, event: Event) -> Any:
        """Get a key for buffering/grouping."""
        return event.get_type()

    def process_buffer(self, buffer: list[Event]) -> list[Event]:
        """Process a buffer of events, potentially consolidating them."""
        return buffer


class DefaultBufferingStrategy(BufferingStrategy):
    """Default strategy that doesn't do any buffering."""

    pass


class TypeBasedBufferingStrategy(BufferingStrategy):
    """Buffer and consolidate events by type."""

    def __init__(
        self, buffer_types: list[str], max_buffer_size: int = 100, max_buffer_time: float = 1.0
    ):
        super().__init__()
        self.buffer_types = buffer_types
        self.max_buffer_size = max_buffer_size
        self.max_buffer_time = max_buffer_time
        self.buffer_timestamps: dict[str, float] = {}

    def should_buffer(self, event: Event) -> bool:
        """Check if this event type should be buffered."""
        event_type = event.get_type()
        return any(event_type.startswith(t) for t in self.buffer_types)

    def get_buffer_key(self, event: Event) -> str:
        """Use event type as buffer key."""
        return event.get_type()

    def process_buffer(self, buffer: list[Event]) -> list[Event]:
        """
        Process buffered events, keeping only the most recent per type.
        """
        if not buffer:
            return []

        # For simplicity, just keep the most recent event of each exact type
        by_type = {}
        for event in buffer:
            by_type[event.get_type()] = event

        return list(by_type.values())


class AggregatingBufferingStrategy(BufferingStrategy):
    """
    Buffer events and aggregate their values where possible.
    This strategy is useful for metrics and other data that can be meaningfully combined.
    """

    def __init__(
        self,
        buffer_types: list[str],
        aggregate_fields: list[str],
        max_buffer_size: int = 50,
        max_buffer_time: float = 2.0,
    ):
        """
        Initialize an aggregating buffer strategy.

        Args:
            buffer_types: List of event types to buffer
            aggregate_fields: List of data fields to aggregate (must be numeric)
            max_buffer_size: Maximum number of events in a buffer
            max_buffer_time: Maximum time to buffer before processing (in seconds)
        """
        super().__init__()
        self.buffer_types = buffer_types
        self.aggregate_fields = aggregate_fields
        self.max_buffer_size = max_buffer_size
        self.max_buffer_time = max_buffer_time
        self.buffer_timestamps: dict[str, float] = {}

    def should_buffer(self, event: Event) -> bool:
        """Check if this event type should be buffered."""
        event_type = event.get_type()
        # Check if event has at least one of the fields we can aggregate
        has_aggregatable_field = any(field in event.data for field in self.aggregate_fields)
        return has_aggregatable_field and any(event_type.startswith(t) for t in self.buffer_types)

    def get_buffer_key(self, event: Event) -> str:
        """Group by event type and any grouping keys in the data."""
        event_type = event.get_type()
        # Optional: Extract grouping fields from event data
        group_key = event.data.get("group", "")
        return f"{event_type}:{group_key}"

    def process_buffer(self, buffer: list[Event]) -> list[Event]:
        """
        Aggregate numeric fields across buffered events.
        """
        if not buffer:
            return []

        # Group by specific event type
        event_groups = {}
        for event in buffer:
            key = event.get_type()
            if key not in event_groups:
                event_groups[key] = []
            event_groups[key].append(event)

        result_events = []

        # Process each group separately
        for event_type, events in event_groups.items():
            if len(events) == 1:
                # No aggregation needed for a single event
                result_events.append(events[0])
                continue

            # Start with first event as template
            template = events[0]
            aggregated_data = template.data.copy()

            # Count of events aggregated
            aggregated_data["aggregated_count"] = len(events)

            # Aggregate numeric fields
            for field in self.aggregate_fields:
                values = [e.data.get(field, 0) for e in events if field in e.data]
                if values:
                    aggregated_data[field] = sum(values)
                    aggregated_data[f"{field}_avg"] = sum(values) / len(values)
                    aggregated_data[f"{field}_min"] = min(values)
                    aggregated_data[f"{field}_max"] = max(values)

            # Create new aggregated event
            # Use the same class as the template event if possible
            if hasattr(template, "__class__"):
                event_class = template.__class__
                if hasattr(event_class, "__new__") and callable(event_class.__new__):
                    try:
                        result = event_class(name=event_type, data=aggregated_data)
                        result_events.append(result)
                        continue
                    except Exception:
                        # Fall back to creating a generic Event
                        pass

            # Create generic Event
            from panther.core.observer.events import Event as GenericEvent

            result = GenericEvent(event_type, aggregated_data)
            result_events.append(result)

        return result_events


class TimeWindowBufferingStrategy(BufferingStrategy):
    """Buffer events based on time windows."""

    def __init__(self, buffer_types: list[str], window_size: float = 1.0):
        """
        Initialize a time window buffering strategy.

        Args:
            buffer_types: List of event types to buffer
            window_size: Time window size in seconds
        """
        super().__init__()
        self.buffer_types = buffer_types
        self.window_size = window_size
        self.current_window_start = time.time()

    def should_buffer(self, event: Event) -> bool:
        """Check if this event type should be buffered."""
        event_type = event.get_type()
        return any(event_type.startswith(t) for t in self.buffer_types)

    def get_buffer_key(self, event: Event) -> Any:
        """Group by time window."""
        current_time = time.time()
        # If we've exceeded the window, start a new one
        if current_time - self.current_window_start > self.window_size:
            self.current_window_start = current_time

        return f"window_{self.current_window_start}"

    def process_buffer(self, buffer: list[Event]) -> list[Event]:
        """
        Process all events in the buffer as a batch.
        This strategy doesn't consolidate/reduce events.
        """
        return buffer


class AsyncEventManager:
    """
    Event manager with asynchronous processing capabilities.

    This event manager processes events asynchronously in a separate thread pool,
    allowing event producers to continue without waiting for all observers to complete.
    It supports event prioritization, buffering strategies, and enhanced error handling.
    """

    def __init__(
        self,
        max_workers: int = 5,
        queue_size: int = 100,
        buffering_strategy: BufferingStrategy = None,
    ):
        """
        Initialize a new AsyncEventManager.

        Args:
            max_workers: Maximum number of worker threads for processing events
            queue_size: Maximum number of events that can be queued
            buffering_strategy: Strategy for buffering/consolidating events
        """
        self.logger = logging.getLogger("AsyncEventManager")
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

        # Event queue is now a priority queue
        self.event_queue = queue.PriorityQueue(maxsize=queue_size)
        self.processing = False
        self.observers: dict[str, list[IObserver]] = defaultdict(list)
        self.global_observers: list[IObserver] = []
        self.metrics = {
            "processed": 0,
            "errors": 0,
            "queue_high_water": 0,
            "retry_count": 0,
            "buffered_count": 0,
            "by_type": {},
            "by_priority": defaultdict(int),
            "processing_time": {},
        }

        # Buffering
        self.buffering_strategy = buffering_strategy or DefaultBufferingStrategy()
        self.event_buffers: dict[Any, list[tuple[Event, Future]]] = defaultdict(list)

        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds

        # State
        self._lock = threading.RLock()
        self._buffer_lock = threading.RLock()
        self._shutdown = False
        self._sequence_counter = 0

        # Start the processing threads
        self.processing_thread = threading.Thread(target=self._process_event_queue, daemon=True)
        self.processing_thread.start()

        self.buffer_thread = threading.Thread(target=self._process_buffers, daemon=True)
        self.buffer_thread.start()

    def register_observer(self, observer: IObserver, event_types: list[str] = None):
        """
        Register an observer for specific event types.

        Args:
            observer: The observer instance to register
            event_types: List of event types to subscribe to, or None for all events
        """
        with self._lock:
            if not event_types:
                self.global_observers.append(observer)
                self.logger.debug(
                    f"Registered observer '{observer.__class__.__name__}' as global observer"
                )
            else:
                for event_type in event_types:
                    self.observers[event_type].append(observer)
                    self.logger.debug(
                        f"Registered observer '{observer.__class__.__name__}' for event type '{event_type}'"
                    )

    def unregister_observer(self, observer: IObserver, event_types: list[str] = None):
        """
        Unregister an observer from specific or all event types.

        Args:
            observer: The observer instance to unregister
            event_types: List of event types to unsubscribe from, or None for all
        """
        with self._lock:
            if not event_types:
                try:
                    self.global_observers.remove(observer)
                    self.logger.debug(
                        f"Unregistered observer '{observer.__class__.__name__}' from global observers"
                    )
                except ValueError:
                    pass

                for event_type in list(self.observers.keys()):
                    try:
                        self.observers[event_type].remove(observer)
                        self.logger.debug(
                            f"Unregistered observer '{observer.__class__.__name__}' from event type '{event_type}'"
                        )
                    except ValueError:
                        pass
            else:
                for event_type in event_types:
                    try:
                        self.observers[event_type].remove(observer)
                        self.logger.debug(
                            f"Unregistered observer '{observer.__class__.__name__}' from event type '{event_type}'"
                        )
                    except ValueError:
                        pass

    def notify(self, event: Event, priority: int = 0) -> Future:
        """
        Queue an event for asynchronous processing.

        Args:
            event: The event to process
            priority: Event priority (higher values = higher priority)

        Returns:
            Future: Future representing the eventual completion

        Raises:
            queue.Full: If the event queue is full
            RuntimeError: If the event manager is shutdown
        """
        if self._shutdown:
            raise RuntimeError("AsyncEventManager is shutdown")

        future = concurrent.futures.Future()

        # Check if this event should be buffered
        if self.buffering_strategy.should_buffer(event):
            with self._buffer_lock:
                buffer_key = self.buffering_strategy.get_buffer_key(event)
                self.event_buffers[buffer_key].append((event, future))

                # Mark first event timestamp if buffer is new
                if buffer_key not in self.buffering_strategy.buffer_timestamps:
                    self.buffering_strategy.buffer_timestamps[buffer_key] = time.time()

                self.metrics["buffered_count"] += 1
                self.logger.debug("Buffered event %r of type %s", event, event.get_type())

                # Process buffer immediately if it reaches max size
                if len(self.event_buffers[buffer_key]) >= self.buffering_strategy.max_buffer_size:
                    self._flush_buffer(buffer_key)

            return future

        # Use atomic increment for sequence counter
        with self._lock:
            sequence = self._sequence_counter
            self._sequence_counter += 1

        try:
            # Create prioritized event entry
            prioritized = PrioritizedEvent(
                priority=priority,
                timestamp=time.time(),
                sequence=sequence,
                event=event,
                future=future,
            )

            self.event_queue.put(prioritized, block=False)

            # Update metrics
            queue_size = self.event_queue.qsize()
            if queue_size > self.metrics["queue_high_water"]:
                self.metrics["queue_high_water"] = queue_size

            with self._lock:
                self.metrics["by_priority"][priority] += 1

            self.logger.debug(
                "Queued event %r for async processing with priority %d", event, priority
            )

        except queue.Full:
            self.logger.error("Event queue full, dropping event %r", event.get_type())
            future.set_exception(queue.Full("Event queue is full"))

        return future

    def _process_event_queue(self):
        """Process events from the queue until shutdown."""
        self.logger.info("Async event processing thread started")

        while not self._shutdown:
            try:
                # Block with timeout to periodically check for shutdown
                prioritized_event = self.event_queue.get(timeout=1.0)
                event = prioritized_event.event
                future = prioritized_event.future

                start_time = time.time()
                try:
                    self._notify_observers(event)
                    future.set_result(True)
                    self.logger.debug("Processed event of type %s", event.get_type())

                    # Update metrics
                    with self._lock:
                        self.metrics["processed"] += 1
                        event_type = event.get_type()
                        self.metrics["by_type"][event_type] = (
                            self.metrics["by_type"].get(event_type, 0) + 1
                        )

                        # Track processing time
                        processing_time = time.time() - start_time
                        if event_type in self.metrics["processing_time"]:
                            old_count, old_avg = self.metrics["processing_time"][event_type]
                            new_avg = (old_avg * old_count + processing_time) / (old_count + 1)
                            self.metrics["processing_time"][event_type] = (old_count + 1, new_avg)
                        else:
                            self.metrics["processing_time"][event_type] = (1, processing_time)

                except Exception as e:
                    self.logger.error("Error processing event of type %s: %s", event.get_type(), e)

                    # Implement retry mechanism for failed events
                    retry_count = getattr(event, "_retry_count", 0)
                    if retry_count < self.max_retries:
                        # Increment retry count and requeue with reduced priority
                        setattr(event, "_retry_count", retry_count + 1)
                        self.metrics["retry_count"] += 1

                        # Requeue with reduced priority (ensure it's still positive)
                        retry_priority = max(0, prioritized_event.priority - 1)
                        self.logger.warning(
                            "Retrying event of type %s (attempt %d/%d)",
                            event.get_type(),
                            retry_count + 1,
                            self.max_retries,
                        )

                        # Create a new future for the retry
                        retry_future = concurrent.futures.Future()

                        # Use a new sequence number for the retry
                        with self._lock:
                            sequence = self._sequence_counter
                            self._sequence_counter += 1

                        # Add delay before retrying based on retry count
                        retry_delay = self.retry_delay * (2**retry_count)
                        timer = threading.Timer(
                            retry_delay,
                            lambda: self.event_queue.put(
                                PrioritizedEvent(
                                    priority=retry_priority,
                                    timestamp=time.time(),
                                    sequence=sequence,
                                    event=event,
                                    future=retry_future,
                                )
                            ),
                        )
                        timer.daemon = True
                        timer.start()

                        # Chain the original future to the retry future
                        retry_future.add_done_callback(
                            lambda f: (
                                future.set_result(f.result())
                                if f.exception() is None
                                else future.set_exception(f.exception())
                            )
                        )
                    else:
                        # Max retries reached, fail the future
                        self.logger.error(
                            "Max retries (%d) reached for event of type %s",
                            self.max_retries,
                            event.get_type(),
                        )
                        future.set_exception(e)
                        with self._lock:
                            self.metrics["errors"] += 1
                finally:
                    self.event_queue.task_done()

            except queue.Empty:
                # Timeout occurred, just loop and check shutdown flag
                pass

        self.logger.info("Async event processing thread stopped")

    def _process_buffers(self):
        """Process event buffers periodically."""
        self.logger.info("Buffer processing thread started")

        while not self._shutdown:
            try:
                # Sleep for a short interval
                time.sleep(0.1)

                # Check for buffers that need processing
                now = time.time()
                flush_keys = []

                with self._buffer_lock:
                    # Find buffers that have reached their time limit
                    for key, timestamp in self.buffering_strategy.buffer_timestamps.items():
                        if (
                            now - timestamp >= self.buffering_strategy.max_buffer_time
                            and key in self.event_buffers
                        ):
                            flush_keys.append(key)

                # Process each buffer that needs flushing
                for key in flush_keys:
                    self._flush_buffer(key)

            except Exception as e:
                self.logger.error("Error in buffer processing: %s", e)

        self.logger.info("Buffer processing thread stopped")

    def _flush_buffer(self, buffer_key: Any):
        """
        Process and flush a specific event buffer.

        Args:
            buffer_key: Key of the buffer to flush
        """
        with self._buffer_lock:
            if buffer_key not in self.event_buffers:
                return

            # Get all events and futures from this buffer
            buffer_entries = self.event_buffers.pop(buffer_key)
            if not buffer_entries:
                return

            # Remove the timestamp
            self.buffering_strategy.buffer_timestamps.pop(buffer_key, None)

        # Extract events and futures
        events = [e for e, _ in buffer_entries]
        futures = [f for _, f in buffer_entries]

        # Process the buffer to potentially consolidate events
        processed_events = self.buffering_strategy.process_buffer(events)

        self.logger.debug(
            "Flushing buffer %s: consolidated %d events into %d",
            buffer_key,
            len(events),
            len(processed_events),
        )

        # Submit each processed event
        processed_futures = []
        for event in processed_events:
            # Use elevated priority for buffered events to ensure they're
            # processed promptly after the buffering delay
            processed_future = self.notify(event, priority=5)
            processed_futures.append(processed_future)

        # Setup callback to resolve all original futures when processed events complete
        def on_all_complete(_):
            exceptions = []
            for f in processed_futures:
                try:
                    f.result()  # Will raise exception if the future failed
                except Exception as e:
                    exceptions.append(e)

            # If any processed event failed, fail all futures with the first exception
            if exceptions:
                for f in futures:
                    if not f.done():
                        f.set_exception(exceptions[0])
            else:
                # All succeeded, resolve all futures
                for f in futures:
                    if not f.done():
                        f.set_result(True)

        # Create a future that completes when all processed events complete
        combined = concurrent.futures.wait(
            processed_futures, return_when=concurrent.futures.ALL_COMPLETED
        )

        # Add the callback to the combined future
        concurrent.futures.Future().add_done_callback(on_all_complete)

    def _notify_observers(self, event: Event):
        """
        Notify all matching observers about an event.

        Args:
            event: The event to notify observers about
        """
        event_type = event.get_type()
        matching_observers = []

        with self._lock:
            # Specific observers for this event type
            matching_observers.extend(self.observers.get(event_type, []))

            # Hierarchical matching for dot-separated event types
            parts = event_type.split(".")
            for i in range(1, len(parts)):
                parent_type = ".".join(parts[:-i])
                matching_observers.extend(self.observers.get(parent_type, []))

            # Add global observers
            matching_observers.extend(self.global_observers)

            # Remove duplicates (preserves order)
            seen = set()
            matching_observers = [o for o in matching_observers if not (o in seen or seen.add(o))]

        # Sort observers by priority (if they have it)
        prioritized = []
        for observer in matching_observers:
            priority = 0
            if isinstance(observer, IObserver) and hasattr(observer, "get_priority"):
                priority = observer.get_priority()
            prioritized.append((priority, observer))

        # Sort by priority (highest first)
        prioritized.sort(key=lambda x: x[0], reverse=True)

        # Notify each observer sequentially
        for _, observer in prioritized:
            if (
                isinstance(observer, IObserver)
                and hasattr(observer, "is_interested")
                and not observer.is_interested(event_type)
            ):
                continue

            try:
                observer.on_event(event)
            except Exception as e:
                self.logger.error("Error in observer '%s': %s", observer.__class__.__name__, e)

    def shutdown(self, wait: bool = True):
        """
        Shutdown the async event manager.

        Args:
            wait: If True, wait for the queue to be processed before returning
        """
        self.logger.info("Shutting down AsyncEventManager")
        self._shutdown = True

        if wait:
            try:
                self.event_queue.join()
            except Exception:
                pass

        self.executor.shutdown(wait=wait)

        if self.processing_thread.is_alive() and wait:
            self.processing_thread.join(timeout=5.0)

        self.logger.info("AsyncEventManager shutdown complete")

    def get_metrics(self) -> dict[str, Any]:
        """
        Get event processing metrics.

        Returns:
            dict: Event processing metrics
        """
        with self._lock:
            return self.metrics.copy()

    def get_queue_size(self) -> int:
        """
        Get the current size of the event queue.

        Returns:
            int: Current queue size
        """
        return self.event_queue.qsize()

    def is_queue_full(self) -> bool:
        """
        Check if the event queue is full.

        Returns:
            bool: True if the queue is full
        """
        return self.event_queue.full()

    def wait_for_empty_queue(self, timeout: float | None = None) -> bool:
        """
        Wait until the event queue is empty.

        Args:
            timeout: Maximum time to wait in seconds, or None to wait indefinitely

        Returns:
            bool: True if the queue became empty, False if timeout occurred
        """
        try:
            self.event_queue.join()
            return True
        except Exception:
            return False
