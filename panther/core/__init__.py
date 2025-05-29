"""PANTHER core package.

This package contains the core functionality of the PANTHER framework.
"""

# Define the public API - but use lazy imports to avoid circular dependencies
__all__ = [
    "experiment_manager",
    "experiment_strategy",
    "observer",
    "results",
    "test_cases",
    "utils",
    "exceptions",
]


def __getattr__(name):
    """Lazy import implementation to avoid circular imports."""
    if name == "experiment_manager":
        from . import experiment_manager

        return experiment_manager
    elif name == "experiment_strategy":
        from . import experiment_strategy

        return experiment_strategy
    elif name == "observer":
        from . import observer

        return observer
    elif name == "results":
        from . import results

        return results
    elif name == "test_cases":
        from . import test_cases

        return test_cases
    elif name == "utils":
        from . import utils

        return utils
    elif name == "exceptions":
        from . import exceptions

        return exceptions
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
