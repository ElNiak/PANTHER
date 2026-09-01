import json
from pathlib import Path

import pytest

from panther.plugins.services.testers.a_rfc.models import (
    Anchor,
    EvidenceClass,
    Intent,
    Manifest,
    RequirementClaim,
    RequirementClass,
    Status,
)
from panther.plugins.services.testers.a_rfc.report import (
    build,
    to_json,
    to_markdown,
    to_yaml,
)

pytestmark = pytest.mark.unit


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


@pytest.fixture
def mixed_manifest():
    return Manifest(
        rfc="SPEC-1",
        title="An Example Specification",
        claims=(
            _claim(
                id="spec:1.1",
                status=Status.CONFIRMED,
                anchors=(Anchor(EvidenceClass.RUNTIME, "run/42"),),
            ),
            _claim(
                id="spec:2.1",
                text="The system tolerates a duplicate identifier.",
                intent=Intent.ACCIDENTAL,
                status=Status.INFERRED,
                anchors=(Anchor(EvidenceClass.PAPER, "10.1000/xyz"),),
            ),
            _claim(
                id="spec:3.1",
                text="The system rejects an oversized frame.",
                status=Status.CONFIRMED,
                anchors=(Anchor(EvidenceClass.ADR, "adr/0007.md"),),
            ),
        ),
    )


def test_report_counts_by_status(mixed_manifest):
    report = build(mixed_manifest)
    assert report.manifest.count_by_status == {
        "gap": 0,
        "inferred": 1,
        "confirmed": 2,
    }


def test_report_finds_the_overstated_claim(mixed_manifest):
    report = build(mixed_manifest)
    assert [violation.claim_id for violation in report.violations] == ["spec:3.1"]


def test_json_carries_derived_metrics(mixed_manifest):
    payload = json.loads(to_json(build(mixed_manifest)))
    assert payload["count_by_status"]["confirmed"] == 2
    assert "checked_fraction_by_req_class" in payload
    assert payload["checked_fraction_by_req_class"]["protocol-behavioral"] == 0.5


def test_json_is_byte_stable(mixed_manifest):
    report = build(mixed_manifest)
    assert to_json(report) == to_json(report)


def test_markdown_excludes_accidental_claims_from_the_normative_section(
    mixed_manifest,
):
    markdown = to_markdown(build(mixed_manifest))
    normative, _, descriptive = markdown.partition("## Descriptive")
    assert "spec:1.1" in normative
    assert "spec:2.1" not in normative
    assert "spec:2.1" in descriptive


def test_markdown_names_every_violation(mixed_manifest):
    markdown = to_markdown(build(mixed_manifest))
    assert "spec:3.1" in markdown
    assert "supports only inferred" in markdown


def test_yaml_round_trips_as_a_mapping(mixed_manifest):
    import yaml

    payload = yaml.safe_load(to_yaml(build(mixed_manifest)))
    assert payload["rfc"] == "SPEC-1"
    assert payload["count_by_status"]["confirmed"] == 2


def test_unverified_anchors_are_listed_when_a_repo_is_given(
    mixed_manifest, fixture_repo: Path
):
    manifest = Manifest(
        rfc="SPEC-1",
        title="x",
        claims=(
            _claim(
                id="spec:9.1",
                anchors=(
                    Anchor(
                        EvidenceClass.CODE,
                        "does_not_exist.txt",
                        commit=(fixture_repo / "FIRST_SHA").read_text().strip(),
                    ),
                ),
            ),
        ),
    )
    report = build(manifest, repo=fixture_repo)
    assert len(report.unverified) == 1
    assert report.unverified[0].startswith("spec:9.1: does_not_exist.txt (")
    assert "does not exist at" in report.unverified[0]


def test_no_repo_means_no_anchor_verification_attempted(mixed_manifest):
    assert build(mixed_manifest).unverified == ()


def test_payload_reports_supported_status_beside_stored():
    claim = _claim(
        anchors=(
            Anchor(EvidenceClass.CODE, "a.py", commit="0" * 40),
            Anchor(EvidenceClass.PAPER, "10.1000/xyz"),
        ),
        status=Status.GAP,
    )
    payload = json.loads(to_json(build(Manifest(rfc="S", title="t", claims=(claim,)))))
    assert payload["claims"] == [
        {
            "id": "spec:1.1",
            "stored": "gap",
            "supported": "confirmed",
            "promotable": True,
        }
    ]
    assert payload["promotable_count"] == 1


def test_stored_at_supported_level_is_not_promotable(mixed_manifest):
    payload = json.loads(to_json(build(mixed_manifest)))
    by_id = {entry["id"]: entry for entry in payload["claims"]}
    assert by_id["spec:1.1"]["promotable"] is False
    assert by_id["spec:3.1"]["supported"] == "inferred"
    assert by_id["spec:3.1"]["promotable"] is False
    assert payload["promotable_count"] == 0


def test_markdown_lists_promotable_claims():
    claim = _claim(
        anchors=(
            Anchor(EvidenceClass.CODE, "a.py", commit="0" * 40),
            Anchor(EvidenceClass.PAPER, "10.1000/xyz"),
        ),
        status=Status.GAP,
    )
    markdown = to_markdown(build(Manifest(rfc="S", title="t", claims=(claim,))))
    assert "## Promotable" in markdown
    promotable_section = markdown.split("## Promotable")[1].split("##")[0]
    assert "spec:1.1" in promotable_section
    assert "confirmed" in promotable_section


def test_markdown_carries_the_externally_checked_fraction(mixed_manifest):
    markdown = to_markdown(build(mixed_manifest))
    assert "## Externally checked fraction" in markdown
    section = markdown.split("## Externally checked fraction")[1].split("##")[0]
    assert "protocol-behavioral" in section
    assert "0.50" in section


def test_markdown_distinguishes_an_unchecked_class_from_an_empty_one(mixed_manifest):
    """A 0.0 fraction and "no confirmed claims here" must not read alike.

    ``checked_fraction_by_req_class`` reports 0.0 for both, which is the one
    ambiguity that makes the metric misreadable on its own.
    """
    markdown = to_markdown(build(mixed_manifest))
    section = markdown.split("## Externally checked fraction")[1].split("##")[0]
    lines = {
        line.lstrip("- ").split(":")[0].strip(): line
        for line in section.splitlines()
        if line.startswith("- ")
    }
    assert "2 confirmed" in lines["protocol-behavioral"]
    assert "no confirmed claims" in lines["algorithmic"]
    assert "0.0" not in lines["algorithmic"]


def test_report_records_whether_anchors_were_checked(mixed_manifest, fixture_repo):
    assert build(mixed_manifest).anchors_checked is False
    assert build(mixed_manifest, repo=fixture_repo).anchors_checked is True


def test_report_counts_the_anchors_a_repo_would_have_verified():
    claim = _claim(
        anchors=(
            Anchor(EvidenceClass.CODE, "a.py", commit="0" * 40),
            Anchor(EvidenceClass.PAPER, "10.1000/xyz"),
        ),
    )
    report = build(Manifest(rfc="S", title="t", claims=(claim,)))
    assert report.verifiable_anchor_count == 1


def test_markdown_says_not_checked_rather_than_none_failed(mixed_manifest):
    """Without a repo the section must not read as a clean bill of health."""
    section = to_markdown(build(mixed_manifest)).split("## Unverified anchors")[1]
    assert "Not checked" in section
    assert "none failed" not in section


def test_markdown_says_none_failed_when_a_repo_verified_every_anchor(fixture_repo):
    manifest = Manifest(
        rfc="SPEC-1",
        title="x",
        claims=(_claim(id="spec:9.1", anchors=(Anchor(EvidenceClass.ADR, "a.md"),)),),
    )
    section = to_markdown(build(manifest, repo=fixture_repo)).split(
        "## Unverified anchors"
    )[1]
    assert "None failed" in section
    assert "Not checked" not in section
