# ai_rfc Plugin (Phases A+B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The model-driven layer as a claude-code plugin in a nested git repo at `panther/plugins/services/testers/a_rfc/ai_rfc/` (submodule-to-be, D17): four skills + five commands driving the substrate CLIs (Phase A), then an MCP server + parity `arfc` CLI over one shared core (Phase B, D16) so the AI+MCP and AI+CLI experiment arms are capability-identical by construction.

**Architecture:** Marketplace-wrapper layout (panther-ivy-plugin precedent). The server reaches PANTHER as a library via `PANTHER_REPO` on `sys.path` (pure manifest ops import `a_rfc` modules; stage runs shell out to the `python -m …a_rfc.*` CLIs). All write operations are atomic temp+rename; `claim_upsert` rejects any `status` input — adjudication is the only status authority; `answer_record` grants `signed_off_by` only on explicit exact-text confirmation.

**Tech Stack:** Skills/commands per `.claude/rules/skill-conventions.md` (flat-with-prefix names, CSO descriptions <250 chars, `allowed-tools` restricted, knowledge skills `user-invocable: false`, bodies <300 lines, heavy material in `references/`). Server: Python ≥3.10, deps `mcp` + `pyyaml` only, src layout, pytest.

**Spec:** `docs/superpowers/specs/2026-08-25-arfc-progressive-rfc-design.md` (ai_rfc section) + the vertical-slice and forge RUN.md records.

## Global Constraints

- The nested repo is **its own git repo** — commits inside it use its own history (`feat: …` style, no `(a_rfc)` scope); NOTHING under `ai_rfc/` is ever committed to PANTHER until the submodule wiring lands (confirmation batch). PANTHER-side: add `plugins/services/testers/a_rfc/ai_rfc/**` to `[tool.setuptools.exclude-package-data]` and extend flake8/lint excludes mirroring `panther_ivy`.
- Env contract everywhere: `PANTHER_REPO` = PANTHER checkout root; `ARFC_WORKSPACE` = one reconstruction workspace (layout per D12). Both required; fail loudly when absent.
- The token discipline, no-network-in-tests, and stderr conventions carry over from the substrate.
- Outward actions (gh repo create, push, `.gitmodules`, MARK GitLab fetch) happen ONLY in the final confirmation batch.

### Workspace layout contract (what every skill/command/tool assumes)

```
$ARFC_WORKSPACE/
├── clone/  corpus/  forge/<host>__<o>__<r>/snapshot-*/  timeline/  clusters/
├── checkpoints/<cluster-id>/{manifest.yaml,checkpoint.json}
├── manifest.yaml  questions.yaml  revisions.yaml  interviews/int-NNN.md
├── draft/          # nested repo scaffolded from ElNiak/auto-i-d-template
└── out/            # reports + gate-report.json
```

---

### Task A1: Repo scaffold + manifest + marketplace

Create `ai_rfc/` (git init -b main inside it), `.claude-plugin/marketplace.json` (one plugin entry pointing at `plugins/ai-rfc`), `plugins/ai-rfc/.claude-plugin/plugin.json` (`name: "ai-rfc"`, version 0.1.0, description, author ElNiak), `plugins/ai-rfc/.mcp.json` (`"arfc"`: stdio, `command: "uv"`, args running the server package via `${CLAUDE_PLUGIN_ROOT}/server` — Phase B fills the real entry; A ships it commented-out-by-absence: file added in B), `README.md` (what the plugin is, env contract, install line `claude plugin marketplace add <path>`), `.gitignore` (venv, __pycache__, dist). PANTHER side: pyproject exclude-package-data entry. Commit both repos (PANTHER commit touches only pyproject.toml).

### Task A2: `arfc-evidence-hygiene` skill (knowledge, `user-invocable: false`)

Required content (each a section): never write `status` — omission is safe, adjudication decides (`promotion.adjudicate` is the single authority; overstatement is a violation, understatement always permitted); anchor discipline (pin to corpus commits never HEAD; `line` + `line_sha256` make citations verifiable; commit-less code/runtime anchors are refused); why interview+paper stays `inferred` (same-person circularity — the two-class route needs a primary artefact); `checked_fraction_by_req_class` is the honesty metric and 0.0 is expected early; the four silent-failure traps in one table. Source of truth to cite: `panther/plugins/services/testers/a_rfc/README.md`.

### Task A3: `arfc-rfc-style` skill (+ `references/claim-citation.md`)

Sections: I-D structure per the auto-i-d-template (front matter, `--- middle`, RFC 2119 boilerplate `{::boilerplate bcp14-tagged}`); mapping claim `level` → 2119 keywords in prose; **accidental claims never become normative prose** — they live in a descriptive section; the citation convention (backticked `` `a_rfc:<claim-id>` `` tokens, one per normative statement; the gate verifies them against the paired checkpoint) with the worked MARK example; revision discipline (tag `draft-<name>-NN` annotated, `revisions.yaml` entry with `normative_change` + note, `-NN` monotone in cluster ordinal); defer ALL build mechanics (`make`, lint, idnits, upload) to the template's own CLAUDE.md; warn off the template's speckit commands. `references/claim-citation.md`: the regex, dos/don'ts, the no-change rule (citation set must not change when `normative_change: false`).

### Task A4: `arfc-reconstruction-loop` skill (the driver)

Sections: preconditions (env vars set; workspace layout present; timeline built — with `--forge` when a snapshot exists, ALWAYS before any checkpoint); the per-cluster loop as a numbered procedure — next unprocessed cluster (lowest ordinal without a checkpoint or revision entry) → read evidence (`view.json`, `span.diff`, `evidence/pr.json`, corpus queries via `history.index.open_index` churn ranking) → propose/update claims in `manifest.yaml` (through `arfc claim-upsert` when Phase B lands; hand-edit + linter until then), anchors pinned, NO status → run linter mode (`python -m …a_rfc <manifest> --out … --repo …`), fix unverified anchors → record supported statuses from the report's `claims` payload → decide spec-relevance: update draft prose citing claim ids, or record a `normative_change: false` revision with a one-line rationale → `draft checkpoint` → strict gate + citation gate exit 0 → tag → advance; failure-recovery table (strict exit 2 = the system working — fix anchors first, never bypass; `StaleIndexError` = rebuild, never migrate; citation-gate finding = reconcile prose or claims, never delete a claim to silence it; giant epoch = paginated reading + understatement). `allowed-tools`: Read, Grep, Glob, Edit, Write, `Bash(python -m panther.plugins.services.testers.a_rfc*)`, `Bash(git *)`.

### Task A5: `arfc-interviewing` skill

Sections: when to draft a question (a claim capped at gap/inferred that blocks a section); question quality rules (one behaviour per question, carries the claim text **verbatim**, answerable with yes/no/correction); the register round-trip (append to `questions.yaml` open → export markdown bundle for email/issue → reply saved as `interviews/int-NNN.md` dated+attributed → per answered id: `interview` anchor (`locator: int-NNN`) on the claim, register entry answered) ; the sign-off rule: `signed_off_by` ONLY when the author explicitly confirmed the exact claim wording — a paraphrase gets the anchor, not the sign-off (this is the circularity defense; relaxing it makes `checked_fraction` meaningless); re-adjudicate + re-gate after every import.

### Task A6: The five commands

Each a `commands/*.md` with frontmatter description + steps that name exact CLIs: `arfc-init` (validate env vars; clone at full depth — shallow is refused; history → forge (token via env, GitLab live fetch requires user confirmation) → timeline `--forge` → views; scaffold draft from ElNiak/auto-i-d-template **dropping the root `.gitignore` `draft-*` rule**; empty questions/revisions); `arfc-next-cluster` (one loop iteration per the loop skill); `arfc-interview-import <transcript>`; `arfc-release-revision` (strict manifest gate 0 + citation gate 0 + clean draft tree ⇒ annotated tag + revisions entry); `arfc-status` (counts from report.json, open questions, last checkpoint ordinal, `git describe` in draft). Commit Phase A in the nested repo.

### Task B1: Server package + core (workspace, claims, questions, revisions, queries)

`server/pyproject.toml` (name `ai-rfc-server`, `[project.scripts] arfc = "ai_rfc_server.cli:main"`, deps `mcp>=1.0`, `pyyaml`); `src/ai_rfc_server/paths.py` (env resolution, `sys.path` insertion of `PANTHER_REPO`, loud `EnvError`); `core/claims.py`: `upsert_claim(workspace, claim_id, fields) -> None` (schema round-trip via a_rfc `schema.load/dump`, REJECTS `status` in fields, atomic temp+rename), `adjudicate_preview(workspace) -> list[{id, stored, supported, promotable}]`, `record_statuses(workspace, ids|all) -> None` (writes exactly `supported`); `core/questions.py`: `draft_question`, `export_open`, `record_answer` (transcript path + verbatim quote required; `signed_off_by` only with `author_confirmed_exact_text=True`); `core/revisions.py`: `record_revision(tag, cluster_id, normative_change, note)` (computes checkpoint sha from disk); `core/queries.py`: `corpus_query(sql)` SELECT-only allowlist over `history.index.open_index`, row cap 200, `StaleIndexError` surfaced verbatim; `cluster_get(cluster_id, page)` (view.json + capped patch bytes), `cluster_next()`; `core/gates.py`: `run_manifest_gate(strict)`, `run_citation_gate(strict)`, `write_checkpoint(cluster_id)` — subprocess `sys.executable -m panther...` with `cwd=PANTHER_REPO`. Tests: fixture workspace built by the substrate's own code (reuse the vertical-slice fixture recipe); every rule above break-tested (status rejected; sign-off refused without the flag; SELECT-only; atomic write leaves no partial file on injected failure).

### Task B2: `arfc` CLI frontend

`cli.py`: argparse verbs mapping 1:1 onto core functions (`status`, `corpus-query`, `cluster-get`, `cluster-next`, `claim-upsert` (fields as `--field key=value` pairs + `--text/--section/...` for the base four), `claim-adjudicate`, `claim-record-status`, `question-draft`, `question-export`, `answer-record`, `revision-record`, `checkpoint`, `gate`, `citation-gate`). Output: JSON to stdout (machine-readable), diagnostics to stderr, exit codes 0/1/2 mirroring the substrate. Tests: every verb on the fixture workspace.

### Task B3: MCP server frontend + parity

`server.py`: `mcp.server.fastmcp.FastMCP("arfc")`; one `@mcp.tool()` per core function with docstrings as tool descriptions; identical names to the parity table (`arfc_claim_upsert` ↔ `arfc claim-upsert`). `docs/parity.md`: three-column table (MCP tool | `arfc` verb | raw substrate command when one exists). Parity tests: for each write op, run tool-path and CLI-path on twin fixture workspaces → byte-identical resulting files; for reads → identical JSON. Fill `plugins/ai-rfc/.mcp.json` with the real stdio entry. Update the four skills to name the tools/verbs as the preferred interface (Bash raw CLIs stay the documented fallback = the AI+CLI arm).

### Task B4: Wrap

Nested-repo README (tool table, env contract, experiment framing); run the server test suite; a live smoke against `reconstructions/mark` (status, adjudicate, corpus-query, gate — all read-only) recorded in the nested README or RUN note; PANTHER-side full a_rfc suite still green. Then STOP and present the **confirmation batch**: `gh repo create ElNiak/ai_rfc` + push + `.gitmodules` wiring in PANTHER + LICENSE choice + optional MARK GitLab live fetch.
