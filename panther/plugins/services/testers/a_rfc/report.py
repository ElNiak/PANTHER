"""Aggregate a manifest into a report and emit it.

Serialisation injects derived values explicitly: ``dataclasses.asdict`` drops
``@property`` values, and the per-stratum checked fractions are exactly the
numbers a reader wants.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import yaml

from .anchors import AnchorError, verify_detailed
from .models import COMMIT_REQUIRED_FOR, STATUS_RANK, Intent, Manifest
from .promotion import Violation, adjudicate, violations


@dataclass(frozen=True)
class Report:
    """A manifest together with everything checking it revealed."""

    manifest: Manifest
    violations: tuple[Violation, ...]
    unverified: tuple[str, ...]


def build(manifest: Manifest, repo: Path | None = None) -> Report:
    """Check a manifest and collect the findings.

    Args:
        manifest: The manifest to check.
        repo: Optional clone against which repository anchors are verified. When
            omitted, no anchor verification is attempted and ``unverified`` is
            empty — an absence of findings, not a clean bill of health.

    Returns:
        The assembled report.
    """
    unverified: list[str] = []
    if repo is not None:
        for claim in manifest.claims:
            for anchor in claim.anchors:
                if anchor.evidence_class not in COMMIT_REQUIRED_FOR:
                    continue
                try:
                    reason = verify_detailed(anchor, repo)
                except AnchorError as error:
                    reason = str(error)
                if reason is not None:
                    unverified.append(f"{claim.id}: {anchor.locator} ({reason})")

    return Report(
        manifest=manifest,
        violations=violations(manifest),
        unverified=tuple(unverified),
    )


def _adjudicated(report: Report) -> list[dict]:
    """Pair every claim's stored status with what its evidence supports."""
    entries = []
    for claim in report.manifest.claims:
        supported = adjudicate(claim)
        entries.append(
            {
                "id": claim.id,
                "stored": claim.status.value,
                "supported": supported.value,
                "promotable": STATUS_RANK[supported] > STATUS_RANK[claim.status],
            }
        )
    return entries


def _payload(report: Report) -> dict:
    """Build the serialisable view, with derived metrics injected explicitly."""
    claims = _adjudicated(report)
    return {
        "rfc": report.manifest.rfc,
        "title": report.manifest.title,
        "claim_count": len(report.manifest.claims),
        "count_by_status": report.manifest.count_by_status,
        "checked_fraction_by_req_class": (
            report.manifest.checked_fraction_by_req_class
        ),
        "claims": claims,
        "promotable_count": sum(1 for entry in claims if entry["promotable"]),
        "violations": [
            {
                "claim_id": violation.claim_id,
                "stored": violation.stored.value,
                "supported": violation.supported.value,
                "reason": violation.reason,
            }
            for violation in report.violations
        ],
        "unverified_anchors": list(report.unverified),
    }


def to_json(report: Report) -> str:
    """Emit the report as JSON, deterministically."""
    return json.dumps(_payload(report), sort_keys=True, indent=2) + "\n"


def to_yaml(report: Report) -> str:
    """Emit the report as YAML, deterministically."""
    return yaml.safe_dump(_payload(report), sort_keys=True, default_flow_style=False)


def to_markdown(report: Report) -> str:
    """Emit the report as Markdown.

    Claims marked ``intent: accidental`` appear only in the descriptive
    section. Documented behaviour that was never meant is not promoted into
    normative prose, so the specification does not canonize bugs.
    """
    manifest = report.manifest
    lines = [
        f"# {manifest.title}",
        "",
        f"Identifier: `{manifest.rfc}`  ",
        f"Claims: {len(manifest.claims)}",
        "",
        "## Status counts",
        "",
    ]
    for status, count in sorted(manifest.count_by_status.items()):
        lines.append(f"- {status}: {count}")

    lines += ["", "## Promotable", ""]
    promotable = [entry for entry in _adjudicated(report) if entry["promotable"]]
    if not promotable:
        lines.append("_None._")
    for entry in promotable:
        lines.append(
            f"- **{entry['id']}** — stored {entry['stored']}, "
            f"evidence supports {entry['supported']}"
        )

    lines += ["", "## Normative", ""]
    normative = [c for c in manifest.claims if c.intent is not Intent.ACCIDENTAL]
    if not normative:
        lines.append("_None._")
    for claim in normative:
        lines.append(
            f"- **{claim.id}** ({claim.level}, {claim.status.value}) " f"— {claim.text}"
        )

    lines += [
        "",
        "## Descriptive",
        "",
        "_Behaviour recorded as accidental. Excluded from normative prose._",
        "",
    ]
    accidental = [c for c in manifest.claims if c.intent is Intent.ACCIDENTAL]
    if not accidental:
        lines.append("_None._")
    for claim in accidental:
        lines.append(f"- **{claim.id}** ({claim.status.value}) — {claim.text}")

    lines += ["", "## Promotion violations", ""]
    if not report.violations:
        lines.append("_None._")
    for violation in report.violations:
        lines.append(f"- **{violation.claim_id}** — {violation.reason}")

    lines += ["", "## Unverified anchors", ""]
    if not report.unverified:
        lines.append("_None checked, or none failed._")
    for item in report.unverified:
        lines.append(f"- {item}")

    return "\n".join(lines) + "\n"
