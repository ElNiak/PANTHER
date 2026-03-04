"""Command processing mixins.

Cross-cutting concerns composed into service managers and execution
environments via multiple inheritance:

- ``CommandEventMixin``        -- emits command-generation and Docker-build
  events through the service emitter.
- ``CommandModificationMixin`` -- applies pre/post-run command modifications
  and environment-variable injection with event emission and state tracking.
"""

from panther.core.command_processor.mixins.event_mixin import CommandEventMixin
from panther.core.command_processor.mixins.modification_mixin import (
    CommandModificationMixin,
)

__all__ = [
    "CommandModificationMixin",
    "CommandEventMixin",
]
