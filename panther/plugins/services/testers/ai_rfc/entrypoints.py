"""The commands this package exposes, declared once.

Both front doors read this: ``panther ai-rfc`` builds its subcommands from it,
and the conventions suite asserts its invariants across it. Modules are named
by dotted string rather than imported, so reading the registry costs nothing
and the eight argparse CLIs load only when one of them is invoked.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Protocol, cast

#: This package, as a dotted path. Derived rather than written so the registry
#: survives a relocation that the rest of the tree would not.
PACKAGE = __name__.rsplit(".", 1)[0]


class CommandModule(Protocol):
    """A module exposing the substrate's argv-in, exit-code-out contract."""

    def main(self, argv: list[str] | None = ...) -> int:
        """Run the command and return its exit code."""
        ...


@dataclass(frozen=True)
class EntryPoint:
    """One command, reachable through either front door.

    Attributes:
        verb: The token following ``panther ai-rfc``.
        prog: The sub-CLI's own ``argparse`` ``prog=``, which ``--version``
            prints. Deliberately not derived from ``verb``: the root validator
            answers to ``check`` but has always called itself ``ai_rfc``, and
            changing that would alter output the harness records.
        module: Dotted path of the ``cli`` module, not of its package — the
            ``__main__`` guard test derives that name by trimming one segment.
        summary: One line. Shown by ``--help`` and rendered into the generated
            CLI reference by ``mkdocs-click``, where it is the only description
            a reader gets, since the arguments forward untouched.
    """

    verb: str
    prog: str
    module: str
    summary: str

    def load(self) -> CommandModule:
        """Import the module this entry names.

        Returns:
            The command's module, which satisfies :class:`CommandModule`.
        """
        return cast(CommandModule, import_module(self.module))


ENTRY_POINTS: tuple[EntryPoint, ...] = (
    EntryPoint(
        "check",
        "ai_rfc",
        f"{PACKAGE}.cli",
        "Validate a manifest, adjudicate its claims and verify its anchors",
    ),
    EntryPoint(
        "coverage",
        "ai_rfc.coverage",
        f"{PACKAGE}.coverage.cli",
        "Propose runtime anchors from a coverage report",
    ),
    EntryPoint(
        "draft",
        "ai_rfc.draft",
        f"{PACKAGE}.draft.cli",
        "checkpoint, gate, completeness — freeze and gate a prose draft",
    ),
    EntryPoint(
        "forge",
        "ai_rfc.forge",
        f"{PACKAGE}.forge.cli",
        "fetch, adopt — pull and review evidence, with or without credentials",
    ),
    EntryPoint(
        "history",
        "ai_rfc.history",
        f"{PACKAGE}.history.cli",
        "Extract a commit corpus from a clone",
    ),
    EntryPoint(
        "pipeline",
        "ai_rfc.pipeline",
        f"{PACKAGE}.pipeline.cli",
        "status, substrate, run — drive the deterministic stages",
    ),
    EntryPoint(
        "timeline",
        "ai_rfc.timeline",
        f"{PACKAGE}.timeline.cli",
        "Cluster the corpus into an ordered timeline",
    ),
    EntryPoint(
        "views",
        "ai_rfc.views",
        f"{PACKAGE}.views.cli",
        "Emit per-cluster evidence bundles",
    ),
)
