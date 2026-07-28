"""The claim-promotion rule.

The single place a claim's evidential standing is decided. Two properties hold
throughout and are worth preserving in any future edit:

* adjudication is a pure function of the claim's own evidence, and
* every unrecognised or absent input yields the *most restrictive* status.

A rule that fails open produces a manifest that looks excellent and means
nothing, with the run exiting zero.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import STATUS_RANK, EvidenceClass, Manifest, RequirementClaim, Status

#: Evidence that cannot by itself carry a claim beyond ``inferred``. Mined
#: decision records and paper prose describe intent, not behaviour.
WEAK_EVIDENCE = frozenset({EvidenceClass.ADR, EvidenceClass.PAPER})


@dataclass(frozen=True)
class Violation:
    """A claim whose recorded status exceeds what its evidence supports."""

    claim_id: str
    stored: Status
    supported: Status
    reason: str


def adjudicate(claim: RequirementClaim) -> Status:
    """Decide the strongest status a claim's evidence actually supports.

    A claim reaches ``confirmed`` only through developer sign-off, runtime
    corroboration, or two distinct evidence classes at least one of which is
    not weak. Claims resting only on decision records or paper prose are
    capped at ``inferred``. A claim with no evidence at all is a ``gap``,
    sign-off notwithstanding — signing off on nothing records nothing.

    Args:
        claim: The claim to adjudicate.

    Returns:
        The strongest status the evidence supports.
    """
    if not claim.anchors:
        return Status.GAP

    classes = claim.evidence_classes

    if classes <= WEAK_EVIDENCE and not claim.signed_off_by:
        return Status.INFERRED

    if claim.signed_off_by:
        return Status.CONFIRMED

    if EvidenceClass.RUNTIME in classes:
        return Status.CONFIRMED

    if len(classes) >= 2:
        return Status.CONFIRMED

    return Status.INFERRED


def violations(manifest: Manifest) -> tuple[Violation, ...]:
    """Find claims recorded more strongly than their evidence allows.

    A claim recorded *below* what its evidence supports is not a violation —
    understatement is always permitted.

    Args:
        manifest: The manifest to check.

    Returns:
        One violation per overstated claim, in manifest order.
    """
    found = []
    for claim in manifest.claims:
        supported = adjudicate(claim)
        if STATUS_RANK[claim.status] > STATUS_RANK[supported]:
            found.append(
                Violation(
                    claim_id=claim.id,
                    stored=claim.status,
                    supported=supported,
                    reason=(
                        f"recorded as {claim.status.value} but its evidence "
                        f"supports only {supported.value}"
                    ),
                )
            )
    return tuple(found)
