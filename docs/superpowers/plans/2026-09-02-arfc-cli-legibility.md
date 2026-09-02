# `panther ai-rfc` Legibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `panther ai-rfc --help` teach the workflow — eight commands under three headings, in pipeline order, each described in plain words — and rename the one opaque verb from `adjudicate` to `check`.

**Architecture:** The eight verbs stay, one per tool-backed pipeline stage, and the 1:1 verb↔module mapping is preserved. `EntryPoint` gains a `section` field; the click group gains a `format_commands` override that lists commands under their section in registration order instead of alphabetically in one unlabelled block. The rename covers every surface a user reads — verb, stage name, dispatch literal, `--help` prose, docs — and stops at `promotion.adjudicate`, the function that genuinely adjudicates.

**Tech Stack:** Python 3.10, click 8.x (`>=8.0.0,<9.0`), argparse sub-CLIs, pytest, mkdocs-click.

**Spec:** This plan's *Context* section below. The prior plan it extends is `docs/superpowers/plans/2026-09-02-arfc-panther-subcommand.md`, whose Global Constraints are reproduced here and still bind.

**Working directory:** `/Users/elniak/Documents/Documents/Work/Project/Protocol-Testing-Security/PANTHER/master/.claude/worktrees/iut-ai-rfc` — a git worktree on branch `feat/arfc-pipeline-and-runtime-anchors`.

**Line numbers verified against HEAD `e85be8762`.** Another session can commit to this branch inside this worktree. Run `git log --oneline -1` before Task 1; if HEAD has moved, re-anchor every citation by symbol rather than by line.

## Global Constraints

- **Invocation-neutral.** No existing `python -m panther.plugins.services.testers.ai_rfc[.SUB]` string, no `prog=` value, and no file location may change. Those strings are written into generated agent skills and recorded in the frozen pilot artifacts; the pending main run must stay comparable.
- **Nothing under `harness/` is touched.** It is a separate git submodule and its strings are the experiment's instrument.
- **New modules inside the `ai_rfc` package must not define `_report` or `_git`.** A conventions test scans every non-harness `.py` in that package for those names and diffs the result against the README's duplication table. (`panther/cli/commands/ai_rfc.py` is outside the package and is not scanned.)
- Line length 88 (Black), isort import order, Google-style docstrings (Args/Returns/Raises) on public functions, `from __future__ import annotations` as in the surrounding modules.
- Commit format `type(scope): lowercase summary`, no trailing period.
- **Never run `panther docs build`.** `panther/cli/commands/docs.py:82-84` unconditionally `shutil.rmtree`s `docs/`, which holds ten tracked files including the prior plan.
- Run mypy with `--follow-imports=silent`; without it it reports ~1100 pre-existing errors across 108 files.
- Do not trust bare `flake8` — it defaults to 79 columns and reports false E501s. pre-commit runs it at 88.
- This worktree-isolated session refuses compound shell (`source .../activate`). Use `.venv/bin/…` directly. The sandbox blocks an SSL keylog write during pytest collection, so test runs need it disabled.

---

## Context

The `panther ai-rfc` front door landed today (`e3496b7`, `3e45f15`, `305370f2`, `e85be87`). It works, but it is not readable. Its actual help output:

```
Commands:
  adjudicate  Validate a manifest, adjudicate its claims and verify its anchors
  coverage    Propose runtime anchors from a coverage report
  draft       checkpoint, gate, completeness — freeze and gate a prose draft
  forge       fetch, adopt — pull and review evidence, with or without credentials
  history     Extract a commit corpus from a clone
  pipeline    status, substrate, run — drive the deterministic stages
  timeline    Cluster the corpus into an ordered timeline
  views       Emit per-cluster evidence bundles
```

Three defects, all in the text rather than the structure:

1. **`adjudicate`'s summary defines the word with itself** — "Validate a manifest, *adjudicate* its claims". A reader who does not know the word learns nothing.
2. **Two summaries lead with bare tokens** (`checkpoint, gate, completeness —`), so the eye hits jargon before meaning.
3. **The list hides the workflow.** The eight verbs are stages 1–9 of one pipeline (`pipeline/stages.py:39-70`), and `pipeline run` already performs four of them for you (`pipeline/run.py:145-172`). Presented alphabetically as peers, that ordering is invisible — which is what makes eight feel like too many.

### Why the eight verbs stay

Collapsing them costs hand-tunability: `pipeline run` builds each stage's argv purely from the `Workspace` (`run.py:49-74`), so a collapsed `run --stage timeline` could not reach `timeline`'s own `--forge`/`--only`/`--patches`. Every sibling group in this CLI is also exactly two levels deep (`panther config validate`, `panther tools status`), so nesting would break house style.

### Why the rename is safe, and where it stops

`promotion.adjudicate(claim) -> Status` keeps its name: it weighs evidence and returns a verdict, which is genuinely adjudication. The command does not adjudicate — it reports and gates on the result. Two operations, each correctly named.

Three facts, each verified against the tree rather than assumed:

- **No frozen string is touched.** The `python -m` doors go through `__main__.py`, never through click, and `EntryPoint.prog` is deliberately decoupled from `EntryPoint.verb` (`entrypoints.py:32-38`). `prog="ai_rfc"` stays.
- **Nothing reads a stage name back.** Stage names are never written to disk — `_finish` prints to stdout (`pipeline/cli.py:212-222`). They *are* a machine-readable contract (`pipeline status --json` and `run --json` emit `next_action.stage`, `performed[].stage`, `halted_at` at `pipeline/cli.py:107,121,194,218`), but nothing consumes the value `"adjudicate"` from it: `tests/.../pipeline/test_cli.py` asserts only on `mining`, `history` and `timeline` (`:31,32,48,88,108`).
- **The harness reads no stage names.** `grep` over `harness/plugins/ai-rfc/skills/` and `harness/experiment/prompts/` for `pipeline`/`stage`/`mining` returns nothing.

**Accepted cost:** the harness submodule still calls the concept `adjudicate` in its MCP tool `ai_rfc_claim_adjudicate` (`harness/.../tools.py:54`) and CLI verb `claim-adjudicate` (`harness/.../cli.py:97`). `harness/` may not be touched, so that split is recorded as deferred item #4 in Task 4 rather than closed.

---

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `panther/plugins/services/testers/ai_rfc/entrypoints.py` | The registry: one `EntryPoint` per command, now carrying its help heading | 1, 2 |
| `panther/plugins/services/testers/ai_rfc/cli.py` | The manifest gate's argparse CLI — description only; `prog` untouched | 1 |
| `panther/plugins/services/testers/ai_rfc/pipeline/stages.py` | The ordered stage table | 1 |
| `panther/plugins/services/testers/ai_rfc/pipeline/run.py` | Stage → sub-CLI dispatch | 1 |
| `panther/plugins/services/testers/ai_rfc/pipeline/state.py` | Stage → state-probe table | 1 |
| `panther/cli/commands/ai_rfc.py` | The click group: passthrough commands, and now the sectioned listing | 3 |
| `tests/unit/plugins/services/testers/ai_rfc/pipeline/test_stages.py` | Stage-order contract | 1 |
| `tests/unit/plugins/services/testers/ai_rfc/pipeline/test_state.py` | Stage-state contract | 1 |
| `tests/unit/plugins/services/testers/ai_rfc/test_cli_conventions.py` | Registry invariants | 2 |
| `tests/unit/test_cli/test_ai_rfc_commands.py` | Click-door invariants, and now the rendered help | 3 |
| `docs_src/reference/ai_rfc.md`, `docs_src/reference/cli.md` | Hand-written reference; mkdocs-click cannot carry the sections | 1, 4 |
| `panther/plugins/services/testers/ai_rfc/README.md`, `.../pipeline/README.md` | Package docs | 1, 4 |

**Three files look like they should change and must not.** Each was checked; leaving them alone is verified-correct, not an oversight:

- `tests/.../pipeline/test_cli.py` — asserts stage names in the JSON payload, but only `mining`, `history` and `timeline`; its runs halt at stage 5.
- `panther/plugins/services/testers/ai_rfc/report.py` — emits `id`, `stored`, `supported`, `promotable`; the private `_adjudicated` helper's name never reaches `report.json`.
- `tests/.../test_promotion.py` — its 15 references exercise `promotion.adjudicate`, the function that keeps its name.

---

## Task 1: Rename the manifest gate to `check`

**Files:**
- Modify: `panther/plugins/services/testers/ai_rfc/entrypoints.py:36,61`
- Modify: `panther/plugins/services/testers/ai_rfc/cli.py:30-34`
- Modify: `panther/plugins/services/testers/ai_rfc/pipeline/stages.py:62`
- Modify: `panther/plugins/services/testers/ai_rfc/pipeline/run.py:21,77,81,160,161`
- Modify: `panther/plugins/services/testers/ai_rfc/pipeline/state.py:276`
- Test: `tests/unit/plugins/services/testers/ai_rfc/pipeline/test_stages.py:70-73`
- Test: `tests/unit/plugins/services/testers/ai_rfc/pipeline/test_state.py:128-136`
- Modify: `docs_src/reference/ai_rfc.md:24,42`
- Modify: `panther/plugins/services/testers/ai_rfc/README.md:113,234,247,249,256,257`
- Modify: `panther/plugins/services/testers/ai_rfc/pipeline/README.md:32,62`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: the verb string `"check"` and the stage name `"check"`, both of which Task 2 reorders and Task 4 documents. `EntryPoint`'s field list is unchanged by this task.

- [ ] **Step 1: Confirm the tree is where the plan expects**

```bash
cd /Users/elniak/Documents/Documents/Work/Project/Protocol-Testing-Security/PANTHER/master/.claude/worktrees/iut-ai-rfc
git log --oneline -1
git status --short
```

Expected: HEAD is `e85be8762`, working tree clean. If HEAD differs, re-anchor every line citation in this plan by symbol before continuing.

- [ ] **Step 2: Update the two stage-name tests to expect `check`**

In `tests/unit/plugins/services/testers/ai_rfc/pipeline/test_stages.py`, replace lines 70-73:

```python
def test_mining_precedes_the_check_and_prose_precedes_its_gate():
    """Order is the contract: nothing checks claims that were never mined."""
    order = [item.name for item in STAGES]
    assert order.index("mining") < order.index("check")
```

In `tests/unit/plugins/services/testers/ai_rfc/pipeline/test_state.py`, replace lines 128 and 136:

```python
def test_check_and_gate_are_never_reported_done(workspace: Path):
```

```python
    assert states["check"] is State.BLOCKED
```

- [ ] **Step 3: Run the two tests to verify they fail**

```bash
.venv/bin/pytest tests/unit/plugins/services/testers/ai_rfc/pipeline/test_stages.py::test_mining_precedes_the_check_and_prose_precedes_its_gate tests/unit/plugins/services/testers/ai_rfc/pipeline/test_state.py::test_check_and_gate_are_never_reported_done -v
```

Expected: both FAIL. `test_stages` with `ValueError: 'check' is not in list`; `test_state` with `KeyError: 'check'`.

- [ ] **Step 4: Rename the stage**

`pipeline/stages.py` line 62:

```python
    Stage(6, "check", Performer.DETERMINISTIC),
```

`pipeline/state.py` line 276:

```python
        "check": rederivable,
```

`pipeline/run.py` line 21:

```python
from .. import cli as check_cli
```

`pipeline/run.py` lines 77-81:

```python
def _check(ws: Workspace, strict: bool) -> tuple[list[str], CommandModule]:
    argv = [str(ws.manifest), "--out", str(ws.out), "--repo", str(ws.clone)]
    if strict:
        argv.append("--strict")
    return argv, check_cli
```

`pipeline/run.py` lines 160-161:

```python
    elif stage.name == "check":
        argv, module = _check(ws, strict)
```

- [ ] **Step 5: Run the two tests to verify they pass**

```bash
.venv/bin/pytest tests/unit/plugins/services/testers/ai_rfc/pipeline/ -v
```

Expected: PASS, whole pipeline test directory green.

- [ ] **Step 6: Rename the verb, leaving `prog` alone**

`entrypoints.py` line 61 — change the **verb** only. Line 62 is `"ai_rfc"`, the frozen `prog`; do not touch it.

```python
    EntryPoint(
        "check",
        "ai_rfc",
        f"{PACKAGE}.cli",
        "Validate a manifest, adjudicate its claims and verify its anchors",
    ),
```

(The summary is rewritten in Task 2. Leaving it stale for one commit is deliberate — this commit is the rename, that one is the wording.)

`entrypoints.py` line 36, inside the `prog` attribute docstring:

```
            prints. Deliberately not derived from ``verb``: the root validator
            answers to ``check`` but has always called itself ``ai_rfc``,
            and changing that would alter output the harness records.
```

- [ ] **Step 7: Rewrite the argparse description**

`cli.py` lines 30-34. **Leave `prog="ai_rfc"` on line 29 untouched.**

```python
        description=(
            "Report which claims in a reconstructed requirement manifest are "
            "not backed by the code their anchors point at: check the schema, "
            "weigh every claim against the promotion rule, and optionally "
            "verify repository anchors against their pinned commits."
        ),
```

- [ ] **Step 8: Update the docs the rename invalidates**

These are the rename's own worked examples. Leaving them for Task 4 would land a tree whose README tells the reader to run a command that no longer exists.

`docs_src/reference/ai_rfc.md` line 24:

```
| 6 | check | deterministic | `report.{json,yaml,md}` |
```

`docs_src/reference/ai_rfc.md` line 42:

```
| `panther ai-rfc check` | Validate a manifest; weigh claims against evidence; verify anchors |
```

`panther/plugins/services/testers/ai_rfc/README.md` lines 113, 256, 257 — `panther ai-rfc adjudicate` → `panther ai-rfc check` in all three command examples.

`panther/plugins/services/testers/ai_rfc/pipeline/README.md` line 32:

```
| 6 | `check` | deterministic | `manifest.yaml` → `out/report.*` |
```

`panther/plugins/services/testers/ai_rfc/pipeline/README.md` line 62 — `` `adjudicate` and `gate` are `re-derivable` `` → `` `check` and `gate` are `re-derivable` ``.

`panther/plugins/services/testers/ai_rfc/README.md` line 234, in "The authoring loop" — this names the command, since step 3 of that same list says to run it:

```markdown
**Do not decide a claim's status.** Write the claim and its evidence, and let
`check` tell you what that evidence supports. Concretely:
```

`README.md` line 247 — "adjudicated" here describes the value the report calls `supported`, so name it that:

```markdown
4. **Record the supported status.** See the caveat below: the report tells you
```

`README.md` lines 249 and 397 both read `promotion.adjudicate` and cite the retained function. **Leave both exactly as they are.**

- [ ] **Step 9: Verify no user-facing surface still says the old word**

```bash
grep -rn "adjudicate" --include="*.py" --include="*.md" \
  panther/ docs_src/ tests/ \
  | grep -v "/harness/" | grep -v "promotion" | grep -v "_adjudicated"
```

Expected: no hits naming a command or a stage. Hits inside `test_promotion.py`, `promotion.py`, `report.py`, `models.py` and `__init__.py` are the retained function and are correct.

- [ ] **Step 10: Run the full ai_rfc suite and the click-door suite**

```bash
.venv/bin/pytest tests/unit/plugins/services/testers/ai_rfc/ tests/unit/test_cli/test_ai_rfc_commands.py -n auto
```

Expected: all pass. Collect the count rather than assuming it — two counts in the prior plan were stale at approval.

- [ ] **Step 11: Confirm both doors still agree**

```bash
.venv/bin/python -m panther.plugins.services.testers.ai_rfc --help | head -3
.venv/bin/python -m panther ai-rfc check --help | head -3
```

Expected: identical text, and `usage: ai_rfc` in both — the `prog` survived the rename.

- [ ] **Step 12: Commit**

```bash
git add panther/plugins/services/testers/ai_rfc/entrypoints.py \
        panther/plugins/services/testers/ai_rfc/cli.py \
        panther/plugins/services/testers/ai_rfc/pipeline/stages.py \
        panther/plugins/services/testers/ai_rfc/pipeline/run.py \
        panther/plugins/services/testers/ai_rfc/pipeline/state.py \
        panther/plugins/services/testers/ai_rfc/README.md \
        panther/plugins/services/testers/ai_rfc/pipeline/README.md \
        tests/unit/plugins/services/testers/ai_rfc/pipeline/test_stages.py \
        tests/unit/plugins/services/testers/ai_rfc/pipeline/test_state.py \
        docs_src/reference/ai_rfc.md
git commit -m "refactor(ai_rfc): name the manifest gate check, not adjudicate"
```

---

## Task 2: Declare a help section on every entry point

**Files:**
- Modify: `panther/plugins/services/testers/ai_rfc/entrypoints.py:29-46,58-108`
- Test: `tests/unit/plugins/services/testers/ai_rfc/test_cli_conventions.py`

**Interfaces:**
- Consumes: the verb `"check"` from Task 1.
- Produces: `EntryPoint.section: str`, and the three module-level heading constants `DRIVEN`, `BY_HAND`, `PERFORMED`. Task 3 reads `entry.section` off each entry and copies it onto the click command.

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/plugins/services/testers/ai_rfc/test_cli_conventions.py`:

```python
def test_every_entry_declares_a_section():
    """An empty heading would drop a command out of the listing in silence."""
    assert all(entry.section for entry in ENTRY_POINTS)


def test_entries_sharing_a_section_are_contiguous():
    """Declaration order is the help's order. A section split across two runs
    of the tuple would print its heading twice, and the second block would
    read as a different group of commands."""
    runs = []
    for entry in ENTRY_POINTS:
        if not runs or runs[-1] != entry.section:
            runs.append(entry.section)
    assert len(runs) == len(set(runs))
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
.venv/bin/pytest tests/unit/plugins/services/testers/ai_rfc/test_cli_conventions.py -k section -v
```

Expected: both FAIL with `AttributeError: 'EntryPoint' object has no attribute 'section'`.

- [ ] **Step 3: Add the field and the heading constants**

In `entrypoints.py`, above `ENTRY_POINTS`:

```python
#: Headings ``panther ai-rfc --help`` lists commands under. Plain text: click's
#: formatter writes them verbatim, so backticks would print as backticks.
DRIVEN = "Commands you drive"
BY_HAND = "Run these yourself"
PERFORMED = "Stages that pipeline run performs for you"
```

Add to the `EntryPoint` dataclass body, after `summary`:

```python
    section: str
```

And to its `Attributes:` docstring, after the `summary` entry:

```
        section: The heading ``panther ai-rfc --help`` lists this command
            under. Entries sharing one are kept contiguous in
            :data:`ENTRY_POINTS`, because that order is the order the help
            prints.
```

- [ ] **Step 4: Rewrite `ENTRY_POINTS` in workflow order with new summaries**

Replace the whole tuple. Ordering is free — verified: `test_cli_conventions.py` parametrizes over it, `test_ai_rfc_commands.py` compares it as a set, and the only `sorted` call in either file is `test_cli_conventions.py:74`, over `rglob("*.py")`.

```python
ENTRY_POINTS: tuple[EntryPoint, ...] = (
    EntryPoint(
        "pipeline",
        "ai_rfc.pipeline",
        f"{PACKAGE}.pipeline.cli",
        "Show where a workspace stands and run whatever stage is ready "
        "(status, substrate, run)",
        DRIVEN,
    ),
    EntryPoint(
        "check",
        "ai_rfc",
        f"{PACKAGE}.cli",
        "Report which manifest claims are not backed by the code their "
        "anchors point at",
        BY_HAND,
    ),
    EntryPoint(
        "draft",
        "ai_rfc.draft",
        f"{PACKAGE}.draft.cli",
        "Freeze the manifest per cluster, then gate the prose against it "
        "(checkpoint, gate, completeness)",
        BY_HAND,
    ),
    EntryPoint(
        "coverage",
        "ai_rfc.coverage",
        f"{PACKAGE}.coverage.cli",
        "Propose anchors for the lines a test run actually executed",
        BY_HAND,
    ),
    EntryPoint(
        "history",
        "ai_rfc.history",
        f"{PACKAGE}.history.cli",
        "Turn a pinned clone's commits into a queryable corpus",
        PERFORMED,
    ),
    EntryPoint(
        "forge",
        "ai_rfc.forge",
        f"{PACKAGE}.forge.cli",
        "Pull pull-request discussion from GitHub or GitLab (fetch, adopt)",
        PERFORMED,
    ),
    EntryPoint(
        "timeline",
        "ai_rfc.timeline",
        f"{PACKAGE}.timeline.cli",
        "Group the corpus into ordered clusters, one per pull request",
        PERFORMED,
    ),
    EntryPoint(
        "views",
        "ai_rfc.views",
        f"{PACKAGE}.views.cli",
        "Write the per-cluster evidence folder an author reads",
        PERFORMED,
    ),
)
```

Two deliberate departures from the wording first sketched: **"Run these yourself", not "Gates you run yourself"**, because `coverage` is not a gate — it has no `--strict` and never returns 3 (`coverage/cli.py`); and **no backticks in any heading**, because click prints them literally.

- [ ] **Step 5: Run the tests to verify they pass**

```bash
.venv/bin/pytest tests/unit/plugins/services/testers/ai_rfc/test_cli_conventions.py tests/unit/test_cli/test_ai_rfc_commands.py -v
```

Expected: all pass. `test_each_verb_carries_a_description` asserts `ai_rfc.commands[entry.verb].help == entry.summary`, so it tracks the new summaries automatically.

- [ ] **Step 6: Eyeball the help — sections should NOT appear yet**

```bash
.venv/bin/python -m panther ai-rfc --help
```

Expected: still one alphabetical `Commands:` block, but with the new summaries. The sectioning arrives in Task 3. Seeing sections here would mean click found a `format_commands` that does not exist yet.

- [ ] **Step 7: Commit**

```bash
git add panther/plugins/services/testers/ai_rfc/entrypoints.py \
        tests/unit/plugins/services/testers/ai_rfc/test_cli_conventions.py
git commit -m "feat(ai_rfc): give every entry point a help section and a plain summary"
```

---

## Task 3: Render the sections in `panther ai-rfc --help`

**Files:**
- Modify: `panther/cli/commands/ai_rfc.py` (whole file)
- Test: `tests/unit/test_cli/test_ai_rfc_commands.py`

**Interfaces:**
- Consumes: `EntryPoint.section` from Task 2.
- Produces: nothing later tasks depend on in code. `SECTION_ATTR` and `SectionedGroup` stay private to this module.

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_cli/test_ai_rfc_commands.py`:

```python
def _command_sections(output: str) -> dict[str, str]:
    """Split rendered group help into {heading: the block beneath it}.

    Args:
        output: The rendered ``panther ai-rfc --help`` text.

    Returns:
        Each heading the registry declares, mapped to its slice of the help.

    Raises:
        ValueError: If a declared heading is absent — which is exactly what
            click's unsectioned default produces.
    """
    headings = list(dict.fromkeys(entry.section for entry in ENTRY_POINTS))
    starts = [output.index(f"{heading}:") for heading in headings]
    ends = starts[1:] + [len(output)]
    return {
        heading: output[start:end]
        for heading, start, end in zip(headings, starts, ends)
    }


def test_the_sections_appear_in_declaration_order():
    """Registry order is the workflow order; alphabetical would hide it."""
    output = CliRunner().invoke(ai_rfc, ["--help"]).output
    headings = list(dict.fromkeys(entry.section for entry in ENTRY_POINTS))
    positions = [output.index(f"{heading}:") for heading in headings]
    assert positions == sorted(positions)


def test_each_verb_is_listed_under_the_section_it_declares():
    """The only guard on the ``format_commands`` override. Click's default
    sorts every command into one unlabelled block and renders without error,
    so nothing else here would notice the sectioning silently reverting."""
    output = CliRunner().invoke(ai_rfc, ["--help"]).output
    sections = _command_sections(output)
    for entry in ENTRY_POINTS:
        assert entry.verb in sections[entry.section]
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
.venv/bin/pytest tests/unit/test_cli/test_ai_rfc_commands.py -k section -v
```

Expected: both FAIL with `ValueError: substring not found` — click's default emits `Commands:`, not `Commands you drive:`.

- [ ] **Step 3: Add the sectioned group**

In `panther/cli/commands/ai_rfc.py`, after the imports:

```python
#: Attribute a passthrough command carries its help heading on. Mirrors
#: ``FEATURED_EXAMPLE_ATTR`` in ``panther.cli.core.base``, which is how this
#: codebase already attaches help metadata to a command.
SECTION_ATTR = "_panther_help_section"


class SectionedGroup(click.Group):
    """A group that lists its commands under headings, in registration order.

    Click's own ``format_commands`` sorts alphabetically into a single
    unlabelled block. These commands are the stages of one pipeline, so the
    order they are declared in is the order they are meant to be run in, and
    flattening it is what makes eight commands read as too many.
    """

    def format_commands(self, ctx: click.Context, formatter) -> None:
        """Write one definition list per section, in registration order.

        Args:
            ctx: The context being formatted.
            formatter: The help formatter to write into.
        """
        sections: dict[str, list[click.Command]] = {}
        for name in self.commands:
            command = self.get_command(ctx, name)
            if command is None or command.hidden:
                continue
            heading = getattr(command, SECTION_ATTR, "Commands")
            sections.setdefault(heading, []).append(command)

        for heading, commands in sections.items():
            limit = formatter.width - 6 - max(len(c.name) for c in commands)
            rows = [(c.name, c.get_short_help_str(limit)) for c in commands]
            with formatter.section(heading):
                formatter.write_dl(rows)
```

Iterating `self.commands` rather than `self.list_commands(ctx)` is what preserves order: `list_commands` sorts, and `self.commands` is a dict populated by the `add_command` loop at the foot of the module, so it keeps insertion order.

- [ ] **Step 4: Wire it with `cls=` and fix the leaked markup**

Replace the group declaration. **Without `cls=`, `SectionedGroup` is never constructed and the help renders unchanged with no error** — the class would be dead code. The docstring's `` `` `` markers currently print literally in the terminal, so drop them.

```python
@click.group(name="ai-rfc", cls=SectionedGroup)
def ai_rfc() -> None:
    """Reconstruct an RFC-style specification from a project's own history.

    Every subcommand forwards its arguments unchanged to the matching
    python -m panther.plugins.services.testers.ai_rfc entry point, which
    remains supported and is what the agent harness invokes.
    """
```

- [ ] **Step 5: Carry the section onto each command**

In `_passthrough`, replace the `Returns:` clause and the final `return`:

```python
    Returns:
        A click command named for ``entry.verb``, taking every argument
        uninterpreted, and tagged with ``entry.section`` so the group can
        list it under the right heading.
    """
```

```python
    setattr(command, SECTION_ATTR, entry.section)
    return command
```

- [ ] **Step 6: Run the tests to verify they pass**

```bash
.venv/bin/pytest tests/unit/test_cli/test_ai_rfc_commands.py -v
```

Expected: all pass, including the four pre-existing parametrized tests.

- [ ] **Step 7: Read the rendered help**

```bash
.venv/bin/python -m panther ai-rfc --help
```

Expected: three headings in order — `Commands you drive:`, `Run these yourself:`, `Stages that pipeline run performs for you:` — eight commands under them, no stray backticks, no `adjudicate`.

- [ ] **Step 8: Confirm the passthrough still passes through**

```bash
.venv/bin/python -m panther ai-rfc check --help
.venv/bin/python -m panther ai-rfc check --version
```

Expected: the argparse help from `cli.py` with `usage: ai_rfc`, and `ai_rfc <version>`. The group's `format_commands` must not intercept a subcommand's `--help`, which `add_help_option=False` plus `ignore_unknown_options` already guarantees.

- [ ] **Step 9: Commit**

```bash
git add panther/cli/commands/ai_rfc.py tests/unit/test_cli/test_ai_rfc_commands.py
git commit -m "feat(cli): group ai-rfc's commands by what they are for"
```

---

## Task 4: Mirror the grouping in the hand-written docs

mkdocs-click walks `list_commands` and renders its own markdown (`mkdocs_click/_docs.py:122`), so the terminal sections **do not** reach `docs_src/reference/cli.md`'s generated block. The hand-written pages must mirror them by hand.

**Files:**
- Modify: `docs_src/reference/ai_rfc.md:40-49`
- Modify: `docs_src/reference/cli.md:9-10`
- Modify: `docs/superpowers/plans/2026-09-02-arfc-panther-subcommand.md` (Known cosmetic gaps, Deferred)
- Create: `docs/superpowers/plans/2026-09-02-arfc-cli-legibility.md`

**Interfaces:**
- Consumes: the eight summaries and three headings from Task 2.
- Produces: nothing consumed by code.

- [ ] **Step 1: Re-section and re-word the verb table**

`docs_src/reference/ai_rfc.md` lines 40-49. The Purpose column was written independently of `entrypoints.py` and already disagrees with it — compare `forge`'s row ("PR and review evidence, from the API or from records obtained without credentials") with its registry summary. **Copy the Task 2 summaries across verbatim**, or the two surfaces keep drifting.

```markdown
**Commands you drive**

| Command | Purpose |
|---|---|
| `panther ai-rfc pipeline` | Show where a workspace stands and run whatever stage is ready (`status`, `substrate`, `run`) |

**Run these yourself**

| Command | Purpose |
|---|---|
| `panther ai-rfc check` | Report which manifest claims are not backed by the code their anchors point at |
| `panther ai-rfc draft` | Freeze the manifest per cluster, then gate the prose against it (`checkpoint`, `gate`, `completeness`) |
| `panther ai-rfc coverage` | Propose anchors for the lines a test run actually executed |

**Stages `pipeline run` performs for you**

| Command | Purpose |
|---|---|
| `panther ai-rfc history` | Turn a pinned clone's commits into a queryable corpus |
| `panther ai-rfc forge` | Pull pull-request discussion from GitHub or GitLab (`fetch`, `adopt`) |
| `panther ai-rfc timeline` | Group the corpus into ordered clusters, one per pull request |
| `panther ai-rfc views` | Write the per-cluster evidence folder an author reads |
```

Markdown renders backticks, so headings here keep them; only the terminal strings in `entrypoints.py` must stay plain.

- [ ] **Step 2: Update the CLI reference note**

`docs_src/reference/cli.md` lines 9-12. Replace:

```markdown
    plugin type — it is reached as `panther ai-rfc <verb>`. Its eight
    subcommands below are passthroughs onto standalone `argparse` commands, so
    their arguments are not described here; see
    [ai_rfc (reconstructed specs)](ai_rfc.md) for each one's options.
```

with:

```markdown
    plugin type — it is reached as `panther ai-rfc <verb>`. Its eight
    subcommands below are passthroughs onto standalone `argparse` commands, so
    their arguments are not described here; see
    [ai_rfc (reconstructed specs)](ai_rfc.md) for each one's options.

    The generated listing below is flat and alphabetical. `panther ai-rfc
    --help` groups the same eight under three headings — the one command you
    drive, the three you run yourself, and the four `pipeline run` performs
    for you — because that grouping is the workflow order.
```

- [ ] **Step 3: Record the accepted split and the new deferral**

In `docs/superpowers/plans/2026-09-02-arfc-panther-subcommand.md`, under **Known cosmetic gaps**, add: the harness submodule's `ai_rfc_claim_adjudicate` and `claim-adjudicate` still name the concept `adjudicate`, and `panther ai-rfc check --version` still prints `ai_rfc` because `prog` may not change.

Under **Deferred, and why**, add item 4: rename the concept inside the harness submodule, blocked on the main experiment run for the same reason as items 1–3.

- [ ] **Step 4: Save this plan into the repo**

Copy this plan to `docs/superpowers/plans/2026-09-02-arfc-cli-legibility.md`, matching the sibling plan's naming.

- [ ] **Step 5: Verify the docs build inputs without building**

```bash
grep -rn "adjudicate" docs_src/ | grep -v promotion
.venv/bin/python -c "import mkdocs"
```

Expected: no hits in `docs_src/`. **Do not run `panther docs build`** — it `shutil.rmtree`s `docs/`, which holds these plan files.

- [ ] **Step 6: Commit**

```bash
git add docs_src/reference/ai_rfc.md docs_src/reference/cli.md \
        docs/superpowers/plans/2026-09-02-arfc-panther-subcommand.md \
        docs/superpowers/plans/2026-09-02-arfc-cli-legibility.md
git commit -m "docs(ai_rfc): mirror the grouped CLI and record the split"
```

---

## Final Verification

- [ ] **Full suite**

```bash
.venv/bin/pytest tests/ -n auto -m unit
```

Report the pass/fail count. Collect it; do not assume it.

- [ ] **Types**

```bash
.venv/bin/mypy --follow-imports=silent \
  panther/cli/commands/ai_rfc.py \
  panther/plugins/services/testers/ai_rfc/entrypoints.py \
  panther/plugins/services/testers/ai_rfc/pipeline/run.py
```

- [ ] **Lint**

```bash
pre-commit run --files $(git diff --name-only e85be8762..HEAD)
```

- [ ] **The two doors agree on exit codes 1 and 3**

Check **1 and 3 specifically**. The prior plan records that exits 2 and 0 both arrive as an argparse-raised `SystemExit` and survive a wrongly-written `return`, so those two prove nothing. Run the click door and the `python -m` door against a manifest that violates the promotion rule, once with `--strict` (expect 3 from both) and once against a missing manifest (expect 1 from both).

- [ ] **The frozen door still produces identical output**

Task 1 Step 7 deliberately rewrites that door's `--help` prose, so diff behaviour, not help text:

```bash
.venv/bin/python -m panther.plugins.services.testers.ai_rfc fixture.yaml --out a/
.venv/bin/python -m panther ai-rfc check              fixture.yaml --out b/
diff a/report.json b/report.json && echo "doors agree"
```

Separately confirm `git diff e85be8762..HEAD` shows no change to any `prog=` line, no file rename, and no edit under `harness/`.

---

## Risks

- **`format_commands` reverting to sorted order is silent** — the help still renders, just flat. Task 3 Step 1's tests are the only guard.
- **`panther check` already exists** as a top-level command (`panther/cli/core/main.py:160`, a code-quality runner wrapping black/isort/flake8/mypy/bandit). `panther ai-rfc check` is a different group with no technical conflict, but the two are easy to confuse in conversation.
- **Stale line numbers**, if another session commits to this branch between approval and execution. Task 1 Step 1 is the check.

---

## Corrections found during execution

Recorded because each was invisible until the step was actually run.

**The plan's own rendering test was too weak.** Task 3 Step 1 asserted
`entry.verb in sections[entry.section]`. `draft`'s summary names `checkpoint`,
and `draft` sits in the same section as `check`, so that assertion would have
passed with `check` misfiled into any section — the exact defect it exists to
catch. Strengthened at implementation time to `f"\n  {entry.verb} "`, which
matches only the term column click's `write_dl` writes.

**One documentation edit silently did nothing.** Task 1 Step 8's second pattern
for `docs_src/reference/ai_rfc.md:42` assumed the `panther ai-rfc adjudicate` →
`check` replacement had already run in that file, but that replacement was
scoped to the package README. Neither matched, and the row kept the old verb
until a follow-up edit. The Step 9 verification grep is what caught it.

**isort blocked the Task 3 commit.** It removed one blank line after the
imports in `panther/cli/commands/ai_rfc.py`. The hook fixed the file and failed
the commit, as designed; re-staging and re-committing was the whole remedy. No
`--no-verify`.

**The sandbox does block pytest collection**, exactly as the constraints said:
`PermissionError: [Errno 1] Operation not permitted` writing the SSL keylog,
raised through `nicegui` → `aiohttp` → `ssl.create_default_context`. Every test
run in this plan needs the sandbox disabled. The `panther` CLI itself imports
lazily and runs fine sandboxed.

## Outcome

Four commits on `feat/arfc-pipeline-and-runtime-anchors`, one per task:

| Task | SHA | Commit |
|---|---|---|
| 1 | `0515735be` | `refactor(ai_rfc): name the manifest gate check, not adjudicate` |
| 2 | `4fd785ab2` | `feat(ai_rfc): give every entry point a help section and a plain summary` |
| 3 | `d2bfa8d09` | `feat(cli): group ai-rfc's commands by what they are for` |
| 4 | — | `docs(ai_rfc): mirror the grouped CLI and record the split` — this file's own commit, so it cannot name its own SHA |

Verified after the last: **1512 unit tests pass**. The 20 failures and 14
collection errors elsewhere in `tests/` are pre-existing and touch nothing this
plan changed — webapp observer API drift (`'WebObserver' object has no
attribute 'update_gui'`), two docker-compose environment tests, and
`pytest_asyncio` missing for `tests/e2e`. mypy is clean on the six changed
modules, pre-commit clean on all sixteen changed files, both doors agree on
exit 1 and exit 3 with a byte-identical `report.json`, and no `prog=` value,
file location or `harness/` path was touched.
