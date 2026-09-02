"""The ai_rfc substrate's commands, mounted under ``panther ai-rfc``.

The substrate is eight argparse CLIs that a human and an agent both drive as
``python -m``. This group is a second door onto the same ``main`` functions: it
forwards argv untouched and exits on whatever the sub-CLI returns, so the two
doors cannot disagree about behaviour or exit codes.

Each sub-CLI is imported inside its callback rather than at module scope.
``register_commands`` swallows an ``ImportError`` here into a warning that is
never printed, because it runs before any click context exists — so a top-level
import would let a broken substrate delete this command from ``panther --help``
in silence. Importing late turns that into an error someone sees.
"""

from __future__ import annotations

import sys

import click

from panther.plugins.services.testers.ai_rfc.entrypoints import ENTRY_POINTS, EntryPoint


@click.group(name="ai-rfc")
def ai_rfc() -> None:
    """Reconstruct an RFC-style specification from a project's own history.

    Every subcommand forwards its arguments unchanged to the matching
    ``python -m panther.plugins.services.testers.ai_rfc`` entry point, which
    remains supported and is what the agent harness invokes.
    """


def _passthrough(entry: EntryPoint) -> click.Command:
    """Build the click command that forwards to one entry point.

    Args:
        entry: The registry entry to wrap.

    Returns:
        A click command named for ``entry.verb``, taking every argument
        uninterpreted.
    """

    @click.command(
        name=entry.verb,
        help=entry.summary,
        short_help=entry.summary,
        context_settings={"ignore_unknown_options": True},
        add_help_option=False,
    )
    @click.argument("args", nargs=-1, type=click.UNPROCESSED)
    def command(args: tuple[str, ...]) -> None:
        sys.exit(entry.load().main(list(args)))

    return command


for _entry in ENTRY_POINTS:
    ai_rfc.add_command(_passthrough(_entry))
