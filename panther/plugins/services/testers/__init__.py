"""Tester service plugins for protocol verification.

Contains validation and formal-verification tools:

- **panther_ivy** -- Ivy-based formal verification of protocol
  implementations (installed as a git submodule).

Tester plugins register via ``@register_plugin()`` and implement
the ``IServiceManager`` interface.

Creating a New Tester Plugin:
    Directory structure::

        plugins/services/testers/your_tester/
        +-- __init__.py
        +-- plugin.py           # Inherits from IServiceManager
        +-- config_schema.py    # Pydantic configuration schema

    Key methods to implement:
        - ``initialize()`` -- setup with configuration
        - ``execute()`` -- run verification/testing logic
        - ``get_test_results()`` -- return structured pass/fail results
        - ``cleanup()`` -- release resources

    Best practices: provide detailed pass/fail results, ensure
    reproducibility, minimize IUT-specific dependencies, handle
    timeouts gracefully.

    Reference implementation: ``panther_ivy/``.
"""
