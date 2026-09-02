"""Model-free substrate for reconstructed requirement manifests.

This package validates manifests produced by reconstruction agents running
outside the framework, weighs every claim against the evidence its anchors
point at, and reports the result. It makes no model calls and opens no
sockets.
"""

from .anchors import AnchorError, UnknownCommitError, verify
from .models import (
    Anchor,
    EvidenceClass,
    Intent,
    Manifest,
    RequirementClaim,
    RequirementClass,
    Status,
)
from .promotion import Violation, adjudicate, violations
from .report import ManifestReport, build, to_json, to_markdown, to_yaml
from .schema import SchemaError, dump, load

__all__ = [
    "Anchor",
    "AnchorError",
    "EvidenceClass",
    "Intent",
    "Manifest",
    "RequirementClass",
    "ManifestReport",
    "RequirementClaim",
    "SchemaError",
    "Status",
    "UnknownCommitError",
    "Violation",
    "adjudicate",
    "build",
    "dump",
    "load",
    "to_json",
    "to_markdown",
    "to_yaml",
    "verify",
    "violations",
]
