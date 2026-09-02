"""The ``panther ai-rfc`` door onto the ai_rfc substrate.

The eight commands answer to two front doors — ``python -m`` and this group —
and the guarantee worth having is that they cannot disagree. Everything here
derives from the one registry: a command on disk that nobody registered fails
in ``test_cli_conventions``, and a registered command nobody mounted fails here.
"""

import pytest
from click.testing import CliRunner

from panther.cli.commands.ai_rfc import ai_rfc
from panther.cli.core.main import cli
from panther.plugins.services.testers.ai_rfc.entrypoints import ENTRY_POINTS

pytestmark = pytest.mark.unit


def test_the_group_reaches_the_panther_cli():
    """A silent ImportError would delete it from ``panther --help``.

    ``register_commands`` collects an import failure into a warning it prints
    only when a click context exists, and it runs at import time when none
    does. Asserting on the built group is the only thing that notices.
    """
    assert "ai-rfc" in cli.commands


def test_every_registered_command_is_mounted():
    """The drift check the registry exists for, in the click direction."""
    assert set(ai_rfc.commands) == {entry.verb for entry in ENTRY_POINTS}


@pytest.mark.parametrize("entry", ENTRY_POINTS, ids=[e.verb for e in ENTRY_POINTS])
def test_a_malformed_invocation_still_exits_two(entry):
    """Exit 2 belongs to argparse alone; click must not relabel it."""
    result = CliRunner().invoke(ai_rfc, [entry.verb, "--no-such-flag"])
    assert result.exit_code == 2


@pytest.mark.parametrize("entry", ENTRY_POINTS, ids=[e.verb for e in ENTRY_POINTS])
def test_version_passes_through_to_the_sub_cli(entry):
    """The sub-CLI's own prog must survive the forward, not the verb."""
    result = CliRunner().invoke(ai_rfc, [entry.verb, "--version"])
    assert result.exit_code == 0
    assert entry.prog in result.output


@pytest.mark.parametrize("entry", ENTRY_POINTS, ids=[e.verb for e in ENTRY_POINTS])
def test_each_verb_carries_a_description(entry):
    """``mkdocs-click`` renders these; an empty help is a blank reference row."""
    assert ai_rfc.commands[entry.verb].help == entry.summary


def _command_sections(output: str) -> dict[str, str]:
    """Split rendered group help into {heading: the block beneath it}.

    Args:
        output: The rendered ``panther ai-rfc --help`` text.

    Returns:
        Each heading the registry declares, mapped to its slice of the help.

    Raises:
        ValueError: If a declared heading is absent, which is what click's
            unsectioned default produces.
    """
    headings = list(dict.fromkeys(entry.section for entry in ENTRY_POINTS))
    starts = [output.index(f"{heading}:") for heading in headings]
    ends = starts[1:] + [len(output)]
    return {
        heading: output[start:end]
        for heading, start, end in zip(headings, starts, ends)
    }


def test_the_sections_appear_in_declaration_order():
    """Registry order is the workflow order; alphabetical would hide it."""
    output = CliRunner().invoke(ai_rfc, ["--help"]).output
    headings = list(dict.fromkeys(entry.section for entry in ENTRY_POINTS))
    positions = [output.index(f"{heading}:") for heading in headings]
    assert positions == sorted(positions)


def test_each_verb_is_listed_under_the_section_it_declares():
    """The only guard on the ``format_commands`` override.

    Click's default sorts every command into one unlabelled block and renders
    without error, so nothing else here would notice the sectioning reverting.
    The needle carries the term column's indent because ``draft``'s summary
    names ``checkpoint``, which a bare substring test would match as ``check``.
    """
    output = CliRunner().invoke(ai_rfc, ["--help"]).output
    sections = _command_sections(output)
    for entry in ENTRY_POINTS:
        assert f"\n  {entry.verb} " in sections[entry.section]
