"""
TestCase implementation - now uses refactored modular components.

This file maintains backward compatibility while delegating to the new refactored implementation.
The original implementation has been backed up to backup_originals/test_case_impl_original.py
"""

# Import the refactored implementation
from panther.core.test_cases.test_case_impl_refactored import (
    TestCaseImplRefactored as TestCaseImpl,
)

# Export the main class for backward compatibility
__all__ = ["TestCaseImpl"]

# For any code that imports specific classes, provide aliases
TestCase = TestCaseImpl  # Alternative name that might be used
