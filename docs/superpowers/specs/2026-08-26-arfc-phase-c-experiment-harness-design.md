# Phase C — AI+MCP vs AI+CLI Experiment Harness — Design

Companion to `2026-08-25-arfc-progressive-rfc-design.md` (decisions D1–D18 stay in force) and to the protocol at `ai_rfc/docs/experiment-protocol.md`. This document settles how the protocol is *executed*: the harness, the arm enforcement, the pristine workspace, the metrics, and the aioquic pilot.

## Context

Everything the 2026-08-25 spec scheduled has landed except Phase C: the deterministic `a_rfc` substrate (`history/`, `timeline/`, `views/`, `draft/`, `forge/`), the `ai_rfc` plugin (four skills, five commands, MCP server + parity `arfc` CLI, 25 tests; published at github.com/ElNiak/ai_rfc and wired as a submodule), MARK reconstructed end-to-end with both gates clean, aioquic's forge-informed 342-cluster timeline, and Phase R (the related-work report and the experiment protocol). Phase C is the experiment itself: three arms over one shared core, arm assignment enforced by removal/allowlist and audited, outcomes recomputed from substrate state, cost cache-adjusted.

Six things the protocol assumes do not exist yet:

1. The plugin is installed nowhere; `PANTHER_REPO`/`ARFC_WORKSPACE` are configured nowhere.
2. `arfc_revision_tag` was specified but never built; a draft commit/tag needs `git`, so the tool arm cannot be enforced by removing Bash.
3. The loop skill names all three surfaces in one text; the protocol needs per-arm prompts "identical modulo minimal invocation syntax" with a published diff.
4. aioquic has views for 1 of 342 clusters, no draft scaffold, no registers; its cluster 1 is a 508-commit epoch.
5. `claude --bare` (the hermetic mode) needs an API key that is not configured; without isolation every run loads the user's global hooks, plugins, `CLAUDE.md` and rules.
6. The protocol's primary outcome, the final `checked_fraction`, moves only through sign-offs and runtime anchors, so it is identically 0.0 in every model-only run.

## Decision register (settled with user — do not reopen)

| # | Decision |
|---|---|
| D19 | Next step = Phase C: harness + pilot. Housekeeping (LICENSE, `GITLAB_TOKEN` refetch, camera-ready obligations) deferred |
| D20 | Runs launch under the OAuth subscription inside an **isolated `CLAUDE_CONFIG_DIR` profile**, proven by spike S0 before any product code; `claude --bare` + `ANTHROPIC_API_KEY` is the documented fallback |
| D21 | Pilot matrix = aioquic ordinals **2–11** × arms **A/B/C** × **2 repeats**; run order = seeded shuffle inside each repeat block, frozen before launch |
| D22 | Model pin `claude-opus-5`, `--effort high` |
| D23 | Primary outcome = **state-verified per-cluster completion** (checkpoint ∧ revision entry ∧ tag when normative ∧ both strict gates 0 at run end), reported as completed/10 per run and pass^k over repeats; `checked_fraction` stays reported as the honesty metric; protocol §3 is amended to say so |
| D24 | **One whole-window session per run**; per-cluster tokens are attributed from cumulative stream-json usage at checkpoint tool-call events |
| D25 | Harness = a **custom runner over `claude -p`** as an `experiment/` package in the `ai_rfc` repo; stdlib + PyYAML; tests drive a fake `claude` shim — no network, no model |
| D26 | New core operations with MCP tool + CLI twin + parity row + parity test: `arfc_draft_commit(message)` / `arfc draft-commit`, `arfc_revision_tag(tag, message)` / `arfc revision-tag`; tag order = entry recorded → clean tree → strict manifest gate 0 → annotated tag → strict citation gate → **tag rolled back on findings** (exit 2) |
| D27 | Window mechanics = **pre-seeded checkpoints** for every out-of-window ordinal (1 and 12–342) from the empty manifest, each with a sidecar `harness.json`; no substrate artifact is mutated. The loop skill is **rendered from one template** (byte-equality test against the plugin's `SKILL.md`) into arm variants A/B/C with published diffs |
| D28 | Arm C gets `Bash(sqlite3 *)` as the raw affordance of the corpus index (disclosed in `parity.md`); runs root `~/arfc-experiments/` outside the PANTHER tree; `--disable-slash-commands`; arm prompt via `--append-system-prompt-file`. **Amended 2026-08-27:** the families are enforced by a `PreToolUse` guard, not by `--allowedTools`, which does not confine a built-in on 2.1.247 — without it arms B and C are capability-identical |

Settled by architect (changeable before the relevant task freezes them): `--max-budget-usd 25` and a 120-minute wall-clock cap per run; auto-i-d-template pinned at `dcdd985a86afad97a50f7b5e1b613f57c194b774` (its HEAD on 2026-08-26); draft name `draft-elniak-aioquic-reconstructed`; `rfc: AIOQUIC-RECON`; harness git identity `arfc-harness <arfc-harness@localhost>` set locally in the draft repo; campaign id `pilot-aioquic-w02-11-<YYYYMMDD>`.

## Verified mechanics the design rests on

| Fact | Where |
|---|---|
| The citation gate looks up a checkpoint for every **revision entry**; nothing iterates `checkpoints/` | `a_rfc/draft/gate.py:212-219` |
| Once an entry is recorded, the gate reports its tag "registered but absent" until the tag exists — so a tag tool must tag first, then gate | `a_rfc/draft/gate.py:183-195` |
| `cluster_next` treats any `checkpoints/<id>/` directory as processed, and any `revisions.yaml` entry's `cluster_id` | `ai_rfc_server/core/queries.py:63-88` |
| `requirements: {}` loads and checkpoints (zero claims iterate cleanly) — untested today | `a_rfc/schema.py:147-153`, `a_rfc/draft/checkpoint.py:79-99` |
| `checkpoint.json` = `adjudication{count_by_stored,count_by_supported,promotable_count,violation_count}, cluster_id, manifest_sha256, ordinal, prev_cluster_id, timeline_sha256`; `checked_fraction` is recomputable via `report.build(schema.load(<ckpt>/manifest.yaml), repo=clone)` | `a_rfc/draft/checkpoint.py:87-99`, `a_rfc/report.py:78-101` |
| Substrate guards key on content digests and `git rev-parse HEAD`, never on absolute paths → per-run copies are safe | `a_rfc/views/emit.py:63-85`, `a_rfc/history/index.py:104-135` |
| The loop skill's frontmatter grants `Bash(python -m …a_rfc*)`, `Bash(git *)`, `Bash(arfc *)` — a cross-arm permission leak if skills were loaded | `plugins/ai-rfc/skills/arfc-reconstruction-loop/SKILL.md:4` |
| Claude Code 2.1.246: `--tools` restricts the built-in set; `--allowedTools` + `-p` auto-denies everything else; `--append-system-prompt-file`, `--setting-sources project`, `--strict-mcp-config`, `--disable-slash-commands`, `--max-budget-usd` exist; there is no `--max-turns`; `--safe-mode` disables plugins and MCP wholesale (unusable); `total_cost_usd` is computed from a bundled price table regardless of auth | `claude --help`; code.claude.com/docs/en/cli-reference |
| **Corrected on 2.1.247 by spike S0 (2026-08-27):** `--allowedTools` auto-denies everything else **for MCP tools only**. It does *not* constrain a built-in that `--tools` has enabled, under any permission mode (`dontAsk` and `manual` both leak). Arm separation therefore rests on `--tools` (removal, proven for arm A) plus a `PreToolUse` guard for command families; deny rules enforce but are blacklists and cannot express an arm. A guard must exit **2** — the documented `permissionDecision: "deny"` JSON is ignored. `--setting-sources` takes `user,project,local`, so the arms' `project` excludes user settings and the guard is mounted with `--settings` | `ai_rfc/docs/spike-s0.md` |
| Undocumented, resolved by spike S0: `CLAUDE_CONFIG_DIR` credential resolution on macOS, `${PANTHER_REPO}`-style expansion in a plugin `.mcp.json`, the shape of permission denials in stream-json, whether `--tools` without `Skill` removes skill loading | — |

## Architecture

```
~/arfc-experiments/                                   (outside every CLAUDE.md ancestry)
├── profile/                 CLAUDE_CONFIG_DIR — logged in once, no user settings/plugins/hooks
├── pristine/aioquic-w02-11/ prepared workspace + pristine.sha256 + pristine.json
└── campaigns/<id>/          campaign.json · prompts/{arm-A,arm-B,arm-C,interactive}.md + diffs
    ├── bin/arfc             shim → <venv>/python -m ai_rfc_server.cli
    ├── runs/<A1..C2>/       workspace/ argv.json env.json prompt.md events.jsonl result.json stderr.log status.json
    ├── audit/<run>.json     surface classification, integrity, bypass attempts, error taxonomy
    └── analysis/            aggregate.json report.md

ai_rfc repo:  experiment/{config,workspace,arms,render,runner,matrix,audit,metrics,report,spike}.py
              plugins/ai-rfc/server/…/core/draft.py (+ tools.py, cli.py, parity)   ← product change
PANTHER:      a_rfc substrate unchanged except one new test (empty-manifest checkpoint)
```

The harness is model-driven orchestration and therefore lives **outside** PANTHER's framework boundary, in the `ai_rfc` repo beside the protocol it executes. Analysis is a pure function of on-disk artifacts: a reviewer with the campaign directory and the two repos re-derives every number with `python -m experiment analyze <campaign>`.

## §1 Product changes (`ai_rfc`; one test in `a_rfc`)

**Draft operations.** New `ai_rfc_server/core/draft.py`:

- `commit_draft(ctx, message) -> {commit, files}`: `git add -A` and `git commit -m` inside `$ARFC_WORKSPACE/draft`; a clean tree is a `CoreError` ("nothing to commit"), never a silent no-op.
- `tag_revision(ctx, tag, message) -> {exit_code, tag, commit?, stage?, findings, rolled_back}`, in this order: the tag must match the gate's `REVISION_TAG` pattern (`draft-<name>-NN`); `revisions.yaml` must already carry the entry (else `CoreError` "record the revision first"); the draft tree must be clean (`git status --porcelain` empty, else `CoreError`); the strict manifest gate must exit 0 (else return `exit_code: 2, stage: manifest_gate`); then `git tag -a TAG -m MESSAGE`; then the strict citation gate — on findings the tag is deleted and the result carries `exit_code: 2, stage: citation_gate, findings, rolled_back: true`. Exit codes are information, never bypassed.

Tools `arfc_draft_commit`, `arfc_revision_tag` (appended to `ALL_TOOLS`); verbs `arfc draft-commit -m MSG`, `arfc revision-tag TAG -m MSG` (exit code passed through); two rows in `docs/parity.md` (the existing `test_every_tool_is_in_the_parity_table` enforces them); parity twins run with pinned `GIT_AUTHOR_DATE`/`GIT_COMMITTER_DATE` and compare `git cat-file -p <tag>` bytes across the twin workspaces; refusal tests for dirty tree, missing entry, manifest-gate 2, and rollback on citation findings. `/arfc-release-revision` is rewritten to the same order (record entry → commit → tag → strict citation gate). Rationale: without these two operations arms A and B cannot finish a normative revision unless handed `Bash(git *)`, which defeats enforcement by removal in A and blurs B's command family.

**One template, four renderings.** `experiment/prompts/loop.tmpl.md` is the reconstruction loop with invocation slots (`{{op.cluster_next}}`, `{{op.cluster_get}}`, `{{op.corpus_query}}`, `{{op.claim_upsert}}`, `{{op.adjudicate}}`, `{{op.record_status}}`, `{{op.lint}}`, `{{op.checkpoint}}`, `{{op.revision_record}}`, `{{op.draft_commit}}`, `{{op.revision_tag}}`, `{{op.gate}}`, `{{op.citation_gate}}`, `{{op.question_draft}}`). `experiment/arms.py` holds the invocation tables: `interactive` (today's phrasing: prefer the MCP tools or `arfc` verbs, raw commands as fallback), `A` (tool names), `B` (`arfc` verbs), `C` (raw `python -m` commands, `git`, `sqlite3`). `python -m experiment render` writes the plugin's `SKILL.md` from `interactive`; a test asserts byte-equality, so the plugin text can only change through the template. `campaign init` renders `arm-A.md`/`arm-B.md`/`arm-C.md` = rendered loop + the arm-neutral `arfc-rfc-style`, `arfc-evidence-hygiene` and `claim-citation` texts verbatim (skills are unreachable in hermetic runs, so their content ships in the appended prompt identically for every arm), emits `diff-A-B.patch`, `diff-A-C.patch`, `diff-B-C.patch`, and records sha256s in `campaign.json`. The diffs are publishable artifacts.

**`.mcp.json`.** Spike S0 checks whether `${PANTHER_REPO}`/`${ARFC_WORKSPACE}` expand in a plugin `.mcp.json`. If not, the `env` block is dropped so the server inherits the environment (a product fix; the harness never depends on it because it renders an explicit `--mcp-config`).

**`a_rfc`.** One test: `draft checkpoint` on a manifest with `requirements: {}` writes `manifest.yaml` + `checkpoint.json` with zero counts.

## §2 Hermetic profile and per-arm enforcement

**Profile.** `python -m experiment profile init --root ~/arfc-experiments` creates `profile/`; the user logs in there once (`CLAUDE_CONFIG_DIR=~/arfc-experiments/profile claude auth login` — Keychain entries are per config dir). Sessions run with `--setting-sources project` and cwd = the run workspace under the runs root, so no `CLAUDE.md`/`.claude/rules` ancestry exists. Constant flags for every arm:

```
claude -p <task prompt> --output-format stream-json --verbose
  --append-system-prompt-file <campaign>/prompts/arm-X.md
  --disable-slash-commands --setting-sources project
  --model claude-opus-5 --effort high --permission-mode dontAsk
  --max-budget-usd 25
```

plus a 120-minute wall-clock cap enforced by the runner. Session persistence stays on inside the isolated profile (a backup transcript beside `events.jsonl`).

| Arm | `--tools` | `--allowedTools` | Guard families (`--settings`) | MCP |
|---|---|---|---|---|
| A | `Read,Edit,Write,Grep,Glob` (Bash absent) | `Read Edit Write Grep Glob mcp__arfc` | — (no Bash to confine) | `--mcp-config <campaign>/arfc.json --strict-mcp-config` |
| B | `Read,Edit,Write,Grep,Glob,Bash` | those five + `"Bash(arfc *)"` | `arfc ` | `--strict-mcp-config`, no config |
| C | `Read,Edit,Write,Grep,Glob,Bash` | those five + `"Bash(python -m panther.plugins.services.testers.a_rfc*)" "Bash(git *)" "Bash(sqlite3 *)"` | `python -m panther…a_rfc`, `git `, `sqlite3 ` | `--strict-mcp-config`, no config |

**The `--allowedTools` column is normative for MCP tools only** (measured on 2.1.247;
see the fact table). Bash confinement is the guard column: the families are *derived*
from the `Bash(...)` entries beside them by `experiment.enforcement.bash_families`, so
the two columns cannot drift. The guard (`experiment/guard.py`) is mounted per arm via
`--settings` from the campaign directory — never from `ARFC_WORKSPACE`, which arms B
and C can write — and exits 2 on anything outside its families. It fails closed on
command substitution and checks every `&&`/`||`/`;`/`|`-separated segment, so
`arfc status && echo x` is refused.

`arfc.json` is rendered per campaign with absolute paths (`<venv>/python`, the server `src` dir, `PANTHER_REPO`, and `ARFC_WORKSPACE` substituted per run). `arfc` reaches PATH through `<campaign>/bin/arfc` (a two-line shim over `<venv>/python -m ai_rfc_server.cli`); PANTHER imports through the master `.venv` editable install; both are recorded in `campaign.json`. Prose editing is `Edit`/`Write` in every arm; commit/tag is `arfc_*` tools in A, `arfc` verbs in B, `git` in C. Anything outside an arm's guard families is refused and captured as bypass-attempt data, readable from the errored `tool_result`, the result event's `permission_denials`, or the `hook_started`/`hook_response` pair. `sqlite3` in C is the raw affordance of `corpus/index.sqlite` (the index is derived and disposable; a write through it is detected by nothing and disclosed as such).

**Spike S0** (`python -m experiment spike --root ~/arfc-experiments`, writes `spike-report.json`; go/no-go before any product code):

1. A trivial `-p` run authenticates in the profile (init event / result present, no auth error).
2. `--include-hook-events` on a run that executes one Bash call shows no user hook firing (the same run without isolation shows the ARS SessionStart hook — the positive control).
3. A codeword `CLAUDE.md` placed above a temp cwd leaks into a run from that cwd (positive control) and does not leak from the runs root.
4. The init event's `tools`, `mcp_servers`, `slash_commands` match each arm's spec exactly.
5. `git commit` inside a scaffolded `draft/` succeeds in-session (no sandbox settings present).
6. `--plugin-dir plugins/ai-rfc` with the two env vars exported yields `arfc` connected; unset, it fails — this decides the `.mcp.json` question. *(Answered: it connects **either way**, so the env block is not load-bearing. Note the server can still read `pending` at init, a startup race in `-p`; arm A mounts via `--mcp-config`, which is unaffected.)*
7. The `result` event carries `total_cost_usd`, `usage`, `modelUsage`, `permission_denials`; their exact shapes become the test fixtures.
8. The arm's guard denies `arfc status && echo x` and the denial is visible in the stream. *(Answered: `--allowedTools` alone does **not** deny it — see the fact table. The `PreToolUse` guard does, and only via exit 2.)*
9. `--append-system-prompt-file` is accepted and its content is visible to the model (canary echo).

Fallback if 1–3 fail: `--bare` + `ANTHROPIC_API_KEY`, documented in the campaign and the paper.

## §3 Pristine workspace and the window

`python -m experiment workspace prepare aioquic --root ~/arfc-experiments` builds `pristine/aioquic-w02-11/`:

1. Copy `clone/`, `corpus/` (including `index.sqlite`), `forge/github.com__aiortc__aioquic/snapshot-2026-08-25T15-16-59Z/`, `timeline/` from `reconstructions/aioquic/`; record `git rev-parse HEAD` of the clone (`6d36838d008c2202c337142fa07e8bf80e96bac8`).
2. Emit views for all 342 clusters with `--forge <snapshot>`; run `--verify` once (exit 0 required).
3. Write `manifest.yaml` (`rfc: AIOQUIC-RECON`, `title`, `requirements: {}`), `questions.yaml` (`questions: {}`), `revisions.yaml` (`revisions: {}`), `interviews/`.
4. Scaffold `draft/` from `ElNiak/auto-i-d-template` at the pinned commit: remove its `.git`, `git init -b main`, delete the `draft-*` rule from the root `.gitignore`, strip the template's own `.claude/`, `CLAUDE.md`, `.claude-plugin/` and any `.mcp*.json` (recorded in `pristine.json`), set the local identity, create `draft-elniak-aioquic-reconstructed.md` with real front matter (`docname: draft-elniak-aioquic-reconstructed-latest`, `category: info`, BCP 14 boilerplate, empty middle), commit "scaffold" with a pinned date.
5. Pre-seed checkpoints from the empty manifest for `c0001-epoch-a80c3bdd1e02` and for ordinals 12–342 (`c0012-pr-2fe6a3623f9e` … `c0342-pr-6d36838d008c`) through `draft.checkpoint.write_checkpoint`; beside each, `harness.json` = `{"pre_seeded": true, "reason": "outside window", "window": [2, 11]}`. Consequence in every arm: `cluster_next` (and the raw rule "lowest ordinal without checkpoint or revision") walks exactly `c0002-pr-60258445de47` … `c0011-epoch-d290ebea69fd`, then reports none; the citation gate never sees these checkpoints because it only looks up checkpoints from revision entries.
6. Write `pristine.sha256` (sorted `<sha256>  <relative path>` over every regular file except `**/.git/**`) and `pristine.json` (template commit, clone HEAD, draft HEAD, strip list, window, tool versions).

Per run, the runner `copytree`s the pristine tree into `runs/<id>/workspace/` and re-verifies `pristine.sha256` plus both HEADs before launch. Truncating `clusters.jsonl` was considered and rejected: it mutates a stage output and leaves `timeline.json.cluster_count` inconsistent. `arfc status` will read "332 of 342 processed" at start; the task prompt says why.

## §4 Runner and run matrix

`python -m experiment campaign init --root … --id pilot-aioquic-w02-11-<date> --seed 20260826` writes `campaign.json`: target, window, arms, repeats, seed, model/effort, `claude --version`, profile path, budget/timeout, pristine digest, prompt digests + diff paths, venv/shim paths, `git describe --always --dirty` of PANTHER and `ai_rfc`, and the **pre-run parity-suite result**. Run ids are `A1 B1 C1 A2 B2 C2`; order = for each repeat block, `random.Random(seed + block).shuffle([A, B, C])`, concatenated and frozen in `campaign.json`.

`python -m experiment run <campaign>` executes runs in the frozen order. Per run: copy + verify the workspace; write `argv.json`, `env.json` (values redacted to presence for anything not in the allowlist below), `prompt.md`; launch with stdin closed, stdout streamed line-by-line into `events.jsonl`, stderr into `stderr.log`; the final `type: result` event is also written as `result.json`; `status.json` = `{run_id, arm, repeat, started_at, finished_at, exit_code, timed_out, budget_hit, claude_version}`. Environment = exactly `CLAUDE_CONFIG_DIR`, `PANTHER_REPO` (the PANTHER checkout root), `ARFC_WORKSPACE` (`runs/<id>/workspace`), `PATH` (`<campaign>/bin:<venv>/bin:/usr/bin:/bin`), `HOME`, `LANG`; nothing else is inherited. Timeout: SIGTERM, then SIGKILL after 30 s, both recorded. The task prompt (`experiment/prompts/task.md`, identical across arms) states the window in words, that out-of-window clusters are pre-marked processed by the harness, that each cluster gets one full loop iteration ending with both gates at exit 0, that the run ends when the next cluster is none, and that the model must never ask the user anything. Resume skips runs whose `status.json` is complete; a failed or interrupted run is never retried in place — a retry is a new run id (`A1r2`), reported separately.

## §5 Audit, metrics, report

**Audit** (`python -m experiment audit <campaign>`, one JSON per run) reads `events.jsonl` and classifies every `tool_use`: `mcp__arfc__*` (class-1 surface); `Bash` by command family (`arfc …`, `python -m panther.plugins.services.testers.a_rfc…`, `git …`, `sqlite3 …`, other); `Edit`/`Write` by target (`draft/*.md` prose; hand-edits of `manifest.yaml`/`questions.yaml`/`revisions.yaml`; other); `Read`/`Grep`/`Glob`. Definitions:

- *Integrity violation*: an **executed** call on a surface outside the run's arm (impossible by construction; still checked). `integrity_rate(arm)` = runs with zero violations / runs.
- *Bypass attempt*: a **denied** call, taxonomized by the surface it reached for (MCP-in-CLI-arm, Bash-in-MCP-arm, out-of-family Bash, disallowed built-in). Counted from denial records in the stream and from `result.permission_denials`.
- *Error taxonomy*: class-1 channel = MCP tool errors (guardrail, core, schema, non-zero `exit_code` payloads); class-2 channel = Bash non-zero exits, argparse usage errors, wrong flags; `first_failure` = index and elapsed time of the first error of either channel.
- *Hand-edit asymmetry*: count of manifest/register hand-edits per arm (the measured asymmetry `parity.md` names).

**Analysis** (`python -m experiment analyze <campaign>`) is a pure, idempotent function of `runs/*/workspace/`, `events.jsonl`, `result.json`:

- Per cluster `c` in the window: `artifacts(c)` = checkpoint present without `harness.json` ∧ revision entry with `cluster_id = c` ∧ (`normative_change: false` ∨ the entry's tag exists in `draft/`). Per run: `gates_clean` = the harness itself re-runs the strict manifest gate and the strict citation gate on the final workspace through `ai_rfc_server.core.gates`, both exit 0. `completed(c) = artifacts(c) ∧ gates_clean`. Both `artifacts_fraction` and `completed_fraction` (= primary, completed/10) are reported so the gate's effect is visible.
- Reliability: `pass^k(c)` = completed in every repeat; per arm the mean and minimum over clusters; run-to-run variance of `completed_fraction`.
- Claims: per checkpoint in the window, `report.build(schema.load(<ckpt>/manifest.yaml), repo=clone)` → counts by supported status, unverified anchors, `checked_fraction_by_req_class` (reported as the honesty metric, expected 0.0).
- Cost: `total_cost_usd`, `usage` token classes, `modelUsage`, `duration_ms`, `duration_api_ms`, `num_turns` from `result.json`; `failure_cost_share(arm)` = Σ cost of runs with zero completed clusters / Σ cost of the arm's runs; cost per completed cluster.
- Trajectory: walking assistant messages, cumulate `usage` (input + cache_creation + cache_read + output) and record it at each checkpoint call (`arfc_checkpoint` tool in A, `arfc checkpoint` in B, `…a_rfc.draft checkpoint` in C); tokens-to-first-completion; per-cluster token deltas; `trajectory_auc` = trapezoid integral of completed-fraction against cumulative cost normalized to the run's total.
- Compaction events and API errors in the stream are counted and reported per run.

Output: `analysis/aggregate.json` (every number with its inputs) and `analysis/report.md` (tables per arm and per cluster, formulas named).

## §6 Testing

- `a_rfc` (PANTHER): the empty-manifest checkpoint test.
- Server: refusal and rollback tests for `commit_draft`/`tag_revision`; parity twins with pinned dates; the two `parity.md` rows.
- `experiment/tests/`: a fake `claude` executable (`tests/fake_claude/claude`, Python) is put first on PATH; it reads a scenario name from `FAKE_CLAUDE_SCENARIO`, replays a stream-json fixture (captured from spike S0 and hand-reduced), performs scripted workspace mutations through the real substrate (e.g. checkpoint `c0002…` on the fixture workspace), and exits with the scenario's code — including a `hang` scenario for the timeout path. Covered: runner capture/timeout/status, matrix ordering determinism from the seed, audit classification (fixtures include a denied Bash call in arm A and an MCP call in arm B), metrics recompute on a fixture workspace (the conftest `_build_workspace` moves to `ai_rfc_server/testing.py` for reuse), render byte-equality, pristine-digest tamper detection, resume-by-skip. No network, no model.
- Lint/format per each repo's conventions; the parity suite runs before and after the pilot (protocol stop-ship rule).

## §7 Pilot procedure and deliverables

Order: S0 spike (go/no-go) → §1 product changes (nested-repo commits, PANTHER submodule bump) → §3 workspace prepare → `campaign init` (prompt freeze, parity pre-run) → six runs in the background under a Monitor, interleaved per the frozen order → `audit` + `analyze` → deliverables. Committed to `ai_rfc`: `docs/experiments/<run-date>-pilot-aioquic.md` (commands, per-run cost and wall time, completion and pass^k, integrity rates, bypass taxonomy, first-failure timings, what broke and what the main run must change), a copy of `analysis/aggregate.json`, the prompt diffs, the `docs/experiment-protocol.md` §3 amendment (D23), and the preregistration checklist pre-filled with pilot-derived numbers. Run artifacts stay under `~/arfc-experiments/<campaign>/`.

Out of scope, tracked for later: the MARK pilot, the preregistered main run, the `ai_rfc` LICENSE, the MARK `GITLAB_TOKEN` refetch, camera-ready obligations.

## Risks

1. OAuth may not resolve in an isolated profile → spike item 1; fallback `--bare` + API key.
2. ~~`--tools` may not remove Bash/Skill the way the help text implies → spike item 4 decides; allowlist-only enforcement is the degraded mode and is disclosed.~~ **Resolved 2026-08-27, inverted.** `--tools` does remove Bash (arm A verified). It is the *allowlist* that fails to confine a built-in, so "allowlist-only" was never an available degraded mode. Enforcement is `--tools` plus the `PreToolUse` guard; the residual risk is that arms B and C could edit the guard's settings file, detected by hashing it per run and by the absence of `hook_started` events.
3. Stream-json field names (`permission_denials`, denial records) are undocumented → spike item 7/8 captures the truth as fixtures.
4. Subscription rate limits and time-varying API conditions → interleaved order; retries as new run ids; API errors counted.
5. The 508-commit cluster 1 is excluded → external-validity note in the report.
6. Long single sessions may auto-compact → compaction events counted per run and reported.
7. Arm C's `git *` can move `clone/` HEAD and trip the digest guard → contained by per-run copies, classified as an environment failure.
8. Wall time: six runs × up to two hours, sequential.

## Confirmation points (despite D18)

The user's one-time `claude auth login` inside the profile; the first real-model launch (subscription spend and time); dropping the `env` block from `.mcp.json` if spike item 6 says expansion is unsupported; the wording of the protocol §3 amendment; pushing `ai_rfc` commits to github.com/ElNiak/ai_rfc.
