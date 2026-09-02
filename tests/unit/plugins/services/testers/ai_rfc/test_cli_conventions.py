"""Conventions every ai_rfc entry point holds to.

The substrate is eight independent ``python -m`` commands that a human and an
agent both drive, so the properties that make them scriptable are worth
asserting once across all of them rather than eight times in eight files.
"""

import importlib
import re
import sys
from pathlib import Path

import pytest

from panther import __version__
from panther.plugins.services.testers.ai_rfc import cli as root_cli
from panther.plugins.services.testers.ai_rfc.entrypoints import ENTRY_POINTS, PACKAGE

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("entry", ENTRY_POINTS, ids=[e.prog for e in ENTRY_POINTS])
def test_every_entry_point_reports_its_version(entry, capsys):
    """Reproducibility is the stated point, so each command names its build."""
    with pytest.raises(SystemExit) as exit_info:
        entry.load().main(["--version"])
    assert exit_info.value.code == 0
    stdout = capsys.readouterr().out
    assert entry.prog in stdout
    assert __version__ in stdout


@pytest.mark.parametrize("entry", ENTRY_POINTS, ids=[e.prog for e in ENTRY_POINTS])
def test_a_malformed_invocation_exits_two_everywhere(entry):
    """2 belongs to argparse alone; strict findings return 3.

    This is the half of the split that is easy to regress. Moving findings to 3
    is only useful if 2 keeps meaning "the command was wrong" — a caller that
    branches on the pair needs both halves to hold, and only the findings half
    has tests of its own.
    """
    with pytest.raises(SystemExit) as exit_info:
        entry.load().main(["--no-such-flag"])
    assert exit_info.value.code == 2


@pytest.mark.parametrize("entry", ENTRY_POINTS, ids=[e.prog for e in ENTRY_POINTS])
def test_importing_an_entry_point_does_not_run_it(entry):
    """``python -m`` must stay the only way these run.

    An unguarded ``__main__.py`` calls ``sys.exit(cli.main())`` at import time,
    so anything that merely imports it — a test, a driver, a documentation tool
    — exits the interpreter, parsing whatever ``sys.argv`` happened to hold.
    """
    name = f"{entry.module.rsplit('.', 1)[0]}.__main__"
    sys.modules.pop(name, None)

    importlib.import_module(name)


PACKAGE_ROOT = Path(root_cli.__file__).parent

#: Helpers the README's "Known duplication to consolidate" table tracks by
#: hand, keyed by the name in its first column. Every row naming a function
#: belongs here: a row left uncovered is the one that silently passes, and the
#: register then reads as verified while being wrong.
TRACKED_HELPERS = ("_report", "_git", "_digest", "_digest_bytes")


def _package_sources() -> list[Path]:
    """Every module the table speaks for: the package, minus the harness."""
    return [
        path
        for path in sorted(PACKAGE_ROOT.rglob("*.py"))
        if "harness" not in path.relative_to(PACKAGE_ROOT).parts
        and "__pycache__" not in path.parts
    ]


def _defines(helper: str) -> set[str]:
    """Modules defining ``helper``, as paths relative to the package root."""
    pattern = re.compile(rf"^def {re.escape(helper)}\(", re.MULTILINE)
    return {
        path.relative_to(PACKAGE_ROOT).as_posix()
        for path in _package_sources()
        if pattern.search(path.read_text())
    }


def _declared(helper: str) -> set[str]:
    """Modules the README's table lists as holding a copy of ``helper``.

    Anchored to the table's own heading rather than scanning the whole file:
    any other pipe-delimited line naming the same helper would otherwise shadow
    the real row, and the test would then assert against something that is not
    the register.
    """
    lines = (PACKAGE_ROOT / "README.md").read_text().splitlines()
    start = next(
        index
        for index, line in enumerate(lines)
        if line.startswith("## Known duplication to consolidate")
    )
    for line in lines[start:]:
        if line.startswith("## ") and not line.startswith("## Known duplication"):
            break
        cells = [cell.strip() for cell in line.split("|")]
        if len(cells) > 2 and f"`{helper}`" in cells[1]:
            return set(re.findall(r"`([^`]+\.py)`", cells[2]))
    raise AssertionError(f"the duplication table has no row for {helper}")


@pytest.mark.parametrize("helper", TRACKED_HELPERS)
def test_the_duplication_table_names_every_copy(helper):
    """The table is only worth keeping if it is accurate.

    Its stated purpose is that accepted debt stays legible "rather than
    discovered twice", and it had already failed at that twice: five ``_report``
    copies were recorded against eight on disk, three ``_git`` against five, as
    ``coverage/``, ``forge/`` and ``pipeline/`` landed without anyone updating
    the row. A hand-maintained register of hand-maintained copies drifts unless
    something counts them, so this counts them.
    """
    defined = _defines(helper)
    # Guards the vacuous pass: a helper consolidated away, leaving an emptied
    # row nobody deleted, would otherwise match set() against set().
    assert defined, f"{helper} is in the table but defined nowhere"
    assert _declared(helper) == defined


def test_every_cli_module_on_disk_is_registered():
    """A sub-package nobody registers is the failure this file exists to stop.

    Single-sourcing the list only removes the second copy; it does not notice a
    ninth sub-package that never reached the first. This counts them, the way
    ``test_the_duplication_table_names_every_copy`` counts helper copies.
    """
    on_disk = {
        PACKAGE + "." + ".".join(path.relative_to(PACKAGE_ROOT).with_suffix("").parts)
        for path in PACKAGE_ROOT.rglob("cli.py")
        if "harness" not in path.relative_to(PACKAGE_ROOT).parts
    }
    assert on_disk == {entry.module for entry in ENTRY_POINTS}


def test_every_entry_declares_a_section():
    """An empty heading renders as a bare colon with its commands beneath it.

    Not a crash, which is why it is worth asserting: the listing still prints
    and still holds every command, under a heading that says nothing.
    """
    assert all(entry.section for entry in ENTRY_POINTS)


def test_entries_sharing_a_section_are_contiguous():
    """Declaration order is the help's order, so a section must not be split.

    ``setdefault`` in the group's ``format_commands`` merges a repeated heading
    into its first occurrence rather than printing it twice, so a split section
    silently hoists the later command up out of declaration order — quieter
    than a duplicated heading, and the reason this is asserted here.
    """
    runs: list[str] = []
    for entry in ENTRY_POINTS:
        if not runs or runs[-1] != entry.section:
            runs.append(entry.section)
    assert len(runs) == len(set(runs))
