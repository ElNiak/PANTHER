"""PANTHER test cases package.

This package contains test case definitions and interfaces for the PANTHER framework.
"""

# Import key modules for easier access
from . import test_case_impl as test_case
from . import test_interface_impl as test_interface

# Define the public API
__all__ = ["test_case", "test_interface"]
