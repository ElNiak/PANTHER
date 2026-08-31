# Progressive RFC Reconstruction — Design

## Context

Goal: given an IUT/SUT and its git repository, reconstruct its specification *progressively* — cluster the history into an ordered timeline of PR clusters (and honest "epoch" clusters for direct pushes), emit one evidence folder per cluster (metadata, PR/MR discussions, diffs), and grow an RFC-style document revision by revision, where RFC v_i reflects the implementation state at cluster i. Claims stay evidentially honest through the existing `a_rfc` promotion rule; prose lives in an Internet-Draft scaffolded from `github.com/ElNiak/auto-i-d-template`; the model-driven layer becomes a claude-code plugin in a new nested submodule `ai_rfc`.

**Previous work this builds on** (all in `panther/plugins/services/testers/a_rfc/`, deliberately out-of-framework — no PluginType registration, no model calls, no network, file-on-disk handoffs):
- Manifest core: `models.py`, `schema.py` (strict, deterministic `load`/`dump`), `promotion.py` (`adjudicate` is the sole status authority; `violations` fire only on overstatement), `anchors.py` (`verify` — path-at-commit only; `line` never checked = documented gap #1), `report.py` (never reports what a claim *could* be promoted to = gap #2), `cli.py` (exit 0/1/2, stderr `_report` because `panther.*` loggers swallow warnings).
- `history/` subpackage: deterministic commit corpus (`commits.jsonl`: `sha,parents,author_name,author_email,authored_at,committed_at,subject,body,is_merge,file_count,files_recorded,files_truncated`; `files.jsonl`: `sha,path,status,previous_path`; `report.json`) + SQLite index with SHA-256 staleness refusal (the digest-guard pattern every new stage copies), `DEFAULT_FILE_CAP=1000`, shallow-clone refusal, byte-stable sorting. **Merge commits have zero file rows** (`git_log.py` passes `--no-merges` for the file pass) — PR file sets MUST be unions over member commits.
- Real data: MARK corpus (969 commits, 58 merges) and MARK clone (HEAD `b901f36095d746ee99dfa85b3d2ad1fbe5f2c533`) under `reconstructions/mark/`. The July 29 end-to-end run produced a 49-claim manifest and 5 confirmed defects (memory `handoff-2026-07-29-arfc-mark-demo`; those artifacts are LOST — only the memo survives).

## Decision register (settled with user — do not reopen)

| # | Decision |
|---|---|
| D1 | Extend `a_rfc` as-is: out-of-framework library + CLIs, stdlib+PyYAML only, no model calls; network ONLY in the isolated `forge/` stage |
| D2 | Layered PR sourcing: git heuristics always; optional forge fetch (GitHub + GitLab adapters) cached immutably to disk; downstream reads only the cache |
| D3 | Targets: MARK (gitlab.cylab.be/cylab/mark) then aioquic (github.com/aiortc/aioquic, 311 squash-merged PRs) |
| D4 | RFC form layered: per-cluster manifest checkpoints (deterministic, gated) + agent-written prose I-D citing claim ids |
| D5 | Orphan commits → synthetic **epoch** clusters; total ordered timeline, every commit exactly once |
| D6 | Views + checkpoints for ALL clusters; prose revisions only for spec-relevant clusters; explicit no-normative-change markers (with rationale) otherwise |
| D7 | Agentic layer = claude-code plugin (skills + commands + MCP server) |
| D8 | Author loop: YAML question register + interview transcripts → `interview` anchors + sign-offs (verbatim-confirmation rule) |
| D9 | Views hold metadata + forge evidence + unified diffs (span diff always; per-member patches opt-in, lands with P4); NO source snapshots |
| D10 | Targeted research done during planning; ARS deep-research pipeline as Phase R for the ICSE related-work |
| D11 | Prose draft = nested git repo scaffolded from `ElNiak/auto-i-d-template` (kramdown-rfc, Makefile, tag-driven -NN revisions); RFC v_i ↔ draft revision tags |
| D12 | Workspace = plain `--out` root (`corpus/`, `forge/`, `timeline/`, `clusters/`, `checkpoints/`, `questions.yaml`, `interviews/`) + nested `draft/` repo |
| D13 | Fix a_rfc gaps #1 (anchor line verification) + #2 (`supported` in reports); runtime-anchor adapter DEFERRED |
| D14 | Vertical slice first: MARK thin end-to-end before widening |
| D15 | Epochs stay maximal runs in v1; deterministic `--epoch-max` splitter only if practice demands (deferred) |
| D16 | Schema-validated claim writes live in the plugin core (one core, two frontends); `a_rfc` keeps its "nothing here writes a manifest" stance |
| D17 | Plugin repo = **git submodule `ai_rfc`** nested under `panther/plugins/services/testers/a_rfc/` (precedent: `panther_ivy` submodule) |
| D18 | Full roadmap authorized in sequence; return to user only on failures, genuine scope changes, and outward-facing actions |

Settled by architect (recorded; changeable before the relevant phase freezes them): citation marker = backticked `` `a_rfc:<claim-id>` `` in prose; forge fetch depth = PRs/MRs + reviews + comments/notes only; question export = markdown bundle only (server stays offline); plugin layout follows the marketplace-wrapper precedent.

## Architecture

```
                       PANTHER a_rfc (deterministic, no model calls)
repository ──► history/ ──► timeline/ ──► views/          draft/ (checkpoints + gates)
               corpus       clusters      evidence folders   ▲            ▲
                  ▲             ▲                            │            │
                  │         forge/ (ONLY networked stage; immutable snapshots; Phase P4)
                  │
        ai_rfc submodule (model-driven, OUTSIDE the framework boundary; Phases A–C)
        skills + commands + MCP server + `arfc` CLI — one core, two frontends
```

Boundary rule: `timeline/` and `views/` are **corpus-side** — they import nothing from the manifest core and re-parse JSONL themselves (accepted duplication, recorded in the README table). `draft/` is **manifest-side** — it imports `schema`/`promotion` from the parent package (same domain) but reads timeline artifacts only as files on disk. Every stage records SHA-256 digests of its inputs and refuses on mismatch.

### Timeline semantics

- Total order = **first-parent walk** from the corpus tip (tip = the unique commit appearing in no other commit's `parents`). Ordinals run root→tip, 1-based. Topological, never chronological (rebase makes `authored_at` non-monotonic).
- **PR cluster** = spine merge M (role `anchor`, last member) + branch members: BFS from `M.parents[1:]` over the corpus parent map, stopping at spine or already-assigned commits; branch members sorted by `(authored_at, sha)`, role `branch`. Nested merges become plain members (`nested_merge_count`). A parent sha absent from the corpus raises `TimelineError` (loud, never skipped).
- **Epoch** = maximal run of consecutive spine non-merge commits between PR clusters; members in spine order, role `spine`; anchor = first member.
- **Squash merges**: single spine commit; becomes a 1-member PR cluster ONLY via forge sha-match (P4). `(#N)` subject parse recorded as `subject_pr_hint`, NEVER clusters by itself. **Fast-forward merges**: invisible; forge rescue in P4 (`provenance: forge_ff`), else epoch.
- Cluster id `c<%04d ordinal>-<pr|epoch>-<12-hex anchor sha>`; `spine_prev_sha` = spine commit before the cluster's first spine element (None for root; downstream diffs against the empty tree `4b825dc642cb6eb9a060e54bf8d69288fbee4904`).
- Invariant (asserted + break-tested): members partition the corpus — every commit exactly once.

### Determinism rules

Patches via `git diff` (never `format-patch` — it embeds the git version): config/flags exactly `-c core.quotePath=true -c diff.algorithm=myers diff --no-color --no-ext-diff --no-textconv --no-renames --full-index --src-prefix=a/ --dst-prefix=b/ -U3 <base> <target> --`. `view.json` records `git_version` + per-patch SHA-256; `views --verify` re-emits and compares (drift = named failure, exit 3). Sort/tiebreaks: clusters by ordinal; members by (cluster ordinal, position); file_set by path; all JSON `sort_keys=True`. Forge snapshots (P4): dir `snapshot-<fetched_atZ>`, writer refuses existing dirs, consumers take explicit snapshot paths.

### CLI surface (all: required `--out`, stderr `_report`, exit 0/1/2)

| Command | Slice? |
|---|---|
| `python -m …a_rfc.history CLONE --out corpus/` | exists |
| `python -m …a_rfc.timeline CORPUS --out DIR [--repo CLONE]` | yes |
| `python -m …a_rfc.views TIMELINE --corpus DIR --repo CLONE --out DIR [--only ID] [--verify]` | yes |
| `python -m …a_rfc.draft checkpoint MANIFEST --timeline DIR --cluster ID --out DIR` | yes |
| `python -m …a_rfc.draft gate DRAFTREPO --timeline DIR --checkpoints DIR --questions FILE --out DIR [--strict]` | yes |
| `python -m …a_rfc.forge URL --repo CLONE --out DIR [--host github\|gitlab]` | P4 |

### ai_rfc submodule (Phases A–C; detailed plan written at Phase A)

Marketplace-wrapper layout at `a_rfc/ai_rfc/`: `.claude-plugin/marketplace.json`; `plugins/ai-rfc/` with `plugin.json`, `.mcp.json` (stdio server, env `PANTHER_REPO` + `ARFC_WORKSPACE`), skills (`arfc-reconstruction-loop`, `arfc-rfc-style`, `arfc-interviewing`, `arfc-evidence-hygiene`), commands (`/arfc-init`, `/arfc-next-cluster`, `/arfc-interview-import`, `/arfc-release-revision`, `/arfc-status`), `server/` (Python `mcp` SDK, **one core two frontends**: every MCP tool body calls `core/`; `cli.py` exposes identical `arfc <verb>` commands — AI+MCP vs AI+CLI arms capability-identical by construction, enforced by parity tests). Write tools: atomic temp+rename; `arfc_claim_upsert` **rejects any `status` input**; `arfc_answer_record` grants `signed_off_by` only on explicit exact-text confirmation; `arfc_revision_tag` preconditions = clean tree + strict gate 0 + citation gate 0. Draft build mechanics defer to auto-i-d-template's own CLAUDE.md (no duplication).

### Silent-failure traps → break-tests (house pattern)

1 `(#N)` squash misattribution (hint-only) · 2 member coverage hole/double-count (partition assertion) · 3 forge cache from different HEAD (P4) · 4 epoch off-by-one (spine concatenation property test) · 5 capped commits → incomplete file sets (`files_complete: false` + stderr) · 6 patch drift across git versions (digests + `--verify`) · 7 merge commits have zero file rows (union-over-members) · 8 stale checkpoint after manifest edit (re-hash) · 9 chronological ordering leak under rebase.

### Risks

1. Cross-git-version patch stability is empirical — digests + `--verify` convert drift into a named failure. 2. Forge restructuring changes cluster ids vs git-only timelines — fetch BEFORE checkpointing on aioquic. 3. Sign-off laundering via interviews — verbatim-confirmation + adjudication-only writes. 4. MARK's giant epochs — paginated reading + understatement (D15).

### Confirmation points (despite D18)

`gh repo create` for `ai_rfc` + first push + submodule URL wiring; first `gitlab.cylab.be` fetch (sandbox override); any deviation from the decision register.
