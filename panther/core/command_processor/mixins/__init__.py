"""Command processing mixins.

Cross-cutting concerns composed into service managers and execution
environments via multiple inheritance:

- ``CommandEventMixin``        -- emits command-generation and Docker-build
  events through the service emitter.
"""

from panther.core.command_processor.mixins.event_mixin import CommandEventMixin

__all__ = [
    "CommandEventMixin",
]
