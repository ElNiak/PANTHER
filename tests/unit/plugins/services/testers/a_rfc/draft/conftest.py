import json
from pathlib import Path

import pytest

from panther.plugins.services.testers.a_rfc.timeline.build import build_timeline
from panther.plugins.services.testers.a_rfc.timeline.corpus import (
    find_tip,
    read_commits,
)
from panther.plugins.services.testers.a_rfc.timeline.store import write_timeline


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
