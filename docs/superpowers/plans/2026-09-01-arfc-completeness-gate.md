# a_rfc Completeness Gate — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic `draft completeness` verb that answers "which timeline clusters produced no claim, and which claims does no prose cite?" — the missing signal that today makes it impossible to know whether a reconstruction is finished.

**Architecture:** A new pure-function module `draft/completeness.py` reads a workspace's timeline, checkpoints, live manifest and draft git repo, and emits a sorted-key `completeness.json` plus stderr findings. It attributes claims to clusters by sorting checkpoints on their recorded `ordinal` and differencing each against its predecessor **in that sorted list**. It reuses the citation machinery already in `draft/gate.py` rather than reimplementing it, and ships as a third verb on the existing `a_rfc.draft` CLI with the same 0/1/3 exit contract.

**Tech Stack:** Python 3.10+, stdlib `argparse`/`json`/`dataclasses`, PyYAML via the existing `..schema`, pytest. No new dependencies.

**Spec:** Self-contained; "Why this exists" below carries the audit finding it derives from, and the roadmap at the end places it among the other four plans.

## Global Constraints

- Python 3.10+; line length 88 (Black); isort; full type annotations; Google-style docstrings (Args/Returns/Raises) on every public function.
- All JSON written with `sort_keys=True, indent=2` and a trailing newline — this codebase's byte-reproducibility rule.
- Diagnostics go to **stderr** via the module's `_report()`, never `logging` (every `panther.*` logger is `propagate=False` with an ERROR-only handler, so a logged warning is discarded before anyone sees it).
- Exit codes: **0** success, **1** unreadable/uninterpretable input, **3** strict findings, **2** reserved for argparse. Never conflate 2 and 3.
- No backward-compat shims. No comments unless the *why* is non-obvious.
- All work here is in the **parent** repo (`panther/plugins/services/testers/a_rfc/`), not the `ai_rfc` submodule.
- Every pytest invocation is prefixed `SSLKEYLOGFILE=` — the global env var trips the sandbox during collection.

## Why this exists

`adjudicate` and `gate` check only internal *consistency* — that citations are a subset of the checkpoint, revision tags are monotone, and no claim outranks its evidence (`draft/gate.py:1-8`). Nothing measures *coverage*. On MARK the deterministic pipeline already produced **69 clusters** over 969 commits, but only **2** were ever checkpointed (`reconstructions/mark/checkpoints/` holds exactly `c0049-pr-ba8ca432c304` and `c0069-epoch-b901f36095d7`), yielding 7 claims. Nothing in the tool reports that 67 clusters are untouched. This verb makes that visible, and it is a prerequisite for trusting any automated whole-run driver.

## Scope check

The full audit spans five workstreams (defects, whole-run driver, naming migration, simplification, documentation). Per the scope rule these are **five separate plans**, each shipping working software on its own. **This is plan 1 of 5** — the completeness gate, plus the one exit-code defect and one docs gap that touch the same files. The roadmap at the end sketches the rest.

## Where to save this plan

`docs/superpowers/plans/2026-09-01-arfc-completeness-gate.md`, matching the existing convention (`docs/superpowers/plans/2026-08-25-ai-rfc-plugin.md`, `…-arfc-forge-stage.md`).

**Two hazards.** `docs/` is gitignored (`.gitignore:54`) yet nine files under it are tracked, so committing needs `git add -f`. And `panther_builder.py package-dev` and `clean` **`rm -rf` the `docs/` directory** — commit before running either, or the plan is deleted.

## File Structure

| File | Responsibility |
|---|---|
| `panther/plugins/services/testers/a_rfc/draft/completeness.py` | **Create.** Read timeline/checkpoints, attribute claims, analyse citations, build the report. |
| `panther/plugins/services/testers/a_rfc/draft/gate.py` | **Modify.** De-underscore `_cited_ids` → `cited_ids`; update its one call site. |
| `panther/plugins/services/testers/a_rfc/draft/cli.py` | **Modify.** Add the `completeness` verb; fix the stale `--strict` help at `:74`. |
| `tests/unit/plugins/services/testers/a_rfc/draft/conftest.py` | **Modify.** Add one `sparse_workspace` fixture beside the existing ones. |
| `tests/unit/plugins/services/testers/a_rfc/draft/test_completeness.py` | **Create.** Unit tests. |
| `mkdocs.yml`, `docs_src/` | **Modify.** First `a_rfc` entry in the published docs. |

**Naming note:** the verb is `completeness`, not `coverage`, because `a_rfc/coverage/` is already the JaCoCo test-coverage package. Two senses of "coverage" in one tool would be a real collision.

## Reuse the existing fixtures — do not hand-roll workspaces

`tests/unit/plugins/services/testers/a_rfc/draft/conftest.py` already provides what these
tests need. Rebuilding them would duplicate working code and risk encoding the formats wrongly:

- **`timeline_dir`** — a two-cluster timeline (epoch then pr) built *through the shipped code*
  (`build_timeline` + `write_timeline`), not hand-written JSON.
- **`draft_workspace`** — a gate-clean workspace returning
  `{"repo", "timeline", "checkpoints", "questions", "revisions"}`. Its draft repo carries two
  real tags (`draft-test-spec-00`, `-01`) citing `` `a_rfc:spec:1.1` `` and
  `` `a_rfc:spec:2.1` ``, with one checkpoint per cluster.
- **`manifest_path`**, **`git(repo, *args)`**, and the module-private `_manifest_text`,
  `_checkpoint_sha` helpers.

**Three format facts those fixtures encode. Getting any wrong breaks every test:**

1. A manifest is `rfc:` / `title:` / `requirements:`, where `requirements` is a **mapping of
   claim id to body** — not a list, and there is no `id:` key inside a body (the mapping key
   *is* the id). Required per body: `text`, `section`, `level`, `layer`; `status`,
   `req_class`, `intent`, `anchors` all default (`schema.py:98-122`).
2. `revisions.yaml` is a **mapping keyed by tag**, each value holding `cluster_id`,
   `checkpoint_manifest_sha256`, `normative_change`, `note`. Not a list.
3. Claim ids contain colons (`spec:1.1`), so a citation reads `` `a_rfc:spec:1.1` `` and
   `CITATION`'s `[^`\s]+` captures `spec:1.1`.

Only one new fixture is needed — a workspace whose timeline has **more clusters than
checkpoints**, since `draft_workspace` checkpoints both of its two. Task 1 adds it, laid out
so its root doubles as the CLI's workspace argument (`timeline/`, `checkpoints/`, `draft/`,
`manifest.yaml`, `revisions.yaml` all directly under it).

---

### Task 1: The sparse-workspace fixture, and readers for timeline and checkpoints

**Files:**
- Create: `panther/plugins/services/testers/a_rfc/draft/completeness.py`
- Modify: `tests/unit/plugins/services/testers/a_rfc/draft/conftest.py`
- Test: `tests/unit/plugins/services/testers/a_rfc/draft/test_completeness.py`

**Interfaces:**
- Consumes: `CHECKPOINT_FILE` from `.checkpoint`.
- Produces: `CompletenessError`; `load_clusters(timeline_dir) -> tuple[dict, ...]`; `checkpoint_records(checkpoints_dir) -> tuple[tuple[str, dict], ...]`.

Real shapes, read from the MARK workspace — do not guess:
- `clusters.jsonl` row: `{"anchor_sha": str, "files_complete": bool, "id": str, "kind": "epoch"|"pr", "member_count": int, "nested_merge_count": int, "ordinal": int, "pr_number": int|None, "provenance": str, "spine_prev_sha": str|None, "subject_pr_hint": str|None, "title": str}`
- `checkpoint.json` record: `{"adjudication": {...}, "cluster_id": str, "manifest_sha256": str, "ordinal": int, "prev_cluster_id": str|None, "timeline_sha256": str}`

- [ ] **Step 1: Add the sparse fixture to the existing conftest**

Append to `tests/unit/plugins/services/testers/a_rfc/draft/conftest.py` (it already imports
`read_clusters`, `write_checkpoint`, and defines `git`, `_manifest_text`, `_checkpoint_sha`):

```python
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
```

- [ ] **Step 2: Write the failing test**

Create `tests/unit/plugins/services/testers/a_rfc/draft/test_completeness.py`:

```python
"""Tests for the deterministic completeness gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from panther.plugins.services.testers.a_rfc.draft import completeness


def test_load_clusters_returns_rows_ordered_by_ordinal(timeline_dir: Path) -> None:
    rows = completeness.load_clusters(timeline_dir)

    assert [row["ordinal"] for row in rows] == [1, 2]
    assert all("id" in row for row in rows)


def test_load_clusters_raises_when_timeline_missing(tmp_path: Path) -> None:
    with pytest.raises(completeness.CompletenessError):
        completeness.load_clusters(tmp_path / "absent")


def test_checkpoint_records_sorted_by_ordinal_not_directory_name(
    tmp_path: Path,
) -> None:
    root = tmp_path / "checkpoints"
    for name, ordinal in (("zzz-late", 9), ("aaa-early", 2)):
        directory = root / name
        directory.mkdir(parents=True)
        (directory / "checkpoint.json").write_text(
            json.dumps(
                {
                    "adjudication": {},
                    "cluster_id": name,
                    "manifest_sha256": f"{ordinal:064d}",
                    "ordinal": ordinal,
                    "prev_cluster_id": None,
                    "timeline_sha256": "1" * 64,
                },
                sort_keys=True,
            )
        )

    records = completeness.checkpoint_records(root)

    assert [record["ordinal"] for _, record in records] == [2, 9]


def test_checkpoint_records_is_empty_when_root_absent(tmp_path: Path) -> None:
    assert completeness.checkpoint_records(tmp_path / "absent") == ()


def test_sparse_workspace_has_one_checkpoint_for_two_clusters(
    sparse_workspace: dict[str, Path],
) -> None:
    clusters = completeness.load_clusters(sparse_workspace["timeline"])
    records = completeness.checkpoint_records(sparse_workspace["checkpoints"])

    assert len(clusters) == 2
    assert len(records) == 1
```

- [ ] **Step 3: Run test to verify it fails**

Run: `SSLKEYLOGFILE= python -m pytest tests/unit/plugins/services/testers/a_rfc/draft/test_completeness.py -v`
Expected: FAIL — `ImportError: cannot import name 'completeness'`

- [ ] **Step 4: Write minimal implementation**

Create `draft/completeness.py`:

```python
"""Measure how much of a timeline a reconstruction has actually specified.

The citation gate checks that a draft is internally consistent: that every
revision cites only claims its checkpoint holds. It cannot say whether the
reconstruction is *finished*, because nothing in the workspace records how much
of the timeline was ever visited. This module answers that: which clusters
produced no claim, and which claims no prose cites.
"""

from __future__ import annotations

import json
from pathlib import Path

from .checkpoint import CHECKPOINT_FILE


class CompletenessError(ValueError):
    """Raised when the gate's inputs cannot be interpreted as written."""


def load_clusters(timeline_dir: Path) -> tuple[dict, ...]:
    """Read a timeline's clusters, ordered by ordinal.

    Args:
        timeline_dir: Directory written by the timeline stage.

    Returns:
        Every cluster row, ascending by ``ordinal``.

    Raises:
        CompletenessError: If ``clusters.jsonl`` is absent or malformed.
    """
    path = timeline_dir / "clusters.jsonl"
    try:
        lines = path.read_text().splitlines()
    except OSError as error:
        raise CompletenessError(f"could not read {path}: {error}") from error
    try:
        rows = [json.loads(line) for line in lines if line.strip()]
    except json.JSONDecodeError as error:
        raise CompletenessError(f"{path} is not valid JSON Lines: {error}") from error
    return tuple(sorted(rows, key=lambda row: row["ordinal"]))


def checkpoint_records(checkpoints_dir: Path) -> tuple[tuple[str, dict], ...]:
    """Read every checkpoint record, ordered by the ordinal each one names.

    Sorting on the recorded ordinal rather than the directory name is what makes
    claim attribution correct: directory names are cluster ids, and ids do not
    sort into processing order.

    Args:
        checkpoints_dir: The checkpoints root.

    Returns:
        Pairs of directory name and record, ascending by ``ordinal``. Empty when
        the root does not exist.

    Raises:
        CompletenessError: If a record is present but unreadable.
    """
    if not checkpoints_dir.is_dir():
        return ()
    records: list[tuple[str, dict]] = []
    for directory in sorted(checkpoints_dir.iterdir()):
        record_path = directory / CHECKPOINT_FILE
        if not record_path.exists():
            continue
        try:
            records.append((directory.name, json.loads(record_path.read_text())))
        except (OSError, json.JSONDecodeError) as error:
            raise CompletenessError(f"could not read {record_path}: {error}") from error
    return tuple(sorted(records, key=lambda pair: pair[1]["ordinal"]))
```

- [ ] **Step 5: Run test to verify it passes**

Run: `SSLKEYLOGFILE= python -m pytest tests/unit/plugins/services/testers/a_rfc/draft/test_completeness.py -v`
Expected: PASS, 5 tests

- [ ] **Step 6: Commit**

```bash
git add panther/plugins/services/testers/a_rfc/draft/completeness.py \
        tests/unit/plugins/services/testers/a_rfc/draft/conftest.py \
        tests/unit/plugins/services/testers/a_rfc/draft/test_completeness.py
git commit -m "feat(a_rfc): read timeline clusters and checkpoint records for completeness"
```

---

### Task 2: Attribute claims to the cluster that introduced them

**Files:**
- Modify: `panther/plugins/services/testers/a_rfc/draft/completeness.py`
- Test: `tests/unit/plugins/services/testers/a_rfc/draft/test_completeness.py`

**Interfaces:**
- Consumes: `load_clusters`, `checkpoint_records` (Task 1); `load`, `SchemaError` from `..schema`; `MANIFEST_FILE` from `.checkpoint`.
- Produces: `ClusterCompleteness` frozen dataclass — `cluster_id: str`, `ordinal: int`, `checkpointed: bool`, `new_claim_ids: tuple[str, ...]`, `manifest_changed: bool`; and `attribute_claims(timeline_dir, checkpoints_dir) -> tuple[ClusterCompleteness, ...]`.

**Why two measures.** A set difference over claim ids alone misses a checkpoint that promoted a claim's status or edited its text without adding an id. `manifest_changed` (digest inequality) catches those. A cluster counts as *silent* only when both say nothing happened.

**Why the predecessor in the sorted list.** Each record carries `prev_cluster_id`, but that names the timeline's ordinal−1 neighbour, which may never have been processed. Differencing against the previous *processed* checkpoint is what attributes claims correctly on a sparse run — exactly MARK's situation (clusters 49 and 69, nothing between).

- [ ] **Step 1: Write the failing test**

```python
def test_first_checkpoint_owns_every_claim_it_holds(
    draft_workspace: dict[str, Path],
) -> None:
    rows = completeness.attribute_claims(
        draft_workspace["timeline"], draft_workspace["checkpoints"]
    )
    by_ordinal = {row.ordinal: row for row in rows}

    assert by_ordinal[1].new_claim_ids == ("spec:1.1",)
    assert by_ordinal[1].checkpointed is True


def test_later_checkpoint_owns_only_its_additions(
    draft_workspace: dict[str, Path],
) -> None:
    rows = completeness.attribute_claims(
        draft_workspace["timeline"], draft_workspace["checkpoints"]
    )
    by_ordinal = {row.ordinal: row for row in rows}

    assert by_ordinal[2].new_claim_ids == ("spec:2.1",)
    assert by_ordinal[2].manifest_changed is True


def test_uncheckpointed_clusters_are_reported_as_such(
    sparse_workspace: dict[str, Path],
) -> None:
    rows = completeness.attribute_claims(
        sparse_workspace["timeline"], sparse_workspace["checkpoints"]
    )

    assert [row.checkpointed for row in rows] == [True, False]
    assert rows[1].new_claim_ids == ()


def test_attribution_covers_every_cluster_in_the_timeline(
    sparse_workspace: dict[str, Path],
) -> None:
    clusters = completeness.load_clusters(sparse_workspace["timeline"])
    rows = completeness.attribute_claims(
        sparse_workspace["timeline"], sparse_workspace["checkpoints"]
    )

    assert [row.cluster_id for row in rows] == [row["id"] for row in clusters]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `SSLKEYLOGFILE= python -m pytest tests/unit/plugins/services/testers/a_rfc/draft/test_completeness.py -v -k "owns or uncheckpointed or covers"`
Expected: FAIL — `AttributeError: module 'completeness' has no attribute 'attribute_claims'`

- [ ] **Step 3: Write minimal implementation**

Extend the imports and append to `completeness.py`:

```python
from dataclasses import dataclass

from ..schema import SchemaError, load
from .checkpoint import CHECKPOINT_FILE, MANIFEST_FILE


@dataclass(frozen=True)
class ClusterCompleteness:
    """What one timeline cluster contributed to the reconstruction."""

    cluster_id: str
    ordinal: int
    checkpointed: bool
    new_claim_ids: tuple[str, ...]
    manifest_changed: bool


def _claim_ids(checkpoint_dir: Path) -> frozenset[str]:
    """The claim ids held by a checkpoint's frozen manifest copy."""
    try:
        manifest = load(checkpoint_dir / MANIFEST_FILE)
    except (SchemaError, OSError) as error:
        raise CompletenessError(
            f"could not read {checkpoint_dir / MANIFEST_FILE}: {error}"
        ) from error
    return frozenset(claim.id for claim in manifest.claims)


def attribute_claims(
    timeline_dir: Path, checkpoints_dir: Path
) -> tuple[ClusterCompleteness, ...]:
    """Attribute each claim to the cluster whose checkpoint first held it.

    Each checkpoint is differenced against its predecessor in *processing*
    order, not against its timeline neighbour: on a sparse run the ordinal-1
    neighbour is usually unprocessed, and differencing against it would credit
    every claim to every checkpoint.

    Args:
        timeline_dir: Directory written by the timeline stage.
        checkpoints_dir: The checkpoints root.

    Returns:
        One row per timeline cluster, ascending by ordinal.

    Raises:
        CompletenessError: If any input is absent or malformed.
    """
    by_cluster: dict[str, ClusterCompleteness] = {}
    seen: frozenset[str] = frozenset()
    previous_digest: str | None = None
    for name, record in checkpoint_records(checkpoints_dir):
        held = _claim_ids(checkpoints_dir / name)
        digest = record["manifest_sha256"]
        by_cluster[record["cluster_id"]] = ClusterCompleteness(
            cluster_id=record["cluster_id"],
            ordinal=record["ordinal"],
            checkpointed=True,
            new_claim_ids=tuple(sorted(held - seen)),
            manifest_changed=digest != previous_digest,
        )
        seen = seen | held
        previous_digest = digest

    return tuple(
        by_cluster.get(
            row["id"],
            ClusterCompleteness(
                cluster_id=row["id"],
                ordinal=row["ordinal"],
                checkpointed=False,
                new_claim_ids=(),
                manifest_changed=False,
            ),
        )
        for row in load_clusters(timeline_dir)
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `SSLKEYLOGFILE= python -m pytest tests/unit/plugins/services/testers/a_rfc/draft/test_completeness.py -v`
Expected: PASS, 9 tests

- [ ] **Step 5: Commit**

```bash
git add panther/plugins/services/testers/a_rfc/draft/completeness.py \
        tests/unit/plugins/services/testers/a_rfc/draft/test_completeness.py
git commit -m "feat(a_rfc): attribute claims to the cluster whose checkpoint introduced them"
```

---

### Task 3: Find claims no prose cites

**Files:**
- Modify: `panther/plugins/services/testers/a_rfc/draft/gate.py`
- Modify: `panther/plugins/services/testers/a_rfc/draft/completeness.py`
- Test: `tests/unit/plugins/services/testers/a_rfc/draft/test_completeness.py`

**Interfaces:**
- Consumes: `cited_ids(draft_repo, tag) -> tuple[set[str], str | None]` and `load_revisions(path) -> tuple[RevisionEntry, ...]` from `.gate`. `RevisionEntry` carries `.tag`, `.number`, `.cluster_id`, `.checkpoint_manifest_sha256`, `.normative_change`, `.note`.
- Produces: `citation_gaps(draft_repo, revisions_path, claim_ids) -> tuple[tuple[str, ...], tuple[str, ...]]` returning `(uncited_at_head, never_cited)`.

**Why two answers.** `uncited_at_head` is the live question — what the current draft omits. `never_cited` additionally catches a claim cited once and later dropped, which `uncited_at_head` alone would report identically to one never written.

- [ ] **Step 1: Write the failing test**

```python
def test_gate_clean_workspace_has_no_citation_gaps(
    draft_workspace: dict[str, Path],
) -> None:
    uncited, never = completeness.citation_gaps(
        draft_workspace["repo"],
        draft_workspace["revisions"],
        frozenset({"spec:1.1", "spec:2.1"}),
    )

    assert uncited == ()
    assert never == ()


def test_uncited_at_head_lists_claims_the_latest_tag_omits(
    sparse_workspace: dict[str, Path],
) -> None:
    uncited, never = completeness.citation_gaps(
        sparse_workspace["repo"],
        sparse_workspace["revisions"],
        frozenset({"spec:1.1"}),
    )

    assert uncited == ("spec:1.1",)
    assert never == ("spec:1.1",)


def test_never_cited_excludes_a_claim_cited_then_dropped(
    draft_workspace: dict[str, Path], git
) -> None:
    """spec:2.1 is cited at -01; a -02 that drops it is uncited but not never."""
    repo = draft_workspace["repo"]
    (repo / "draft-test-spec.md").write_text(
        "# Spec\n\nThe system does the thing. `a_rfc:spec:1.1`\n"
    )
    git(repo, "add", "draft-test-spec.md")
    git(repo, "commit", "-m", "revision 02")
    git(repo, "tag", "draft-test-spec-02")
    revisions = draft_workspace["revisions"]
    revisions.write_text(
        revisions.read_text()
        + "  draft-test-spec-02:\n"
        + f"    cluster_id: {completeness.load_clusters(draft_workspace['timeline'])[1]['id']}\n"
        + f"    checkpoint_manifest_sha256: {'0' * 64}\n"
        + "    normative_change: true\n"
        + "    note: 'drops the second behaviour'\n"
    )

    uncited, never = completeness.citation_gaps(
        repo, revisions, frozenset({"spec:1.1", "spec:2.1"})
    )

    assert uncited == ("spec:2.1",)
    assert never == ()
```

Note: `git` is the module-level helper already defined in the draft conftest; expose it as a
fixture there if pytest does not resolve it as one — a two-line `@pytest.fixture def git(): return _git_helper` is acceptable, or import it directly in the test module.

- [ ] **Step 2: Run test to verify it fails**

Run: `SSLKEYLOGFILE= python -m pytest tests/unit/plugins/services/testers/a_rfc/draft/test_completeness.py -v -k cite`
Expected: FAIL — `AttributeError: module 'completeness' has no attribute 'citation_gaps'`

- [ ] **Step 3a: Rename the gate helper**

In `draft/gate.py`, rename the function at `:128` from `_cited_ids` to `cited_ids`, give it a
full Google-style docstring, and update its single call site inside `run_gate` (the
`cited, problem = _cited_ids(draft_repo, entry.tag)` line near `:248`):

```python
def cited_ids(draft_repo: Path, tag: str) -> tuple[set[str], str | None]:
    """Return the claim ids cited at ``tag``, or a finding when unreadable.

    Args:
        draft_repo: The nested prose-draft git repository.
        tag: The revision tag to read.

    Returns:
        The cited claim ids and ``None``; or an empty set and the reason the tag
        could not be read.
    """
```

- [ ] **Step 3b: Write the completeness implementation**

```python
from .gate import GateError, cited_ids, load_revisions


def citation_gaps(
    draft_repo: Path, revisions_path: Path, claim_ids: frozenset[str]
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Find claims the prose does not cite.

    Args:
        draft_repo: The nested prose-draft git repository.
        revisions_path: Path to ``revisions.yaml``.
        claim_ids: Every claim id the reconstruction currently holds.

    Returns:
        Two tuples: ids uncited at the highest-numbered revision tag, and ids
        cited at no tag at all. The second is a subset of the first.

    Raises:
        CompletenessError: If the revision map or the draft repo is unreadable.
    """
    try:
        entries = load_revisions(revisions_path)
    except (GateError, OSError) as error:
        raise CompletenessError(f"could not read {revisions_path}: {error}") from error
    if not entries:
        return tuple(sorted(claim_ids)), tuple(sorted(claim_ids))

    ever: set[str] = set()
    head: set[str] = set()
    highest = max(entry.number for entry in entries)
    for entry in entries:
        cited, problem = cited_ids(draft_repo, entry.tag)
        if problem is not None:
            raise CompletenessError(problem)
        ever |= cited
        if entry.number == highest:
            head = cited
    return tuple(sorted(claim_ids - head)), tuple(sorted(claim_ids - ever))
```

- [ ] **Step 4: Run the whole draft suite**

Run: `SSLKEYLOGFILE= python -m pytest tests/unit/plugins/services/testers/a_rfc/draft/ -v`
Expected: PASS — 12 completeness tests, **and every pre-existing `test_gate.py` test still green**, which is what proves the rename did not break `run_gate`.

- [ ] **Step 5: Commit**

```bash
git add panther/plugins/services/testers/a_rfc/draft/completeness.py \
        panther/plugins/services/testers/a_rfc/draft/gate.py \
        tests/unit/plugins/services/testers/a_rfc/draft/test_completeness.py
git commit -m "feat(a_rfc): report claims no revision of the prose cites"
```

---

### Task 4: Assemble the report

**Files:**
- Modify: `panther/plugins/services/testers/a_rfc/draft/completeness.py`
- Test: `tests/unit/plugins/services/testers/a_rfc/draft/test_completeness.py`

**Interfaces:**
- Produces: `CompletenessReport` frozen dataclass; `build(timeline_dir, checkpoints_dir, manifest_path, revisions_path, draft_repo) -> CompletenessReport`; `to_json(report) -> str`; `findings(report) -> tuple[str, ...]`.

`manifest_drift` compares the **live** manifest against the union of all checkpointed ids — claims mined but never frozen. Fractions round to 4 places so the JSON stays byte-reproducible.

- [ ] **Step 1: Write the failing test**

```python
def test_build_on_a_clean_workspace_reports_nothing_outstanding(
    draft_workspace: dict[str, Path], tmp_path: Path
) -> None:
    report = completeness.build(
        draft_workspace["timeline"],
        draft_workspace["checkpoints"],
        tmp_path / "m2.yaml",
        draft_workspace["revisions"],
        draft_workspace["repo"],
    )

    assert report.unprocessed_clusters == ()
    assert report.uncited_at_head == ()
    assert report.manifest_drift == ()
    assert report.totals["processed_fraction"] == 1.0
    assert completeness.findings(report) == ()


def test_build_on_a_sparse_workspace_reports_the_gaps(
    sparse_workspace: dict[str, Path],
) -> None:
    report = completeness.build(
        sparse_workspace["timeline"],
        sparse_workspace["checkpoints"],
        sparse_workspace["manifest"],
        sparse_workspace["revisions"],
        sparse_workspace["repo"],
    )

    assert len(report.unprocessed_clusters) == 1
    assert report.uncited_at_head == ("spec:1.1",)
    assert report.totals["clusters_total"] == 2
    assert report.totals["clusters_processed"] == 1
    assert report.totals["processed_fraction"] == 0.5
    assert any("1 of 2" in finding for finding in completeness.findings(report))


def test_to_json_is_byte_stable(sparse_workspace: dict[str, Path]) -> None:
    args = (
        sparse_workspace["timeline"],
        sparse_workspace["checkpoints"],
        sparse_workspace["manifest"],
        sparse_workspace["revisions"],
        sparse_workspace["repo"],
    )

    first = completeness.to_json(completeness.build(*args))
    second = completeness.to_json(completeness.build(*args))

    assert first == second
    assert first.endswith("\n")
    assert json.loads(first)["totals"]["clusters_total"] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `SSLKEYLOGFILE= python -m pytest tests/unit/plugins/services/testers/a_rfc/draft/test_completeness.py -v -k "build or byte_stable"`
Expected: FAIL — `AttributeError: module 'completeness' has no attribute 'build'`

- [ ] **Step 3: Write minimal implementation**

```python
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class CompletenessReport:
    """How much of a timeline the reconstruction has specified."""

    clusters: tuple[ClusterCompleteness, ...]
    unprocessed_clusters: tuple[str, ...]
    silent_clusters: tuple[str, ...]
    uncited_at_head: tuple[str, ...]
    never_cited: tuple[str, ...]
    manifest_drift: tuple[str, ...]
    totals: dict[str, float]


def build(
    timeline_dir: Path,
    checkpoints_dir: Path,
    manifest_path: Path,
    revisions_path: Path,
    draft_repo: Path,
) -> CompletenessReport:
    """Measure a workspace's reconstruction completeness.

    Args:
        timeline_dir: Directory written by the timeline stage.
        checkpoints_dir: The checkpoints root.
        manifest_path: The live manifest.
        revisions_path: Path to ``revisions.yaml``.
        draft_repo: The nested prose-draft git repository.

    Returns:
        The assembled report.

    Raises:
        CompletenessError: If any input is absent or malformed.
    """
    rows = attribute_claims(timeline_dir, checkpoints_dir)
    checkpointed: frozenset[str] = frozenset()
    for name, _ in checkpoint_records(checkpoints_dir):
        checkpointed = checkpointed | _claim_ids(checkpoints_dir / name)

    try:
        live = frozenset(claim.id for claim in load(manifest_path).claims)
    except (SchemaError, OSError) as error:
        raise CompletenessError(f"could not read {manifest_path}: {error}") from error

    uncited_at_head, never_cited = citation_gaps(
        draft_repo, revisions_path, checkpointed
    )
    processed = sum(1 for row in rows if row.checkpointed)
    return CompletenessReport(
        clusters=rows,
        unprocessed_clusters=tuple(
            row.cluster_id for row in rows if not row.checkpointed
        ),
        silent_clusters=tuple(
            row.cluster_id
            for row in rows
            if row.checkpointed and not row.new_claim_ids and not row.manifest_changed
        ),
        uncited_at_head=uncited_at_head,
        never_cited=never_cited,
        manifest_drift=tuple(sorted(live - checkpointed)),
        totals={
            "checkpointed_claims": len(checkpointed),
            "clusters_processed": processed,
            "clusters_total": len(rows),
            "processed_fraction": round(processed / len(rows), 4) if rows else 0.0,
            "uncited_at_head": len(uncited_at_head),
        },
    )


def to_json(report: CompletenessReport) -> str:
    """Serialize a report byte-stably.

    Args:
        report: The report to serialize.

    Returns:
        Sorted-key JSON with a trailing newline.
    """
    return (
        json.dumps(
            {
                "clusters": [asdict(row) for row in report.clusters],
                "manifest_drift": list(report.manifest_drift),
                "never_cited": list(report.never_cited),
                "silent_clusters": list(report.silent_clusters),
                "totals": report.totals,
                "uncited_at_head": list(report.uncited_at_head),
                "unprocessed_clusters": list(report.unprocessed_clusters),
            },
            sort_keys=True,
            indent=2,
        )
        + "\n"
    )


def findings(report: CompletenessReport) -> tuple[str, ...]:
    """Render a report as one diagnostic line per gap.

    Args:
        report: The report to describe.

    Returns:
        The findings, empty when the reconstruction is complete.
    """
    lines: list[str] = []
    if report.unprocessed_clusters:
        lines.append(
            f"{len(report.unprocessed_clusters)} of "
            f"{int(report.totals['clusters_total'])} clusters were never "
            f"checkpointed"
        )
    for cluster_id in report.silent_clusters:
        lines.append(f"{cluster_id}: checkpointed but changed no claim")
    for claim_id in report.uncited_at_head:
        lines.append(f"{claim_id}: no revision of the prose cites it at head")
    for claim_id in report.manifest_drift:
        lines.append(f"{claim_id}: in the live manifest but in no checkpoint")
    return tuple(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `SSLKEYLOGFILE= python -m pytest tests/unit/plugins/services/testers/a_rfc/draft/ -v`
Expected: PASS, 15 completeness tests plus every pre-existing draft test

- [ ] **Step 5: Commit**

```bash
git add panther/plugins/services/testers/a_rfc/draft/completeness.py \
        tests/unit/plugins/services/testers/a_rfc/draft/test_completeness.py
git commit -m "feat(a_rfc): assemble the completeness report"
```

---

### Task 5: Ship the CLI verb and fix the exit-code help

**Files:**
- Modify: `panther/plugins/services/testers/a_rfc/draft/cli.py`
- Test: `tests/unit/plugins/services/testers/a_rfc/draft/test_completeness.py`

**Interfaces:**
- Consumes: `build`, `to_json`, `findings`, `CompletenessError` from `.completeness`.
- Produces: `python -m panther.plugins.services.testers.a_rfc.draft completeness <workspace> --out DIR [--strict]`.

**Two things here, deliberately together** — they edit the same file, so one agent must own it.

1. The new verb takes a **workspace root positional** and derives `timeline/`,
   `checkpoints/`, `manifest.yaml`, `revisions.yaml`, `draft/` from it — unlike `gate`, which
   takes five separate required paths. That divergence is intentional: five required flags for
   one workspace is friction this verb should not inherit. The `sparse_workspace` fixture is
   laid out to match.
2. **Defect A2a.** `draft/cli.py:74` reads `help="Exit 2 when any finding is reported."` while
   the code returns **3** (`:121-122`) and its own docstring says 3. The suite reserves 2 for
   argparse (`cli.py:74-78`), so the help is actively misleading.

- [ ] **Step 1: Write the failing test**

```python
from panther.plugins.services.testers.a_rfc.draft import cli as draft_cli


def test_completeness_verb_writes_report_and_exits_zero(
    sparse_workspace: dict[str, Path], tmp_path: Path
) -> None:
    code = draft_cli.main(
        [
            "completeness",
            str(sparse_workspace["root"]),
            "--out",
            str(tmp_path / "out"),
        ]
    )

    assert code == 0
    written = json.loads((tmp_path / "out" / "completeness.json").read_text())
    assert written["totals"]["clusters_total"] == 2
    assert len(written["unprocessed_clusters"]) == 1


def test_completeness_verb_exits_three_under_strict(
    sparse_workspace: dict[str, Path], tmp_path: Path
) -> None:
    code = draft_cli.main(
        [
            "completeness",
            str(sparse_workspace["root"]),
            "--out",
            str(tmp_path / "out"),
            "--strict",
        ]
    )

    assert code == 3


def test_completeness_verb_exits_one_on_unreadable_input(tmp_path: Path) -> None:
    code = draft_cli.main(
        ["completeness", str(tmp_path / "absent"), "--out", str(tmp_path / "out")]
    )

    assert code == 1


def test_gate_strict_help_states_the_code_it_actually_returns() -> None:
    """draft/cli.py:74 claimed exit 2; the code returns 3."""
    parser = draft_cli._parser()
    subparsers = next(
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    strict = next(
        action
        for action in subparsers.choices["gate"]._actions
        if action.dest == "strict"
    )

    assert "3" in strict.help
    assert "Exit 2" not in strict.help
```

Add `import argparse` to the test module's imports.

- [ ] **Step 2: Run test to verify it fails**

Run: `SSLKEYLOGFILE= python -m pytest tests/unit/plugins/services/testers/a_rfc/draft/test_completeness.py -v -k "verb or strict_help"`
Expected: FAIL — argparse `invalid choice: 'completeness'`, and the help assertion fails on the literal `Exit 2`.

- [ ] **Step 3: Write minimal implementation**

In `draft/cli.py`, add the imports:

```python
from .completeness import CompletenessError
from .completeness import build as build_completeness
from .completeness import findings as completeness_findings
from .completeness import to_json as completeness_json
```

Replace the gate `--strict` help at `:72-76`:

```python
    gate.add_argument(
        "--strict",
        action="store_true",
        help="Exit 3 when any finding is reported.",
    )
```

Add the third verb after the gate parser, before `return parser`:

```python
    complete = verbs.add_parser(
        "completeness",
        help="Report which clusters produced no claim and which claims no "
        "prose cites.",
    )
    complete.add_argument(
        "workspace",
        type=Path,
        help="Workspace root holding timeline/, checkpoints/, draft/, "
        "manifest.yaml and revisions.yaml.",
    )
    complete.add_argument(
        "--out", type=Path, required=True, help="Directory for completeness.json."
    )
    complete.add_argument(
        "--strict",
        action="store_true",
        help="Exit 3 when any finding is reported.",
    )
```

Add the branch in `main`, immediately after the `checkpoint` branch returns:

```python
    if args.verb == "completeness":
        workspace = args.workspace
        try:
            report = build_completeness(
                workspace / "timeline",
                workspace / "checkpoints",
                workspace / "manifest.yaml",
                workspace / "revisions.yaml",
                workspace / "draft",
            )
        except (CompletenessError, OSError) as error:
            _report(f"error: {error}")
            return 1

        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "completeness.json").write_text(completeness_json(report))

        found = completeness_findings(report)
        for finding in found:
            _report(f"finding: {finding}")
        if not found:
            _report("note: reconstruction complete")
        if found and args.strict:
            return 3
        return 0
```

Update `main`'s docstring Returns section to name `completeness` alongside `gate`.

- [ ] **Step 4: Run test to verify it passes**

Run: `SSLKEYLOGFILE= python -m pytest tests/unit/plugins/services/testers/a_rfc/ -v`
Expected: PASS — 19 completeness tests; every pre-existing `a_rfc` test green; collected count strictly above the 588 baseline.

- [ ] **Step 5: Commit**

```bash
git add panther/plugins/services/testers/a_rfc/draft/cli.py \
        tests/unit/plugins/services/testers/a_rfc/draft/test_completeness.py
git commit -m "feat(a_rfc): add the draft completeness verb; fix the gate --strict exit-code help"
```

---

### Task 6: Verify against MARK, and publish the docs

**Files:**
- Modify: `panther/plugins/services/testers/a_rfc/README.md`
- Modify: `mkdocs.yml`, `docs_src/`

**This is the task that proves the feature.** MARK is real, frozen data with a known answer: 69 clusters, 2 checkpointed, so **67 unprocessed**. Synthetic fixtures cannot catch a shape mismatch against production data; this can.

- [ ] **Step 1: Run against the real MARK workspace**

```bash
SSLKEYLOGFILE= python -m panther.plugins.services.testers.a_rfc.draft completeness \
    reconstructions/mark --out /tmp/mark-completeness
```

Expected on stderr: `finding: 67 of 69 clusters were never checkpointed`, plus one line per uncited claim.

- [ ] **Step 2: Confirm the numbers against the frozen record**

```bash
python -c "
import json
r = json.load(open('/tmp/mark-completeness/completeness.json'))
assert r['totals']['clusters_total'] == 69, r['totals']
assert r['totals']['clusters_processed'] == 2, r['totals']
assert len(r['unprocessed_clusters']) == 67
print('MARK:', r['totals'])
"
```

Expected: prints the totals, exits 0. If `clusters_processed` is not 2, **stop** — the attribution logic disagrees with `reconstructions/mark/checkpoints/`, which holds exactly `c0049-pr-ba8ca432c304` and `c0069-epoch-b901f36095d7`.

- [ ] **Step 3: Confirm the citation gate still passes on the frozen tags**

```bash
SSLKEYLOGFILE= python -m panther.plugins.services.testers.a_rfc.draft gate \
    reconstructions/mark/draft \
    --timeline reconstructions/mark/timeline \
    --checkpoints reconstructions/mark/checkpoints \
    --questions reconstructions/mark/questions.yaml \
    --revisions reconstructions/mark/revisions.yaml \
    --out /tmp/mark-gate --strict; echo "exit=$?"
```

Expected: `exit=0`. This is the regression guard for Task 3's rename — the gate must still parse both historical tags of MARK's real draft repo. A non-zero exit means `cited_ids` broke `run_gate`, and green unit tests would not have told you.

- [ ] **Step 4: Document the verb**

Add a `## Completeness` section to `panther/plugins/services/testers/a_rfc/README.md`: what the verb measures, the difference between `uncited_at_head` and `never_cited`, why attribution uses the previous *processed* checkpoint, and the 0/1/3 exit contract. Then add `a_rfc` to `mkdocs.yml`'s nav with a page under `docs_src/` — today `grep -ril "a_rfc\|arfc" mkdocs.yml docs_src` returns nothing, so this is the tool's first appearance in the published documentation.

- [ ] **Step 5: Full suite, then commit**

```bash
SSLKEYLOGFILE= python -m pytest tests/ -n auto -m unit
git add panther/plugins/services/testers/a_rfc/README.md mkdocs.yml docs_src
git commit -m "docs(a_rfc): document the completeness verb and publish a_rfc to the docs site"
```

Do **not** run `panther_builder.py package-dev` or `clean` before committing — both `rm -rf` the `docs/` directory.

---

## Self-review

**Spec coverage.** Every design element is claimed by a task: fixture + readers → Task 1; attribution with both measures → Task 2; the two citation questions → Task 3; report, JSON, findings → Task 4; CLI verb, exit codes and defect A2a → Task 5; MARK verification and the docs gap → Task 6.

**Placeholders.** None. Every code step is runnable; every test asserts a concrete value; every command is copy-pasteable.

**Type consistency.** `ClusterCompleteness` is defined once (Task 2) and used unchanged. `cited_ids` returns `tuple[set[str], str | None]` in Task 3 and is consumed with that shape. `citation_gaps` takes `frozenset[str]`; Task 4 passes `checkpointed`, a `frozenset`. `totals` is `dict[str, float]`, so `== 2` on `clusters_total` holds (`2 == 2.0`).

**Two known wrinkles, both deliberate.**
- Task 5's help-text test reaches into argparse's `_actions`/`_SubParsersAction` internals. It is the only way to assert help text without shelling out. If it proves brittle, replace it with a subprocess call to `--help` plus a substring assertion — do **not** delete it, because an untested help string is exactly how the `Exit 2` error survived.
- Task 3's third test mutates `draft_workspace` in place to add a third tag. That is safe because the fixture is function-scoped on `tmp_path`, but it does depend on the fixture's internal layout (`draft-test-spec.md`, tag naming). If the conftest changes, that test changes with it.

---

## Roadmap — the other four plans

Ordering is forced by file ownership, not preference.

| Plan | Contents | Why this order |
|---|---|---|
| 2. Defects | A1 `guard.py` fail-open (`:29-32` catches only `JSONDecodeError`/`ValueError`, so a non-dict payload raises `AttributeError`, exits 1, and the hook **fails open** — only exit 2 blocks); A2b `experiment/cli.py`'s undocumented exit 2; A3 absence notes for `timeline --repo` and `views --forge`; A4 ~25 missing `help=` on the agent-facing `ai_rfc_server/cli.py` plus its `:161` docstring; A5 five missing `__main__` guards | Disjoint files; the only genuine fan-out |
| 3. Simplification | SHA-256 helper duplicated ~10×, filename triplet in 4 places, `MCP_FILE`/`MCP_CONFIG`, `RAW_PREFIX`/`RAW_SUBSTRATE`, hardcoded markdown column counts | **Before** the rename, so each renamed literal has exactly one definition site |
| 4. Naming `arfc`→`ai_rfc` | C1 internal (`class1`/`class2` → `mcp_surface_errors`/`bash_surface_errors`; `profile.py` → `login_profile.py`; `AI_RFC_ROOT` → `_plugin_root`); C2 env vars; C3 console script; C4 dual-accept citation regex; C5 MCP key + 16 tool names | Strictly by blast radius, one commit per tier |
| 5. Sweep driver | `ai_rfc/sweep/` — resume derived from disk (the artifact triple, since `checkpoint.py:68-73` poisons blind retry), budget-capped, timeline digest pinned. Note `pipeline.next_stage()` **cannot** drive the loop: it is workspace-granular and returns `DONE` after the first claim (`state.py:180-191`) | Needs this plan's completeness gate as its success measure |

## Status as of 2026-09-01

Plans 1, 2 and 3 are complete and committed. The package directory rename also
landed: `testers/a_rfc` → `testers/ai_rfc`, submodule at `ai_rfc/harness`,
import path `panther.plugins.services.testers.ai_rfc`, single version with no
alias or compat branch.

**Superseded decision.** This plan previously mandated *emit-new, accept-both,
permanently* for every wire rename. That is now **withdrawn** at the user's
direction: carry a single version and no legacy branch, per CLAUDE.md's "do NOT
add backward compatibility shims when refactoring". The accepted cost is
recorded with each item below rather than hidden.

---

## Plan 6 (final phase) — one spelling everywhere, no compat

Everything below still carries the old spelling. The goal is a single version:
no dual-accept, no alias, no legacy branch. Ordered by blast radius.

| # | Surface | Files | Cost of the single-version cut |
|---|---|---|---|
| 6.1 | Internal names: `class1`/`class2` → `mcp_surface_errors`/`bash_surface_errors`; `profile.py` → `login_profile.py`; `AI_RFC_ROOT` → `_plugin_root`; expand `AUC` in its docstring | few | none |
| 6.2 | Surface labels `bash:arfc`, `bash:python_a_rfc`, `_A_RFC`, canaries `ARFC-CANARY-7731` / `ARFC-OK` | few | none — internal to the audit |
| 6.3 | Env vars `ARFC_WORKSPACE`, `ARFC_EXPERIMENTS_ROOT` → `AI_RFC_*` | 36 | any shell, `.mcp.json` or saved profile using the old names stops resolving; no fallback |
| 6.4 | Console script `arfc` → `ai_rfc`; skills `arfc-*`; commands `/arfc-*`; config file `arfc.json` | ~20 | users retype the slash commands; the committed enforcement fixture keys on the literal `"arfc "` prefix and must be regenerated, not edited |
| 6.5 | MCP server key `arfc` and all 16 `arfc_*` tools → `ai_rfc_*` | 21 | every `mcp__arfc__*` entry in a user's `settings.json` allowlist stops matching and must be updated — a required migration note, not an afterthought |
| 6.6 | Citation prefix `` `a_rfc:<id>` `` → `` `ai_rfc:<id>` `` | 13 | **the sharp one**, see below |
| 6.7 | Forge provenance stamp `a_rfc.forge/1` | 1 code + 3 committed `meta.json` | old snapshots no longer match the current stamp |

### 6.6 is the one that needs a decision before it starts

`draft/gate.py` re-parses **historical git tags**: it runs `git show <tag>:<file>`
over every past revision and applies today's `CITATION` regex.
`reconstructions/mark/draft` carries two real tags whose frozen prose says
`a_rfc:`. Changing the regex with no legacy branch makes the gate see **zero**
citations in both, which trips the "no normative change" invariant as a false
failure — verified today that the gate is currently clean on exactly those tags.

With compat ruled out, there are two honest options, and they are a **user
decision**, not an implementation detail:

- **Regenerate MARK's reconstruction** so its tags cite `ai_rfc:`. Treats the
  reconstruction as reproducible working data. Costs a re-run of the 2-cluster
  vertical slice; the frozen `RUN.md` stays as the historical record.
- **Retire the frozen MARK draft repo** and accept that the pre-rename slice is
  no longer gate-checkable, keeping it only as an archived artifact.

Rewriting the tagged prose in place is not an option: it rewrites published
history to match a later rename, which is the falsification this tool exists to
prevent.

### Already accepted, single-version costs

- `experiment audit` can no longer re-derive the 2026-08-31 aioquic pilot's
  metrics: those transcripts name the old package and the classifier now has one
  branch. The published `report.md` stands.
- `reconstructions/*/RUN.md` keep the old command lines on purpose — they record
  what was actually executed, and are documentation of history, not code.

### Verification for plan 6

Per tier: full suite green, then re-run `draft gate --strict` and
`draft completeness` against `reconstructions/mark`. For 6.6 specifically, the
gate result is the *point* of the tier — decide the MARK question first, then
make the gate prove the chosen outcome rather than discovering it.
