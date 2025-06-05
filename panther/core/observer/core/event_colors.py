"""
Event color coding system for enhanced visual feedback in PANTHER framework.

This module provides color codes for different event types to improve
readability and user experience in console and log outputs.
"""

import sys
import os

# Map PANTHER event types to colorlog colors
EVENT_LOG_COLORS = {
    "error": "bold_red",
    "fail": "bold_red",
    "warning": "bold_yellow",
    "pass": "bold_green",
    "success": "bold_green",
    "start": "cyan",
    "stop": "blue",
    "end": "blue",
    "security": "bold_yellow",
    "performance": "yellow",
    "network": "magenta",
    "data": "cyan",
    "debug": "white",
    "info": "green",
    "system": "cyan",
    "test": "blue",
    "custom": "magenta",
    "user": "green",
    "config": "blue",
}


def get_severity_indicator(event_type: str) -> str:
    """
    Get a visual severity indicator for an event type.
    Use standard ASCII characters for better compatibility.

    Args:
        event_type: Type of the event

    Returns:
        str: Severity indicator symbol
    """
    # Use standardized ASCII symbols instead of Unicode for better compatibility
    if "error" in event_type.lower() or "fail" in event_type.lower():
        return "[ERROR]"
    elif "warning" in event_type.lower():
        return "[WARN]"
    elif "pass" in event_type.lower() or "success" in event_type.lower():
        return "[OK]"
    elif "start" in event_type.lower():
        return "[START]"
    elif "stop" in event_type.lower() or "end" in event_type.lower():
        return "[END]"
    elif "security" in event_type.lower():
        return "[SECURITY]"
    elif "performance" in event_type.lower():
        return "[PERF]"
    elif "network" in event_type.lower():
        return "[NET]"
    elif "data" in event_type.lower():
        return "[DATA]"
    else:
        return "[EVENT]"


def is_terminal_capable() -> bool:
    """
    Check if the current terminal supports color output.

    Returns:
        bool: True if terminal supports colors, False otherwise
    """
    # Check if we're in a terminal
    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        return False

    # Check environment variables
    if os.environ.get("NO_COLOR"):
        return False

    if os.environ.get("FORCE_COLOR"):
        return True

    # Check TERM environment variable
    term = os.environ.get("TERM", "")
    if term in ["dumb", "unknown"]:
        return False

    return True
