# ai_rfc "one door" — a uniform CLI and an autonomous `ai-rfc run` (design, 2026-09-03)

> Refines the roadmap of `docs/superpowers/specs/2026-09-02-ai-rfc-extraction-and-flow-design.md`:
> this is the design for its SP2 (production driver), SP3 (config-driven CLI) and SP4 (ledger),
> re-cut into three dependency-ordered sub-projects CLI-1, CLI-2, CLI-3. Decisions D29–D37 stay in
> force; recommendations R1–R11 are refined below. Execution plans:
> `docs/superpowers/plans/2026-09-03-arfc-one-door-cli{1,2,3}.md`.

## Context

An operator who wants a specification reconstructed from a repository meets three unrelated
surfaces: the `panther ai-rfc` door (eight substrate programs, every path explicit, no
environment), the harness (`python -m experiment …`, ten verbs that resolve only with the shell
inside the harness directory, `--panther-repo` typed three times, three printed paths copied by
hand, a closed target table `{aioquic, mark}`), and the parity CLI (`ai_rfc`, sixteen verbs, no
paths at all, two environment variables). `ai-rfc pipeline run` performs the deterministic
stages and then prints "next: read the cluster evidence and write claims" — an instruction to a
human for a step only a model session performs — and nothing in the substrate can hand over to
the harness.

Twelve frictions, each verified in the code on 2026-09-03: two front doors; the run-from-directory
harness; two path conventions across thirteen verbs; `forge --out` names a cache root that
downstream `--forge` refuses; the agent boundary with no handover; the environment triple
assembled in three places and `PANTHER_REPO` pushed onto `sys.path` in four; five colliding
`ai_rfc`/`ai-rfc` names; the `check` vs `claim-adjudicate` vocabulary split; a parity `checkpoint`
that cannot report exit 3; alphabetical `--from` choices; the closed target table; no substrate
writer for the question register.

Outcome wanted: **one console script, one config file, one command that does whatever is next
until the reconstruction is done or must stop**, resumable after a kill, with the three-arm
experiment instrument kept but out of the operator's way.

## Decision register (continues the global numbering after D52)

| # | Decision |
|---|---|
| D53 | This design is the spec for the roadmap's SP2, SP3 and SP4, refining R1–R11 and settling the seven items the extraction spec left undecided (below). |
| D54 | **`ai-rfc run --config recon.yaml` performs everything that is next** — clone and forge at `init`, history, timeline, views, then one model session per cluster (checkpoints and gates happen through the session's tools), consolidation rounds (SP7c hook), check/lint/build at the end — until done or a stop condition. `ai-rfc next` performs exactly one action. `ai-rfc status` prints the ledger. State is derived from artifacts, never a counter. |
| D55 | Sequencing: SP1 (extraction) → SP7a → SP7b → **CLI-1 → CLI-2 → CLI-3** → SP7c → SP7d. SP7a/SP7b execute as written; the unification folds their harness/server halves in one pass; SP7c targets the new driver's hook; SP7d targets `ai-rfc experiment`. |
| D56 | Verb tree: lifecycle at top level (`init`, `run`, `next`, `status`, `verify`, `doctor`, `config example`, `toolchain provision\|verify`); agent verbs grouped (`claim`, `cluster`, `corpus`, `question`, `answer`, `revision`, `checkpoint`, `gate`, `citation-gate`, `draft`, `structure`); the instrument under `ai-rfc experiment …`. The `ai_rfc` console script, the campaign `bin/ai_rfc` shim and both `prog="ai_rfc"` values retire (CLI-3); arm B's Bash family becomes `ai-rfc *`; MCP tool names `ai_rfc_*` stay — they are identifiers, not a door. |
| D57 | The config is the input; `init` seals a copy into the workspace with its digest. Every later verb takes `--config` or `AI_RFC_CONFIG`; the MCP server and agent verbs read `AI_RFC_CONFIG` and derive the workspace (R8: `PANTHER_REPO` gone; `AI_RFC_WORKSPACE` derived, no longer a contract). Drift between the sealed copy and the file is refused for `source.pin`, `window`, `draft.name`, noted for everything else, and reported by `verify`. |
| D58 | Production sessions are the MCP shape (today's arm A): `claude -p` with the `ai_rfc` MCP server, Read/Edit/Write/Grep/Glob, no Bash, the PreToolUse guard mounted with empty prefixes; budget, timeout and attempts from the config. The instrument (arms B/C, audit, parity, metrics, judge, ground truth) stays as `ai_rfc.experiment`, reached through `ai-rfc experiment …`, and shares the session launcher with production. |
| D59 | Stop conditions: the reconstruction's lifetime budget (summed over every run's transcript, moved-aside runs included), wall clock, a cluster not done after `attempts_per_cluster` (default 2; `--retry <id>` resets), a surface shortfall (MCP not mounted), a build that will not compile, a stale substrate under existing checkpoints, operator interrupt. Never skip a cluster. A mid-sweep consolidation failure is recorded and the sweep continues; a failing sweep-end consolidation exits 1. Every stop prints the ledger and the exact resume line. Interrupted leftovers are moved aside with a suffix naming the cause, never deleted. |
| D60 | Three dependency-ordered sub-projects with their own gates: **CLI-1 one door** (config + field-table validation, argparse root, ledger, `init`/`status`/`verify`/`doctor`, `run` for the deterministic stages stopping at the boundary), **CLI-2 autonomous driver** (sessions inside `run`, `next`, stop policy, resumability, instrument split), **CLI-3 one core** (server core calls Python APIs, agent verbs folded, `ai_rfc` retired, prompts and guard re-rendered, leaf programs retired from the operator's help). They satisfy SP3+SP4, SP2, and SP3's folding respectively. |
| D61 | Settled from the code: `timeout_s` is per session (today's cap is per run); attempts count only sessions that ended on their own (a killed or launch-errored session consumes none — MARK's ordinal 38 halted on a $0, one-turn launch error with $12.62 left, not on budget as D38 records); runs live under the workspace (`<workspace>/runs/<ts>/`, inverting today's nesting, which the instrument keeps for campaigns); the checkpoint stage is agent-performed in the MCP shape, so the driver never runs it; `pipeline.next_stage` drives only pin..views, the ledger drives the rest; R4's retirement of the explicit-path leaf verbs happens in CLI-3, once the server core no longer shells out to them — until then the root mounts them unchanged. |

## Undecided in the extraction spec → settled

| Item | Settled as |
|---|---|
| What replaces the `pipeline run` boundary | `run` continues into sessions when the config has a `sessions:` block; without one it stops at the boundary exactly as today and prints the instruction (a hand-mined workspace stays possible). |
| Where the ten `experiment` verbs go | `ai-rfc experiment preflight\|campaign init\|run\|audit\|analyze\|questions\|judge\|ground-truth\|render`; production never needs them. |
| Profile and experiments root | `sessions.profile` in the config, default `<experiments_root>/profile`; `doctor` creates it and prints the login line; `AI_RFC_EXPERIMENTS_ROOT` keeps its meaning for the instrument and as the default parent of workspaces and tools. |
| Import identity | SP1 makes `ai_rfc.experiment` a package; nothing depends on the shell's directory. |
| Name collision | one script `ai-rfc`; `prog` values `ai-rfc <verb>`; the campaign shim becomes `bin/ai-rfc`. |
| `forge --out` cache root | `init` fetches the snapshot into `<workspace>/forge/` and records the snapshot directory the timeline used; the leaf verb keeps its flag until CLI-3 retires it. |
| The tag step for operators | `ai-rfc revision tag` is the folded parity verb (CLI-3) and `run` performs it inside sessions (CLI-2); an operator can also tag a hand-written revision. |

## Design

### 1. The operator's flow

```
ai-rfc config example > recon.yaml        # starter, every field documented
$EDITOR recon.yaml
ai-rfc doctor                              # claude binary+version, profile login, toolchain verify,
                                           # tokens, no CLAUDE.md ancestry, python deps
ai-rfc init   --config recon.yaml          # networked once: clone at pin, forge snapshot; scaffold
                                           # draft (adopter), seal references, seal config
ai-rfc run    --config recon.yaml          # history → timeline → views → sessions per cluster →
                                           # consolidations → check → lint → build; stops per D59
ai-rfc status --config recon.yaml          # ledger: stage states, clusters done/partial/outstanding,
                                           # spend vs budget, attempts, last stop reason + resume line
ai-rfc verify --config recon.yaml --strict # digest, config drift, strict check, gate, completeness,
                                           # lint, build → exit 3 on findings
```

### 2. `recon.yaml` — a declarative field table (R3, stdlib + PyYAML)

`ai_rfc/config.py` holds `FIELDS: tuple[Field, ...]` (`path`, `kind`, `required`, `default`,
`choices`, `doc`); `load_config(path) -> ReconConfig` (a frozen dataclass tree) raises
`ConfigError("<path>: <problem>")`; `example()` and `reference_markdown()` render from the same
table (SP5's reference page). Sections:

| Section | Fields |
|---|---|
| top | `name` (required, `[a-z0-9][a-z0-9-]*`), `workspace` (path; default `<experiments_root>/reconstructions/<name>`) |
| `source` | `repo` (URL or local path, required), `host` (`github\|gitlab\|none`; default inferred from the URL), `pin` (sha or ref, required; `init` records the resolved sha), `token_env` (default `GITHUB_TOKEN`/`GITLAB_TOKEN` by host) |
| `window` | `[low, high]` inclusive ordinals; default every cluster |
| `draft` | `name` (required, starts with `draft-`), `title`, `abbrev`, `rfc_id` (manifest `rfc:`), `author` (name, org, email; default the harness identity) |
| `references` | RFC/I-D ids sealed from the toolchain cache (SP7a) |
| `sessions` | `model` (default `claude-opus-5`), `effort` (`low\|medium\|high\|xhigh`, default `high`), `budget_usd` (required when the block exists), `timeout_s` (per session, default 7200), `attempts_per_cluster` (default 2), `consolidate_every` (default 10; SP7c), `profile` (path), `claude` (binary; resolved at `init`) |
| `toolchain` | path to `toolchain.json` (default `<experiments_root>/tools/toolchain.json`) |
| `stages` | per-stage tuning (R4): `history.cap`, `timeline.forge` (bool, default true), `views.patches` (`span\|members`), `lint.must_fraction_ceiling`, `build.targets` |
| `experiment` | optional instrument block: `arms`, `repeats`, `seed`; ignored by `run`, read by `ai-rfc experiment campaign init` |

`init` writes `<workspace>/recon.yaml` (the sealed copy), `<workspace>/init.json` (config sha256,
resolved pin, forge snapshot directory, claude binary + version, toolchain sha256, package
version) and the pristine digest. It replaces `experiment/workspace.py`'s `Target` table and
`prepare` for production; campaigns keep `prepare` over a config.

### 3. The argparse root (R1)

`ai_rfc/cli.py` (SP1's interim dispatcher) becomes a real root: `main(argv)` builds one parser;
every existing `_parser()` becomes `configure(parser)`; exit codes 0/1/2/3 and `--json` are
uniform; help sections come from `entrypoints.py`'s three headings plus "Lifecycle" and "Agent".
`python -m ai_rfc.<sub>` keeps working through each module's `main()` around its `configure()`,
because the server core and the raw arm still invoke it until CLI-3. `panther ai-rfc` forwards
argv untouched to `ai_rfc.cli.main` (R6). `--from`/`--until` choices follow pipeline order.

### 4. The ledger (SP4, D35) — `ai_rfc/ledger.py`

One reader for every progress surface. `ClusterState{id, ordinal, kind, in_window, checkpoint,
revision_tag, tag_exists, done, partial_reason}`; `clusters(workspace, window)`, `next_cluster()`,
`partial()`. **Done** = a checkpoint directory holding `checkpoint.json`, **and** a `kind: cluster`
revision entry, **and** its annotated tag (the harness's strict definition; the server's
"any directory counts" definition disappears). Out-of-window clusters and clusters carrying the
pre-seed marker are done by definition. Consolidation checkpoints live under `consolidations/`
(D48) and never count. Replaces `pipeline/state._checkpoint`,
`draft/completeness.checkpoint_records`'s processed set, server
`queries._processed_cluster_ids`/`cluster_next`, `experiment/progress.window_progress`,
`metrics.cluster_artifacts` and `per_cluster.partial_reason`; those callers read ledger rows.

### 5. The driver (CLI-2) — `ai_rfc/driver/`

| Module | From | Holds |
|---|---|---|
| `spawn.py`, `stream.py`, `enforcement.py`, `guard.py` | `experiment/*` verbatim | process-group spawn with a SIGINT/SIGTERM handler that kills the group (today `start_new_session=True` orphans the session on Ctrl-C), transcript streaming, the guard |
| `session.py` | `arms.py` profile/argv/mcp config, `runner.build_env`/`prepare_run_argv`, `per_cluster`'s event reading, cost and shortfall checks | `SessionSpec` (claude, model, effort, budget_usd, timeout_s, profile, python, workspace, toolchain, prompt_file, task, surface), `run_session(spec, run_dir) -> SessionResult` |
| `sweep.py` | `per_cluster.run_per_cluster` minus the campaign summaries | `plan_next(ws, cfg, ledger) -> Action` (pure) and `run(cfg, ws, *, mode="all"\|"one", until, retry)`; `next_round()` hook for SP7c |
| `record.py` | the `sessions.jsonl` writer | `run.json` (once per invocation: config/init digests, prompt drift, claude version, budget, spent before), `sessions.jsonl` rows (`task_template`, `kind`), `status.json`, `spent()`, `attempts()`, `move_aside()` |
| `stop.py` | the budget/wall/halt/shortfall branches | `StopReason`, `classify(result)`, `resume_line(reason, config_path)` |

State machine:

| Condition | Action |
|---|---|
| `pin` pending | stop `needs_init` (`init` does clone + forge, D34) |
| `history`/`timeline`/`views` pending | perform via `DISPATCH`; non-zero → stop `stage_failed` |
| `timeline`/`views` stale **and** any checkpoint exists | stop `stale_substrate` (re-clustering renumbers what checkpoints pin) |
| views done, `next_cluster()` = c, attempts(c) < N, budget and clock left | a session for c; then re-read the ledger |
| attempts(c) ≥ N and c not done | stop `cluster_halted`; the resume line carries `--retry c` |
| budget or wall clock reached | stop `budget` / `wall_clock` |
| first judgeable session mounted no `ai_rfc` MCP | stop `surface_shortfall` + a doctor hint |
| `next_round()` due (SP7c) | consolidation session; mid-sweep failure noted, sweep continues; sweep-end failure → exit 1 |
| no cluster outstanding, no round due | `check --strict`, `lint`, `build` (skipped without a toolchain); findings → stop `build_failed`, exit 1; else `done`, exit 0 |

`next` performs one row; `--until <stage>|cluster:<id>|ordinal:<n>`. Exit codes: done 0; stopped
with work outstanding 1; strict findings 3. Session classification from the result event:
*refused* (worked, cluster not done → consumes an attempt), *errored* (`is_error`, at most one turn
→ a launch or API failure: stop with the resume line, no attempt consumed), *killed* (timeout or
interrupt), *budget_hit*. Budget is a lifetime cap: `spent()` sums result events across
`runs/*/events.jsonl`, moved-aside directories included (the `sessions.jsonl` row is appended after
the process returns, so a kill in between would lose it). Per session `--max-budget-usd` is what
the run has left. Leftovers on resume: a `runs/<ts>/` without `status.json` becomes
`runs/<ts>.interrupted-<cause>/`; a `checkpoints/<id>/` without `checkpoint.json` becomes
`checkpoints/<id>.interrupted-<ts>/`; a dirty draft worktree is named and left to the retry.

### 6. One core (CLI-3)

`ai_rfc/server/core/gates.py` stops shelling out to `python -m ai_rfc.draft …`: the core calls
`write_checkpoint`, `run_gate`, the check API, `build` and `lint` in-process (exit codes become
return values; `checkpoint` regains 3). `paths.resolve_context()` reads `AI_RFC_CONFIG`, loads the
sealed config, derives the workspace and toolchain. The sixteen parity verbs (plus SP7a/b's
`draft build|lint|render`, `structure upsert`) become grouped subcommands of the root; `tools.py`
and the grouped verbs call the same core (parity twins stay byte-identical). `render.py`'s slot
tables and the guard families are re-rendered to `ai-rfc …`; `experiment/config._SHIM` writes
`bin/ai-rfc`; `docs/parity.md` gains the new verb column; `experiment-protocol.md` records the
change; `claim adjudicate` becomes `claim check` to match the substrate rename; the explicit-path
leaf verbs leave the operator's help.

### 7. Error handling

Every failure names the artifact and the command that fixes it; nothing fails open. `init`
refuses an existing workspace; `run` refuses a drifted pin/window/draft name and a stale
substrate under checkpoints; a missing toolchain skips `build` and says so (D49: the build gate is
hard whenever a toolchain is configured; `doctor` warns when none is). Diagnostics go to stderr
(the `panther.*` loggers swallow warnings).

### 8. Testing

Existing suites move with their modules (post-SP1: `tests/substrate`, `tests/server`,
`tests/experiment`, plus new `tests/cli`, `tests/ledger`, `tests/driver`). New properties:
field-table validation (every required field, every choice, `example()` round-trips through
`load_config`); root help lists every verb once and forwards untouched; the ledger agrees with the
five replaced readers on the fixture workspace and on a copy of the finished MARK A1 workspace
(37 done, ordinal 38 partial); driver scenarios with `fake_claude` (which gains scenario
selection by `AI_RFC_FAKE_SCENARIO` and per-ordinal steps: two clusters complete; kill mid-session
then resume; budget stop; gate refusal halts with `--retry`; consolidation hook no-op; `next`
does one action); parity twins for every folded verb; `panther ai-rfc --help` equals
`ai-rfc --help`.

## Sub-projects and gates

| Sub-project | Content | Gate |
|---|---|---|
| **CLI-1 one door** (SP3 config + root, SP4 ledger, SP3 doctor) | `ai_rfc/config.py`, root `ai_rfc/cli.py`, `ai_rfc/ledger.py`, `init` (absorbs `prepare`'s scaffold/registers/references/digest), `status`, `verify`, `doctor`, `config example`, `toolchain provision\|verify` moved out of `experiment`, `run` for the deterministic stages, `panther ai-rfc` passthrough | MARK: `init` from a `recon.yaml`, `run` stops at mining with the ledger printed, `status`/`verify` agree with the old readers on the A1 copy |
| **CLI-2 autonomous driver** (SP2 driver + instrument split) | `ai_rfc/driver/*`, sessions inside `run`, `next`, stop policy, resumability, SP7c hook, `ai-rfc experiment …` over the shared launcher, fake_claude scenarios | a two-cluster MARK sweep completes and resumes after a kill; a budget stop reproduces the resume line |
| **CLI-3 one core** (SP3 folding, R2/R8 retirements) | the core calls APIs, grouped agent verbs, `AI_RFC_CONFIG` context, `ai_rfc` script/shim/prog retired, prompts/guard/parity/docs re-rendered, leaf verbs retired from the operator's help | parity twins byte-identical; no `ai_rfc` command remains in prompts or docs; a campaign runs end to end |

## Sequencing (D55) and coordination

SP1 (peer session, in progress) → SP7a → SP7b → CLI-1 → CLI-2 → CLI-3 → SP7c → SP7d. SP7c's plan
is written against `driver.sweep.next_round()`; SP7d's against `ai-rfc experiment`. The peer
roadmap's SP2/SP3/SP4 rows are satisfied by CLI-1..3; SP5 (docs site) consumes
`config.reference_markdown()` and the root's help; SP6 (PANTHER side) keeps the passthrough.
Working rules from the SP7a plan apply: shared worktree, `git status --short` before every commit,
per-repository commit formats, `docs/` needs `git add -f`, sandbox off for pytest and nested git.

## Risks

1. Ctrl-C orphaning a spending session until `driver/spawn.py` lands.
2. The ledger's strict "done": hand-made workspaces and the server's laxer counting show as partial until their entries and tags exist — intended honesty, but the first `status` on old workspaces will surprise.
3. Spend undercount: killed sessions report no result event; `status` labels spend a floor.
4. Three plans edit `experiment/{per_cluster,config,runner}.py` (SP7a Tasks 5–8, SP7c, CLI-2); whichever lands second re-anchors by symbol; CLI-2 moves them into `driver/`.
5. Prompt drift: sessions render from the sealed prompts and `run.json` notes drift; a deliberate prompt change needs a new `init` or an explicit `--reseal-prompts`.
6. Two run layouts coexist (campaign: workspace inside the run directory; production: runs inside the workspace); `fake_claude` and `metrics.window_clusters` depend on the former and gain the config-driven form.
