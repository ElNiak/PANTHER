# ai_rfc Extraction and Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the ai_rfc substrate, MCP server, plugin and experiment driver into one installable `ai-rfc` distribution in the existing `ai_rfc` repository, consumed by PANTHER as a single submodule, with every one of the 769 tests green and the substrate's outputs byte-identical.

**Architecture:** The substrate (55 files under `panther/plugins/services/testers/ai_rfc/`) moves into the repository that today is its `harness` submodule (github.com/ElNiak/ai_rfc), becoming the top-level package `ai_rfc`; the MCP server becomes `ai_rfc.server`, the experiment driver `ai_rfc.experiment`. A root `pyproject.toml` installs it editable; an interim dispatcher `ai-rfc <verb>` replaces the `python -m panther.plugins.services.testers.ai_rfc[.SUB]` door; `PANTHER_REPO` and every `sys.path` insertion retire because the substrate is an installed package. PANTHER deletes the substrate files, re-points the submodule one level up, and keeps `panther ai-rfc` as a passthrough onto the installed tool.

**Tech Stack:** Python 3.10, setuptools, argparse, pytest 8 + pytest-xdist (`--import-mode=importlib`), mypy, black, flake8, git submodules, rsync/perl for the mechanical move.

**Spec:** Part A of this file, which Task 0 commits as `docs/superpowers/specs/2026-09-02-ai-rfc-extraction-and-flow-design.md` in PANTHER. Part A is the design and decision register from the 2026-09-02 brainstorm; Part B is this plan (sub-project SP1 of the roadmap in Part A).

**Execution (decided 2026-09-02):** subagent-driven, after SP0's plan has been executed the same way. One fresh implementer per task, a reviewer between tasks, and every spawn prompt carries the Global Constraints' path definitions verbatim (`PANTHER`, `AIRFC`, `PY`, `G`), because a worker sees only its own task. Tasks 3, 7 and 8 stop at their confirmation points regardless of who executes them.

## Global Constraints

- **Paths.** `PANTHER` = `/Users/elniak/Documents/Documents/Work/Project/Protocol-Testing-Security/PANTHER/master/.claude/worktrees/iut-ai-rfc` (worktree, branch `feat/arfc-pipeline-and-runtime-anchors`). `AIRFC` = `$PANTHER/panther/plugins/services/testers/ai_rfc/harness` until Task 7 moves it to `$PANTHER/panther/plugins/services/testers/ai_rfc`. `PY` = `$PANTHER/.venv/bin/python`; there is no other venv. `G` = `$PANTHER/reconstructions/_baselines/extraction-2026-09-02` (goldens; gitignored).
- **Two repositories move under you.** Another session (`iut-ai-rfc-a7`) commits to this worktree. Run `git log -1 --format='%h %ad %s' --date=format:'%H:%M:%S'` and `git status --short` in **both** `$PANTHER` and `$AIRFC` before every task; a moved HEAD is concurrent work, so re-anchor every line number in this plan by symbol before editing at it. Expected at approval: PANTHER `b0184fec4`, ai_rfc `26e522a`, both trees clean.
- **Stage by explicit path.** Never `git add -A` or `git add .` in either repository; the harness checkout has held a peer's uncommitted work before. Commit format `type(scope): lowercase summary`, no trailing period. No `--no-verify`; a pre-commit failure is fixed and re-staged.
- **The pilot campaign is read-only evidence forever.** `~/arfc-experiments/campaigns/pilot-aioquic-w02-11-20260831/` froze `plugin_root` and `git`; nothing matches them after Task 5, and `audit`/`analyze` already fabricate violations against it (review C-5). Never run those verbs against it.
- **Never run `panther docs build` or `panther_builder.py clean|package-dev`** in `$PANTHER`: both `shutil.rmtree` the tracked `docs/` directory (`panther/cli/commands/docs.py:84`). Files under `docs/` are gitignored but tracked, so they need `git add -f`.
- **Sandbox.** `pytest` needs the sandbox off (an SSL keylog write at collection); so do nested-git and submodule operations (Task 7), `pip install`, and `git push`. Prefix every `pytest` and `python -m` invocation with `SSLKEYLOGFILE=`. `mypy` needs `--follow-imports=silent`; `flake8` needs `--max-line-length=88`; `ruff` exists only as a pre-commit hook.
- **No backward-compatibility shims.** `python -m panther.plugins.services.testers.ai_rfc`, `PANTHER_REPO`, `ai_rfc_server` and `prog="ai_rfc.<sub>"` retire cleanly; nothing forwards from an old name. The one deliberate exception is the parity CLI's console script `ai_rfc`, which is the AI+CLI arm's surface and is folded into `ai-rfc` by SP3, not by this plan.
- **Byte identity is the oracle.** The three goldens Task 0 captures must reproduce byte-for-byte after every task that can touch them (Tasks 1, 3, 7). Capture and replay from `$PANTHER` with the same relative paths: `pipeline status --json` prints `args.workspace` as typed.
- Line length 88, Google-style docstrings on public functions, `from __future__ import annotations` as in the surrounding modules, comments only where the *why* is non-obvious.
- **Confirmation points:** the first `pip install` into `.venv` (Task 3), the submodule re-pointing (Task 7), and every `git push` (Task 8). Stop and ask before each.

---

# Part A — Design (becomes the spec)

## Context

`ai_rfc` reconstructs an RFC-style specification from a repository's own history and gates every claim against evidence. It is 18,443 lines across two repositories: the PANTHER-side substrate (`panther/plugins/services/testers/ai_rfc/`, 6.9k LOC, eight argparse programs behind a `panther ai-rfc` click door) and the `harness` git submodule (11.5k LOC: the Claude Code plugin, an MCP server with a parity CLI, and an experiment driver built around campaigns, arms and audits). A pilot experiment completed on 2026-08-31; a whole-codebase review on 2026-09-02 (`docs/research/2026-09-02-ai-rfc-code-review.md`) found six Criticals, and a five-task provenance-fix plan (`docs/superpowers/plans/2026-09-02-arfc-provenance-fix.md`) awaits execution.

Two things prompted the brainstorm. Every structural improvement was parked behind "after the main experiment run" because the invocation strings were the pilot's instrument. And the operator experience is fragmented: two front doors, eight programs with two path conventions, a production sweep phrased as `campaign init --arms A --repeats 1`, and five surfaces that each compute "how far along is this reconstruction" on their own. The user settled nine decisions; the headline is that **the main run is not planned any more, so nothing is frozen.**

## Decision register

Decisions D1 to D28 from `docs/superpowers/specs/2026-08-25-arfc-progressive-rfc-design.md` and `docs/superpowers/specs/2026-08-26-arfc-phase-c-experiment-harness-design.md` stay in force except where a row below amends one.

### Decided with the user on 2026-09-02

| # | Decision | Consequence |
|---|---|---|
| D29 | The preregistered main experiment run is **not planned any more**. | No invocation string, verb, `prog` or MCP tool name is frozen. The four items deferred in `2026-09-02-arfc-panther-subcommand.md` (dispatcher root, skills onto `panther ai-rfc`, extraction, harness rename) and the six harness-side items deferred in the provenance plan (three Criticals: C-1's narrow end, C-5, C-6; plus the `READ_TOOLS` rename, S-7 and server-13) are unblocked. |
| D30 | **Extract** the substrate into the existing `ai_rfc` repository (today the `harness` submodule); PANTHER consumes it as **one submodule** at `panther/plugins/services/testers/ai_rfc`, installed editable by the builder like `panther_ivy`. | One repo holds substrate + server + driver + plugin + docs + all tests. Ends the two-repo drift the review named first, the five-level dotted path, and the non-plugin under `plugins/`. Amends D17 (nesting direction reverses). |
| D31 | **Carve a production driver** out of the harness; arms, audit, metrics, parity and the Bash guard become an optional `ai_rfc.experiment` subpackage. | The operator gets `reconstruct`; the instrument stays tested and off the operator's path. |
| D32 | The **operator running a reconstruction end-to-end** is the primary persona; the agent loop is the inner loop; adopters read the docs. | CLI and docs are designed from the operator's flow; MCP/skills second. |
| D33 | The CLI is **config-file driven, PANTHER-style**: `ai-rfc run --config recon.yaml`. | Rejected: workspace-centric verbs; flat verbs with `--workspace`. |
| D34 | The YAML **declares** the reconstruction; **lifecycle verbs take `--config`**; **acquisition (clone + forge) is the one networked phase.** | Amends D1's "network only in forge" to "network only in acquisition". Rejected: fully declarative reconcile; YAML for the batch part only. |
| D35 | **One per-cluster ledger derived from artifacts**, read by `status`, `completeness`, the MCP `status`/`cluster_next`, the sweep's next-cluster rule and the slash command. | Fixes the false `done`, the missing cluster id, and bare directories counted as processed. Rejected: a recorded ledger file. |
| D36 | **Docs site in the extracted repo**, generated where possible, READMEs as source pages. | Reference generated from the argparse root, the config validator and the tool registry; decision and debt registers as pages. |
| D37 | **Sequencing:** provenance fixes first in PANTHER (SP0, the existing plan unchanged), then extraction (SP1, this plan), then everything else on the new layout. | |

### Recommended, not asked — flip any at approval

| # | Recommendation | Alternatives considered |
|---|---|---|
| R1 | One **argparse root** (SP3) with subparsers; each `_parser()` becomes `configure(parser)`; exit codes 0/1/2/3 and `--json` uniform. | click; typer. |
| R2 | One console script **`ai-rfc`**; the parity CLI's 16 verbs fold into the same tree in SP3 (coinciding verbs become one verb; agent-only ones under `ai-rfc claim|cluster|corpus`). One core, two frontends preserved. | Two scripts. |
| R3 | Config validation by a **declarative field table** rendering both validation and the reference page; stdlib + PyYAML only. | Pydantic/OmegaConf. |
| R4 | Hand-tuning options live **in the YAML under per-stage sections**, plus `run --stage <name>` and `verify`; the explicit-path leaf programs retire in SP3. | Keep the leaf programs as an escape hatch. |
| R5 | The **workspace is the state**; sweep sessions log under `<workspace>/runs/<timestamp>/`. | `outputs/<date>/<id>/` per invocation. |
| R6 | Keep **`panther ai-rfc`** as a thin passthrough onto the installed tool. | Remove it. |
| R7 | Extraction is a **plain move commit** citing the PANTHER SHA range. | `git filter-repo --subdirectory-filter` to carry the 125 substrate commits; optional. |
| R8 | Retire **`PANTHER_REPO`**; the server takes `AI_RFC_WORKSPACE` now and `AI_RFC_CONFIG` once a config exists (SP3). | Keep both. |
| R9 | Add **`ai-rfc doctor`** (SP3). | Fold into `status`. |
| R10 | The plugin **requires the installed `ai-rfc` distribution** (`.mcp.json` runs `python3 -m ai_rfc.server`). A marketplace install copies only the plugin directory (verified in `~/.claude/plugins/cache/`), and today's server already needed a PANTHER checkout on `sys.path`, so the plugin was never self-sufficient. | Keep the server source inside the plugin directory via `package-dir`; buys nothing since the substrate is still needed. |
| R11 | Consolidate the registered duplicate helpers when the argparse root lands (SP3). | Keep the register forever. |

## Findings the roadmap rests on

- **Two doors, eight programs.** `entrypoints.py:71-131`; `panther/cli/commands/ai_rfc.py:67-105`; `panther/cli/core/main.py:163`. Leaf help prints `usage: ai_rfc.pipeline`; `pipeline run --from/--until` choices are alphabetical.
- **Linear stage model over a cyclic loop.** `pipeline/state.py:198-209` grades mining `done` on any claim, `:237-244` prose `done` on `revisions.yaml` existing; MARK shows `checkpoint partial 2 of 69` and `next: checkpoint` with no cluster id (`pipeline/cli.py:142`); a bare `pipeline run` there raises `checkpoint needs --cluster` (`run.py:125-127`) and exits 1 (`cli.py:254-256`).
- **Five readers of progress:** `pipeline status`, `draft completeness`, the server's `queries.py`, `experiment/per_cluster.py` + `metrics.cluster_artifacts`, the `/ai-rfc-status` command.
- **No command writes the question register**; only the server's `core/questions.py` does. **Path conventions split**: eleven verbs take every path, two take a workspace root; `forge --out` names a cache root while downstream `--forge` wants the snapshot subdirectory.
- **Extraction blast radius (measured):** 219 lines in 79 files reference the dotted path in PANTHER's tree; 8 files import `from panther import __version__` (exactly the eight CLI modules; `report.py` is not among them) and nothing else from PANTHER; the harness reaches the substrate through lazy imports in `ai_rfc_server/core/{claims,revisions,queries,draft,questions}.py`, `testing.py`, `experiment/metrics.py:165`, `workspace.py:129-133`, plus `gates.py:19` (`_A_RFC`), `arms.py:25` (`RAW_PREFIX`), `render.py:30` and the `_RAW` table; the server front-loads `PANTHER_REPO` on `sys.path` (`paths.py:68-69`) and three more places do the same (`workspace.py:127`, `metrics.py:52`, `preflight.py:245`); two conftests derive the PANTHER root by depth (`experiment/tests/conftest.py:16`, `server/tests/conftest.py:7`).
- **Packaging today:** `.gitmodules` points the `harness` submodule at github.com/ElNiak/ai_rfc; `panther_builder.py:163-176` installs `panther_ivy` editable; the server is its own distribution (`ai-rfc-server`, script `ai_rfc`) reached by `.mcp.json` through a `sys.path` insertion; `experiment/` is a package but the harness root is not, so `python -m experiment` only works from that directory.
- **Baseline (review, 2026-09-02):** 390 / 339 / 40 = 769 tests; PANTHER-side black and flake8 clean; `types-PyYAML` undeclared.

## Roadmap

| # | Sub-project | Goal | Gate |
|---|---|---|---|
| SP0 | Provenance fixes | Execute `docs/superpowers/plans/2026-09-02-arfc-provenance-fix.md` unchanged. | > 390 passing; `pipeline run WS --strict` exits 3 on an overstated manifest. |
| SP1 | Extraction + packaging | **This plan.** | 769 green in the new repo; goldens byte-identical; PANTHER suite delta explained. |
| SP2 | Production driver + instrument split | `ai-rfc reconstruct --config` over `per_cluster.run_per_cluster`; arms/audit/metrics/parity/guard under `ai_rfc.experiment`; the six deferred harness items. | A two-cluster MARK sweep completes and resumes after a kill. |
| SP3 | Config-driven CLI | `recon.yaml`, argparse root, lifecycle verbs, `doctor`, parity CLI folded in, helper consolidation, `AI_RFC_CONFIG`. | Every verb reachable through `--config`. |
| SP4 | Ledger + status | `ai_rfc/ledger.py`; one reader for all five surfaces. | A drift test across the five surfaces on MARK. |
| SP5 | Docs site | mkdocs in the `ai_rfc` repo with generated reference and both registers. | Site builds from a clean clone. |
| SP6 | PANTHER side | Builder, `docs build` wipe, pointer pages. | `panther docs build` no longer destroys tracked work. |

---

# Part B — SP1 tasks

## File Structure

Target layout of the `ai_rfc` repository after Task 6:

```
pyproject.toml                       distribution ai-rfc; scripts ai-rfc, ai_rfc
ai_rfc/
├── __init__.py                      __version__ + the manifest-core re-exports
├── __main__.py  cli.py              the dispatcher: ai-rfc <verb> [args]
├── entrypoints.py                   the registry (check now names ai_rfc.check.cli)
├── models.py schema.py promotion.py anchors.py report.py README.md
├── check/{__init__,__main__,cli}.py the manifest validator (was the package-root cli.py)
├── history/ forge/ timeline/ views/ draft/ coverage/ pipeline/
├── server/                          was plugins/ai-rfc/server/src/ai_rfc_server
│   └── __init__.py __main__.py cli.py server.py tools.py paths.py testing.py core/
└── experiment/                      was experiment/ (prompts/, guard.py travel with it)
plugins/ai-rfc/                      the Claude Code plugin (.mcp.json, skills/, commands/)
docs/                                experiment-protocol.md parity.md spike-s0.md experiments/
tests/substrate/  tests/server/  tests/experiment/
README.md
```

Responsibilities that change: `ai_rfc/cli.py` is the door (interim; SP3's argparse root replaces it); `ai_rfc/server/paths.py` resolves only the workspace; `ai_rfc/experiment/{arms,config,runner,preflight,workspace,metrics,cli}.py` lose every `sys.path` insertion and every `PANTHER_REPO` export; `panther/cli/commands/ai_rfc.py` becomes a passthrough onto `ai_rfc.cli.main`.

Rewrite rules used by several tasks, always followed by a grep that must return nothing:

| Rule | perl expression |
|---|---|
| dotted path | `s/panther\.plugins\.services\.testers\.ai_rfc/ai_rfc/g` |
| version import | `s/from panther import __version__/from ai_rfc import __version__/g` |
| server package | `s/\bai_rfc_server\b/ai_rfc.server/g` |
| experiment package | `s/\bfrom experiment(\.|\s)/from ai_rfc.experiment$1/g` |

---

### Task 0: Durable spec, plan, goldens and baselines

**Files:**
- Create: `$PANTHER/docs/superpowers/specs/2026-09-02-ai-rfc-extraction-and-flow-design.md` (Part A of this file, verbatim)
- Create: `$PANTHER/docs/superpowers/plans/2026-09-02-ai-rfc-extraction.md` (this file, verbatim)
- Create: `$G/` (goldens; gitignored under `reconstructions/`)

**Interfaces:**
- Produces: the goldens `mark-status.txt`, `mark-status.json`, `aioquic-status.txt`, `mark-check/report.json`, `mark-verify.exit`, and `baseline-tests.txt`, which Tasks 1, 3 and 7 diff against.

- [ ] **Step 1: Confirm both trees are where the plan expects**

```bash
git -C "$PANTHER" log -1 --format='%h %ad %s' --date=format:'%H:%M:%S'; git -C "$PANTHER" status --short
git -C "$AIRFC" log -1 --format='%h %ad %s' --date=format:'%H:%M:%S'; git -C "$AIRFC" status --short
git -C "$AIRFC" remote get-url origin
```

Expected: SP0 lands first (D37), so PANTHER's HEAD is the last of the provenance plan's five commits on top of `b0184fec4`, and the ai_rfc HEAD is `26e522a`; both trees clean; remote `https://github.com/ElNiak/ai_rfc.git`. Those five commits are expected, not concurrent work: they touch `promotion.py`, `schema.py`, `pipeline/cli.py`, `draft/checkpoint.py`, `forge/fetch.py`, `coverage/propose.py`, `coverage/cli.py` and their tests, none of which this plan cites by line. Any other new commit is concurrent work: read it before continuing and re-anchor line numbers by symbol.

- [ ] **Step 2: Write the spec and the plan into the repository**

Copy Part A of this file to the spec path and this whole file to the plan path (no edits). Then:

```bash
cd "$PANTHER"
git add -f docs/superpowers/specs/2026-09-02-ai-rfc-extraction-and-flow-design.md docs/superpowers/plans/2026-09-02-ai-rfc-extraction.md
git commit -m "docs(ai_rfc): record the extraction and flow design and its first plan"
```

- [ ] **Step 3: Capture the goldens**

From `$PANTHER`, with the relative paths exactly as written (the JSON echoes them):

```bash
G=reconstructions/_baselines/extraction-2026-09-02; mkdir -p "$G"
SSLKEYLOGFILE= .venv/bin/python -m panther.plugins.services.testers.ai_rfc.pipeline status reconstructions/mark > "$G/mark-status.txt"
SSLKEYLOGFILE= .venv/bin/python -m panther.plugins.services.testers.ai_rfc.pipeline status reconstructions/mark --json > "$G/mark-status.json"
SSLKEYLOGFILE= .venv/bin/python -m panther.plugins.services.testers.ai_rfc.pipeline status reconstructions/aioquic > "$G/aioquic-status.txt"
SSLKEYLOGFILE= .venv/bin/python -m panther.plugins.services.testers.ai_rfc reconstructions/mark/manifest.yaml --out "$G/mark-check" --repo reconstructions/mark/clone; echo $? > "$G/mark-check.exit"
SSLKEYLOGFILE= .venv/bin/python -m panther.plugins.services.testers.ai_rfc.views reconstructions/mark/timeline --corpus reconstructions/mark/corpus --repo reconstructions/mark/clone --out reconstructions/mark/clusters --forge reconstructions/mark/forge/gitlab.cylab.be__cylab__mark/snapshot-2026-09-01T09-35-27Z --only c0049-pr-ba8ca432c304 --verify; echo $? > "$G/mark-verify.exit"
```

Expected: `mark-check.exit` holds `0`; `mark-verify.exit` holds `0`. If verify exits 3, the views were emitted with different flags: retry once without `--forge`, and record which form reproduced in `$G/NOTES.md`. Never re-emit the views.

- [ ] **Step 4: Record the test baselines**

```bash
cd "$PANTHER"; SSLKEYLOGFILE= .venv/bin/pytest tests/unit/plugins/services/testers/ai_rfc/ tests/unit/test_cli/test_ai_rfc_commands.py -n auto -q 2>&1 | tail -1 | tee "$G/baseline-tests.txt"
SSLKEYLOGFILE= .venv/bin/pytest tests/ -n auto -m unit -q 2>&1 | tail -1 | tee -a "$G/baseline-tests.txt"
cd "$AIRFC"; SSLKEYLOGFILE= "$PY" -m pytest experiment/tests -q 2>&1 | tail -1 | tee -a "$G/baseline-tests.txt"
cd "$AIRFC/plugins/ai-rfc/server"; SSLKEYLOGFILE= "$PY" -m pytest tests -q 2>&1 | tail -1 | tee -a "$G/baseline-tests.txt"
```

Expected: the first line reports the post-SP0 substrate count (390 plus the roughly nine tests the provenance plan adds), the third 339, the fourth 40; the second (the whole PANTHER unit suite) is recorded as measured, with its known 20 failures and 14 collection errors outside ai_rfc. Every later gate compares against this file, not against a number remembered from a plan.

---

### Task 1: Move the substrate and its tests into the ai_rfc repository

**Files:**
- Create: `$AIRFC/ai_rfc/` (the 55 substrate files, copied), `$AIRFC/ai_rfc/check/__init__.py`, `$AIRFC/ai_rfc/check/__main__.py`
- Modify: `$AIRFC/ai_rfc/__init__.py` (version), `$AIRFC/ai_rfc/entrypoints.py:82-86` (the `check` entry)
- Delete: `$AIRFC/ai_rfc/__main__.py` (the old root door; Task 3 recreates it for the dispatcher)
- Create: `$AIRFC/tests/substrate/` (the PANTHER test tree, copied)
- Modify: `$AIRFC/tests/substrate/test_cli_conventions.py:15-17,61`

**Interfaces:**
- Consumes: nothing.
- Produces: the importable top-level package `ai_rfc` with `ai_rfc.__version__ == "0.1.0"`, the registry entry `EntryPoint("check", "ai_rfc", "ai_rfc.check.cli", ...)`, and `python -m ai_rfc.<sub>` for the seven subpackages plus `python -m ai_rfc.check`.

- [ ] **Step 1: Copy the substrate and its tests**

```bash
rsync -a --exclude harness --exclude .mypy_cache --exclude __pycache__ "$PANTHER/panther/plugins/services/testers/ai_rfc/" "$AIRFC/ai_rfc/"
mkdir -p "$AIRFC/tests/substrate"
rsync -a --exclude __pycache__ --exclude tests "$PANTHER/tests/unit/plugins/services/testers/ai_rfc/" "$AIRFC/tests/substrate/"
ls "$AIRFC/ai_rfc" "$AIRFC/tests/substrate"
```

Expected: `ai_rfc/` holds `README.md`, the seven subpackage directories, `cli.py`, `entrypoints.py`, `models.py`, `schema.py`, `anchors.py`, `promotion.py`, `report.py`, `__init__.py`, `__main__.py`; `tests/substrate/` holds `conftest.py`, `test_*.py` and the subpackage test directories. The excluded `tests/` under the PANTHER test tree held only an untracked `pytest.log`.

- [ ] **Step 2: Turn the root validator into the `check` subpackage**

```bash
cd "$AIRFC"
mkdir ai_rfc/check
mv ai_rfc/cli.py ai_rfc/check/cli.py
rm ai_rfc/__main__.py
```

Create `ai_rfc/check/__init__.py`:

```python
"""The manifest validator: schema, promotion rule, anchor verification."""
```

Create `ai_rfc/check/__main__.py`:

```python
"""``python -m ai_rfc.check``."""

import sys

from . import cli

if __name__ == "__main__":
    sys.exit(cli.main())
```

- [ ] **Step 3: Rewrite the imports**

```bash
cd "$AIRFC"
grep -rl "panther" ai_rfc tests/substrate --include='*.py' --include='*.md' \
  | xargs perl -pi -e 's/panther\.plugins\.services\.testers\.ai_rfc/ai_rfc/g; s/from panther import __version__/from ai_rfc import __version__/g'
grep -rn "import panther\|from panther\|panther\.plugins" ai_rfc tests/substrate --include='*.py'
```

Expected: the final grep prints nothing. (Prose mentions of PANTHER in docstrings and READMEs remain and are fine.)

- [ ] **Step 4: Give the package its own version**

In `ai_rfc/__init__.py`, after the module docstring and before `from .anchors import ...`, insert:

```python
__version__ = "0.1.0"
```

Every `cli.py` now imports `from ai_rfc import __version__`; the relative imports below it never import a `cli` module, so there is no cycle.

- [ ] **Step 5: Point the registry at the moved validator**

In `ai_rfc/entrypoints.py`, the `check` entry (lines 80-87) becomes:

```python
    EntryPoint(
        "check",
        "ai_rfc",
        f"{PACKAGE}.check.cli",
        "Report which manifest claims are not backed by the code their "
        "anchors point at",
        BY_HAND,
    ),
```

`PACKAGE` derives from `__name__` and is now `ai_rfc`, so every other entry's `f"{PACKAGE}.<sub>.cli"` already resolves.

- [ ] **Step 6: Fix the conventions test's two root assumptions**

In `tests/substrate/test_cli_conventions.py`, replace lines 15-17:

```python
from ai_rfc import __version__
from ai_rfc.entrypoints import ENTRY_POINTS, PACKAGE
import ai_rfc
```

and line 61:

```python
PACKAGE_ROOT = Path(ai_rfc.__file__).parent
```

(The old line imported the package-root `cli` module, which no longer exists.) Reorder the three imports to satisfy isort: `import ai_rfc` first, then the two `from` lines.

The same file's `test_the_duplication_table_names_every_copy[_report]` compares every `def _report(` on disk against the README's register, and that register names the root file. In `ai_rfc/README.md`, in the "Known duplication to consolidate" table, the `stderr `_report`` row (line 478 today) lists `` `cli.py` `` first; change that one cell to `` `check/cli.py` ``. No other row names the root file.

- [ ] **Step 7: Run the substrate suite in its new home**

```bash
cd "$AIRFC"; SSLKEYLOGFILE= "$PY" -m pytest --import-mode=importlib -p no:cacheprovider tests/substrate -q 2>&1 | tail -3
```

Expected: the count recorded in `$G/baseline-tests.txt` line 1 (390) passes, zero failures. `python -m pytest` puts `$AIRFC` on `sys.path`, which is what makes `import ai_rfc` resolve before Task 3 installs anything. The `unit` marker is unregistered here until Task 3, so warnings are expected; failures are not.

- [ ] **Step 8: Prove the outputs did not move**

```bash
cd "$PANTHER"
PYTHONPATH="$AIRFC" SSLKEYLOGFILE= .venv/bin/python -m ai_rfc.pipeline status reconstructions/mark | diff - "$G/mark-status.txt" && echo "status identical"
PYTHONPATH="$AIRFC" SSLKEYLOGFILE= .venv/bin/python -m ai_rfc.check reconstructions/mark/manifest.yaml --out "$G/mark-check-task1" --repo reconstructions/mark/clone; echo "exit=$?"
diff "$G/mark-check/report.json" "$G/mark-check-task1/report.json" && echo "report identical"
```

Expected: both `identical` lines print and the exit matches `$G/mark-check.exit`.

- [ ] **Step 9: Commit the move, citing where it came from**

```bash
cd "$AIRFC"
FIRST=$(git -C "$PANTHER" log --format=%h --reverse -- panther/plugins/services/testers/a_rfc panther/plugins/services/testers/ai_rfc | head -1)
LAST=$(git -C "$PANTHER" log -1 --format=%h)
git add ai_rfc tests/substrate
git commit -m "feat: move the substrate in from PANTHER $FIRST..$LAST"
```

Expected: `FIRST` is `09172cfdf` (2026-07-28, the first claim-model commit) unless history was rewritten.

---

### Task 2: Remove the dead aggregates module

**Files:**
- Modify: `$AIRFC/ai_rfc/history/__init__.py:7` and its `__all__`
- Modify: `$AIRFC/ai_rfc/history/README.md` (any paragraph naming `history_shape`)
- Delete: `$AIRFC/ai_rfc/history/aggregates.py`, `$AIRFC/tests/substrate/history/test_aggregates.py`

**Interfaces:**
- Consumes: the moved tree from Task 1.
- Produces: `ai_rfc.history` without `HistoryShape` and `history_shape`.

- [ ] **Step 1: Confirm nothing but the re-export and the test names it**

```bash
cd "$AIRFC"; grep -rn "aggregates\|history_shape\|HistoryShape" ai_rfc tests plugins docs
```

Expected: hits only in `ai_rfc/history/__init__.py`, `ai_rfc/history/aggregates.py`, `tests/substrate/history/test_aggregates.py`, and possibly `ai_rfc/history/README.md`. Any other hit is a production caller the review missed: stop and report it instead of deleting.

- [ ] **Step 2: Remove the module, its re-export and its test**

```bash
cd "$AIRFC"; git rm -q ai_rfc/history/aggregates.py tests/substrate/history/test_aggregates.py
```

In `ai_rfc/history/__init__.py` delete the line `from .aggregates import HistoryShape, history_shape` and the `"HistoryShape"` and `"history_shape"` entries from `__all__`. In `ai_rfc/history/README.md` delete any paragraph or table row describing `history_shape`; if the README does not mention it, leave the file alone.

- [ ] **Step 3: Verify and commit**

```bash
cd "$AIRFC"
grep -rn "aggregates\|history_shape\|HistoryShape" ai_rfc tests plugins docs; echo "grep exit=$? (1 means clean)"
SSLKEYLOGFILE= "$PY" -m pytest --import-mode=importlib -p no:cacheprovider tests/substrate/history -q 2>&1 | tail -1
git add ai_rfc/history/__init__.py ai_rfc/history/README.md
git commit -m "refactor: drop the aggregates module nothing calls"
```

Expected: the grep finds nothing; the history suite passes with exactly the aggregates tests fewer than before.

---

### Task 3: Package the distribution and add the dispatcher door

**Files:**
- Create: `$AIRFC/pyproject.toml`, `$AIRFC/ai_rfc/cli.py`, `$AIRFC/ai_rfc/__main__.py`
- Modify: `$AIRFC/.gitignore`, `$AIRFC/ai_rfc/entrypoints.py:32-38,71-131` (`prog` values and docstring), the eight `cli.py` modules (`prog=` and `version=` strings)
- Modify: `$AIRFC/tests/substrate/test_cli_conventions.py:138-143`
- Test: `$AIRFC/tests/substrate/test_root_cli.py` (new)

**Interfaces:**
- Consumes: `ENTRY_POINTS`, `__version__`.
- Produces: `ai_rfc.cli.main(argv: list[str] | None = None) -> int` (the door Task 7's PANTHER passthrough calls), the console script `ai-rfc`, registry `prog` values of the form `ai-rfc <verb>`, and the pytest configuration (`--import-mode=importlib`, the `unit` marker) every later task's test run relies on.

- [ ] **Step 1: Write the failing dispatcher tests**

Create `tests/substrate/test_root_cli.py`:

```python
"""The one door: ``ai-rfc <verb>`` forwards to the registered sub-CLI."""

import re

import pytest

from ai_rfc import __version__, cli
from ai_rfc.entrypoints import ENTRY_POINTS

pytestmark = pytest.mark.unit


def test_help_lists_every_verb_in_registration_order(capsys):
    """Registration order is the workflow order; the listing must keep it.

    The needle is "exactly two spaces then a word": the second usage line is
    indented deeper, and a bare ``startswith("  ")`` would capture it.
    """
    assert cli.main(["--help"]) == 0
    out = capsys.readouterr().out
    rendered = [
        line.split()[0] for line in out.splitlines() if re.match(r"^ {2}\S", line)
    ]
    assert rendered == [entry.verb for entry in ENTRY_POINTS]


def test_a_bare_invocation_is_a_usage_error(capsys):
    """Like ``panther``: usage printed, exit 2, because nothing was asked."""
    assert cli.main([]) == 2
    assert "usage: ai-rfc" in capsys.readouterr().err


def test_an_unknown_verb_exits_two(capsys):
    assert cli.main(["frobnicate"]) == 2
    assert "unknown verb" in capsys.readouterr().err


def test_version_names_the_door(capsys):
    assert cli.main(["--version"]) == 0
    assert capsys.readouterr().out == f"ai-rfc {__version__}\n"


@pytest.mark.parametrize("entry", ENTRY_POINTS, ids=[e.verb for e in ENTRY_POINTS])
def test_a_verb_forwards_its_arguments_untouched(entry):
    """argparse owns 2 for a malformed invocation, and the door must not relabel it."""
    with pytest.raises(SystemExit) as exit_info:
        cli.main([entry.verb, "--no-such-flag"])
    assert exit_info.value.code == 2


def test_a_sub_cli_return_code_passes_through(tmp_path):
    """1 is *returned* by ``check`` for an unreadable manifest, never raised, so
    a door that dropped the return value would report success here."""
    missing = tmp_path / "missing.yaml"
    assert cli.main(["check", str(missing), "--out", str(tmp_path / "out")]) == 1
```

- [ ] **Step 2: Run them to verify they fail**

```bash
cd "$AIRFC"; SSLKEYLOGFILE= "$PY" -m pytest --import-mode=importlib -p no:cacheprovider tests/substrate/test_root_cli.py -q 2>&1 | tail -3
```

Expected: collection error `ImportError: cannot import name 'cli' from 'ai_rfc'`.

- [ ] **Step 3: Write the dispatcher**

Create `ai_rfc/cli.py`:

```python
"""The one door onto the tool: ``ai-rfc <verb> [args]``.

Every verb forwards its arguments untouched to the sub-CLI the registry names
and returns whatever that sub-CLI returns, so this door and
``python -m ai_rfc.<sub>`` cannot disagree about behaviour or exit codes.

Interim by design: the argparse root that SP3 builds replaces this module and
retires the leaf programs. It exists so the extraction ships one working door
without redesigning the verbs.
"""

from __future__ import annotations

import sys

from . import __version__
from .entrypoints import ENTRY_POINTS

PROG = "ai-rfc"
_BY_VERB = {entry.verb: entry for entry in ENTRY_POINTS}


def _usage() -> str:
    width = max(len(entry.verb) for entry in ENTRY_POINTS)
    lines = [f"usage: {PROG} <verb> [args]", f"       {PROG} --help | --version", ""]
    section = None
    for entry in ENTRY_POINTS:
        if entry.section != section:
            section = entry.section
            lines.append(f"{section}:")
        lines.append(f"  {entry.verb:<{width}}  {entry.summary}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Dispatch to one registered command.

    Args:
        argv: Argument vector without the program name; ``None`` reads
            ``sys.argv[1:]``.

    Returns:
        The sub-CLI's exit code; 0 for ``--help`` and ``--version``; 2 for a
        missing or unknown verb, which is a malformed invocation and so shares
        argparse's code.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        sys.stderr.write(_usage())
        return 2
    if args[0] in ("-h", "--help"):
        sys.stdout.write(_usage())
        return 0
    if args[0] == "--version":
        print(f"{PROG} {__version__}")
        return 0
    entry = _BY_VERB.get(args[0])
    if entry is None:
        sys.stderr.write(f"{PROG}: unknown verb {args[0]!r}\n" + _usage())
        return 2
    return entry.load().main(args[1:])
```

Create `ai_rfc/__main__.py`:

```python
"""``python -m ai_rfc <verb>`` — the same door as the ``ai-rfc`` script."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Name every leaf after the door**

The registry's `prog` is what `--version` prints and what the conventions test asserts, and each leaf hard-codes the same string twice (`prog=` and `version=f"..."`). Rewrite both mechanically:

```bash
cd "$AIRFC"
perl -pi -e 's/prog="ai_rfc\.(\w+)"/prog="ai-rfc $1"/g; s/version=f"ai_rfc\.(\w+) \{__version__\}"/version=f"ai-rfc $1 {__version__}"/g' ai_rfc/*/cli.py
perl -pi -e 's/prog="ai_rfc"/prog="ai-rfc check"/; s/version=f"ai_rfc \{__version__\}"/version=f"ai-rfc check {__version__}"/' ai_rfc/check/cli.py
perl -pi -e 's/"ai_rfc\.(\w+)",/"ai-rfc $1",/g; s/^        "ai_rfc",$/        "ai-rfc check",/' ai_rfc/entrypoints.py
grep -n 'prog=\|version=f' ai_rfc/*/cli.py ai_rfc/entrypoints.py | grep -v 'ai-rfc'
```

Expected: the last grep prints nothing. In `entrypoints.py` replace the `prog` attribute docstring (the paragraph beginning "Deliberately not derived from ``verb``") with:

```
        prog: The sub-CLI's own ``argparse`` ``prog=``, which ``--version``
            prints and which the leaf's usage line shows. Always
            ``ai-rfc <verb>``, so a usage line names the command the user
            typed; kept as data rather than derived so the conventions suite
            can assert the two agree.
```

- [ ] **Step 5: Exclude the door from the registry glob**

`test_every_cli_module_on_disk_is_registered` globs every `cli.py`; the dispatcher is the door, not a verb. In `tests/substrate/test_cli_conventions.py` replace lines 138-142:

```python
    on_disk = {
        PACKAGE + "." + ".".join(path.relative_to(PACKAGE_ROOT).with_suffix("").parts)
        for path in PACKAGE_ROOT.rglob("cli.py")
        # The package-root cli.py is the door that dispatches to these, not one
        # of them; the door has its own test module.
        if path != PACKAGE_ROOT / "cli.py"
    }
```

- [ ] **Step 6: Write the packaging**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "ai-rfc"
version = "0.1.0"
description = "Reconstruct an RFC-style specification from a repository's own history, and gate every claim against its evidence"
requires-python = ">=3.10"
dependencies = ["PyYAML>=6.0,<7.0"]

[project.optional-dependencies]
# Upper-bounded deliberately: the server is written against the v1 API, and
# mcp 2.x renamed FastMCP to MCPServer. Without the bound a fresh install
# resolves to 2.x, the server dies at import, and Claude Code mounts no tools —
# which does not fail the session, it just removes every write and gate tool
# from it. See the 2026-09-02 run that spent $5.90 mining 39 claims in an
# invented vocabulary because nothing was there to validate them.
mcp = ["mcp>=1.0,<2"]
tests = ["pytest>=8", "pytest-xdist"]
dev = ["types-PyYAML", "mypy", "black", "flake8"]

[project.scripts]
ai-rfc = "ai_rfc.cli:main"

[tool.setuptools.packages.find]
include = ["ai_rfc*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--import-mode=importlib"
markers = ["unit: fast, no external dependency"]
```

Append to `.gitignore`:

```
.mypy_cache/
```

- [ ] **Step 7: Install it editable — confirmation point**

Ask before this step; it changes `.venv`. Sandbox off.

```bash
cd "$AIRFC"; "$PY" -m pip install -e '.[mcp,tests,dev]' 2>&1 | tail -2
"$PANTHER/.venv/bin/ai-rfc" --help | head -4
"$PANTHER/.venv/bin/ai-rfc" check --version
```

Expected: `usage: ai-rfc <verb> [args]` then the three section headings; `ai-rfc check 0.1.0`.

- [ ] **Step 8: Run the substrate suite through the installed package**

```bash
cd "$AIRFC"; SSLKEYLOGFILE= "$PY" -m pytest tests/substrate -q 2>&1 | tail -2
```

Expected: the Task 2 count plus the six dispatcher tests (one of them parametrised eight ways, so plus 13 collected), zero failures, no unknown-marker warning.

- [ ] **Step 9: Types and goldens**

```bash
cd "$AIRFC"; "$PANTHER/.venv/bin/mypy" --follow-imports=silent ai_rfc 2>&1 | tail -1
cd "$PANTHER"
SSLKEYLOGFILE= .venv/bin/ai-rfc pipeline status reconstructions/mark | diff - "$G/mark-status.txt" && echo "status identical"
SSLKEYLOGFILE= .venv/bin/ai-rfc pipeline status reconstructions/mark --json | diff - "$G/mark-status.json" && echo "json identical"
SSLKEYLOGFILE= .venv/bin/ai-rfc check reconstructions/mark/manifest.yaml --out "$G/mark-check-task3" --repo reconstructions/mark/clone; diff "$G/mark-check/report.json" "$G/mark-check-task3/report.json" && echo "report identical"
```

Expected: mypy reports at most 2 errors (the eight YAML-stub errors vanish once `types-PyYAML` is installed; the remaining two are `coverage/cli.py:109`'s missing annotation and one `Returning Any`); all three `identical` lines print.

- [ ] **Step 10: Commit**

```bash
cd "$AIRFC"
git add pyproject.toml .gitignore ai_rfc/cli.py ai_rfc/__main__.py ai_rfc/entrypoints.py ai_rfc/check/cli.py ai_rfc/*/cli.py tests/substrate/test_root_cli.py tests/substrate/test_cli_conventions.py
git commit -m "feat: package ai-rfc and open one door onto its verbs"
```

---

### Task 4: Fold the MCP server into `ai_rfc.server`

**Files:**
- Move: `plugins/ai-rfc/server/src/ai_rfc_server/` → `ai_rfc/server/`; `plugins/ai-rfc/server/tests/` → `tests/server/`
- Delete: `plugins/ai-rfc/server/pyproject.toml` (and the untracked `src/ai_rfc_server.egg-info`)
- Create: `ai_rfc/server/__main__.py`
- Modify: `ai_rfc/server/paths.py` (whole file), `ai_rfc/server/core/gates.py:1-31,86`, `ai_rfc/server/cli.py:40-43`, `tests/server/conftest.py` (whole file), `tests/substrate/test_cli_conventions.py:70-77,138-143`, `pyproject.toml` (`[project.scripts]`)
- Test: `tests/server/test_paths.py` (new)

**Interfaces:**
- Consumes: the installed package from Task 3 (the gate subprocesses run `python -m ai_rfc.check` from the workspace directory, which only resolves because the package is installed).
- Produces: `ai_rfc.server.paths.Context(workspace: Path)` with `manifest`/`questions`/`revisions` properties; `ai_rfc.server.paths.resolve_context() -> Context` reading `AI_RFC_WORKSPACE` alone; `python -m ai_rfc.server` (the MCP server) and the console script `ai_rfc` (the parity CLI). Task 5 rewrites the experiment package against these names.

- [ ] **Step 1: Move the files**

```bash
cd "$AIRFC"
git mv plugins/ai-rfc/server/src/ai_rfc_server ai_rfc/server
git mv plugins/ai-rfc/server/tests tests/server
git rm -q plugins/ai-rfc/server/pyproject.toml
rm -rf plugins/ai-rfc/server
grep -rl "ai_rfc_server\|panther" ai_rfc/server tests/server --include='*.py' \
  | xargs perl -pi -e 's/\bai_rfc_server\b/ai_rfc.server/g; s/panther\.plugins\.services\.testers\.ai_rfc/ai_rfc/g'
grep -rn "ai_rfc_server\|panther\.plugins" ai_rfc/server tests/server
```

Expected: `plugins/ai-rfc/server` no longer exists; the final grep prints nothing.

Two tests derive paths by depth from their old location. `tests/server/test_parity.py:86` opens `docs/parity.md` through `Path(__file__).resolve().parents[4]`; from `tests/server/` the repository root is `parents[2]`, so change that literal. Then:

```bash
cd "$AIRFC"; grep -n "parents\[\|SERVER_ROOT\|PANTHER_ROOT" tests/server/*.py
```

Expected: only `test_parity.py`'s corrected `parents[2]`; `SERVER_ROOT` and `PANTHER_ROOT` are deleted with the conftest in Step 6, so any other hit must be rewritten to `Path(__file__).resolve().parents[2]` now.

- [ ] **Step 2: Write the failing contract test**

Create `tests/server/test_paths.py`:

```python
"""The environment contract is one variable: the workspace."""

import pytest

from ai_rfc.server.paths import EnvError, resolve_context


def test_the_contract_needs_only_the_workspace(tmp_path, monkeypatch):
    """The substrate is an installed package, so no checkout is located."""
    monkeypatch.delenv("PANTHER_REPO", raising=False)
    monkeypatch.setenv("AI_RFC_WORKSPACE", str(tmp_path))
    assert resolve_context().workspace == tmp_path.resolve()


def test_a_missing_workspace_is_refused(monkeypatch):
    monkeypatch.delenv("AI_RFC_WORKSPACE", raising=False)
    with pytest.raises(EnvError):
        resolve_context()


def test_a_workspace_that_is_not_a_directory_is_refused(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_RFC_WORKSPACE", str(tmp_path / "absent"))
    with pytest.raises(EnvError):
        resolve_context()
```

- [ ] **Step 3: Run it to verify the first test fails**

```bash
cd "$AIRFC"; SSLKEYLOGFILE= "$PY" -m pytest tests/server/test_paths.py -q 2>&1 | tail -3
```

Expected: `test_the_contract_needs_only_the_workspace` FAILS with `EnvError: PANTHER_REPO and AI_RFC_WORKSPACE must both be set`; the other two pass already.

- [ ] **Step 4: Rewrite `paths.py`**

Replace `ai_rfc/server/paths.py` entirely:

```python
"""Resolve the one environment handle everything here depends on.

``AI_RFC_WORKSPACE`` names one reconstruction workspace. It is required;
nothing guesses, because a tool quietly operating on the wrong workspace is
the kind of failure that looks like success. The substrate is an installed
package, so no checkout has to be located or placed on ``sys.path``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class EnvError(RuntimeError):
    """Raised when the environment contract is not met."""


@dataclass(frozen=True)
class Context:
    """The resolved handle every core operation receives."""

    workspace: Path

    @property
    def manifest(self) -> Path:
        """The workspace manifest."""
        return self.workspace / "manifest.yaml"

    @property
    def questions(self) -> Path:
        """The workspace question register."""
        return self.workspace / "questions.yaml"

    @property
    def revisions(self) -> Path:
        """The workspace revision map."""
        return self.workspace / "revisions.yaml"


def resolve_context() -> Context:
    """Read and validate the environment contract.

    Returns:
        The resolved context.

    Raises:
        EnvError: If ``AI_RFC_WORKSPACE`` is missing or does not name a
            directory.
    """
    workspace = os.environ.get("AI_RFC_WORKSPACE")
    if not workspace:
        raise EnvError(
            "AI_RFC_WORKSPACE must be set; refusing to guess which workspace "
            "to operate on"
        )
    workspace_path = Path(workspace).resolve()
    if not workspace_path.is_dir():
        raise EnvError(f"AI_RFC_WORKSPACE={workspace_path} is not a directory")
    return Context(workspace=workspace_path)
```

- [ ] **Step 5: Run the substrate from the workspace, not from a checkout**

In `ai_rfc/server/core/gates.py`: line 19 becomes `_A_RFC = "ai_rfc"`; in `_run`, `cwd=ctx.panther_repo,` becomes `cwd=ctx.workspace,`; in `manifest_gate`, `code, stderr = _run(ctx, _A_RFC, *args)` becomes `code, stderr = _run(ctx, f"{_A_RFC}.check", *args)`. Replace the module docstring's second paragraph ("These shell out ... with ``cwd`` at the PANTHER checkout") with:

```
These shell out to the substrate CLIs — the same commands the AI+CLI arm
types — with ``cwd`` at the workspace, and never reinterpret an exit code:
3 from a strict gate is information, not an obstacle. The substrate leaves 2
to argparse, so a 2 here means the invocation was malformed, which is a
defect in the caller rather than a finding about the manifest.
```

In `ai_rfc/server/cli.py` lines 40-43 the description becomes:

```python
        description="Drive a reconstruction workspace (AI_RFC_WORKSPACE).",
```

Then find every remaining reference to the retired field:

```bash
cd "$AIRFC"; grep -rn "panther_repo\|PANTHER_REPO" ai_rfc/server tests/server
```

Expected: nothing.

- [ ] **Step 6: Rewrite the server test conftest and add the server entry point**

Replace `tests/server/conftest.py` entirely:

```python
from pathlib import Path

import pytest

from ai_rfc.server.testing import build_workspace


@pytest.fixture
def make_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """A workspace factory plus an env switcher, for twin-workspace tests."""

    def build(name: str) -> Path:
        return build_workspace(tmp_path / name)

    def use(root: Path) -> None:
        monkeypatch.setenv("AI_RFC_WORKSPACE", str(root))

    return build, use


@pytest.fixture
def workspace(make_workspace):
    build, use = make_workspace
    root = build("ws")
    use(root)

    from ai_rfc.server.paths import resolve_context

    return resolve_context()
```

Create `ai_rfc/server/__main__.py`:

```python
"""``python -m ai_rfc.server`` — the stdio MCP server."""

from .server import main

if __name__ == "__main__":
    main()
```

Add the parity CLI's script to `pyproject.toml` under `[project.scripts]`:

```toml
# The AI+CLI arm's parity frontend keeps its name until SP3 folds it into ai-rfc.
ai_rfc = "ai_rfc.server.cli:main"
```

and reinstall so the script exists: `cd "$AIRFC"; "$PY" -m pip install -e '.[mcp,tests,dev]' 2>&1 | tail -1`.

- [ ] **Step 7: Keep the conventions suite honest about the new subpackage**

`ai_rfc/server/cli.py` defines its own `_report`, which the duplication-table scan would now count. In `tests/substrate/test_cli_conventions.py` replace `_package_sources` (lines 70-77):

```python
def _package_sources() -> list[Path]:
    """Every module the table speaks for: the substrate, minus the frontends.

    ``server`` and ``experiment`` are separate programs that share no helper
    with the substrate; their own ``_report`` copies are not what the register
    tracks.
    """
    return [
        path
        for path in sorted(PACKAGE_ROOT.rglob("*.py"))
        if not {"server", "experiment", "__pycache__"}
        & set(path.relative_to(PACKAGE_ROOT).parts)
    ]
```

(Relative parts, as the registry test already does: an absolute path's parts include every ancestor directory, and a checkout living under a directory called `experiment` would otherwise exclude everything.)

and in `test_every_cli_module_on_disk_is_registered` extend the comprehension's condition:

```python
        if path != PACKAGE_ROOT / "cli.py"
        and not {"server", "experiment"} & set(path.relative_to(PACKAGE_ROOT).parts)
```

- [ ] **Step 8: Run the server and substrate suites**

```bash
cd "$AIRFC"; SSLKEYLOGFILE= "$PY" -m pytest tests/server tests/substrate -q 2>&1 | tail -2
SSLKEYLOGFILE= "$PY" -c "import ai_rfc.server.server as s; print(len(s.ALL_TOOLS))"
"$PANTHER/.venv/bin/ai_rfc" --help | head -1
```

Expected: 40 + 3 new server tests and the substrate count, zero failures; `16`; `usage: ai_rfc`. The experiment suite is expected to be broken until Task 5 (its conftest inserts a `server/src` path that no longer exists); do not run it here.

- [ ] **Step 9: Commit**

```bash
cd "$AIRFC"
git add ai_rfc/server tests/server pyproject.toml tests/substrate/test_cli_conventions.py
git commit -m "refactor: make the MCP server the ai_rfc.server package"
```

---

### Task 5: Fold the experiment package into `ai_rfc.experiment`

**Files:**
- Move: `experiment/` → `ai_rfc/experiment/` (with `prompts/`, `guard.py`); then `ai_rfc/experiment/tests/` → `tests/experiment/` (with `fixtures/`, `fake_claude/`)
- Modify: `ai_rfc/experiment/arms.py:142-161`, `config.py:31-33,132-135,282-287`, `runner.py:97-109,140-152`, `metrics.py:52,130-136,164-165`, `workspace.py:124-135,211-225,462-505`, `preflight.py:107-124,220-260,575-594`, `cli.py:101-128,152-183 (the preflight --panther-repo argument),392-403,448`, `render.py:27-33,59-63,68-72,73-77,91-97,119-122,132-135`, `prompts/loop.tmpl.md` (the preconditions line)
- Modify: `tests/experiment/conftest.py:1-43`, `tests/experiment/test_render.py:37-44`, `tests/experiment/test_enforcement.py:16`, `tests/experiment/test_stream.py:23`, `tests/experiment/test_workspace.py:102,121,128`, `tests/experiment/test_preflight.py` (calls passing `panther_repo=`), `tests/experiment/test_arms.py` (calls to `mcp_config`)
- Modify: `pyproject.toml` (`package-data`), `plugins/ai-rfc/skills/ai-rfc-reconstruction-loop/SKILL.md` (regenerated)

**Interfaces:**
- Consumes: `ai_rfc.server.paths.Context(workspace=...)`, `ai_rfc.server.testing.build_workspace`, `ai_rfc.server.core.gates`, `python -m ai_rfc.server`, the dispatcher `python -m ai_rfc <verb>`.
- Produces: `ai_rfc.experiment.arms.mcp_config(*, python: str, workspace: Path) -> dict`; `ai_rfc.experiment.workspace.preseed(workspace: Path, ordinals: Iterable[int]) -> list[str]`; `ai_rfc.experiment.preflight.build_invocations(*, root, plugin_dir, workspace, claude_bin, model)`, `prepare_scratch(*, root, python)`, `run_preflight(*, root, plugin_dir, claude_bin, model, timeout_s)`; `RAW_PREFIX == "python -m ai_rfc"`; `python -m ai_rfc.experiment <command>` from any directory.

- [ ] **Step 1: Move and rewrite mechanically**

```bash
cd "$AIRFC"
git mv experiment ai_rfc/experiment
git mv ai_rfc/experiment/tests tests/experiment
grep -rl "experiment\|ai_rfc_server\|panther" ai_rfc/experiment tests/experiment --include='*.py' --include='*.md' --include='*.jsonl' --include='claude' \
  | xargs perl -pi -e 's/\bfrom experiment(\.|\s)/from ai_rfc.experiment$1/g; s/\bai_rfc_server\b/ai_rfc.server/g; s/panther\.plugins\.services\.testers\.ai_rfc/ai_rfc/g'
grep -rn "^import experiment\b" ai_rfc/experiment tests/experiment
```

Expected: the last grep lists any test that used `import experiment` for attribute access; change each such line to `from ai_rfc import experiment` (keeps `experiment.X` working). Then:

```bash
grep -rn "ai_rfc_server\|panther\.plugins\|^from experiment\|^import experiment" ai_rfc/experiment tests/experiment
```

Expected: nothing.

- [ ] **Step 2: Write the failing tests for the new contracts**

`tests/experiment/test_arms.py` already tests `mcp_config` (the test whose assertions sit at lines 186-196 today: `server["args"][0] == "-c"` and an env holding `PANTHER_REPO`). Rewrite that test's call and assertions to:

```python
    config = mcp_config(python="/venv/bin/python", workspace=tmp_path / "ws")
    server = config["mcpServers"]["ai_rfc"]
    assert server["command"] == "/venv/bin/python"
    assert server["args"] == ["-m", "ai_rfc.server"]
    assert server["env"] == {"AI_RFC_WORKSPACE": str(tmp_path / "ws")}
```

and delete the file's `from .conftest import PANTHER_ROOT` import (line 19) and the two `sys.path` lines that use it (lines 35-36).

Append to `tests/experiment/test_render.py`:

```python
def test_the_raw_arm_uses_the_dispatcher():
    """Arm C's family is ``python -m ai_rfc``; every raw command must start there."""
    c = render_loop("C")
    assert "python -m ai_rfc check " in c
    assert "python -m ai_rfc draft checkpoint " in c
    assert "python -m ai_rfc draft gate " in c
    assert "python -m ai_rfc.draft" not in c and "python -m ai_rfc $" not in c
```

- [ ] **Step 3: Run them to verify they fail**

```bash
cd "$AIRFC"; SSLKEYLOGFILE= "$PY" -m pytest tests/experiment/test_arms.py::test_the_mcp_config_launches_the_installed_server tests/experiment/test_render.py::test_the_raw_arm_uses_the_dispatcher -q 2>&1 | tail -3
```

Expected: both FAIL (`mcp_config` rejects the missing keyword arguments; the rendering still says `python -m ai_rfc $AI_RFC_WORKSPACE/manifest.yaml`). If collection itself fails on the conftest, do Step 4 first and re-run.

- [ ] **Step 4: Rewrite the test conftest and the two guard paths**

Replace lines 1-22 of `tests/experiment/conftest.py` with:

```python
"""Fixtures shared by the experiment tests.

The package is installed, so nothing here touches ``sys.path``; the paths are
derived from this file's location only to reach the plugin directory and the
fake ``claude``.
"""

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FAKE_CLAUDE = Path(__file__).parent / "fake_claude" / "claude"
```

Replace the `panther_repo`, `plugin_root` and `fixture_workspace` fixtures (lines 24-43) with:

```python
@pytest.fixture
def panther_repo() -> Path:
    """A git repository the campaign record can ``git describe``.

    The name survives from when this located the substrate; it now only feeds
    the record and the ``reconstructions/`` lookup, and SP2 retires it.
    """
    assert (REPO_ROOT / ".git").exists(), REPO_ROOT
    return REPO_ROOT


@pytest.fixture
def plugin_root() -> Path:
    return REPO_ROOT / "plugins" / "ai-rfc"


@pytest.fixture
def fixture_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """One complete fixture workspace with the env contract pointing at it."""
    from ai_rfc.server.testing import build_workspace

    root = build_workspace(tmp_path / "ws")
    monkeypatch.setenv("AI_RFC_WORKSPACE", str(root))
    return root
```

In `tests/experiment/test_enforcement.py:16` and `tests/experiment/test_stream.py:23`, `GUARD = Path(__file__).resolve().parents[1] / "guard.py"` becomes:

```python
GUARD = Path(__file__).resolve().parents[2] / "ai_rfc" / "experiment" / "guard.py"
```

The retired variable and the deleted conftest names appear in five more places; every one is listed here so none is found by a red suite:

```bash
cd "$AIRFC"; grep -rn "PANTHER_ROOT\|HARNESS_ROOT\|SERVER_SRC\|PANTHER_REPO" tests/experiment
```

- `tests/experiment/test_runner.py:52` — remove `"PANTHER_REPO",` from the expected key set of `env.json` (six keys remain).
- `tests/experiment/test_fake_claude.py:22` — delete the `"PANTHER_REPO": str(panther_repo),` entry from the env it builds.
- `tests/experiment/test_preflight.py:71-72` — the two assertions on `plugin_mcp_env`/`plugin_mcp_noenv` now read `assert by_name["plugin_mcp_env"].env["AI_RFC_WORKSPACE"] == str(<the workspace the test passed to build_invocations>)` and `assert "AI_RFC_WORKSPACE" not in by_name["plugin_mcp_noenv"].env`.
- `tests/experiment/fake_claude/claude` — delete lines 23-25 (the `sys.path.insert` of `server/src` and the `PANTHER_REPO` bootstrap; the package is installed in the interpreter that runs the shim), and remove `"PANTHER_REPO",` from the env-key tuple near line 404. Its `RAW` constant is now `python -m ai_rfc` after the perl rewrite, so the bare validator call at line 298 must name the verb: `f"{RAW} check {ws}/manifest.yaml --out {ws}/out --repo {ws}/clone --strict"`. The `{RAW}.draft checkpoint …` and `{RAW}.draft gate …` forms at lines 230 and 310 stay valid as module invocations, and `{RAW} --bogus` at line 360 still exits 2 (the dispatcher's unknown-verb code).

- [ ] **Step 5: Retire the bootstrap from the experiment sources**

`arms.py` — replace `mcp_config` (lines 142-161):

```python
def mcp_config(*, python: str, workspace: Path) -> dict[str, Any]:
    """The rendered MCP config mounting the ``ai_rfc`` server for one run.

    The server is a module of the installed package, so the config names the
    interpreter and the module and nothing else; there is no checkout to
    locate and no path to bootstrap.
    """
    return {
        "mcpServers": {
            "ai_rfc": {
                "command": python,
                "args": ["-m", "ai_rfc.server"],
                "env": {"AI_RFC_WORKSPACE": str(workspace)},
            }
        }
    }
```

`config.py` — line 31-33 `_SHIM` becomes:

```python
_SHIM = """#!/bin/sh
exec "{python}" -c "import sys; from ai_rfc.server.cli import main; sys.exit(main())" "$@"
"""
```

delete the `server_src` property (lines 132-135); line 286 becomes `_SHIM.format(python=python)`.

`runner.py` — delete the `"PANTHER_REPO": str(campaign.panther_repo),` line in `build_env`; the `mcp_config(...)` call in `prepare_run_argv` becomes `mcp_config(python=campaign.python, workspace=ref.workspace)`.

`metrics.py` — delete `_extend_sys_path` (the function at line 52 and every call to it, `grep -n _extend_sys_path`); line 136 becomes `ctx = Context(workspace=workspace)`; the lazy imports at lines 130-131 and 165 stay as the perl rewrote them (`from ai_rfc.server.core.gates import ...`, `from ai_rfc.server.paths import Context`, `from ai_rfc import report, schema`) but move to module scope if `flake8` flags them as late imports with no remaining reason.

`workspace.py` — delete `_substrate_modules` (lines 124-135) and add at module scope:

```python
from ai_rfc.draft.checkpoint import write_checkpoint
from ai_rfc.timeline.store import read_clusters
from ai_rfc.views import cli as views_cli
```

`preseed` loses its `panther_repo` parameter and the docstring line for it: signature `def preseed(workspace: Path, ordinals: Iterable[int]) -> list[str]:`; delete the line `write_checkpoint, read_clusters, _ = _substrate_modules(panther_repo)`. In `prepare`, delete `_, read_clusters, views_cli = _substrate_modules(panther_repo)` and change the `preseed(...)` call to `preseed(pristine, out_of_window(ordinals, target.window))`; `prepare` keeps `panther_repo` because `target.source` is relative to it. Remove `import sys` if nothing else uses it.

`preflight.py` — `build_invocations` loses `panther_repo` and the `"PANTHER_REPO": str(panther_repo),` line; `prepare_scratch` becomes `def prepare_scratch(*, root: Path, python: str) -> Path:`, its `sys.path` loop and `server_src`/`panther_repo` arguments go, the import becomes `from ai_rfc.server.testing import build_workspace` at module scope, and the `mcp_config` call becomes `mcp_config(python=python, workspace=workspace)`; `run_preflight` loses `panther_repo` and passes neither `panther_repo=` nor `server_src=` down.

`cli.py` — `_default_plugin_dir` returns `Path(__file__).resolve().parents[2] / "plugins" / "ai-rfc"`; `_run_parity` becomes:

```python
def _run_parity(python: str) -> dict:
    """Run the server parity suite; the protocol's stop-ship construct check.

    Args:
        python: Interpreter to run pytest with.

    Returns:
        Whether it passed and pytest's last line.
    """
    env = {**os.environ, "SSLKEYLOGFILE": ""}
    completed = subprocess.run(
        [python, "-m", "pytest", "-q", "tests/server/test_parity.py"],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        env=env,
    )
```

(the rest of its body unchanged); its call becomes `_run_parity(args.python)`. Delete the `--panther-repo` argument from the `preflight` parser only, and the `panther_repo=args.panther_repo.resolve(),` line from the `preflight` branch. `workspace prepare` and `campaign init` keep theirs.

Then:

```bash
cd "$AIRFC"; grep -rn "PANTHER_REPO\|server_src\|_extend_sys_path\|_substrate_modules\|sys\.path" ai_rfc/experiment
```

Expected: nothing except `guard.py`'s own `sys.path` line, which is the hook's bootstrap and stays — but its depth changes: `guard.py` now lives at `ai_rfc/experiment/guard.py`, so `sys.path.insert(0, str(Path(__file__).resolve().parents[1]))` becomes `parents[2]` (the repository root, where `ai_rfc` is importable even without the install), and the perl rewrite has already turned its `from experiment.enforcement import is_allowed` into `from ai_rfc.experiment.enforcement import is_allowed`.

- [ ] **Step 6: Point the raw arm at the dispatcher**

In `render.py` after the perl: `SKILL_FRONTMATTER`'s `allowed-tools` line already reads `Bash(python -m ai_rfc*)`. Edit the `_RAW` table: in `lint` and `gate`, `"`python -m ai_rfc "` becomes `"`python -m ai_rfc check "`; in `checkpoint`, `"`python -m ai_rfc.draft checkpoint "` becomes `"`python -m ai_rfc draft checkpoint "`; in `citation_gate`, `"`python -m ai_rfc.draft gate "` becomes `"`python -m ai_rfc draft gate "`. The two `runtime` strings become `"commands below run with an interpreter that imports `ai_rfc` (`python -m ai_rfc …`)"` (interactive) and `"`python` on `PATH` imports `ai_rfc`; run every `python -m ai_rfc …` command as written"` (C). In `prompts/loop.tmpl.md`, the preconditions bullet `` - `PANTHER_REPO` and `AI_RFC_WORKSPACE` are set; `` becomes `` - `AI_RFC_WORKSPACE` is set; `` (confirm with `grep -n PANTHER_REPO ai_rfc/experiment/prompts/loop.tmpl.md`, expected nothing after).

In `tests/experiment/test_render.py`, `test_arm_renderings_name_only_their_surface` becomes:

```python
def test_arm_renderings_name_only_their_surface():
    a, b, c = (render_loop(arm) for arm in "ABC")
    assert "ai_rfc_cluster_next" in a
    assert "ai_rfc cluster-next" not in a and "python -m ai_rfc" not in a
    assert "ai_rfc cluster-next" in b
    assert "ai_rfc_cluster_next" not in b and "python -m ai_rfc" not in b
    assert "python -m ai_rfc" in c
    assert "arfc_" not in c and "ai_rfc cluster" not in c
```

Regenerate the plugin skill, which the byte-equality test pins:

```bash
cd "$AIRFC"; SSLKEYLOGFILE= "$PY" -m ai_rfc.experiment render
git diff --stat plugins/ai-rfc/skills/ai-rfc-reconstruction-loop/SKILL.md
```

Expected: `wrote .../SKILL.md`; the diff touches the frontmatter's `allowed-tools`, the preconditions bullet, and the four raw commands, nothing else.

- [ ] **Step 7: Fix the call sites the signatures changed**

```bash
cd "$AIRFC"; grep -rn "preseed(\|mcp_config(\|prepare_scratch(\|build_invocations(\|run_preflight(\|_run_parity(" tests/experiment ai_rfc/experiment | grep -v "def "
```

For every hit, drop the `panther_repo`/`server_src` arguments (`test_workspace.py:102,121,128` pass `panther_repo` positionally to `preseed`; `test_preflight.py` and `test_arms.py` pass keywords). Ship the prompts with the package: add to `pyproject.toml`:

```toml
[tool.setuptools.package-data]
"ai_rfc.experiment" = ["prompts/*.md"]
```

- [ ] **Step 8: Run all three suites**

```bash
cd "$AIRFC"; SSLKEYLOGFILE= "$PY" -m pip install -e '.[mcp,tests,dev]' 2>&1 | tail -1
SSLKEYLOGFILE= "$PY" -m pytest -n auto -q 2>&1 | tail -2
SSLKEYLOGFILE= "$PY" -m ai_rfc.experiment --help | head -3
```

Expected: 769 minus the aggregates tests plus the new ones (six dispatcher, three paths, two here), zero failures; the experiment help from any directory. If a fixture-driven test fails on a command string, the fixture still carries an old prefix: `grep -rn "python -m" tests/experiment/fixtures tests/experiment/fake_claude` and align it with `RAW_PREFIX`.

- [ ] **Step 9: Lint and commit**

```bash
cd "$AIRFC"; "$PANTHER/.venv/bin/black" --check ai_rfc tests | tail -1; "$PANTHER/.venv/bin/flake8" --max-line-length=88 ai_rfc/experiment | tail -3
git add ai_rfc/experiment tests/experiment pyproject.toml plugins/ai-rfc/skills/ai-rfc-reconstruction-loop/SKILL.md
git commit -m "refactor: make the experiment driver the ai_rfc.experiment package"
```

Expected: black clean on the files this task touched (the four pre-existing harness reformat findings may remain elsewhere; do not reformat unrelated files); flake8's 49 harness findings may remain, none new.

---

### Task 6: The plugin surface and the repository README

**Files:**
- Modify: `plugins/ai-rfc/.mcp.json` (whole file), `plugins/ai-rfc/.claude-plugin/plugin.json` (description), `.claude-plugin/marketplace.json` (description), `plugins/ai-rfc/commands/ai-rfc-init.md` (whole file), `plugins/ai-rfc/skills/ai-rfc-evidence-hygiene/SKILL.md:9`, `docs/parity.md` (four rows), `README.md` (whole file)
- Test: `tests/server/test_plugin_manifest.py` (new)

**Interfaces:**
- Consumes: `python -m ai_rfc.server`, the `ai-rfc` verbs.
- Produces: a plugin that launches the installed server, and commands that name the new door.

- [ ] **Step 1: Write the failing manifest test**

Create `tests/server/test_plugin_manifest.py`:

```python
"""The plugin launches the installed server; nothing bootstraps a path."""

import json
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2] / "plugins" / "ai-rfc"


def test_the_mcp_manifest_runs_the_installed_server():
    server = json.loads((PLUGIN / ".mcp.json").read_text())["ai_rfc"]
    assert server["command"] == "python3"
    assert server["args"] == ["-m", "ai_rfc.server"]
    assert set(server["env"]) == {"AI_RFC_WORKSPACE"}


def test_no_command_names_the_retired_door_or_variable():
    offenders = [
        path.name
        for path in (PLUGIN / "commands").glob("*.md")
        if "panther.plugins" in path.read_text() or "PANTHER_REPO" in path.read_text()
    ]
    assert offenders == []
```

- [ ] **Step 2: Run it to verify it fails**

```bash
cd "$AIRFC"; SSLKEYLOGFILE= "$PY" -m pytest tests/server/test_plugin_manifest.py -q 2>&1 | tail -3
```

Expected: both FAIL (`args` is a `-c` bootstrap; `ai-rfc-init.md` names both).

- [ ] **Step 3: Rewrite the manifest, the descriptions and the init command**

`plugins/ai-rfc/.mcp.json`:

```json
{
  "ai_rfc": {
    "command": "python3",
    "args": ["-m", "ai_rfc.server"],
    "env": {
      "AI_RFC_WORKSPACE": "${AI_RFC_WORKSPACE}"
    }
  }
}
```

In `plugins/ai-rfc/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`, replace "the PANTHER ai_rfc substrate" with "the ai_rfc substrate" in each `description`.

Replace `plugins/ai-rfc/commands/ai-rfc-init.md` entirely:

```markdown
---
description: Initialize a reconstruction workspace — clone, corpus, forge snapshot, timeline, views, scaffolded draft
---

Initialize the reconstruction workspace at `$AI_RFC_WORKSPACE` for the target
repository given as `$ARGUMENTS` (a forge URL). `AI_RFC_WORKSPACE` must be
set and `ai-rfc --help` must answer (the `ai-rfc` distribution is installed
in the interpreter `python3` resolves to); stop with a clear message if either
fails or the workspace already holds a corpus.

1. **Clone at full depth** into `$AI_RFC_WORKSPACE/clone` (shallow clones are
   refused by extraction). Record `git rev-parse HEAD` — this is the pin
   everything else is verified against.
2. **Corpus**: `ai-rfc history $AI_RFC_WORKSPACE/clone --out $AI_RFC_WORKSPACE/corpus`.
3. **Forge snapshot**: `ai-rfc forge fetch <URL> --repo $AI_RFC_WORKSPACE/clone
   --out $AI_RFC_WORKSPACE/forge`. A token is an **optional fidelity
   upgrade**, not a prerequisite: without `GITHUB_TOKEN`/`GITLAB_TOKEN`
   (`gh auth token` can supply the GitHub one) the discussion endpoints are
   refused, but the pull records clustering actually reads still arrive, the
   command still exits 0, and the snapshot records `fidelity_ceiling: pulls`
   so the pipeline reports it done rather than stale. A fetch against a
   self-hosted GitLab requires the user's explicit go-ahead first. On
   failure, continue git-only and say so. When no route to the API exists at
   all, write the records to a JSON file by other means and use
   `ai-rfc forge adopt <records.json> <URL>` instead.
4. **Timeline**: `ai-rfc timeline $AI_RFC_WORKSPACE/corpus --repo
   $AI_RFC_WORKSPACE/clone --out $AI_RFC_WORKSPACE/timeline`, adding
   `--forge <snapshot dir>` when step 3 produced one. Report the
   cluster/rescue/unmatched numbers.
5. **Views**: `ai-rfc views $AI_RFC_WORKSPACE/timeline --corpus
   $AI_RFC_WORKSPACE/corpus --repo $AI_RFC_WORKSPACE/clone --out
   $AI_RFC_WORKSPACE/clusters` plus `--forge <snapshot>` when available.
6. **Draft scaffold**: clone `https://github.com/ElNiak/auto-i-d-template`
   (or pass a local path — `scaffold_draft` takes `template` as a parameter,
   so an already-downloaded copy works with no network)
   into `$AI_RFC_WORKSPACE/draft`, remove its `.git`, `git init -b main`,
   and **delete the `draft-*` rule from its root `.gitignore`** (the
   template repo ignores draft files; a draft repo must not). Create
   `draft-<name>.md` from the template's example with real front matter.
   Commit the scaffold.
7. **Registers**: write an empty `questions.yaml` (`questions: {}`) and
   `revisions.yaml` (`revisions: {}`), and create `interviews/`.

Finish by reporting the pin, the cluster counts, and the first cluster id
the loop will process.
```

In `plugins/ai-rfc/skills/ai-rfc-evidence-hygiene/SKILL.md` line 9, replace the parenthetical path `$PANTHER_REPO/panther/plugins/services/testers/ai_rfc` with `the installed ai_rfc package, python -m ai_rfc --help` (read the sentence after editing; it must still parse).

In `docs/parity.md`, the raw-substrate column of four rows: `ai_rfc_claim_adjudicate` → `` `python -m ai_rfc check <manifest> --out …` → report.json `claims` ``; `ai_rfc_checkpoint` → `` `python -m ai_rfc draft checkpoint …` ``; `ai_rfc_gate` → `` `python -m ai_rfc check <manifest> --out … --repo … [--strict]` ``; `ai_rfc_citation_gate` → `` `python -m ai_rfc draft gate … [--strict]` ``; and in the `ai_rfc_revision_tag` row `python -m …ai_rfc.draft gate … --strict` → `python -m ai_rfc draft gate … --strict`.

- [ ] **Step 4: Rewrite the repository README**

Replace `README.md` entirely:

```markdown
# ai_rfc — reconstruct a specification from a repository's own history

`ai_rfc` mines a software project's history into an RFC-style specification
whose every claim is gated against the evidence behind it. One repository
holds all of it:

- `ai_rfc/` — the deterministic **substrate**: corpus extraction, forge
  snapshots, timeline clustering, evidence views, claim manifests, checkpoints
  and gates. It makes no model calls and opens no socket except in `forge`.
  Its design and schema are documented in `ai_rfc/README.md`.
- `ai_rfc/server/` — the **MCP server** and its parity CLI (`ai_rfc <verb>`):
  one core, two frontends, so an agent cannot overstate what the evidence
  supports whichever door it uses.
- `ai_rfc/experiment/` — the **driver and instrument**: pristine workspaces,
  hermetic `claude -p` sessions, per-cluster sweeps, audit and metrics.
- `plugins/ai-rfc/` — the **Claude Code plugin**: skills, commands, `.mcp.json`.

## Install

```bash
pip install -e '.[mcp]'        # the substrate, the server and the ai-rfc door
ai-rfc --help                  # every verb, in workflow order
claude plugin marketplace add /path/to/ai_rfc && claude plugin install ai-rfc
```

The plugin runs `python3 -m ai_rfc.server`, so the distribution must be
installed in the interpreter `python3` resolves to for the session.

PANTHER consumes this repository as the submodule
`panther/plugins/services/testers/ai_rfc`; `panther build dev` installs it and
`panther ai-rfc <verb>` forwards to `ai-rfc <verb>`.

## Environment contract

One variable: `AI_RFC_WORKSPACE`, a reconstruction workspace (clone, corpus,
timeline, clusters, checkpoints, manifest, questions, revisions, draft).
Missing it fails loudly; nothing guesses.

## Two doors, one behaviour

`ai-rfc <verb>` and `python -m ai_rfc <verb>` are the same dispatcher over the
same eight programs (`history`, `forge`, `timeline`, `views`, `check`,
`draft`, `coverage`, `pipeline`), each also reachable as
`python -m ai_rfc.<sub>`. Exit codes everywhere: 0 clean, 1 unusable input,
2 malformed invocation (argparse), 3 strict findings.

## Experiment harness

`python -m ai_rfc.experiment` runs from any directory: `profile init`,
`preflight`, `workspace prepare|reseal`, `campaign init`, `run`, `audit`,
`questions`, `analyze`. State lives under `AI_RFC_EXPERIMENTS_ROOT` (default
`~/ai-rfc-experiments`), never inside a repository. The first full campaign is
reported in `docs/experiments/2026-08-31-pilot-aioquic.md`; the protocol is
`docs/experiment-protocol.md`; the tool-to-CLI parity table is
`docs/parity.md`. A whole-repository sweep is a target whose window spans every
cluster, run with `--session-mode per-cluster`; see `ai_rfc/experiment/per_cluster.py`.

## Tests

```bash
pip install -e '.[mcp,tests,dev]'
pytest -n auto                 # tests/substrate, tests/server, tests/experiment
```
```

- [ ] **Step 5: Run the tests and commit**

```bash
cd "$AIRFC"; SSLKEYLOGFILE= "$PY" -m pytest tests/server tests/experiment/test_render.py -q 2>&1 | tail -2
git add plugins/ai-rfc/.mcp.json plugins/ai-rfc/.claude-plugin/plugin.json .claude-plugin/marketplace.json plugins/ai-rfc/commands/ai-rfc-init.md plugins/ai-rfc/skills/ai-rfc-evidence-hygiene/SKILL.md docs/parity.md README.md tests/server/test_plugin_manifest.py
git commit -m "feat(plugin): launch the installed server and name the ai-rfc door"
```

Expected: all pass, including the two new manifest tests.

---

### Task 7: PANTHER consumes ai_rfc as one submodule

**Files:**
- Delete (from PANTHER's index): `panther/plugins/services/testers/ai_rfc/**` except `harness/`, `tests/unit/plugins/services/testers/ai_rfc/**`, the `harness` gitlink
- Modify: `$PANTHER/.gitmodules`, `$PANTHER/panther_builder.py:163-176`, `$PANTHER/pyproject.toml` (every `panther_ivy` exclusion), `$PANTHER/panther/cli/commands/ai_rfc.py` (whole file), `$PANTHER/docs_src/reference/ai_rfc.md` (whole file), `$PANTHER/docs_src/reference/cli.md:5-22`, `$PANTHER/CLAUDE.md:24-27,171`
- Test: `$PANTHER/tests/unit/test_cli/test_ai_rfc_commands.py` (whole file)

**Interfaces:**
- Consumes: `ai_rfc.cli.main` from the installed distribution.
- Produces: the submodule `panther/plugins/services/testers/ai_rfc` → `https://github.com/ElNiak/ai_rfc.git`, and `panther ai-rfc <args>` ≡ `ai-rfc <args>`.

- [ ] **Step 1: Confirm the trees and record the pre-task count — confirmation point**

Ask before this task: it re-points a submodule and needs the sandbox off. Then:

```bash
git -C "$PANTHER" log -1 --format='%h %ad %s' --date=format:'%H:%M:%S'; git -C "$PANTHER" status --short
git -C "$AIRFC" status --short; git -C "$AIRFC" log -1 --format=%h
cd "$PANTHER"; SSLKEYLOGFILE= .venv/bin/pytest tests/ -n auto -m unit -q 2>&1 | tail -1 | tee "$G/before-task7.txt"
SSLKEYLOGFILE= .venv/bin/pytest tests/unit/test_cli/test_ai_rfc_commands.py --collect-only -q 2>&1 | tail -1 | tee -a "$G/before-task7.txt"
```

Expected: both trees clean; the ai_rfc HEAD is Task 6's commit; the second line records how many tests the old door file holds (collected, not remembered: the legibility plan added tests after the last count anyone wrote down).

- [ ] **Step 2: Write the failing door test**

Replace `tests/unit/test_cli/test_ai_rfc_commands.py` entirely:

```python
"""The ``panther ai-rfc`` door onto the installed ai_rfc tool.

Everything after ``ai-rfc`` is forwarded to ``ai_rfc.cli.main`` and the exit
code comes back untouched, so the door and ``ai-rfc`` cannot disagree.
"""

import pytest
from click.testing import CliRunner

from panther.cli.commands.ai_rfc import ai_rfc
from panther.cli.core.main import cli

pytestmark = pytest.mark.unit


def test_the_door_reaches_the_panther_cli():
    """A silent ImportError would delete it from ``panther --help``."""
    assert "ai-rfc" in cli.commands


def test_help_is_the_tools_own():
    result = CliRunner().invoke(ai_rfc, ["--help"])
    assert result.exit_code == 0
    assert result.output.startswith("usage: ai-rfc <verb>")


def test_a_malformed_invocation_still_exits_two():
    """argparse owns 2, and click must not relabel it on the way out."""
    assert CliRunner().invoke(ai_rfc, ["check", "--no-such-flag"]).exit_code == 2


def test_an_unreadable_manifest_exits_one(tmp_path):
    """1 is returned, not raised: the one code a ``return`` in the callback would lose."""
    result = CliRunner().invoke(
        ai_rfc, ["check", str(tmp_path / "missing.yaml"), "--out", str(tmp_path / "out")]
    )
    assert result.exit_code == 1


def test_a_strict_finding_exits_three(tmp_path):
    manifest = tmp_path / "overstated.yaml"
    manifest.write_text(
        "rfc: SPEC-1\n"
        "title: 'x'\n"
        "requirements:\n"
        "  'spec:1.1':\n"
        "    text: 'x'\n"
        "    section: '1.1'\n"
        "    level: MUST\n"
        "    layer: timing\n"
        "    status: confirmed\n"
    )
    result = CliRunner().invoke(
        ai_rfc, ["check", str(manifest), "--out", str(tmp_path / "out"), "--strict"]
    )
    assert result.exit_code == 3
```

Run: `cd "$PANTHER"; SSLKEYLOGFILE= .venv/bin/pytest tests/unit/test_cli/test_ai_rfc_commands.py -q 2>&1 | tail -3`
Expected: `test_help_is_the_tools_own` FAILS (the old group prints click help); the exit-code tests pass through the old group already, which is why the help test is the gate.

- [ ] **Step 3: Replace the door**

Replace `panther/cli/commands/ai_rfc.py` entirely:

```python
"""``panther ai-rfc``: PANTHER's door onto the ai_rfc tool.

ai_rfc is its own project, installed from the submodule at
``panther/plugins/services/testers/ai_rfc`` by ``panther build dev``. This
command forwards everything after ``ai-rfc`` to that tool's own dispatcher and
exits with whatever it returns, so ``panther ai-rfc`` and ``ai-rfc`` cannot
disagree.

The import happens inside the callback. ``register_commands`` swallows an
``ImportError`` raised at import time into a warning nobody sees, so an
uninstalled submodule must fail here, where the message reaches a terminal.
"""

from __future__ import annotations

import sys

import click


@click.command(
    name="ai-rfc",
    help="Reconstruct an RFC-style specification from a project's own history.",
    context_settings={"ignore_unknown_options": True},
    add_help_option=False,
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def ai_rfc(args: tuple[str, ...]) -> None:
    """Forward to ``ai-rfc`` and exit with its code."""
    try:
        from ai_rfc.cli import main
    except ImportError:
        raise click.ClickException(
            "ai_rfc is not installed: run "
            "`git submodule update --init panther/plugins/services/testers/ai_rfc` "
            "and then `panther build dev`"
        ) from None
    sys.exit(main(list(args)))
```

`sys.exit(...)` rather than `return`: click discards a callback's return value and exits 0, which would flatten every 1 and 3 into success. `list(args)` rather than `None`: `main(None)` would re-read `sys.argv`, which here begins with the verb.

Run the door test again: expected all five pass (the old group is gone, and the substrate is still importable from PANTHER's tree, so nothing else moved yet).

- [ ] **Step 4: Retire the substrate from PANTHER and re-point the submodule** (sandbox off)

```bash
cd "$PANTHER"
git rm -q --cached panther/plugins/services/testers/ai_rfc/harness
git rm -r -q panther/plugins/services/testers/ai_rfc tests/unit/plugins/services/testers/ai_rfc
mv panther/plugins/services/testers/ai_rfc/harness panther/plugins/services/testers/ai_rfc__moving
rm -rf panther/plugins/services/testers/ai_rfc tests/unit/plugins/services/testers/ai_rfc tests/unit/plugins/_arfc_probe
mv panther/plugins/services/testers/ai_rfc__moving panther/plugins/services/testers/ai_rfc
```

(A sibling rename, never `$TMPDIR`: a move across volumes copies and can lose the nested `.git`.) Edit `.gitmodules`: delete the three-line `[submodule "panther/plugins/services/testers/ai_rfc/harness"]` block; leave the stale `submodule.…/harness` section in `.git/config` alone, since the worktree shares that file with the main checkout. Then:

```bash
git submodule add https://github.com/ElNiak/ai_rfc.git panther/plugins/services/testers/ai_rfc
git submodule status
cat .gitmodules
"$PY" -m pip install -e 'panther/plugins/services/testers/ai_rfc[mcp,tests,dev]' 2>&1 | tail -1
"$PY" -c "import ai_rfc, pathlib; print(pathlib.Path(ai_rfc.__file__).resolve())"
```

Expected: `git submodule add` reports the existing repository was added without cloning; `git submodule status` shows `panther_ivy` and `panther/plugins/services/testers/ai_rfc` at Task 6's SHA; `.gitmodules` holds exactly two entries; the reinstall is required because Task 3's editable install recorded the old `…/ai_rfc/harness` path, which no longer exists, and the printed path now ends in `testers/ai_rfc/ai_rfc/__init__.py`. `AIRFC` now means `$PANTHER/panther/plugins/services/testers/ai_rfc`.

- [ ] **Step 5: Teach the builder, the packaging and the docs**

`panther_builder.py` — after the `panther_ivy` block (ending at the `os.environ["CMAKE_POLICY_VERSION_MINIMUM"] = old_val` line), add:

```python
        # Install ai_rfc submodule if present
        ai_rfc_path = project_root / "panther" / "plugins" / "services" / "testers" / "ai_rfc"
        if (ai_rfc_path / "pyproject.toml").exists():
            print("Installing ai_rfc submodule...")
            _run([sys.executable, "-m", "pip", "install", "--editable", f"{ai_rfc_path}[mcp]"])
```

`pyproject.toml` — beside every `panther_ivy` entry (`grep -n panther_ivy pyproject.toml` lists the black `extend-exclude`, the bandit `exclude_dirs` and the flake8/mypy `exclude` lines), add the sibling `panther/plugins/services/testers/ai_rfc` entry in the same syntax, so PANTHER's linters never walk the submodule.

`CLAUDE.md` — after the `pip install -e panther/plugins/services/testers/panther_ivy/` line add:

```bash
# If using ai_rfc (init submodule first):
git submodule update --init panther/plugins/services/testers/ai_rfc
pip install -e 'panther/plugins/services/testers/ai_rfc[mcp]'
```

and change the "Excluded from linting" bullet to name both submodules.

`docs_src/reference/ai_rfc.md` — replace entirely:

```markdown
# ai_rfc — reconstructed specifications

`ai_rfc` reconstructs an RFC-style specification from a software project's own
history and gates every claim against the evidence behind it. It is its own
project, consumed here as the submodule `panther/plugins/services/testers/ai_rfc`
and installed by `panther build dev`.

- `panther ai-rfc <verb>` forwards to the tool's own `ai-rfc <verb>` and
  returns its exit code unchanged (0 clean, 1 unusable input, 2 malformed
  invocation, 3 strict findings).
- `ai-rfc --help` lists every verb in workflow order.
- The tool's documentation, schema, promotion rule and design records live in
  its repository: <https://github.com/ElNiak/ai_rfc>.
```

`docs_src/reference/cli.md` — replace the admonition (lines 5-22) with:

```markdown
!!! note "`ai-rfc` forwards its arguments"

    `panther ai-rfc` is a passthrough onto the installed `ai-rfc` tool, an
    independent project consumed as a submodule; its arguments are not
    described here. See [ai_rfc (reconstructed specs)](ai_rfc.md).
```

- [ ] **Step 6: Verify**

```bash
cd "$PANTHER"
SSLKEYLOGFILE= .venv/bin/python -c "import panther.plugins.services.testers.ai_rfc.schema" 2>&1 | tail -1
SSLKEYLOGFILE= .venv/bin/python -m panther --help | grep ai-rfc
SSLKEYLOGFILE= .venv/bin/python -m panther ai-rfc check --help | head -1
SSLKEYLOGFILE= .venv/bin/python -m panther ai-rfc pipeline status reconstructions/mark | diff - "$G/mark-status.txt" && echo "status identical"
SSLKEYLOGFILE= .venv/bin/pytest tests/unit/test_cli/test_ai_rfc_commands.py -q 2>&1 | tail -1
SSLKEYLOGFILE= .venv/bin/pytest tests/ -n auto -m unit -q 2>&1 | tail -1 | tee "$G/after-task7.txt"
git status --short | head -20
```

Expected: the first line is a `ModuleNotFoundError` naming `schema` (the bare package name would still import: the submodule's directory sits inside a regular package without an `__init__.py`, which Python treats as a namespace package, so only a leaf proves the substrate is gone); `panther --help` lists `ai-rfc`; `usage: ai-rfc check`; `status identical`; five door tests pass. Compare `$G/after-task7.txt` with `$G/before-task7.txt`: the passed count drops by the substrate suite's count from `$G/baseline-tests.txt` line 1 minus the old door file's collected count from `$G/before-task7.txt` line 2, plus the new door file's 5; no new failure or collection error. Write the counts and the arithmetic into `$G/NOTES.md`.

- [ ] **Step 7: Commit — explicit paths only**

```bash
cd "$PANTHER"
git add .gitmodules panther/plugins/services/testers/ai_rfc panther_builder.py pyproject.toml CLAUDE.md panther/cli/commands/ai_rfc.py tests/unit/test_cli/test_ai_rfc_commands.py docs_src/reference/ai_rfc.md docs_src/reference/cli.md
git status --short
git commit -m "refactor(ai_rfc): consume ai_rfc as one submodule installed by the builder"
```

Expected: `git status --short` before the commit shows only the staged removals and the files above; nothing unstaged is left behind except untracked caches.

---

### Task 8: Push and record the outcome — confirmation point

**Files:**
- Modify: `$PANTHER/docs/superpowers/specs/2026-09-02-ai-rfc-extraction-and-flow-design.md` (append an *Outcome* section)

- [ ] **Step 1: Push the submodule before the parent**

Ask first. The `ai_rfc` push works inside the sandbox over HTTPS (a `failed to store: 100001` keychain warning after success is harmless); the PANTHER push needs the sandbox off (SSH).

```bash
git -C "$PANTHER/panther/plugins/services/testers/ai_rfc" push origin main
git -C "$PANTHER" push origin feat/arfc-pipeline-and-runtime-anchors
```

- [ ] **Step 2: Record what landed**

Append to the spec file an `## Outcome` section listing, per task, the commit SHA in each repository, the three suite counts from Task 5 Step 8, the PANTHER delta from `$G/NOTES.md`, and which goldens were diffed. Then:

```bash
cd "$PANTHER"; git add -f docs/superpowers/specs/2026-09-02-ai-rfc-extraction-and-flow-design.md
git commit -m "docs(ai_rfc): record the extraction outcome"
```

---

## Self-review

**Spec coverage.** D30 (one repo, one submodule): Tasks 1, 4, 5, 7. R7 (plain move citing the range): Task 1 Step 9. R8 (retire `PANTHER_REPO` from the server): Task 4; the experiment package's `--panther-repo` flag survives on `workspace prepare` and `campaign init` only because it still locates `reconstructions/` and feeds `git describe`, which SP2 retires with the driver. R10 (installed distribution, no `sys.path`): Tasks 3 to 6. B-1 (dispatcher root): Task 3, marked interim. Dead `aggregates` (review U-3): Task 2. `types-PyYAML` (review U-1): Task 3's `dev` extra. Goldens and byte identity: Tasks 0, 1, 3, 7. Nothing in Part A's SP1 row is unaddressed.

**Placeholders.** None: every edit carries its code or its exact command, and every gate names its expected output. Two steps rely on the executor reading a sentence after a mechanical edit (Task 6 Step 3's skill line; Task 5 Step 7's call sites); both name the grep that lists every site.

**Type consistency.** `mcp_config(*, python: str, workspace: Path)` is defined in Task 5 Step 5, tested in Step 2 and called in `runner.py` and `preflight.py` with the same keywords. `Context(workspace=...)` from Task 4 Step 4 is what Task 5's `metrics.py:136` constructs. `preseed(workspace, ordinals)` matches its three test call sites. `ai_rfc.cli.main(argv) -> int` is what Task 7's door calls and what Task 3's tests exercise.

**Known ordering hazard.** Between Task 4 and Task 5 the experiment suite does not collect; both tasks say so, and Task 5 restores it.

## Outcome (executed 2026-09-03, subagent-driven)

| Task | Commits | Gate |
|---|---|---|
| 0 | none (goldens + baselines under `reconstructions/_baselines/extraction-2026-09-02/`) | substrate 405 (376 without the 29 PANTHER door tests); experiment 377; server 40; whole PANTHER unit suite 1529 passed / 19 failed / 8 errors |
| 1 | ai_rfc `d7f2c69` | 376 passed; both goldens identical |
| 2 | ai_rfc `7561521` | 371 (5 aggregates tests gone) |
| 3 | ai_rfc `9d87151`, fix `3d1ac2c` | 384; `ai-rfc` script; three goldens identical |
| 4 | ai_rfc `41d7b65`, fix `17467fd` | server 43 + substrate 384 |
| 5 | ai_rfc `51e84fa`, fix `3b12595` | 806 (experiment 379) |
| 6 | ai_rfc `9971640`, fix `abc07a3` | 808 |
| 7 | PANTHER `b50e569d0` | door tests 5/5; whole unit suite 1149 passed with the same 19 failures / 8 errors |
| final fix wave | PANTHER `ddfee0af8`, ai_rfc `89c4bd5`, pointer bump `80e6a19e4` | door tests 5/5 under both pytest configs; 808 |
| 8 | pending the user's push confirmation | |

## Corrections found during execution

- **`-o pythonpath=` was needed for Task 1's suite run** and the plan's Step 7
  did not say so: PANTHER's `pytest.ini` is discovered from the nested
  checkout until Task 3 writes `pyproject.toml`, and its `pythonpath` puts the
  old copy first.
- **The move needed four more edits than the brief listed** — the validator's
  relative imports (`..report`, `..schema`) after it went one level deeper,
  `pipeline/run.py`'s import of it, `tests/substrate/test_cli.py`'s import,
  and the README's three prose mentions of the root `cli.py`.
- **`tests/pytest.ini` and the root `pytest.ini` both put
  `panther/plugins/services/testers` on `sys.path`**, so a submodule root
  named `ai_rfc` (no `__init__.py`) becomes a namespace package that shadows
  the installed one under pytest (setuptools' editable finder is appended to
  `sys.meta_path`; `PathFinder` wins). Both files now list the submodule root
  first. The shadow is structural (D30 named the directory after the package)
  and SP6 should remove it at the root.
- **`panther build dev` never installed the submodule**: the plan named
  `panther_builder.py`, whose install block runs only on the bootstrap path
  because `panther_builder.py` forwards to the `panther` CLI whenever it
  resolves. `panther/cli/commands/build.py` now carries
  `_install_ai_rfc_submodule` beside the ivy step.
- **`python3` in `.mcp.json` did not resolve to an interpreter with the
  package** and a server that fails to start mounts no tools without failing
  the session; the command is now `${AI_RFC_PYTHON}`, a required variable
  beside `AI_RFC_WORKSPACE` (R10 amended: the requirement is explicit).
- **`CLAUDE.md` may not be written by any agent** (a project guard hook), so
  Task 7's two edits are for the user, below.
- **The experiment suite was 377, not 339; the `mcp_config` test already
  existed; `test_parity.py` and the guard hook derived paths by depth;
  `test_arms.py` builds one old-prefix string on purpose; the stream fixture
  freezes an older spelling on purpose** — all recorded in the ledger as
  rulings.
- **The regenerated arm-C prompt instructs `python -m ai_rfc draft
  checkpoint` while `metrics._cluster_of_call` matched only the module form**
  — it now accepts both, and the fake `claude` emits the dispatcher form.
- The old `ai-rfc-server` distribution had to be uninstalled before Task 4's
  reinstall; `[tool.mypy] explicit_package_bases = true` is needed for mypy to
  run from a checkout nested under PANTHER's package tree.

## CLAUDE.md edits for the user to apply

Insert after the `pip install -e panther/plugins/services/testers/panther_ivy/` line:

```bash
# If using ai_rfc (init submodule first):
git submodule update --init panther/plugins/services/testers/ai_rfc
pip install -e 'panther/plugins/services/testers/ai_rfc[mcp]'
```

Change the "Excluded from linting" bullet to:

```
- **Excluded from linting**: `panther/plugins/services/testers/panther_ivy/` and `panther/plugins/services/testers/ai_rfc/` (submodules)
```

## Backlog carried forward

SP2: dead `campaign` parameters with stale docstrings in `metrics.py` and
`summary.py`; the temporal comment in `metrics.py`; `git["panther"]` in the
campaign record now pins a repository holding none of the code under test;
`server/__main__.py` without `sys.exit`. SP3: `entrypoints.py:43` still names
`mkdocs-click`; `dynamic = ["version"]` instead of three copies of `0.1.0`;
`check/cli.py` mixes absolute and relative imports; `doctor` should check
`AI_RFC_PYTHON`'s interpreter, which the init command's `ai-rfc --help` probe
does not. SP5: the isort/black pass (7 package files, ~16 test files, and
`tests/server/test_core.py`), a pre-commit config and CI for the new
repository, the README's "fails loudly" overclaim for `AI_RFC_PYTHON`,
`fake_claude/claude:295` at 92 columns. SP6: the structural namespace shadow
(either `panther_ivy` becomes importable by its install rather than by the
`testers` path entry, or the submodule directory is not named `ai_rfc`).
