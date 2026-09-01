"""Frozen records for reconstructed requirement claims.

This module holds data and derived read-only views. It decides nothing:
a claim's evidential standing is adjudicated in :mod:`promotion`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Status(Enum):
    """Evidential standing of a claim, weakest to strongest."""

    GAP = "gap"
    INFERRED = "inferred"
    CONFIRMED = "confirmed"


class EvidenceClass(Enum):
    """The kind of evidence an anchor points at."""

    CODE = "code"
    PAPER = "paper"
    INTERVIEW = "interview"
    ADR = "adr"
    RUNTIME = "runtime"


class RequirementClass(Enum):
    """The verification story a requirement belongs to."""

    PROTOCOL_BEHAVIORAL = "protocol-behavioral"
    DATA_MODEL = "data-model"
    ALGORITHMIC = "algorithmic"


class Intent(Enum):
    """Whether observed behaviour is meant, incidental, or undetermined."""

    INTENDED = "intended"
    ACCIDENTAL = "accidental"
    UNKNOWN = "unknown"


STATUS_RANK: dict[Status, int] = {
    Status.GAP: 0,
    Status.INFERRED: 1,
    Status.CONFIRMED: 2,
}

COMMIT_REQUIRED_FOR = frozenset({EvidenceClass.CODE, EvidenceClass.RUNTIME})


@dataclass(frozen=True)
class Anchor:
    """One piece of evidence supporting a claim.

    Args:
        evidence_class: What kind of evidence this is.
        locator: Where it lives — a repository path, a DOI, an interview id.
        commit: The commit the locator was resolved against. Required for the
            classes in ``COMMIT_REQUIRED_FOR``; ``None`` for the others.
        line: Optional line number within a file locator.
        line_sha256: Optional hex digest of the cited line's bytes (newline
            stripped), so the citation survives verification even after the
            surrounding file drifts. Meaningless without ``line``.
    """

    evidence_class: EvidenceClass
    locator: str
    commit: str | None = None
    line: int | None = None
    line_sha256: str | None = None


@dataclass(frozen=True)
class RequirementClaim:
    """A single reconstructed requirement and the evidence behind it.

    ``status`` defaults to the most restrictive value. Nothing in this module
    ever widens it; see :mod:`promotion`.
    """

    id: str
    text: str
    section: str
    level: str
    layer: str
    req_class: RequirementClass
    intent: Intent
    anchors: tuple[Anchor, ...] = ()
    status: Status = Status.GAP
    signed_off_by: str | None = None
    question_id: str | None = None
    testable: bool | None = None

    @property
    def evidence_classes(self) -> frozenset[EvidenceClass]:
        """The distinct evidence classes among this claim's anchors."""
        return frozenset(anchor.evidence_class for anchor in self.anchors)

    @property
    def is_externally_checked(self) -> bool:
        """Whether a non-model oracle — a person or a run — has seen this."""
        return bool(self.signed_off_by) or (
            EvidenceClass.RUNTIME in self.evidence_classes
        )


@dataclass(frozen=True)
class Manifest:
    """A whole reconstructed specification.

    Derived quantities are properties rather than fields so they cannot drift
    out of sync with the claims they summarise.
    """

    rfc: str
    title: str
    claims: tuple[RequirementClaim, ...]

    @property
    def count_by_status(self) -> dict[str, int]:
        """Claim counts keyed by status value, including statuses with none."""
        counts = {status.value: 0 for status in Status}
        for claim in self.claims:
            counts[claim.status.value] += 1
        return counts

    @property
    def checked_fraction_by_req_class(self) -> dict[str, float]:
        """Fraction of confirmed claims externally checked, per requirement class.

        Returns:
            One entry per requirement class, including classes with no claims,
            which report ``0.0`` rather than raising.
        """
        fractions: dict[str, float] = {}
        for req_class in RequirementClass:
            confirmed = [
                claim
                for claim in self.claims
                if claim.req_class is req_class and claim.status is Status.CONFIRMED
            ]
            if not confirmed:
                fractions[req_class.value] = 0.0
                continue
            checked = sum(1 for claim in confirmed if claim.is_externally_checked)
            fractions[req_class.value] = checked / len(confirmed)
        return fractions

    @property
    def confirmed_count_by_req_class(self) -> dict[str, int]:
        """Confirmed claim counts per requirement class.

        The denominator behind ``checked_fraction_by_req_class``. It is reported
        separately because a fraction of ``0.0`` has two readings — nothing
        confirmed here was externally checked, or nothing here is confirmed —
        and only the count says which one applies.

        Returns:
            One entry per requirement class, including classes with no claims.
        """
        counts = {req_class.value: 0 for req_class in RequirementClass}
        for claim in self.claims:
            if claim.status is Status.CONFIRMED:
                counts[claim.req_class.value] += 1
        return counts
