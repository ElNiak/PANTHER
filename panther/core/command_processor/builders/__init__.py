"""Command builder functionality.

Provides the builder pattern for fluent, injection-safe command construction:

- ``CommandBuilder``        -- base builder for argument/env accumulation.
- ``ServiceCommandBuilder`` -- protocol-testing extension with certificate,
  network, role, and logging parameter helpers.
"""

from panther.core.command_processor.builders.base_builder import CommandBuilder
from panther.core.command_processor.builders.service_builder import (
    ServiceCommandBuilder,
)

__all__ = [
    "CommandBuilder",
    "ServiceCommandBuilder",
]
