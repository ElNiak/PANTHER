"""Fixtures for the claim-manifest tests.

Every fixture builds its own files in ``tmp_path``. Nothing here reads the
repository, reaches the network, or calls a model.
"""

import subprocess
from pathlib import Path

import pytest

BASE_ONLY = """\
rfc: SPEC-1
title: 'An Example Specification'
requirements:
  'spec:1.1':
    text: >-
      The system responds within the configured interval.
    section: '1.1'
    level: MUST
    layer: timing
    testable: true
"""

EXTENDED = """\
rfc: SPEC-1
title: 'An Example Specification'
requirements:
  'spec:1.1':
    text: >-
      The system responds within the configured interval.
    section: '1.1'
    level: MUST
    layer: timing
    testable: true
    status: confirmed
    req_class: protocol-behavioral
    intent: intended
    signed_off_by: dev-01
    question-id: q-007
    anchors:
      - evidence_class: code
        locator: src/timer.py
        commit: '00112233445566778899aabbccddeeff00112233'
        line: 42
      - evidence_class: paper
        locator: 10.1000/xyz
  'spec:2.1':
    text: >-
      The system records each rejection.
    section: '2.1'
    level: SHOULD
    layer: logging
    status: inferred
    req_class: data-model
    intent: accidental
    anchors:
      - evidence_class: adr
        locator: adr/0007.md
"""

UNQUOTED_SECTIONS = """\
rfc: SPEC-1
title: 'An Example Specification'
requirements:
  'spec:4.2':
    text: >-
      A requirement whose section number was left unquoted.
    section: 4.2
    level: MUST
    layer: timing
"""


@pytest.fixture
def base_only_manifest(tmp_path: Path) -> Path:
    """A manifest carrying none of the extended fields."""
    path = tmp_path / "base_only.yaml"
    path.write_text(BASE_ONLY)
    return path


@pytest.fixture
def extended_manifest(tmp_path: Path) -> Path:
    """A manifest exercising every extended field."""
    path = tmp_path / "extended.yaml"
    path.write_text(EXTENDED)
    return path


@pytest.fixture
def unquoted_sections_manifest(tmp_path: Path) -> Path:
    """A manifest that will lose data to YAML type coercion."""
    path = tmp_path / "unquoted.yaml"
    path.write_text(UNQUOTED_SECTIONS)
    return path


@pytest.fixture
def fixture_repo(tmp_path: Path) -> Path:
    """A two-commit repository whose second commit adds a file.

    Returns:
        Path to the repository. ``(repo / "FIRST_SHA").read_text()`` holds the
        first commit's hash, so tests can pin an anchor to a commit at which a
        later file does not yet exist.
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    def run(*args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    run("init", "-q", "-b", "main")
    run("config", "user.email", "fixture@example.invalid")
    run("config", "user.name", "Fixture Author")

    (repo / "first.txt").write_text("first\n")
    run("add", "first.txt")
    run("commit", "-q", "-m", "first")
    first_sha = run("rev-parse", "HEAD")

    (repo / "second.txt").write_text("second\n")
    run("add", "second.txt")
    run("commit", "-q", "-m", "second")

    (repo / "FIRST_SHA").write_text(first_sha)
    return repo
