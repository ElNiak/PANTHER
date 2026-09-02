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

#: Attribute a passthrough command carries its help heading on. Mirrors
#: ``FEATURED_EXAMPLE_ATTR`` in ``panther.cli.core.base``, which is how this
#: codebase already attaches help metadata to a command.
SECTION_ATTR = "_panther_help_section"


class SectionedGroup(click.Group):
    """A group that lists its commands under headings, in registration order.

    Click's own ``format_commands`` sorts alphabetically into a single
    unlabelled block. These commands are the stages of one pipeline, so the
    order they are declared in is the order they are meant to be run in, and
    flattening it is what makes eight commands read as too many.
    """

    def format_commands(
        self, ctx: click.Context, formatter: click.HelpFormatter
    ) -> None:
        """Write one definition list per section, in registration order.

        Args:
            ctx: The context being formatted.
            formatter: The help formatter to write into.
        """
        sections: dict[str, list[click.Command]] = {}
        # Not ``list_commands``: it sorts, and the declared order is the order
        # the stages are meant to be run in.
        for name in self.commands:
            command = self.get_command(ctx, name)
            if command is None or command.hidden:
                continue
            heading = getattr(command, SECTION_ATTR, "Commands")
            sections.setdefault(heading, []).append(command)

        for heading, commands in sections.items():
            names = [command.name or "" for command in commands]
            limit = formatter.width - 6 - max(len(name) for name in names)
            rows = [
                (name, command.get_short_help_str(limit))
                for name, command in zip(names, commands)
            ]
            with formatter.section(heading):
                formatter.write_dl(rows)


@click.group(name="ai-rfc", cls=SectionedGroup)
def ai_rfc() -> None:
    """Reconstruct an RFC-style specification from a project's own history.

    Every subcommand forwards its arguments unchanged to the matching
    "python -m panther.plugins.services.testers.ai_rfc" entry point, which
    remains supported and is what the agent harness invokes.
    """


def _passthrough(entry: EntryPoint) -> click.Command:
    """Build the click command that forwards to one entry point.

    Args:
        entry: The registry entry to wrap.

    Returns:
        A click command named for ``entry.verb``, taking every argument
        uninterpreted, and tagged with ``entry.section`` so the group can list
        it under the right heading.
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

    setattr(command, SECTION_ATTR, entry.section)
    return command


for _entry in ENTRY_POINTS:
    ai_rfc.add_command(_passthrough(_entry))
