import subprocess
from pathlib import Path

import pytest

SOURCE = """\
package be.cylab.mark.detection;

public class OWAverage {
    public double analyze(double[] values) {
        return values[0];
    }
}
"""


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def java_repo(tmp_path: Path) -> tuple[Path, str]:
    """A repository laying a source file under a Maven-shaped path.

    The point of the layout is the gap it creates: coverage names the file
    ``be/cylab/mark/detection/OWAverage.java`` while the manifest cites
    ``server/src/main/java/be/cylab/...``, which is the resolution the binder
    exists to do.
    """
    repo = tmp_path / "clone"
    target = repo / "server" / "src" / "main" / "java" / "be" / "cylab" / "mark"
    (target / "detection").mkdir(parents=True)
    (target / "detection" / "OWAverage.java").write_text(SOURCE)
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "add OWAverage")
    return repo, _git(repo, "rev-parse", "HEAD")


COVERAGE = """\
<report name="server">
  <package name="be/cylab/mark/detection">
    <sourcefile name="OWAverage.java">
      <line nr="5" mi="0" ci="3" mb="0" cb="0"/>
      <line nr="6" mi="2" ci="0" mb="0" cb="0"/>
    </sourcefile>
  </package>
</report>
"""


@pytest.fixture
def coverage_report(tmp_path: Path) -> Path:
    """A report covering line 5 of the fixture source and not line 6."""
    path = tmp_path / "jacoco.xml"
    path.write_text(COVERAGE)
    return path


def manifest_text(line: int) -> str:
    """A one-claim manifest citing the fixture source at ``line``."""
    return (
        "rfc: MARK-TEST\n"
        "title: 'Fixture'\n"
        "requirements:\n"
        "  'mark:alg.1':\n"
        "    text: 'A claim about the averaging agent.'\n"
        "    section: '3.1'\n"
        "    level: MUST\n"
        "    layer: detection\n"
        "    status: inferred\n"
        "    anchors:\n"
        "      - evidence_class: code\n"
        "        locator: "
        "server/src/main/java/be/cylab/mark/detection/OWAverage.java\n"
        "        commit: '{commit}'\n"
        f"        line: {line}\n"
    )
