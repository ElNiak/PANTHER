from pathlib import Path

import pytest

from panther.plugins.services.testers.a_rfc.runtime.jacoco import CoverageError, read

pytestmark = pytest.mark.unit

#: Trimmed from MARK's own `mvn -pl server verify` output, so the shape under
#: test is the one JaCoCo really emits rather than one written to pass.
FIXTURE = Path(__file__).parent / "fixtures" / "jacoco-server.xml"

NESTED = """\
<report name="aggregate">
  <group name="server">
    <package name="be/cylab/mark/detection">
      <sourcefile name="OWAverage.java">
        <line nr="52" mi="0" ci="2" mb="0" cb="0"/>
        <line nr="53" mi="2" ci="0" mb="0" cb="0"/>
      </sourcefile>
    </package>
  </group>
</report>
"""


def test_reads_the_flat_per_module_shape():
    report = read(FIXTURE)
    assert report.tool == "jacoco"
    assert report.tool_version == "server"
    assert len(report.report_sha256) == 64
    assert len(report.lines) == 15


def test_reads_the_group_nested_aggregate_shape(tmp_path: Path):
    """`report-aggregate` wraps packages in one group per module.

    MARK's build produces both shapes — per-module reports from `report` and a
    merged one from the coverage module — so a reader that handles only the
    flat one silently returns nothing for the aggregate.
    """
    path = tmp_path / "aggregate.xml"
    path.write_text(NESTED)
    report = read(path)
    suffixes = {line.source_path_suffix for line in report.lines}
    assert suffixes == {"be/cylab/mark/detection/OWAverage.java"}
    assert report.executed_at("be/cylab/mark/detection/OWAverage.java", 52) is True


def test_a_line_is_executed_only_when_instructions_were_covered():
    report = read(FIXTURE)
    assert report.executed_at("be/cylab/mark/data/FileSource.java", 52) is True
    assert report.executed_at("be/cylab/mark/data/FileSource.java", 94) is False


def test_a_line_absent_from_the_report_is_not_executed():
    """Coverage omits lines carrying no code; silence must not read as a run."""
    report = read(FIXTURE)
    assert report.executed_at("be/cylab/mark/data/FileSource.java", 9999) is False
    assert report.executed_at("no/such/File.java", 52) is False


def test_a_non_report_root_is_refused(tmp_path: Path):
    path = tmp_path / "wrong.xml"
    path.write_text("<coverage><line/></coverage>\n")
    with pytest.raises(CoverageError, match="not a JaCoCo report"):
        read(path)


def test_malformed_xml_is_refused(tmp_path: Path):
    path = tmp_path / "bad.xml"
    path.write_text("<report><package>\n")
    with pytest.raises(CoverageError, match="not valid XML"):
        read(path)
