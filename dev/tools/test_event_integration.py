#!/usr/bin/env python3
"""
Test script for the event-driven plugin architecture integration.
This script validates that the PANTHER event system is working correctly
by running a test and analyzing the emitted events.
"""

import argparse
import logging
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# Add parent directory to sys.path
parent_dir = Path(__file__).parent.parent.absolute()
sys.path.append(str(parent_dir))

from panther.core.debug_tools import DebugTools
from panther.core.observer.events import Event
from panther.core.observer.management.event_manager import EventManager
from panther.core.observer.event_emitter import EventEmitter
from panther.plugins.services.testers.panther_ivy.panther_ivy import PantherIvyServiceManager


class EventCollectorObserver:
    """Observer that collects events for later analysis."""

    def __init__(self):
        self.collected_events = []
        self.logger = logging.getLogger("EventCollector")

    def on_event(self, event: Event):
        """Collect an event."""
        self.collected_events.append(event)
        self.logger.info(f"Collected event: {event.name}")

    def get_events(self):
        """Get collected events."""
        return self.collected_events

    def get_events_by_type(self, event_type: str):
        """Get events of a specific type."""
        return [e for e in self.collected_events if e.name.startswith(event_type)]


def setup_logging(level=logging.INFO):
    """Set up basic logging."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )


def run_test_with_events(config_path, output_dir, verbose=False):
    """Run a test with event monitoring enabled."""
    logger = logging.getLogger("EventIntegrationTest")
    logger.info(f"Running event integration test with config: {config_path}")

    # Set up debug logging if verbose
    if verbose:
        log_dir = DebugTools.setup_verbose_logging(output_dir)
        logger.info(f"Verbose logging enabled. Logs in {log_dir}")

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Build the command
    cmd = ["python", "-m", "panther", "--experiment-config", config_path, "--enable-metrics"]
    if verbose:
        cmd.append("--debug")

    logger.info(f"Executing: {' '.join(cmd)}")

    try:
        # Run the command
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        logger.info(f"Exit code: {result.returncode}")

        # Write output to files
        with open(os.path.join(output_dir, "stdout.log"), "w") as f:
            f.write(result.stdout)
        with open(os.path.join(output_dir, "stderr.log"), "w") as f:
            f.write(result.stderr)

        if result.returncode != 0:
            logger.error("Test failed!")
            logger.error(f"STDOUT: {result.stdout[:500]}...")
            logger.error(f"STDERR: {result.stderr[:500]}...")
            return False

        logger.info("Test succeeded!")
        return True
    except Exception as e:
        logger.error(f"Error running test: {e}")
        return False


def test_event_system_directly():
    """Test the event system directly without running a full experiment."""
    logger = logging.getLogger("DirectEventTest")
    logger.info("Testing event system directly")

    # Create event manager and observer
    event_manager = EventManager()
    collector = EventCollectorObserver()
    event_manager.register_observer(collector)

    # Create event emitter
    emitter = EventEmitter(event_manager)

    # Test various event types
    emitter.emit_test_started("test1", {"param": "value"})
    emitter.emit_environment_setup_started("docker", {"config": "test"})
    emitter.emit_service_started("service1", {"type": "test"})
    emitter.emit_step_progress("step1", 50.0, "Half done")
    emitter.emit_test_completed("test1", True, {"result": "passed"})

    # Get collected events
    events = collector.get_events()
    logger.info(f"Collected {len(events)} events")

    # Validate we got the expected events
    expected_event_types = [
        "test.started",
        "environment.setup_started",
        "service.started",
        "step.progress",
        "test.completed",
    ]

    success = True
    for expected_type in expected_event_types:
        matching_events = [e for e in events if e.name == expected_type]
        if matching_events:
            logger.info(f"✓ Found event of type: {expected_type}")
        else:
            logger.error(f"✗ Missing event of type: {expected_type}")
            success = False

    return success


def test_service_event_emission():
    """Test that service managers properly emit events."""
    logger = logging.getLogger("ServiceEventTest")
    logger.info("Testing service manager event emission")

    # Create event manager and observer
    event_manager = EventManager()
    collector = EventCollectorObserver()
    event_manager.register_observer(collector)
    emitter = EventEmitter(event_manager)

    # Try to instantiate a minimal PantherIvyServiceManager
    try:
        # Create a dummy service config - this won't actually run
        class DummyConfig:
            def __init__(self):
                self.name = "test"
                self.version = None

        class DummyProtocol:
            def __init__(self):
                self.name = "test"
                self.role = "client"

        # Create a service instance directly for testing
        service = PantherIvyServiceManager(
            service_config_to_test=DummyConfig(),
            service_type="testers",
            protocol=DummyProtocol(),
            implementation_name="test_implementation",
        )

        # Set the event emitter
        service.event_emitter = emitter

        # Test event emission
        service.notify_service_started({"test": True})
        service.notify_service_stopped(True, {"test": True})
        service.notify_service_error("test_error", "Test error message", {"test": True})

        # Get collected events
        events = collector.get_events()
        logger.info(f"Collected {len(events)} events")

        # Validate service events
        service_events = [e for e in events if e.name.startswith("service.")]
        if len(service_events) >= 2:  # We expect at least service_started and service_stopped
            logger.info(f"✓ Service manager emitted {len(service_events)} events")
            for evt in service_events:
                logger.info(f"  - {evt.name}")
            return True
        else:
            logger.error(f"✗ Service manager emitted only {len(service_events)} events")
            return False
    except Exception as e:
        logger.error(f"Error testing service event emission: {e}")
        return False


def analyze_event_logs(log_dir):
    """Analyze event logs for completeness and timing."""
    logger = logging.getLogger("EventAnalyzer")
    logger.info(f"Analyzing event logs in {log_dir}")

    # Expected event sequence for a successful test
    expected_events = ["test.started", "environment.setup", "service.started", "test.completed"]

    # Find event log files
    event_logs = []
    for root, _, files in os.walk(log_dir):
        for file in files:
            if "event" in file.lower() and file.endswith(".log"):
                event_logs.append(os.path.join(root, file))

    if not event_logs:
        logger.warning("No event log files found")
        return False

    found_events = []
    try:
        # Check all log files
        for log_file in event_logs:
            logger.info(f"Analyzing log file: {log_file}")
            with open(log_file) as f:
                for line in f:
                    for expected in expected_events:
                        if expected in line:
                            found_events.append(expected)
                            break

        # Check if we found all expected events
        missing_events = [e for e in expected_events if e not in found_events]
        if missing_events:
            logger.warning(f"Missing events: {missing_events}")
            return False
        else:
            logger.info("All expected events found!")
            return True

    except Exception as e:
        logger.error(f"Error analyzing events log: {e}")
        return False


def check_service_event_integration():
    """Check if service managers are properly integrating with the event system."""
    logger = logging.getLogger("ServiceEventChecker")

    result = test_service_event_emission()
    if result:
        logger.info("Service event integration check passed")
    else:
        logger.error("Service event integration check failed")

    return result


def main():
    """Main integration test function."""
    parser = argparse.ArgumentParser(description="Event Integration Testing")
    parser.add_argument(
        "--config",
        default="experiment-config/experiment_config_example_minimal.yaml",
        help="Path to experiment config file",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/event_integration_test",
        help="Output directory for logs and artifacts",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument(
        "--test",
        choices=["direct", "service", "full"],
        default="direct",
        help="Test mode: direct=test event system only, service=test service event integration, full=run complete test",
    )
    args = parser.parse_args()

    if args.verbose:
        setup_logging(level=logging.DEBUG)
    else:
        setup_logging()

    logger = logging.getLogger("Integration")

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    success = True
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = os.path.join(args.output_dir, timestamp)
    os.makedirs(output_dir, exist_ok=True)

    # Run the requested test
    if args.test == "direct":
        logger.info("Running direct event system test")
        if not test_event_system_directly():
            logger.error("Direct event system test failed")
            success = False

    elif args.test == "service":
        logger.info("Running service event integration test")
        if not check_service_event_integration():
            logger.error("Service event integration test failed")
            success = False

    elif args.test == "full":
        logger.info("Running full integration test with experiment")
        if not run_test_with_events(args.config, output_dir, args.verbose):
            logger.error("Integration test failed")
            success = False

        # Analyze logs if verbose
        if args.verbose and success:
            logger.info("Analyzing event logs...")
            if not analyze_event_logs(output_dir):
                logger.warning("Event analysis found issues, but test passed")

    # Report results
    if success:
        logger.info("Event integration test completed successfully!")
        return 0
    else:
        logger.error("Event integration test failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
