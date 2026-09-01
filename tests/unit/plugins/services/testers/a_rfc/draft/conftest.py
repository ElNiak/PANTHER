import json
import subprocess
from pathlib import Path

import pytest

from panther.plugins.services.testers.a_rfc.draft.checkpoint import write_checkpoint
from panther.plugins.services.testers.a_rfc.timeline.build import build_timeline
from panther.plugins.services.testers.a_rfc.timeline.corpus import (
    find_tip,
    read_commits,
)
from panther.plugins.services.testers.a_rfc.timeline.store import (
    read_clusters,
    write_timeline,
)


def _record(sha: str, parents: list[str]) -> str:
    return json.dumps(
        {
            "sha": sha,
            "parents": parents,
            "author_name": "a",
            "author_email": "a@a",
            "authored_at": "2026-01-01T00:00:00+00:00",
            "committed_at": "2026-01-01T00:00:00+00:00",
            "subject": f"s {sha}",
            "body": "",
            "is_merge": len(parents) > 1,
            "file_count": 1,
            "files_recorded": 1,
            "files_truncated": False,
        },
        sort_keys=True,
    )


@pytest.fixture
def timeline_dir(tmp_path: Path) -> Path:
    """A two-cluster timeline (epoch then pr) built through the shipped code."""
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    records = [
        _record("aa", []),
        _record("ff", ["aa"]),
        _record("dd", ["aa"]),
        _record("mm", ["dd", "ff"]),
    ]
    (corpus / "commits.jsonl").write_text("\n".join(records) + "\n")
    (corpus / "files.jsonl").write_text("")
    commits = read_commits(corpus)
    out = tmp_path / "timeline"
    write_timeline(build_timeline(commits), find_tip(commits), corpus, out)
    return out


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def _manifest_text(with_second_claim: bool, question_id: str = "q-001") -> str:
    text = (
        "rfc: SPEC-1\n"
        "title: 'A reconstructed specification'\n"
        "requirements:\n"
        "  'spec:1.1':\n"
        "    text: 'The system does the thing.'\n"
        "    section: '1.1'\n"
        "    level: MUST\n"
        "    layer: behaviour\n"
        "    anchors:\n"
        "      - evidence_class: code\n"
        "        locator: src/a.py\n"
        f"        commit: '{'0' * 40}'\n"
    )
    if with_second_claim:
        text += (
            "  'spec:2.1':\n"
            "    text: 'The system also does this.'\n"
            "    section: '2.1'\n"
            "    level: SHOULD\n"
            "    layer: behaviour\n"
            f"    question-id: {question_id}\n"
        )
    return text


def _checkpoint_sha(checkpoint_dir: Path) -> str:
    record = json.loads((checkpoint_dir / "checkpoint.json").read_text())
    return record["manifest_sha256"]


@pytest.fixture
def draft_workspace(tmp_path: Path, timeline_dir: Path) -> dict[str, Path]:
    """A gate-clean workspace: draft repo, checkpoints, questions, revisions."""
    clusters = read_clusters(timeline_dir)
    epoch_id, pr_id = clusters[0]["id"], clusters[1]["id"]

    first_manifest = tmp_path / "m1.yaml"
    first_manifest.write_text(_manifest_text(with_second_claim=False))
    second_manifest = tmp_path / "m2.yaml"
    second_manifest.write_text(_manifest_text(with_second_claim=True))
    checkpoints = tmp_path / "checkpoints"
    first_checkpoint = write_checkpoint(
        first_manifest, timeline_dir, epoch_id, checkpoints
    )
    second_checkpoint = write_checkpoint(
        second_manifest, timeline_dir, pr_id, checkpoints
    )

    repo = tmp_path / "draft"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.email", "t@t")
    git(repo, "config", "user.name", "t")
    draft_file = repo / "draft-test-spec.md"
    draft_file.write_text("# Spec\n\nThe system does the thing. `a_rfc:spec:1.1`\n")
    git(repo, "add", "draft-test-spec.md")
    git(repo, "commit", "-m", "revision 00")
    git(repo, "tag", "draft-test-spec-00")
    draft_file.write_text(
        draft_file.read_text() + "\nIt also does this. `a_rfc:spec:2.1`\n"
    )
    git(repo, "add", "draft-test-spec.md")
    git(repo, "commit", "-m", "revision 01")
    git(repo, "tag", "draft-test-spec-01")

    questions = tmp_path / "questions.yaml"
    questions.write_text(
        "questions:\n"
        "  q-001:\n"
        "    question: 'Is the second behaviour deliberate?'\n"
        "    claim_ids: ['spec:2.1']\n"
        "    status: open\n"
        "    asked_at: '2026-08-25'\n"
    )

    revisions = tmp_path / "revisions.yaml"
    revisions.write_text(
        "revisions:\n"
        "  draft-test-spec-00:\n"
        f"    cluster_id: {epoch_id}\n"
        f"    checkpoint_manifest_sha256: {_checkpoint_sha(first_checkpoint)}\n"
        "    normative_change: true\n"
        "    note: 'initial reconstruction'\n"
        "  draft-test-spec-01:\n"
        f"    cluster_id: {pr_id}\n"
        f"    checkpoint_manifest_sha256: {_checkpoint_sha(second_checkpoint)}\n"
        "    normative_change: true\n"
        "    note: 'adds the second behaviour'\n"
    )

    return {
        "repo": repo,
        "timeline": timeline_dir,
        "checkpoints": checkpoints,
        "questions": questions,
        "revisions": revisions,
    }


@pytest.fixture
def manifest_path(tmp_path: Path) -> Path:
    path = tmp_path / "manifest.yaml"
    path.write_text(
        "rfc: SPEC-1\n"
        "title: 'A reconstructed specification'\n"
        "requirements:\n"
        "  'spec:1.1':\n"
        "    text: 'The system does the thing.'\n"
        "    section: '1.1'\n"
        "    level: MUST\n"
        "    layer: behaviour\n"
        "    anchors:\n"
        "      - evidence_class: code\n"
        "        locator: src/a.py\n"
        f"        commit: '{'0' * 40}'\n"
        "      - evidence_class: paper\n"
        "        locator: 10.1000/xyz\n"
        "  'spec:2.1':\n"
        "    text: 'The system also does this.'\n"
        "    section: '2.1'\n"
        "    level: SHOULD\n"
        "    layer: behaviour\n"
        "    question-id: q-001\n"
    )
    return path


@pytest.fixture
def sparse_workspace(tmp_path: Path, timeline_dir: Path) -> dict[str, Path]:
    """A workspace of two clusters with only the first checkpointed.

    Laid out so ``tmp_path`` itself is a valid workspace root: the completeness
    verb derives every input from it.
    """
    epoch_id = read_clusters(timeline_dir)[0]["id"]

    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(_manifest_text(with_second_claim=False))
    checkpoints = tmp_path / "checkpoints"
    checkpoint = write_checkpoint(manifest, timeline_dir, epoch_id, checkpoints)

    repo = tmp_path / "draft"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.email", "t@t")
    git(repo, "config", "user.name", "t")
    (repo / "draft-test-spec.md").write_text("# Spec\n\nNo citations yet.\n")
    git(repo, "add", "draft-test-spec.md")
    git(repo, "commit", "-m", "revision 00")
    git(repo, "tag", "draft-test-spec-00")

    revisions = tmp_path / "revisions.yaml"
    revisions.write_text(
        "revisions:\n"
        "  draft-test-spec-00:\n"
        f"    cluster_id: {epoch_id}\n"
        f"    checkpoint_manifest_sha256: {_checkpoint_sha(checkpoint)}\n"
        "    normative_change: true\n"
        "    note: 'initial reconstruction'\n"
    )
    return {
        "root": tmp_path,
        "repo": repo,
        "timeline": timeline_dir,
        "checkpoints": checkpoints,
        "manifest": manifest,
        "revisions": revisions,
    }
