"""The deterministic citation gate over a prose draft's revision map.

The prose Internet-Draft is the agent's artifact; this gate checks only what
can be decided mechanically — that every revision tag exists, maps to a real
cluster in increasing order, pins an unedited checkpoint, cites only claims
that checkpoint holds, and that a "no normative change" revision really
changed nothing it cites. Prose style is deliberately not gated.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml

from ..schema import SchemaError, load
from .checkpoint import CHECKPOINT_FILE, MANIFEST_FILE, verify_checkpoint
from .questions import QuestionError, load_questions

#: A revision tag: the draft name, a dash, and a two-digit revision number.
REVISION_TAG = re.compile(r"^draft-.+-(?P<nn>\d\d)$")

#: A claim citation in prose: a backticked ``ai_rfc:<claim-id>`` token. The
#: backticks keep kramdown-rfc's own ``{{ }}`` machinery away from it.
CITATION = re.compile(r"`ai_rfc:([^`\s]+)`")


class GateError(ValueError):
    """Raised when the gate's inputs cannot be interpreted as written."""


@dataclass(frozen=True)
class RevisionEntry:
    """One row of ``revisions.yaml``: a tag and what it claims to freeze."""

    tag: str
    number: int
    cluster_id: str
    checkpoint_manifest_sha256: str
    normative_change: bool
    note: str


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a git command inside ``repo`` without raising on failure.

    ``check=True`` is deliberately not used, for the reason recorded on the
    ``anchors`` module's copy of this helper: the caller must distinguish
    result-shaped failures from error-shaped ones, with stderr in hand.
    """
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True
    )


def load_revisions(path: Path) -> tuple[RevisionEntry, ...]:
    """Read a revision map from disk, strictly.

    Args:
        path: Path to ``revisions.yaml``.

    Returns:
        The entries, ordered by revision number.

    Raises:
        GateError: If the document is malformed, a tag does not carry a
            two-digit revision suffix, or a field is missing or mistyped.
        OSError: If the file cannot be read.
    """
    document = yaml.safe_load(Path(path).read_text())
    if not isinstance(document, dict) or "revisions" not in document:
        raise GateError(f"{path}: top level must be a mapping with revisions")
    revisions = document["revisions"]
    if not isinstance(revisions, dict):
        raise GateError(f"{path}: revisions must be a mapping of tag to body")

    entries = []
    for tag, body in sorted(revisions.items()):
        matched = REVISION_TAG.match(str(tag))
        if not matched:
            raise GateError(f"{tag}: not a revision tag; expected draft-<name>-NN")
        if not isinstance(body, dict):
            raise GateError(f"{tag}: revision body must be a mapping")
        for required in ("cluster_id", "checkpoint_manifest_sha256"):
            if required not in body:
                raise GateError(f"{tag}: missing required field {required}")
        normative_change = body.get("normative_change")
        if not isinstance(normative_change, bool):
            raise GateError(
                f"{tag}: normative_change is {normative_change!r}; it must be "
                f"an explicit boolean — omitting it would let a revision "
                f"dodge the no-change check silently"
            )
        entries.append(
            RevisionEntry(
                tag=str(tag),
                number=int(matched.group("nn")),
                cluster_id=str(body["cluster_id"]),
                checkpoint_manifest_sha256=str(body["checkpoint_manifest_sha256"]),
                normative_change=normative_change,
                note=str(body.get("note", "")),
            )
        )
    entries.sort(key=lambda entry: entry.number)
    return tuple(entries)


def _cluster_ordinals(timeline_dir: Path) -> dict[str, int]:
    rows = (timeline_dir / "clusters.jsonl").read_text().splitlines()
    return {
        record["id"]: record["ordinal"] for record in (json.loads(row) for row in rows)
    }


def _repo_tags(draft_repo: Path) -> set[str]:
    result = _git(draft_repo, "tag", "-l")
    if result.returncode != 0:
        raise GateError(
            f"{draft_repo} is not a git repository: {result.stderr.strip()}"
        )
    return {tag for tag in result.stdout.splitlines() if tag}


def cited_ids(draft_repo: Path, tag: str) -> tuple[set[str], str | None]:
    """Return the claim ids cited at ``tag``, or a finding when unreadable.

    Args:
        draft_repo: The nested prose-draft git repository.
        tag: The revision tag to read.

    Returns:
        The cited claim ids and ``None``; or an empty set and the reason the tag
        could not be read.
    """
    listed = _git(draft_repo, "ls-tree", "--name-only", tag)
    if listed.returncode != 0:
        return set(), f"{tag}: could not list its tree: {listed.stderr.strip()}"
    drafts = [
        name
        for name in listed.stdout.splitlines()
        if name.startswith("draft-") and name.endswith(".md")
    ]
    if len(drafts) != 1:
        return set(), (
            f"{tag}: expected exactly one draft-*.md at the tag, "
            f"found {len(drafts)}"
        )
    shown = _git(draft_repo, "show", f"{tag}:{drafts[0]}")
    if shown.returncode != 0:
        return set(), f"{tag}: could not read {drafts[0]}: {shown.stderr.strip()}"
    return set(CITATION.findall(shown.stdout)), None


def run_gate(
    draft_repo: Path,
    timeline_dir: Path,
    checkpoints_dir: Path,
    questions_path: Path,
    revisions_path: Path,
) -> tuple[str, ...]:
    """Run every deterministic check over a draft and its revision map.

    Args:
        draft_repo: The nested prose-draft git repository.
        timeline_dir: Directory written by the timeline stage.
        checkpoints_dir: Root directory of the manifest checkpoints.
        questions_path: The question register.
        revisions_path: The revision map.

    Returns:
        One human-readable finding per broken check; empty when clean.

    Raises:
        GateError: If an input cannot be interpreted as written — malformed
            register, malformed revision map, or a path that is not a repo.
        OSError: If an input cannot be read.
    """
    entries = load_revisions(revisions_path)
    try:
        question_ids = {question.id for question in load_questions(questions_path)}
    except QuestionError as error:
        raise GateError(str(error)) from None
    ordinals = _cluster_ordinals(timeline_dir)
    tags = _repo_tags(draft_repo)

    findings: list[str] = []

    registered = {entry.tag for entry in entries}
    for entry in entries:
        if entry.tag not in tags:
            findings.append(
                f"{entry.tag}: registered in revisions.yaml but absent from "
                "the draft repository"
            )
    for tag in sorted(tags):
        if REVISION_TAG.match(tag) and tag not in registered:
            findings.append(
                f"{tag}: tagged in the draft repository but absent from "
                f"revisions.yaml"
            )

    previous_ordinal: int | None = None
    for entry in entries:
        ordinal = ordinals.get(entry.cluster_id)
        if ordinal is None:
            findings.append(
                f"{entry.tag}: no cluster {entry.cluster_id} in the timeline"
            )
            continue
        if previous_ordinal is not None and ordinal <= previous_ordinal:
            findings.append(
                f"{entry.tag}: cluster ordinal {ordinal} does not increase "
                f"over the previous revision's {previous_ordinal}"
            )
        previous_ordinal = ordinal

    claim_ids_by_tag: dict[str, set[str]] = {}
    for entry in entries:
        checkpoint_dir = checkpoints_dir / entry.cluster_id
        if not (checkpoint_dir / CHECKPOINT_FILE).exists():
            findings.append(
                f"{entry.tag}: no checkpoint for {entry.cluster_id} under "
                f"{checkpoints_dir}"
            )
            continue
        record = json.loads((checkpoint_dir / CHECKPOINT_FILE).read_text())
        if record["manifest_sha256"] != entry.checkpoint_manifest_sha256:
            findings.append(
                f"{entry.tag}: revisions.yaml pins manifest "
                f"{entry.checkpoint_manifest_sha256[:12]}… but the checkpoint "
                f"records {record['manifest_sha256'][:12]}…"
            )
        stale = verify_checkpoint(checkpoint_dir)
        if stale is not None:
            findings.append(f"{entry.tag}: {stale}")
            continue
        try:
            manifest = load(checkpoint_dir / MANIFEST_FILE)
        except SchemaError as error:
            findings.append(f"{entry.tag}: checkpoint manifest is unloadable: {error}")
            continue
        claim_ids_by_tag[entry.tag] = {claim.id for claim in manifest.claims}
        for claim in manifest.claims:
            if claim.question_id and claim.question_id not in question_ids:
                findings.append(
                    f"{entry.tag}: {claim.id} references {claim.question_id}, "
                    f"which is not in the question register"
                )

    cited_by_tag: dict[str, set[str]] = {}
    for entry in entries:
        if entry.tag not in tags:
            continue
        cited, problem = cited_ids(draft_repo, entry.tag)
        if problem is not None:
            findings.append(problem)
            continue
        cited_by_tag[entry.tag] = cited
        known = claim_ids_by_tag.get(entry.tag)
        if known is None:
            continue
        for claim_id in sorted(cited - known):
            findings.append(
                f"{entry.tag}: cites {claim_id}, which is not in its "
                f"checkpoint manifest"
            )

    previous_entry: RevisionEntry | None = None
    for entry in entries:
        if not entry.normative_change and entry.tag in cited_by_tag:
            previous_cited = (
                cited_by_tag.get(previous_entry.tag, set())
                if previous_entry is not None
                else set()
            )
            if cited_by_tag[entry.tag] != previous_cited:
                findings.append(
                    f"{entry.tag}: recorded as no normative change, but its "
                    f"cited claim set differs from the previous revision's"
                )
        previous_entry = entry

    deduped: list[str] = []
    for finding in findings:
        if finding not in deduped:
            deduped.append(finding)
    return tuple(deduped)
