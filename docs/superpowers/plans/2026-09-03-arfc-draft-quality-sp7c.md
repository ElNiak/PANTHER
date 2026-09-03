# ai_rfc Draft Quality v2 — SP7c "consolidation rounds" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop the draft from reading like a list of clusters. Every K clusters and once at the end of a sweep, a **consolidation round** rewrites the Introduction, moves the per-cluster narration into a Change Log appendix, pastes the rendered structure blocks, adds references and prunes implementation trivia — recorded as a first-class revision of its own kind, on its own checkpoint root.

**Architecture:** A consolidation is a second kind of round, not a second pass over a cluster. `campaign init` freezes a second prompt per arm from a `consolidation.tmpl.md`; the sweep asks a pure function, derived entirely from artifacts on disk, whether one is due; a due round launches with the consolidation prompt instead of the loop prompt and records a `kind: consolidation` revision against the consolidation checkpoint SP7b built. Two analysis joins learn to ignore those revisions so per-cluster metrics stay per-cluster.

**Tech Stack:** Python 3.10 (stdlib + PyYAML), pytest 8 + pytest-xdist, git.

**Spec:** `docs/superpowers/specs/2026-09-02-arfc-draft-quality-design.md` — **D43** (a consolidation round every K and at sweep end; no in-session subagents; the editorial pass), **D48** (its checkpoint lives under `consolidations/<NN>/`), **D41** (figures whose captions cite), **D50** (if SP4's ledger lands first, the scheduler consumes it), **D52** (`normative_change: false` keeps every citation; a mid-sweep failure is recorded and the sweep continues, a sweep-end failure exits 1). Predecessors: `…-sp7a.md`, `…-sp7b.md`. Successor: SP7d.

## Global Constraints

- **Layout.** Executes AFTER SP1, SP7a and SP7b, on the ai_rfc repository layout. `AIRFC` = the submodule at `$PANTHER/panther/plugins/services/testers/ai_rfc`; driver code under `ai_rfc/experiment/`, its tests under `tests/experiment/`. `PY` = `$PANTHER/.venv/bin/python`. **Task 0 is the precondition gate.**
- **Everything this plan assumes about unlanded code is in the `Interface contract` below**, pinned to the SP7a plan at `34e4bdd45` and the SP7b plan at `bec576f39`. Tasks cite contract items by number and never restate them. A contract item found false is repaired **once, there**.
- **This plan is written three levels ahead of the tree** (post-SP1, post-SP7a, post-SP7b). That is further than SP7a or SP7b reached, and the risk is real: the two items most likely to have moved are **C7** (`prepare_run_argv`'s prompt selection, which SP7a Task 8 rewrites) and **C9** (`loop.tmpl.md`'s step numbering, which SP7a Task 9 rewrites). Task 0 checks both first and says what to do with either answer.
- **Anchors by symbol, never by line number.** Every `file:line` here was verified on the pre-move, pre-SP7a tree; re-anchor with `grep -n "def <name>"` before each edit.
- **Two sessions, one branch.** `git log -1` and `git status --short` in BOTH repos before every task. **A modified file you did not touch means wait** — pre-commit stashes and restores a peer's unstaged work around your commit. Never `git stash` on this worktree.
- **Stage by explicit path**; never `git add -A` or `.`. Commits in `$AIRFC` are `type: lowercase summary`. No `--no-verify`.
- **Tests**: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests -n auto`, at whatever count SP7b's Task 10 recorded. Sandbox off for `pytest` and nested-git writes. `black`, `flake8 --max-line-length=88`, `mypy --follow-imports=silent`.
- **Never run** `panther docs build`, `panther_builder.py clean|package-dev`, or `ai_rfc.experiment audit|analyze` against `~/ai-rfc-experiments/campaigns/mark-full-1` or the aioquic pilot. The MARK A1 baseline is sealed read-only at `~/ai-rfc-experiments/baselines/mark-a1-2026-09-03`; copy from it, never into it.
- **No model runs in this plan.** Every test drives the sweep through a stubbed `spawn`. The paid runs are SP7d's, each approved separately.
- Line length 88, Google-style docstrings, `from __future__ import annotations`, comments only for a non-obvious *why*. No backward-compatibility shims. Fixed dates in fixtures. A test needle must never match a fixture's own name.

## Interface contract

| # | Item | Assumed shape | Verify with |
|---|---|---|---|
| C1 | `ai_rfc/draft/checkpoint.py` | `write_consolidation_checkpoint(manifest_path, ordinal, base_checkpoint, cluster_id, out) -> Path`, writing `out/<NN>/` (SP7b Task 4) | `grep -n "def write_consolidation_checkpoint" -A 8 ai_rfc/draft/checkpoint.py` |
| C2 | `ai_rfc/draft/gate.py` | `RevisionEntry.kind` (default `"cluster"`) and `.checkpoint`; `run_gate(..., consolidations_dir=None)` (SP7b Task 5) | `grep -n "kind\|consolidations_dir" ai_rfc/draft/gate.py` |
| C3 | `ai_rfc/server/core/revisions.py` | `record_revision(ctx, tag, cluster_id, normative_change, note, kind="cluster", checkpoint=None)`, refusing a **second cluster entry** for one cluster (SP7b Task 7) | `grep -n "def record_revision" -A 10 ai_rfc/server/core/revisions.py` |
| C4 | `ai_rfc/server/tools.py` | `ALL_TOOLS` has **20** members, including `ai_rfc_structure_upsert` and `ai_rfc_draft_render` (SP7b Task 7) | `grep -n "ALL_TOOLS" -A 24 ai_rfc/server/tools.py` |
| C5 | `plugins/ai-rfc/skills/` | `ai-rfc-rfc-style` (rewritten by SP7a), `ai-rfc-figures` (SP7a), `ai-rfc-structures` (SP7b); **no** `ai-rfc-editorial` — this plan adds it | `ls plugins/ai-rfc/skills/` |
| C6 | `ai_rfc/experiment/config.py` | `Campaign` is a dataclass ending in defaulted fields (`session_mode: str = "single"` is the precedent); `load_campaign` does `Campaign(**payload)`, so **a new field without a default breaks every frozen campaign.json** | `grep -n "class Campaign" -A 30 ai_rfc/experiment/config.py` |
| C7 | `ai_rfc/experiment/runner.py` | **SP7a Task 8 was to add `prepare_run_argv(..., prompt_file=)`.** Before SP7a the prompt file was hard-coded as `campaign.prompts_dir / f"arm-{ref.arm}.md"`. If the keyword is present, Task 4 uses it; if SP7a landed differently, Task 4 adds it | `grep -n "def prepare_run_argv" -A 12 ai_rfc/experiment/runner.py; grep -n "arm-" ai_rfc/experiment/runner.py` |
| C8 | `ai_rfc/experiment/config.py` | `init_campaign` renders one prompt per arm (`arm_prompt(arm, plugin_root)`), writes `prompts/arm-<X>.md`, and records `prompt_sha256[f"arm-{arm}.md"]`; SP7a Task 8 added a frozen `task.tmpl.md` beside it | `grep -n "def init_campaign" -A 60 ai_rfc/experiment/config.py` |
| C9 | `ai_rfc/experiment/prompts/loop.tmpl.md` | steps numbered 1–10 as **literal text**, with SP7a Task 9's rewritten step 6 and its new build step; step 3b does not exist | `grep -n "^[0-9]" ai_rfc/experiment/prompts/loop.tmpl.md` |
| C10 | `ai_rfc/experiment/render.py` | `SLOT_TABLES: dict[str, dict[str, str]]` keyed `"interactive"`, `"C"`, `"B"`, `"A"`; `render_loop(arm)` refuses a `{{slot}}` with no table entry and **ignores unused table keys**; `arm_prompt(arm, plugin_root)` concatenates `render_loop(arm)` with `NEUTRAL_TEXTS`; `write_plugin_skill(plugin_root)` regenerates `ai-rfc-reconstruction-loop/SKILL.md`, which `test_render.py` pins **byte-for-byte** | `grep -n "SLOT_TABLES\|def render_loop\|def arm_prompt\|NEUTRAL_TEXTS\|def write_plugin_skill" ai_rfc/experiment/render.py` |

Facts verified directly on the current tree, invalidated only by SP1's verbatim move:

| # | Item | Verified shape |
|---|---|---|
| C11 | `experiment/per_cluster.py` | `run_per_cluster(campaign, ref, *, report=print) -> tuple[int \| None, bool, int]`. Its loop is `while True:` → `row, artifacts, position, done, total = window_progress(ref.workspace)` → `if row is None: return …`. **The per-K hook is immediately after `window_progress`; the sweep-end hook is the `row is None` branch.** Neither exists today |
| C12 | `experiment/metrics.py` | `cluster_artifacts` joins revisions by `body.get("cluster_id") == cluster["id"]` and takes `entries[0]`. It drives `completed` in `analyze_run`, `window_progress`, and the sweep's own "is this cluster done" test. **A consolidation entry carries the preceding cluster's id (D48), so without a filter it is indistinguishable from that cluster's own revision except by dict order** |
| C13 | `experiment/summary.py` | `revision_of` performs the same `cluster_id` join, first match wins, feeding `note` and `normative_change` |
| C14 | `experiment/summary.py` | `_previous_tag` steps to the previous revision by decrementing the tag's two-digit suffix, explicitly *not* by cluster; it feeds `citation_delta` and `diffstat` |
| C15 | `tests/experiment/` | `fake_claude` is a real script at `tests/fake_claude/claude`, driven by `$CLAUDE_CONFIG_DIR/fake-scenarios/<run-id>.json`, and is **pinned to one run id** — its own tests say it "cannot stand in for an agent working through a window". The multi-cluster mechanism is `_stub_spawn` in `test_per_cluster.py`, which monkeypatches `per_cluster.spawn` to a counter and patches `cluster_artifacts` in **both** `per_cluster` and `progress` (each imported the name). `_stub_spawn`'s `fake_spawn` ignores `argv` entirely |
| C16 | `tests/experiment/test_per_cluster.py` | `test_a_campaign_frozen_before_the_field_existed_still_loads` already exists — the precedent this plan's new `Campaign` field must satisfy |

> **A correction to the spec, carried here.** The roadmap's gate for SP7c reads "`fake_claude` sequence `c1,c2,cons,c3,cons(final)`". `fake_claude` **cannot** express that: it replays one scenario for one run id and cannot work a window (**C15**). The gate is met with `_stub_spawn`, extended to distinguish the two kinds of round by the prompt file in `argv` — which also makes the assertion stronger, since it checks *which prompt ran*, not merely how many sessions did. Task 8 implements it and Task 9 records the correction in the spec.

## Two design calls this plan makes explicit

**Which revisions the analysis ignores, and which it must not.** Three joins touch revisions (**C12**, **C13**, **C14**). Only the first two get a `kind` filter:

- `cluster_artifacts` and `revision_of` attribute *a revision to a cluster*. A consolidation carries the preceding cluster's id, so without the filter it can be mistaken for that cluster's own work — inflating `completed`, and letting the sweep believe a cluster is done that is not. **Filtered.**
- `_previous_tag` answers *what did this revision change relative to the draft before it*. When a consolidation sits between `c2` and `c3`, `c3`'s diff should be against the consolidated draft — that is exactly what a reader wants, and filtering would produce a diff against a draft state that no longer existed. **Deliberately not filtered**, with a comment saying so, because it looks like an oversight.

**A consolidation's `cluster_id`.** It repeats the preceding cluster round's id. That is what D48's gate check 8 compares (`record["cluster_id"] == previous.cluster_id`), and it is why SP7b's `record_revision` guardrail refuses a second **cluster** entry for one cluster while allowing a consolidation (**C3**).

## File Structure

| File (under `$AIRFC`) | Task | Responsibility after the change |
|---|---|---|
| `ai_rfc/experiment/config.py` | 1, 4 | `Campaign.consolidate_every`; freeze a second prompt per arm |
| `ai_rfc/experiment/consolidation.py` (new) | 2 | `consolidation_due(workspace, every, at_end=False)` — derived from disk, never recorded |
| `ai_rfc/experiment/metrics.py`, `summary.py` | 3 | Two joins ignore consolidation revisions; one deliberately does not |
| `ai_rfc/experiment/prompts/consolidation.tmpl.md` (new) | 4 | The editorial round's prompt |
| `ai_rfc/experiment/render.py` | 4, 5 | `CONSOLIDATION_TEXTS`, `consolidation_prompt`, the step-3b slot rows |
| `ai_rfc/experiment/prompts/loop.tmpl.md` | 5 | Step 3b, `structure_upsert` |
| `plugins/ai-rfc/skills/ai-rfc-editorial/SKILL.md` (new) | 6 | What an editorial pass may and may not do |
| `ai_rfc/experiment/per_cluster.py` | 7 | Schedule and run a consolidation round; failure semantics |
| `ai_rfc/experiment/cli.py` | 8 | `--consolidate-every`, `campaign init --task consolidation` |
| `docs/experiment-protocol.md`, `README.md`, the spec | 9 | The recorded round change and the gate correction |

Tasks 1–3 touch no prompt and no scheduling and can land first; Tasks 4–6 are the prompt surface; Tasks 7–8 are the sweep; Task 9 records.

---

### Task 0: Verify the contract, and settle the two items most likely to have moved

**Files:** none — this task reads, and edits the `Interface contract` table above.

- [ ] **Step 1: Layout, trees and suite**

```bash
cd $AIRFC && ls ai_rfc/draft/structures.py ai_rfc/experiment/render.py tests/experiment
cd $AIRFC && $PY -c "import ai_rfc.draft.structures, ai_rfc.experiment.render"
cd $AIRFC && git status --short
cd $PANTHER && git status --short
cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests -n auto 2>&1 | tail -3
```

Expected: everything lists and imports; both trees clean; the suite at SP7b's recorded count. If `ai_rfc/draft/structures.py` is absent, SP7b has not landed: **STOP**.

- [ ] **Step 2: Settle C7 — how a session's system prompt is chosen**

```bash
cd $AIRFC && grep -n "def prepare_run_argv" -A 12 ai_rfc/experiment/runner.py
cd $AIRFC && grep -n "arm-" ai_rfc/experiment/runner.py
```

Three possible answers, each with a defined consequence:

- `prepare_run_argv` takes a `prompt_file` keyword (SP7a Task 8 landed as planned) → Task 4 passes the consolidation prompt through it and adds nothing.
- It still hard-codes `campaign.prompts_dir / f"arm-{ref.arm}.md"` → **Task 4 adds the keyword itself**, defaulting to today's expression so every existing caller is unchanged. Note the extra scope in the contract table.
- It selects the prompt some third way → read it, write the actual mechanism into **C7**, and route Task 4 through that instead.

- [ ] **Step 3: Settle C9 — where step 3b goes**

```bash
cd $AIRFC && grep -n "^[0-9]" ai_rfc/experiment/prompts/loop.tmpl.md
```

Expected: steps numbered 1–10 in literal text, with SP7a's rewritten step 6 and its build step. Step 3b is inserted between 3 and 4 as an additive list item; the surrounding numerals do **not** move. If SP7a renumbered the steps, record the landed numbering in **C9** and place 3b where `claim_upsert` now sits.

- [ ] **Step 4: The remaining items**

```bash
cd $AIRFC
grep -n "def write_consolidation_checkpoint" -A 8 ai_rfc/draft/checkpoint.py   # C1
grep -n "kind\|consolidations_dir" ai_rfc/draft/gate.py                        # C2
grep -n "def record_revision" -A 10 ai_rfc/server/core/revisions.py            # C3
grep -n "ALL_TOOLS" -A 24 ai_rfc/server/tools.py                               # C4
ls plugins/ai-rfc/skills/                                                      # C5
grep -n "class Campaign" -A 30 ai_rfc/experiment/config.py                     # C6
grep -n "def init_campaign" -A 60 ai_rfc/experiment/config.py                  # C8
grep -n "SLOT_TABLES\|def render_loop\|def arm_prompt\|NEUTRAL_TEXTS\|def write_plugin_skill" ai_rfc/experiment/render.py  # C10
grep -n "def run_per_cluster" -A 12 ai_rfc/experiment/per_cluster.py           # C11
grep -n "def cluster_artifacts" -A 15 ai_rfc/experiment/metrics.py             # C12
grep -n "def revision_of\|def _previous_tag" -A 12 ai_rfc/experiment/summary.py # C13, C14
grep -n "_stub_spawn" -A 22 tests/experiment/test_per_cluster.py               # C15
```

Repair the table where reality differs, then commit the repair if anything changed:

```bash
cd $PANTHER && git status --short
git add -f docs/superpowers/plans/2026-09-03-arfc-draft-quality-sp7c.md
git commit -m "docs(ai_rfc): repair the SP7c contract against the landed tree"
```

---

### Task 1: A campaign says how often to consolidate

**Files:**
- Modify: `ai_rfc/experiment/config.py`
- Test: `tests/experiment/test_config.py`, `tests/experiment/test_per_cluster.py`

**Interfaces:**
- Consumes: the `Campaign` dataclass and `load_campaign`'s `Campaign(**payload)` (**C6**).
- Produces: `Campaign.consolidate_every: int = 10`.

**Why this shape.** `load_campaign` splats the frozen JSON straight into the dataclass (**C6**), so a field without a default makes **every campaign frozen before today unloadable** — including the finished MARK campaign this work is measured against. `session_mode: str = "single"` is the existing precedent, and `test_a_campaign_frozen_before_the_field_existed_still_loads` (**C16**) is the existing test for exactly this hazard; extend it rather than writing a second one.

- [ ] **Step 1: Write the failing tests**

Append to `tests/experiment/test_config.py`:

```python
def test_a_campaign_defaults_to_consolidating_every_ten_clusters(tmp_path):
    campaign = _minimal_campaign(tmp_path)
    assert campaign.consolidate_every == 10


def test_a_campaign_frozen_before_consolidation_existed_still_loads(tmp_path):
    # load_campaign splats the frozen JSON into the dataclass, so a field
    # without a default would make every existing campaign.json unloadable —
    # the finished MARK campaign included.
    from experiment.config import load_campaign

    campaign = _minimal_campaign(tmp_path)
    payload = json.loads((campaign.root / "campaign.json").read_text())
    del payload["consolidate_every"]
    (campaign.root / "campaign.json").write_text(json.dumps(payload))
    assert load_campaign(campaign.root).consolidate_every == 10
```

`_minimal_campaign` is whatever helper the module already uses to build a frozen campaign — read its name at the top of the file rather than assuming one.

- [ ] **Step 2: Run them to verify they fail**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/experiment/test_config.py -k consolidat -v`
Expected: FAIL — `AttributeError: 'Campaign' object has no attribute 'consolidate_every'`.

- [ ] **Step 3: Add the field**

In `ai_rfc/experiment/config.py`, append to `Campaign` **after** every other defaulted field (re-anchor with `grep -n "session_mode"`):

```python
    #: Cluster rounds between consolidation rounds; 0 disables mid-sweep ones.
    consolidate_every: int = 10
```

and set it in `init_campaign` from the config, beside the other fields it freezes.

- [ ] **Step 4: Run the tests and commit**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/experiment/test_config.py -v`
Expected: all PASS, `test_a_campaign_frozen_before_the_field_existed_still_loads` included.

```bash
cd $AIRFC && $PY -m black ai_rfc/experiment/config.py tests/experiment/test_config.py
cd $AIRFC && $PY -m flake8 --max-line-length=88 ai_rfc/experiment/config.py
cd $AIRFC && git status --short
git add ai_rfc/experiment/config.py tests/experiment/test_config.py
git commit -m "feat: let a campaign say how often to consolidate"
```

---

### Task 2: Whether a consolidation is due, derived from disk

**Files:**
- Create: `ai_rfc/experiment/consolidation.py`
- Test: `tests/experiment/test_consolidation.py`

**Interfaces:**
- Consumes: `ai_rfc.draft.gate.load_revisions` and `RevisionEntry.kind` (**C2**).
- Produces: `Due` (frozen: `ordinal`, `base_cluster`, `since`, `reason`) and `consolidation_due(workspace, every, *, at_end=False) -> Due | None`.

**Why this shape.** D50 says state is always derived from artifacts, never recorded — so there is no counter anywhere. The function reads `revisions.yaml` and nothing else, which makes it pure enough to test without a sweep, and makes a resumed campaign schedule identically to one that never stopped. It reads through the substrate's `load_revisions` rather than parsing the YAML again, so the driver and the gate cannot disagree about what a revision is.

If SP4's ledger lands before this (D50), replace the body with a ledger query; the signature is what the sweep depends on and does not change.

- [ ] **Step 1: Write the failing tests**

Create `tests/experiment/test_consolidation.py`:

```python
"""When a consolidation round is due."""

from __future__ import annotations

import pytest

from experiment.consolidation import consolidation_due

pytestmark = pytest.mark.unit

HEAD = "revisions:\n"
SHA = "a" * 64


def _cluster(tag, cluster_id):
    return (
        f"  {tag}:\n"
        f"    cluster_id: {cluster_id}\n"
        f"    checkpoint_manifest_sha256: {SHA}\n"
        "    normative_change: true\n"
        "    note: 'x'\n"
    )


def _consolidation(tag, cluster_id, checkpoint):
    return (
        f"  {tag}:\n"
        f"    cluster_id: {cluster_id}\n"
        f"    checkpoint_manifest_sha256: {SHA}\n"
        "    normative_change: false\n"
        "    note: 'consolidated'\n"
        "    kind: consolidation\n"
        f"    checkpoint: {checkpoint}\n"
    )


def _workspace(tmp_path, body):
    (tmp_path / "revisions.yaml").write_text(HEAD + body)
    return tmp_path


def test_nothing_is_due_before_any_revision(tmp_path):
    assert consolidation_due(tmp_path, 2) is None


def test_nothing_is_due_below_the_threshold(tmp_path):
    ws = _workspace(tmp_path, _cluster("draft-t-01", "c1"))
    assert consolidation_due(ws, 2) is None


def test_one_is_due_at_the_threshold(tmp_path):
    ws = _workspace(tmp_path, _cluster("draft-t-01", "c1") + _cluster("draft-t-02", "c2"))
    due = consolidation_due(ws, 2)
    assert due is not None
    assert (due.ordinal, due.base_cluster, due.since) == (1, "c2", 2)


def test_the_counter_restarts_after_a_consolidation(tmp_path):
    ws = _workspace(
        tmp_path,
        _cluster("draft-t-01", "c1")
        + _cluster("draft-t-02", "c2")
        + _consolidation("draft-t-03", "c2", "consolidations/01")
        + _cluster("draft-t-04", "c3"),
    )
    assert consolidation_due(ws, 2) is None
    due = consolidation_due(ws, 2, at_end=True)
    assert (due.ordinal, due.base_cluster, due.since) == (2, "c3", 1)


def test_the_sweep_end_does_not_consolidate_twice(tmp_path):
    ws = _workspace(
        tmp_path,
        _cluster("draft-t-01", "c1")
        + _consolidation("draft-t-02", "c1", "consolidations/01"),
    )
    assert consolidation_due(ws, 2, at_end=True) is None


def test_zero_disables_mid_sweep_consolidation_but_not_the_final_one(tmp_path):
    ws = _workspace(tmp_path, _cluster("draft-t-01", "c1") + _cluster("draft-t-02", "c2"))
    assert consolidation_due(ws, 0) is None
    assert consolidation_due(ws, 0, at_end=True) is not None
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/experiment/test_consolidation.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'experiment.consolidation'`.

- [ ] **Step 3: Write it**

Create `ai_rfc/experiment/consolidation.py`:

```python
"""When a consolidation round is due, derived entirely from artifacts.

Nothing here records state (D50): the answer is a function of the workspace's
``revisions.yaml``, so a resumed sweep schedules exactly as one that never
stopped. Revisions are read through the substrate's own loader, so the driver
and the gate cannot disagree about what a revision is.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ai_rfc.draft.gate import GateError, load_revisions


@dataclass(frozen=True)
class Due:
    """A consolidation round that should run now."""

    ordinal: int
    base_cluster: str
    since: int
    reason: str


def consolidation_due(workspace: Path, every: int, *, at_end: bool = False) -> Due | None:
    """Decide whether a consolidation round is due.

    Args:
        workspace: The reconstruction workspace.
        every: Cluster rounds between consolidations; 0 disables mid-sweep ones.
        at_end: True when the sweep has no clusters left, which consolidates any
            unconsolidated remainder regardless of ``every``.

    Returns:
        The round to run, or None when none is due — including when every
        cluster round so far is already consolidated.
    """
    revisions = workspace / "revisions.yaml"
    if not revisions.is_file():
        return None
    try:
        entries = load_revisions(revisions)
    except (GateError, OSError):
        # A malformed revisions file is the gate's finding to report, not a
        # reason to schedule an editorial pass over it.
        return None

    consolidations = 0
    since = 0
    base_cluster = ""
    for entry in entries:
        if entry.kind == "consolidation":
            consolidations += 1
            since = 0
        else:
            since += 1
            base_cluster = entry.cluster_id

    if since == 0 or not base_cluster:
        return None
    if at_end:
        return Due(consolidations + 1, base_cluster, since, "sweep end")
    if every and since >= every:
        return Due(consolidations + 1, base_cluster, since, f"{since} cluster rounds")
    return None
```

- [ ] **Step 4: Run the tests and commit**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/experiment/test_consolidation.py -v`
Expected: all PASS.

```bash
cd $AIRFC && $PY -m black ai_rfc/experiment/consolidation.py tests/experiment/test_consolidation.py
cd $AIRFC && $PY -m flake8 --max-line-length=88 ai_rfc/experiment/consolidation.py
cd $AIRFC && $PY -m mypy --follow-imports=silent ai_rfc/experiment/consolidation.py
cd $AIRFC && git status --short
git add ai_rfc/experiment/consolidation.py tests/experiment/test_consolidation.py
git commit -m "feat: derive from disk whether a consolidation round is due"
```

---

### Task 3: Keep per-cluster metrics per-cluster

**Files:**
- Modify: `ai_rfc/experiment/metrics.py`, `ai_rfc/experiment/summary.py`
- Test: `tests/experiment/test_metrics.py`, `tests/experiment/test_summary.py`

**Interfaces:**
- Consumes: `RevisionEntry.kind` (**C2**); the two joins in **C12** and **C13**; `_previous_tag` in **C14**.
- Produces: `cluster_artifacts` and `revision_of` ignore `kind: consolidation` entries; `_previous_tag` deliberately does not.

**Why this shape.** A consolidation revision carries the **preceding cluster's id** (D48), so on the raw `cluster_id` join it is indistinguishable from that cluster's own revision except by dict order (**C12**). Left unfiltered it inflates `completed`, and — worse — the sweep's own "is this cluster done" test would pass for a cluster whose round never ran, so the sweep would skip it silently. That is a wrong *number* and a wrong *behaviour* from one missing filter.

`_previous_tag` is the deliberate exception, and it needs a comment saying so or a future reader will "fix" it.

- [ ] **Step 1: Write the failing tests**

Append to `tests/experiment/test_metrics.py`:

```python
def test_a_consolidation_is_not_mistaken_for_its_cluster_s_revision(tmp_path):
    # Both entries name c1; only the cluster round is c1's own work.
    from experiment.metrics import cluster_artifacts

    workspace = _workspace_with_revisions(
        tmp_path,
        "revisions:\n"
        "  draft-t-01:\n"
        "    cluster_id: c1\n"
        f"    checkpoint_manifest_sha256: {'a' * 64}\n"
        "    normative_change: true\n"
        "    note: 'the cluster round'\n"
        "  draft-t-02:\n"
        "    cluster_id: c1\n"
        f"    checkpoint_manifest_sha256: {'a' * 64}\n"
        "    normative_change: false\n"
        "    note: 'the consolidation'\n"
        "    kind: consolidation\n"
        "    checkpoint: consolidations/01\n",
    )
    artifacts = cluster_artifacts(workspace, {"id": "c1", "ordinal": 1})
    assert artifacts["revision_tag"] == "draft-t-01"
    assert artifacts["note"] == "the cluster round"


def test_a_cluster_with_only_a_consolidation_is_not_complete(tmp_path):
    from experiment.metrics import cluster_artifacts

    workspace = _workspace_with_revisions(
        tmp_path,
        "revisions:\n"
        "  draft-t-01:\n"
        "    cluster_id: c9\n"
        f"    checkpoint_manifest_sha256: {'a' * 64}\n"
        "    normative_change: false\n"
        "    note: 'consolidated'\n"
        "    kind: consolidation\n"
        "    checkpoint: consolidations/01\n",
    )
    assert not cluster_artifacts(workspace, {"id": "c9", "ordinal": 9})["artifacts"]
```

Append to `tests/experiment/test_summary.py`:

```python
def test_a_summary_reports_the_cluster_round_not_the_consolidation(tmp_path):
    from experiment.summary import revision_of

    entry = revision_of(_revisions_with_a_consolidation(tmp_path), "c1")
    assert entry["note"] == "the cluster round"


def test_the_diff_base_is_the_previous_tag_even_when_it_consolidated(tmp_path):
    # Deliberate: c3's diff should be against the consolidated draft, which is
    # the text that actually preceded it.
    from experiment.summary import _previous_tag

    assert _previous_tag("draft-t-04") == "draft-t-03"
```

Write `_workspace_with_revisions` and `_revisions_with_a_consolidation` beside the module's existing helpers, following whatever shape those use.

- [ ] **Step 2: Run them to verify they fail**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/experiment/test_metrics.py tests/experiment/test_summary.py -k consolidat -v`
Expected: FAIL — the joins return the consolidation entry, so `revision_tag` is `draft-t-02` and `note` is `'the consolidation'`.

- [ ] **Step 3: Filter the two attributing joins**

In `ai_rfc/experiment/metrics.py`'s `cluster_artifacts` (re-anchor with `grep -n "def cluster_artifacts"`), narrow the comprehension that selects entries:

```python
    entries = [
        (tag, body)
        for tag, body in (document.get("revisions") or {}).items()
        if body.get("cluster_id") == cluster["id"]
        # A consolidation carries the preceding cluster's id (D48); it is not
        # that cluster's own round, and counting it would let the sweep skip a
        # cluster whose round never ran.
        and body.get("kind", "cluster") != "consolidation"
    ]
```

Apply the identical narrowing in `summary.py`'s `revision_of`.

- [ ] **Step 4: Say why the third join is not filtered**

In `summary.py`'s `_previous_tag`, add to the docstring:

```python
    """The tag before this one, by ordinal — deliberately not by cluster.

    A consolidation shares the tag sequence, so when one sits between two
    cluster rounds it becomes the next round's diff base. That is intended: the
    consolidated draft is the text that actually preceded it, and diffing past
    it would compare against a state that no longer existed.
    """
```

- [ ] **Step 5: Run the suites and commit**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/experiment -n auto 2>&1 | tail -3`
Expected: 0 failed.

```bash
cd $AIRFC && $PY -m black ai_rfc/experiment/metrics.py ai_rfc/experiment/summary.py tests/experiment
cd $AIRFC && $PY -m flake8 --max-line-length=88 ai_rfc/experiment/metrics.py ai_rfc/experiment/summary.py
cd $AIRFC && git status --short
git add ai_rfc/experiment/metrics.py ai_rfc/experiment/summary.py tests/experiment/test_metrics.py tests/experiment/test_summary.py
git commit -m "feat: keep a consolidation out of its cluster's own accounting"
```

---

### Task 4: A second prompt per arm

> **Run Task 6 first.** `CONSOLIDATION_TEXTS` names `ai-rfc-editorial/SKILL.md`, so
> `consolidation_prompt` cannot render until that file exists. The numbering follows the roadmap;
> the dependency does not.

**Files:**
- Create: `ai_rfc/experiment/prompts/consolidation.tmpl.md`
- Modify: `ai_rfc/experiment/render.py`, `ai_rfc/experiment/config.py`, `ai_rfc/experiment/runner.py`
- Test: `tests/experiment/test_render.py`, `tests/experiment/test_config.py`, `tests/experiment/test_runner.py`

**Interfaces:**
- Consumes: `SLOT_TABLES`, `render_loop`, `arm_prompt`, `NEUTRAL_TEXTS` (**C10**); `init_campaign`'s freezing loop (**C8**); `prepare_run_argv` (**C7**).
- Produces: `CONSOLIDATION_TEXTS`; `render_consolidation(arm) -> str`; `consolidation_prompt(arm, plugin_root) -> str`; `prompts/consolidation-<X>.md` frozen and hashed per arm; `prepare_run_argv(..., prompt_file=None)`.

**Why this shape.** A campaign freezes exactly one prompt per arm today and `prepare_run_argv` hard-codes which file it reads (**C7**, **C8**) — that is the single structural assumption a second kind of round breaks, and it is the whole of this task. `render_loop` and `render_consolidation` share one slot validator rather than each getting their own, so the two templates cannot disagree about what a slot is.

**Arm C gets "not available".** D42 freezes arm C at its 18-tool surface, so it has no `structure_upsert` and no `draft_render`; its slot entries say so, and Task 7 skips consolidation rounds for arm C entirely rather than running one with a prompt full of unavailable commands. A v2 campaign compares arms A and B.

- [ ] **Step 1: Write the failing tests**

Append to `tests/experiment/test_render.py`:

```python
def test_the_consolidation_template_renders_for_every_arm():
    from experiment.render import SLOT_TABLES, render_consolidation

    for arm in SLOT_TABLES:
        text = render_consolidation(arm)
        assert "{{" not in text, f"{arm} left a slot unrendered"


def test_arm_c_is_told_the_new_commands_are_unavailable():
    from experiment.render import render_consolidation

    text = render_consolidation("C")
    assert "not available in arm C" in text


def test_the_consolidation_prompt_bundles_the_editorial_skills(tmp_path, plugin_root):
    from experiment.render import consolidation_prompt

    text = consolidation_prompt("A", plugin_root)
    assert "# Editorial" in text or "editorial" in text.lower()
    assert "ai_rfc:struct:" in text or "structure" in text.lower()


def test_the_loop_and_the_consolidation_share_one_slot_validator():
    # A slot present in the template but missing from an arm's table must fail
    # the same way for both renderings.
    from experiment.render import ExperimentError, render_consolidation, render_loop

    for render in (render_loop, render_consolidation):
        with pytest.raises(ExperimentError):
            render("no-such-arm")
```

Append to `tests/experiment/test_config.py`:

```python
def test_a_campaign_freezes_a_consolidation_prompt_per_arm(tmp_path):
    campaign = _minimal_campaign(tmp_path)
    for arm in campaign.arms:
        frozen = campaign.prompts_dir / f"consolidation-{arm}.md"
        assert frozen.is_file()
        assert campaign.prompt_sha256[f"consolidation-{arm}.md"] == _sha256(frozen.read_text())
```

Append to `tests/experiment/test_runner.py`:

```python
def test_a_run_can_be_pointed_at_a_different_frozen_prompt(tmp_path):
    from experiment.runner import prepare_run_argv

    campaign = _minimal_campaign(tmp_path)
    ref = _ref(campaign)
    other = campaign.prompts_dir / f"consolidation-{ref.arm}.md"
    argv = prepare_run_argv(campaign, ref, prompt_file=other)
    assert str(other) in argv
    assert f"arm-{ref.arm}.md" not in " ".join(argv)


def test_the_default_prompt_is_still_the_arm_prompt(tmp_path):
    from experiment.runner import prepare_run_argv

    campaign = _minimal_campaign(tmp_path)
    ref = _ref(campaign)
    assert f"arm-{ref.arm}.md" in " ".join(prepare_run_argv(campaign, ref))
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/experiment/test_render.py tests/experiment/test_config.py tests/experiment/test_runner.py -k "consolidation or prompt" -v`
Expected: FAIL — `render_consolidation` does not exist and `prepare_run_argv` takes no `prompt_file` (unless SP7a Task 8 already added it, per **C7** — in which case only the render tests fail).

- [ ] **Step 3: Write the template**

Create `ai_rfc/experiment/prompts/consolidation.tmpl.md`:

```markdown
# Consolidation round

The draft has grown one cluster at a time and now reads like the order it was
written in. This round changes no claim and adds no evidence. It makes the
document read like a specification.

Work only from what is already in the manifest and the draft. Do not open the
corpus, do not adjudicate, do not answer questions. If you find yourself wanting
a fact that is not already a claim, stop and record it as a question instead.

1. Read every revision recorded since the last consolidation, and the draft as
   it stands: {{revisions_since}}
2. Declare any structure the clusters described in prose but never registered —
   a format, message, record, enumeration or state machine whose fields you can
   each bind to an existing claim: {{structure_upsert}}
3. Render the structures and paste each block verbatim into its owning section,
   delimiters included: {{draft_render}}
4. The editorial pass. In this order:
   - Rewrite the abstract so it says what the protocol does, not how the
     document was produced.
   - Rewrite the Introduction: scope, method, organization. No cluster
     ordinals, no counts of statements added or withdrawn, no "this revision".
   - Regroup the body by concern, not by the order clusters were processed.
   - Move every per-cluster narration sentence into Appendix A, Change Log.
   - Move implementation trivia into Appendix B, Implementation Notes.
   - **Move, never drop.** A sentence you cannot place goes to an appendix. A
     citation that disappears is a normative change, and this round is not one.
   - Add the references the body already relies on, and a figure where a
     reader would otherwise have to imagine the shape. A figure's caption
     cites the claims it depicts.
5. Freeze a consolidation checkpoint. Its requirements must be byte-identical
   to the checkpoint you consolidate from; only the structures may
   differ: {{checkpoint_consolidation}}
6. Record the revision as a consolidation, commit, build and tag:
   {{revision_record_consolidation}}
   {{draft_commit}}
   {{revision_tag}}
7. Lint the result and fix what it finds: {{draft_lint}}

`normative_change` is `false` for this round, and the citation set after it must
equal the set before it. The gate checks both.
```

- [ ] **Step 4: Extract one validator and add the second rendering**

In `ai_rfc/experiment/render.py`, factor the body of `render_loop` so both templates share it (re-anchor with `grep -n "def render_loop"`):

```python
def _render_template(name: str, arm: str) -> str:
    """Render one prompt template for one arm, refusing an unfilled slot."""
    if arm not in SLOT_TABLES:
        raise ExperimentError(f"unknown arm {arm!r}; known arms are {sorted(SLOT_TABLES)}")
    template = (PROMPTS_DIR / name).read_text()
    table = SLOT_TABLES[arm]
    missing = set(SLOT_RE.findall(template)) - set(table)
    if missing:
        raise ExperimentError(f"arm {arm}: no text for slot(s) {sorted(missing)}")
    return SLOT_RE.sub(lambda match: table[match.group(1)], template)


def render_loop(arm: str) -> str:
    """Render the per-cluster round prompt for one arm."""
    return _render_template("loop.tmpl.md", arm)


def render_consolidation(arm: str) -> str:
    """Render the consolidation round prompt for one arm."""
    return _render_template("consolidation.tmpl.md", arm)
```

Keep `render_loop`'s existing name and signature exactly — `arm_prompt`, `write_plugin_skill` and the tests all call it.

Add the bundle and its prompt beside `NEUTRAL_TEXTS` (**C10**):

```python
#: Bundled into the consolidation prompt. The loop's evidence-hygiene text is
#: absent on purpose: this round adjudicates nothing.
CONSOLIDATION_TEXTS = (
    ("skills", "ai-rfc-rfc-style", "SKILL.md"),
    ("skills", "ai-rfc-rfc-style", "references", "claim-citation.md"),
    ("skills", "ai-rfc-figures", "SKILL.md"),
    ("skills", "ai-rfc-structures", "SKILL.md"),
    ("skills", "ai-rfc-editorial", "SKILL.md"),
)


def consolidation_prompt(arm: str, plugin_root: Path) -> str:
    """The consolidation round's system prompt for one arm."""
    return _bundle(render_consolidation(arm), CONSOLIDATION_TEXTS, plugin_root)
```

where `_bundle` is `arm_prompt`'s existing concatenation extracted the same way `_render_template` was — one joiner, so the two prompts cannot drift in how they strip frontmatter.

- [ ] **Step 5: Add the four slot rows to all four arms**

Every `{{slot}}` in the new template needs an entry in each of the four tables or `render_consolidation` refuses the arm (**C10**). The four new slots are `revisions_since`, `structure_upsert`, `draft_render`, `checkpoint_consolidation`, `revision_record_consolidation` — the rest (`draft_commit`, `revision_tag`, `draft_lint`) already exist from SP7a. Following the file's own convention of writing interactive and C text explicitly:

```python
"interactive": {
    "revisions_since": "read `revisions.yaml` and the tags since the last `kind: consolidation` entry",
    "structure_upsert": "`ai_rfc_structure_upsert` with the id, kind, title, section and members",
    "draft_render": "`ai_rfc_draft_render`",
    "checkpoint_consolidation": "`ai_rfc_checkpoint` with the consolidation ordinal and its base",
    "revision_record_consolidation": "`ai_rfc_revision_record` with `kind='consolidation'` and the checkpoint path",
},
"C": {
    "revisions_since": "read `revisions.yaml` and the tags since the last `kind: consolidation` entry",
    "structure_upsert": "not available in arm C",
    "draft_render": "not available in arm C",
    "checkpoint_consolidation": "not available in arm C",
    "revision_record_consolidation": "not available in arm C",
},
"B": {
    "revisions_since": "read `revisions.yaml` and the tags since the last `kind: consolidation` entry",
    "structure_upsert": "`ai_rfc structure-upsert ID --json …`",
    "draft_render": "`ai_rfc draft-render`",
    "checkpoint_consolidation": "`ai_rfc checkpoint ID --consolidation NN --base DIR`",
    "revision_record_consolidation": "`ai_rfc revision-record TAG --kind consolidation --checkpoint consolidations/NN …`",
},
"A": {
    "revisions_since": "read `revisions.yaml` and the tags since the last `kind: consolidation` entry",
    "structure_upsert": "the `ai_rfc_structure_upsert` tool",
    "draft_render": "the `ai_rfc_draft_render` tool",
    "checkpoint_consolidation": "the `ai_rfc_checkpoint` tool with `consolidation` and `base`",
    "revision_record_consolidation": "the `ai_rfc_revision_record` tool with `kind='consolidation'`",
},
```

Merge these into the existing per-arm dicts rather than replacing them. `render_loop` ignores unused table keys (**C10**), so the loop rendering is unaffected — `test_render.py`'s byte-exact pin on the generated skill stays green until Task 5 edits `loop.tmpl.md`.

- [ ] **Step 6: Freeze it per arm**

In `init_campaign` (**C8**), beside the loop's freezing lines:

```python
    for arm in arms:
        text = consolidation_prompt(arm, plugin_root)
        (prompts_dir / f"consolidation-{arm}.md").write_text(text)
        prompt_sha256[f"consolidation-{arm}.md"] = _sha256(text)
```

- [ ] **Step 7: Let a run choose its prompt**

Per **C7**. If `prepare_run_argv` already takes `prompt_file`, skip this step and say so in the commit. Otherwise add it, defaulting to today's expression so no caller changes:

```python
def prepare_run_argv(
    campaign: Campaign,
    ref: RunRef,
    task: str | None = None,
    budget_usd: float | None = None,
    prompt_file: Path | None = None,
) -> list[str]:
```

and replace the hard-coded expression with `prompt_file or campaign.prompts_dir / f"arm-{ref.arm}.md"`.

- [ ] **Step 8: Run the three suites and commit**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/experiment -n auto 2>&1 | tail -3`
Expected: 0 failed. `test_plugin_skill_is_the_interactive_rendering` must still pass — nothing here touches `loop.tmpl.md`.

```bash
cd $AIRFC && $PY -m black ai_rfc/experiment tests/experiment
cd $AIRFC && $PY -m flake8 --max-line-length=88 ai_rfc/experiment
cd $AIRFC && $PY -m mypy --follow-imports=silent ai_rfc/experiment/render.py ai_rfc/experiment/config.py ai_rfc/experiment/runner.py
cd $AIRFC && git status --short
git add ai_rfc/experiment/render.py ai_rfc/experiment/config.py ai_rfc/experiment/runner.py ai_rfc/experiment/prompts/consolidation.tmpl.md tests/experiment
git commit -m "feat: freeze a consolidation prompt per arm"
```

---

### Task 5: Step 3b in the loop

**Files:**
- Modify: `ai_rfc/experiment/prompts/loop.tmpl.md`, `plugins/ai-rfc/skills/ai-rfc-reconstruction-loop/SKILL.md` (regenerated)
- Test: `tests/experiment/test_render.py`

**Interfaces:**
- Consumes: the landed step numbering (**C9**); `SLOT_TABLES`'s new `structure_upsert` row (Task 4); `write_plugin_skill` (**C10**).
- Produces: a cluster round that declares a structure when its cluster defines one.

**Why this shape.** Structures are not only a consolidation's business: a cluster that introduces a wire format should register it while its evidence is in hand (D40). The step is **inserted**, not renumbered — the surrounding numerals are literal text and every other step keeps its number, which is what keeps this a one-line diff rather than a rewrite of a prompt SP7a just rewrote.

`write_plugin_skill` regenerates a file that `test_render.py` pins byte-for-byte (**C10**), so that test goes red the moment the template changes and stays red until the regeneration runs. That is the intended sequence, not a failure.

- [ ] **Step 1: Write the failing test**

Append to `tests/experiment/test_render.py`:

```python
def test_the_loop_tells_a_cluster_to_register_a_structure_it_defines():
    from experiment.render import render_loop

    for arm in ("interactive", "A", "B"):
        text = render_loop(arm)
        assert "3b" in text
        assert "structure" in text.lower()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/experiment/test_render.py -k register_a_structure -v`
Expected: FAIL — no `3b` in the rendering.

- [ ] **Step 3: Insert the step**

In `ai_rfc/experiment/prompts/loop.tmpl.md`, between the existing steps 3 and 4 (**C9**), add:

```markdown
3b. If this cluster defines or changes a wire format, message, record,
    enumeration or state machine, register it now, binding every field, value
    or transition to a claim you just recorded: {{structure_upsert}}
    Then render and paste the block into its owning section: {{draft_render}}
    Skip this step when the cluster describes only behaviour.
```

Leave every other step's number untouched.

- [ ] **Step 4: Regenerate the pinned skill**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m ai_rfc.experiment render`

(the verb `write_plugin_skill` is wired to; read the CLI to confirm its name). Then:

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/experiment/test_render.py -v`
Expected: all PASS, including the byte-exact pin, which now matches the regenerated file.

- [ ] **Step 5: Commit**

```bash
cd $AIRFC && git status --short
git add ai_rfc/experiment/prompts/loop.tmpl.md plugins/ai-rfc/skills/ai-rfc-reconstruction-loop/SKILL.md tests/experiment/test_render.py
git commit -m "feat: let a cluster round register the structure it defines"
```

---

### Task 6: The editorial skill

**Files:**
- Create: `plugins/ai-rfc/skills/ai-rfc-editorial/SKILL.md`
- Test: `tests/experiment/test_render.py`

**Interfaces:**
- Consumes: nothing.
- Produces: the last member of `CONSOLIDATION_TEXTS` (**C5**, Task 4).

**Why this task exists.** `CONSOLIDATION_TEXTS` names this file, so Task 4's `consolidation_prompt` cannot render without it. It was assigned to no plan until the spec was amended on 2026-09-03; SP7a authors only `ai-rfc-rfc-style` and `ai-rfc-figures`.

- [ ] **Step 1: Write the failing test**

Append to `tests/experiment/test_render.py`:

```python
def test_the_editorial_skill_states_the_move_never_drop_rule():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    text = (root / "plugins/ai-rfc/skills/ai-rfc-editorial/SKILL.md").read_text()
    assert "Move, never drop" in text
    assert "Change Log" in text and "Implementation Notes" in text
    assert "normative" in text.lower()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/experiment/test_render.py -k editorial_skill -v`
Expected: FAIL — `FileNotFoundError`.

- [ ] **Step 3: Write the skill**

Create `plugins/ai-rfc/skills/ai-rfc-editorial/SKILL.md`:

```markdown
---
name: ai-rfc-editorial
description: Use during a consolidation round, when the draft must be reorganised into a specification without changing what it claims.
---

# Editorial

A consolidation round changes how the document reads, never what it asserts.
You are reorganising evidence that is already adjudicated.

## The rule that governs everything

**Move, never drop.** Every sentence you remove from the body goes somewhere:
narration to Appendix A, Change Log; implementation trivia to Appendix B,
Implementation Notes. If a sentence belongs nowhere, it is telling you the
document is missing a section — add the section.

A citation that disappears is a normative change, and this round records
`normative_change: false`. The citation set after your edit must equal the set
before it, and the gate checks. If you genuinely believe a claim should no
longer be cited, stop: that is a cluster round's decision, not yours.

## The order

1. **Abstract.** Say what the protocol does. A reader should not learn from it
   that the document was reconstructed.
2. **Introduction.** Scope, method, organization. Strip every cluster ordinal,
   every count of statements added or withdrawn, every "this revision".
3. **Body.** Regroup by concern. The order clusters were processed is an
   artefact of how the work happened and means nothing to a reimplementer.
4. **Appendices.** Change Log first, Implementation Notes second.
5. **Figures and references.** Add a figure where a reader would otherwise have
   to imagine a shape; its caption cites the claims it depicts. Add the
   references the body already relies on.

## What you may not do

Do not adjudicate, do not open the corpus, do not answer an open question, do
not add a claim. If you want a fact that is not already a claim, record a
question and leave the prose alone.
```

- [ ] **Step 4: Run the test and commit**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/experiment/test_render.py -v`
Expected: all PASS.

```bash
cd $AIRFC && git status --short
git add plugins/ai-rfc/skills/ai-rfc-editorial/SKILL.md tests/experiment/test_render.py
git commit -m "feat: say what an editorial pass may and may not change"
```

---

### Task 7: The sweep runs them

**Files:**
- Modify: `ai_rfc/experiment/per_cluster.py`
- Test: `tests/experiment/test_per_cluster.py`

**Interfaces:**
- Consumes: `consolidation_due` and `Due` (Task 2); the frozen `consolidation-<X>.md` and `prepare_run_argv(prompt_file=)` (Task 4); the loop shape in **C11**.
- Produces: `_run_consolidation(campaign, ref, due, *, budget_usd, timeout_s, report) -> tuple[int | None, bool]`; a sweep that schedules consolidation rounds mid-sweep and at the end.

**Why this shape.** Three decisions, each with a consequence a reviewer should be able to check:

- **The check goes after the budget and time guard**, not immediately after `window_progress`. A consolidation costs money like any round; running one past the budget would be the same bug as running a cluster round past it, and the existing guard already handles both if the check sits below it.
- **Success is re-derived, never recorded** (D50). After the session returns, the round succeeded exactly when `consolidation_due(...)` no longer says one is due — because the agent recorded a `kind: consolidation` revision. There is no flag to get out of sync.
- **Arm C never consolidates.** D42 freezes it at the 18-tool surface, so it has no `structure_upsert` and no `draft_render`; its slot rows say "not available in arm C" (Task 4). Launching a round whose every command is unavailable would burn budget to produce nothing, so the sweep skips it and reports why once.

Failure semantics are D52's: mid-sweep, report and carry on — a sweep that halts because an editorial pass failed loses the cluster work it had left to do; at sweep end, exit 1, because the final consolidation is the deliverable.

- [ ] **Step 1: Write the failing tests**

Append to `tests/experiment/test_per_cluster.py`:

```python
def _stub_consolidation(per_cluster, monkeypatch, dues):
    """Make `consolidation_due` answer from a scripted list, once each."""
    answers = list(dues)

    def fake_due(_workspace, _every, *, at_end=False):
        for index, (want_end, due) in enumerate(answers):
            if want_end == at_end:
                answers.pop(index)
                return due
        return None

    monkeypatch.setattr(per_cluster, "consolidation_due", fake_due)


def test_a_consolidation_runs_after_every_k_clusters_and_at_the_end(
    per_cluster_campaign, monkeypatch
):
    import experiment.per_cluster as per_cluster
    from experiment.consolidation import Due

    calls = _stub_spawn(per_cluster, monkeypatch, sessions_per_cluster=1)
    prompts = []
    original = per_cluster.prepare_run_argv

    def record_argv(campaign, ref, **kwargs):
        prompts.append(kwargs.get("prompt_file"))
        return original(campaign, ref, **kwargs)

    monkeypatch.setattr(per_cluster, "prepare_run_argv", record_argv)
    monkeypatch.setattr(
        progress, "window_clusters",
        lambda _ws: [
            {"ordinal": 1, "id": "c1"}, {"ordinal": 2, "id": "c2"}, {"ordinal": 3, "id": "c3"}
        ],
    )
    _stub_consolidation(
        per_cluster, monkeypatch,
        [(False, Due(1, "c2", 2, "2 cluster rounds")), (True, Due(2, "c3", 1, "sweep end"))],
    )

    ref = _ref(per_cluster_campaign)
    exit_code, timed_out, sessions = per_cluster.run_per_cluster(per_cluster_campaign, ref)

    kinds = ["consolidation" if p and "consolidation-" in str(p) else "cluster" for p in prompts]
    assert kinds == ["cluster", "cluster", "consolidation", "cluster", "consolidation"]
    assert (exit_code, timed_out) == (0, False)
    assert sessions == 5 and calls["n"] == 3


def test_arm_c_never_consolidates(per_cluster_campaign, monkeypatch):
    import experiment.per_cluster as per_cluster
    from experiment.consolidation import Due

    _stub_spawn(per_cluster, monkeypatch, sessions_per_cluster=1)
    monkeypatch.setattr(progress, "window_clusters", lambda _ws: [{"ordinal": 1, "id": "c1"}])
    _stub_consolidation(per_cluster, monkeypatch, [(True, Due(1, "c1", 1, "sweep end"))])
    notes = []

    ref = _ref(per_cluster_campaign, arm="C")
    _, _, sessions = per_cluster.run_per_cluster(
        per_cluster_campaign, ref, report=notes.append
    )
    assert sessions == 1
    assert any("arm C" in note for note in notes)


def test_a_mid_sweep_consolidation_failure_does_not_stop_the_sweep(
    per_cluster_campaign, monkeypatch
):
    import experiment.per_cluster as per_cluster
    from experiment.consolidation import Due

    _stub_spawn(per_cluster, monkeypatch, sessions_per_cluster=1)
    monkeypatch.setattr(
        progress, "window_clusters",
        lambda _ws: [{"ordinal": 1, "id": "c1"}, {"ordinal": 2, "id": "c2"}],
    )
    # Always still due: the round never recorded its revision.
    monkeypatch.setattr(
        per_cluster, "consolidation_due",
        lambda _ws, _every, *, at_end=False: (
            None if at_end else Due(1, "c1", 1, "1 cluster round")
        ),
    )
    notes = []
    exit_code, _, sessions = per_cluster.run_per_cluster(
        per_cluster_campaign, _ref(per_cluster_campaign), report=notes.append
    )
    assert exit_code == 0
    assert sessions >= 2
    assert any("consolidation" in note and "recorded no revision" in note for note in notes)


def test_a_failed_final_consolidation_exits_one(per_cluster_campaign, monkeypatch):
    import experiment.per_cluster as per_cluster
    from experiment.consolidation import Due

    _stub_spawn(per_cluster, monkeypatch, sessions_per_cluster=1)
    monkeypatch.setattr(progress, "window_clusters", lambda _ws: [{"ordinal": 1, "id": "c1"}])
    monkeypatch.setattr(
        per_cluster, "consolidation_due",
        lambda _ws, _every, *, at_end=False: Due(1, "c1", 1, "sweep end") if at_end else None,
    )
    exit_code, _, _ = per_cluster.run_per_cluster(
        per_cluster_campaign, _ref(per_cluster_campaign)
    )
    assert exit_code == 1
```

`_ref` gains an `arm=` keyword if it has none; read its current shape first (**C15**).

- [ ] **Step 2: Run them to verify they fail**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/experiment/test_per_cluster.py -k consolidat -v`
Expected: FAIL — `AttributeError: module 'experiment.per_cluster' has no attribute 'consolidation_due'`.

- [ ] **Step 3: Write the round**

In `ai_rfc/experiment/per_cluster.py`, import `consolidation_due` and `Due` at module level (the tests monkeypatch the name **on this module**, so it must be bound here, exactly as `cluster_artifacts` is), then:

```python
def _run_consolidation(
    campaign: Campaign,
    ref: RunRef,
    due: Due,
    *,
    budget_usd: float,
    timeout_s: int,
    at_end: bool,
    report: Callable[[str], None],
) -> bool:
    """Run one consolidation round.

    Args:
        campaign: The frozen campaign.
        ref: The run being swept.
        due: What `consolidation_due` decided.
        budget_usd: Budget remaining for this session.
        timeout_s: Seconds remaining.
        at_end: True for the sweep's final consolidation.
        report: Progress sink.

    Returns:
        True when the round recorded its revision, re-derived from disk rather
        than from the session's exit code — an agent can exit 0 having done
        nothing.
    """
    report(
        f"{ref.run_id}: consolidation {due.ordinal:02d} due ({due.reason}), "
        f"base {due.base_cluster}"
    )
    argv = prepare_run_argv(
        campaign,
        ref,
        task=CONSOLIDATION_TASK.format(ordinal=due.ordinal, base=due.base_cluster),
        budget_usd=budget_usd,
        prompt_file=campaign.prompts_dir / f"consolidation-{ref.arm}.md",
    )
    spawn(
        argv,
        cwd=ref.workspace,
        env=_env(campaign, ref),
        events_path=ref.run_dir / EVENTS_FILE,
        stderr_path=ref.run_dir / STDERR_FILE,
        timeout_s=timeout_s,
        append=True,
    )
    if consolidation_due(ref.workspace, campaign.consolidate_every, at_end=at_end) is None:
        report(f"{ref.run_id}: consolidation {due.ordinal:02d} recorded")
        return True
    report(
        f"{ref.run_id}: consolidation {due.ordinal:02d} recorded no revision"
        + ("" if at_end else "; continuing the sweep")
    )
    return False
```

with the task text as a module constant:

```python
CONSOLIDATION_TASK = (
    "Run consolidation round {ordinal:02d}. The last cluster round was "
    "{base}. Follow the consolidation prompt exactly and change no claim."
)
```

`_env`, `EVENTS_FILE`, `STDERR_FILE` and the `spawn` keyword set are whatever the cluster round already uses — copy that call site rather than inventing one, and re-anchor it with `grep -n "spawn("`.

- [ ] **Step 4: Schedule it**

In `run_per_cluster`, **below** the existing budget and time guard, before the cluster round is prepared:

```python
        if ref.arm != "C" and row is not None:
            due = consolidation_due(ref.workspace, campaign.consolidate_every)
            if due is not None:
                _run_consolidation(
                    campaign, ref, due,
                    budget_usd=budget_left, timeout_s=int(time_left),
                    at_end=False, report=report,
                )
                sessions += 1
                continue
```

and in the `row is None` branch that ends the sweep (**C11**), before returning:

```python
        if row is None:
            if ref.arm == "C":
                report(f"{ref.run_id}: arm C does not consolidate (its tool surface is frozen)")
            else:
                due = consolidation_due(
                    ref.workspace, campaign.consolidate_every, at_end=True
                )
                if due is not None:
                    ok = _run_consolidation(
                        campaign, ref, due,
                        budget_usd=budget_left, timeout_s=int(time_left),
                        at_end=True, report=report,
                    )
                    sessions += 1
                    if not ok:
                        exit_code = 1
            report(f"{ref.run_id}: window complete after {sessions} session(s)")
            return exit_code, any_timeout, sessions
```

The `continue` after a mid-sweep consolidation is deliberate: the next pass re-reads `window_progress`, so the round that just ran is accounted for before a cluster round is chosen. Without it, a consolidation that recorded a revision would be followed by a cluster round chosen from stale progress.

- [ ] **Step 5: Run the suite and commit**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/experiment -n auto 2>&1 | tail -3`
Expected: 0 failed. Every pre-existing `test_per_cluster` test must pass unchanged — a campaign whose `consolidate_every` is the default and whose workspace has no revisions yields `None` from `consolidation_due`, so the sweep behaves exactly as before.

```bash
cd $AIRFC && $PY -m black ai_rfc/experiment/per_cluster.py tests/experiment/test_per_cluster.py
cd $AIRFC && $PY -m flake8 --max-line-length=88 ai_rfc/experiment/per_cluster.py
cd $AIRFC && $PY -m mypy --follow-imports=silent ai_rfc/experiment/per_cluster.py
cd $AIRFC && git status --short
git add ai_rfc/experiment/per_cluster.py tests/experiment/test_per_cluster.py
git commit -m "feat: run a consolidation round every k clusters and at the sweep's end"
```

---

### Task 8: The two switches, and the sequence that proves it

**Files:**
- Modify: `ai_rfc/experiment/cli.py`
- Test: `tests/experiment/test_cli.py`, `tests/experiment/test_per_cluster.py`

**Interfaces:**
- Consumes: `Campaign.consolidate_every` (Task 1); `_run_consolidation` (Task 7).
- Produces: `campaign init --consolidate-every N`; a way to run one consolidation round against an existing workspace.

**Why the second switch matters.** D47's evaluation order includes "one paid consolidation on the MARK A1 copy (~$20)" as its second step. That is a **single consolidation round against a finished workspace**, not a sweep — so SP7d cannot run its own evaluation without this switch. It is the load-bearing half of this task.

Read `ai_rfc/experiment/cli.py`'s existing `campaign init` parser and its run verb before editing: SP7a Task 5 added `toolchain` verbs and SP3 may have restructured the root. The tests below assert **behaviour**, not a parser shape, so they hold whichever way the CLI is organised.

- [ ] **Step 1: Write the failing tests**

Append to `tests/experiment/test_cli.py`:

```python
def test_campaign_init_takes_a_consolidation_interval(tmp_path, monkeypatch):
    root = _init_campaign_via_cli(tmp_path, extra=["--consolidate-every", "3"])
    assert json.loads((root / "campaign.json").read_text())["consolidate_every"] == 3


def test_campaign_init_defaults_the_interval_to_ten(tmp_path, monkeypatch):
    root = _init_campaign_via_cli(tmp_path)
    assert json.loads((root / "campaign.json").read_text())["consolidate_every"] == 10


def test_one_consolidation_can_be_run_against_a_finished_workspace(
    tmp_path, monkeypatch, capsys
):
    # D47's second evaluation step is exactly this: one paid consolidation on a
    # copy of a finished campaign, with no sweep around it.
    import experiment.per_cluster as per_cluster

    seen = {}

    def fake_consolidation(campaign, ref, due, **kwargs):
        seen["at_end"] = kwargs["at_end"]
        seen["ordinal"] = due.ordinal
        return True

    monkeypatch.setattr(per_cluster, "_run_consolidation", fake_consolidation)
    assert _run_cli(["run", "--task", "consolidation", *_run_args(tmp_path)]) == 0
    # at_end is right outside a sweep too: a manual consolidation consolidates
    # whatever remains, regardless of the interval.
    assert seen["at_end"] is True
```

`_init_campaign_via_cli`, `_run_cli` and `_run_args` are the module's existing helpers — read their names at the top of the file. If none exists for driving `campaign init`, write one beside the module's other helpers rather than calling `init_campaign` directly, so the test covers the parser.

- [ ] **Step 2: Run them to verify they fail**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/experiment/test_cli.py -k consolidat -v`
Expected: FAIL — argparse rejects `--consolidate-every`.

- [ ] **Step 3: Add the switches**

On the `campaign init` parser:

```python
    init.add_argument(
        "--consolidate-every",
        type=int,
        default=10,
        help="Cluster rounds between consolidation rounds; 0 disables mid-sweep ones.",
    )
```

threading it into the `CampaignConfig` the verb builds. On the run verb:

```python
    run.add_argument(
        "--task",
        choices=("sweep", "consolidation"),
        default="sweep",
        help="Run the window, or one consolidation round against the workspace as it stands.",
    )
```

and in its dispatch, when `--task consolidation`, resolve the run ref, ask `consolidation_due(workspace, campaign.consolidate_every, at_end=True)`, and call `_run_consolidation(..., at_end=True)` — returning 0 when it recorded, 1 when it did not. `at_end=True` is right even outside a sweep: a manual consolidation consolidates whatever remains, regardless of the interval.

- [ ] **Step 4: The gate — the full sequence**

The spec's gate for SP7c is the sequence `c1,c2,cons,c3,cons(final)`. `test_a_consolidation_runs_after_every_k_clusters_and_at_the_end` (Task 7 Step 1) is that gate: three clusters, a mid-sweep consolidation after the second, and a final one, asserted on **which prompt each session was launched with** rather than on a session count.

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/experiment/test_per_cluster.py -k every_k_clusters -v`
Expected: PASS, with `kinds == ["cluster", "cluster", "consolidation", "cluster", "consolidation"]`.

- [ ] **Step 5: Run everything and commit**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests -n auto 2>&1 | tail -3`
Expected: 0 failed.

```bash
cd $AIRFC && $PY -m black ai_rfc/experiment/cli.py tests/experiment/test_cli.py
cd $AIRFC && $PY -m flake8 --max-line-length=88 ai_rfc/experiment/cli.py
cd $AIRFC && git status --short
git add ai_rfc/experiment/cli.py tests/experiment/test_cli.py
git commit -m "feat: set the consolidation interval, and run one on its own"
```

---

### Task 9: Record the round, and correct the spec's own gate

**Files:**
- Modify: `docs/experiment-protocol.md`, `README.md`, `docs/superpowers/specs/2026-09-02-arfc-draft-quality-design.md` (in `$PANTHER`)
- Test: the whole suite

- [ ] **Step 1: The whole suite**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests -n auto 2>&1 | tail -3`
Expected: 0 failed. Record the count.

- [ ] **Step 2: Protocol and README**

In `docs/experiment-protocol.md`, add "2026-09-03 — draft quality v2, SP7c": (1) a sweep now runs two kinds of round, and a campaign records `consolidate_every` (default 10); (2) a consolidation round runs every K cluster rounds and once at the sweep's end, launched with its own frozen `consolidation-<arm>.md` prompt; (3) it changes no claim — `normative_change` is `false` and the citation set is preserved, which the gate checks; (4) its checkpoint lives under `consolidations/<NN>/` and its revision carries `kind: consolidation`; (5) **arm C never consolidates**, because D42 freezes its tool surface, so a v2 campaign compares arms A and B; (6) whether a consolidation is due is derived from `revisions.yaml` alone and never recorded, so a resumed sweep schedules identically; (7) a mid-sweep consolidation that records no revision is reported and the sweep continues; a failed final one exits 1.

In `README.md`: add `--consolidate-every` and `run --task consolidation` to the verb table, and one sentence saying a consolidation round reorganises the draft without changing what it claims.

- [ ] **Step 3: Correct the spec's gate wording**

The spec's roadmap row for SP7c says the gate is a "`fake_claude` sequence". `fake_claude` replays one scenario for one run id and cannot work a window (**C15**); the gate is met with `_stub_spawn` asserting which prompt each session ran. Amend that row in `docs/superpowers/specs/2026-09-02-arfc-draft-quality-design.md`:

> `_stub_spawn` sequence `c1,c2,cons,c3,cons(final)`, asserted on the prompt each session was launched with

- [ ] **Step 4: Commit**

```bash
cd $AIRFC && git status --short
git add docs/experiment-protocol.md README.md
git commit -m "docs: record the consolidation round"
```

```bash
cd $PANTHER && git status --short
git add -f docs/superpowers/specs/2026-09-02-arfc-draft-quality-design.md
git commit -m "docs(ai_rfc): correct SP7c's gate — fake_claude cannot work a window"
```

Then bump the submodule pointer in PANTHER (`chore(ai_rfc): bump ai_rfc to SP7c (<old>..<new>)`), pushing the submodule before the parent, each push confirmed with the user first.

---

## Self-review (run by the plan author on 2026-09-03)

1. **Spec coverage.** The roadmap row names six items: `loop.tmpl.md` steps → Task 5; `consolidation.tmpl.md` → Task 4; the `ai-rfc-editorial` skill → Task 6; scheduling from disk → Tasks 2 and 7; `--consolidate-every` → Tasks 1 and 8; protocol docs → Task 9. The gate is Task 7 Step 1's sequence test, re-stated in Task 8 Step 4 and corrected in Task 9 Step 3. D43 → Tasks 4, 5, 7. D48 → Task 3 (the join filter) and Task 7 (the base cluster). D50 → Task 2's derivation, with the ledger contingency noted in its "Why this shape". D52's three SP7c clauses → the prompt's closing paragraph (Task 4 Step 3) and Task 7's failure semantics. D41 → the consolidation prompt's figure step and the editorial skill. Not in SP7c: the instrument and the paid runs (D44, D47 → SP7d), though Task 8's `--task consolidation` exists **because** D47 step 2 needs it.
2. **Placeholder scan.** No "TBD"/"TODO"/"handle edge cases". Two exceptions to "every code step shows its code", both deliberate and both named here rather than glossed — SP7b's self-review learned that lesson the expensive way. **Task 3 Step 1's `_workspace_with_revisions` and `_revisions_with_a_consolidation`** are described, not written: each wraps a helper the target test module already has under a name only the landed tree knows, and the tests that call them are written in full, so the shape is pinned even though the wrapper is not. **Task 8 Step 1's `_init_campaign_via_cli`, `_run_cli` and `_run_args`** are the same case. Everything else is code.

   Five steps say "read the landed shape first", each naming the exact grep and what to do with either answer: Task 0 (the whole contract), Task 4 Step 7 (`prepare_run_argv`, which SP7a Task 8 may already have parameterised), Task 5 Step 4 (the render verb's name), Task 7 Step 3 (the `spawn` call site and `_env`), and Task 8 Step 3 (the CLI's parser shape, which SP7a Task 5 and SP3 both touch). Each is a symbol whose location only an earlier plan decides.
3. **Type consistency.** `consolidation_due(workspace, every, *, at_end=False) -> Due | None` is called with those arguments in Tasks 2, 7 and 8, and its `Due(ordinal, base_cluster, since, reason)` is constructed positionally in Task 7's tests exactly as Task 2 declares it. `_run_consolidation(campaign, ref, due, *, budget_usd, timeout_s, at_end, report) -> bool` matches between Task 7's definition, its scheduler call sites and Task 8's dispatch. `render_consolidation(arm) -> str` and `consolidation_prompt(arm, plugin_root) -> str` match between Task 4's definitions and its tests. `prepare_run_argv(..., prompt_file=None)` matches between Task 4 Step 7 and Task 7 Step 3.
4. **The two things a reviewer should check hardest.** First, that the mid-sweep `continue` in Task 7 Step 4 is present — without it a consolidation is followed by a cluster round chosen from stale progress, which is a silent mis-sequencing no test in this plan would catch except the ordering assertion. Second, that `consolidation_due` is imported **into `per_cluster`'s module namespace**; the tests monkeypatch it there, so a `from … import` inside the function body would make every scheduling test pass against unpatched code.

## Execution

Subagent-driven, one fresh implementer per task, a reviewer between tasks. Tasks 1–3 touch no prompt and no scheduling and may run first in any order. Task 4 needs Task 6's skill file to exist for `consolidation_prompt` to render, so **run Task 6 before Task 4** despite the numbering, or write the skill as Task 4's first step. Task 5 needs Task 4's slot rows. Task 7 needs Tasks 2 and 4. Task 8 needs Tasks 1 and 7. Task 9 is last.

Keep the deviation log SP7a and SP7b used: one row per step where reality differed, so SP7d is written against fact.
