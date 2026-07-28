from pathlib import Path

import pytest

from panther.plugins.services.testers.a_rfc.models import (
    EvidenceClass,
    Intent,
    ReqClass,
    Status,
)
from panther.plugins.services.testers.a_rfc.schema import SchemaError, dump, load

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
    assert first.req_class is ReqClass.PROTOCOL_BEHAVIORAL
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
