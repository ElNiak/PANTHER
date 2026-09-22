# ai_rfc Future-Free Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop a run from seeing its repository's future. A windowed pristine is built at the
window's end commit and holds nothing after it. Every copy of it is checked for history it should
not have. `cluster_get` refuses clusters after the window. Every file tool and every Bash path an
arm uses is confined to the run's workspace.

**Architecture:**
- **The clone.** `acquire` clones every workspace with `--no-local --revision=<pin>` and removes
  `origin`, so a clone stores only its pin's history.
- **The cut.** `workspace prepare` runs a resolution pass over the operator's pin in scratch space.
  It finds the end commit there: the last member of the window's top cluster. It cuts the forge
  snapshot at that commit by rule R1, and builds the pristine at it. It then asserts three things:
  the window's timeline rows are byte-equal to the resolution pass's, the corpus holds nothing
  after the end, and the clone's objects are exactly HEAD's history.
- **Copies.** `copy_workspace`, `reseal` and the audit re-check the clone against an object-set
  digest sealed in `pristine.json`.
- **The guard.** The existing `PreToolUse` guard gains the workspace as an argument and is mounted
  for the file tools as well as Bash. The audit reads every call with the same predicate.

**Tech Stack:** Python 3.10 (`<wt>/.venv`), pytest + xdist, git ≥ 2.49 (subprocess), PyYAML.

**Spec:** `docs/superpowers/specs/2026-09-21-arfc-ground-truth-yardstick-design.md` (PANTHER), as
amended 2026-09-22:
- §7.1 future-free prepare, §7.2 clusters after the window, and §7.4 the path guard;
- the prevention half of §7.3: git honesty in the audit, and route 5;
- the second D-row in §8, the prepare, copy, guard and `cluster_get` tests in §9, and the documents
  in §10;
- the answers in §11.

The rulings behind it were made with the user on 2026-09-22 in the session that wrote this plan;
§11 of the spec lists them. The measurement half is
`docs/superpowers/plans/2026-09-21-arfc-ground-truth-measurement.md`. **This plan runs after it**,
because both edit `experiment/audit.py`, and its Task 8 builds on that plan's
`classify_future`.

Path shorthands:
- `<wt>` = the PANTHER worktree `…/PANTHER/master/.claude/worktrees/iut-ai-rfc`.
- `<ai_rfc>` = `<wt>/panther/plugins/services/testers/ai_rfc` (the ai_rfc repo, branch `main`).
- `<evidence>` = `~/ai-rfc-experiments/pristine/aioquic-w02-11`. Its `clone/` is at the tip
  `6d36838`, and it holds all 342 clusters. **It is read-only evidence: never write there.**

## Global Constraints

- **Cost and credentials:** $0, with one exception: Task 11 Step 6 (the preflight's live calls)
  spends, and it stops for the user's approval first. Never use an Anthropic API key.
- **Running tests:** run every test from `<ai_rfc>` with
  `SSLKEYLOGFILE= <wt>/.venv/bin/python -m pytest <paths> -q -n 4 --basetemp
  /tmp/claude-501/pytest-ffw-<task>`. Never use `-n auto`, which hangs. Report collected, passed,
  failed and skipped separately, never as a total.
- **Git discipline:**
  - Stage by explicit path, and run `git status --short` in every repo you touch before each commit.
  - Never `git add -A` / `git add .`, `--no-verify`, `git stash`, or amending a commit on the
    branch.
  - Commit with the paths as a pathspec: `git commit -m … -- <paths>`.
- **No compatibility shims.**
  - A replaced field, argument or function is removed, and every caller is updated in the same task.
  - Pristines prepared before this plan are **refused** by `copy_workspace`, never exempted. They
    have an `origin` remote, and aioquic's also store objects past their end. They stay read-only
    evidence.
- **Evidence is read-only.** Never write under `~/ai-rfc-experiments/pristine/`,
  `~/ai-rfc-experiments/campaigns/`, `~/ai-rfc-experiments/rebuild-sp7d/` or `~/arfc-experiments/`.
  Cloning from `<evidence>/clone` with `--no-local` only reads it, and so does copying a pristine to
  `/tmp`.
- **The end commit is derived, never typed.**
  - A pin is a branch, a tag or a full commit id. An abbreviated id is refused.
  - `--depth` is never used, because the substrate refuses shallow clones.
  - There is no fallback for a git older than 2.49.
- **Unmeasured is never zero:** a check that could not run says so (`measured: false` plus a
  reason). It never reports an empty problem list as if it had passed.
- **Code citations** go by function name; line numbers drift. **Docstrings** are Google-style on
  every public function. **Commit messages** carry no attribution lines.

## File Structure

| File | Responsibility | Tasks |
|---|---|---|
| `<ai_rfc>/ai_rfc/lifecycle/workspace.py` | `clone_object_problems`, `clone_object_record` (new); `acquire` clones at the pin and drops `origin` | 1, 2 |
| `<ai_rfc>/ai_rfc/forge/store.py` | `write_snapshot` records `derived_from` / `truncated_at` | 3 |
| `<ai_rfc>/ai_rfc/forge/adopt.py` | `adopt_snapshot` carries them; `carried_ceiling` (new, shared) | 3 |
| `<ai_rfc>/ai_rfc/forge/cut.py` | **New.** Rule R1: `cut_snapshot`, `SnapshotCut` | 3 |
| `<ai_rfc>/ai_rfc/experiment/workspace.py` | `resolve_cut`, `WindowCut` (new); `prepare` builds at the end and asserts the cut; `copy_workspace` / `reseal` check git honesty | 4, 5 |
| `<ai_rfc>/ai_rfc/experiment/cli.py` | The prepare verb prints the cut | 4 |
| `<ai_rfc>/ai_rfc/server/core/clusters.py`, `server/core/queries.py` | `refuse_after_the_window` (new); `cluster_get` calls it | 6 |
| `<ai_rfc>/ai_rfc/driver/enforcement.py` | `FILE_TOOLS`, `GUARDED_TOOLS`, `REMOTE_GIT`, `outside_paths`, `remote_git`, `refusal` (new); `render_settings` takes the workspace and mounts every guarded tool | 7 |
| `<ai_rfc>/ai_rfc/driver/guard.py` | Reads `tool_name` and the workspace argument; asks `refusal` | 7 |
| `<ai_rfc>/ai_rfc/driver/session.py` | Passes the workspace to `render_settings` | 7 |
| `<ai_rfc>/ai_rfc/experiment/audit.py` | `in_arm` asks `refusal`; `guard_stats` counts guarded calls; `clone_objects_audit`, `with_git_route` (new); `audit_run` carries `clone_objects` | 8 |
| `<ai_rfc>/ai_rfc/experiment/preflight.py` | The `read_denial` check; `render_settings` gets a workspace | 7, 9 |
| `<ai_rfc>/ai_rfc/experiment/README.md`, `<ai_rfc>/CONTEXT.md` | The guard's description; three glossary terms | 10 |
| `<wt>/docs/superpowers/specs/2026-09-02-arfc-draft-quality-design.md` | The second D-row (PANTHER) | 10 |
| Tests: `tests/experiment/test_clone_objects.py` (new), `tests/cli/test_init.py`, `tests/substrate/forge/test_cut.py` (new), `tests/experiment/test_prepare_cut.py` (new), `tests/experiment/test_workspace.py`, `tests/server/test_core.py`, `tests/driver/test_enforcement.py`, `tests/experiment/test_runner.py`, `tests/experiment/test_audit.py`, `tests/experiment/test_preflight.py` | | 1–9 |

---

## Task 0: Entry gate (no code)

- [ ] **Step 1: the two rows before this one have landed.** This plan edits files that the
  owed-fixes row and the measurement plan also change. Check both:
  - The owed-fixes row's hand-over (its Task 13) is done.
  - The measurement plan's Task 10 hand-over is done. `ai_rfc/experiment/future.py` exists on
    `main`, with `classify_future`.
  - ai_rfc `main` is clean. Check with `ListAgents` and the rows' handoff memory files.

  If either row is still running, stop and report.
- [ ] **Step 2: re-read the sites by name.** Confirm each of these exists on `main`:
  - in `lifecycle/workspace.py`: `acquire`, `_run_git`, `_git`, `write_digest`, `RECORD_FILE`,
    `Layout`;
  - in `lifecycle/init/cli.py`: `initialise`, `_fill`;
  - in `experiment/workspace.py`: `prepare`, `_carry_through_the_stages`, `copy_workspace`, `reseal`,
    `PREPARED_STAGES`, `_git_checked`;
  - in `forge/store.py`: `write_snapshot`, `read_snapshot`, `META_FILE`; in `forge/adopt.py`:
    `adopt_snapshot`;
  - in `timeline/build.py`: `_match_pulls`; in `timeline/store.py`: `read_clusters`,
    `MEMBERS_FILE`; in `timeline/corpus.py`: `read_commits`;
  - in `server/core/queries.py`: `cluster_get`; in `server/core/clusters.py`:
    `checked_cluster_id`; in `ledger.py`: `window_of`, `LedgerError`;
  - in `driver/enforcement.py`: `is_allowed`, `command_groups`, `bash_prefixes`, `render_settings`,
    `_CONTINUATION`; `driver/guard.py`'s `main`; in `driver/session.py`: `prepare_argv`;
  - in `experiment/audit.py`: `in_arm`, `guard_stats`, `audit_events`, `audit_run`, and
    `audit_run`'s `future_material` key from the measurement plan;
  - in `experiment/preflight.py`: `build_invocations`, `prepare_scratch`, `evaluate`, `CHECKS`.

  If one of them moved or was renamed, record its new name in this plan's deviation log before
  using it.
- [ ] **Step 3: the environment.**
  - `git --version` reports 2.49 or later.
  - `/usr/bin/git --version` exits 0. An unaccepted Xcode licence fails about 60 tests.
  - `<evidence>/clone` exists.
- [ ] **Step 4: the baseline.** Run the full suite (`tests/`) with the Global Constraints command,
  and record collected, passed, failed and skipped. Known flakes pass when run alone.

## Task 1: Git honesty for a clone

Spec §7.1, "Git honesty is asserted everywhere". Research 11 measured that the seal
(`write_digest`) skips `.git`, so a clone storing the tip verified clean.

**Files:**
- Modify: `ai_rfc/lifecycle/workspace.py` (add two functions beside `write_digest`)
- Test: `tests/experiment/test_clone_objects.py` (new)

**Interfaces:**
- Produces: `clone_object_problems(clone: Path) -> list[str]`, which is empty when the clone has no
  remote, no alternates, and stores exactly HEAD's objects.
- Produces: `clone_object_record(clone: Path) -> dict[str, Any]`, which returns
  `{"count": int, "sha256": str}` over the sorted stored object ids.
- Both raise `LifecycleError` when git cannot read the repository.

- [ ] **Step 1: Write the failing tests**

```python
"""A clone holds its pin's history and nothing else, or says why not."""

import subprocess
from pathlib import Path

import pytest

from ai_rfc.lifecycle.workspace import clone_object_problems, clone_object_record
from ai_rfc.server.testing import git

pytestmark = pytest.mark.unit


@pytest.fixture
def source(tmp_path: Path) -> tuple[Path, str, str]:
    """A two-commit repository: the first commit is the pin, the second its future."""
    repo = tmp_path / "source"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@t")
    git(repo, "config", "user.name", "t")
    shas = []
    for name, when in (("a", "2026-01-01T00:00:01+00:00"), ("b", "2026-01-01T00:00:02+00:00")):
        (repo / f"{name}.txt").write_text(f"{name}\n")
        git(repo, "add", f"{name}.txt")
        git(repo, "commit", "-q", "-m", name, date=when)
        shas.append(git(repo, "rev-parse", "HEAD"))
    return repo, shas[0], shas[1]


def _clone_at(source: Path, rev: str, dest: Path) -> Path:
    subprocess.run(
        ["git", "clone", "-q", "--no-local", f"--revision={rev}", str(source), str(dest)],
        check=True,
        capture_output=True,
    )
    git(dest, "remote", "remove", "origin")
    return dest


def test_a_clone_of_its_pin_s_history_has_no_problem(source, tmp_path):
    repo, first, _ = source
    assert clone_object_problems(_clone_at(repo, first, tmp_path / "clone")) == []


def test_a_remote_is_a_problem(source, tmp_path):
    repo, first, _ = source
    clone = _clone_at(repo, first, tmp_path / "clone")
    git(clone, "remote", "add", "origin", str(repo))
    assert any("remote" in problem for problem in clone_object_problems(clone))


def test_an_object_head_does_not_reach_is_a_problem(source, tmp_path):
    repo, first, _ = source
    clone = _clone_at(repo, first, tmp_path / "clone")
    # A fetch by path writes FETCH_HEAD and the objects; HEAD does not move.
    git(clone, "fetch", "-q", str(repo), "main")
    assert git(clone, "rev-parse", "HEAD") == first
    assert any("does not reach" in p for p in clone_object_problems(clone))


def test_alternates_are_a_problem(source, tmp_path):
    repo, first, _ = source
    clone = _clone_at(repo, first, tmp_path / "clone")
    info = clone / ".git" / "objects" / "info"
    info.mkdir(parents=True, exist_ok=True)
    (info / "alternates").write_text(str(repo / ".git" / "objects") + "\n")
    assert any("alternates" in p for p in clone_object_problems(clone))


def test_the_object_record_is_stable_and_counts_what_is_stored(source, tmp_path):
    repo, first, _ = source
    one = clone_object_record(_clone_at(repo, first, tmp_path / "one"))
    two = clone_object_record(_clone_at(repo, first, tmp_path / "two"))
    assert one == two
    assert one["count"] == 3  # the commit, its tree, and a.txt's blob
```

- [ ] **Step 2: Run them and see them fail**, with `ImportError: cannot import name
  'clone_object_problems'`.

- [ ] **Step 3: Implement** in `ai_rfc/lifecycle/workspace.py`, after `verify_digest`. `hashlib` is
  already imported there for `_digests`; if it isn't, import it.

```python
def _stored_objects(clone: Path) -> set[str]:
    listing = _git(
        clone, "cat-file", "--batch-all-objects", "--batch-check=%(objectname)"
    )
    return set(listing.split())


def clone_object_problems(clone: Path) -> list[str]:
    """What lets a clone hold, or reach, history its HEAD does not.

    The seal (:func:`write_digest`) skips ``.git``, so a clone that stores
    objects past its pin verifies clean. Three things are checked. A remote:
    in a truncated clone whose ``origin`` named the full repository, ``git
    fetch origin main`` restored the tip (measured 2026-09-21). An alternates
    file, which lends the clone another repository's objects. And a stored
    object that HEAD does not reach.

    Args:
        clone: A repository's working tree.

    Returns:
        One line per problem; empty when the clone holds exactly its HEAD's
        history.

    Raises:
        LifecycleError: If git cannot read the repository.
    """
    problems = []
    remotes = _git(clone, "remote").split()
    if remotes:
        problems.append(
            f"{clone} has remote(s) {', '.join(remotes)}; a fetch through one "
            "restores history past HEAD"
        )
    alternates = clone / _git(
        clone, "rev-parse", "--git-path", "objects/info/alternates"
    )
    if alternates.exists():
        problems.append(f"{alternates} lends {clone} another repository's objects")
    reachable = {
        line.split(" ", 1)[0]
        for line in _git(clone, "rev-list", "--objects", "HEAD").splitlines()
        if line
    }
    extra = _stored_objects(clone) - reachable
    if extra:
        problems.append(
            f"{clone} stores {len(extra)} object(s) HEAD does not reach "
            f"(first: {min(extra)})"
        )
    return problems


def clone_object_record(clone: Path) -> dict[str, Any]:
    """The count and sha256 of a clone's stored object ids, sorted one per line.

    Sealed into ``pristine.json`` by ``workspace prepare`` and compared on
    every copy, so a clone that gained history after it was sealed is caught
    even when the gain is reachable from a HEAD that did not move.

    Args:
        clone: A repository's working tree.

    Returns:
        ``{"count": ..., "sha256": ...}``.

    Raises:
        LifecycleError: If git cannot read the repository.
    """
    stored = sorted(_stored_objects(clone))
    digest = hashlib.sha256("\n".join(stored).encode()).hexdigest()
    return {"count": len(stored), "sha256": digest}
```

  `git rev-parse --git-path` prints a path relative to the directory `-C` names, or an absolute one
  for a linked worktree. `clone / <absolute>` is that absolute path, so both cases resolve.

- [ ] **Step 4: Run** `tests/experiment/test_clone_objects.py` and see 5 pass.

- [ ] **Step 5: Commit**: `feat(lifecycle): say when a clone holds or reaches history its HEAD
  does not`, with `ai_rfc/lifecycle/workspace.py tests/experiment/test_clone_objects.py`.

## Task 2: `acquire` clones only its pin's history, with no remote

Spec §7.1, "Every clone holds only its pin's history". Measured on git 2.55.0 on 2026-09-22:
- `--no-local --revision=<branch>` and `--revision=<full sha>` both clone, leaving HEAD detached and
  no ref;
- `--revision=<7-char sha>` fails with `fatal: Remote revision 008c0d2 not found in upstream
  origin`;
- the clone keeps an `origin` remote with no refs, and a later `checkout --detach main` fails,
  because no `main` ref exists;
- `-q` does not silence the detached-HEAD advice; `-c advice.detachedHead=false` does.

**Files:**
- Modify: `ai_rfc/lifecycle/workspace.py` (`acquire`)
- Test: `tests/cli/test_init.py`

**Interfaces:**
- Consumes: `clone_object_problems` (Task 1).
- Produces: every workspace's `clone/` is detached at the pin, has no remote, and stores only the
  pin's history. `Acquired.resolved_sha` is unchanged in meaning.

- [ ] **Step 1: Write the failing tests** (add them to `tests/cli/test_init.py`, and import
  `subprocess` there if it isn't already).

```python
def test_init_clones_only_the_history_its_pin_reaches(
    tmp_path, source_repo, template_repo
):
    """A clone is its pin's history and nothing else, and it has no way back.

    A plain local clone copies the objects directory whole (research 11:
    7,686 objects stored against 3,624 reachable), and an ``origin`` that
    names the full repository restores the tip with one fetch.
    """
    from ai_rfc.lifecycle.workspace import clone_object_problems

    template, commit = template_repo
    first = git(source_repo, "rev-list", "--max-parents=0", "HEAD")
    second = git(source_repo, "rev-parse", "HEAD")
    config_path = _config(tmp_path, source_repo)
    config_path.write_text(
        config_path.read_text().replace("pin: main", f"pin: {first}")
    )
    argv = ["init", "--config", str(config_path), "--template", template,
            "--template-commit", commit]
    assert cli.main(argv) == 0

    clone = Layout(tmp_path / "ws").clone
    assert git(clone, "rev-parse", "HEAD") == first
    assert git(clone, "remote") == ""
    assert clone_object_problems(clone) == []
    future = subprocess.run(
        ["git", "-C", str(clone), "cat-file", "-e", second], capture_output=True
    )
    assert future.returncode != 0


def test_init_refuses_an_abbreviated_pin_and_says_what_a_pin_is(
    tmp_path, source_repo, template_repo, capsys
):
    template, commit = template_repo
    first = git(source_repo, "rev-list", "--max-parents=0", "HEAD")
    config_path = _config(tmp_path, source_repo)
    config_path.write_text(
        config_path.read_text().replace("pin: main", f"pin: {first[:7]}")
    )
    argv = ["init", "--config", str(config_path), "--template", template,
            "--template-commit", commit]
    assert cli.main(argv) == 1
    err = capsys.readouterr().err
    assert "full commit id" in err and first[:7] in err
    assert not (tmp_path / "ws").exists()
```

- [ ] **Step 2: Run them and see them fail.** The first fails on `git(clone, "remote") == ""`,
  because `origin` is there; the second on the message.

- [ ] **Step 3: Implement.** In `acquire`, replace the clone-and-checkout block (from `cloned =
  _run_git("clone", …)` through `resolved = _git(layout.clone, "rev-parse", "HEAD")`) with:

```python
    # --no-local, because a local clone copies the objects directory whole,
    # every commit past the pin with it (research 11: 7,686 objects stored
    # against 3,624 reachable). --revision fetches the pin's history and
    # nothing else, and leaves HEAD detached at it with no ref, so there is no
    # checkout to do: `checkout --detach main` would fail on a ref that no
    # longer exists.
    cloned = _run_git(
        "-c",
        "advice.detachedHead=false",
        "clone",
        "-q",
        "--no-local",
        f"--revision={config.source.pin}",
        config.source.repo,
        str(layout.clone),
    )
    if cloned.returncode != 0:
        raise LifecycleError(
            f"cloning {config.source.repo} at {config.source.pin} failed: "
            f"{cloned.stderr.strip()}; a pin is a branch, a tag or a full "
            "commit id, and git must be 2.49 or later"
        )
    # A remote is a way back to the history the clone was cut from: in a
    # truncated clone, `git fetch origin main` restored the tip (measured
    # 2026-09-21). Nothing in ai_rfc reads a clone's remotes.
    removed = _run_git("-C", str(layout.clone), "remote", "remove", "origin")
    if removed.returncode != 0:
        raise LifecycleError(
            f"removing origin from {layout.clone} failed: {removed.stderr.strip()}"
        )
    resolved = _git(layout.clone, "rev-parse", "HEAD")
```

  Update `acquire`'s docstring:
  - the summary line: "Clone the source's history up to its pin, with no remote, and fetch the forge
    snapshot, the networked phase";
  - `Raises`: "LifecycleError: If the clone fails (a pin that is not a branch, a tag or a full commit
    id; a pin the source lacks; a git older than 2.49), origin cannot be removed, the forge stage
    refuses, or the snapshot cannot be adopted."

- [ ] **Step 4: Find every pin the suite uses.** Run
  `grep -rn -E "pin: |source\.pin|pin=" tests ai_rfc/experiment/optimize` from `<ai_rfc>`. Each pin
  must be a branch, a tag or a full sha. A fixture that pins an abbreviated sha or an expression
  such as `HEAD~1` is rewritten to a full sha that the fixture reads with `git rev-parse`. List what
  changed in the commit message body.

- [ ] **Step 5: Run** `tests/cli tests/experiment tests/substrate/pipeline` and see them pass,
  including `test_init_removes_the_workspace_it_half_built` (its "cloning" assertion still holds)
  and `test_init_resolves_a_sha_pin_and_records_the_window`.

- [ ] **Step 6: Commit**: `fix(lifecycle): clone only the pin's history and keep no remote`, with
  `ai_rfc/lifecycle/workspace.py tests/cli/test_init.py` and any fixture Step 4 changed.

## Task 3: The forge cut (rule R1) and the snapshot's identity

Spec §7.1, "Forge rule R1"; §11 questions 2 and 3.

**Files:**
- Create: `ai_rfc/forge/cut.py`
- Modify: `ai_rfc/forge/store.py` (`write_snapshot`), `ai_rfc/forge/adopt.py` (`adopt_snapshot`, and a
  new `carried_ceiling`)
- Test: `tests/substrate/forge/test_cut.py` (new)

**Interfaces:**
- Produces: `write_snapshot(..., derived_from: dict[str, str] | None = None, truncated_at: str |
  None = None)`. Both keys are written to `meta.json` only when given, and both or neither must be
  given. A fetched snapshot's meta is unchanged byte for byte.
- Produces: `carried_ceiling(snapshot: dict[str, Any]) -> str`, the `fidelity_ceiling`
  `adopt_snapshot` computes today, now shared.
- Produces: `cut_snapshot(source: Path, out_root: Path, *, end: str, end_time: datetime, ancestors:
  frozenset[str]) -> SnapshotCut`.
- Produces: `SnapshotCut(snapshot: Path, derived_from: dict[str, str], pulls_kept: tuple[int, ...],
  dropped: dict[str, int])`. The keys of `dropped` are `pulls`, `reviews` and `comments`.

- [ ] **Step 1: Write the failing tests** (`tests/substrate/forge/test_cut.py`)

```python
"""Rule R1: a cut snapshot keeps what had happened by the end commit, and says so."""

import hashlib
import json
from datetime import datetime, timezone

import pytest

from ai_rfc.forge.adopt import adopt_snapshot
from ai_rfc.forge.cut import cut_snapshot
from ai_rfc.forge.store import ForgeError, read_snapshot, write_snapshot

pytestmark = pytest.mark.unit

END = "e" * 40
BEFORE = "2019-09-04T10:00:00Z"
AFTER = "2019-09-05T10:00:00Z"
END_TIME = datetime(2019, 9, 4, 11, 0, 27, tzinfo=timezone.utc)
ANCESTORS = frozenset({"a" * 40, "b" * 40, END})


@pytest.fixture
def captured(tmp_path):
    return write_snapshot(
        tmp_path / "captured",
        host="github.com",
        owner="o",
        repo="r",
        kind="github",
        clone_head="f" * 40,
        fetched_at="2026-08-25T15-16-59Z",
        authenticated=True,
        pulls=[
            {"number": 1, "merged_at": BEFORE, "squash_commit_sha": "a" * 40,
             "merge_commit_sha": None, "title": "landed by squash"},
            {"number": 2, "merged_at": BEFORE, "squash_commit_sha": None,
             "merge_commit_sha": "b" * 40, "title": "landed by merge"},
            {"number": 3, "merged_at": AFTER, "squash_commit_sha": "c" * 40,
             "merge_commit_sha": None, "title": "landed after the end"},
            {"number": 4, "merged_at": None, "squash_commit_sha": None,
             "merge_commit_sha": None, "title": "never merged"},
        ],
        reviews=[
            {"pr_number": 1, "id": 10, "submitted_at": BEFORE},
            {"pr_number": 1, "id": 11, "submitted_at": AFTER},
            {"pr_number": 1, "id": 12, "submitted_at": None},
            {"pr_number": 3, "id": 13, "submitted_at": BEFORE},
        ],
        comments=[
            {"pr_number": 2, "id": 20, "kind": "issue_comment", "created_at": BEFORE},
            # 12:30 at +02:00 is 10:30Z: before the end, compared as an instant.
            {"pr_number": 2, "id": 21, "kind": "issue_comment",
             "created_at": "2019-09-04T12:30:00+02:00"},
            {"pr_number": 2, "id": 22, "kind": "issue_comment", "created_at": AFTER},
            {"pr_number": 4, "id": 23, "kind": "issue_comment", "created_at": BEFORE},
        ],
    )


def _cut(captured, tmp_path):
    return cut_snapshot(captured, tmp_path / "cut", end=END, end_time=END_TIME,
                        ancestors=ANCESTORS)


def test_r1_keeps_pulls_that_landed_by_the_end_and_their_discussion_dated_by_then(
    captured, tmp_path
):
    cut = _cut(captured, tmp_path)
    kept = read_snapshot(cut.snapshot)
    assert [p["number"] for p in kept["pulls"]] == [1, 2]
    assert [r["id"] for r in kept["reviews"]] == [10]
    assert [c["id"] for c in kept["comments"]] == [20, 21]
    assert cut.pulls_kept == (1, 2)
    assert cut.dropped == {"pulls": 2, "reviews": 3, "comments": 2}


def test_a_cut_snapshot_names_what_it_was_cut_from_and_where(captured, tmp_path):
    cut = _cut(captured, tmp_path)
    meta = json.loads((cut.snapshot / "meta.json").read_text())
    assert meta["clone_head"] == meta["truncated_at"] == END
    assert meta["fetched_at"] == "2026-08-25T15-16-59Z"
    assert meta["acquisition"] == "cut"
    source_meta = (captured / "meta.json").read_bytes()
    assert meta["derived_from"] == {
        "dir_name": captured.name,
        "meta_sha256": hashlib.sha256(source_meta).hexdigest(),
    }
    assert cut.derived_from == meta["derived_from"]


def test_adopting_a_cut_snapshot_carries_its_identity(captured, tmp_path):
    cut = _cut(captured, tmp_path)
    adopted = adopt_snapshot(cut.snapshot, tmp_path / "adopted")
    meta = json.loads((adopted / "meta.json").read_text())
    assert meta["acquisition"] == "adopt"
    assert meta["truncated_at"] == END
    assert meta["derived_from"]["dir_name"] == captured.name


def test_a_fetched_snapshot_records_neither_field(captured):
    meta = json.loads((captured / "meta.json").read_text())
    assert "derived_from" not in meta and "truncated_at" not in meta


def test_one_identity_field_without_the_other_is_refused(tmp_path):
    with pytest.raises(ForgeError, match="derived_from"):
        write_snapshot(tmp_path, host="h", owner="o", repo="r", kind="github",
                       clone_head=END, fetched_at="t", authenticated=False,
                       pulls=[], reviews=[], comments=[], truncated_at=END)
```

- [ ] **Step 2: Run them and see them fail**, with `ModuleNotFoundError: ai_rfc.forge.cut`.

- [ ] **Step 3: Implement `write_snapshot`'s two fields** (`forge/store.py`):
  - Add `derived_from: dict[str, str] | None = None` and `truncated_at: str | None = None` after
    `fidelity_ceiling`, with these `Args` lines:
    - `derived_from`: "For a snapshot cut from another, that snapshot's `{"dir_name",
      "meta_sha256"}`. Written only when given, so a fetched snapshot's meta is unchanged."
    - `truncated_at`: "For a cut snapshot, the commit it was cut at."
  - Add "or only one of `derived_from` and `truncated_at` is given" to `Raises`.
  - Validate after the `fidelity_ceiling` check:

```python
    if (derived_from is None) != (truncated_at is None):
        raise ForgeError(
            "derived_from and truncated_at describe one cut together; a snapshot "
            "carrying only one of them could not say what it was cut from, or where"
        )
```

  - After `meta` is built, and before it is written:

```python
    if derived_from is not None:
        meta["derived_from"] = dict(derived_from)
        meta["truncated_at"] = truncated_at
```

- [ ] **Step 4: Share the ceiling and carry the fields** (`forge/adopt.py`). Add, above
  `adopt_snapshot`:

```python
def carried_ceiling(snapshot: dict[str, Any]) -> str:
    """The fidelity ceiling a snapshot states, or the one its rows imply.

    A snapshot written before the field existed still states what it
    delivered: discussion rows are there or they are not, and that is the most
    an older capture can say about its own ceiling.

    Args:
        snapshot: A snapshot as :func:`read_snapshot` returns it.

    Returns:
        The ceiling to record for a copy of it.
    """
    return snapshot["meta"].get(
        "fidelity_ceiling",
        FULL_FIDELITY if snapshot["reviews"] or snapshot["comments"] else "pulls",
    )
```

  In `adopt_snapshot`:
  - replace the `fidelity_ceiling=meta.get(…)` argument with
    `fidelity_ceiling=carried_ceiling(snapshot)`, and move the existing comment about carried
    fields to above `denied_subfetches`;
  - add `derived_from=meta.get("derived_from"), truncated_at=meta.get("truncated_at"),`;
  - add one sentence to its docstring: "A cut snapshot's `derived_from` and `truncated_at` are
    carried too, for the same reason."

- [ ] **Step 5: Implement `ai_rfc/forge/cut.py`**

```python
"""Cut a forge snapshot at a commit: keep only what had happened by then.

A windowed pristine holds nothing after its window's end (the ground-truth
yardstick spec, section 7.1). Its forge snapshot is therefore derived from the
one captured, by rule R1:
- a pull is kept only if it merged and its landing commit is an ancestor of the
  end;
- a review or comment is kept only if its pull is kept and its own timestamp is
  at or before the end's committer time.

R1 keeps exactly the pulls the truncated timeline can match
(:func:`ai_rfc.timeline.build._match_pulls` reads the same two fields), so
cluster ids survive by construction. A date cut does so only while it keeps a
superset of R1.

R1 cannot see a kept pull's title or body edited after the end: the snapshot
stores them as they were when fetched, and nothing records their history.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .adopt import carried_ceiling
from .store import META_FILE, read_snapshot, write_snapshot


@dataclass(frozen=True)
class SnapshotCut:
    """What cutting a snapshot kept and dropped."""

    snapshot: Path
    derived_from: dict[str, str]
    pulls_kept: tuple[int, ...]
    dropped: dict[str, int]


def _landing(pull: dict[str, Any]) -> str | None:
    return pull.get("squash_commit_sha") or pull.get("merge_commit_sha")


def _dated_by(stamp: Any, end_time: datetime) -> bool:
    """Whether ``stamp`` is at or before ``end_time``. Undated or unreadable is not."""
    if not isinstance(stamp, str) or not stamp:
        return False
    try:
        # Python 3.10's fromisoformat does not read a trailing "Z".
        when = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return False
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return when <= end_time


def cut_snapshot(
    source: Path,
    out_root: Path,
    *,
    end: str,
    end_time: datetime,
    ancestors: frozenset[str],
) -> SnapshotCut:
    """Write the part of ``source`` that describes the repository up to ``end``.

    Args:
        source: A snapshot directory written by :func:`write_snapshot`.
        out_root: The forge cache root the cut snapshot is filed under.
        end: The commit to cut at; it becomes the snapshot's ``clone_head``.
        end_time: ``end``'s committer time, timezone-aware.
        ancestors: Every commit ``git rev-list <end>`` lists, ``end`` included.

    Returns:
        The cut snapshot, and what it kept and dropped.

    Raises:
        ForgeError: If the destination already holds this snapshot.
        OSError: If ``source`` cannot be read.
        KeyError: If ``source``'s ``meta.json`` omits a field naming what was
            captured.
    """
    snapshot = read_snapshot(source)
    meta = snapshot["meta"]
    pulls = [
        pull
        for pull in snapshot["pulls"]
        if pull.get("merged_at") and _landing(pull) in ancestors
    ]
    kept = {pull["number"] for pull in pulls}
    reviews = [
        review
        for review in snapshot["reviews"]
        if review["pr_number"] in kept and _dated_by(review.get("submitted_at"), end_time)
    ]
    comments = [
        comment
        for comment in snapshot["comments"]
        if comment["pr_number"] in kept and _dated_by(comment.get("created_at"), end_time)
    ]
    derived_from = {
        "dir_name": source.name,
        "meta_sha256": hashlib.sha256((source / META_FILE).read_bytes()).hexdigest(),
    }
    written = write_snapshot(
        out_root,
        host=meta["host"],
        owner=meta["owner"],
        repo=meta["repo"],
        kind=meta["kind"],
        clone_head=end,
        fetched_at=meta["fetched_at"],
        authenticated=meta["authenticated"],
        pulls=pulls,
        reviews=reviews,
        comments=comments,
        denied_subfetches=meta.get("denied_subfetches", 0),
        acquisition="cut",
        fidelity_ceiling=carried_ceiling(snapshot),
        derived_from=derived_from,
        truncated_at=end,
    )
    return SnapshotCut(
        snapshot=written,
        derived_from=derived_from,
        pulls_kept=tuple(sorted(kept)),
        dropped={
            "pulls": len(snapshot["pulls"]) - len(pulls),
            "reviews": len(snapshot["reviews"]) - len(reviews),
            "comments": len(snapshot["comments"]) - len(comments),
        },
    )
```

- [ ] **Step 6: Run** `tests/substrate/forge` and see it pass, including the existing adopt and
  store tests.

- [ ] **Step 7: Commit**: `feat(forge): cut a snapshot at a commit by rule R1 and record what it
  was cut from`, with `ai_rfc/forge/cut.py ai_rfc/forge/store.py ai_rfc/forge/adopt.py
  tests/substrate/forge/test_cut.py`.

## Task 4: `prepare` derives the end, builds the pristine there, and asserts the cut

Spec §7.1: its first four bullets and the recorded digest. §11 question 1.

**Files:**
- Modify: `ai_rfc/experiment/workspace.py` (`prepare`, `_carry_through_the_stages`; add `WindowCut`,
  `resolve_cut`, `_assert_the_cut`)
- Modify: `ai_rfc/experiment/cli.py` (the workspace-prepare handler prints the cut)
- Test: `tests/experiment/test_prepare_cut.py` (new)

**Interfaces:**
- Consumes: `acquire` (Task 2); `cut_snapshot` and `SnapshotCut` (Task 3); `clone_object_problems`
  and `clone_object_record` (Task 1).
- Produces: `WindowCut`, a frozen dataclass with `operator_pin`, `resolved_pin`, `end`,
  `top_cluster`, `ancestors: frozenset[str]`, `cluster_rows: tuple[str, ...]`, `member_rows:
  tuple[str, ...]` and `forge: SnapshotCut | None`. Its `record` property returns the dict stored as
  `pristine.json["cut"]`.
- Produces: `resolve_cut(config: ReconConfig, scratch: Path, *, forge_snapshot: Path | None) ->
  WindowCut`.
- Produces: `pristine.json` gains `cut` (the `record` above) and `clone_objects` (`{"count",
  "sha256"}`). The sealed `recon.yaml`'s `source.pin` is the end.

- [ ] **Step 1: Write the failing tests** (`tests/experiment/test_prepare_cut.py`)

```python
"""A windowed pristine is built at its window's end and holds nothing after it."""

import hashlib
import json
import subprocess
from pathlib import Path

import pytest
import yaml

from ai_rfc.config import load_config
from ai_rfc.experiment import ExperimentError
from ai_rfc.experiment.workspace import prepare
from ai_rfc.forge.store import write_snapshot
from ai_rfc.lifecycle.workspace import (
    CONFIG_FILE,
    RECORD_FILE,
    Layout,
    clone_object_problems,
    clone_object_record,
)
from ai_rfc.server.testing import git


def _commit(repo: Path, name: str, when: str) -> str:
    (repo / name).write_text(f"{name}\n")
    git(repo, "add", name)
    git(repo, "commit", "-q", "-m", f"add {name}", date=when)
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture
def cut_source(tmp_path: Path) -> tuple[Path, Path, dict[str, str]]:
    """Five clusters: epoch, merge PR #2, forge-squash PR #5, epoch, merge PR #6.

    The window [2, 3] ends at the squash commit, the last member of c0003, and
    c0003 exists only because pull #5 is kept: without it the squash commit is
    an ordinary epoch commit.
    """
    repo = tmp_path / "source"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@t")
    git(repo, "config", "user.name", "t")
    _commit(repo, "a.txt", "2019-09-01T00:00:01+00:00")
    _commit(repo, "b.txt", "2019-09-01T00:00:02+00:00")
    git(repo, "checkout", "-q", "-b", "feat")
    _commit(repo, "f.txt", "2019-09-01T00:00:03+00:00")
    git(repo, "checkout", "-q", "main")
    git(repo, "merge", "-q", "--no-ff", "feat", "-m", "Merge pull request #2",
        date="2019-09-01T00:00:04+00:00")
    merge_one = git(repo, "rev-parse", "HEAD")
    squash = _commit(repo, "s.txt", "2019-09-01T00:00:05+00:00")
    _commit(repo, "d.txt", "2019-09-02T00:00:06+00:00")
    _commit(repo, "e.txt", "2019-09-02T00:00:07+00:00")
    git(repo, "checkout", "-q", "-b", "feat2")
    _commit(repo, "g.txt", "2019-09-02T00:00:08+00:00")
    git(repo, "checkout", "-q", "main")
    git(repo, "merge", "-q", "--no-ff", "feat2", "-m", "Merge pull request #6",
        date="2019-09-02T00:00:09+00:00")
    tip = git(repo, "rev-parse", "HEAD")
    captured = write_snapshot(
        tmp_path / "captured",
        host="github.com", owner="o", repo="r", kind="github",
        clone_head=tip, fetched_at="2026-08-25T15-16-59Z", authenticated=True,
        pulls=[
            {"number": 2, "merged_at": "2019-09-01T00:00:04Z", "title": "feat",
             "merge_commit_sha": merge_one, "squash_commit_sha": None},
            {"number": 5, "merged_at": "2019-09-01T00:00:05Z", "title": "squashed",
             "merge_commit_sha": None, "squash_commit_sha": squash},
            {"number": 6, "merged_at": "2019-09-02T00:00:09Z", "title": "feat2",
             "merge_commit_sha": tip, "squash_commit_sha": None},
            {"number": 7, "merged_at": None, "title": "never merged",
             "merge_commit_sha": None, "squash_commit_sha": None},
        ],
        reviews=[],
        comments=[
            {"pr_number": 5, "id": 1, "kind": "issue_comment",
             "created_at": "2019-09-01T00:00:05Z", "body": "before"},
            {"pr_number": 5, "id": 2, "kind": "issue_comment",
             "created_at": "2019-09-03T00:00:00Z", "body": "after"},
        ],
    )
    return repo, captured, {"squash": squash, "tip": tip}


def _prepare(tmp_path, repo, captured, template_repo, window, root):
    """Prepare ``repo`` at its tip with ``window`` under ``tmp_path / root``."""
    template, commit = template_repo
    home = tmp_path / root
    home.mkdir()
    config_path = home / "recon.yaml"
    config_path.write_text(
        "name: fixture\n"
        f"workspace: {home / 'unused'}\n"
        "source:\n"
        f"  repo: {repo}\n"
        "  host: none\n"
        f"  pin: {git(repo, 'rev-parse', 'HEAD')}\n"
        f"window: [{window[0]}, {window[1]}]\n"
        "draft:\n"
        "  name: draft-test-fixture\n"
        "  title: Fixture\n"
        "  abbrev: Fix\n"
        "  rfc_id: FIX-1\n"
        "references: []\n"
        f"toolchain: {home / 'tools' / 'toolchain.json'}\n"
    )
    return prepare(
        load_config(config_path),
        root=home / "root",
        config_path=config_path,
        template=template,
        template_commit=commit,
        forge_snapshot=captured,
    )


def _rows(pristine: Path, name: str) -> list[str]:
    return (pristine / "timeline" / name).read_text().splitlines()


def test_a_cut_keeps_the_window_s_clusters_byte_equal_to_the_full_history(
    cut_source, template_repo, tmp_path
):
    repo, captured, _ = cut_source
    windowed = _prepare(tmp_path, repo, captured, template_repo, (2, 3), "cut")
    full = _prepare(tmp_path, repo, captured, template_repo, (2, 5), "full")
    assert len(_rows(full, "clusters.jsonl")) == 5
    assert _rows(windowed, "clusters.jsonl") == _rows(full, "clusters.jsonl")[:3]
    ids = {json.loads(row)["id"] for row in _rows(windowed, "clusters.jsonl")}
    assert _rows(windowed, "members.jsonl") == [
        row for row in _rows(full, "members.jsonl") if json.loads(row)["cluster_id"] in ids
    ]
    assert json.loads(_rows(windowed, "clusters.jsonl")[2])["provenance"] == "forge_squash"


def test_a_cut_pristine_holds_nothing_after_its_end(cut_source, template_repo, tmp_path):
    repo, captured, shas = cut_source
    windowed = _prepare(tmp_path, repo, captured, template_repo, (2, 3), "cut")
    clone = windowed / "clone"
    assert git(clone, "rev-parse", "HEAD") == shas["squash"]
    assert git(clone, "remote") == ""
    assert clone_object_problems(clone) == []
    tip = subprocess.run(["git", "-C", str(clone), "cat-file", "-e", shas["tip"]],
                         capture_output=True)
    assert tip.returncode != 0
    commits = [json.loads(row)["sha"]
               for row in (windowed / "corpus" / "commits.jsonl").read_text().splitlines()]
    assert len(commits) == 5 and shas["tip"] not in commits
    snapshot = Layout(windowed).latest_forge_snapshot()
    pulls = [json.loads(row)["number"]
             for row in (snapshot / "pulls.jsonl").read_text().splitlines()]
    assert pulls == [2, 5]
    bodies = [json.loads(row)["body"]
              for row in (snapshot / "comments.jsonl").read_text().splitlines()]
    assert bodies == ["before"]
    meta = json.loads((snapshot / "meta.json").read_text())
    assert meta["clone_head"] == meta["truncated_at"] == shas["squash"]
    # derived_from names the operator's capture, which outlives the prepare.
    assert meta["derived_from"] == {
        "dir_name": captured.name,
        "meta_sha256": hashlib.sha256((captured / "meta.json").read_bytes()).hexdigest(),
    }


def test_the_sealed_config_pins_the_end_and_the_record_names_the_cut(
    cut_source, template_repo, tmp_path
):
    repo, captured, shas = cut_source
    windowed = _prepare(tmp_path, repo, captured, template_repo, (2, 3), "cut")
    sealed = yaml.safe_load((windowed / CONFIG_FILE).read_text())
    assert sealed["source"]["pin"] == shas["squash"]
    assert sealed["source"]["repo"] == str(repo)
    record = json.loads((windowed / RECORD_FILE).read_text())
    assert record["clone_head"] == shas["squash"]
    cut = record["cut"]
    assert cut["operator_pin"] == cut["resolved_pin"] == shas["tip"]
    assert cut["end"] == shas["squash"] and cut["cut"] is True
    assert cut["top_cluster"].startswith("c0003-pr-")
    assert cut["forge"]["pulls_kept"] == [2, 5]
    assert cut["forge"]["dropped"] == {"pulls": 2, "reviews": 0, "comments": 1}
    assert record["clone_objects"] == clone_object_record(windowed / "clone")


def test_a_window_ending_at_the_last_cluster_is_not_cut(cut_source, template_repo, tmp_path):
    repo, captured, shas = cut_source
    full = _prepare(tmp_path, repo, captured, template_repo, (2, 5), "full")
    record = json.loads((full / RECORD_FILE).read_text())
    assert record["cut"]["cut"] is False and record["cut"]["end"] == shas["tip"]
    assert record["cluster_count"] == 5
    # Discussion dated after the pin is future even when nothing is cut.
    assert record["cut"]["forge"]["dropped"] == {"pulls": 1, "reviews": 0, "comments": 1}


def test_prepare_refuses_a_cut_that_changes_a_kept_cluster(
    cut_source, template_repo, tmp_path, monkeypatch
):
    """Same ids, different content: the assert that makes a cut trustworthy.

    Dropping every pull changes pass 2's c0002 (it loses pull #2) and c0003
    (it stops being a squash rescue), while the ordinals stay 1..3.
    """
    from ai_rfc.experiment import workspace as workspace_module

    real = workspace_module.cut_snapshot

    def drop_every_pull(source, out_root, *, end, end_time, ancestors):
        return real(source, out_root, end=end, end_time=end_time, ancestors=frozenset())

    monkeypatch.setattr(workspace_module, "cut_snapshot", drop_every_pull)
    repo, captured, _ = cut_source
    with pytest.raises(ExperimentError) as excinfo:
        _prepare(tmp_path, repo, captured, template_repo, (2, 3), "cut")
    assert "rows 1..3" in str(excinfo.value)
    assert not (tmp_path / "cut" / "root" / "pristine" / "fixture-w02-03").exists()
```

- [ ] **Step 2: Run them and see them fail.** The pristine's clone is at the tip, and `record` has
  no `cut`.

- [ ] **Step 3: Implement.** In `ai_rfc/experiment/workspace.py`:

  **3a. Imports.** Add `dataclasses`, `tempfile`, `from dataclasses import dataclass`, `from datetime
  import datetime` and `from typing import Any` (keep `Iterable`). Then add:
  - `from ai_rfc.forge.cut import SnapshotCut, cut_snapshot`;
  - `from ai_rfc.forge.store import ForgeError`;
  - `from ai_rfc.timeline.corpus import read_commits`;
  - `MEMBERS_FILE` beside `read_clusters` in the `ai_rfc.timeline.store` import;
  - `acquire`, `clone_object_problems` and `clone_object_record` in the `..lifecycle.workspace`
    import.

  **3b. The cut.** Add these below `_git_checked`:

```python
@dataclass(frozen=True)
class WindowCut:
    """Where a windowed pristine ends, and what the full history said up to there.

    The end is the last member of the window's top cluster, which only a
    timeline over the full history can name: cluster H ends where cluster H+1
    begins. The rows are pass 1's, kept byte for byte so pass 2 can be held to
    them.
    """

    operator_pin: str
    resolved_pin: str
    end: str
    top_cluster: str
    ancestors: frozenset[str]
    cluster_rows: tuple[str, ...]
    member_rows: tuple[str, ...]
    forge: SnapshotCut | None

    @property
    def record(self) -> dict[str, Any]:
        """The ``cut`` block ``pristine.json`` records."""
        return {
            "operator_pin": self.operator_pin,
            "resolved_pin": self.resolved_pin,
            "end": self.end,
            "top_cluster": self.top_cluster,
            "cut": self.end != self.resolved_pin,
            "forge": None
            if self.forge is None
            else {
                "derived_from": self.forge.derived_from,
                "pulls_kept": list(self.forge.pulls_kept),
                "dropped": self.forge.dropped,
            },
        }


def resolve_cut(
    config: ReconConfig, scratch: Path, *, forge_snapshot: Path | None
) -> WindowCut:
    """Find a window's end from the full history, and cut the forge snapshot there.

    Pass 1 of a prepare: the operator's pin is acquired, and history and
    timeline are run over it, in ``scratch``. The window's top cluster H ends
    at cluster H+1's ``spine_prev_sha``, which research 11 measured on all 341
    aioquic boundaries. When H is the last cluster, or the config declares no
    window, the end is the pin itself. The forge snapshot, adopted or fetched
    here once, is cut at the end by rule R1 even then, because discussion
    dated after the pin is future too.

    Args:
        config: The operator's configuration.
        scratch: An empty directory that outlives this call and is removed
            after the pristine is built.
        forge_snapshot: A snapshot to adopt instead of fetching one.

    Returns:
        The end, and pass 1's rows for the window's clusters.

    Raises:
        ExperimentError: If acquisition or a stage fails, the timeline
            clustered nothing, or the timeline contradicts itself about where
            the top cluster ends.
    """
    full = Layout(scratch / "full")
    full.root.mkdir(parents=True)
    try:
        acquired = acquire(config, full, forge_snapshot=forge_snapshot)
    except LifecycleError as error:
        raise ExperimentError(str(error)) from None
    for name in ("history", "timeline"):
        result = perform(BY_NAME[name], full)
        if not result.ok:
            raise ExperimentError(
                f"resolution pass: {name} exited {result.exit_code}; see stderr"
            )
    rows = read_clusters(full.timeline)
    if not rows:
        raise ExperimentError(
            f"{config.name}: the timeline holds no clusters, so there is no "
            f"window to derive and nothing to seal; check that "
            f"{config.source.repo} at {config.source.pin} has history"
        )
    last = rows[-1]["ordinal"]
    top = min(config.window[1], last) if config.window else last
    if rows[top - 1]["ordinal"] != top:
        raise ExperimentError(
            f"{full.clusters_jsonl}: row {top} is ordinal "
            f"{rows[top - 1]['ordinal']}; ordinals must run 1..{last} in order"
        )
    top_cluster = rows[top - 1]["id"]
    end = acquired.resolved_sha if top == last else rows[top]["spine_prev_sha"]

    member_rows = tuple(
        line
        for line in (full.timeline / MEMBERS_FILE).read_text().splitlines()
        if json.loads(line)["cluster_id"] in {row["id"] for row in rows[:top]}
    )
    if not any(
        json.loads(line)["cluster_id"] == top_cluster and json.loads(line)["sha"] == end
        for line in member_rows
    ):
        raise ExperimentError(
            f"{end} is not a member of {top_cluster}; the timeline's boundary "
            f"and its members disagree, so there is no end to cut at"
        )

    ancestors = frozenset(_git_checked(full.clone, "rev-list", end).split())
    end_time = datetime.fromisoformat(
        _git_checked(full.clone, "log", "-1", "--format=%cI", end)
    )
    # Cut from the operator's own capture when there is one, so derived_from
    # names a snapshot that outlives this call and whose meta can be re-hashed.
    # Only a snapshot fetched here is cut from its scratch copy.
    captured = (
        forge_snapshot if forge_snapshot is not None else full.latest_forge_snapshot()
    )
    try:
        forge = (
            cut_snapshot(
                captured,
                scratch / "forge",
                end=end,
                end_time=end_time,
                ancestors=ancestors,
            )
            if captured is not None
            else None
        )
    except (ForgeError, OSError, KeyError) as error:
        raise ExperimentError(f"cutting {captured} at {end} failed: {error}") from None
    return WindowCut(
        operator_pin=config.source.pin,
        resolved_pin=acquired.resolved_sha,
        end=end,
        top_cluster=top_cluster,
        ancestors=ancestors,
        cluster_rows=tuple(full.clusters_jsonl.read_text().splitlines()[:top]),
        member_rows=member_rows,
        forge=forge,
    )


def _assert_the_cut(layout: Layout, cut: WindowCut) -> None:
    """Refuse a pristine whose window is not the full history's window, byte for byte.

    Raises:
        ExperimentError: If the timeline or member rows differ from pass 1's,
            the corpus holds a commit after the end or lacks one before it, or
            the clone holds or reaches history past its pin.
    """
    count = len(cut.cluster_rows)
    if tuple(layout.clusters_jsonl.read_text().splitlines()) != cut.cluster_rows:
        raise ExperimentError(
            f"the pristine's clusters.jsonl differs from the full history's rows "
            f"1..{count} (cut at {cut.end}); a cut can keep a cluster's id and "
            f"change what it names"
        )
    members = tuple((layout.timeline / MEMBERS_FILE).read_text().splitlines())
    if members != cut.member_rows:
        raise ExperimentError(
            f"the pristine's members.jsonl differs from the full history's rows "
            f"for clusters 1..{count} (cut at {cut.end})"
        )
    corpus = {commit.sha for commit in read_commits(layout.corpus)}
    if corpus != cut.ancestors:
        raise ExperimentError(
            f"the corpus holds {len(corpus - cut.ancestors)} commit(s) after "
            f"{cut.end} and lacks {len(cut.ancestors - corpus)} before it"
        )
    try:
        problems = clone_object_problems(layout.clone)
    except LifecycleError as error:
        raise ExperimentError(str(error)) from None
    if problems:
        raise ExperimentError(
            "the clone holds or reaches history past its pin: " + "; ".join(problems)
        )
```

  `Layout` exposes `clusters_jsonl` through `pipeline.workspace.Workspace`; confirm it with the
  Task 0 read.

  **3c. `prepare`.** Replace its body after the `pristine.exists()` refusal:

```python
    # Pass 1 finds the end in scratch; pass 2 builds the pristine at it. The
    # scratch goes whatever happens: nothing in it is evidence, and the
    # pristine records what pass 1 decided.
    with tempfile.TemporaryDirectory(prefix="ai-rfc-prepare-") as scratch:
        cut = resolve_cut(config, Path(scratch), forge_snapshot=forge_snapshot)
        at_end = dataclasses.replace(
            config, source=dataclasses.replace(config.source, pin=cut.end)
        )
        try:
            initialise(
                at_end,
                config_path=config_path,
                dest=pristine,
                template=template,
                template_commit=template_commit,
                forge_snapshot=cut.forge.snapshot if cut.forge else None,
            )
        except LifecycleError as error:
            raise ExperimentError(str(error)) from None

        # `initialise` removes what it built when it fails; everything below is
        # this function's, and a refusal here would otherwise leave a tree the
        # retry refuses as already prepared. The directory is known not to have
        # existed, so there is nothing of anyone else's to reach.
        try:
            return _carry_through_the_stages(at_end, pristine, cut)
        except BaseException:
            shutil.rmtree(pristine, ignore_errors=True)
            raise
```

  Also update `prepare`'s docstring:
  - The summary says it builds the workspace **at the window's end commit**, which a full-history
    pass derives, and seals it.
  - One paragraph cites spec §7.1: the operator's pin is resolved, never trusted as the end.
  - `Raises` adds: "the cut does not reproduce the full history's window, the corpus holds a commit
    after the end, or the clone holds or reaches history past its pin".

  **3d. `_carry_through_the_stages(config, pristine, cut)`.**
  - Add the `cut: WindowCut` parameter.
  - After the stage loop, call `_assert_the_cut(layout, cut)`.
  - Delete the "no clusters" refusal block. `resolve_cut` owns that refusal now, and pass 2 has
    exactly pass 1's H ≥ 1 rows. Leave `ordinals = […]` and the window line.
  - In `record.update({...})`, add `"cut": cut.record` and
    `"clone_objects": clone_object_record(layout.clone)`. Wrap that call in the same `LifecycleError`
    → `ExperimentError` conversion `_git_checked` uses.

- [ ] **Step 4: The verb prints the cut.** In `ai_rfc/experiment/cli.py`, the
  `args.command == "workspace" and args.verb == "prepare"` branch reads `pristine.json` into
  `record` and prints `clusters: … pre-seeded: … window: …`. Directly after that `print`, add:

```python
            cut = record["cut"]
            print(
                f"cut: {cut['end']} after {cut['top_cluster']}"
                if cut["cut"]
                else "cut: none (the window ends at the last cluster)"
            )
            if cut["forge"] is not None:
                kept = len(cut["forge"]["pulls_kept"])
                dropped = cut["forge"]["dropped"]["pulls"]
                print(f"forge: {kept} pull(s) kept, {dropped} dropped")
```

  Extend `test_cli_workspace_prepare_reports_the_tree` (in `tests/experiment/test_workspace.py`)
  to assert that `"cut: none (the window ends at the last cluster)"` appears in its captured
  stdout. That test's window is [2, 2] over two clusters, and it adopts no snapshot, so no `forge:`
  line appears.

- [ ] **Step 5: Run** `tests/experiment/test_prepare_cut.py tests/experiment/test_workspace.py
  tests/experiment/optimize` and see them pass. The existing prepare tests must still pass
  unchanged: `test_prepare_adopts_captured_forge_data_instead_of_fetching_it` keeps its snapshot
  name and `acquisition: adopt`, and `test_prepare_refuses_a_timeline_that_clustered_nothing` still
  finds "no clusters", now raised by `resolve_cut`.

- [ ] **Step 6: Commit**: `feat(experiment): build a windowed pristine at its window's end and
  prove the cut kept the window`, with `ai_rfc/experiment/workspace.py ai_rfc/experiment/cli.py
  tests/experiment/test_prepare_cut.py tests/experiment/test_workspace.py`.

## Task 5: `copy_workspace` and `reseal` refuse a clone past its pin

Spec §7.1: "Git honesty is asserted everywhere" and "Older pristines are refused".

**Files:**
- Modify: `ai_rfc/experiment/workspace.py` (`copy_workspace`, `reseal`; add
  `_refuse_a_clone_past_its_pin`)
- Test: `tests/experiment/test_workspace.py`

**Interfaces:**
- Consumes: `clone_object_problems`, `clone_object_record` (Task 1); `pristine.json["clone_objects"]`
  (Task 4).
- Produces: `copy_workspace` and `reseal` raise `ExperimentError` for a clone with problems, for an
  object set other than the recorded one, and for a pristine that records none.

- [ ] **Step 1: Write the failing tests.** First update the `sealed` fixture in
  `tests/experiment/test_workspace.py`: its `record` gains
  `"clone_objects": clone_object_record(fixture_workspace / "clone")` (import it from
  `ai_rfc.lifecycle.workspace`). Then add:

```python
def test_copy_refuses_a_clone_that_gained_a_remote(sealed, tmp_path):
    # .git is outside the seal, so the digest still verifies; this check is the only one.
    git(sealed / "clone", "remote", "add", "origin", str(tmp_path))
    with pytest.raises(ExperimentError, match="remote"):
        copy_workspace(sealed, tmp_path / "run")


def _rewrite_record(sealed: Path, change) -> None:
    record = json.loads((sealed / RECORD_FILE).read_text())
    change(record)
    (sealed / RECORD_FILE).write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    write_digest(sealed)


def test_copy_refuses_a_pristine_that_records_no_object_set(sealed, tmp_path):
    _rewrite_record(sealed, lambda record: record.pop("clone_objects"))
    with pytest.raises(ExperimentError, match="records no clone_objects"):
        copy_workspace(sealed, tmp_path / "run")


def test_copy_refuses_an_object_set_other_than_the_sealed_one(sealed, tmp_path):
    _rewrite_record(sealed, lambda record: record["clone_objects"].update(count=0))
    with pytest.raises(ExperimentError, match="differ"):
        copy_workspace(sealed, tmp_path / "run")


def test_reseal_refuses_a_clone_that_gained_history(sealed, tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    git(other, "init", "-q", "-b", "main")
    (other / "x.txt").write_text("x\n")
    git(other, "add", "x.txt")
    git(other, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "x")
    git(sealed / "clone", "fetch", "-q", str(other), "main")
    with pytest.raises(ExperimentError, match="does not reach"):
        reseal(sealed, tmp_path / "baseline")
```

- [ ] **Step 2: Run them and see them fail.** The copies succeed.

- [ ] **Step 3: Implement.** Add this to `ai_rfc/experiment/workspace.py`:

```python
def _refuse_a_clone_past_its_pin(workspace: Path) -> None:
    """Refuse a workspace whose clone can show more history than its record sealed.

    The seal skips ``.git`` (:func:`write_digest`), so this is the only check
    between a clone that gained history and every run copied from it. A
    pristine that records no object set was prepared before pristines were cut
    at their window's end: it is evidence, and it is refused rather than
    exempted.

    Args:
        workspace: A pristine, or a copy of one.

    Raises:
        ExperimentError: If the clone has a remote, alternates or an object
            its HEAD does not reach, if its object set differs from the
            record's, or if the record holds none.
    """
    clone = workspace / "clone"
    try:
        problems = clone_object_problems(clone)
        objects = clone_object_record(clone)
    except LifecycleError as error:
        raise ExperimentError(str(error)) from None
    sealed = json.loads((workspace / RECORD_FILE).read_text()).get("clone_objects")
    if sealed is None:
        problems.append(
            f"{workspace / RECORD_FILE} records no clone_objects: it was prepared "
            "before pristines were cut at their window's end, so it is evidence, "
            "not a baseline; prepare a new one with a current `workspace prepare`"
        )
    elif sealed != objects:
        problems.append(
            f"the clone's {objects['count']} stored object(s) differ from the "
            f"{sealed['count']} its record sealed"
        )
    if problems:
        raise ExperimentError(f"{workspace}: " + "; ".join(problems))
```

  Then:
  - In `copy_workspace`, call `_refuse_a_clone_past_its_pin(dest)` after the loop that checks the
    clone and draft HEADs, and add the refusal to its `Raises`.
  - In `reseal`, call `_refuse_a_clone_past_its_pin(dest)` after the draft-dirty check, before
    `record["draft_head"]` is re-read. The record's `clone_objects` is carried unchanged, because a
    clone never moves.

- [ ] **Step 4: Run** `tests/experiment` and see it pass. Every fixture that builds a pristine by
  hand and then copies it needs `clone_objects` too. Find them with
  `grep -rn "RECORD_FILE\|pristine.json" tests/experiment`, and fix each in this task.

- [ ] **Step 5: Commit**: `feat(experiment): refuse a pristine copy whose clone holds history
  past its pin`, with `ai_rfc/experiment/workspace.py tests/experiment/test_workspace.py` and any
  fixture Step 4 changed.

## Task 6: `cluster_get` refuses a cluster after the window

Spec §7.2 (amended 2026-09-22): refuse only ordinals above the window's top; earlier clusters stay
readable.

**Files:**
- Modify: `ai_rfc/server/core/clusters.py` (add `refuse_after_the_window`),
  `ai_rfc/server/core/queries.py` (`cluster_get`)
- Test: `tests/server/test_core.py`

**Interfaces:**
- Produces: `refuse_after_the_window(workspace: Path, cluster_id: str) -> None`. It raises
  `CoreError` when the workspace records a window and the cluster's ordinal is above its top.
- Callers: `cluster_get` only. Arm A's MCP tool (`server/tools.py`) and arm B's verb
  (`agent/cluster/cli.py`) both reach it.

- [ ] **Step 1: Write the failing tests** (in `tests/server/test_core.py`; import `json` if the file
  does not already).

```python
def _cluster_ids(ctx) -> list[str]:
    rows = (ctx.workspace / "timeline" / "clusters.jsonl").read_text().splitlines()
    return [json.loads(row)["id"] for row in rows]


def test_cluster_get_refuses_a_cluster_after_the_window(workspace):
    first, second = _cluster_ids(workspace)[:2]
    (workspace.workspace / "pristine.json").write_text(json.dumps({"window": [1, 1]}))
    assert cluster_get(workspace, first)["view"]
    with pytest.raises(CoreError, match="after this run's window"):
        cluster_get(workspace, second)


def test_cluster_get_serves_a_cluster_before_the_window(workspace):
    first = _cluster_ids(workspace)[0]
    (workspace.workspace / "pristine.json").write_text(json.dumps({"window": [2, 2]}))
    assert cluster_get(workspace, first)["view"]
```

- [ ] **Step 2: Run them and see the first fail.** The second cluster is served.

- [ ] **Step 3: Implement.** In `server/core/clusters.py`, add
  `from ai_rfc.ledger import LedgerError, window_of` and:

```python
def refuse_after_the_window(workspace: Path, cluster_id: str) -> None:
    """Refuse a cluster that comes after the window this workspace records.

    A cluster after the window's top describes the repository after the
    window's end, which is future material to a run (the ground-truth
    yardstick spec, section 7.2). A future-free pristine holds none, so this
    is defence in depth. A cluster before the window is the run's past and its
    context, and is served. A workspace that records no window has nothing
    after it.

    Args:
        workspace: The workspace the cluster belongs to.
        cluster_id: An id :func:`checked_cluster_id` has already confirmed.

    Raises:
        CoreError: If the window record cannot be read, or the cluster's
            ordinal is above the window's top.
    """
    try:
        window = window_of(workspace)
    except LedgerError as error:
        raise CoreError(str(error)) from None
    if window is None:
        return
    ordinal = _cluster_ordinals(workspace / "timeline")[cluster_id]
    if ordinal > window[1]:
        raise CoreError(
            f"cluster {cluster_id!r} comes after this run's window, which ends "
            f"at c{window[1]:04d}; what happened after the window is not the "
            "run's to read"
        )
```

  In `queries.cluster_get`, call `refuse_after_the_window(ctx.workspace, cluster_id)` right after
  `checked_cluster_id(...)`, import it beside `checked_cluster_id`, and add the refusal to
  `Raises`. If importing `ai_rfc.ledger` from `server/core/clusters.py` is circular, move the import
  inside the function and say why in a comment.

- [ ] **Step 4: Run** `tests/server tests/ledger` and see them pass.

- [ ] **Step 5: Commit**: `feat(server): refuse a cluster after the run's window`, with
  `ai_rfc/server/core/clusters.py ai_rfc/server/core/queries.py tests/server/test_core.py`.

## Task 7: The path guard

Spec §7.4. The guard today confines Bash to an arm's prefixes (`guard.py` → `is_allowed`), is
mounted with `matcher: "Bash"` only, and takes the prefixes as its whole argv.

**Files:**
- Modify: `ai_rfc/driver/enforcement.py` (add `FILE_TOOLS`, `GUARDED_TOOLS`, `REMOTE_GIT`,
  `outside_paths`, `remote_git`, `refusal`; change `render_settings`)
- Modify: `ai_rfc/driver/guard.py` (`main`), `ai_rfc/driver/session.py` (`prepare_argv`),
  `ai_rfc/experiment/preflight.py` (`prepare_scratch`)
- Test: `tests/driver/test_enforcement.py`, `tests/experiment/test_runner.py`

**Interfaces:**
- Produces: `FILE_TOOLS: dict[str, tuple[str, ...]]`, mapping `Read`, `Edit`, `Write`, `Grep` and
  `Glob` to the input keys that name a path.
- Produces: `GUARDED_TOOLS = ("Bash", *FILE_TOOLS)`, and `REMOTE_GIT: frozenset[str]`.
- Produces: `outside_paths(command: str, workspace: Path) -> list[str]` and
  `remote_git(command: str) -> str | None`.
- Produces: `refusal(tool: str, tool_input: dict[str, Any], prefixes: Sequence[str], workspace: Path)
  -> str | None`, which returns the message the guard prints, or `None` when the arm may make the
  call. Task 8's audit calls this same function.
- Changes: `render_settings(*, python: str, guard: Path, workspace: Path, prefixes: Sequence[str])`.
  The hook command is `python guard.py <workspace> <prefixes…>`, mounted once per tool in
  `GUARDED_TOOLS`. One entry per tool, rather than a regex matcher, so nothing rests on how the CLI
  reads matcher patterns.

- [ ] **Step 1: Write the failing tests** (`tests/driver/test_enforcement.py`).
  - Update the helpers: `_run_guard_raw(payload, *argv)` passes argv through unchanged, and
    `_run_guard(command, *prefixes, workspace=_WORKSPACE)` sends
    `{"tool_name": "Bash", "tool_input": {"command": command}}` with argv `[str(workspace),
    *prefixes]`. `_WORKSPACE = Path(__file__).resolve().parent`.
  - Update `test_settings_use_the_nested_hook_shape`: its entries' matchers are
    `list(GUARDED_TOOLS)`, and every entry carries the same command.
  - Update `test_a_path_with_a_space_still_reaches_the_guard_as_one_argument`: it now expects
    `[python, str(guard), str(workspace), "ai-rfc "]`.
  - Every `render_settings(...)` call in the file gains `workspace=Path("/w")`.
  - Then add:

```python
from ai_rfc.driver.arms import READ_TOOLS
from ai_rfc.driver.enforcement import (
    FILE_TOOLS,
    GUARDED_TOOLS,
    REMOTE_GIT,
    outside_paths,
    refusal,
)

C = bash_prefixes(arm_profile("C"))


@pytest.fixture
def ws(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    (root / "clone").mkdir(parents=True)
    return root


def test_the_guarded_file_tools_are_exactly_the_arms_file_tools():
    assert set(FILE_TOOLS) == set(READ_TOOLS)
    assert GUARDED_TOOLS[0] == "Bash"


@pytest.mark.parametrize(
    "tool,key",
    [("Read", "file_path"), ("Edit", "file_path"), ("Write", "file_path"),
     ("Grep", "path"), ("Glob", "path")],
)
def test_a_file_tool_is_confined_to_the_workspace(ws, tool, key):
    assert refusal(tool, {key: str(ws / "clone" / "a.py")}, (), ws) is None
    assert "denied" in refusal(tool, {key: str(ws.parent / "other" / "a.py")}, (), ws)


def test_a_relative_path_resolves_against_the_workspace(ws):
    assert refusal("Grep", {"path": "clone"}, (), ws) is None
    assert refusal("Grep", {"path": "../other"}, (), ws) is not None


def test_a_symlink_out_of_the_workspace_is_followed(ws):
    outside = ws.parent / "outside.txt"
    outside.write_text("x\n")
    (ws / "link").symlink_to(outside)
    assert refusal("Read", {"file_path": str(ws / "link")}, (), ws) is not None


def test_an_anchored_pattern_is_a_path_and_a_relative_one_is_not(ws):
    assert refusal("Glob", {"pattern": "**/*.py"}, (), ws) is None
    assert refusal("Glob", {"pattern": str(ws.parent / "**" / "*.py")}, (), ws) is not None
    assert refusal("Glob", {"pattern": "../**/*.py"}, (), ws) is not None
    assert refusal("Grep", {"pattern": "H3_", "glob": "../**/*.py"}, (), ws) is not None


@pytest.mark.parametrize(
    "command",
    [
        "git -C /elsewhere/clone log",
        "git --git-dir=/elsewhere/.git log",
        "git -C .. log",
        "git -C clone log -- ../../x",
        "sqlite3 /elsewhere/corpus/index.sqlite 'SELECT 1'",
        "sqlite3 corpus/index.sqlite \"ATTACH '/elsewhere/index.sqlite' AS o\"",
        "python -m ai_rfc.timeline ../other/corpus --out timeline",
        "git -C clone log ~/other",
    ],
)
def test_a_bash_path_outside_the_workspace_is_refused(ws, command):
    assert refusal("Bash", {"command": command}, C, ws) is not None


@pytest.mark.parametrize(
    "command",
    [
        "git -C clone log --oneline -5",
        "git -C clone show 509065a:aioquic/h3/connection.py",
        "sqlite3 corpus/index.sqlite 'SELECT count(*) FROM commits'",
        "git -C clone log --format=%H/%s",
    ],
)
def test_an_in_workspace_bash_command_passes(ws, command):
    assert refusal("Bash", {"command": command}, C, ws) is None


def test_dev_null_is_not_a_path_outside(ws):
    assert outside_paths("git -C clone log 2>/dev/null", ws) == []


@pytest.mark.parametrize("sub", sorted(REMOTE_GIT))
def test_a_git_subcommand_that_reaches_another_repository_is_refused(ws, sub):
    assert "reaches another repository" in refusal(
        "Bash", {"command": f"git -C clone {sub} x"}, C, ws
    )


def test_the_guard_reads_the_tool_and_the_workspace(ws):
    def run(payload, *argv):
        return _run_guard_raw(json.dumps(payload), *argv)

    inside = {"tool_name": "Read", "tool_input": {"file_path": str(ws / "clone")}}
    outside = {"tool_name": "Read", "tool_input": {"file_path": "/etc/hosts"}}
    assert run(inside, str(ws)) == 0
    assert run(outside, str(ws)) == 2
    assert run({"tool_input": {"file_path": str(ws)}}, str(ws)) == 2  # no tool_name
    assert run(inside) == 2  # no workspace argument
```

  In `tests/experiment/test_runner.py`'s settings test:
  - the first entry's matcher stays `"Bash"`;
  - assert `[entry["matcher"] for entry in hooks] == list(GUARDED_TOOLS)`;
  - replace `tuple(parsed[2:]) == families` with `parsed[2] == str(ref.workspace)` and
    `tuple(parsed[3:]) == families`. If `session_spec`'s workspace is not `ref.workspace`, use the
    one it sets.

- [ ] **Step 2: Run them and see them fail**, with `ImportError: cannot import name 'FILE_TOOLS'`.

- [ ] **Step 3: Implement the predicates** in `ai_rfc/driver/enforcement.py`. Add `import os`,
  then add below `is_allowed`:

```python
#: The file tools every arm holds (``arms.READ_TOOLS``; a test pins the two
#: equal), and the input keys that name a path. A ``pattern`` or ``glob``
#: names a path only when it is absolute or climbs.
FILE_TOOLS: dict[str, tuple[str, ...]] = {
    "Read": ("file_path",),
    "Edit": ("file_path",),
    "Write": ("file_path",),
    "Grep": ("path", "glob"),
    "Glob": ("path", "pattern"),
}
#: The tools the guard is mounted for, Bash first.
GUARDED_TOOLS: tuple[str, ...] = ("Bash", *FILE_TOOLS)
#: git subcommands that reach a repository other than the one ``-C`` names, or
#: rewrite where this one borrows objects from. Refused whatever their
#: arguments (the yardstick spec, section 7.4).
REMOTE_GIT = frozenset(
    {"archive", "bundle", "clone", "config", "fetch", "ls-remote", "pull",
     "push", "remote", "submodule", "worktree"}
)
_GIT_OPTIONS_WITH_VALUE = frozenset(
    {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env"}
)
_PATTERN_KEYS = frozenset({"pattern", "glob"})
#: Outside every workspace, and still no route to a repository.
_HARMLESS_OUTSIDE = frozenset({"/dev/null"})
#: An absolute, home-relative or climbing path inside a longer word: a SQL
#: string's ATTACH target, a redirect's file, an option's value, a URL's host.
_EMBEDDED_PATH = re.compile(r"(?:^|(?<=[\s'\"=:,(<>]))(?:~|\.\.|/)[^\s'\",;)]*")


def _inside(candidate: str, workspace: Path) -> bool:
    """Whether ``candidate`` resolves inside ``workspace``, symlinks followed."""
    if candidate in _HARMLESS_OUTSIDE:
        return True
    path = Path(os.path.expanduser(candidate))
    if not path.is_absolute():
        path = workspace / path
    real = Path(os.path.realpath(path))
    root = Path(os.path.realpath(workspace))
    return real == root or real.is_relative_to(root)


def outside_paths(command: str, workspace: Path) -> list[str]:
    """Every path a Bash command names that resolves outside ``workspace``.

    A word counts as a path when it holds a slash, is ``..``, or starts with
    ``~``; a relative one resolves against the workspace, which is the session's
    working directory. Paths embedded in longer words count too, so a SQL
    ``ATTACH '/other.sqlite'`` or a URL is caught. The check fails closed on an
    unterminated quote, which :func:`is_allowed` refuses first anyway.

    Args:
        command: The raw ``tool_input.command`` string.
        workspace: The run's workspace root.

    Returns:
        The offending paths, in the order they appear; empty when none.
    """
    try:
        words = shlex.split(_CONTINUATION.sub(" ", command))
    except ValueError:
        return [command]
    found: list[str] = []
    for word in words:
        candidates = _EMBEDDED_PATH.findall(word)
        if "/" in word or word == ".." or word.startswith("~"):
            value = word.split("=", 1)[1] if word.startswith("-") and "=" in word else word
            candidates.append(value)
        found.extend(c for c in candidates if not _inside(c, workspace))
    return found


def remote_git(command: str) -> str | None:
    """The git subcommand in ``command`` that reaches another repository, if any.

    Args:
        command: The raw ``tool_input.command`` string.

    Returns:
        The first such subcommand, or None.
    """
    try:
        groups = command_groups(command)
    except ValueError:
        return None
    for stages in groups:
        for stage in stages:
            try:
                words = shlex.split(stage)
            except ValueError:
                continue
            if not words or words[0] != "git":
                continue
            index = 1
            while index < len(words) and words[index].startswith("-"):
                index += 2 if words[index] in _GIT_OPTIONS_WITH_VALUE else 1
            if index < len(words) and words[index] in REMOTE_GIT:
                return words[index]
    return None


def _anchored(pattern: str) -> bool:
    return pattern.startswith(("/", "~")) or ".." in Path(pattern).parts


def refusal(
    tool: str, tool_input: dict[str, Any], prefixes: Sequence[str], workspace: Path
) -> str | None:
    """Why the guard blocks one call, or None when the arm may make it.

    The live ``PreToolUse`` guard and the audit both call this, so the two
    cannot disagree about a call.

    Args:
        tool: The tool's name, as the hook payload's ``tool_name`` gives it.
        tool_input: The call's input object.
        prefixes: The arm's allowed Bash prefixes, from :func:`bash_prefixes`.
        workspace: The run's workspace root.

    Returns:
        The message the guard prints to stderr before exiting 2, or None.
    """
    if tool == "Bash":
        command = str(tool_input.get("command", ""))
        if not is_allowed(command, prefixes):
            shown = ", ".join(repr(prefix) for prefix in prefixes) or "(none)"
            return f"denied: this arm may run only {shown}; refused: {command}"
        outside = outside_paths(command, workspace)
        if outside:
            return (
                f"denied: {outside[0]!r} is outside the run's workspace "
                f"{workspace}; refused: {command}"
            )
        remote = remote_git(command)
        if remote is not None:
            return f"denied: git {remote} reaches another repository; refused: {command}"
        return None
    for key in FILE_TOOLS.get(tool, ()):
        value = tool_input.get(key)
        if value is None or value == "":
            continue
        if not isinstance(value, str):
            return f"denied: {tool} {key} is not a path; refused: {value!r}"
        if key in _PATTERN_KEYS and not _anchored(value):
            continue
        if not _inside(value, workspace):
            return (
                f"denied: {tool} may reach only paths inside the run's workspace "
                f"{workspace}; refused {key}={value}"
            )
    return None
```

  `Any`, `re` and `shlex` are already imported there, for `render_settings` and
  `command_groups`.

- [ ] **Step 4: Mount the guard for every guarded tool.** Change `render_settings`:

```python
def render_settings(
    *, python: str, guard: Path, workspace: Path, prefixes: Sequence[str]
) -> dict[str, Any]:
    """The settings document mounting the guard for one arm's session.

    The shape is the nested settings form (``{"hooks": {"PreToolUse": [...]}}``),
    not the flat plugin form. One entry per guarded tool, each running the same
    command, rather than one regex matcher: nothing then rests on how the CLI
    reads matcher patterns.

    Args:
        python: Interpreter that runs the guard.
        guard: Absolute path to ``guard.py``.
        workspace: The run's workspace; the guard refuses paths outside it.
        prefixes: The arm's allowed command prefixes.

    Returns:
        A document to write beside the campaign and pass via ``--settings``.
    """
```

  Keep the existing quoting comment. The command becomes
  `shlex.join([python, str(guard), str(workspace), *prefixes])`, and the return becomes
  `{"hooks": {"PreToolUse": [{"matcher": tool, "hooks": [{"type": "command", "command": argv}]}
  for tool in GUARDED_TOOLS]}}`.

- [ ] **Step 5: The guard script.** In `driver/guard.py`:
  - import `refusal` instead of `is_allowed`;
  - update the module docstring: it blocks a call this arm may not make, whether that is a Bash
    command outside its prefixes or any guarded tool naming a path outside the run's workspace;
  - in `main`, after the existing `tool_input` checks, replace the `command`/`is_allowed` tail with:

```python
    if not argv:
        sys.stderr.write("guard: no workspace argument; refusing every call\n")
        return 2
    tool = payload.get("tool_name")
    if not isinstance(tool, str) or not tool:
        sys.stderr.write("guard: hook payload names no tool\n")
        return 2
    reason = refusal(tool, tool_input, argv[1:], Path(argv[0]))
    if reason is None:
        return 0
    sys.stderr.write(reason + "\n")
    return 2
```

  `main`'s `Args` now reads: "`argv`: the run's workspace, then the arm's allowed command prefixes."

- [ ] **Step 6: The callers.**
  - `driver/session.py` `prepare_argv` passes `workspace=spec.workspace`.
  - `experiment/preflight.py` `prepare_scratch` passes `workspace=scratch / "cwd"` to both
    `render_settings` calls, because the preflight's guarded probes run there.

- [ ] **Step 7: Run** `tests/driver tests/experiment/test_runner.py tests/experiment/test_preflight.py`
  and see them pass.

- [ ] **Step 8: Commit**: `feat(driver): confine every file tool and every Bash path to the run's
  workspace`, with `ai_rfc/driver/enforcement.py ai_rfc/driver/guard.py ai_rfc/driver/session.py
  ai_rfc/experiment/preflight.py tests/driver/test_enforcement.py tests/experiment/test_runner.py`.

## Task 8: The audit reads calls the way the guard does, and checks the clone

Spec §7.3 (prevention half) and §7.4, last paragraph.

**Files:**
- Modify: `ai_rfc/experiment/audit.py` (`in_arm`, `audit_events`, `guard_stats`, `audit_run`; add
  `clone_objects_audit`, `with_git_route`)
- Test: `tests/experiment/test_audit.py`

**Interfaces:**
- Consumes: `refusal`, `GUARDED_TOOLS` (Task 7); `clone_object_problems`, `clone_object_record`
  (Task 1); `classify_future` (the measurement plan's Task 5).
- Changes: `in_arm(name, tool_input, surface, arm, workspace: Path) -> bool`.
- Changes: `guard_stats(...)` replaces `bash_calls`, `fired_for_every_bash_call` and
  `expected_no_bash` with `guarded_calls` and `fired_for_every_guarded_call`.
- Produces: `clone_objects_audit(workspace: Path) -> dict[str, Any]`, returning
  `{"measured": bool, "problems": list[str], "objects": dict | None, "sealed": dict | None,
  "reason": str | None}`.
- Produces: `with_git_route(future: dict, clone_objects: dict) -> dict`.
- Produces: `session_workspace(events: list[dict], fallback: Path) -> Path`, the directory the
  session actually ran in. It is the init event's `cwd`, or `fallback` when the transcript has none.
- The audit record gains `clone_objects`. `future_material` becomes `touched`, through the `git`
  route, when the clone has problems.
- **Paths are judged against the workspace the session ran in, not the directory being audited.**
  A transcript records the absolute paths the model typed, which name the run's **original**
  location. Evidence is re-audited only on copies under `/tmp/claude-501/`, so judging those paths
  against `run_dir / "workspace"` would put every read of every old run out of arm. The same root
  goes to `edit_target`, through `audit_events`, which also fixes its misfiling of prose and register
  edits on a copy. Only the path classification moves. `clone_objects_audit` and `classify_future`
  still read the files on disk, under `run_dir / "workspace"`.

- [ ] **Step 1: Write the failing tests** (`tests/experiment/test_audit.py`; reuse its imports, and
  add what's missing)

```python
from ai_rfc.experiment.audit import (
    audit_events,
    clone_objects_audit,
    guard_stats,
    with_git_route,
)


def _use(tool: str, tool_input: dict, *, text: str = "ok", error: bool = False,
         call_id: str = "t1") -> list[dict]:
    return [
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": call_id, "name": tool, "input": tool_input}]}},
        {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": call_id, "content": text,
             "is_error": error}]}},
    ]


def test_a_read_outside_the_workspace_that_ran_is_out_of_arm(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    audit = audit_events(_use("Read", {"file_path": "/etc/hosts"}), "A", ws)
    assert audit["integrity"] is False
    assert audit["executed_out_of_arm"][0]["name"] == "Read"


def test_a_read_outside_the_workspace_the_guard_blocked_is_a_bypass_attempt(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    events = _use("Read", {"file_path": "/etc/hosts"}, error=True,
                  text="denied: Read may reach only paths inside the run's workspace")
    audit = audit_events(events, "A", ws)
    assert audit["integrity"] is True
    assert audit["bypass_attempts"]["count"] == 1


def test_a_read_inside_the_workspace_is_in_arm(tmp_path):
    ws = tmp_path / "workspace"
    (ws / "clone").mkdir(parents=True)
    audit = audit_events(_use("Read", {"file_path": str(ws / "clone" / "a.py")}), "A", ws)
    assert audit["integrity"] is True


def test_guard_stats_counts_every_guarded_call():
    events = _use("Read", {"file_path": "/w/a"}) + _use("Glob", {"pattern": "*"}, call_id="t2")
    stats = guard_stats(events, "A", "", "")
    assert stats["guarded_calls"] == 2
    assert stats["fired_for_every_guarded_call"] is False  # no hook events in this transcript


def test_a_clone_that_gained_history_touches_through_route_five(tmp_path):
    from ai_rfc.server.testing import git

    ws = tmp_path / "workspace"
    clone = ws / "clone"
    clone.mkdir(parents=True)
    git(clone, "init", "-q", "-b", "main")
    (clone / "a").write_text("a\n")
    git(clone, "add", "a")
    git(clone, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "a")
    git(clone, "remote", "add", "origin", str(tmp_path))
    objects = clone_objects_audit(ws)
    assert objects["measured"] is True and objects["problems"]
    future = with_git_route(
        {"verdict": "clean", "end": "x", "reason": None, "touching": [], "metadata": 0}, objects
    )
    assert future["verdict"] == "touched"
    assert future["touching"][-1]["route"] == "git"


def test_a_workspace_without_a_clone_is_unmeasured_never_clean(tmp_path):
    objects = clone_objects_audit(tmp_path)
    assert objects["measured"] is False and objects["reason"]
    clean = {"verdict": "clean", "end": "x", "reason": None, "touching": [], "metadata": 0}
    assert with_git_route(clean, objects) == clean


def test_a_git_route_keeps_why_the_transcript_was_unmeasured(tmp_path):
    objects = {"measured": True, "problems": ["origin"], "objects": None, "sealed": None,
               "reason": None}
    unmeasured = {"verdict": "unmeasured", "end": None, "reason": "no timeline",
                  "touching": [], "metadata": 0}
    touched = with_git_route(unmeasured, objects)
    assert touched["verdict"] == "touched" and touched["reason"] == "no timeline"


def test_a_copied_run_is_judged_against_the_workspace_it_ran_in(tmp_path):
    """Evidence is audited on copies; its transcript names the original location."""
    original = Path("/orig/runs/A1/workspace")
    events = [{"type": "system", "subtype": "init", "cwd": str(original)}]
    events += _use("Read", {"file_path": str(original / "clone" / "a.py")})
    copy = tmp_path / "copy" / "runs" / "A1" / "workspace"
    root = session_workspace(events, copy)
    assert root == original
    assert audit_events(events, "A", root)["integrity"] is True
    assert session_workspace(events[1:], copy) == copy  # no init event: the fallback
```

  Add `session_workspace` to the import from `ai_rfc.experiment.audit`, and `from pathlib import
  Path` if the file doesn't import it.

  Then update the existing tests that assert `bash_calls`, `fired_for_every_bash_call` or
  `expected_no_bash` to the new keys. Find them with
  `grep -n "bash_calls\|fired_for_every\|expected_no_bash" tests/experiment/test_audit.py`.

- [ ] **Step 2: Run them and see them fail**, with an `ImportError` on `clone_objects_audit`.

- [ ] **Step 3: Implement.**

  **`in_arm`:**
  - Add the `workspace: Path` parameter.
  - Rewrite its body so that every guarded tool is judged by `refusal`:

```python
    if name in GUARDED_TOOLS and refusal(
        name, tool_input, bash_prefixes(arm_profile(arm)), workspace
    ) is not None:
        return False
    if name == "Bash":
        return True
    return surface in ALLOWED_SURFACES[arm]
```

  - Update its docstring: for every tool the guard is mounted for, the verdict comes from
    `enforcement.refusal`, the function the live guard runs, so a path outside the workspace is out
    of arm exactly as a command outside the prefixes is. Keep the existing paragraph about the
    `bash:mixed` label.
  - Add `workspace` to `Args`.
  - In `audit_events`, pass `workspace` to `in_arm`.
  - Fix the imports: import `GUARDED_TOOLS` and `refusal` from `ai_rfc.driver.enforcement`, and drop
    `is_allowed` if nothing else in the module uses it.

  **`guard_stats`:**
  - `guarded = sum(1 for use in tool_uses(events) if use["name"] in GUARDED_TOOLS)`.
  - The record's `bash_calls` becomes `"guarded_calls": guarded`, and
    `"fired_for_every_guarded_call": starts >= guarded` replaces the old flag.
  - Delete `expected_no_bash`: arm A now makes guarded calls too.
  - Rewrite the docstring's arm A paragraph to say this, and rename "Bash call" to "guarded call"
    throughout.

  **New functions** (after `guard_stats`; `RECORD_FILE`, `clone_object_problems`,
  `clone_object_record` and `LifecycleError` come from `ai_rfc.lifecycle`):

```python
def clone_objects_audit(workspace: Path) -> dict[str, Any]:
    """Whether a run's clone still holds exactly the history its pristine sealed.

    A run that fetched, added a remote or borrowed another repository's objects
    reached history past its pin through route 5 (git), whatever its transcript
    says. A clone that cannot be read is unmeasured, never clean.

    Args:
        workspace: The run's workspace root.

    Returns:
        ``measured``, ``problems``, ``objects`` (the clone's object record),
        ``sealed`` (the one ``pristine.json`` holds, or None) and ``reason``
        (why it is unmeasured, or None).
    """
    clone = workspace / "clone"
    if not (clone / ".git").exists():
        return {"measured": False, "problems": [], "objects": None, "sealed": None,
                "reason": f"{clone} is not a repository"}
    try:
        problems = clone_object_problems(clone)
        objects = clone_object_record(clone)
    except LifecycleError as error:
        return {"measured": False, "problems": [], "objects": None, "sealed": None,
                "reason": str(error)}
    record = workspace / RECORD_FILE
    sealed = json.loads(record.read_text()).get("clone_objects") if record.exists() else None
    if sealed is not None and sealed != objects:
        problems.append(
            f"the clone's {objects['count']} stored object(s) differ from the "
            f"{sealed['count']} its pristine sealed"
        )
    return {"measured": True, "problems": problems, "objects": objects,
            "sealed": sealed, "reason": None}


def with_git_route(future: dict[str, Any], clone_objects: dict[str, Any]) -> dict[str, Any]:
    """The future-material verdict, touched when the run's clone gained history.

    Args:
        future: :func:`ai_rfc.experiment.future.classify_future`'s verdict.
        clone_objects: :func:`clone_objects_audit`'s record.

    Returns:
        ``future`` unchanged when the clone has no problem; otherwise a copy
        marked ``touched`` with one more ``touching`` record on route ``git``,
        whose ``call`` is None because no single call is to blame. A
        ``reason`` the transcript verdict gave, such as why it was
        unmeasured, is kept.
    """
    if not clone_objects["problems"]:
        return future
    touching = [*future["touching"], {"call": None, "tool": "git", "route": "git",
                                      "evidence": clone_objects["problems"][:4]}]
    return {**future, "verdict": "touched", "touching": touching}


def session_workspace(events: list[dict[str, Any]], fallback: Path) -> Path:
    """The workspace a transcript's session ran in, which its paths are relative to.

    The session's working directory is its workspace (``driver.session``
    launches it with ``cwd=spec.workspace``), and the init event records it. An
    audit of a copied campaign must judge the transcript's paths against that
    original location, not against the copy's.

    Args:
        events: The parsed transcript.
        fallback: The workspace to use when the transcript records no ``cwd``.

    Returns:
        The init event's ``cwd``, else ``fallback``.
    """
    init = init_event(events) or {}
    cwd = init.get("cwd")
    return Path(cwd) if isinstance(cwd, str) and cwd else fallback
```

  Add `init_event` to the module's existing import from `ai_rfc.driver.stream`.

  **`audit_run`:**
  - Bind `workspace = run_dir / "workspace"`, the files on disk, and
    `ran_in = session_workspace(events, workspace)`, where the transcript's paths point.
  - Pass `ran_in` to `audit_events`.
  - Compute `clone_objects = clone_objects_audit(workspace)`, and set
    `"clone_objects": clone_objects`.
  - The measurement plan's `future_material` entry becomes
    `"future_material": with_git_route(classify_future(events, workspace, campaign.window),
    clone_objects)`. It reads the clone on disk; its path matching splits on `/workspace/`, so it
    doesn't depend on the root.

- [ ] **Step 4: Run** the whole `tests/experiment` directory and see it pass. The audit record's keys
  changed, so any fixture comparison that is exact must be updated in this task.

- [ ] **Step 5: Commit**: `feat(experiment): audit every guarded call with the guard's own verdict
  and check the run's clone`, with `ai_rfc/experiment/audit.py tests/experiment/test_audit.py`.

## Task 9: Preflight measures the read block

Spec §7.4: "a preflight check measures whether the installed CLI honours an exit-2 block on these
tools". This task writes the check and tests its pure half. **Running it spends, and that is Task 11
Step 6.**

**Files:**
- Modify: `ai_rfc/experiment/preflight.py` (`CHECKS`, `prepare_scratch`, `build_invocations`,
  `evaluate`; add `_read_denial_check`)
- Test: `tests/experiment/test_preflight.py`

**Interfaces:**
- Produces: the check `read_denial`, required. It passes when a guarded `Read` outside the probe's
  workspace is denied and leaks nothing, and a `Read` inside it runs.

- [ ] **Step 1: Write the failing tests** (in `tests/experiment/test_preflight.py`).
  - In `test_invocations_cover_every_check_in_order`, insert `"read_denial"` and
    `"read_denial_control"` after `"denial_control"`, and change `len(CHECKS) == 9` to `10`.
  - Add `INSIDE_CANARY`, `OUTSIDE_CANARY` and `REQUIRED` to the `ai_rfc.experiment.preflight`
    import, then add:

```python
def _read(text, *, error, call_id="r1"):
    """One Read call and its result, the shape the stream parser reads."""
    return [
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": call_id, "name": "Read",
             "input": {"file_path": "/x"}}]}},
        {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": call_id, "is_error": error,
             "content": text}]}},
    ]


def test_the_read_denial_probes_carry_the_guard(tmp_path):
    by_name = {inv.name: inv for inv in _invocations(tmp_path)}
    for name in ("read_denial", "read_denial_control"):
        argv = by_name[name].argv
        assert argv[argv.index("--settings") + 1].endswith("guard-C.json"), name
    assert "outside.txt" in by_name["read_denial"].argv[2]
    assert "inside.txt" in by_name["read_denial_control"].argv[2]


def test_evaluate_read_denial(tmp_path):
    refused = _read("PreToolUse hook denied: Read may reach only paths inside", error=True)
    inside = _read(INSIDE_CANARY, error=False, call_id="r2")
    checks = {c["check"]: c for c in evaluate(
        {"read_denial": _outcome(refused), "read_denial_control": _outcome(inside)}, tmp_path)}
    assert checks["read_denial"]["passed"] is True

    leaked = _read(OUTSIDE_CANARY, error=False)
    checks = {c["check"]: c for c in evaluate(
        {"read_denial": _outcome(leaked), "read_denial_control": _outcome(inside)}, tmp_path)}
    assert checks["read_denial"]["passed"] is False
    assert checks["read_denial"]["evidence"]["leaked"] is True


def test_read_denial_is_required():
    assert CHECKS[-1] == "read_denial" and "read_denial" in REQUIRED
```

  If `denials()` does not report an errored `Read` result whose text says "denied", read
  `driver/stream.py` `denials` and build the refused event the way it expects; don't loosen the
  check. The fixture `denied-bash.jsonl` shows the shape a real CLI denial takes.

- [ ] **Step 2: Run them and see them fail.**

- [ ] **Step 3: Implement.**
  - Add `"read_denial"` to the end of `CHECKS`. `REQUIRED` includes it without further change.
  - Add these constants beside the other probes:

```python
OUTSIDE_CANARY = "AI_RFC-OUTSIDE-5521"
INSIDE_CANARY = "AI_RFC-INSIDE-3307"
_READ = "Use the Read tool to read exactly {path} . Then reply DONE."
```

  - In `prepare_scratch`, write `scratch / "outside.txt"` holding `OUTSIDE_CANARY` and
    `scratch / "cwd" / "inside.txt"` holding `INSIDE_CANARY`, each followed by a newline.
  - In `build_invocations`, after `denial_control`, add:

```python
        call("read_denial", _READ.format(path=scratch / "outside.txt"), *guard_flags, where=cwd),
        call("read_denial_control", _READ.format(path=cwd / "inside.txt"), *guard_flags, where=cwd),
```

  - Add the check:

```python
def _read_denial_check(denial: dict[str, Any], control: dict[str, Any]) -> CheckResult:
    """A guarded Read outside the workspace is refused, and one inside it runs."""
    leaked = any(
        not r["is_error"] and OUTSIDE_CANARY in r["text"]
        for r in tool_results(denial["events"]).values()
    )
    found = denials(denial["events"])
    inside_ran = any(
        not r["is_error"] and INSIDE_CANARY in r["text"]
        for r in tool_results(control["events"]).values()
    )
    passed = denial["exit_code"] == 0 and not leaked and bool(found) and inside_ran
    return passed, {
        "leaked": leaked,
        "inside_ran": inside_ran,
        "guard_hooks": len(hook_events(denial["events"])),
        "denials": found[:3],
    }
```

  - In `evaluate`, add
    `"read_denial": _read_denial_check(got("read_denial"), got("read_denial_control")),` and change
    its docstring's "nine" to "ten".
  - Change the module docstring's "Fourteen real `claude -p` calls … nine checks" to "Sixteen …
    ten checks".

- [ ] **Step 4: Run** `tests/experiment/test_preflight.py` and see it pass. Nothing here calls
  `claude`.

- [ ] **Step 5: Commit**: `feat(preflight): measure that the guard blocks a Read outside the
  workspace`, with `ai_rfc/experiment/preflight.py tests/experiment/test_preflight.py`.

## Task 10: Documents

Spec §8 (the second D-row) and §10.

- [ ] **Step 1: `<ai_rfc>/ai_rfc/experiment/README.md`.** Its enforcement section (search for
  `guard.py`) says the guard exits 2 for a Bash command outside the arm's prefixes. Extend it with
  the current rules:
  - The guard is mounted for Bash and for the five file tools, for every arm.
  - It refuses any path outside the run's workspace.
  - It refuses arm C's repository-reaching git subcommands.
  - The audit judges calls with the same predicate, and the preflight's `read_denial` check measures
    the CLI's honouring of the block.

  Add a short "Future-free pristines" paragraph as well:
  - a pristine is built at its window's end;
  - older pristines are refused by `copy_workspace` and remain evidence;
  - the three consequences named in Task 11 Step 7.
- [ ] **Step 2: `<ai_rfc>/CONTEXT.md`** (the measurement plan's Task 9 created it). Add three terms
  to its "Ground truth" section, one line each, with no implementation detail:
  - **cut**: building a windowed pristine at its window's anchor commit, so it holds nothing after
    it;
  - **path guard**: the hook that confines every tool an arm uses to its run's workspace;
  - **clone object set**: the objects a pristine's clone stores, sealed so that a copy that gained
    history is caught.

  If the file calls the anchor commit something else, use its word.
- [ ] **Step 3: commit in ai_rfc**: `docs: describe the path guard and future-free pristines`, with
  `ai_rfc/experiment/README.md CONTEXT.md`.
- [ ] **Step 4: the D-row (PANTHER).**
  - Find the highest D-number across `docs/superpowers/specs/*arfc*`, using the command in the
    measurement plan's Task 9 Step 4. That plan's D-row is already there.
  - Add the next number to the decision table of
    `docs/superpowers/specs/2026-09-02-arfc-draft-quality-design.md`, using the text of the yardstick
    spec's second D-row in §8.
  - Replace "D-(next+1)" in the yardstick spec's §8 with the number you assigned, and the first
    D-row's placeholder too, if the measurement plan left it unnumbered.
- [ ] **Step 5: commit in PANTHER.** Run `git status -sb` first, because peers commit on this
  branch. Message: `docs(ai_rfc): record the future-free workspace D-row`, with the two spec paths.

## Task 11: Gate and acceptance

- [ ] **Step 1: the full suite**, with the same command as Task 0 Step 4. Report the counts against
  the baseline as arithmetic: baseline + new tests − replaced tests.
- [ ] **Step 2: the aioquic w02-11 reproduction, offline, $0.** Work under
  `/tmp/claude-501/ffw-accept/`.
  - Copy `<evidence>/recon.yaml` to `recon.yaml` there, and change two fields:
    - `source.repo` becomes `<evidence>/clone`. A `--no-local` clone only reads it.
    - `workspace:` becomes `/tmp/claude-501/ffw-accept/unused`.

    If `require_toolchain` refuses because `~/ai-rfc-experiments/tools/toolchain.json` fails, set
    `references: []` and delete `toolchain:` in the copy, then record that you did. References do not
    touch cluster ids.
  - Run the code under test, `<wt>/.venv/bin/ai-rfc`, from `<ai_rfc>`. It must not be a pinned
    venv under `~/ai-rfc-experiments/code-pins/`:

```sh
<wt>/.venv/bin/ai-rfc experiment workspace prepare --root /tmp/claude-501/ffw-accept/root \
  --config /tmp/claude-501/ffw-accept/recon.yaml --window 2-11 \
  --template ~/Documents/Documents/Work/AMC3/01_Development/tools/auto-i-d-template \
  --template-commit dcdd985a86afad97a50f7b5e1b613f57c194b774 \
  --forge-snapshot ~/ai-rfc-experiments/pristine/aioquic-w02-11/forge/github.com__aiortc__aioquic/snapshot-2026-08-25T15-16-59Z
```

  **Expected**, as research 11 measured on 2026-09-21:
  - `11 clusters (5 pr, 6 epoch) over 588 commits`;
  - `clusters: 11  pre-seeded: 1  window: [2, 11]`;
  - `cut: 509065ad2fe02d5ecbf335bdab06c7717fb510ca after c0011-epoch-d290ebea69fd`;
  - in `pristine.json`: `cut.forge.pulls_kept == [19, 22, 23, 24, 25]` and
    `clone_objects.count == 3624`;
  - the new `timeline/clusters.jsonl` equals the first 11 lines of
    `<evidence>/timeline/clusters.jsonl`. Compare with `head -11` into a file, then `cmp`;
  - `grep -rl H3_NO_ERROR <new pristine>` finds nothing;
  - in the new clone, `git cat-file -e 6d36838d008c2202c337142fa07e8bf80e96bac8` fails, and
    `git remote` prints nothing.

  Any difference is a finding: stop and report it.
- [ ] **Step 3: copies.**
  - `copy_workspace(<new pristine>, /tmp/claude-501/ffw-accept/run/workspace)` succeeds.
  - `copy_workspace(<evidence>, /tmp/claude-501/ffw-accept/old-copy)` is **refused**, naming
    "records no clone_objects" and the remote. It writes only into `/tmp`.
  - Delete `old-copy` afterwards.
- [ ] **Step 4: `cluster_get` on the copy.** With `AI_RFC_CONFIG=<copy>/recon.yaml`:
  - `cluster_get(resolve_context(), "c0001-epoch-a80c3bdd1e02")` serves c0001, which comes before
    the window;
  - `cluster_get(..., "c0012-pr-2fe6a3623f9e")` is refused by `checked_cluster_id`, because the
    cluster is not in the timeline at all.

  Task 6's unit test covers the refusal above the top, which a future-free pristine cannot reach.
- [ ] **Step 5: the guard, without a session.** Pipe payloads into
  `<wt>/.venv/bin/python <ai_rfc>/ai_rfc/driver/guard.py <copy>`:
  - a `Read` of `<evidence>/clone/aioquic/h3/connection.py` exits 2;
  - a `Read` of `<copy>/clone/aioquic/h3/connection.py` exits 0;
  - a `Bash` command `git -C <evidence>/clone log -1`, with arm C's prefixes appended to the argv,
    exits 2.
- [ ] **Step 6: STOP — the preflight spends.** `ai-rfc experiment preflight` makes 16 real
  `claude -p` calls, each with a $1 budget cap; earlier runs cost cents. Ask the user before running
  it. Once they agree, run it and report every check, `read_denial` in particular. A `read_denial`
  failure means the CLI does not honour an exit-2 block on `Read`: stop and report it, and do not
  adjust the guard to pass.
- [ ] **Step 7: hand over.** Stop before any gitlink bump or push; both need the user. Report:
  - every commit, per repository, with its SHA;
  - the suite counts, and the acceptance results of Steps 2–6;
  - three consequences the Main Campaign must act on (its session was told on 2026-09-22):
    1. MARK w01-69 is re-prepared with the new prepare. It needs no cut.
    2. The optimize route's interview fixture is rebuilt when next needed, because the old
       `~/ai-rfc-experiments/pristine/interview-fixture` is refused.
    3. The freeze's arm-parity check covers the path guard.

---

## Self-review notes (made while writing)

- **Spec coverage:**
  - §7.1: bullets 1–4 → Task 4; the clone → Task 2; R1 → Task 3; git honesty → Tasks 1, 4, 5 and 8;
    older pristines → Tasks 5 and 11; the audit stays → Task 8.
  - §7.2 → Task 6; §7.3's prevention half → Task 8; §7.4 → Tasks 7, 8 and 9.
  - §8's second D-row and §10 → Task 10; §9 → the tests of Tasks 1–9.
  - §11: 1 → Tasks 2 and 4; 2 and 3 → Task 3; 4 → Tasks 7–9; 5 → Tasks 1, 4, 5 and 8; 6 and 7 are
    disclosures, in the README (Task 10).
- **Beyond the literal ruling, flagged for the user.** The Bash path check applies to every arm's
  Bash, arm B's included, not only arm C's. Arm B's `ai-rfc --config <another workspace>` reaches a
  full pristine the same way arm C's `git -C` does. Every legitimate command either arm makes names
  paths inside its workspace. If the user wants arm B exempt, `refusal` takes the arm's prefixes
  already, and the path check can be made conditional on arm C's.
- **Measured, not assumed:** the `--revision` behaviour (Task 2's preamble) was probed on git 2.55.0
  on 2026-09-22, and research 11's numbers (Task 11 Step 2) are from 2026-09-21.
- **Audits of copies (found in review, 2026-09-22):** Task 8 judges a transcript's paths against the
  init event's `cwd`, so re-auditing a copied campaign doesn't put every old read out of arm.
- **`config` in `REMOTE_GIT` is safe:** the draft repository's identity is repo-local
  (`lifecycle/workspace.py` `scaffold` sets `user.name`/`user.email`), so refusing `git config`
  can't strand a prose commit. No arm prompt runs `git config`.
- **Old transcripts and `guard_stats`:** runs made before Task 7 mounted the guard for Bash only, so
  a re-audit of one reports `fired_for_every_guarded_call: false`. That's true of those runs, and is
  why the counts are reported beside the flag.
- **Python 3.10:** `datetime.fromisoformat` does not read `Z`, so Task 3 replaces it. No nested
  same-quote f-strings.
- **Unmeasured:** whether the CLI honours an exit-2 block on `Read`, `Grep`, `Glob`, `Edit` and
  `Write`. Task 9 builds the check, and Task 11 Step 6 runs it with the user's approval.
