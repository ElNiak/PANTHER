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
        section: The heading ``panther ai-rfc --help`` lists this command
            under. Entries sharing one are kept contiguous in
            :data:`ENTRY_POINTS`, because that order is the order the help
            prints.
    """

    verb: str
    prog: str
    module: str
    summary: str
    section: str

    def load(self) -> CommandModule:
        """Import the module this entry names.

        Returns:
            The command's module, which satisfies :class:`CommandModule`.
        """
        return cast(CommandModule, import_module(self.module))


#: Headings ``panther ai-rfc --help`` lists commands under. Plain text: click's
#: formatter writes them verbatim, so backticks would print as backticks.
DRIVEN = "Commands you drive"
BY_HAND = "Run these yourself"
PERFORMED = "Stages pipeline run reaches before it needs you"


ENTRY_POINTS: tuple[EntryPoint, ...] = (
    EntryPoint(
        "pipeline",
        "ai_rfc.pipeline",
        f"{PACKAGE}.pipeline.cli",
        "Show where a workspace stands and run whatever stage is ready "
        "(status, substrate, run)",
        DRIVEN,
    ),
    EntryPoint(
        "check",
        "ai_rfc",
        f"{PACKAGE}.cli",
        "Report which manifest claims are not backed by the code their "
        "anchors point at",
        BY_HAND,
    ),
    EntryPoint(
        "draft",
        "ai_rfc.draft",
        f"{PACKAGE}.draft.cli",
        "Freeze the manifest per cluster, then gate the prose against it "
        "(checkpoint, gate, completeness)",
        BY_HAND,
    ),
    EntryPoint(
        "coverage",
        "ai_rfc.coverage",
        f"{PACKAGE}.coverage.cli",
        "Propose anchors for the lines a test run actually executed",
        BY_HAND,
    ),
    EntryPoint(
        "history",
        "ai_rfc.history",
        f"{PACKAGE}.history.cli",
        "Turn a pinned clone's commits into a queryable corpus",
        PERFORMED,
    ),
    EntryPoint(
        "forge",
        "ai_rfc.forge",
        f"{PACKAGE}.forge.cli",
        "Pull pull-request discussion from GitHub or GitLab (fetch, adopt)",
        PERFORMED,
    ),
    EntryPoint(
        "timeline",
        "ai_rfc.timeline",
        f"{PACKAGE}.timeline.cli",
        "Group the corpus into ordered clusters, one per pull request",
        PERFORMED,
    ),
    EntryPoint(
        "views",
        "ai_rfc.views",
        f"{PACKAGE}.views.cli",
        "Write the per-cluster evidence folder an author reads",
        PERFORMED,
    ),
)
