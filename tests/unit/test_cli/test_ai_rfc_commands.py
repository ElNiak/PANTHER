"""The ``panther ai-rfc`` door onto the installed ai_rfc tool.

Everything after ``ai-rfc`` is forwarded to ``ai_rfc.cli.main`` and the exit
code comes back untouched, so the door and ``ai-rfc`` cannot disagree.
"""

import pytest
from click.testing import CliRunner

from panther.cli.commands.ai_rfc import ai_rfc
from panther.cli.core.main import cli

pytestmark = pytest.mark.unit


def test_the_door_reaches_the_panther_cli():
    """A silent ImportError would delete it from ``panther --help``."""
    assert "ai-rfc" in cli.commands


def test_help_is_the_tools_own():
    result = CliRunner().invoke(ai_rfc, ["--help"])
    assert result.exit_code == 0
    assert result.output.startswith("usage: ai-rfc <verb>")


def test_a_malformed_invocation_still_exits_two():
    """Argparse owns 2, and click must not relabel it on the way out."""
    assert CliRunner().invoke(ai_rfc, ["check", "--no-such-flag"]).exit_code == 2


def test_an_unreadable_manifest_exits_one(tmp_path):
    """1 is returned, not raised: the one code a ``return`` in the callback would lose."""
    result = CliRunner().invoke(
        ai_rfc,
        ["check", str(tmp_path / "missing.yaml"), "--out", str(tmp_path / "out")],
    )
    assert result.exit_code == 1


def test_a_strict_finding_exits_three(tmp_path):
    manifest = tmp_path / "overstated.yaml"
    manifest.write_text(
        "rfc: SPEC-1\n"
        "title: 'x'\n"
        "requirements:\n"
        "  'spec:1.1':\n"
        "    text: 'x'\n"
        "    section: '1.1'\n"
        "    level: MUST\n"
        "    layer: timing\n"
        "    status: confirmed\n"
    )
    result = CliRunner().invoke(
        ai_rfc, ["check", str(manifest), "--out", str(tmp_path / "out"), "--strict"]
    )
    assert result.exit_code == 3


def test_panther_ai_rfc_help_is_the_root_help():
    """`panther ai-rfc --help` is `ai-rfc --help`, forwarded untouched."""
    result = CliRunner().invoke(cli, ["ai-rfc", "--help"])
    assert result.exit_code == 0
    assert "Lifecycle" in result.output
    assert "init" in result.output and "run" in result.output
