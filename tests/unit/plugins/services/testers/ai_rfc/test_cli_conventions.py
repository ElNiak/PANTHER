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
from panther.plugins.services.testers.ai_rfc.coverage import cli as coverage_cli
from panther.plugins.services.testers.ai_rfc.draft import cli as draft_cli
from panther.plugins.services.testers.ai_rfc.forge import cli as forge_cli
from panther.plugins.services.testers.ai_rfc.history import cli as history_cli
from panther.plugins.services.testers.ai_rfc.pipeline import cli as pipeline_cli
from panther.plugins.services.testers.ai_rfc.timeline import cli as timeline_cli
from panther.plugins.services.testers.ai_rfc.views import cli as views_cli

pytestmark = pytest.mark.unit

#: Every ``python -m`` entry point the package exposes. A new sub-package that
#: is not listed here is silently exempt from both invariants below, which is
#: the whole failure this file exists to prevent — so adding one is part of
#: adding the sub-package.
ENTRY_POINTS = (
    ("ai_rfc", root_cli),
    ("ai_rfc.draft", draft_cli),
    ("ai_rfc.forge", forge_cli),
    ("ai_rfc.history", history_cli),
    ("ai_rfc.pipeline", pipeline_cli),
    ("ai_rfc.coverage", coverage_cli),
    ("ai_rfc.timeline", timeline_cli),
    ("ai_rfc.views", views_cli),
)


@pytest.mark.parametrize("prog,module", ENTRY_POINTS, ids=[p for p, _ in ENTRY_POINTS])
def test_every_entry_point_reports_its_version(prog, module, capsys):
    """Reproducibility is the stated point, so each command names its build."""
    with pytest.raises(SystemExit) as exit_info:
        module.main(["--version"])
    assert exit_info.value.code == 0
    stdout = capsys.readouterr().out
    assert prog in stdout
    assert __version__ in stdout


@pytest.mark.parametrize("prog,module", ENTRY_POINTS, ids=[p for p, _ in ENTRY_POINTS])
def test_a_malformed_invocation_exits_two_everywhere(prog, module):
    """2 belongs to argparse alone; strict findings return 3.

    This is the half of the split that is easy to regress. Moving findings to 3
    is only useful if 2 keeps meaning "the command was wrong" — a caller that
    branches on the pair needs both halves to hold, and only the findings half
    has tests of its own.
    """
    with pytest.raises(SystemExit) as exit_info:
        module.main(["--no-such-flag"])
    assert exit_info.value.code == 2


@pytest.mark.parametrize("prog,module", ENTRY_POINTS, ids=[p for p, _ in ENTRY_POINTS])
def test_importing_an_entry_point_does_not_run_it(prog, module):
    """``python -m`` must stay the only way these run.

    An unguarded ``__main__.py`` calls ``sys.exit(cli.main())`` at import time,
    so anything that merely imports it — a test, a driver, a documentation tool
    — exits the interpreter, parsing whatever ``sys.argv`` happened to hold.
    """
    name = f"{module.__name__.rsplit('.', 1)[0]}.__main__"
    sys.modules.pop(name, None)

    importlib.import_module(name)


PACKAGE_ROOT = Path(root_cli.__file__).parent

#: Helpers the README's "Known duplication to consolidate" table tracks by
#: hand, keyed by the name in its first column.
TRACKED_HELPERS = ("_report", "_git")


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
    """Modules the README's table lists as holding a copy of ``helper``."""
    for line in (PACKAGE_ROOT / "README.md").read_text().splitlines():
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
    assert _declared(helper) == _defines(helper)
