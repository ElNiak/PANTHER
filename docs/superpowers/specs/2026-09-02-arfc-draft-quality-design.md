# ai_rfc draft quality v2 — design (2026-09-02)

> Sub-project **SP7** of the roadmap in
> `docs/superpowers/specs/2026-09-02-ai-rfc-extraction-and-flow-design.md`. It executes after
> SP1 (extraction) on the new layout; its Phase 0 is SP0 (the provenance fixes), executed once.
> The design-level plan this spec records is `~/.claude/plans/explore-deeply-panther-and-rustling-token.md`
> (reviewed against the codebase on 2026-09-02; 1 Critical and 9 Warnings fixed in place).
> Execution plans: `docs/superpowers/plans/2026-09-03-arfc-draft-quality-sp7{a,b,c,d}.md`.

## Context

`ai_rfc` reconstructs a specification from a repository's history. The deterministic substrate
(`panther/plugins/services/testers/ai_rfc/`) builds a corpus, a PR/epoch timeline and
per-cluster evidence views, and gates claim manifests and prose drafts; the harness submodule
(`ai_rfc/harness/`) drives one `claude -p` session per cluster with 16 MCP tools mirrored 1:1
by CLI verbs.

Every draft the loop has produced — MARK (20k words, 365 citations) and the six aioquic pilot
drafts — has **zero figures, zero tables, no wire or message formats, no state machines, no
references, 83 % MUST**, an Introduction that narrates clusters, and has never been rendered
by kramdown-rfc/xml2rfc. Four causes, in order of leverage:

1. The round prompt constrains only front matter, boilerplate, keyword mapping and the citation
   token (`harness/experiment/prompts/*`, `plugins/ai-rfc/skills/ai-rfc-rfc-style/SKILL.md`).
2. The manifest has no notion of structure, field, message or state; the citation gate is a
   regex over the tagged draft checked for set membership (`draft/gate.py`).
3. The template is decorative: the scaffold copies the auto-i-d-template *library root* (no
   `Makefile`), the rfc-style skill points at a `CLAUDE.md` the scaffold deletes, and no arm can
   run `make`. None of kramdown-rfc, xml2rfc, idnits or aasvg is installed on the machine.
4. The instrument has no quality dimension (`experiment/metrics.py`).

Outcome wanted: drafts a reimplementer could use — generated, gate-verified structure blocks
(bit diagrams, field tables, state tables), cited free-form ASCII figures, real references, a
proper Internet-Draft skeleton, every revision compiled by the template toolchain — plus a
quality instrument (lint, ground truth, judge) so the improvement is measured, not asserted.

## Decision register

Decisions D1–D37 of the earlier specs stay in force except where a row below amends one.
The plan file numbers these decisions locally as D1–D15; the global numbers are used here.

### Decided with the user on 2026-09-02

| # (plan) | Decision | Consequence |
|---|---|---|
| D38 (D1) | The MARK campaign `~/ai-rfc-experiments/campaigns/mark-full-1` keeps running **from this worktree**. | Until `runs/A1/status.json` exists, only docs, execution plans and tests that import nothing new may touch the worktree; toolchain provisioning lives outside the repo and may start. Every substrate, server and driver file is LIVE (the driver's modules are cached only in the running process; a relaunch imports what is on disk). **Outcome:** the campaign finished on 2026-09-02 at 18:17 with 37 of 69 checkpoints, the budget exhausted at ordinal 38; the gate is open, and D50's sequencing is what remains. |
| D39 (D2) | The provenance-fix plan `2026-09-02-arfc-provenance-fix.md` is Phase 0 of this branch (= SP0). | Executed after a per-task landed-state check: at `21523d10c` its Task 1 has already landed, Tasks 2, 3 and 5 have not. |
| D40 (D3) | A `structures:` registry in the manifest: kinds `wire-format`, `message`, `record`, `enum`, `state-machine`; every field, value and transition is bound to a claim id that must exist. The substrate renders every block; the gate compares the tagged block byte-for-byte against the block frozen in the paired checkpoint. | Figure correctness reduces to claim correctness, which `promotion.adjudicate` already decides. No new evidence class: a figure is output, never evidence. |
| D41 (D4) | Free-form ASCII figures are allowed; the caption sentence cites the claims depicted; the figure must compile; an uncited figure is a lint finding. | Architecture and sequence overviews stay possible. |
| D42 (D5, amended) | Every new capability is ONE core function exposed as an `ai-rfc` verb and an MCP tool, landed with its `parity.md` row and `test_parity.py` twin. The raw arm C is frozen at today's surface. | Amends the three-arm parity requirement in light of D29/D31: the parity table records the arm-C delta; no raw-command slot rows, no enforcement-family change. |
| D43 (D6) | Rounds stay lean; a **consolidation round** runs every K clusters (`--consolidate-every`, default 10) and at sweep end as a `kind: consolidation` revision. | No in-session subagents; no two-pass clusters. The consolidation prompt rewrites the Introduction, moves cluster narration to a Change Log appendix, pastes rendered structure blocks, adds references and prunes implementation trivia ("move, never drop"). |
| D44 (D7) | Measurement on three axes: deterministic `draft lint` metrics; an aioquic ground-truth set for window w02-11 (HTTP/3-scoped, values from the pinned code, RFC sections recorded); an LLM-as-judge rubric (secondary, blinded, quote-verified). | A packet-format window is a follow-up campaign; the six pilot drafts are scored free as the old-instrument reference. |
| D45 (D8) | The draft repo becomes a real template adopter (`template/Makefile`, `.gitignore`, `.editorconfig`); `ID_TEMPLATE_HOME` points at ONE shared, pinned (`dcdd985a…`), pre-provisioned checkout under `AI_RFC_EXPERIMENTS_ROOT/tools/`. | `make txt html lint idnits` and `make diff` become real gates. The Docker image `ghcr.io/martinthomson/i-d-template-action` is the documented fallback (it clones upstream when no `Makefile` is present, so the `lib` mount keeps the pin). |
| D46 (D9) | Builds are offline: a per-target `references.yaml` allowlist is fetched once at `workspace prepare` into `<workspace>/refcache/`, sealed by the pristine digest; non-RFC references are inline in the front matter; an unknown reference is a build finding. | Amends nothing about `forge`; acquisition stays the only networked phase. |
| D47 (D10) | Evaluation order: free offline replay on a copy of the finished MARK A1 workspace → one paid consolidation on that copy (~$20) → aioquic w02-11 arm A ×2 under v2 (~$40–60) → packet-format window scan and campaign. | Each spend needs its own approval. |
| D48 (D11) | Consolidation rounds may author structures. They freeze a consolidation checkpoint under its own root `consolidations/<NN>/`, never under `checkpoints/`; its `requirements:` must be byte-identical to the predecessor checkpoint's, only `structures:` may differ. Cluster rounds may author structures too. | The four readers of `checkpoints/` (`gate.py:223`, `pipeline/state.py:228`, `completeness.py:80`, server `queries.py:71-75`) stay untouched. |
| D49 (D12) | The build gate is hard on every revision tag; `campaign init` refuses to start unless `toolchain verify` passes. | After init, a build failure is a content fault the agent gets two attempts to fix. |
| D50 (D14) | Sequencing: SP0 → SP1 → **SP7**; SP2–SP6 interleave as their owner decides. If SP4's ledger lands before consolidation scheduling, the scheduler consumes the ledger. | State is always derived from artifacts, never recorded. |
| D51 (D15) | The six harness-side provenance items belong to SP2 and are not re-planned here. This spec keeps one item nobody else names: the task-prompt freeze defect (`config.py:271-273` freezes a `task.md` no per-cluster session runs; `per_cluster.py:350` renders the source template; `runner.py:244-248` records a whole-window `prompt.md`). | |

### Settled from the code, not asked

| # (plan) | Decision |
|---|---|
| D52 (D13) | `level` becomes a closed enum {MUST, MUST NOT, SHOULD, SHOULD NOT, MAY}. Migration is zero everywhere except the aioquic pilot's run C1, which carries `level: descriptive` in its manifest and seven checkpoints; pilot workspaces are frozen evidence and never re-gated, so the enum stays five members and `draft lint --manifest` reports an unloadable manifest as a finding. `REVISION_TAG` stays two digits (the template's `id.mk`/`upload.mk` only see two; 69+7 fits; lint warns at 90). A consolidation recorded `normative_change: false` keeps every citation; dropping one is `true` with a note. Lint accepts legacy `a_rfc:` tokens, the gate does not. Build `--date` is the tag's commit date. A mid-sweep consolidation failure is recorded and the sweep continues; a failing sweep-end consolidation exits 1. A data-model claim outside any structure is a lint finding. |

## Architecture of a v2 round

```
cluster round (per_cluster.py)                      consolidation round (new, every K + end)
 1 cluster_next  2 cluster_get  3 claim_upsert        1 read revisions since last consolidation
 3b structure_upsert (when the cluster defines/      2 structure_upsert (cross-cluster structures)
    changes a format/record/enum/state machine)      3 draft render → paste blocks (delimited)
 4 lint anchors  5 record statuses + strict gate      4 editorial pass: abstract, Introduction,
 6 prose → owning section, keyword policy               regroup by concern, narration → App. A,
 7 checkpoint                                             trivia → App. B (move, never drop),
 8 revision_record → draft_commit → draft BUILD →         figures (caption cites), references
    revision_tag (manifest gate → tag → citation gate)  5 consolidation checkpoint (D48)
 9 citation gate  10 questions                        6 revision_record kind=consolidation →
                                                          commit → build → tag → citation gate
                                                       7 draft lint → 0
```

- **Structures** (`models.py`, `schema.py`): `structures: {id: {kind, title, section,
  fields | values | states + transitions}}`, each element carrying `claim: <id>`; ids match
  `[A-Za-z0-9][A-Za-z0-9_.:-]*` without `--`; `width` is an int ≥ 1 or `variable` (last field
  only); `from`/`to` ∈ `states`; every `claim` must exist in `requirements:`. `dump` emits
  `structures:` only when non-empty, so structure-free manifests stay byte-identical (golden
  test); `dump` sorts keys, so `structures:` serialises between `requirements` and `title`.
  A structure's stored and supported status is the minimum over its bound claims
  (`promotion.structure_statuses`), reported under "## Structures" in `report.md`.
- **Renderer** (`draft/structures.py`, new): one delimited kramdown block per structure. The
  delimiter is a kramdown block extension, which `kramdown-rfc` drops from the XML
  (`convert_comment` returns nothing; raw HTML comments would pass through, where `--` is
  illegal):

  ```
  {::comment}
  ai_rfc:struct:<id> begin
  {:/comment}
  …body…
  {::comment}
  ai_rfc:struct:<id> end
  {:/comment}
  ```

  Bodies: wire-format → `~~~` artwork with the 0..31 bit ruler (≤ 72 columns, deterministic
  spanning) plus a legend table `| Field | Bits | Description | Claim |`; message/record → a
  bold title line plus `| Field | Type | Size | Description | Claim |`; enum →
  `| Value | Name | Description | Claim |`; state-machine → `~~~` ladder boxes plus
  `| From | Event | Guard | To | Claim |`. Every row carries `` `ai_rfc:<claim-id>` `` so the
  existing citation regex counts it; tokens never sit inside artwork; `|` is escaped in cells;
  no trailing whitespace (the template's `lint-whitespace` refuses it).
- **Checkpoint** (`draft/checkpoint.py`): reads every input before `mkdir` (SP0 Task 3),
  writes `structures.md` and records `structures_sha256` when structures exist;
  `verify_checkpoint` compares it. `write_consolidation_checkpoint` writes
  `<workspace>/consolidations/<NN>/` with a `checkpoint.json` carrying `kind: consolidation`,
  `cluster_id`, `base_checkpoint`, `manifest_sha256`, `structures_sha256`, so
  `verify_checkpoint` applies unchanged.
- **Gate** (`draft/gate.py`): `RevisionEntry` gains `kind` (default `cluster`) and
  `checkpoint: consolidations/<NN>` (required for consolidations, forbidden otherwise);
  `run_gate` gains `consolidations_dir` (CLI `--consolidations`); one helper resolves each
  entry's checkpoint directory. New checks: **8** a consolidation entry names a consolidation
  checkpoint of the previous entry's cluster whose `requirements:` bytes equal the previous
  checkpoint's, computed on the fly (existing checkpoints record no such digest); **9** every
  delimited block at a tag names a structure in the paired `structures.md`; **10** the block
  body is byte-identical to the frozen block; **11** malformed delimiters are findings.
- **Build** (`draft/build.py`, new): clones the draft at the ref into a scratch directory, runs
  `make -f $T/main.mk LIBDIR=$T` with the targets `txt html lint idnits`, an offline environment
  (`KRAMDOWN_OFFLINE=1`, both refcache variables, `xml2rfc -N --cache`, a black-hole proxy,
  `DEFAULT_BRANCH=main BRANCH_FETCH=false`, `idnits=<abs> idnits_bin=`), and a PATH built from
  `toolchain.json` (the template's `.venv`, `.gems` and `node_modules` plus the Ruby, Node and
  make bin directories, which a session's PATH lacks). It parses both tools' diagnostics —
  kramdown-rfc's broken-reference stub is promoted to an error, xml2rfc's
  "Unable to resolve external request" is one already — and writes `build-report.json`.
- **Lint** (`draft/lint.py`, new): section presence (non-stub abstract, Introduction, Security
  and IANA considerations, non-empty references), BCP 14 keyword histogram and MUST fraction,
  figure/table/structure-block counts, uncited figures, cited and uncited claims, structures
  defined but unrendered or stale, data-model claims bound to no structure, an
  Introduction narration detector, both citation token spellings; `--strict` exits 3.
- **Harness**: four new MCP tools and `ai-rfc` verbs (`draft build`, `draft lint`,
  `draft render`, `structure upsert`), `revision record --kind`, `checkpoint --consolidation`;
  `revision_tag` gains a `draft_build` stage before `git tag`; a `record_revision` guardrail
  refuses a second cluster entry for one cluster; consolidation scheduling derived from disk
  (`consolidation.py`), with `cluster_artifacts`, `revision_of` and `partial_reason` filtering
  consolidation entries; the adopter scaffold, `toolchain provision|verify`, `references.yaml`,
  `workspace migrate-draft`; lint, judge and ground-truth results in `metrics.py`/`report.py`.
- **Prompts and skills**: `loop.tmpl.md` gains the structure step and the build-before-tag
  step; a `consolidation.tmpl.md` carries the editorial pass; `draft-skeleton.md` becomes a
  full Internet-Draft outline (Introduction with Scope/Method/Organization, Conventions with
  Terminology, Architecture Overview, Data Model and Structures, Protocol Operation,
  Configuration and Defaults, Error Handling, Observed Accidental Behaviour, Security
  Considerations, IANA Considerations; appendices Change Log, Implementation Notes, Open
  Questions, Acknowledgements). The rfc-style skill loses its dead `CLAUDE.md` instruction and
  gains a keyword policy (MUST needs enforcing evidence); new internal skills `ai-rfc-figures`,
  `ai-rfc-structures`, `ai-rfc-editorial`.

## Cross-plan constraints

- SP1 moves the substrate out of `panther/plugins/services/testers/ai_rfc/`, which the live
  campaign's MCP server imports (`paths.py:68-69`). **SP1 must also wait for
  `runs/A1/status.json`**; otherwise every later session fails with a surface shortfall and
  the driver halts.
- Two plans, one worktree, two sessions: `git log -1` and `git status --short` in both
  repositories before every task; re-anchor line numbers by symbol.
- Harness edits are submodule commits (`type: summary`, no scope); PANTHER commits are
  `type(scope): summary`. Push the submodule before the parent.

## Path translation for the post-SP1 layout

| Today | After SP1 |
|---|---|
| `panther/plugins/services/testers/ai_rfc/<x>.py` | `ai_rfc/<x>.py` in the ai_rfc repo, mounted as the single submodule at the same PANTHER path |
| `harness/plugins/ai-rfc/server/src/ai_rfc_server/…` | `ai_rfc/server/…` |
| `harness/experiment/…` | `ai_rfc/experiment/…` |
| `harness/plugins/ai-rfc/{skills,commands,.mcp.json}` | `plugins/ai-rfc/…` at the repo root |
| PANTHER `tests/unit/plugins/services/testers/ai_rfc/` | `tests/` in the ai_rfc repo (one suite, 769 baseline) |
| `python -m panther.plugins.services.testers.ai_rfc.draft <verb>` | `ai-rfc draft <verb>` |
| `PANTHER_REPO` | retired; `AI_RFC_WORKSPACE` (+ `AI_RFC_CONFIG` after SP3); `AI_RFC_TOOLCHAIN` is new |

## Roadmap placement

| Sub-project | Content | Gate |
|---|---|---|
| SP7a compile-and-lint | task-prompt freeze fix; toolchain provisioning and verify; adopter scaffold, references, `migrate-draft`; `draft build` and `draft lint` (without structure fields); their tools and verbs; the skeleton and skill rewrites | the template example builds twice byte-identically offline; the MARK A1 copy builds, lints and gates clean |
| SP7b structures | `Level` enum; revision `kind`/`checkpoint`; `structures:` schema, renderer, frozen `structures.md`, consolidation checkpoint, gate checks 8–11; `draft render`, `structure upsert`, `checkpoint --consolidation` | goldens per kind; a one-byte tamper is a finding |
| SP7c consolidation rounds | `loop.tmpl.md` steps, `consolidation.tmpl.md`, the `ai-rfc-editorial` skill, scheduling from disk, `campaign init --consolidate-every`, `run --task consolidation`, protocol docs | `_stub_spawn` sequence `c1,c2,cons,c3,cons(final)`, asserted on the prompt each session was launched with |
| SP7d instrument and runs | lint/build metrics in analysis; `experiment judge`; `experiment ground-truth` with `experiment/groundtruth/aioquic-w02-11.yaml`; the three evaluation runs | before/after table on the MARK copy, both sides re-linted by the final instrument; aioquic v2 compared with the pilot |

`ai-rfc-editorial` belongs to SP7c: SP7a Task 9 authors only `ai-rfc-rfc-style` and `ai-rfc-figures`,
while SP7c's `CONSOLIDATION_TEXTS` is the sole consumer of the editorial skill.

**SP7a Task 10's numbers are the SP7a waypoint, not SP7d's "before".** Task 10 lints with SP7a's
structure-less lint; SP7d's "after" uses the SP7b-extended lint. SP7d's replay therefore re-runs
the *final* lint on a fresh copy of the MARK A1 workspace so that both sides of the before/after
table are produced by one instrument, and the comparison measures content rather than instrument
drift. Task 10's own copy under `/tmp/claude` is disposable and is never SP7d's input.

## Settled by the judge probe (2026-09-03, `claude` 2.1.259)

The open item "`claude -p --tools \"\"` is unverified syntax" is closed. The syntax is real and
documented ("Use `\"\"` to disable all tools"), and the session's `init` event is the authority
on what the judge actually holds — never the model's self-report, which claimed tools it did not
have. Verified incantation, run from a working directory outside any project:

```
claude -p --tools "" --strict-mcp-config \
  --system-prompt "<rubric>" --exclude-dynamic-system-prompt-sections \
  --model <model> --output-format stream-json --verbose
```

`init` then reports `"tools":[]` and `"mcp_servers":[]` (both confirmed), and the project-specific
context disappears. `judge.py` must assert those two fields on the init event rather than trusting
the flags.

**D44's "blinded" is not fully achieved by these flags.** Two residual leaks, both measured:

- The user-global `~/.claude/CLAUDE.md` still loads. Only `--bare` removes CLAUDE.md
  auto-discovery — but `--bare` also skips keychain reads, so it fails with "Not logged in"
  unless `ANTHROPIC_API_KEY` is set in the environment (it is not, on this machine today).
  **A fully blinded judge therefore requires an API key, not the interactive OAuth session.**
  Until one is provisioned, the judge runs with the global CLAUDE.md in context; record that in
  the run manifest, since it is a scoring-relevant condition.
- `slash_commands` still lists the user's skills. With `tools:[]` there is no Skill tool to
  invoke them, so they are inert, but the names remain in the prompt.

A non-neutral working directory leaks the project through the path alone: the first probe named
"PANTHER" purely from its cwd string. Run the judge from a neutral directory.

**Decided 2026-09-03: accept the leak and record it.** SP7d's judge runs without `--bare`, with the
user-global `CLAUDE.md` in context, rather than waiting on an API key. The run manifest must
therefore carry the condition explicitly — alongside the model id, prompt templates, toolchain
versions and dataset digest — so a reader knows the scores were not produced under a fully blinded
harness. The judge stays secondary and quote-verified, which is what makes this tolerable; it is not
a substitute for the deterministic lint or the ground-truth set. If an `ANTHROPIC_API_KEY` is
provisioned later, switching to `--bare` is a one-line change and the manifest field records which
regime produced which scores.

## Settled by the toolchain run-and-see (2026-09-03)

Provisioned by hand under `~/ai-rfc-experiments/tools/` and recorded in `toolchain.json` there
(the `experiment toolchain provision|verify` commands of SP7a automate exactly this):

- **Ruby 4.0.1 runs kramdown-rfc 1.7.43**; no fallback needed. Bundler 4.0.3 installs the
  binstubs under `.gems/ruby/4.0.0/bin`, not the `.gems/bin` the template's PATH export
  expects, so `draft build` passes `kramdown-rfc=<binstub>` with `GEM_PATH`/`GEM_HOME` as
  make command-line variables (make exports those to recipes).
- xml2rfc 3.34.0 (plus iddiff, svgcheck, rfc-tidy, pyang) in the library venv; idnits 3.1.0
  and aasvg 0.5.7 via npm (`@ietf-tools/idnits` is on the registry).
- **Offline double build is byte-identical** with the network denied
  (`KRAMDOWN_OFFLINE=1`, `xml2rfc -N --cache`, a black-hole proxy, `-D 2026-08-26`), after one
  online seed build that cached all 17 allowlisted references.
- **The bcp14 boilerplate injects RFC 2119/8174 itself**: listing them in `normative:` produces
  a "both inline and in YAML header" warning. The skeleton must NOT list them.
- `XML2RFC_OPTS` must be passed in full on the make command line: a command-line variable
  silences `config.mk`'s `+= --cache=…`, so `--cache` is repeated explicitly. Never set `CI=true`.
- The `make idnits` target needs the draft committed in a clone (`build-targets.sh` reads
  `HEAD`); `draft build`'s scratch clone satisfies it. idnits reports kramdown-rfc's
  `<?line?>` instructions as a LINE_PI warning on unversioned XML.
- Apple GNU Make 3.81 sufficed. The template `Gemfile` pins nothing; the resolved
  `Gemfile.lock` is recorded beside `toolchain.json`.
