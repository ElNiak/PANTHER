# ai_rfc extraction and flow — design (2026-09-02)

> Part A of `docs/superpowers/plans/2026-09-02-ai-rfc-extraction.md`, recorded verbatim as the spec that plan and the later sub-projects of its roadmap argue from.

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
