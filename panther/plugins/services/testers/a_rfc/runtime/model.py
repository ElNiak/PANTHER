"""What a coverage run says, independent of the tool that produced it.

A reader is any callable from a path to a :class:`CoverageReport`. Keeping the
model tool-agnostic is not speculation: MARK is Maven with JaCoCo and aioquic is
Python with coverage.py, and both are reconstruction targets today.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutedLine:
    """One source line and whether a run reached it."""

    #: The tail of the source path as the coverage tool spells it, e.g.
    #: ``be/cylab/mark/detection/OWAverage.java``. Coverage tools report a path
    #: relative to their own source roots, which is not the repository path an
    #: anchor cites; resolving one to the other is :mod:`commit`'s job.
    source_path_suffix: str
    line: int
    executed: bool


@dataclass(frozen=True)
class CoverageReport:
    """One coverage run, with enough provenance to cite it.

    The digest is of the report file itself. An anchor proposed from a run has
    to be traceable to that run, and the report is the only artifact that
    survives it.
    """

    tool: str
    tool_version: str
    report_sha256: str
    lines: tuple[ExecutedLine, ...]

    def executed_at(self, suffix: str, line: int) -> bool:
        """Whether the run reached one line of one file.

        Args:
            suffix: The source path suffix to look up.
            line: The 1-based line number.

        Returns:
            True only when the report has that line and it ran. An absent line
            is not executed — coverage tools omit lines that carry no code, and
            treating silence as execution is the direction that invents
            evidence.
        """
        return any(
            entry.source_path_suffix == suffix and entry.line == line and entry.executed
            for entry in self.lines
        )
