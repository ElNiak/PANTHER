"""``panther ai-rfc``: PANTHER's door onto the ai_rfc tool.

ai_rfc is its own project, installed from the submodule at
``panther/plugins/services/testers/ai_rfc`` by ``panther build dev``. This
command forwards everything after ``ai-rfc`` to that tool's own dispatcher and
exits with whatever it returns, so ``panther ai-rfc`` and ``ai-rfc`` cannot
disagree.

The import happens inside the callback. ``register_commands`` swallows an
``ImportError`` raised at import time into a warning nobody sees, so an
uninstalled submodule must fail here, where the message reaches a terminal.
"""

from __future__ import annotations

import sys

import click


@click.command(
    name="ai-rfc",
    help="Reconstruct an RFC-style specification from a project's own history.",
    context_settings={"ignore_unknown_options": True},
    add_help_option=False,
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def ai_rfc(args: tuple[str, ...]) -> None:
    """Forward to ``ai-rfc`` and exit with its code."""
    try:
        from ai_rfc.cli import main
    except ImportError:
        raise click.ClickException(
            "ai_rfc is not installed: run "
            "`git submodule update --init panther/plugins/services/testers/ai_rfc` "
            "and then `panther build dev`"
        ) from None
    sys.exit(main(list(args)))
