"""
Integration script for the new event-driven plugin architecture.
"""

import argparse
import logging
import os
import sys
import traceback
from pathlib import Path
import subprocess

# Add parent directory to sys.path
parent_dir = Path(__file__).parent.parent.absolute()
sys.path.append(str(parent_dir))

from panther.core.debug_tools import DebugTools


def setup_logging():
    """
    Set up basic logging.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )


class EventFlowVisualizer:
    """
    Tool to visualize event flow for debugging.
    """

    def __init__(self, events_log_path):
        """
        Initialize with path to event log.
        """
        self.events_log_path = events_log_path
        self.logger = logging.getLogger("EventFlowVisualizer")
        self.events = []

    def parse_events(self):
        """
        Parse events from log file.

        Returns:
            List of event dictionaries
        """
        try:
            self.events = []
            with open(self.events_log_path) as f:
                for line in f:
                    try:
                        if " EVENT - " in line:
                            # Extract timestamp and event info
                            parts = line.split(" EVENT - ", 1)
                            if len(parts) == 2:
                                timestamp_str = parts[0].strip()
                                event_info = parts[1].strip()

                                # Parse timestamp
                                try:
                                    from datetime import datetime

                                    timestamp = datetime.strptime(
                                        timestamp_str, "%Y-%m-%d %H:%M:%S,%f"
                                    )
                                except ValueError:
                                    timestamp = timestamp_str

                                # Parse event type and data
                                if ": " in event_info:
                                    event_parts = event_info.split(": ", 1)
                                    event_type = event_parts[0]
                                    event_data = event_parts[1]

                                    # Try to parse JSON data
                                    try:
                                        import json

                                        data = json.loads(event_data)
                                    except (json.JSONDecodeError, ImportError):
                                        data = {"raw": event_data}

                                    self.events.append(
                                        {
                                            "timestamp": timestamp,
                                            "event_type": event_type,
                                            "data": data,
                                        }
                                    )
                    except Exception as e:
                        self.logger.warning(f"Failed to parse event line: {line}. Error: {e}")

            self.logger.info(f"Parsed {len(self.events)} events from log")
            return self.events
        except Exception as e:
            self.logger.error(f"Failed to parse events log: {e}")
            return []

    def generate_mermaid_diagram(self, output_path):
        """
        Generate a Mermaid.js diagram of event flow.

        Args:
            output_path: Path to write the diagram file

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.events:
            self.parse_events()

        if not self.events:
            self.logger.warning("No events to visualize")
            return False

        try:
            mermaid = ["sequenceDiagram", "    title Event Flow Diagram"]

            # Create a set of participants
            participants = set()
            for event in self.events:
                event_type = (
                    event["event_type"].split(".", 1)[0]
                    if "." in event["event_type"]
                    else event["event_type"]
                )
                if "test_name" in event["data"]:
                    participants.add(f"Test_{event['data']['test_name']}")
                if "service_name" in event["data"]:
                    participants.add(f"Service_{event['data']['service_name']}")
                if "environment_type" in event["data"]:
                    participants.add(f"Env_{event['data']['environment_type']}")
                participants.add(event_type)

            # Add participants in a logical order
            for participant in sorted(participants):
                mermaid.append(f"    participant {participant}")

            # Add events as interactions
            for i, event in enumerate(self.events):
                source = (
                    event["event_type"].split(".", 1)[0]
                    if "." in event["event_type"]
                    else event["event_type"]
                )
                event_name = (
                    event["event_type"].split(".", 1)[1] if "." in event["event_type"] else "event"
                )

                # Determine target based on data
                target = source
                if "test_name" in event["data"]:
                    target = f"Test_{event['data']['test_name']}"
                elif "service_name" in event["data"]:
                    target = f"Service_{event['data']['service_name']}"
                elif "environment_type" in event["data"]:
                    target = f"Env_{event['data']['environment_type']}"

                # Don't show self-messages
                if source != target:
                    mermaid.append(f"    {source}->>{target}: {event_name}")
                    # Add notes for errors
                    if "error" in event["data"] or (
                        "success" in event["data"] and not event["data"]["success"]
                    ):
                        error_msg = event["data"].get("error", "Failed")
                        mermaid.append(f"    Note over {target}: {error_msg}")

            # Write diagram to file
            with open(output_path, "w") as f:
                f.write("\n".join(mermaid))

            self.logger.info(f"Generated Mermaid diagram at {output_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to generate Mermaid diagram: {e}")
            return False


def run_minimal_test(config_path: str, output_dir: str, verbose: bool = False) -> bool:
    """
    Run a minimal test using the new architecture.

    Args:
        config_path: Path to experiment config
        output_dir: Directory for output files
        verbose: Whether to enable verbose logging

    Returns:
        bool: True if successful, False otherwise
    """
    logger = logging.getLogger("IntegrationTest")
    logger.info(f"Running minimal test with config: {config_path}")

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
        logger.error(traceback.format_exc())
        return False


def analyze_debug_logs(log_dir: str) -> bool:
    """
    Analyze debug logs for issues.

    Args:
        log_dir: Directory containing debug logs

    Returns:
        bool: True if analysis succeeded, False otherwise
    """
    logger = logging.getLogger("LogAnalyzer")
    logger.info(f"Analyzing logs in {log_dir}")

    # Analyze error log
    error_log_path = os.path.join(log_dir, "debug_errors.log")
    if os.path.exists(error_log_path):
        with open(error_log_path) as f:
            errors = f.readlines()
            logger.info(f"Found {len(errors)} error log entries")
            if errors:
                logger.info("Sample errors:")
                for error in errors[:5]:
                    logger.info(f"  {error.strip()}")

    # Generate event flow diagram
    event_log_path = os.path.join(log_dir, "events.log")
    if os.path.exists(event_log_path):
        visualizer = EventFlowVisualizer(event_log_path)
        diagram_path = os.path.join(log_dir, "event_flow.mmd")
        if visualizer.generate_mermaid_diagram(diagram_path):
            logger.info(f"Generated event flow diagram at {diagram_path}")

    return True


def main():
    """
    Main integration function.
    """
    parser = argparse.ArgumentParser(description="Plugin Architecture Integration")
    parser.add_argument(
        "--config",
        default="experiment-config/experiment_config_example_minimal.yaml",
        help="Path to experiment config file",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/integration_test",
        help="Output directory for logs and artifacts",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    setup_logging()
    logger = logging.getLogger("Integration")

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Run test
    success = run_minimal_test(args.config, args.output_dir, args.verbose)

    # Analyze logs if verbose
    if args.verbose:
        analyze_debug_logs(os.path.join(args.output_dir, "debug_logs"))

    # Report results
    if success:
        logger.info("Integration test completed successfully!")
        return 0
    else:
        logger.error("Integration test failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
