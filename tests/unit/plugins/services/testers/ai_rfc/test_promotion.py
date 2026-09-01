import pytest

from panther.plugins.services.testers.ai_rfc.models import (
    Anchor,
    EvidenceClass,
    Intent,
    Manifest,
    RequirementClaim,
    RequirementClass,
    Status,
)
from panther.plugins.services.testers.ai_rfc.promotion import adjudicate, violations

pytestmark = pytest.mark.unit

SHA = "00112233445566778899aabbccddeeff00112233"


def _claim(**overrides):
    base = dict(
        id="spec:1.1",
        text="The system responds within the configured interval.",
        section="1.1",
        level="MUST",
        layer="timing",
        req_class=RequirementClass.PROTOCOL_BEHAVIORAL,
        intent=Intent.INTENDED,
    )
    base.update(overrides)
    return RequirementClaim(**base)


def test_claim_without_anchors_cannot_exceed_gap():
    assert adjudicate(_claim()) is Status.GAP
    assert adjudicate(_claim(status=Status.CONFIRMED)) is Status.GAP


def test_signoff_without_any_anchor_is_still_a_gap():
    assert adjudicate(_claim(signed_off_by="dev-01")) is Status.GAP


def test_adr_only_claim_is_capped_at_inferred():
    claim = _claim(anchors=(Anchor(EvidenceClass.ADR, "adr/0007.md"),))
    assert adjudicate(claim) is Status.INFERRED


def test_paper_only_claim_is_capped_at_inferred():
    claim = _claim(anchors=(Anchor(EvidenceClass.PAPER, "10.1000/xyz"),))
    assert adjudicate(claim) is Status.INFERRED


def test_adr_and_paper_together_are_still_capped_at_inferred():
    claim = _claim(
        anchors=(
            Anchor(EvidenceClass.ADR, "adr/0007.md"),
            Anchor(EvidenceClass.PAPER, "10.1000/xyz"),
        )
    )
    assert adjudicate(claim) is Status.INFERRED


def test_single_code_anchor_alone_is_inferred():
    claim = _claim(anchors=(Anchor(EvidenceClass.CODE, "src/timer.py", commit=SHA),))
    assert adjudicate(claim) is Status.INFERRED


def test_runtime_anchor_reaches_confirmed():
    claim = _claim(anchors=(Anchor(EvidenceClass.RUNTIME, "run/42"),))
    assert adjudicate(claim) is Status.CONFIRMED


def test_signoff_with_an_anchor_reaches_confirmed():
    claim = _claim(
        anchors=(Anchor(EvidenceClass.ADR, "adr/0007.md"),),
        signed_off_by="dev-01",
    )
    assert adjudicate(claim) is Status.CONFIRMED


def test_two_distinct_evidence_classes_reach_confirmed():
    claim = _claim(
        anchors=(
            Anchor(EvidenceClass.CODE, "src/timer.py", commit=SHA),
            Anchor(EvidenceClass.PAPER, "10.1000/xyz"),
        )
    )
    assert adjudicate(claim) is Status.CONFIRMED


def test_two_narrative_classes_do_not_reach_confirmed():
    """An interview and a paper may be one person's account counted twice."""
    claim = _claim(
        anchors=(
            Anchor(EvidenceClass.INTERVIEW, "interview-03"),
            Anchor(EvidenceClass.PAPER, "10.1000/xyz"),
        )
    )
    assert adjudicate(claim) is Status.INFERRED


def test_interview_plus_adr_does_not_reach_confirmed():
    """Two classes, but neither is evidence the system itself produced."""
    claim = _claim(
        anchors=(
            Anchor(EvidenceClass.INTERVIEW, "interview-03"),
            Anchor(EvidenceClass.ADR, "adr/0007.md"),
        )
    )
    assert adjudicate(claim) is Status.INFERRED


def test_interview_plus_code_reaches_confirmed():
    """A narrative source corroborated by a primary artefact does promote."""
    claim = _claim(
        anchors=(
            Anchor(EvidenceClass.INTERVIEW, "interview-03"),
            Anchor(EvidenceClass.CODE, "src/timer.py", commit=SHA),
        )
    )
    assert adjudicate(claim) is Status.CONFIRMED


def test_two_anchors_of_the_same_class_do_not_reach_confirmed():
    claim = _claim(
        anchors=(
            Anchor(EvidenceClass.CODE, "src/a.py", commit=SHA),
            Anchor(EvidenceClass.CODE, "src/b.py", commit=SHA),
        )
    )
    assert adjudicate(claim) is Status.INFERRED


def test_overstated_status_is_reported_as_a_violation():
    manifest = Manifest(
        rfc="SPEC-1",
        title="x",
        claims=(
            _claim(
                id="spec:1.1",
                status=Status.CONFIRMED,
                anchors=(Anchor(EvidenceClass.ADR, "adr/0007.md"),),
            ),
        ),
    )
    found = violations(manifest)
    assert len(found) == 1
    assert found[0].claim_id == "spec:1.1"
    assert found[0].stored is Status.CONFIRMED
    assert found[0].supported is Status.INFERRED


def test_understated_status_is_not_a_violation():
    manifest = Manifest(
        rfc="SPEC-1",
        title="x",
        claims=(
            _claim(
                status=Status.INFERRED,
                anchors=(Anchor(EvidenceClass.RUNTIME, "run/42"),),
            ),
        ),
    )
    assert violations(manifest) == ()


def test_a_clean_manifest_reports_no_violations():
    manifest = Manifest(
        rfc="SPEC-1",
        title="x",
        claims=(
            _claim(
                id="spec:1.1",
                status=Status.CONFIRMED,
                anchors=(Anchor(EvidenceClass.RUNTIME, "run/42"),),
            ),
            _claim(
                id="spec:2.1",
                status=Status.INFERRED,
                anchors=(Anchor(EvidenceClass.PAPER, "10.1000/xyz"),),
            ),
        ),
    )
    assert violations(manifest) == ()
