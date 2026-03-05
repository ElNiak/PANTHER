"""Service plugins for protocol implementations and verification tools.

Provides the service manager abstraction used by all IUT (Implementation
Under Test) and tester plugins.  Each service manager controls command
generation, Docker builds, lifecycle events, and structured logging for
a single implementation.

Service Hierarchy::

    IServiceManager                      ← abstract contract
    └── BaseQUICServiceManager           ← template method pattern
        ├── PythonQUICServiceManager     ← venv / asyncio (aioquic)
        ├── RustQUICServiceManager       ← Cargo builds   (quiche, quinn)
        └── direct subclasses            ← C / Go          (picoquic, lsquic, …)

Service Types:
    IUT
        Protocol implementations to evaluate.  Organised by protocol
        (``quic/``, ``http/``, ``minip/``).

    Testers
        Validation and formal-verification tools.
        Currently: **panther_ivy** (Ivy-based formal verification).

Interface Contract:
    Every service manager implements ``initialize(config)``,
    ``start()``, ``stop()``, and ``get_status()``.

See Also:
    :mod:`panther.plugins.services.services_interface`
        ``IServiceManager`` abstract base.
    :mod:`panther.plugins.services.service_manager_mixin`
        Shared validation helpers re-exported below.
"""

from panther.plugins.services.service_manager_mixin import (
    validate_cmd,
    validate_structure,
)
from panther.plugins.services.services_interface import (
    IServiceManager,
    quote_shell,
    quote_yaml,
)

__all__ = [
    "IServiceManager",
    "quote_shell",
    "quote_yaml",
    "validate_cmd",
    "validate_structure",
]
