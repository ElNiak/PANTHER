"""Read a JaCoCo XML report.

JaCoCo emits two shapes. A single module's ``report`` holds ``package``
elements directly; ``report-aggregate`` wraps them in ``group`` elements, one
per module, and MARK's build produces both — per-module reports from ``report``
and a merged one from the ``coverage`` module. Walking ``package`` at any depth
reads either without branching on which it is.
"""

from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from pathlib import Path

from .model import CoverageReport, ExecutedLine

TOOL = "jacoco"


class CoverageError(RuntimeError):
    """Raised when a coverage report cannot be read as one."""


def read(path: Path) -> CoverageReport:
    """Parse a JaCoCo XML report.

    A line counts as executed when ``ci`` — JaCoCo's count of *covered
    instructions* — is above zero. That is the strongest thing the format
    states: it says the line ran, not that anything asserted on what it did.

    Args:
        path: The ``jacoco.xml`` to read.

    Returns:
        The parsed report.

    Raises:
        CoverageError: If the file is not a JaCoCo report.
        OSError: If it cannot be read.
    """
    raw = path.read_bytes()
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as error:
        raise CoverageError(f"{path} is not valid XML: {error}") from None
    if root.tag != "report":
        raise CoverageError(
            f"{path} has root <{root.tag}>, not <report>; not a JaCoCo report"
        )

    lines: list[ExecutedLine] = []
    for package in root.iter("package"):
        prefix = package.get("name", "")
        for sourcefile in package.findall("sourcefile"):
            name = sourcefile.get("name", "")
            suffix = f"{prefix}/{name}" if prefix else name
            for line in sourcefile.findall("line"):
                number = line.get("nr")
                if number is None:
                    continue
                lines.append(
                    ExecutedLine(
                        source_path_suffix=suffix,
                        line=int(number),
                        executed=int(line.get("ci", "0")) > 0,
                    )
                )

    return CoverageReport(
        tool=TOOL,
        # JaCoCo's XML carries no plugin version. The report is digested
        # instead, which identifies the run exactly rather than the tool
        # approximately.
        tool_version=root.get("name", ""),
        report_sha256=hashlib.sha256(raw).hexdigest(),
        lines=tuple(lines),
    )
