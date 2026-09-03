"""Propose ``runtime`` anchors from a bound coverage run.

AnchorProposals only. A ``runtime`` anchor is primary evidence, so adding one beside
an existing ``code`` anchor takes a claim to ``confirmed`` under the promotion
rule — which is exactly why this module writes a separate file and never
touches the manifest. Merging is somebody's decision, and it should look like
one.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..models import EvidenceClass, Manifest
from .commit import PinError, line_digest, path_index, require_clean_checkout, resolve
from .model import CoverageReport

#: What an emitted anchor claims, recorded beside every proposal. A covered
#: line is a line that *ran*; nothing in a coverage report says an assertion
#: examined what it did. The promotion rule cannot tell those apart, so the
#: distinction is written down where a reader will meet it.
PROPOSAL_CRITERION = "line-executed"


@dataclass(frozen=True)
class AnchorProposal:
    """One runtime anchor a coverage run supports."""

    claim_id: str
    locator: str
    commit: str
    line: int
    line_sha256: str


@dataclass(frozen=True)
class SkippedAnchor:
    """One code anchor that got no runtime anchor, and why."""

    claim_id: str
    locator: str
    line: int | None
    reason: str


def propose(
    manifest: Manifest,
    report: CoverageReport,
    repo: Path,
    commit: str,
) -> tuple[tuple[AnchorProposal, ...], tuple[SkippedAnchor, ...], str]:
    """Propose runtime anchors for the lines a run actually reached.

    An anchor is emitted only where the manifest already cites that exact file
    and line as ``code`` evidence and the report says it ran. Proposing for
    lines nothing claims would grow the manifest from coverage, which is
    backwards: coverage corroborates a claim somebody made, it does not make
    claims.

    Args:
        manifest: The manifest whose code anchors are being corroborated.
        report: A coverage run, already read.
        repo: The clone the run came from, at ``commit``.
        commit: The commit to bind the anchors to.

    Returns:
        The proposals, the code anchors that got none with the reason, and the
        commit ``commit`` resolved to. Callers recording provenance must use
        this third element, not the ``commit`` argument: a branch or tag
        names a commit today and may name another tomorrow, so recording what
        was typed would describe the run with something that moves while
        every proposal in it is pinned to what it resolved to.

    Raises:
        PinError: If the checkout is not at ``commit`` or is dirty.
    """
    # Everything below uses what the ref resolved to, never what was typed. A
    # branch or tag names a commit today and may name another tomorrow, so
    # recording the given string would pin an anchor to something that moves.
    commit = require_clean_checkout(repo, commit)
    index = path_index(repo, commit)

    proposals: list[AnchorProposal] = []
    skipped: list[SkippedAnchor] = []
    for claim in manifest.claims:
        for anchor in claim.anchors:
            if anchor.evidence_class is not EvidenceClass.CODE:
                continue
            if anchor.line is None:
                skipped.append(
                    SkippedAnchor(
                        claim.id, anchor.locator, None, "the anchor cites no line"
                    )
                )
                continue
            suffix = _suffix_for(anchor.locator, report)
            if suffix is None:
                skipped.append(
                    SkippedAnchor(
                        claim.id,
                        anchor.locator,
                        anchor.line,
                        "the coverage report does not mention this file",
                    )
                )
                continue
            if not report.executed_at(suffix, anchor.line):
                skipped.append(
                    SkippedAnchor(
                        claim.id,
                        anchor.locator,
                        anchor.line,
                        "the run did not reach this line",
                    )
                )
                continue
            try:
                resolved = resolve(suffix, index)
                digest = line_digest(repo, commit, resolved, anchor.line)
            except PinError as error:
                skipped.append(
                    SkippedAnchor(claim.id, anchor.locator, anchor.line, str(error))
                )
                continue
            proposals.append(
                AnchorProposal(claim.id, resolved, commit, anchor.line, digest)
            )
    return tuple(proposals), tuple(skipped), commit


def _suffix_for(locator: str, report: CoverageReport) -> str | None:
    """The coverage suffix naming the same file as a repository path.

    The manifest cites a repository path and the report a source-root-relative
    one, so the two are matched from the tail inwards. The longest match wins,
    which is what stops ``Evidence.java`` in one package standing in for the
    same basename in another.
    """
    parts = locator.split("/")
    known = {entry.source_path_suffix for entry in report.lines}
    for start in range(len(parts)):
        candidate = "/".join(parts[start:])
        if candidate in known:
            return candidate
    return None
