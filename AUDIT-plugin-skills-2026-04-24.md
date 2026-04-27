# panther-ivy-plugin — claude-audit report

Date: 2026-04-24
Plan of record: `/Users/elniak/.claude/plans/serene-seeking-pony.md`
Scope: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/` — skills tree (17 SKILL.md, 42 references, 2 READMEs), plus widened scope: plugin root `README.md`, `.claude/rules/*`, `agents/*`, `commands/*`, `hooks/{README.md,hooks.json}`, top-level JSON configs (spot-check).

Audit method: four parallel Explore subagents, one per file cluster, then a main-thread synthesis. Read-only. No files have been edited.

## 1. Executive summary

| Count | Category |
|---|---|
| ~80 | files scanned (17 SKILL.md, 42 references, 8 rules, 3 agents, 7 commands, 1 README, 2 skill-tree READMEs, `hooks.json` + `hooks/README.md`, 4 top-level JSON configs) |
| **1** | **CRITICAL** — `ivy-writing-guide/README.md` nested inside a skill; decision 4 = delete after migrating unique content |
| **5** | **WARNING** — 4 oversize references with mixed concerns needing splits; 1 duplicate paragraph across two references |
| **8** | **INFO** — soft-cap length overshoots and minor placement nits; per decision 2, length overshoot is INFO not WARNING |
| **3** | **BRAINSTORM** — duplicate Output Style block; plan-mode reference-file naming drift; hardcoded memory path in two SKILL.md bodies |
| **0** | cross-layer conflicts |

Widened scope (README, rules, agents, commands, hooks, configs) is **clean** — no actionable findings. The three thin-pointer rules flagged as suspicious in the plan (`ivy-patterns.md`, `nct-methodology.md`, `insights.md`) turn out to be intentional pointer stubs, not stale; the plan pre-scan hypothesis was wrong.

## 2. Decisions applied (from plan section 2)

| # | Decision | Applied |
|---|---|---|
| 1 | Widen scope beyond `skills/` | Yes; findings for README, rules, agents, commands, hooks all clean |
| 2 | Length 300–499 = INFO, ≥500 = CRITICAL | INFO applied to navigate/build/verify; nothing hits hard cap |
| 3 | Output Style duplicate → brainstorm | Three options presented below; no fix selected |
| 4 | `ivy-writing-guide/README.md` = delete | CRITICAL; blocked on content migration |
| 5 | Description length overshoot not flagged | No description flagged for length alone |
| 6 | Fix application mode | Deferred, asked at end of report |

## 3. CRITICAL — block on any follow-up work

### C1. `skills/ivy-writing-guide/README.md` (41 lines) — delete after migration

**Location:** `plugins/panther-ivy-plugin/skills/ivy-writing-guide/README.md`

**Rule:** nested README inside a skill directory violates plugin convention; `skills/*/` should contain SKILL.md + `references/*.md` only. Decision 4 is deletion.

**Evidence:** file contains three Ivy language examples — axioms/conjectures, type `this`, nested objects. The subagent verified these are **not present** in `ivy-writing-guide/SKILL.md` and the SKILL.md points to a canonical memory file `~/.claude/projects/<project>/memory/reference_ivy_patterns.md` for the full syntax reference. The memory-file content was also not confirmed to include these three examples during the audit.

**Proposed fix (two-step):**

1. **Migrate first.** Append the three example sections to `skills/ivy-writing-guide/references/ivy-1.7-patterns-reference.md` (the in-skill syntax reference, currently 304 lines — section E below proposes splitting it, so the migration target may evolve). Or append to `~/.claude/projects/<project>/memory/reference_ivy_patterns.md` so the canonical memory copy absorbs them.
2. **Then delete** `skills/ivy-writing-guide/README.md`.

**Why two steps:** delete-first loses the examples. Migrate-first preserves content and makes the deletion a no-op for coverage.

## 4. WARNING — content/structure, not size

### W1. `skills/ivy-error-patterns/references/verifier_patterns.md` (504 lines) — split catalog from gate architecture

**Current:** three concerns mixed — (a) numbered append-only entries `#100–#589` (the catalog, ~380 lines), (b) gate-to-ID-range mapping and per-gate slices (lines 17–38, ~25 lines), (c) convention rules for additions (lines 499–505, ~7 lines).

**Fix:** keep entries `#100–#589` in `verifier_patterns.md`; extract (b)+(c) either into a new `verifier_patterns_architecture.md` or merge them into `reflection-patterns/references/gates.md` which already owns the gate-discipline layer. The architecture section is ~32 lines, so either target is viable.

### W2. `skills/ivy-toolkit/references/tool-catalog.md` (473 lines) — split per-tool reference from orchestration

**Current:** three concerns mixed — per-tool reference for 18 tools (~400 lines), mode-mapping plus LSP-operations plus Serena tools (lines 53–98, ~45 lines), tool-selection decision matrix (lines 120–134, ~15 lines). Per-tool entries are primary; architecture and selection are cross-cutting.

**Fix:** keep tools 1–18 in `tool-catalog.md` (~400 lines); extract mode mapping, LSP operations, Serena section into `tool-architecture.md`; move the selection decision matrix into `lsp-patterns.md` (which already covers LSP invocation patterns) or create `tool-selection-guide.md`.

### W3. `skills/ivy-writing-guide/references/ivy-1.7-patterns-reference.md` (304 lines) — split syntax from modeling patterns from generator patterns

**Current:** six concerns mixed — syntax reference (sections 1–14, ~180 lines), state-machine patterns (lines 168–196), packet-type enum pattern (lines 198–211), RFC-to-Ivy mapping (lines 239–248), test spec template (lines 250–272), generator patterns with anti-patterns (lines 276–305).

**Fix:** rename to `ivy-1.7-syntax.md` keeping sections 1–14 (~180 lines); extract state machines + packet-type enum + RFC mapping into `ivy-modeling-patterns.md` (~100 lines); extract test spec template + generator patterns into `generator-patterns.md` (~40 lines) or fold into existing `syntax-examples.md`.

### W4. `skills/ivy-error-patterns/references/error-table.md` — `generator starvation` entry (lines 288–316) is a walkthrough, not a lookup

**Current:** entries 1–12 are quick-lookup format (symptom → root cause → fix, ~5–10 lines each). Entry 13, "Generator starvation (test passes but no protocol traffic)", is 29 lines with "Diagnosis" subsection, cross-reference into the `verify` workflow, and multi-step investigation procedure.

**Fix:** extract entry 13 into `generator-patterns.md` (matches W3 migration target) or into `ivy-toolkit/references/generator-guide.md`. Leave a one-line pointer in `error-table.md` that says "for generator starvation, see generator-patterns.md".

### W5. RFC bracket-tag annotation duplicated across two files

**Location 1:** `skills/ivy-writing-guide/SKILL.md` lines 48–52
**Location 2:** `skills/ivy-writing-guide/references/ivy-1.7-patterns-reference.md` lines 225–230

**Current:** identical content explaining the `[rfcNNNN:X.Y]` citation format.

**Fix:** pick a single canonical location. The `.claude/rules/ivy-formatting.md` file already documents the RFC citation format authoritatively; both duplicates could simply link to it instead. Recommended location: `.claude/rules/ivy-formatting.md` remains canonical; both SKILL.md and the reference file use a one-line pointer.

### Also (from batch 2, downgraded per decision 2):

### W6 (was CRITICAL in subagent-2 report). `skills/methodology-reference/references/comprehensive-methodology-detail.md` (411 lines) — split by methodology

**Reason to downgrade:** the subagent labeled this CRITICAL on mixed-concerns grounds; the plan treats length+mixed-concerns in a reference file as WARNING, not CRITICAL (only SKILL.md ≥500 lines is CRITICAL). The mixed-concerns concern is legitimate.

**Current:** four concerns — NCT 10-step workflow (lines 1–129), NACT APT lifecycle (lines 131–257), NSCT Shadow NS simulation (lines 260–357), optional layers + decision matrix (lines 370–411).

**Fix:** split into four focused references — `nct-workflow.md`, `nact-lifecycle.md`, `nsct-simulation.md`, `optional-layers.md`. Each becomes independently loadable; the SKILL.md updates its link list.

### W7. `skills/propagation-patterns/SKILL.md` lines 11–16 — Authority Rule placement

**Current:** the block states `ivy_propagation(mode="impact", ...)` output is the single source of truth. This is a governance rule inline in a pattern-library skill body.

**Fix:** extract to `.claude/rules/propagation-authority.md` (matches the existing pattern of other rules sitting in `.claude/rules/`). Leave a one-line pointer in the SKILL.md body.

## 5. INFO — soft-cap overshoots and minor nits

Per decision 2, all of these are INFO. No fix required; listed so they can be tracked if a future cleanup pass lands.

| # | File | Current | Note |
|---|---|---|---|
| I1 | `skills/navigate/SKILL.md` | 329 lines | 29 lines over soft cap; `plan-mode-lifecycle.md` reference exists (284 lines) and could absorb more |
| I2 | `skills/build/SKILL.md` | 354 lines | 54 lines over soft cap; Iron Laws notice (lines 17–19) is a candidate for extraction into `.claude/rules/` reference |
| I3 | `skills/verify/SKILL.md` | 373 lines | 73 lines over soft cap; Phase 6/7 diagnosis content could extract further into `failure-diagnosis.md` |
| I4 | `skills/navigate/references/plan-mode-lifecycle.md` | 284 lines | Under cap but near; three procedures bundled (Phase 0 detection, Phase 1.5 post-plan-approval, Plan-Author Branch) |
| I5 | `skills/triage/references/full-health-check.md` | 397 lines | 97 lines over soft cap; justified by 9-step runbook cohesion |
| I6 | `skills/verify/references/failure-diagnosis.md` | 201 lines | Under cap |
| I7 | `skills/review/` | no `references/` subdirectory | Not a rule violation; review is dispatch-centric. Listed so future expansion considers creating it |
| I8 | `skills/navigate/SKILL.md` frontmatter | blank line inside frontmatter block | Benign; remove blank line before closing `---` |

## 6. BRAINSTORM — present options, let the user decide

### B1. Duplicate "Output Style" block across 5 workflow spines

**Where (verbatim in five files):**
- `skills/navigate/SKILL.md:15–20`
- `skills/build/SKILL.md:6–11`
- `skills/verify/SKILL.md:6–11`
- `skills/review/SKILL.md:6–11`
- `skills/triage/SKILL.md:6–11`

**Block contents:**
```
## Output Style

This workflow's output formatting is managed by the style system.
Follow the style directives injected via `additionalContext` -- they contain
the active workflow overlay and phase modifier. Do not invent
formatting for tool results that arrive pre-formatted in `hookSpecificOutput`.
```

**Options:**

- **Option 1 — extract to a shared reference** (e.g., `skills/_shared/output-style.md`) and have each SKILL.md link to it. Drawback: violates the "references/ per-skill only" memory rule; introduces a shared directory.
- **Option 2 — accept as intentional boilerplate.** 30 lines of duplication is tolerable; each skill remains self-contained on load. Drawback: hard to update if the rule changes.
- **Option 3 — consolidate into `.claude/rules/output-style.md`** alongside existing rule files (`iron-laws.md`, `ivy-formatting.md`, etc.). Each SKILL.md body has a one-line pointer. Drawback: no precedent in this plugin for SKILL.md bodies pointing at `.claude/rules/` files; rules are typically harness-injected.

The plan said brainstorm; no default selected. Option 3 aligns best with the plugin's existing convention of putting cross-cutting rules in `.claude/rules/`.

### B2. Plan-mode reference file naming drift

**Three references cover nearly-identical procedures under three names:**
- `skills/navigate/references/plan-mode-lifecycle.md` (284 lines, covers Phase 0 detection + Phase 1.5 post-plan-approval + Plan-Author Branch)
- `skills/build/references/plan-mode-handling.md` (27 lines, Phase 0 only)
- `skills/verify/references/plan-mode-preamble.md` (53 lines, Phase 0 + 5-step)

**Options:**

- **Option 1 — unify naming** to `plan-mode-protocol.md` across all three skills. Each reference remains per-skill and keeps the skill-specific content, but name consistency makes cross-skill grepping and maintenance easier.
- **Option 2 — consolidate into a single shared reference** under a shared location, referenced by all three SKILL.md bodies. Same cross-skill sharing trade-off as B1 Option 1.
- **Option 3 — accept the drift.** Each skill's file captures what its workflow specifically needs, and the names reflect the difference in scope (lifecycle vs. handling vs. preamble).

### B3. Hardcoded memory path in two SKILL.md bodies

**Where:**
- `skills/methodology-reference/SKILL.md` line 20: `~/.claude/projects/<project>/memory/reference_nct_methodology.md`
- `skills/specification-patterns/SKILL.md` line 17: same path

**Why it's flagged:** the path template includes `<project>` which resolves per-user and per-project — it is not a constant literal. Writing the path inline creates a minor drift risk if the memory convention changes. Per memory rule, **skills should not hardcode paths into another skill's references/**. This is not quite that — it points into user auto-memory, not another skill — but the same hygiene concern applies.

**Options:**

- **Option 1 — leave as-is.** The path template is correct and the convention is documented in user auto-memory; the duplication is by-design because both skills own aspects of the 14-layer pattern.
- **Option 2 — centralize in `.claude/rules/nct-methodology.md`** (the existing thin-pointer rule) so the skills say "canonical table is in the path documented by `.claude/rules/nct-methodology.md`" and the rule holds the single copy of the path.
- **Option 3 — drop the explicit path** from both SKILL.md bodies, relying on the fact that the canonical-content skill load surface already points users to the right place.

## 7. Widened scope — all clean

The plan predicted possible findings in `README.md`, `.claude/rules/*`, `agents/*`, `commands/*`, `hooks/*`, and top-level JSON configs. The subagent found none. Highlights:

- **README.md (235 lines):** documents plugin internals for contributors; no duplication with SKILL.md routing bodies; no stale "Specification Engineer" framing (that content was moved to `navigate/SKILL.md` per the 2026-04-23 memory note); no external-plugin authority citations.
- **Thin-pointer rules** (`ivy-patterns.md` 11 lines, `nct-methodology.md` 11 lines, `insights.md` 7 lines): **intentional**. Each stub points to a canonical source (skill reference or user auto-memory). The plan had flagged them as suspected staleness; audit disproves that hypothesis.
- **All 8 `.claude/rules/*.md` files** align with each other and with SKILL.md bodies. No contradictions. The canonical recovery pattern in `agent-dispatch.md` and `mcp-tool-reliability.md` is mirrored correctly.
- **All 3 agent definitions** (model-reviewer 256, spec-analyst 270, traceability-agent 233) under the 500-line cap with valid frontmatter, documented file-ownership, justified per-agent timeout overrides.
- **All 7 slash commands** consistently dispatch to MCP tools or skills (no inline procedure), reference `.claude/rules/mcp-tool-reliability.md` for error recovery, use no prose "(a)/(b)/(c)" menus.
- **Every one of the 27 hook scripts referenced in `hooks.json` exists on disk.** No dead entries. Matcher patterns are tight, no duplicate matcher+event combinations, ordering-dependency comments are present.
- **Top-level configs** (`.mcp.json`, `.lsp.json`, `settings.json`, `routing-rules.json`) reference only existing skills/scripts/workflows.

## 8. Cross-layer findings

**None.** SKILL.md bodies do not contradict `.claude/rules/*`. Agent definitions follow the dispatch contract. Commands dispatch to skills cleanly. Hooks reference existing scripts. Routing rules point at existing skills.

## 9. Proposed fix sequence (ordered by blast radius, smallest first)

1. **I8** — remove blank line in `navigate/SKILL.md` frontmatter. Trivial, one-file edit.
2. **W5** — consolidate RFC bracket-tag annotation into `.claude/rules/ivy-formatting.md`; shorten the two duplicate locations to one-line pointers. Two-file edit.
3. **B3** — resolve hardcoded memory path (pick Option 1/2/3). If Option 2, extract path into `.claude/rules/nct-methodology.md`; two-file edit.
4. **W7** — move propagation-patterns Authority Rule into `.claude/rules/propagation-authority.md`. Two-file edit.
5. **B1** — resolve Output Style duplication. Option 3 is five SKILL.md edits + one new rule file; Option 2 is zero edits; Option 1 is five SKILL.md edits + one shared reference.
6. **W4** — extract `error-table.md` generator-starvation entry into a dedicated `generator-patterns.md`. New-file creation + one-line update in `error-table.md`.
7. **W1** — split `verifier_patterns.md` catalog from gate architecture. New file; SKILL.md link list update.
8. **W2** — split `tool-catalog.md` per-tool from architecture from selection. New file(s); SKILL.md link list update.
9. **W3** — split `ivy-1.7-patterns-reference.md` into syntax + modeling patterns + generator patterns. Three-file refactor.
10. **W6** — split `comprehensive-methodology-detail.md` into four methodology-focused files. Four-file refactor.
11. **B2** — unify plan-mode reference file names. Three-file rename (or zero edits if Option 3 "accept drift").
12. **C1** — delete `ivy-writing-guide/README.md` **after** migrating the three example sections (axioms, type `this`, nested objects) into the chosen syntax reference. Migration-first, then delete.

Early items (1–4) are quick wins with low blast radius. Mid items (5–7) are scoped refactors. Late items (8–11) are multi-file splits that benefit from the mid items landing first.

## 10. Next step — fix application mode

All 12 items in section 9 are proposals. None will be applied without approval. Per the plan (decision 6, deferred), you now choose how to apply fixes:

- **Single ordered queue** — approve each item individually in the order above; I apply one, you verify, we proceed.
- **Batch per directory** — approve all skill-body fixes first (1, 3, 4, 5, 11), then all reference refactors (2, 6, 7, 8, 9, 10), then C1 last.
- **Self-contained quick wins first** — batch-approve items 1–4, apply them together, then tackle each refactor individually.
- **Pick and choose** — tell me specific item numbers and I apply only those.

I will ask with AskUserQuestion in the chat so you can mark the ones to apply.
