from pathlib import Path

import pytest

from panther.plugins.services.testers.ai_rfc.models import (
    EvidenceClass,
    Intent,
    RequirementClass,
    Status,
)
from panther.plugins.services.testers.ai_rfc.schema import SchemaError, dump, load

pytestmark = pytest.mark.unit


def reload_from_text(text: str, tmp_path: Path):
    """Write ``text`` to a scratch file and load it back."""
    scratch = tmp_path / "round_trip.yaml"
    scratch.write_text(text)
    return load(scratch)


def test_base_only_manifest_loads_with_restrictive_defaults(base_only_manifest: Path):
    manifest = load(base_only_manifest)
    assert manifest.rfc == "SPEC-1"
    assert len(manifest.claims) == 1
    claim = manifest.claims[0]
    assert claim.status is Status.GAP
    assert claim.anchors == ()
    assert claim.intent is Intent.UNKNOWN
    assert claim.testable is True


def test_extended_manifest_preserves_every_field(extended_manifest: Path):
    manifest = load(extended_manifest)
    by_id = {claim.id: claim for claim in manifest.claims}

    first = by_id["spec:1.1"]
    assert first.status is Status.CONFIRMED
    assert first.req_class is RequirementClass.PROTOCOL_BEHAVIORAL
    assert first.intent is Intent.INTENDED
    assert first.signed_off_by == "dev-01"
    assert first.question_id == "q-007"
    assert len(first.anchors) == 2
    assert first.anchors[0].evidence_class is EvidenceClass.CODE
    assert first.anchors[0].line == 42

    second = by_id["spec:2.1"]
    assert second.intent is Intent.ACCIDENTAL
    assert second.anchors[0].evidence_class is EvidenceClass.ADR
    assert second.anchors[0].commit is None


def test_section_identifiers_are_strings(extended_manifest: Path):
    manifest = load(extended_manifest)
    for claim in manifest.claims:
        assert isinstance(claim.section, str)
        assert isinstance(claim.id, str)


def test_unquoted_section_is_rejected_loudly(unquoted_sections_manifest: Path):
    with pytest.raises(SchemaError) as excinfo:
        load(unquoted_sections_manifest)
    message = str(excinfo.value)
    assert "section" in message
    assert "quote" in message.lower()


@pytest.mark.parametrize(
    "field,written,coerced",
    [
        # YAML 1.1 reads these as bool and int. `signed_off_by` is the worse of
        # the two: `adjudicate` returns CONFIRMED for any truthy value, so an
        # unquoted `yes` promotes a claim to the strongest status with no signer
        # behind it, and `is_externally_checked` then inflates checked_fraction.
        ("signed_off_by", "yes", "bool"),
        ("signed_off_by", "true", "bool"),
        # A claim whose question-id is an int can never match the register,
        # which holds strings, so the gate reports a question that does exist
        # as missing.
        ("question-id", "7", "int"),
    ],
)
def test_unquoted_extended_identifiers_are_rejected_loudly(
    tmp_path: Path, field: str, written: str, coerced: str
):
    """Every field the schema gates must be gated, not just some of them.

    The README documents `signed_off_by` and `question-id` as strings, but they
    were absent from the checked set, so YAML coerced them silently.
    """
    document = (
        "rfc: test\n"
        "title: t\n"
        "requirements:\n"
        '  "spec:1":\n'
        "    text: t\n"
        '    section: "1"\n'
        "    level: MUST\n"
        "    layer: app\n"
        f"    {field}: {written}\n"
    )
    path = tmp_path / "manifest.yaml"
    path.write_text(document)

    with pytest.raises(SchemaError) as excinfo:
        load(path)
    message = str(excinfo.value)
    assert field in message
    assert coerced in message
    assert "quote" in message.lower()


def test_load_of_dump_is_a_fixed_point(extended_manifest: Path, tmp_path: Path):
    manifest = load(extended_manifest)
    assert reload_from_text(dump(manifest), tmp_path) == manifest


def test_dump_is_byte_stable(extended_manifest: Path, tmp_path: Path):
    manifest = load(extended_manifest)
    once = dump(manifest)
    twice = dump(reload_from_text(once, tmp_path))
    assert once == twice


def test_anchor_missing_evidence_class_is_a_schema_error(tmp_path: Path):
    path = tmp_path / "bad.yaml"
    path.write_text(
        "rfc: SPEC-1\n"
        "title: 'x'\n"
        "requirements:\n"
        "  'spec:1.1':\n"
        "    text: 'x'\n"
        "    section: '1.1'\n"
        "    level: MUST\n"
        "    layer: timing\n"
        "    anchors:\n"
        "      - locator: src/a.py\n"
    )
    with pytest.raises(SchemaError) as excinfo:
        load(path)
    assert "evidence_class" in str(excinfo.value)


def test_unknown_status_value_is_a_schema_error(tmp_path: Path):
    path = tmp_path / "bad_status.yaml"
    path.write_text(
        "rfc: SPEC-1\n"
        "title: 'x'\n"
        "requirements:\n"
        "  'spec:1.1':\n"
        "    text: 'x'\n"
        "    section: '1.1'\n"
        "    level: MUST\n"
        "    layer: timing\n"
        "    status: probably\n"
    )
    with pytest.raises(SchemaError) as excinfo:
        load(path)
    assert "probably" in str(excinfo.value)


def test_anchor_line_sha256_round_trips(tmp_path: Path):
    digest = "ab" * 32
    manifest = reload_from_text(
        "rfc: SPEC-1\n"
        "title: 'x'\n"
        "requirements:\n"
        "  'spec:1.1':\n"
        "    text: 'x'\n"
        "    section: '1.1'\n"
        "    level: MUST\n"
        "    layer: timing\n"
        "    anchors:\n"
        "      - evidence_class: code\n"
        "        locator: src/a.py\n"
        f"        commit: '{'0' * 40}'\n"
        "        line: 3\n"
        f"        line_sha256: '{digest}'\n",
        tmp_path,
    )
    anchor = manifest.claims[0].anchors[0]
    assert anchor.line_sha256 == digest
    assert f"line_sha256: {digest}" in dump(manifest)


def test_anchor_line_sha256_without_line_is_rejected(tmp_path: Path):
    with pytest.raises(SchemaError) as excinfo:
        reload_from_text(
            "rfc: SPEC-1\n"
            "title: 'x'\n"
            "requirements:\n"
            "  'spec:1.1':\n"
            "    text: 'x'\n"
            "    section: '1.1'\n"
            "    level: MUST\n"
            "    layer: timing\n"
            "    anchors:\n"
            "      - evidence_class: code\n"
            "        locator: src/a.py\n"
            f"        line_sha256: '{'ab' * 32}'\n",
            tmp_path,
        )
    assert "line_sha256" in str(excinfo.value)


def test_a_whitespace_only_signer_is_refused(tmp_path: Path):
    """`signed_off_by` is the strongest lever in the promotion rule.

    Blanks are not names, and `schema` refuses a malformed document rather than
    repairing it — treating whitespace as absent would silently downgrade a
    claim the author believed they had signed.
    """
    path = tmp_path / "blank_signer.yaml"
    path.write_text(
        "rfc: SPEC-1\n"
        "title: 'x'\n"
        "requirements:\n"
        "  'spec:1.1':\n"
        "    text: 'x'\n"
        "    section: '1.1'\n"
        "    level: MUST\n"
        "    layer: timing\n"
        "    signed_off_by: '   '\n"
    )
    with pytest.raises(SchemaError) as excinfo:
        load(path)
    assert "signed_off_by" in str(excinfo.value)


def test_a_duplicated_requirement_id_is_refused(tmp_path: Path):
    """Two claims, one id: safe_load keeps the last and the count under-reports."""
    path = tmp_path / "duplicate_id.yaml"
    path.write_text(
        "rfc: SPEC-1\n"
        "title: 'x'\n"
        "requirements:\n"
        "  'spec:1.1':\n"
        "    text: first\n"
        "    section: '1.1'\n"
        "    level: MUST\n"
        "    layer: timing\n"
        "  'spec:1.1':\n"
        "    text: second\n"
        "    section: '1.1'\n"
        "    level: MUST\n"
        "    layer: timing\n"
    )
    with pytest.raises(SchemaError) as excinfo:
        load(path)
    assert "spec:1.1" in str(excinfo.value)
