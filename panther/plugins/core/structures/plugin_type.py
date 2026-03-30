"""Enumeration of plugin types supported by the PANTHER framework."""

from enum import Enum


class PluginType(Enum):
    """Enumeration of plugin types supported by PANTHER."""

    SERVICE = "service"
    NETWORK_ENVIRONMENT = "network_environment"
    EXECUTION_ENVIRONMENT = "execution_environment"
    TESTER = "tester"
    PROTOCOL = "protocol"
    OBSERVER = "observer"
    IUT = "iut"  # Implementation Under Test
