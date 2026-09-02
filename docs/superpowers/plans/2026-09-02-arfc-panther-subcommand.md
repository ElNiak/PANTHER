# `panther ai-rfc` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the eight-command `ai_rfc` substrate one front door, `panther ai-rfc <verb>`, without moving a file or changing any existing invocation.

**Architecture:** A single registry inside the `ai_rfc` package declares the eight commands as dotted strings. A click group in PANTHER's CLI builds one passthrough subcommand per entry, forwarding raw argv to the existing argparse `main()` and exiting on its return code. The conventions test drops its hand-maintained copy of the same list and gains a filesystem check binding the registry to the subpackages actually on disk.

**Tech Stack:** Python 3.10+, click 8.5 (PANTHER's CLI), argparse (the substrate's, unchanged), pytest, mypy.

**Spec:** This document. Sections *Why this shape* and *Verified mechanics* below are the design rationale.

**Status: executed 2026-09-02**, in four commits `e3496b795`, `847a02741`, `3e45f1536`, `305370f28`. See *Corrections found during execution* at the end — the plan as approved contained four wrong expectations and one instruction that would have destroyed tracked files. Anything in this document not amended there was carried out as written.

> **Warning:** `docs/` is wiped by `panther_builder.py clean|package-dev` **and** by `panther docs build`. This file lives there and is tracked; keep it committed.

## Global Constraints

- **Invocation-neutral.** No existing `python -m panther.plugins.services.testers.ai_rfc[.SUB]` string, no `prog=` value, and no file location may change. `harness/experiment/render.py:30,60-92` writes those strings into generated agent skills and the frozen pilot artifacts record them; the pending main run must stay comparable to the pilot.
- **Nothing under `harness/` is touched.** It is a separate git submodule and its strings are the experiment's instrument.
- **New modules inside the `ai_rfc` package must not define `_report` or `_git`.** `test_the_duplication_table_names_every_copy` scans every non-harness `.py` in the package for those names and diffs the result against the README's duplication table.
- Line length 88 (Black), isort import order, Google-style docstrings (Args/Returns/Raises) on public functions, `from __future__ import annotations` as in the surrounding modules.
- Commit format follows the repo: `type(scope): lowercase summary`, no trailing period.

---

## Why this shape

`ai_rfc` is not a PANTHER plugin. It sits in `panther/plugins/services/testers/`
but implements none of that contract — `plugin_discovery.py:338` looks for
`ai_rfc/ai_rfc.py`, does not find it, and debug-logs past. Nothing under
`panther/` outside the package references it, and its entire dependency on the
framework is `from panther import __version__` in eight files. The location is
an accident of history.

Two consequences shape this plan. First, the five-level dotted path buys
nothing, so hiding it behind a front door is pure gain. Second, since nothing
depends on the location, moving the package would also be safe — but it would
rewrite ~135 lines across ~70 files in two repositories and break the
`parents[5]`/`parents[10]` depth arithmetic in two harness conftests, all of
which changes strings the pending main run depends on. Hence: front door now,
relocation deferred.

The root `cli.py` is a leaf, not a root: `prog="ai_rfc"` names the manifest
validator, one of the eight. Its verb here is `adjudicate`, which is the
project's own word for that stage (`pipeline/stages.py:62`).

`pipeline/run.py:1-7` already settles the one doctrinal question. The package's
subpackages hand data over on disk and share no domain code, but `run.py`
reaches five sibling CLIs through `cli.main(argv)` and states why that is
compatible: it "changes how they are invoked and not what they share." A
dispatcher does the same thing and needs no subprocess.

## Verified mechanics

Checked against installed click 8.5.0 and the real files, with real processes.

- `SystemExit` is not among click's five handlers (`click/core.py:1549-1595`)
  and passes through `main.py:215-217` (`except SystemExit as e: return e.code`)
  verbatim. Exit codes 0/1/2/3 all survive.
- **The callback must `sys.exit(...)`, never `return`.** `core.py:1552-1562`
  discards the callback's return value and calls bare `ctx.exit()`, with the
  comment "it's not safe to `ctx.exit(rv)` here!". A `return` silently flattens
  1 and 3 to 0.
- **It must pass `list(args)`, never `None`.** All eight signatures are
  `main(argv=None)`, and `parse_args(None)` re-reads `sys.argv`, which on this
  path begins `["ai-rfc", "<verb>", ...]`.
- `add_help_option=False` plus `ignore_unknown_options=True` forwards `--help`,
  `-h` and `--version` to argparse intact; `Group.allow_interspersed_args=False`
  (`core.py:1680`) stops click consuming anything after the verb.
- `PantherGroup` (`panther/cli/core/base.py:31`) overrides only `format_help`.
- **Registration failure is silent.** `main.py:175-186` collects `ImportError`
  into `missing_commands` but only warns `if ctx`, and `register_commands()`
  runs at import (`main.py:230`) when no context exists. A broken module makes
  `ai-rfc` vanish from `panther --help` with no message. Hence the lazy import
  in Task 3, and the registration assertion in its tests.

## File Structure

| File | Responsibility |
|---|---|
| `…/ai_rfc/entrypoints.py` *(new)* | The one declaration of the eight commands, plus the `CommandModule` Protocol. Holds dotted strings; imports nothing from the package. |
| `panther/cli/commands/ai_rfc.py` *(new)* | The click group. Builds one passthrough per registry entry; owns no knowledge of what the commands do. |
| `panther/cli/core/main.py` *(modify)* | One row in `commands_to_register`. |
| `…/ai_rfc/pipeline/run.py` *(modify)* | Swaps `object` annotations for the Protocol; drops the `type: ignore`. |
| `tests/unit/plugins/…/ai_rfc/test_cli_conventions.py` *(modify)* | Derives from the registry; gains the filesystem-parity check. |
| `tests/unit/test_cli/test_ai_rfc_commands.py` *(new)* | Asserts the click door agrees with the registry and with `python -m`. |
| READMEs + `docs_src/reference/*.md` *(modify)* | Document the new form. |

Known and accepted: the eight commands are enumerated by hand in four places —
the registry, `docs_src/reference/ai_rfc.md:40-47`, `README.md:99-108`, and
partially `pipeline/run.py`. This plan single-sources two of the four. The doc
tables stay hand-maintained.

---

## Task 1: The registry

**Files:**
- Create: `panther/plugins/services/testers/ai_rfc/entrypoints.py`
- Modify: `tests/unit/plugins/services/testers/ai_rfc/test_cli_conventions.py:1-80`

**Interfaces:**
- Consumes: nothing.
- Produces: `ENTRY_POINTS: tuple[EntryPoint, ...]`, `EntryPoint` (frozen dataclass with `.verb`, `.prog`, `.module`, `.summary`, `.load()`), `CommandModule` (Protocol with `main(argv) -> int`), `PACKAGE: str`. Tasks 2 and 3 both import from here.

- [ ] **Step 1: Write the failing test — the registry must match what is on disk**

Add to `tests/unit/plugins/services/testers/ai_rfc/test_cli_conventions.py`, after the existing `TRACKED_HELPERS` block:

```python
def test_every_cli_module_on_disk_is_registered():
    """A sub-package nobody registers is the failure this file exists to stop.

    Single-sourcing the list only removes the second copy; it does not notice a
    ninth sub-package that never reached the first. This counts them, the way
    ``test_the_duplication_table_names_every_copy`` counts helper copies.
    """
    on_disk = {
        PACKAGE + "." + ".".join(path.relative_to(PACKAGE_ROOT).with_suffix("").parts)
        for path in PACKAGE_ROOT.rglob("cli.py")
        if "harness" not in path.relative_to(PACKAGE_ROOT).parts
    }
    assert on_disk == {entry.module for entry in ENTRY_POINTS}
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `pytest tests/unit/plugins/services/testers/ai_rfc/test_cli_conventions.py::test_every_cli_module_on_disk_is_registered -v`

Expected: FAIL with `NameError: name 'PACKAGE' is not defined` (the registry does not exist yet).

- [ ] **Step 3: Create the registry**

Create `panther/plugins/services/testers/ai_rfc/entrypoints.py`:

```python
"""The commands this package exposes, declared once.

Both front doors read this: ``panther ai-rfc`` builds its subcommands from it,
and the conventions suite asserts its invariants across it. Modules are named
by dotted string rather than imported, so reading the registry costs nothing
and the eight argparse CLIs load only when one of them is invoked.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Protocol, cast

#: This package, as a dotted path. Derived rather than written so the registry
#: survives a relocation that the rest of the tree would not.
PACKAGE = __name__.rsplit(".", 1)[0]


class CommandModule(Protocol):
    """A module exposing the substrate's argv-in, exit-code-out contract."""

    def main(self, argv: list[str] | None = ...) -> int:
        """Run the command and return its exit code."""


@dataclass(frozen=True)
class EntryPoint:
    """One command, reachable through either front door.

    Attributes:
        verb: The token following ``panther ai-rfc``.
        prog: The sub-CLI's own ``argparse`` ``prog=``, which ``--version``
            prints. Deliberately not derived from ``verb``: the root validator
            answers to ``adjudicate`` but has always called itself ``ai_rfc``,
            and changing that would alter output the harness records.
        module: Dotted path of the ``cli`` module, not of its package — the
            ``__main__`` guard test derives that name by trimming one segment.
        summary: One line. Shown by ``--help`` and rendered into the generated
            CLI reference by ``mkdocs-click``, where it is the only description
            a reader gets, since the arguments forward untouched.
    """

    verb: str
    prog: str
    module: str
    summary: str

    def load(self) -> CommandModule:
        """Import the module this entry names.

        Returns:
            The command's module, which satisfies :class:`CommandModule`.
        """
        return cast(CommandModule, import_module(self.module))


ENTRY_POINTS: tuple[EntryPoint, ...] = (
    EntryPoint(
        "adjudicate",
        "ai_rfc",
        f"{PACKAGE}.cli",
        "Validate a manifest, adjudicate its claims and verify its anchors",
    ),
    EntryPoint(
        "coverage",
        "ai_rfc.coverage",
        f"{PACKAGE}.coverage.cli",
        "Propose runtime anchors from a coverage report",
    ),
    EntryPoint(
        "draft",
        "ai_rfc.draft",
        f"{PACKAGE}.draft.cli",
        "checkpoint, gate, completeness — freeze and gate a prose draft",
    ),
    EntryPoint(
        "forge",
        "ai_rfc.forge",
        f"{PACKAGE}.forge.cli",
        "fetch, adopt — pull and review evidence, with or without credentials",
    ),
    EntryPoint(
        "history",
        "ai_rfc.history",
        f"{PACKAGE}.history.cli",
        "Extract a commit corpus from a clone",
    ),
    EntryPoint(
        "pipeline",
        "ai_rfc.pipeline",
        f"{PACKAGE}.pipeline.cli",
        "status, substrate, run — drive the deterministic stages",
    ),
    EntryPoint(
        "timeline",
        "ai_rfc.timeline",
        f"{PACKAGE}.timeline.cli",
        "Cluster the corpus into an ordered timeline",
    ),
    EntryPoint(
        "views",
        "ai_rfc.views",
        f"{PACKAGE}.views.cli",
        "Emit per-cluster evidence bundles",
    ),
)
```

- [ ] **Step 4: Point the conventions test at the registry**

In `test_cli_conventions.py`, replace the eight `cli` imports (lines 16-23) with
two — keeping `root_cli`, which `PACKAGE_ROOT` still needs:

```python
from panther import __version__
from panther.plugins.services.testers.ai_rfc import cli as root_cli
from panther.plugins.services.testers.ai_rfc.entrypoints import ENTRY_POINTS, PACKAGE
```

Delete the `#:` comment block and the `ENTRY_POINTS` tuple (lines 27-40)
entirely — the registry now carries both the list and the warning.

Rewrite the three parametrized tests to take an `EntryPoint`. Bodies are
otherwise unchanged:

```python
@pytest.mark.parametrize("entry", ENTRY_POINTS, ids=[e.prog for e in ENTRY_POINTS])
def test_every_entry_point_reports_its_version(entry, capsys):
    """Reproducibility is the stated point, so each command names its build."""
    with pytest.raises(SystemExit) as exit_info:
        entry.load().main(["--version"])
    assert exit_info.value.code == 0
    stdout = capsys.readouterr().out
    assert entry.prog in stdout
    assert __version__ in stdout


@pytest.mark.parametrize("entry", ENTRY_POINTS, ids=[e.prog for e in ENTRY_POINTS])
def test_a_malformed_invocation_exits_two_everywhere(entry):
    """2 belongs to argparse alone; strict findings return 3."""
    with pytest.raises(SystemExit) as exit_info:
        entry.load().main(["--no-such-flag"])
    assert exit_info.value.code == 2


@pytest.mark.parametrize("entry", ENTRY_POINTS, ids=[e.prog for e in ENTRY_POINTS])
def test_importing_an_entry_point_does_not_run_it(entry):
    """``python -m`` must stay the only way these run."""
    name = f"{entry.module.rsplit('.', 1)[0]}.__main__"
    sys.modules.pop(name, None)

    importlib.import_module(name)
```

Keep the original docstring bodies from the file where they are longer than the
one-liners above; only the parametrize decorator and the first line of each
body change.

- [ ] **Step 5: Run the whole conventions suite**

Run: `pytest tests/unit/plugins/services/testers/ai_rfc/test_cli_conventions.py -v`

Expected: PASS — **29** tests (3 parametrized × 8, plus the new filesystem check
and the 4 duplication-table checks). The new test proves the registry names
exactly the eight `cli.py` files on disk. (The approved plan said 27, counting
only two tracked helpers; a concurrent session had grown `TRACKED_HELPERS` to
four during planning.)

- [ ] **Step 6: Prove the new test can fail**

Temporarily add a ninth entry to `ENTRY_POINTS` naming a module that does not
exist, re-run `test_every_cli_module_on_disk_is_registered`, confirm FAIL, then
remove it. A gate never seen red is not known to be a gate.

- [ ] **Step 7: Commit**

```bash
git add panther/plugins/services/testers/ai_rfc/entrypoints.py \
        tests/unit/plugins/services/testers/ai_rfc/test_cli_conventions.py
git commit -m "feat(ai_rfc): declare the eight entry points once, and count them"
```

---

## Task 2: Retire the pipeline's type-ignore

**Files:**
- Modify: `panther/plugins/services/testers/ai_rfc/pipeline/run.py:21-27,48,52,60,76,83,96,152,174`

**Interfaces:**
- Consumes: `CommandModule` from Task 1.
- Produces: nothing new.

`pyproject.toml:335` sets `warn_unused_ignores = true`, so the annotations and
the ignore comment must change in the same step — removing either alone fails
mypy.

- [ ] **Step 1: Confirm the ignore is currently load-bearing**

Run: `mypy --follow-imports=silent panther/plugins/services/testers/ai_rfc/pipeline/run.py`
Expected: `Success` — the ignore is doing real work, so its removal must be paired.

- [ ] **Step 2: Swap the annotations and drop the ignore, together**

Add the import beside the existing relative imports at `run.py:21-27`:

```python
from ..entrypoints import CommandModule
```

Replace `object` with `CommandModule` in all six return annotations (lines 48,
52, 60, 76, 83, 96), each of the form:

```python
def _history(ws: Workspace) -> tuple[list[str], CommandModule]:
```

At line 152:

```python
        module: CommandModule = forge_cli
```

At line 174, delete the trailing comment:

```python
    return StageResult(stage, module.main(argv), tuple(argv))
```

- [ ] **Step 3: Type-check**

Run: `mypy --follow-imports=silent panther/plugins/services/testers/ai_rfc/pipeline/run.py`
Expected: `Success: no issues found`. A failure here means the Protocol does not
match `forge_cli.main`, whose extra defaulted `transport` parameter is the only
signature that differs; widen the Protocol rather than re-adding the ignore.

- [ ] **Step 4: Prove runtime behaviour is unchanged**

Run: `pytest tests/unit/plugins/services/testers/ai_rfc/pipeline/ -v`
Expected: PASS, same count as before the change. Annotations are erased at
runtime; any change here means something else moved.

- [ ] **Step 5: Commit**

```bash
git add panther/plugins/services/testers/ai_rfc/pipeline/run.py
git commit -m "refactor(ai_rfc): type the pipeline's sub-CLI dispatch"
```

---

## Task 3: The `panther ai-rfc` group

**Files:**
- Create: `panther/cli/commands/ai_rfc.py`
- Modify: `panther/cli/core/main.py:162` (insert one row after the `ivy` entry)
- Test: `tests/unit/test_cli/test_ai_rfc_commands.py`

**Interfaces:**
- Consumes: `ENTRY_POINTS`, `EntryPoint` from Task 1.
- Produces: `ai_rfc` (a `click.Group` named `ai-rfc`) for `register_commands`.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_cli/test_ai_rfc_commands.py`:

```python
"""The ``panther ai-rfc`` door onto the ai_rfc substrate.

The eight commands answer to two front doors — ``python -m`` and this group —
and the guarantee worth having is that they cannot disagree. Everything here
derives from the one registry: a command on disk that nobody registered fails
in ``test_cli_conventions``, and a registered command nobody mounted fails here.
"""

import pytest
from click.testing import CliRunner

from panther.cli.commands.ai_rfc import ai_rfc
from panther.cli.core.main import cli
from panther.plugins.services.testers.ai_rfc.entrypoints import ENTRY_POINTS

pytestmark = pytest.mark.unit


def test_the_group_reaches_the_panther_cli():
    """A silent ImportError would delete it from ``panther --help``.

    ``register_commands`` collects an import failure into a warning it prints
    only when a click context exists, and it runs at import time when none
    does. Asserting on the built group is the only thing that notices.
    """
    assert "ai-rfc" in cli.commands


def test_every_registered_command_is_mounted():
    """The drift check the registry exists for, in the click direction."""
    assert set(ai_rfc.commands) == {entry.verb for entry in ENTRY_POINTS}


@pytest.mark.parametrize("entry", ENTRY_POINTS, ids=[e.verb for e in ENTRY_POINTS])
def test_a_malformed_invocation_still_exits_two(entry):
    """argparse owns 2, and click must not relabel it on the way out."""
    result = CliRunner().invoke(ai_rfc, [entry.verb, "--no-such-flag"])
    assert result.exit_code == 2


@pytest.mark.parametrize("entry", ENTRY_POINTS, ids=[e.verb for e in ENTRY_POINTS])
def test_version_passes_through_to_the_sub_cli(entry):
    """The sub-CLI's own prog must survive the forward, not the verb."""
    result = CliRunner().invoke(ai_rfc, [entry.verb, "--version"])
    assert result.exit_code == 0
    assert entry.prog in result.output


@pytest.mark.parametrize("entry", ENTRY_POINTS, ids=[e.verb for e in ENTRY_POINTS])
def test_each_verb_carries_a_description(entry):
    """``mkdocs-click`` renders these; an empty help is a blank reference row."""
    assert ai_rfc.commands[entry.verb].help == entry.summary
```

- [ ] **Step 2: Run them to verify they fail**

Run: `pytest tests/unit/test_cli/test_ai_rfc_commands.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'panther.cli.commands.ai_rfc'`.

- [ ] **Step 3: Write the click group**

Create `panther/cli/commands/ai_rfc.py`:

```python
"""The ai_rfc substrate's commands, mounted under ``panther ai-rfc``.

The substrate is eight argparse CLIs that a human and an agent both drive as
``python -m``. This group is a second door onto the same ``main`` functions: it
forwards argv untouched and exits on whatever the sub-CLI returns, so the two
doors cannot disagree about behaviour or exit codes.

Each sub-CLI is imported inside its callback rather than at module scope.
``register_commands`` swallows an ``ImportError`` here into a warning that is
never printed, because it runs before any click context exists — so a top-level
import would let a broken substrate delete this command from ``panther --help``
in silence. Importing late turns that into an error someone sees.
"""

from __future__ import annotations

import sys

import click

from panther.plugins.services.testers.ai_rfc.entrypoints import (
    ENTRY_POINTS,
    EntryPoint,
)


@click.group(name="ai-rfc")
def ai_rfc() -> None:
    """Reconstruct an RFC-style specification from a project's own history.

    Every subcommand forwards its arguments unchanged to the matching
    ``python -m panther.plugins.services.testers.ai_rfc`` entry point, which
    remains supported and is what the agent harness invokes.
    """


def _passthrough(entry: EntryPoint) -> click.Command:
    """Build the click command that forwards to one entry point.

    Args:
        entry: The registry entry to wrap.

    Returns:
        A click command named for ``entry.verb``, taking every argument
        uninterpreted.
    """

    @click.command(
        name=entry.verb,
        help=entry.summary,
        short_help=entry.summary,
        context_settings={"ignore_unknown_options": True},
        add_help_option=False,
    )
    @click.argument("args", nargs=-1, type=click.UNPROCESSED)
    def command(args: tuple[str, ...]) -> None:
        sys.exit(entry.load().main(list(args)))

    return command


for _entry in ENTRY_POINTS:
    ai_rfc.add_command(_passthrough(_entry))
```

Two lines are load-bearing and easy to "simplify" wrongly. `sys.exit(...)`
rather than `return`: click discards a callback's return value and exits 0,
which would flatten every exit 1 and 3 into success. And `list(args)` rather
than `None`: `parse_args(None)` re-reads `sys.argv`, which here begins with the
verb.

- [ ] **Step 4: Register it**

In `panther/cli/core/main.py`, insert one row into `commands_to_register`
immediately after the `ivy` entry at line 162, keeping the two
tester-adjacent commands together:

```python
        ("ivy", "panther.cli.commands.ivy", "ivy"),
        ("ai-rfc", "panther.cli.commands.ai_rfc", "ai_rfc"),
```

- [ ] **Step 5: Run the tests**

Run: `pytest tests/unit/test_cli/test_ai_rfc_commands.py -v`
Expected: PASS — **26** tests (3 parametrized × 8, plus 2 unparametrized). The
approved plan said 34, miscounting three parametrized tests as four. Confirm
with `--collect-only` rather than trusting the total: a test that fails to
collect is exactly the failure this task exists to prevent.

- [ ] **Step 6: Verify parity against the real shell, both doors**

Run each pair and compare. Use `.venv/bin/…` directly rather than `source
…/activate`, which a worktree-isolated session refuses.

| Probe | Both doors must give |
|---|---|
| `panther --help \| grep ai-rfc` | the command, with its summary |
| `… adjudicate --no-such-flag` | 2 |
| `… adjudicate --version` | 0, and identical `ai_rfc <version>` output |
| `… adjudicate /nonexistent.yaml --out DIR` | 1 |
| `… adjudicate OVERSTATED.yaml --out DIR --strict` | 3 |

**The last two are the only ones that test anything.** argparse *raises*
`SystemExit` for both `--version` and a bad flag, so those codes propagate even
if the callback wrongly used `return`. Only a code that `main()` **returns** —
1 for an unreadable manifest, 3 for a strict finding — can catch that bug. The
approved plan checked only 2 and 0, and so would have asserted the `sys.exit`
rule without ever testing it.

For the exit-3 probe, a manifest with `status: confirmed` and no `anchors:` at
all is unambiguously overstated; the schema is in
`tests/unit/plugins/services/testers/ai_rfc/conftest.py`.

If `grep` finds nothing, the module failed to import and `register_commands`
swallowed it — run `python -c "import panther.cli.commands.ai_rfc"` to see the
real error.

- [ ] **Step 7: Confirm invocation-neutrality**

Run: `pytest tests/unit/plugins/services/testers/ai_rfc/ -n auto`
Expected: PASS, unchanged count. Nothing in this task touches the substrate.

- [ ] **Step 8: Commit**

```bash
git add panther/cli/commands/ai_rfc.py panther/cli/core/main.py \
        tests/unit/test_cli/test_ai_rfc_commands.py
git commit -m "feat(cli): reach the ai_rfc substrate as panther ai-rfc"
```

---

## Task 4: Documentation

**Files:**
- Modify: `panther/plugins/services/testers/ai_rfc/README.md:99-108,113,156,249-252`
- Modify: `panther/plugins/services/testers/ai_rfc/history/README.md:15,39,71`
- Modify: `docs_src/reference/ai_rfc.md:40-47`
- Modify: `docs_src/reference/cli.md:5-11`

**Interfaces:** none.

**A path qualifies for rewriting only when it follows `python -m`.** The same
dotted path also appears in Python `import` statements inside ```python fences;
those are library API examples and must be left alone. In particular
`history/README.md:89` is `from …ai_rfc.history.index import open_index` — do
not touch it.

- [ ] **Step 1: Rewrite the shell invocations**

The transformation is mechanical: `python -m panther.plugins.services.testers.ai_rfc`
becomes `panther ai-rfc adjudicate`, and `python -m …ai_rfc.<sub>` becomes
`panther ai-rfc <sub>`. Purpose columns and surrounding prose are unchanged.
Two of the ten `README.md` table rows, as worked examples:

```
| `panther ai-rfc forge fetch URL --repo CLONE --out DIR [--host github\|gitlab]` | Fetch pull data into an immutable snapshot (the only networked command); a token is optional and the snapshot records the fidelity it reached |
| `panther ai-rfc draft gate DRAFTREPO --timeline DIR --checkpoints DIR --questions FILE --revisions FILE --out DIR [--strict]` | Citation gate; findings exit 3 under `--strict` |
```

The eight rows of `docs_src/reference/ai_rfc.md:40-47` change from module names
to verbs the same way: `` `ai_rfc.pipeline` `` becomes `` `panther ai-rfc
pipeline` ``, and the first row's `` `ai_rfc` `` becomes `` `panther ai-rfc
adjudicate` ``. **Leave lines 5 and 79 alone** — they cite the package's
filesystem location, which this change does not alter.

- [ ] **Step 2: Add the compatibility note, once**

In `.../ai_rfc/README.md`, under the `## CLI` heading at line 110:

```markdown
Every command is also reachable as
`python -m panther.plugins.services.testers.ai_rfc[.SUB]`, unchanged. That form
remains supported and is what the agent harness invokes, so a rendered skill or
a frozen experiment artifact will always show it rather than the short form.
```

- [ ] **Step 3: Rewrite the `cli.md` note's substance, not its paths**

`docs_src/reference/cli.md:5-11` currently claims ai_rfc "has no console
script", that its entry points are reached only as `python -m …`, and that
"nothing below covers them". The second and third become false: `ai-rfc` is
registered, and the `::: mkdocs-click` directive on line 13 renders it. Replace
the admonition with:

```markdown
!!! note "The `ai-rfc` subcommands forward their arguments"

    The `ai_rfc` substrate, which reconstructs a requirement specification from
    an existing implementation's history, is deliberately not registered as a
    plugin type — it is reached as `panther ai-rfc <verb>`. Its eight
    subcommands below are passthroughs onto standalone `argparse` commands, so
    their arguments are not described here; see
    [ai_rfc (reconstructed specs)](ai_rfc.md) for each one's options.
```

- [ ] **Step 4: Check the claims**

```bash
grep -rn "python -m panther.plugins.services.testers.ai_rfc" \
  panther/plugins/services/testers/ai_rfc/README.md \
  panther/plugins/services/testers/ai_rfc/history/README.md \
  docs_src/reference/
```

Expected: only the deliberate compatibility notes. Any other hit is a shell
invocation that was missed. (The Python import at `history/README.md:89` uses
`from …`, so this pattern does not match it; confirm it separately by eye.)

**Do NOT run `panther docs build`.** `panther/cli/commands/docs.py:82-84`
unconditionally `shutil.rmtree`s `docs/` before copying `docs_src/` into it, and
`docs/` holds ten tracked files — every plan under `docs/superpowers/plans/` and
the research notes. It is a generated staging directory that also contains
committed work. Verify the `mkdocs-click` rendering instead through
`panther ai-rfc --help`, which shows each verb with its summary, and through
`test_each_verb_carries_a_description`, which asserts
`command.help == entry.summary` for all eight. Same hazard as
`panther_builder.py package-dev|clean`.

- [ ] **Step 5: Commit**

```bash
git add panther/plugins/services/testers/ai_rfc/README.md \
        panther/plugins/services/testers/ai_rfc/history/README.md \
        docs_src/reference/ai_rfc.md docs_src/reference/cli.md
git commit -m "docs(ai_rfc): document the panther ai-rfc front door"
```

---

## Final verification

```bash
source .venv/bin/activate
pre-commit run --files $(git diff --name-only HEAD~4)
pytest tests/ -n auto -m unit          # report the pass/fail count
mypy panther/plugins/services/testers/ai_rfc/ panther/cli/commands/ai_rfc.py
```

No reinstall is needed: the registration table is Python in `main.py`, not a
`[project.scripts]` entry, and the install is editable. If `panther --help`
omits `ai-rfc`, treat it as the silent-`ImportError` symptom rather than a
packaging one.

## Known cosmetic gaps

Accepted, not defects. `panther ai-rfc adjudicate --version` prints
`ai_rfc <version>` rather than `adjudicate`, because the prog strings may not
change. Bare `panther ai-rfc` prints group help and exits **2**, since
`Group.no_args_is_help` raises a `UsageError` — the same shape as bare
`panther`. `panther --debug ai-rfc …` echoes a banner to **stdout**
(`main.py:49-50`) before the sub-CLI's output. An uncaught exception yields the
same exit code by either route but a shorter stderr through click.

One real parity divergence: click consumes `--` before forwarding
(`click/parser.py:333-334`), so `panther ai-rfc adjudicate -- -weird.yaml`
reaches argparse as `['-weird.yaml']` and errors, where `python -m` would treat
it as the manifest. It affects only paths beginning with a hyphen. Closing it
means re-inserting the separator on the click side, which is redesign rather
than plumbing.

## Corrections found during execution

Recorded because every one of them was invisible until the step was actually
run, and a future reader would otherwise rediscover them.

**One instruction would have destroyed tracked work.** Task 4 Step 4 said to run
`panther docs build`. `panther/cli/commands/docs.py:82-84` unconditionally
`shutil.rmtree`s `docs/` before repopulating it from `docs_src/`, and `docs/`
holds ten tracked files — including this plan and every other under
`docs/superpowers/plans/`. Not run; the step is amended above.

**Two expected test counts were wrong.** Task 1 said 27, actually 29: a
concurrent session grew `TRACKED_HELPERS` from two helpers to four *while the
plan was being written*, so it was already stale at approval. Task 3 said 34,
actually 26 — three parametrized tests miscounted as four. Both were confirmed
by collection rather than assumed.

**The mypy invocation was incomplete.** Both Task 2 steps needed
`--follow-imports=silent`. Without it mypy follows imports and reports ~1100
pre-existing errors across 108 files, which buries the one file under test.

**The parity verification tested nothing.** See Task 3 Step 6 above: exits 2 and
0 both arrive as argparse-raised `SystemExit` and survive a wrongly-written
`return`. Exit 1 and exit 3 were added, and both agree across the two doors.

**Two tool frictions worth knowing.** A worktree-isolated session refuses
compound shell (`source …/activate`, heredoc piped into another command), so use
`.venv/bin/…` directly and the dedicated edit tools. And the sandbox blocks an
SSL keylog write during pytest collection, so test runs need it disabled.

**Two lint surprises.** Pyright rejects a docstring-only Protocol body, so
`CommandModule.main` carries an explicit `...`. Ruff's D403 rejects a docstring
opening with a lowercase word, which blocked one commit over a sentence starting
"argparse" — its suggested fix, capitalising a module name, would have been
wrong; rephrase instead. Note also that a bare `flake8` reports false E501s here
because it defaults to 79 columns, while pre-commit runs it at 88 — and that
flake8 is `stages: [manual]`, so it never runs at commit time.

**Pre-existing debt left alone.** `panther/cli/core/main.py` has an unused `e`
binding in its `except AttributeError` handler, present in HEAD before this work
and merely shifted a line by the new registration row. Fixing it would bundle an
unrelated change into a commit.

## Deferred, and why

Each changes strings the rendered agent skills record, so each is blocked on
the main experiment run completing.

1. **Make the module root a dispatcher.** `python -m …ai_rfc <verb>`, with the
   validator moving to `validate/`. This is what would make the two doors
   identical rather than merely parallel.
2. **Re-render the agent skills onto `panther ai-rfc`.** Needs an upstream
   change in the harness submodule plus a pointer bump, and breaks
   comparability with the pilot.
3. **Extract `ai_rfc` as its own project.** The strongest structural finding:
   the substrate needs nothing from PANTHER but a version string, and the
   repository actually named `ai_rfc` is nested inside it. Costs ~135 lines
   across ~70 files in two repositories — one more after this change, since
   `panther/cli/commands/ai_rfc.py` hard-codes the registry's dotted path —
   plus rewriting the `parents[5]`/`parents[10]` conftest arithmetic into a
   marker-file search, and the two filesystem-path citations at
   `docs_src/reference/ai_rfc.md:5,79` that Task 4 deliberately leaves alone.
