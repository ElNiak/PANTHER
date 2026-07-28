"""Load and emit claim manifests.

The only module here that touches YAML. It is deliberately strict: a value it
cannot interpret raises rather than taking a permissive default, because a
manifest that loads wrong is far worse than one that fails to load.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import (
    Anchor,
    EvidenceClass,
    Intent,
    Manifest,
    ReqClass,
    RequirementClaim,
    Status,
)

_STRING_FIELDS = ("section", "id")


class SchemaError(ValueError):
    """Raised when a manifest cannot be interpreted as written."""


def _enum(enum_cls: type, raw: Any, field: str, claim_id: str):
    """Resolve ``raw`` to a member of ``enum_cls`` or raise.

    Args:
        enum_cls: The closed vocabulary to resolve against.
        raw: The value read from the document.
        field: Field name, for the error message.
        claim_id: Requirement identifier, for the error message.

    Returns:
        The matching enumeration member.

    Raises:
        SchemaError: If ``raw`` is not one of the permitted values.
    """
    try:
        return enum_cls(raw)
    except ValueError:
        permitted = ", ".join(member.value for member in enum_cls)
        raise SchemaError(
            f"{claim_id}: {field} is {raw!r}; permitted values are {permitted}"
        ) from None


def _anchor(raw: Any, claim_id: str) -> Anchor:
    """Build an anchor from a mapping, requiring its evidence class."""
    if not isinstance(raw, dict):
        raise SchemaError(f"{claim_id}: each anchor must be a mapping, got {raw!r}")
    if "evidence_class" not in raw:
        raise SchemaError(f"{claim_id}: anchor is missing evidence_class")
    if "locator" not in raw:
        raise SchemaError(f"{claim_id}: anchor is missing locator")
    line = raw.get("line")
    return Anchor(
        evidence_class=_enum(
            EvidenceClass, raw["evidence_class"], "evidence_class", claim_id
        ),
        locator=str(raw["locator"]),
        commit=None if raw.get("commit") is None else str(raw["commit"]),
        line=None if line is None else int(line),
    )


def _claim(claim_id: Any, raw: Any) -> RequirementClaim:
    """Build one claim, defaulting every extended field restrictively."""
    if not isinstance(raw, dict):
        raise SchemaError(f"{claim_id}: requirement body must be a mapping")

    for field in _STRING_FIELDS:
        value = claim_id if field == "id" else raw.get(field)
        if value is not None and not isinstance(value, str):
            raise SchemaError(
                f"{claim_id}: {field} is {value!r} ({type(value).__name__}); "
                f"quote it in the document so YAML does not coerce its type"
            )

    for required in ("text", "section", "level", "layer"):
        if required not in raw:
            raise SchemaError(f"{claim_id}: missing required field {required}")

    return RequirementClaim(
        id=claim_id,
        text=str(raw["text"]).strip(),
        section=raw["section"],
        level=str(raw["level"]),
        layer=str(raw["layer"]),
        req_class=_enum(
            ReqClass,
            raw.get("req_class", ReqClass.PROTOCOL_BEHAVIORAL.value),
            "req_class",
            claim_id,
        ),
        intent=_enum(
            Intent, raw.get("intent", Intent.UNKNOWN.value), "intent", claim_id
        ),
        anchors=tuple(_anchor(item, claim_id) for item in raw.get("anchors", ())),
        status=_enum(Status, raw.get("status", Status.GAP.value), "status", claim_id),
        signed_off_by=raw.get("signed_off_by"),
        question_id=raw.get("question-id"),
        testable=raw.get("testable"),
    )


def load(path: Path) -> Manifest:
    """Read a manifest from disk.

    A manifest carrying none of the extended fields loads successfully, with
    every extended field taking its most restrictive default.

    Args:
        path: Path to a YAML manifest.

    Returns:
        The parsed manifest, with claims ordered by identifier.

    Raises:
        SchemaError: If the document is malformed, carries an unknown value in
            a closed vocabulary, or leaves an identifier unquoted.
    """
    document = yaml.safe_load(Path(path).read_text())
    if not isinstance(document, dict):
        raise SchemaError(f"{path}: top level must be a mapping")
    for required in ("rfc", "title", "requirements"):
        if required not in document:
            raise SchemaError(f"{path}: missing required field {required}")
    requirements = document["requirements"]
    if not isinstance(requirements, dict):
        raise SchemaError(f"{path}: requirements must be a mapping of id to body")

    claims = tuple(
        _claim(claim_id, body) for claim_id, body in sorted(requirements.items())
    )
    return Manifest(
        rfc=str(document["rfc"]), title=str(document["title"]), claims=claims
    )


def _anchor_to_dict(anchor: Anchor) -> dict[str, Any]:
    """Render an anchor, omitting fields that are unset."""
    rendered: dict[str, Any] = {
        "evidence_class": anchor.evidence_class.value,
        "locator": anchor.locator,
    }
    if anchor.commit is not None:
        rendered["commit"] = anchor.commit
    if anchor.line is not None:
        rendered["line"] = anchor.line
    return rendered


def dump(manifest: Manifest) -> str:
    """Emit a manifest as YAML.

    Output is deterministic: two runs over equal input produce equal bytes,
    which is what makes an emitted manifest citable.

    Args:
        manifest: The manifest to emit.

    Returns:
        The YAML document as text.
    """
    requirements: dict[str, Any] = {}
    for claim in manifest.claims:
        body: dict[str, Any] = {
            "text": claim.text,
            "section": claim.section,
            "level": claim.level,
            "layer": claim.layer,
            "status": claim.status.value,
            "req_class": claim.req_class.value,
            "intent": claim.intent.value,
        }
        if claim.testable is not None:
            body["testable"] = claim.testable
        if claim.signed_off_by is not None:
            body["signed_off_by"] = claim.signed_off_by
        if claim.question_id is not None:
            body["question-id"] = claim.question_id
        if claim.anchors:
            body["anchors"] = [_anchor_to_dict(anchor) for anchor in claim.anchors]
        requirements[claim.id] = body

    return yaml.safe_dump(
        {"rfc": manifest.rfc, "title": manifest.title, "requirements": requirements},
        sort_keys=True,
        default_flow_style=False,
        allow_unicode=True,
        width=88,
    )
