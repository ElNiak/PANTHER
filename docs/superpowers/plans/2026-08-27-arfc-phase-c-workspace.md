# Pristine Experiment Workspaces Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `experiment/workspace.py` — the module that prepares a reconstruction workspace once, pre-seeds every cluster outside the experiment window, digest-manifests the result, and hands each run a verified private copy.

**Architecture:** A *pristine* workspace is the deterministic output of the `a_rfc` substrate stages (corpus, timeline, views) plus the window pre-seeding of D27, sealed with a SHA-256 manifest. Nothing here mutates a substrate artifact: clusters outside the window are marked processed by writing checkpoints of the workspace manifest, each carrying a `harness.json` sidecar the analysis excludes. Every run gets a `shutil.copytree` copy whose digest and nested-repository HEADs are verified before the run starts, so a run can never inherit another run's edits. The substrate is reached through a lazy import helper exactly as `ai_rfc_server.testing.build_workspace` does — nothing guesses where PANTHER lives.

**Tech Stack:** Python ≥3.10, stdlib + PyYAML, pytest, git. No network in tests (a local git repository stands in for the draft template); no `claude` binary anywhere in this plan.

**Spec:** `docs/superpowers/specs/2026-08-26-arfc-phase-c-experiment-harness-design.md` §3 (D27), on top of `docs/superpowers/specs/2026-08-25-arfc-progressive-rfc-design.md` (D1–D18). This plan re-cuts Task 9 of `docs/superpowers/plans/2026-08-26-arfc-phase-c-foundations.md:2469-3080` into four reviewer-gated tasks, corrects two defects found in it (see **Corrections** at the end), and adds a fifth task that re-baselines the downstream harness plan's opening gate, which the split would otherwise trip.

**Save this plan to:** `docs/superpowers/plans/2026-08-27-arfc-phase-c-workspace.md`. `docs/` is gitignored in this repository, so committing it needs `git add -f`.

## Global Constraints

- Paths (every command below assumes these shell variables):
  - `W=/Users/elniak/Documents/Documents/Work/Project/Protocol-Testing-Security/PANTHER/master/.claude/worktrees/iut-ai-rfc` (PANTHER worktree root)
  - `R=$W/panther/plugins/services/testers/a_rfc/ai_rfc` (the nested `ai_rfc` git repo — its own history, commits styled `feat: …`/`test: …` with no scope)
  - `S=$R/plugins/ai-rfc/server` (the MCP server + `arfc` CLI package)
  - `PY=/Users/elniak/Documents/Documents/Work/Project/Protocol-Testing-Security/PANTHER/master/.venv/bin/python`
- **NEVER run `panther_builder.py package-dev`/`clean` in this tree** — it `rm -rf`s `docs/`, which holds this plan and its spec.
- Pytest needs the `SSLKEYLOGFILE=` prefix (the env var trips the sandbox at aiohttp import).
- Writes into a nested `.git` (the commits at the end of each task) need the sandbox disabled. Repositories that pytest creates under `tmp_path` are fine inside the sandbox.
- Commit with explicit paths only: `git -C $R add <paths>`. Never `git add -A` or `git add .` — the working tree carries an unrelated deferred submodule-pointer change.
- Never push either repository. Never bump the PANTHER submodule pointer — that is Task 10 of the foundations plan, deliberately deferred.
- `experiment/` stays stdlib + PyYAML. No network in tests. No real `claude` in tests. Diagnostics go to stderr, never through `logging` (PANTHER's `panther.*` loggers are configured `propagate=False` with an ERROR-only handler and swallow warnings).
- Google-style docstrings (Args/Returns/Raises) on every public function. No comments that restate what the code does. Format touched Python with `$PY -m black` at line length 88.
- Test-suite baseline before Task 1: **29 passed** for `experiment/tests`, **38 passed** for the server, **207 passed** for PANTHER's `a_rfc` suite. This plan touches neither the server nor PANTHER, so the latter two must not move.

---

### Task 1: `Target` and the pinned draft scaffold

The first half of the module: what a reconstruction target is, and how a draft repository is created from the `auto-i-d-template` at a pinned commit with the template's own agent files stripped out. Stripping matters — a `CLAUDE.md` or `.claude/` inherited from the template would silently feed instructions into every experimental run and destroy the comparison between arms.

**Files:**
- Create: `$R/experiment/prompts/draft-skeleton.md`
- Create: `$R/experiment/workspace.py`
- Create: `$R/experiment/tests/test_workspace.py`

**Interfaces:**
- Consumes: `experiment.ExperimentError`; `ai_rfc_server.testing.git(repo, *args, date=None) -> str` (tests only).
- Produces: `Target(name, source, forge_snapshot, window, draft_name, rfc_id, title, abbrev)` with the `pristine_name` property; `AIOQUIC`; `TARGETS: dict[str, Target]`; `TEMPLATE_URL`; `TEMPLATE_COMMIT`; `TEMPLATE_STRIP`; `out_of_window(ordinals, window) -> list[int]`; `scaffold_draft(dest, target, *, template, template_commit) -> str` (returns the draft HEAD); the private `_git(repo, *args, date=None) -> str`.

- [ ] **Step 1: Write the draft skeleton** `$R/experiment/prompts/draft-skeleton.md`

A `string.Template`. The Conventions sentence deliberately carries no backticked `a_rfc:` token — the citation gate would otherwise extract it as a cited claim and fail the first revision.

```markdown
---
title: "$title"
abbrev: "$abbrev"
docname: $draft_name-latest
category: info

ipr: trust200902
area: General
workgroup: Individual Submission
keyword: Internet-Draft

stand_alone: yes
smart_quotes: no
pi: [toc, sortrefs, symrefs]

author:
 -
    ins: C. Crochet
    name: Christophe Crochet
    organization: UCLouvain
    email: christophe.cr.dev@gmail.com

normative:

informative:


--- abstract

This document reconstructs the specification of $target from its
implementation history. Each revision reflects the implementation as it
stood at one cluster of its development timeline; every normative statement
cites a claim in the accompanying evidence manifest, whose status is
adjudicated from anchored evidence rather than asserted.


--- middle

# Introduction

This document is reconstructed from the implementation's repository
history, one timeline cluster at a time. This revision holds no normative
statements yet.

# Conventions and Definitions

{::boilerplate bcp14-tagged}

Claim citations are backticked tokens that name a claim id in the evidence
manifest checkpointed beside this revision; the citation gate verifies that
every cited claim exists there.


--- back
```

- [ ] **Step 2: Write the failing tests** `$R/experiment/tests/test_workspace.py`

```python
from pathlib import Path

import pytest

from ai_rfc_server.testing import git
from experiment import ExperimentError
from experiment.workspace import Target, out_of_window, scaffold_draft


@pytest.fixture
def template_repo(tmp_path: Path) -> tuple[str, str]:
    """A local stand-in for auto-i-d-template, carrying agent files to strip."""
    repo = tmp_path / "template"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@t")
    git(repo, "config", "user.name", "t")
    (repo / ".gitignore").write_text("draft-*\n*.swp\n")
    (repo / "Makefile").write_text("all:\n\t@echo build\n")
    (repo / "CLAUDE.md").write_text("template agent notes\n")
    (repo / ".claude").mkdir()
    (repo / ".claude" / "settings.json").write_text("{}\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "template", date="2026-01-01T00:00:09+00:00")
    return str(repo), git(repo, "rev-parse", "HEAD")


def _target(source: Path) -> Target:
    return Target(
        name="fixture",
        source=source,
        forge_snapshot=None,
        window=(2, 2),
        draft_name="draft-test-fixture",
        rfc_id="FIX-1",
        title="Fixture",
        abbrev="Fix",
    )


def test_out_of_window_keeps_order():
    assert out_of_window(range(1, 8), (2, 4)) == [1, 5, 6, 7]
    assert out_of_window([], (2, 4)) == []


def test_pristine_name_encodes_target_and_window():
    assert _target(Path("/x")).pristine_name == "fixture-w02-02"


def test_scaffold_strips_agent_files_and_seeds_the_draft(template_repo, tmp_path):
    template, commit = template_repo
    dest = tmp_path / "draft"
    head = scaffold_draft(
        dest, _target(tmp_path), template=template, template_commit=commit
    )
    body = (dest / "draft-test-fixture.md").read_text()
    assert (dest / "Makefile").exists()
    assert not (dest / "CLAUDE.md").exists() and not (dest / ".claude").exists()
    assert "draft-*" not in (dest / ".gitignore").read_text()
    assert "docname: draft-test-fixture-latest" in body
    assert 'title: "Fixture"' in body and "specification of fixture" in body
    assert "`a_rfc:" not in body
    assert git(dest, "log", "--oneline").count("\n") == 0
    assert git(dest, "config", "user.name") == "arfc-harness"
    assert head == git(dest, "rev-parse", "HEAD")


def test_scaffold_is_byte_deterministic(template_repo, tmp_path):
    template, commit = template_repo
    first = scaffold_draft(
        tmp_path / "a", _target(tmp_path), template=template, template_commit=commit
    )
    second = scaffold_draft(
        tmp_path / "b", _target(tmp_path), template=template, template_commit=commit
    )
    assert first == second


def test_scaffold_refuses_an_existing_destination(template_repo, tmp_path):
    template, commit = template_repo
    dest = tmp_path / "draft"
    dest.mkdir()
    with pytest.raises(ExperimentError) as excinfo:
        scaffold_draft(
            dest, _target(tmp_path), template=template, template_commit=commit
        )
    assert "scaffolded once" in str(excinfo.value)
```

`test_scaffold_is_byte_deterministic` is the load-bearing one: two scaffolds of the same target must produce the *same commit SHA*, which holds only if the tree, the message, and both the author and committer identity and date are pinned. Every per-run workspace copy rests on that.

- [ ] **Step 3: Run to verify failure**

Run: `cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests/test_workspace.py -q`
Expected: collection error, `ModuleNotFoundError: No module named 'experiment.workspace'`.

- [ ] **Step 4: Write `$R/experiment/workspace.py`**

```python
"""Pristine reconstruction workspaces: prepared once, copied per run.

A pristine workspace is the deterministic output of the substrate stages
plus the window pre-seeding of D27, digest-manifested so every run starts
from bytes the campaign recorded. Nothing here mutates a substrate artifact:
out-of-window clusters are marked processed by checkpoints of the workspace
manifest, each carrying a harness sidecar the analysis excludes.
"""

from __future__ import annotations

import os
import shutil
import string
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from . import ExperimentError

PROMPTS = Path(__file__).parent / "prompts"
DRAFT_SKELETON = PROMPTS / "draft-skeleton.md"
TEMPLATE_URL = "https://github.com/ElNiak/auto-i-d-template"
TEMPLATE_COMMIT = "dcdd985a86afad97a50f7b5e1b613f57c194b774"
TEMPLATE_STRIP = (
    ".claude",
    ".claude-plugin",
    ".codacy",
    ".serena",
    ".specify",
    "CLAUDE.md",
    ".mcp.example.json",
    ".mcp.json",
)
HARNESS_NAME = "arfc-harness"
HARNESS_EMAIL = "arfc-harness@localhost"
PINNED_DATE = "2026-08-26T00:00:00+00:00"


@dataclass(frozen=True)
class Target:
    """One reconstruction target and the window the experiment processes."""

    name: str
    source: Path
    forge_snapshot: Path | None
    window: tuple[int, int]
    draft_name: str
    rfc_id: str
    title: str
    abbrev: str

    @property
    def pristine_name(self) -> str:
        """Directory name encoding target and window, e.g. ``aioquic-w02-11``."""
        low, high = self.window
        return f"{self.name}-w{low:02d}-{high:02d}"


AIOQUIC = Target(
    name="aioquic",
    source=Path("reconstructions/aioquic"),
    forge_snapshot=Path(
        "forge/github.com__aiortc__aioquic/snapshot-2026-08-25T15-16-59Z"
    ),
    window=(2, 11),
    draft_name="draft-elniak-aioquic-reconstructed",
    rfc_id="AIOQUIC-RECON",
    title="aioquic: A Reconstructed Specification",
    abbrev="aioquic Reconstructed",
)
TARGETS: dict[str, Target] = {"aioquic": AIOQUIC}


def _git(repo: Path, *args: str, date: str | None = None) -> str:
    env = dict(os.environ)
    if date is not None:
        env["GIT_AUTHOR_DATE"] = date
        env["GIT_COMMITTER_DATE"] = date
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, env=env
    )
    if result.returncode != 0:
        raise ExperimentError(
            f"git {' '.join(args)} in {repo} failed: {result.stderr.strip()}"
        )
    return result.stdout.strip()


def out_of_window(ordinals: Iterable[int], window: tuple[int, int]) -> list[int]:
    """The ordinals outside ``window`` (inclusive bounds), in input order.

    Args:
        ordinals: Cluster ordinals, typically every ordinal in a timeline.
        window: Inclusive ``(low, high)`` range the experiment processes.

    Returns:
        The ordinals to pre-seed, in the order they were given.
    """
    low, high = window
    return [ordinal for ordinal in ordinals if ordinal < low or ordinal > high]


def scaffold_draft(
    dest: Path, target: Target, *, template: str, template_commit: str
) -> str:
    """Clone the template at its pin, strip its agent files, seed the draft.

    Args:
        dest: Where the draft repository is created (must not exist).
        target: Names the draft file and fills its front matter.
        template: Clone source (URL or local path).
        template_commit: The commit the scaffold is pinned to.

    Returns:
        The draft repository's HEAD after the scaffold commit.

    Raises:
        ExperimentError: If ``dest`` exists or any git step fails.
    """
    if dest.exists():
        raise ExperimentError(f"{dest} exists; a draft is scaffolded once")
    cloned = subprocess.run(
        ["git", "clone", "-q", template, str(dest)], capture_output=True, text=True
    )
    if cloned.returncode != 0:
        raise ExperimentError(f"cloning {template} failed: {cloned.stderr.strip()}")
    _git(dest, "checkout", "-q", template_commit)
    shutil.rmtree(dest / ".git")
    for name in TEMPLATE_STRIP:
        path = dest / name
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
    ignore = dest / ".gitignore"
    if ignore.exists():
        kept = [
            line for line in ignore.read_text().splitlines() if line.strip() != "draft-*"
        ]
        ignore.write_text("\n".join(kept) + "\n")
    skeleton = string.Template(DRAFT_SKELETON.read_text()).substitute(
        title=target.title,
        abbrev=target.abbrev,
        draft_name=target.draft_name,
        target=target.name,
    )
    (dest / f"{target.draft_name}.md").write_text(skeleton)
    _git(dest, "init", "-q", "-b", "main")
    _git(dest, "config", "user.name", HARNESS_NAME)
    _git(dest, "config", "user.email", HARNESS_EMAIL)
    _git(dest, "add", "-A")
    _git(dest, "commit", "-q", "-m", "scaffold from auto-i-d-template", date=PINNED_DATE)
    return _git(dest, "rev-parse", "HEAD")
```

- [ ] **Step 5: Run the tests**

Run: `cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests -q`
Expected: **34 passed** (29 baseline + 5).

- [ ] **Step 6: Format and commit (nested repo, sandbox OFF)**

```bash
$PY -m black experiment/workspace.py experiment/tests/test_workspace.py
git -C $R add experiment/workspace.py experiment/prompts/draft-skeleton.md experiment/tests/test_workspace.py
git -C $R commit -m "feat: reconstruction targets and the pinned draft scaffold"
```

---

### Task 2: `preseed` — the window is the only unprocessed range

D27's mechanism. The server decides which cluster comes next by reading the *names of directories* under `checkpoints/`, so writing a checkpoint for an out-of-window cluster is what makes the model skip it — without editing `clusters.jsonl` or any other substrate artifact. Each pre-seeded checkpoint gets a `harness.json` sidecar so the analysis can tell harness bookkeeping from work the model actually did.

**Files:**
- Modify: `$R/experiment/workspace.py` (append)
- Modify: `$R/experiment/tests/test_workspace.py` (append)

**Interfaces:**
- Consumes: `panther.plugins.services.testers.a_rfc.draft.checkpoint.write_checkpoint(manifest_path, timeline_dir, cluster_id, out) -> Path`; `panther.plugins.services.testers.a_rfc.timeline.store.read_clusters(directory) -> tuple[dict, ...]` (rows carry `id` and `ordinal`); `panther.plugins.services.testers.a_rfc.views.cli` (imported here, used in Task 4).
- Produces: `HARNESS_MARKER = "harness.json"`; `preseed(workspace, panther_repo, ordinals) -> list[str]`; the private `_substrate(panther_repo)`.

- [ ] **Step 1: Write the failing tests** (append to `test_workspace.py`; extend the import block first)

Import block becomes:

```python
import hashlib
import json
from pathlib import Path

import pytest

from ai_rfc_server.testing import git
from experiment import ExperimentError
from experiment.workspace import (
    HARNESS_MARKER,
    Target,
    out_of_window,
    preseed,
    scaffold_draft,
)
```

Appended helpers and tests:

```python
def _clusters(workspace: Path) -> list[dict]:
    rows = (workspace / "timeline" / "clusters.jsonl").read_text().splitlines()
    return [json.loads(row) for row in rows]


def _cluster_ids(workspace: Path) -> list[str]:
    return [row["id"] for row in _clusters(workspace)]


def _tree_digest(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_preseed_makes_the_server_skip_the_cluster(fixture_workspace, panther_repo):
    ordinals = [row["ordinal"] for row in _clusters(fixture_workspace)]
    assert ordinals == [1, 2]
    seeded = preseed(
        fixture_workspace, panther_repo, out_of_window(ordinals, (2, 2))
    )
    assert seeded == [_cluster_ids(fixture_workspace)[0]]
    marker = json.loads(
        (fixture_workspace / "checkpoints" / seeded[0] / HARNESS_MARKER).read_text()
    )
    assert marker == {"ordinal": 1, "pre_seeded": True, "reason": "outside window"}

    from ai_rfc_server.core.queries import cluster_next, status
    from ai_rfc_server.paths import resolve_context

    ctx = resolve_context()
    assert cluster_next(ctx)["ordinal"] == 2
    composite = status(ctx)
    assert composite["clusters_total"] == 2
    assert composite["clusters_processed"] == 1


def test_preseed_rejects_an_unknown_ordinal(fixture_workspace, panther_repo):
    with pytest.raises(ExperimentError) as excinfo:
        preseed(fixture_workspace, panther_repo, [99])
    assert "no cluster with ordinal 99" in str(excinfo.value)


def test_preseed_leaves_substrate_artifacts_untouched(fixture_workspace, panther_repo):
    before = _tree_digest(fixture_workspace / "timeline")
    manifest_before = (fixture_workspace / "manifest.yaml").read_bytes()
    preseed(fixture_workspace, panther_repo, [1])
    assert _tree_digest(fixture_workspace / "timeline") == before
    assert (fixture_workspace / "manifest.yaml").read_bytes() == manifest_before
```

The `fixture_workspace` fixture already exists in `experiment/tests/conftest.py`; it builds a complete two-cluster workspace through the substrate's own code and points `PANTHER_REPO` and `ARFC_WORKSPACE` at it, which is what lets `resolve_context()` read it back.

- [ ] **Step 2: Run to verify failure**

Run: `cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests/test_workspace.py -q`
Expected: collection error, `ImportError: cannot import name 'HARNESS_MARKER' from 'experiment.workspace'`.

- [ ] **Step 3: Append to `workspace.py`**

The import block becomes exactly:

```python
from __future__ import annotations

import json
import os
import shutil
import string
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from . import ExperimentError
```

Add `HARNESS_MARKER = "harness.json"` beside the other constants, then append:

```python
def _substrate(panther_repo: Path):  # noqa: ANN202 - substrate modules, resolved lazily
    if str(panther_repo) not in sys.path:
        sys.path.insert(0, str(panther_repo))
    from panther.plugins.services.testers.a_rfc.draft.checkpoint import (
        write_checkpoint,
    )
    from panther.plugins.services.testers.a_rfc.timeline.store import read_clusters
    from panther.plugins.services.testers.a_rfc.views import cli as views_cli

    return write_checkpoint, read_clusters, views_cli


def preseed(workspace: Path, panther_repo: Path, ordinals: Iterable[int]) -> list[str]:
    """Checkpoint the workspace manifest against each ordinal and mark it pre-seeded.

    Args:
        workspace: The workspace whose ``checkpoints/`` directory is written.
        panther_repo: PANTHER repository root, put on ``sys.path``.
        ordinals: Cluster ordinals to pre-seed, in order.

    Returns:
        The cluster ids checkpointed, in the order given.

    Raises:
        ExperimentError: If an ordinal has no cluster.
    """
    write_checkpoint, read_clusters, _ = _substrate(panther_repo)
    by_ordinal = {
        row["ordinal"]: row["id"] for row in read_clusters(workspace / "timeline")
    }
    seeded = []
    for ordinal in ordinals:
        cluster_id = by_ordinal.get(ordinal)
        if cluster_id is None:
            raise ExperimentError(f"no cluster with ordinal {ordinal}")
        checkpoint_dir = write_checkpoint(
            workspace / "manifest.yaml",
            workspace / "timeline",
            cluster_id,
            workspace / "checkpoints",
        )
        (checkpoint_dir / HARNESS_MARKER).write_text(
            json.dumps(
                {"pre_seeded": True, "reason": "outside window", "ordinal": ordinal},
                sort_keys=True,
            )
            + "\n"
        )
        seeded.append(cluster_id)
    return seeded
```

The sidecar is safe: `verify_checkpoint` (`panther/plugins/services/testers/a_rfc/draft/checkpoint.py:106`) digests only `manifest.yaml`, so an extra file in the checkpoint directory cannot make a checkpoint fail verification.

- [ ] **Step 4: Run the tests**

Run: `cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests -q`
Expected: **37 passed**.

- [ ] **Step 5: Format and commit (nested repo, sandbox OFF)**

```bash
$PY -m black experiment/workspace.py experiment/tests/test_workspace.py
git -C $R add experiment/workspace.py experiment/tests/test_workspace.py
git -C $R commit -m "feat: pre-seed out-of-window clusters through substrate checkpoints"
```

---

### Task 3: Digest manifest and verified per-run copies

What makes a run reproducible: a SHA-256 line per file, written once when the workspace is sealed and checked on every copy. The digest deliberately excludes `.git` directories (git's own object store is not byte-stable across versions) and excludes the two files that describe the seal itself.

**Files:**
- Modify: `$R/experiment/workspace.py` (append)
- Modify: `$R/experiment/tests/test_workspace.py` (append)

**Interfaces:**
- Produces: `DIGEST_FILE = "pristine.sha256"`; `RECORD_FILE = "pristine.json"`; `write_digest(root) -> Path`; `verify_digest(root) -> list[str]` (empty means verified; entries are `missing: <path>`, `unexpected: <path>`, `modified: <path>`, in path-sorted order); `copy_workspace(pristine, dest) -> Path`.

- [ ] **Step 1: Write the failing tests** (append to `test_workspace.py`; the import block becomes exactly the block below, then the fixture and tests are appended)

```python
import hashlib
import json
from pathlib import Path

import pytest

from ai_rfc_server.testing import git
from experiment import ExperimentError
from experiment.workspace import (
    DIGEST_FILE,
    HARNESS_MARKER,
    RECORD_FILE,
    Target,
    copy_workspace,
    out_of_window,
    preseed,
    scaffold_draft,
    verify_digest,
    write_digest,
)
```

```python
@pytest.fixture
def sealed(fixture_workspace: Path) -> Path:
    """A fixture workspace sealed the way a pristine one is: record + digest."""
    record = {
        "clone_head": git(fixture_workspace / "clone", "rev-parse", "HEAD"),
        "draft_head": git(fixture_workspace / "draft", "rev-parse", "HEAD"),
    }
    (fixture_workspace / RECORD_FILE).write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n"
    )
    write_digest(fixture_workspace)
    return fixture_workspace


def test_digest_covers_content_but_not_git_or_itself(sealed):
    covered = [
        line.partition("  ")[2]
        for line in (sealed / DIGEST_FILE).read_text().splitlines()
    ]
    assert "manifest.yaml" in covered
    assert "draft/draft-test-spec.md" in covered
    assert not any(part == ".git" for path in covered for part in path.split("/"))
    assert DIGEST_FILE not in covered and RECORD_FILE not in covered
    assert verify_digest(sealed) == []


def test_verify_reports_every_kind_of_drift_in_path_order(sealed):
    (sealed / "manifest.yaml").write_text("rfc: X\ntitle: t\nrequirements: {}\n")
    (sealed / "extra.txt").write_text("x\n")
    (sealed / "questions.yaml").unlink()
    assert verify_digest(sealed) == [
        "unexpected: extra.txt",
        "modified: manifest.yaml",
        "missing: questions.yaml",
    ]


def test_verify_reports_a_missing_manifest(fixture_workspace):
    assert verify_digest(fixture_workspace) == ["pristine.sha256 is missing"]


def test_copy_verifies_and_never_reuses_a_destination(sealed, tmp_path):
    copy = copy_workspace(sealed, tmp_path / "run" / "workspace")
    assert verify_digest(copy) == []
    assert git(copy / "draft", "rev-parse", "HEAD") == git(
        sealed / "draft", "rev-parse", "HEAD"
    )
    with pytest.raises(ExperimentError) as excinfo:
        copy_workspace(sealed, tmp_path / "run" / "workspace")
    assert "never reuses" in str(excinfo.value)


def test_copy_refuses_a_tampered_pristine(sealed, tmp_path):
    (sealed / "manifest.yaml").write_text("rfc: X\ntitle: t\nrequirements: {}\n")
    with pytest.raises(ExperimentError) as excinfo:
        copy_workspace(sealed, tmp_path / "run" / "workspace")
    assert "does not verify" in str(excinfo.value)
```

The path-order assertion is deliberate and is one of the two corrections to the original Task 9 (see **Corrections**): `verify_digest` walks the union of expected and actual paths in sorted order, so `extra.txt` is reported before `manifest.yaml`.

- [ ] **Step 2: Run to verify failure**

Run: `cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests/test_workspace.py -q`
Expected: collection error, `ImportError: cannot import name 'DIGEST_FILE' from 'experiment.workspace'`.

- [ ] **Step 3: Append to `workspace.py`**

The import block becomes exactly:

```python
from __future__ import annotations

import hashlib
import json
import os
import shutil
import string
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from . import ExperimentError
```

Then the constants, beside the others:

```python
DIGEST_FILE = "pristine.sha256"
RECORD_FILE = "pristine.json"
_SKIP_FROM_DIGEST = frozenset({DIGEST_FILE, RECORD_FILE})
```

and the functions:

```python
def _digests(root: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        relative = path.relative_to(root)
        if ".git" in relative.parts or relative.name in _SKIP_FROM_DIGEST:
            continue
        found[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return found


def write_digest(root: Path) -> Path:
    """Write ``pristine.sha256`` over every regular file outside ``.git``.

    Args:
        root: The workspace to seal.

    Returns:
        The digest manifest's path.
    """
    lines = [f"{digest}  {relative}" for relative, digest in _digests(root).items()]
    target = root / DIGEST_FILE
    target.write_text("\n".join(lines) + "\n")
    return target


def verify_digest(root: Path) -> list[str]:
    """Differences between a tree and its digest manifest; empty means verified.

    Args:
        root: A workspace previously sealed by :func:`write_digest`.

    Returns:
        One ``missing:``/``unexpected:``/``modified:`` line per differing
        path, in path-sorted order.
    """
    manifest_path = root / DIGEST_FILE
    if not manifest_path.exists():
        return [f"{DIGEST_FILE} is missing"]
    expected: dict[str, str] = {}
    for line in manifest_path.read_text().splitlines():
        if line.strip():
            digest, _, relative = line.partition("  ")
            expected[relative] = digest
    actual = _digests(root)
    problems = []
    for relative in sorted(set(expected) | set(actual)):
        if relative not in actual:
            problems.append(f"missing: {relative}")
        elif relative not in expected:
            problems.append(f"unexpected: {relative}")
        elif actual[relative] != expected[relative]:
            problems.append(f"modified: {relative}")
    return problems


def copy_workspace(pristine: Path, dest: Path) -> Path:
    """Copy a pristine workspace for one run and verify the copy.

    Args:
        pristine: The sealed workspace to copy from.
        dest: Where the run's private workspace is created (must not exist).

    Returns:
        The destination path.

    Raises:
        ExperimentError: If ``dest`` exists, the copy does not reproduce the
            digest manifest, or a nested repository HEAD moved.
    """
    if dest.exists():
        raise ExperimentError(f"{dest} exists; a run never reuses a workspace")
    shutil.copytree(pristine, dest, symlinks=False)
    problems = verify_digest(dest)
    if problems:
        raise ExperimentError(f"copied workspace does not verify: {problems[:5]}")
    record = json.loads((dest / RECORD_FILE).read_text())
    for name, key in (("clone", "clone_head"), ("draft", "draft_head")):
        head = _git(dest / name, "rev-parse", "HEAD")
        if head != record[key]:
            raise ExperimentError(
                f"{name} HEAD {head} differs from recorded {record[key]}"
            )
    return dest
```

- [ ] **Step 4: Run the tests**

Run: `cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests -q`
Expected: **42 passed**.

- [ ] **Step 5: Format and commit (nested repo, sandbox OFF)**

```bash
$PY -m black experiment/workspace.py experiment/tests/test_workspace.py
git -C $R add experiment/workspace.py experiment/tests/test_workspace.py
git -C $R commit -m "feat: digest-manifested workspaces and verified per-run copies"
```

---

### Task 4: `prepare` and the `workspace prepare` command

The orchestration: copy the substrate outputs, emit and verify every cluster view, write the empty manifest and registers, scaffold the draft, pre-seed everything outside the window, record provenance, seal. The views are emitted *and* re-verified, so a workspace that cannot reproduce its own views byte-for-byte never becomes a campaign input.

**Files:**
- Modify: `$R/experiment/workspace.py` (append)
- Modify: `$R/experiment/cli.py`
- Modify: `$R/experiment/tests/test_workspace.py` (append)

**Interfaces:**
- Consumes: everything from Tasks 1–3; `views_cli.main(argv) -> int` from `_substrate`.
- Produces: `prepare(target, *, root, panther_repo, template=TEMPLATE_URL, template_commit=TEMPLATE_COMMIT) -> Path`; the `python -m experiment workspace prepare <target>` command. The harness plan's runner and matrix import `Target`, `TARGETS`, `copy_workspace`, `verify_digest`, `HARNESS_MARKER` and `RECORD_FILE` from this module.

- [ ] **Step 1: Write the failing tests** (append to `test_workspace.py`; the import block becomes exactly the block below, then the helper and tests are appended)

```python
import hashlib
import json
from pathlib import Path

import pytest

from ai_rfc_server.testing import git
from experiment import ExperimentError
from experiment.workspace import (
    DIGEST_FILE,
    HARNESS_MARKER,
    RECORD_FILE,
    TARGETS,
    Target,
    copy_workspace,
    out_of_window,
    prepare,
    preseed,
    scaffold_draft,
    verify_digest,
    write_digest,
)
```

```python
def _prepare(fixture_workspace, panther_repo, template_repo, tmp_path):
    template, commit = template_repo
    return prepare(
        _target(fixture_workspace),
        root=tmp_path / "root",
        panther_repo=panther_repo,
        template=template,
        template_commit=commit,
    )


def test_prepare_builds_the_pristine_tree(
    fixture_workspace, panther_repo, template_repo, tmp_path
):
    pristine = _prepare(fixture_workspace, panther_repo, template_repo, tmp_path)
    assert pristine == tmp_path / "root" / "pristine" / "fixture-w02-02"
    ids = _cluster_ids(pristine)
    assert sorted(p.name for p in (pristine / "clusters").iterdir()) == sorted(ids)
    assert (pristine / "manifest.yaml").read_text() == (
        "rfc: FIX-1\ntitle: Fixture\nrequirements: {}\n"
    )
    assert (pristine / "questions.yaml").read_text() == "questions: {}\n"
    assert (pristine / "revisions.yaml").read_text() == "revisions: {}\n"
    assert (pristine / "interviews").is_dir()
    assert (pristine / "draft" / "draft-test-fixture.md").exists()
    record = json.loads((pristine / RECORD_FILE).read_text())
    assert record["template_commit"] == template_repo[1]
    assert record["pre_seeded"] == [ids[0]]
    assert record["cluster_count"] == 2
    assert record["window"] == [2, 2]
    assert record["clone_head"] == git(pristine / "clone", "rev-parse", "HEAD")
    assert record["draft_head"] == git(pristine / "draft", "rev-parse", "HEAD")
    assert (pristine / "checkpoints" / ids[0] / HARNESS_MARKER).exists()
    assert (pristine / "checkpoints" / ids[0] / "checkpoint.json").exists()
    assert not (pristine / "checkpoints" / ids[1]).exists()
    assert verify_digest(pristine) == []


def test_prepared_window_is_the_only_unprocessed_range(
    fixture_workspace, panther_repo, template_repo, tmp_path, monkeypatch
):
    pristine = _prepare(fixture_workspace, panther_repo, template_repo, tmp_path)
    monkeypatch.setenv("ARFC_WORKSPACE", str(pristine))

    from ai_rfc_server.core.queries import cluster_next, status
    from ai_rfc_server.paths import resolve_context

    ctx = resolve_context()
    assert cluster_next(ctx)["ordinal"] == 2
    composite = status(ctx)
    assert composite["clusters_total"] == 2
    assert composite["clusters_processed"] == 1


def test_prepare_refuses_to_overwrite_or_to_run_without_the_substrate(
    fixture_workspace, panther_repo, template_repo, tmp_path
):
    _prepare(fixture_workspace, panther_repo, template_repo, tmp_path)
    with pytest.raises(ExperimentError) as overwrite:
        _prepare(fixture_workspace, panther_repo, template_repo, tmp_path)
    assert "prepared once" in str(overwrite.value)

    empty = tmp_path / "empty-source"
    empty.mkdir()
    template, commit = template_repo
    with pytest.raises(ExperimentError) as missing:
        prepare(
            _target(empty),
            root=tmp_path / "other-root",
            panther_repo=panther_repo,
            template=template,
            template_commit=commit,
        )
    assert str(empty / "clone") in str(missing.value)


def test_cli_workspace_prepare_reports_the_tree(
    fixture_workspace, panther_repo, template_repo, tmp_path, monkeypatch, capsys
):
    from experiment.cli import main

    template, commit = template_repo
    monkeypatch.setitem(TARGETS, "fixture", _target(fixture_workspace))
    code = main(
        [
            "workspace",
            "prepare",
            "fixture",
            "--root",
            str(tmp_path / "root"),
            "--panther-repo",
            str(panther_repo),
            "--template",
            template,
            "--template-commit",
            commit,
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert f"pristine: {tmp_path / 'root' / 'pristine' / 'fixture-w02-02'}" in out
    assert "clusters: 2  pre-seeded: 1  window: [2, 2]" in out
```

`monkeypatch.setitem(TARGETS, …)` works because `cli.py` imports the same dictionary object and the parser reads `sorted(TARGETS)` when it is built, inside `main`.

- [ ] **Step 2: Run to verify failure**

Run: `cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests/test_workspace.py -q`
Expected: collection error, `ImportError: cannot import name 'prepare' from 'experiment.workspace'`.

- [ ] **Step 3: Append `prepare` to `workspace.py`**

The import block becomes exactly the block below. Note that `from typing import Any, Iterable` **replaces** the earlier `from typing import Iterable` — it does not sit beside it.

```python
from __future__ import annotations

import hashlib
import json
import os
import shutil
import string
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

from . import ExperimentError
```

Then append:

```python
def _git_version() -> str:
    return subprocess.run(
        ["git", "--version"], capture_output=True, text=True
    ).stdout.strip()


def prepare(
    target: Target,
    *,
    root: Path,
    panther_repo: Path,
    template: str = TEMPLATE_URL,
    template_commit: str = TEMPLATE_COMMIT,
) -> Path:
    """Build the pristine workspace of ``target`` under ``root/pristine/``.

    Copies the substrate outputs, emits and re-verifies every view, writes the
    empty manifest and registers, scaffolds the draft, pre-seeds every
    out-of-window ordinal, records provenance and writes the digest manifest.

    Args:
        target: What to prepare, and the window to leave unprocessed.
        root: The runs root; the workspace lands in ``root/pristine/``.
        panther_repo: PANTHER repository root, put on ``sys.path``.
        template: Draft template clone source.
        template_commit: The commit the draft scaffold is pinned to.

    Returns:
        The pristine directory.

    Raises:
        ExperimentError: If the pristine directory exists, a source part is
            missing, or a substrate stage fails.
    """
    pristine = root / "pristine" / target.pristine_name
    if pristine.exists():
        raise ExperimentError(
            f"{pristine} exists; a pristine workspace is prepared once"
        )
    source = (
        target.source if target.source.is_absolute() else panther_repo / target.source
    )
    for part in ("clone", "corpus", "timeline"):
        if not (source / part).is_dir():
            raise ExperimentError(f"{source / part} is missing")
    pristine.mkdir(parents=True)
    for part in ("clone", "corpus", "timeline"):
        shutil.copytree(source / part, pristine / part, symlinks=False)
    snapshot = None
    if target.forge_snapshot is not None:
        snapshot = pristine / target.forge_snapshot
        shutil.copytree(source / target.forge_snapshot, snapshot, symlinks=False)
    clone_head = _git(pristine / "clone", "rev-parse", "HEAD")

    _, read_clusters, views_cli = _substrate(panther_repo)
    views_args = [
        str(pristine / "timeline"),
        "--corpus",
        str(pristine / "corpus"),
        "--repo",
        str(pristine / "clone"),
        "--out",
        str(pristine / "clusters"),
    ]
    if snapshot is not None:
        views_args += ["--forge", str(snapshot)]
    if views_cli.main(views_args) != 0:
        raise ExperimentError("view emission failed; see stderr")
    if views_cli.main(views_args + ["--verify"]) != 0:
        raise ExperimentError("views do not reproduce byte-for-byte; see stderr")

    (pristine / "manifest.yaml").write_text(
        yaml.safe_dump(
            {"rfc": target.rfc_id, "title": target.title, "requirements": {}},
            sort_keys=False,
        )
    )
    (pristine / "questions.yaml").write_text("questions: {}\n")
    (pristine / "revisions.yaml").write_text("revisions: {}\n")
    (pristine / "interviews").mkdir()
    draft_head = scaffold_draft(
        pristine / "draft", target, template=template, template_commit=template_commit
    )

    ordinals = [row["ordinal"] for row in read_clusters(pristine / "timeline")]
    seeded = preseed(pristine, panther_repo, out_of_window(ordinals, target.window))

    record: dict[str, Any] = {
        "target": target.name,
        "window": list(target.window),
        "source": str(source),
        "clone_head": clone_head,
        "draft_head": draft_head,
        "template": template,
        "template_commit": template_commit,
        "template_stripped": list(TEMPLATE_STRIP),
        "forge_snapshot": str(target.forge_snapshot) if target.forge_snapshot else None,
        "cluster_count": len(ordinals),
        "pre_seeded": seeded,
        "git_version": _git_version(),
        "python": sys.version.split()[0],
    }
    (pristine / RECORD_FILE).write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n"
    )
    write_digest(pristine)
    return pristine
```

- [ ] **Step 4: Register `workspace prepare` in `$R/experiment/cli.py`**

Add `import json` to the import block and, beside the existing `from .profile import …`:

```python
from .workspace import TARGETS, TEMPLATE_COMMIT, TEMPLATE_URL
from .workspace import prepare as prepare_workspace
```

In `_parser()`, after the `render` parser block and before `return parser`:

```python
    workspace = commands.add_parser("workspace", help="Pristine workspaces.")
    workspace_verbs = workspace.add_subparsers(dest="verb", required=True)
    prepare = workspace_verbs.add_parser("prepare", help="Build a pristine workspace.")
    _add_root(prepare)
    prepare.add_argument("target", choices=sorted(TARGETS))
    prepare.add_argument("--panther-repo", type=Path, required=True)
    prepare.add_argument("--template", default=TEMPLATE_URL)
    prepare.add_argument("--template-commit", default=TEMPLATE_COMMIT)
```

In `main()`, after the `elif args.command == "render":` arm:

```python
        elif args.command == "workspace" and args.verb == "prepare":
            pristine = prepare_workspace(
                TARGETS[args.target],
                root=root,
                panther_repo=args.panther_repo.resolve(),
                template=args.template,
                template_commit=args.template_commit,
            )
            record = json.loads((pristine / "pristine.json").read_text())
            print(f"pristine: {pristine}")
            print(
                f"clusters: {record['cluster_count']}  "
                f"pre-seeded: {len(record['pre_seeded'])}  "
                f"window: {record['window']}"
            )
```

- [ ] **Step 5: Run the whole suite**

Run: `cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests -q`
Expected: **46 passed** (29 baseline + 5 + 3 + 5 + 4).

- [ ] **Step 6: Confirm nothing else moved**

```bash
cd $S && SSLKEYLOGFILE= $PY -m pytest -q 2>&1 | tail -1
cd $W && SSLKEYLOGFILE= $PY -m pytest tests/unit/plugins/services/testers/a_rfc -n auto -q 2>&1 | tail -1
```

Expected: `38 passed` and `207 passed`, both unchanged.

- [ ] **Step 7: Format and commit (nested repo, sandbox OFF)**

```bash
$PY -m black experiment/workspace.py experiment/cli.py experiment/tests/test_workspace.py
git -C $R add experiment/workspace.py experiment/cli.py experiment/tests/test_workspace.py
git -C $R commit -m "feat: prepare pristine workspaces behind a workspace prepare command"
```

- [ ] **Step 8: Report** — the four nested-repo SHAs, the three suite counts, and the confirmation that the PANTHER working tree still carries only the deferred submodule-pointer change.

---

### Task 5: Re-baseline the harness plan's Task 0 gate

Splitting Task 9 into four commits invalidates the gate the *next* plan opens with. `docs/superpowers/plans/2026-08-26-arfc-phase-c-harness.md:27` reads:

> Expected: the foundations commit (`feat: pristine workspaces …`), `32 passed`, the digest file listed, `go`. Anything else: STOP and report.

Neither number nor commit message will match after Tasks 1–4, and that gate instructs its executor to stop. Left unfixed, the harness plan halts on a false alarm.

**Files:**
- Modify: `$W/docs/superpowers/plans/2026-08-26-arfc-phase-c-harness.md` (Task 0, Step 1)

- [ ] **Step 1: Correct the expectation line**

Replace the line quoted above with:

```markdown
Expected: the foundations commits through `feat: prepare pristine workspaces behind a workspace prepare command`, `46 passed`, the digest file listed, `go`. Anything else: STOP and report.
```

The other two conditions on that line are unchanged and still pending: `pristine.sha256` comes from foundations Task 10, and the `go` verdict from the spike S0 manual run.

- [ ] **Step 2: Commit (PANTHER)**

`docs/` is gitignored in this repository, so the add needs `-f`.

```bash
cd $W && git add -f docs/superpowers/plans/2026-08-26-arfc-phase-c-harness.md
git commit -m "docs(a_rfc): re-baseline the harness plan gate for the split workspace task"
```

- [ ] **Step 3: Confirm the working tree**

Run: `cd $W && git status --short`
Expected: only ` M panther/plugins/services/testers/a_rfc/ai_rfc`, the deliberately deferred submodule-pointer change.

---

## Corrections to Task 9 of the foundations plan

Two defects were found by reading the original Task 9 against the tree, and are fixed above.

1. **The drift assertion had its entries in the wrong order.** The original test asserts `verify_digest(copy) == ["modified: manifest.yaml", "unexpected: extra.txt"]`, but `verify_digest` walks `sorted(set(expected) | set(actual))`, and `extra.txt` sorts before `manifest.yaml`. The original test would have failed. Task 3 asserts path-sorted order and states it is the contract.
2. **The expected test count was stale.** The original Step 6 expects `32 passed (27 + 5)`; the experiment suite's baseline is now 29, because Task 8 added tests after the plan was written. The counts above are computed from the real baseline: 29 + 5 + 3 + 5 + 4, gating at **34, 37, 42, 46**.

The fixture workspace's shape was confirmed rather than assumed, since `window=(2, 2)`, the `fixture-w02-02` directory name and four assertions depend on it: the green server suite already asserts that `build_workspace` yields exactly two clusters with ordinals 1 and 2 (`plugins/ai-rfc/server/tests/test_core.py:94,109,187`).

Everything else the original assumed was verified present and unchanged: the `fixture_workspace` and `panther_repo` fixtures in `experiment/tests/conftest.py`; `_add_root` at `experiment/cli.py:18`; `ai_rfc_server.testing.git` at `testing.py:14`; `write_checkpoint` at `draft/checkpoint.py:45`; `read_clusters` at `timeline/store.py:85`; the views CLI's `--corpus/--repo/--out/--forge/--verify` flags at `views/cli.py:30-73`; `cluster_next`, `status` and `resolve_context` in the server core; and `_processed_cluster_ids` keying off checkpoint **directory names**, which is what makes pre-seeding work at all.

## Self-review

**Spec coverage.** §3/D27 decomposes as: pristine tree and provenance → Task 4; window pre-seeding and the harness sidecar → Task 2; digest and per-run copy → Task 3; the pinned, agent-file-stripped draft scaffold → Task 1; the `workspace prepare` surface → Task 4. Not in this plan, by design: the real aioquic preparation and the submodule bump (foundations Task 10), the spike S0 manual run, and the runner/matrix/audit/metrics/report half (`docs/superpowers/plans/2026-08-26-arfc-phase-c-harness.md`).

**Placeholder scan.** No TBD or TODO; every code step carries its code; no step refers to another task instead of repeating what it needs.

**Type consistency.** `_git`/`git` are distinct on purpose — the private module helper and the test helper from `ai_rfc_server.testing`, same signature. `Target` field names are identical in Tasks 1 and 4. `HARNESS_MARKER`, `RECORD_FILE`, `DIGEST_FILE` are spelled the same in Tasks 2, 3, 4 and in the harness plan that imports them. `preseed` returns cluster **ids** while `out_of_window` returns **ordinals**; Task 4 threads them in that order.

**Known judgement calls.** `scaffold_draft` stages with `git add -A` — inside the freshly created draft repository only, where the template's own `.gitignore` governs what lands; this is not the forbidden repository-wide `git add -A`. Task 2 and Task 4 both read the window back through the server's `cluster_next`/`status`; the overlap is intentional, since Task 2 gates the mechanism and Task 4 gates the composition. `_git` duplicates `ai_rfc_server.testing.git` rather than importing it, so the experiment package keeps no runtime dependency on the server package.

**Two accepted risks, neither blocking.**

1. `TEMPLATE_COMMIT = "dcdd985a86afad97a50f7b5e1b613f57c194b774"` is carried over from the foundations plan and **has not been verified** — it names a commit in `github.com/ElNiak/auto-i-d-template`, and this plan is offline by construction (every test passes a local repository through the `template` argument). The pin is first exercised for real in foundations Task 10, which is where a wrong value would surface, as a clone failure rather than silent drift.
2. `preseed` lets the substrate's `CheckpointError` propagate when a checkpoint already exists, and `cli.main` catches only `(ExperimentError, OSError)`, so that path would print a traceback rather than an `error: …` line. It is unreachable through `prepare`, which refuses an existing pristine directory first, so it is left alone rather than wrapped; the harness plan's runner is the place that would need to care.

## Execution handoff

Two options: **subagent-driven** (a fresh subagent per task with review between tasks, via `superpowers:subagent-driven-development`) or **inline** (batch execution with checkpoints, via `superpowers:executing-plans`). Tasks 1–4 each carry an independent red-green-commit cycle, which suits the subagent-driven route; Task 5 is a two-line documentation fix that belongs wherever Task 4 lands.

Before Task 1, save this plan to `docs/superpowers/plans/2026-08-27-arfc-phase-c-workspace.md` and commit it with `git add -f` (`docs/` is gitignored here).
