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


def __getattr__(name):  # pylint: disable=invalid-name
    """Lazy import implementation to avoid circular imports."""
    if name == "experiment_manager":
        from . import experiment_manager  # pylint: disable=import-outside-toplevel

        return experiment_manager
    elif name == "experiment_strategy":
        from . import experiment_strategy  # pylint: disable=import-outside-toplevel

        return experiment_strategy
    elif name == "observer":
        from . import observer  # pylint: disable=import-outside-toplevel

        return observer
    elif name == "results":
        from . import results  # pylint: disable=import-outside-toplevel

        return results
    elif name == "test_cases":
        from . import test_cases  # pylint: disable=import-outside-toplevel

        return test_cases
    elif name == "utils":
        from . import utils  # pylint: disable=import-outside-toplevel

        return utils
    elif name == "exceptions":
        from . import exceptions  # pylint: disable=import-outside-toplevel

        return exceptions
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
