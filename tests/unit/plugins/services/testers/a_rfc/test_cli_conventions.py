"""Conventions every a_rfc entry point holds to.

The substrate is six independent ``python -m`` commands that a human and an
agent both drive, so the properties that make them scriptable are worth
asserting once across all of them rather than six times in six files.
"""

import pytest

from panther import __version__
from panther.plugins.services.testers.a_rfc import cli as root_cli
from panther.plugins.services.testers.a_rfc.coverage import cli as coverage_cli
from panther.plugins.services.testers.a_rfc.draft import cli as draft_cli
from panther.plugins.services.testers.a_rfc.forge import cli as forge_cli
from panther.plugins.services.testers.a_rfc.history import cli as history_cli
from panther.plugins.services.testers.a_rfc.pipeline import cli as pipeline_cli
from panther.plugins.services.testers.a_rfc.timeline import cli as timeline_cli
from panther.plugins.services.testers.a_rfc.views import cli as views_cli

pytestmark = pytest.mark.unit

#: Every ``python -m`` entry point the package exposes. A new sub-package that
#: is not listed here is silently exempt from both invariants below, which is
#: the whole failure this file exists to prevent — so adding one is part of
#: adding the sub-package.
ENTRY_POINTS = (
    ("a_rfc", root_cli),
    ("a_rfc.draft", draft_cli),
    ("a_rfc.forge", forge_cli),
    ("a_rfc.history", history_cli),
    ("a_rfc.pipeline", pipeline_cli),
    ("a_rfc.coverage", coverage_cli),
    ("a_rfc.timeline", timeline_cli),
    ("a_rfc.views", views_cli),
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
