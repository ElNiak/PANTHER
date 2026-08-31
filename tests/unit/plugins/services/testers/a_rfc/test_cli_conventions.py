"""Conventions every a_rfc entry point holds to.

The substrate is six independent ``python -m`` commands that a human and an
agent both drive, so the properties that make them scriptable are worth
asserting once across all of them rather than six times in six files.
"""

import pytest

from panther import __version__
from panther.plugins.services.testers.a_rfc import cli as root_cli
from panther.plugins.services.testers.a_rfc.draft import cli as draft_cli
from panther.plugins.services.testers.a_rfc.forge import cli as forge_cli
from panther.plugins.services.testers.a_rfc.history import cli as history_cli
from panther.plugins.services.testers.a_rfc.timeline import cli as timeline_cli
from panther.plugins.services.testers.a_rfc.views import cli as views_cli

pytestmark = pytest.mark.unit

ENTRY_POINTS = (
    ("a_rfc", root_cli),
    ("a_rfc.draft", draft_cli),
    ("a_rfc.forge", forge_cli),
    ("a_rfc.history", history_cli),
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
