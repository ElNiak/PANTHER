"""Unit tests for EventManager singleton pattern."""

import threading
from panther.core.observer.management.event_manager import EventManager


class TestEventManagerSingleton:
    """Test EventManager singleton behavior."""

    def test_singleton_instance(self):
        """Test that EventManager returns the same instance."""
        instance1 = EventManager.get_instance()
        instance2 = EventManager.get_instance()

        assert instance1 is instance2
        assert id(instance1) == id(instance2)

    def test_direct_instantiation_returns_singleton(self):
        """Test that direct instantiation also returns the singleton."""
        instance1 = EventManager.get_instance()
        instance2 = EventManager()

        assert instance1 is instance2

    def test_singleton_thread_safety(self):
        """Test that singleton is thread-safe."""
        instances = []

        def create_instance():
            instances.append(EventManager.get_instance())

        threads = []
        for _ in range(10):
            thread = threading.Thread(target=create_instance)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All instances should be the same
        first_instance = instances[0]
        for instance in instances[1:]:
            assert instance is first_instance

    def test_reset_instance(self):
        """Test that reset_instance properly resets the singleton."""
        # Get initial instance
        instance1 = EventManager.get_instance()

        # Reset the singleton
        EventManager.reset_instance()

        # Get new instance
        instance2 = EventManager.get_instance()

        # They should be different objects
        assert instance1 is not instance2

        # But subsequent calls should return the same new instance
        instance3 = EventManager.get_instance()
        assert instance2 is instance3

    def test_singleton_maintains_state(self):
        """Test that singleton maintains state across calls."""
        # Reset to ensure clean state
        EventManager.reset_instance()

        manager = EventManager.get_instance()

        # Add some test data
        test_key = "test_metric"
        manager.metrics[test_key] = 42

        # Get instance again
        manager2 = EventManager.get_instance()

        # Should have the same data
        assert manager2.metrics[test_key] == 42
