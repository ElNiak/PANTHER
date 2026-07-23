# `panther-ivy-plugin` bloat audit (2026-05-01)

**Subject:** `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/`
(plugin v0.11.0, post-April-2026 orchestrator refactor)
**Reference docs:**
- *Architecting Enterprise-Grade AI Agents for Large-Scale Software Engineering*
  (pasted in command args; cited as *SWE-agent doc*).
- *Improving LLM Formal Specification Generation* (in plugin tree;
  cited as *formal-spec survey*).
**Audit shape:** hybrid — workflow-shape choice → per-artifact verdicts → parking lot.
**Status:** Phase A complete (inventory). Phase B pending user pick.
**Plan file:** `/Users/elniak/.claude/plans/audit-my-plugin-against-modular-meerkat.md`.

---

## Review-side corrections (2026-05-01, post-execution annotation)

A `/review-plan` pass against this audit verified its empirical claims and
surfaced four corrections that were folded in before Phase 1 execution.
These corrections override conflicting claims later in the report.

1. **Section 0 README staleness scope is smaller than claimed.** The actual
   on-disk README already says v0.11.0 (not v0.10.0), with mostly-current
   counts: 5 ops + 7 knowledge skills (matches), 5+3 agents (matches), 2
   commands (matches), but the hook count was wrong (28 → actual 24
   distinct, 35 registrations across 12 events). Phase 1.4 fixed the hook
   row, added a missing "Maintainer self-audit skill (reference-drift)"
   row, and corrected the rules count from 13 to 15.

2. **Section 1c Axis 7 and Section 1d row for `routing-rules.json` are
   RESOLVED.** The file no longer exists. It was removed in the April
   orchestrator refactor (`meta-self-mod-ops/SKILL.md` documents the
   deletion). Drop both items from the Phase B/C deliberation; the cut
   already happened.

3. **Section 4 row for `inject-using-plugin.sh`: KEEP, no MED qualifier.**
   The 10-line script is the SessionStart hook that injects the
   orchestrator priority preamble (the `[panther-ivy-plugin priority
   overview]` header every session begins with). It is load-bearing, not
   a pre-refactor leftover.

4. **The `styles/` system is more dead than the audit knew, but the
   decision is deferred to Phase 2.** All 10 `styles/{overlays,summaries}/
   workflow-*.md` files are dead via two layers: (a) the loader
   `style_utils.py` expects unprefixed names like `overlays/build.md`
   (loader-name mismatch), AND (b) the loader's only known consumer
   (`compose-style.py`) was archived in Phase D. `render-summary.py` does
   NOT load styles — its summary logic is hardcoded per-workflow. The
   `style_utils.py` module + `tests/test_style_utils.py` (134 lines) +
   `tests/test_compose_style.py` (~150 lines) test dead code. The
   2026-04-29 harness audit already flagged this as a sibling problem.
   Decision per user: defer cut-vs-revive to Phase 2 alongside the
   build-ops → scaffold-ops rename.

5. **Side-finding (audit missed):** `.claude/rules/ivy-patterns.md`
   invoked `Skill(panther-ivy-plugin:ivy-syntax)`, not `ivy-patterns`.
   Either a renaming residue or a real bug. Resolved in Phase 1.2 by
   cutting the rule entirely (the skill self-activates via its own
   `paths: "**/*.ivy"` frontmatter).

6. **Pointer-stub rules are intentional, not accidental.** Commit
   `1685b3f` ("refactor(plugin/rules): U-13 reframe stub rules as
   paths-scoped action rules") explicitly designed them as path-triggered
   skill activators. The cut in Phase 1.2 moves the trigger mechanism
   into the skill frontmatter (`paths:` on `methodology/SKILL.md`)
   instead of the rule body, eliminating the pointer-stub anti-pattern
   while preserving the intended path-based activation.

7. **Section 7 row 3 ("Fold `review-ops` content") is REFUTED.** On
   2026-05-01 a parallel Explore pass against the post-`f9606ad` plugin
   tree found that `agents/ivy-reviewer-agent.md` is a real load-bearing
   specialist agent (64 lines, model: opus, four preloaded skills,
   `forbidden_tools: ["Edit", "Write", "Bash"]`). `_KNOWN_WORKFLOWS`
   includes `"review"`. The orchestrator routing table at
   `skills/ivy/SKILL.md:85` dispatches coverage/quality work to
   `ivy-reviewer-agent`. `skills/refine-ops/SKILL.md:384` and
   `skills/experiment-ops/SKILL.md:268` issue `pending_dispatch` to the
   `review` workflow. `review-ops` does stand alone as a workflow.
   Section 7 row 3's "fold into scaffold/refine/experiment" prescription
   is wrong; the actual remaining work is normalizing five to ten
   drifted `model-reviewer` citations (rename residue) to
   `ivy-reviewer-agent`. Resolved by Phase 2 follow-up commit (drift
   normalization), not by a fold.

8. **Section 6c + Section 7 row 4 (styles work) are INCOMPLETE.** The
   audit prescribed renaming five overlay files and five summary files
   to mode names. Reality: `hooks/scripts/compose-style.py` is in
   `.backup/2026-04-28/hooks/scripts/compose-style.py`, removed from
   the live tree. No SessionStart or UserPromptSubmit hook injects
   style content. `.claude-plugin/plugin.json` has no `outputStyles`
   field. The mode-first replacements
   (`styles/overlays/{navigate,scaffold,refine,experiment,review,triage,meta}.md`
   and the parallel summaries) do not exist. The actual work is
   (a) restore `compose-style.py`, (b) register the UserPromptSubmit
   hook, (c) write seven mode-first overlay files and seven summary
   files (covering all of `_KNOWN_WORKFLOWS`), (d) retire the five
   orphan `workflow-*.md` overlays and five orphan `workflow-*.md`
   summaries to `.backup/`. Resolved by Phase 2 follow-up commit
   (styles revival).

9. **Section 6f (tests) — sub-finding annotation.** As of 2026-05-01,
   the test suite reports 37 failures. None of those failures test
   dead code. They are TDD red tests for four hook scripts that do not
   yet exist on disk: `interaction-checkpoint.py` (9 failures plus 2
   in `test_workflow_aware_hooks.py`), `route-user-prompt.py` (12
   failures), `compose-style.py` (5 failures, addressed by the styles
   revival above), `track-workflow-skill.py` (5 failures); plus 2
   output-format bugs in `assess-modeling.py` (missing
   `additionalContext` key) and 2 in `assess-trace.py` (missing `[G1
   modeling gate]` marker emission). Three of the four missing scripts
   are Phase 4 mode-detection features per the squishy-fiddle plan.
   The 6f KEEP verdict stands; the 26 routing/checkpoint/track-workflow
   failures are out of scope for the bloat audit and stay red until
   Phase 4 lands.

**Phase 1 deliverables (PR 1, executed 2026-05-01):**
- 3 pointer-stub rules moved to `.backup/rules-pointer-stubs-2026-05-01/`
- 2 docs/ audit drafts moved to `.backup/docs-pre-refactor-2026-05-01/`
- `methodology/SKILL.md` gained `paths: ["**/*.ivy", "**/skills/*/SKILL.md"]`
- `apt-attack-patterns/SKILL.md` reference to dead `nct-methodology.md`
  stub updated to point directly at the methodology skill
- README hook-count, rules-count, and reference-drift row corrected
- This corrections header added

---

## Methodology

Every artifact must defend itself against at least one of five lenses. Anything
that defends nothing is a CUT candidate; anything that defends one lens worse
than another artifact in the plugin is a FOLD candidate; anything in the right
lens but the wrong shape is a RESHAPE candidate.

| # | Lens | Source |
|---|---|---|
| L1 | Bridges the Ivy gap for a protocol engineer (no formal-methods background) | User goal, grilling Q4 |
| L2 | Keeps the human in cognitive control (presents choices, surfaces CoT) | User goal, grilling Q3 |
| L3 | Fact-checks the LLM (compile / verify / IUT / RFC citation gates) | User goal, grilling Q3 |
| L4 | Persists project context across sessions (continuous dev memory) | User goal, grilling Q3 |
| L5 | Embodies a technique endorsed by the SWE-agent doc or the formal-spec survey | Reference docs |

**Verdict legend:** KEEP — defends ≥1 lens. CUT — defends none. FOLD-INTO-X — defends a
lens that another artifact serves better; merge. RESHAPE — right lens, wrong shape.
PARKED — missing capability, requires upstream `ivy-tools` MCP changes (Section 8).

---

## Section 0 — Ground truth corrections (vs. plugin README)

The README at `submodules/panther-ivy-plugin/README.md` claims component counts that no
longer match the on-disk reality. The April 2026 orchestrator refactor
(`handoff-2026-04-28-orchestrator-refactor.md` in MEMORY.md) reshaped the plugin and
the README was never updated. Mismatches:

| Surface | README claim | On-disk reality | Delta |
|---|---|---|---|
| Plugin version | 0.10.0 | 0.11.0 (`plugin.json`) | -1 minor |
| Skills | 12 (5 workflow + 7 knowledge) | **14** (1 orchestrator `ivy` + 5 ops + 8 knowledge) | +2, renamed |
| Agents | 3 internal | **8** (6 `ivy-*-agent` + 2 `g-*-critic`) | +5 |
| Commands | 5 (`nct-check`, `nct-compile`, `nct-model-info`, `nct-health`, `nct-observability`) | **2** (`nct-iut-test`, `nct-health`) | -3, one renamed |
| Hooks | "29 across 12 events" | ~25 scripts on disk; hooks.json registrations may multiply per event | needs count reconciliation |
| Skill names | `navigate / build / verify / review / triage / methodology-reference / specification-patterns / ivy-writing-guide / ivy-toolkit / counterexample-guide / propagation-patterns / claim-discussion` | `ivy / build-ops / verify-ops / review-ops / triage-ops / meta-self-mod-ops / ivy-syntax / ivy-toolkit / methodology / propagation-patterns / specification-patterns / verification-failures / apt-attack-patterns / reference-drift` | rewrite; `ivy-writing-guide`→`ivy-syntax`, `methodology-reference`→`methodology`, `counterexample-guide`→`verification-failures`, `claim-discussion` removed entirely |

**Verdict (preliminary, pre-taxonomy):** The README is itself a CUT/RESHAPE candidate.
At minimum it must be regenerated from on-disk truth. Likely the correct fix is to
**generate** the component counts at install/build time so they cannot drift again.

---

## Section 0b — Stale residue from the orchestrator refactor

Several artifacts still reference the *pre-refactor* verb-shaped workflows
(`navigate / build / verify / review / triage`) by name, even though those workflow
names no longer exist as skills:

- `styles/overlays/workflow-{navigate,build,verify,review,triage}.md` — 5 overlay
  files keyed to the old names.
- `styles/summaries/workflow-{navigate,build,verify,review,triage}.md` — matching
  5 summary files.
- `.claude/rules/{review,verify,build}-anti-patterns.md` — three rule files keyed
  to the old workflow verbs (these may still apply to the new ops skills,
  but the naming is misleading).

These are pre-classified as **stale-pointer** candidates pending Phase C deep read.

---

## Section 0c — Empirical evidence from four-agent investigation (2026-05-01)

To avoid picking a taxonomy on shallow reading of generic reference docs, four
parallel Explore agents were dispatched against four evidence bases. Findings:

### Agent A — `panther_ivy` git history

- Spec dev empirically proceeds in **three nested time-scales**: linear skeleton
  for new protocols (1 commit pattern: entities → message types → ser/deser →
  test scaffold → shim) → linear feature additions (FSM → Timers → Exports →
  Manifests → Annotations → Validation → Coverage) → absorbing loops triggered by
  Z3 UNSAT or counterexamples.
- Commit `403a0675` (Apr 20, 2026) "commit_as_sequence redesign" is the
  paradigm case: Z3 UNSAT triggered structural redesign mid-feature, replacing
  a four-action queue chain with a single aggregate-parameter action. The
  refinement loop is real and load-bearing.
- BGP `build-state.yaml` explicitly enforces "all 14 layers present; extend
  existing files only" — the 14-layer template is a hard discipline for
  mature protocols.
- Top-10 commit sequence for "how an Ivy spec is built end-to-end" reveals a
  consistent pattern: RFC section identification → model code → test export
  → manifest annotation → coverage validation → IUT verification.

### Agent B — NCT/NACT/NSCT literature

- Canonical paper: **McMillan & Zuck, "Formal specification and testing of
  QUIC", SIGCOMM'19**. Compositional specification-based testing: formal spec
  in Ivy plays one role against an IUT, before/after monitors verify
  conformance, Z3-driven test generation.
- **NCT canonical workflow is 10 explicit phases**: (1) Select RFC → (2)
  Decompose into 14 layers → (3) Types → (4) Stack → (5) Entities → (6)
  Behaviors (before/after monitors) → (7) Test specs (with `_finalize`) →
  (8) Verify (`ivy_verify` / `ivy_check`) → (9) Compile (`ivy_compile`) →
  (10) Execute against IUT.
- Workflow is **"sequential pipeline with embedded tight verification
  sub-loop at steps 8-10"**. Not a pure absorbing Markov chain; not a
  hub-and-spoke multi-agent decomposition.
- NACT extends with the APT 6-stage attack lifecycle (Reconnaissance →
  Infiltration → C2 → Privilege Escalation → Persistence → Exfiltration,
  plus White Noise). Citation: Crochet, Aoga, Legay, NordSec'24.
- NSCT integrates Shadow Network Simulator for deterministic large-scale
  testing. Citation: Rousseaux, Crochet, Aoga, Legay, FORTE'24.

### Agent C — PANTHER core orchestration

- 4-phase model: (1) Initialization → (2) Plugin Loading → (3) Environment
  Deployment → (4) Test Execution. Driven by experiment YAML config.
- Tester contract: `ITesterManager` + `@register_plugin(PluginType.TESTER)`.
  Required methods: `initialize()`, `_do_run_tests()`, `get_test_results()`,
  `cleanup()`.
- Experiment artifacts in `outputs/<date>/<id>/`: per-service `compile/`,
  `runtime/`, `test/` stdout/stderr; `.pcap`, `.qlog`, `sslkeylog.txt`,
  `test_results.yaml`, `experiment_report.{json,md}`, optional metrics.
- **Zero HITL during execution.** PANTHER is fully autonomous from
  `panther run`. Only `panther create` has interactive scaffolding.
- **Critical:** PANTHER deliberately separates spec authoring from experiment
  execution. PANTHER reads pre-written specs. Authoring is external — and
  therefore the plugin's design space is completely open with no upstream
  constraint.

### Agent D — Ivy test-generation pipeline

- `ivyc target=test <file>.ivy` produces three artifacts: compiled C++ test
  binary, generated `.cpp`, generated `.h`. `ivy_check` is verification only
  (Z3, no codegen). `ivy_to_cpp` exists but `panther_ivy` does not invoke it
  directly. `ivy_show` dumps the AST.
- **Test-spec vs. model split:** model files (e.g., `quic_connection.ivy`)
  are declarative protocol truth — types, state machines, invariants, no
  `export`. Test-spec files (e.g., `quic_server_test_timeout.ivy`) include
  the model, import shims/behavior, define initial state in `after init { }`,
  **export actions** for Z3-driven test generation, define monitors as
  before/after clauses, implement `_finalize` for end-state verification.
- **Role inversion is encoded in directory layout, not runtime parameters.**
  `quic_tests/server_tests/` files cause Ivy to act as client; `client_tests/`
  files cause Ivy to act as server. `oppose_role()` is a compile-time mapping;
  `classify_endpoint_type()` infers role from filename keywords.
- **Counterexample format is human-readable text.** Z3 emits S-expressions
  internally, but Ivy renders human-readable traces. `panther_ivy` parses via
  `assumption_failed(...)` regex into a four-value verdict enum
  (`NON_COMPLIANT` / `NO_VIOLATION_FOUND` / `TESTER_CRASH` / `IUT_CRASH`).
  This is a STRONG parking-lot item — machine-readable shaping would
  unlock LLM-driven refinement loops the formal-spec survey §3 prescribes.
- **Isolates are proof compartments, not compilation units.** `ivyc target=test`
  produces one binary per `.ivy` file, regardless of isolate count. Per-node
  testing uses `extract iso(param)` parameterized isolates.
- 14-layer template documented in `methodology-reference.md` and
  panther-ivy-serena skills, NOT in `panther_ivy` parent code itself.

### Cross-agent synthesis — what this means for the taxonomy

The original A/B/C taxonomy options I drafted were **categorically wrong**.
They presented mutually exclusive shapes when the actual answer is **nested
time-scales**:

| Time-scale | Shape | Source |
|---|---|---|
| Outer (per-protocol) | Linear 10-phase NCT pipeline | Agent B literature |
| Middle (per-feature) | Linear sequence of file additions | Agent A git history |
| Inner (per-counterexample) | Absorbing loop until Z3 SAT | Agent A example `403a0675`, Agent D pipeline |

A taxonomy that respects all three time-scales must:
1. Make the **10 NCT phases visible** to the non-expert user (otherwise they
   cannot navigate them).
2. Make **per-feature linear addition** the default authoring mode (matches
   git history empirics).
3. Activate the **absorbing refine loop** when verification fails (matches
   the formal-spec survey's verifier-in-the-loop).

That is **NONE of A / B / C** as I originally framed them. The right shape
is a **phase-aware mode selector** with three modes (scaffold / refine /
experiment) that share a 10-phase progress backbone.

This is the new question for the user.

---

## Section 1 — Workflow taxonomy: LOCKED to mode-first + phase progress (2026-05-01)

User picked **mode-first + phase progress** after the four-agent investigation
revised the original A/B/C options. Locked design:

- **Three explicit modes:** `scaffold` (new protocol or new feature, walks NCT
  phases 1–7), `refine` (counterexample-driven absorbing loop, NCT phases 8–9),
  `experiment` (IUT execution + trace interpretation, NCT phase 10).
- **10-phase progress backbone:** every mode reports current phase as
  `[N/10] <phase name>` so the non-expert protocol engineer always sees where
  they are in the canonical NCT pipeline.
- **Mode transitions:** scaffold auto-transitions to refine on verify failure;
  scaffold auto-transitions to experiment on phase-10 entry; refine returns to
  scaffold when SAT achieved.
- **Per-protocol `PROJECT.md`:** persists current mode, current phase, last
  verify result, RFC sections covered, open counterexamples, last IUT verdict.
  Read by orchestrator on session entry to restore continuous-dev state (lens
  L4).
- **Status line widget:** `Mode: SCAFFOLD | Phase: 4/10 (core stack)`.

### How current skills re-cluster under mode-first

| Existing skill | Lines | Becomes |
|---|---|---|
| `ivy/SKILL.md` (orchestrator) | 197 + 10 critic_prompts/ | `ivy/SKILL.md` retained as orchestrator; first dispatch is mode selection (AskUserQuestion). Critic_prompts/ trimmed (see Section 4). |
| `build-ops/SKILL.md` | 344 + 5 refs | `scaffold-mode/SKILL.md` (phases 1–7). Folds in RFC-analysis from review-ops. |
| `verify-ops/SKILL.md` | 461 + 6 refs | Split: structural verify gate stays as a hook/skill primitive; iterative refine work moves to `refine-mode/SKILL.md` (phases 8–9). IUT-execution work moves to `experiment-mode/SKILL.md`. |
| `review-ops/SKILL.md` | 364 + 0 refs | Folded: phase-1 RFC analysis into scaffold-mode; phase-9 coverage check into refine-mode. No standalone review mode. |
| `triage-ops/SKILL.md` | 387 + 1 ref (full-health-check 396 lines) | Out of user-facing surface. Folds into `nct-health` command + a maintenance hook. Maintainer-only. |
| `meta-self-mod-ops/SKILL.md` | 225 lines | CUT from user surface. Maintainer-only; if kept at all, lives in a `dev/` subdirectory not exposed via Skill listing. |
| `apt-attack-patterns/SKILL.md` | 34 + 2 refs | Knowledge skill, retained, loaded by experiment-mode when NACT methodology is active. |
| `methodology/SKILL.md` | 36 + 5 refs (incl. 526-line comprehensive-methodology-detail) | Knowledge skill, **trimmed**. Comprehensive-methodology-detail.md is 526 lines that duplicate the 10-phase NCT walkthrough — fold the canonical 10-phase reference into a single 100-line `nct-canonical-workflow.md`; rest goes to `.backup/`. |
| `verification-failures/SKILL.md` | 46 + 9 refs (~1.8k lines) | Knowledge skill, retained, primary reference for refine-mode. References stay because verifier_patterns.md (714 lines) is the playbook for counterexample interpretation. |
| `specification-patterns/SKILL.md` | 77 + 2 refs | Knowledge skill, retained, primary reference for scaffold-mode. |
| `propagation-patterns/SKILL.md` | 81 + 1 ref | Knowledge skill, retained but loaded only when scaffold-mode is in extension (not new-protocol) flavor. |
| `ivy-syntax/SKILL.md` | 65 + 5 refs (~870 lines) | Knowledge skill, retained for scaffold-mode + refine-mode. |
| `ivy-toolkit/SKILL.md` | 36 + 7 refs (~1.4k lines) | RESHAPE: skill body is fine; references are bloated. tool-catalog (528 lines) duplicates MCP tool docs; trim to a 100-line "when to call which tool" routing guide. The other 6 refs (timing-and-concurrency, lsp-coordination, hook-lifecycle, error-reference, lsp-patterns, tool-invocation-examples) get individually audited in Phase C. |
| `reference-drift/SKILL.md` | 200 lines | CUT from user surface. Maintainer-only audit tool. |

Net change in user-facing skills: from 14 to **~9** (1 orchestrator + 3 modes + 5
knowledge: methodology, specification-patterns, verification-failures,
ivy-syntax, ivy-toolkit + apt-attack-patterns + propagation-patterns as
on-demand). Maintainer skills (triage-ops, meta-self-mod-ops, reference-drift)
relocated out of the routing table.

### Open questions still constraining Phase C

The mode-first lock answers Axes 1–2. Three more axes remain:

- **Axis 3 (fact-check infrastructure):** how heavy should the LLM-critic gate
  machinery be under the new mode-first design? Currently 10 critic prompts +
  2 g-*-critic agents.
- **Axis 4 (14-layer enforcement):** strict (BGP discipline) or flexible
  (CoAP/MiniP partial)?
- **Axis 5 (experiment-to-spec routing):** when an IUT trace reveals a model
  bug, does experiment-mode auto-route back to scaffold/refine, or surface to
  the user as a choice?

These will be grilled and resolved before Phase C verdicts are written.

## Section 1b — Fact-check infrastructure: LOCKED to "subagents stay, surface FAIL with rich summary" (2026-05-01)

After clarification, the user kept multi-subagent dispatch for context-pollution
defense and self-check-hallucination defense. The contested axis was the
human-review interface, which locked to:

- **All critics still dispatch.** Multi-subagent grading is preserved.
- **PASS verdicts clear silently.** Cognitive load proportional to actual problems.
- **FAIL or split-vote verdicts surface with a structured rich-summary.**
  Format per surfaced critic: verdict, phase, lens, reason, suggested-next-step
  — multiple lines, not single-line, but bounded.
- **Drill-down on demand.** User asks "expand g3" or equivalent to read full
  critic argument when triaging a FAIL.
- **Hard gates remain.** The iron-law deterministic hooks (`NO_FIX_WITHOUT_VERIFY`,
  `NO_LAYER_WITHOUT_SCAFFOLD`, `STALENESS_RULE`) still block at tool-call level;
  critic FAILs surface to the human but only block phase transitions, not
  individual tool calls.

### Critic prompt re-mapping under mode-first

The 10 existing critic prompts (`g0`, `g0b`, `g1`–`g8`) re-bind to the
mode-first design instead of being numbered ad-hoc. Mapping:

| Prompt | Old role | New mode + phase binding | Verdict |
|---|---|---|---|
| `g0_plan.md` | Plan-fidelity gate | Orchestrator entry; checks user's plan against intent. Fires once per session, not per action. | KEEP, RESHAPE narrower |
| `g0b_plan_fidelity.md` | Per-action fidelity | Hook-driven check that the next tool call matches the locked plan. Fires once after plan approval. | KEEP, FOLD into g0 |
| `g1_exploration.md` | Exploration coverage | Scaffold-mode phase 1 (RFC ingestion completeness). | KEEP, RESHAPE for scaffold |
| `g2_modeling.md` | Modeling soundness | Scaffold-mode phases 3–6 (types, stack, entities, monitors). | KEEP, anchor to phases |
| `g3_testspec.md` | Test-spec quality | Scaffold-mode phase 7 (test specs with `_finalize`). | KEEP, anchor to phase 7 |
| `g4_verification.md` | Verify gate | Refine-mode phase 8 (verify SAT). Fires only at phase 7→8 transition. | KEEP, anchor to phase 8 |
| `g5_trace.md` | IUT trace classification | Experiment-mode phase 10 (trace → spec-bug / iut-bug / env-bug). | KEEP, anchor to phase 10 |
| `g6_knowledge.md` | Lesson capture | Session-end hook; captures durable learnings. | KEEP, low-frequency |
| `g7_triage_diag.md` | MCP/LSP health | Triage hook (maintainer-only, not user-facing). | CUT from user surface; keep as a maintainer-mode skill |
| `g8_triage_verify.md` | Verifier health | Same as g7 — folded into maintainer triage. | CUT from user surface |

Net change: 10 critic prompts → 8 user-facing (g0+g0b folded; g7+g8 demoted to
maintainer surface). All 8 surface only on FAIL or split-vote.

Two surviving g-*-critic agents (`g-plan-critic`, `g-fidelity-critic`,
`g-knowledge-critic`) are dispatched by hooks at the right moment for each
critic prompt above. The 6 `ivy-*-agent` agents map to mode work:

| Existing agent | New role |
|---|---|
| `ivy-builder-agent` | scaffold-mode worker |
| `ivy-verifier-agent` | refine-mode worker (verify + counterexample interpret) |
| `ivy-reviewer-agent` | dispatched by g1/g3/g6 critic prompts; not a mode worker |
| `ivy-triage-agent` | maintainer-only, out of user surface |
| `ivy-meta-agent` | maintainer-only, out of user surface |
| (no experiment-mode agent yet) | NEW agent needed: `ivy-experiment-agent` (or fold into ivy-verifier-agent) |

## Section 1d — Corrections to Section 1a after auto-loaded plugin rules surfaced (2026-05-01)

Targeted reads on `meta-self-mod-ops/SKILL.md`, `reference-drift/SKILL.md`,
`triage-ops/SKILL.md`, and `ivy-toolkit/references/tool-catalog.md` triggered
auto-load of the plugin's `.claude/rules/` body (`journaling-contract.md`,
`iron-laws.md`, `agent-dispatch.md`, `mcp-tool-reliability.md`,
`gate-verdicts.md`, `plan-mode.md`, `output-style.md`, plus the
worktree-level `skill-conventions.md`). These rules are load-bearing and
my Section 1a verdicts were drafted without reading them. Corrections:

| Skill | Section 1a verdict | Corrected verdict | Reason |
|---|---|---|---|
| `meta-self-mod-ops` | "CUT from user surface" | **KEEP** (already hidden via `user-invocable: false`) | Backs the `ivy-meta-agent`. Implements the `PLUGIN_3LOOP` iron-law for plugin self-modification. Already invisible to the protocol-engineer user; cutting it would break maintainer self-modification discipline. Confidence: HIGH. |
| `triage-ops` | "Folds into nct-health command + a maintenance hook" | **KEEP** (already hidden via `user-invocable: false`) | Backs the `ivy-triage-agent`. Implements the `mcp-tool-reliability.md` "Retry after fixing MCP server" recovery branch. Already invisible to the protocol-engineer user; cutting would break automatic MCP/LSP recovery. Folding into a command is wrong — it has to remain agent-dispatchable. Confidence: HIGH. |
| `reference-drift` | "CUT from user surface" | **KEEP** (`user-invocable: true`, maintainer-facing) | The plugin's self-audit tool. The very fact that this audit found README staleness in Section 0 is an instance of what reference-drift is designed to catch. Useful for the maintainer (who is also this plugin's user), irrelevant for the protocol-engineer end user, but never a CUT — it's a tool the plugin's developer reaches for. Confidence: HIGH. |
| `routing-rules.json` (Section 1c Axis 7) | "Cuts" | **RECONSIDER** | Section 1c proposed cutting `routing-rules.json` in favor of explicit AskUserQuestion mode selection. But the `output-style.md` rule references the `[ivy-resume]` orchestrator-internal warm-resume marker, and the `journaling-contract.md` lifecycle has Phase 1 / Phase 1.5 reading `pending_dispatch` for warm resume. That mechanism *implements* PROJECT.md-driven resume already. `routing-rules.json` is the cold-start intent classifier; it may still earn its keep when the orchestrator lacks a fresh `pending_dispatch` AND the user enters a free-form prompt without explicitly picking a mode. Confidence: MEDIUM — needs Phase C deep read of `routing-rules.json` to verdict properly. |

### Net implication

The mode-first taxonomy still locks. But the *cutting work* under Phase C
is smaller than Section 1a implied. The plugin's existing infrastructure
(journaling, iron-laws, gate-verdicts, agent-dispatch failure-recovery,
mcp-tool-reliability) is well-designed and load-bearing — the audit's
correct posture is **"rename and re-expose, do not destroy"**:

- **Rename** ops to user-facing modes where the names mismatch the user's
  cognitive model (`build-ops` → `scaffold-mode` body, etc.).
- **Reframe** phase numbering inside each mode to match the canonical
  10-step NCT pipeline (Section 0c, Agent B literature).
- **Add** an experiment-mode skill body (currently this work lives split
  across verify-ops + review-ops + methodology references).
- **Cut** only things that are demonstrably stale: `styles/overlays/`
  files keyed to dead workflow names (Section 0b); old audit drafts in
  `docs/` (`skill-audit-2026-04-27.md`, `superpowers-audit-2026-04-27.md`);
  redundant entries in the 10 critic prompts (Section 1b).

### Newly-flagged bloat candidates (low confidence — verify in Phase C)

The auto-loaded rules surfaced one hint that other rules may overlap or
duplicate skill content:

- `nct-methodology.md` rule (9 lines) is a pointer-stub that just says
  "invoke `Skill(panther-ivy-plugin:methodology)`". This pattern is
  flagged by `feedback_autoload_rule_no_pointer_stub` in MEMORY: the
  rule should either contain content or be deleted entirely. Confidence:
  HIGH (cite-able feedback rule).
- `ivy-patterns.md` rule (9 lines) and `insights.md` rule (7 lines) are
  similarly tiny — same pattern. Confidence: HIGH for review trigger,
  MEDIUM for verdict (need deep read).
- `propagation-authority.md` rule (13 lines) and `review-anti-patterns.md`
  / `verify-anti-patterns.md` / `build-anti-patterns.md` rules (22-23
  lines each) — verify they aren't pointer-stubs that should be folded
  back into their owning skills. Confidence: MEDIUM.

## Section 1c — Defaults for remaining minor axes (locked subject to Phase C pushback)

The audit needs three more axes resolved to write Phase C verdicts. The user
can push back on any specific verdict in Phase C; below are the defaults:

### Axis 4 — 14-layer template enforcement

**Default: strict (BGP discipline) for new protocols, partial allowed for
WIP/legacy.** A new protocol scaffolded under mode-first scaffold mode must
plan all 14 layers; deferring a layer is allowed but requires a
`testable: false` annotation citing the reason. CoAP/MiniP partial state is
grandfathered. Rationale: empirical (BGP `build-state.yaml`),
pedagogical (gives the non-expert a concrete checklist), aligned with NCT
phase 2 in the literature ("Decompose into 14 layers").

### Axis 5 — Experiment-to-spec routing

**Default: auto-handoff with surfaced suggestion.** The experiment-mode g5
trace classifier emits a verdict that includes `spec-bug | iut-bug |
env-bug`. On `spec-bug`, the orchestrator surfaces a suggested transition:
"Trace suggests a model bug at phase 6 (monitors). Enter refine-mode for
that phase?" Human approves transition (single AskUserQuestion). On
`iut-bug` or `env-bug`, the orchestrator stays in experiment-mode and
records the finding to `PROJECT.md`.

### Axis 6 — `PROJECT.md` schema (per-protocol persistent memory)

**Default: minimal first pass.** Lives at
`protocol-testing/<protocol>/PROJECT.md`. Schema:

```yaml
---
protocol: <name>
version: <RFC version>
mode: scaffold | refine | experiment | idle
phase: 1..10
last_verify:
  status: SAT | UNSAT | NOT_RUN
  timestamp: <iso>
  isolate: <name>
rfc_sections_covered: [list of section IDs]
open_counterexamples: [{phase, isolate, last_observed}]
last_iut_run:
  iut: <name>
  verdict: NO_VIOLATION_FOUND | NON_COMPLIANT | TESTER_CRASH | IUT_CRASH
  timestamp: <iso>
deferred_layers: [{layer, reason}]
---
```

The orchestrator reads this on session entry; if `mode != idle` and `phase < 10`,
it offers to resume that mode/phase instead of asking. If `idle`, it asks the
user which mode to enter.

### Axis 7 — Mode detection mechanism

**Default: PROJECT.md-driven resume + AskUserQuestion fallback.** No automatic
intent classification from prompt content (avoids the bug class where the
plugin guesses wrong from a free-form prompt and dispatches the wrong mode).
On session entry, orchestrator reads `PROJECT.md` for the protocol in scope:

- If unfinished work, offer to resume that mode/phase. Single AskUserQuestion.
- If no PROJECT.md or `mode: idle`, ask which mode to enter. Single AskUserQuestion.
- If mid-session the user asks something off-mode, orchestrator surfaces:
  "That's a refine-mode action; switch from scaffold to refine?"

This replaces the current `routing-rules.json` intent-classification machinery
with explicit user-driven mode selection. Cuts `routing-rules.json` and any
hooks that depend on it.



The current orchestrator-and-ops layout is the result of the April refactor. The
audit must decide whether to keep that shape, evolve it, or replace it. Below are the
three candidate shapes with concrete after-state previews showing how the existing
skills re-cluster.

### Option A — Keep orchestrator + ops (status quo evolution)

```
skills/
  ivy/                       (orchestrator — 197 lines body, +10 critic_prompts)
  build-ops/                 (344 lines body)
  verify-ops/                (461 lines body)
  review-ops/                (364 lines body)
  triage-ops/                (387 lines body — KEEP, RESHAPE, or FOLD?)
  meta-self-mod-ops/         (225 lines body — almost certainly CUT for end user)
  ivy-syntax/                (knowledge, 65 + 5 refs)
  ivy-toolkit/               (knowledge, 36 + 7 refs = ~1.4k lines)
  methodology/               (knowledge, 36 + 5 refs = ~850 lines)
  specification-patterns/    (knowledge, 77 + 2 refs)
  verification-failures/     (knowledge, 46 + 9 refs = ~1.8k lines)
  propagation-patterns/      (knowledge, 81 + 1 ref)
  apt-attack-patterns/       (knowledge, 34 + 2 refs)
  reference-drift/           (knowledge, 200 — maintainer-only?)
```

Audit work under Option A: cut individual skills/refs that don't earn the lens; do not
challenge the hub-and-spoke shape itself.

### Option B — Absorbing-Markov-loop (formal-spec survey §3)

```
skills/
  spec-loop/                 (NEW — single skill embodying scaffold → propose →
                              verify → interpret → refine. Body merges build-ops +
                              verify-ops + review-ops; references survive as states
                              of the loop.)
  setup/                     (NEW — workspace detection, RFC ingestion, project
                              memory bootstrap. Folds in the parts of `ivy`
                              orchestrator that are pure routing.)
  experiment/                (NEW — IUT execution, pcap interpretation, NACT/NSCT.
                              Absorbs methodology + apt-attack-patterns context.)
  ivy-syntax/                (knowledge, retained)
  specification-patterns/    (knowledge, retained)
  verification-failures/     (knowledge, retained — used by spec-loop refine state)
```

Cuts implied: `triage-ops`, `meta-self-mod-ops`, `reference-drift`, `ivy-toolkit`
(content folds into Tool catalog inside spec-loop), `propagation-patterns` (folds into
spec-loop refine state), `apt-attack-patterns` (folds into experiment skill).
Critic-prompt machinery: collapses to one or two prompts ("verify state" + "refine
state"), not 10. Strong cut.

Audit work under Option B: heavier — five+ skills get rewritten or merged.
Justification: formal-spec survey §3 explicitly endorses verifier-in-the-loop
absorbing-Markov-chain as the natural shape; current ops carve unnaturally across
the loop's states.

### Option C — Two-loop (spec-author + experiment-run)

```
skills/
  spec-author-loop/          (NEW — same as Option B's spec-loop, scoped to
                              authoring an Ivy model. Markov subloop:
                              scaffold → propose → verify → interpret → refine.)
  experiment-run-loop/       (NEW — IUT campaign loop: configure → run → trace →
                              interpret → refine spec or report. Houses NACT/NSCT.)
  setup/                     (NEW — workspace + RFC + project memory shared by
                              both loops, with handoff protocol.)
  ivy-syntax/                (knowledge, retained for spec-author-loop)
  specification-patterns/    (knowledge, retained for spec-author-loop)
  verification-failures/     (knowledge, retained for both loops)
  apt-attack-patterns/       (knowledge, retained for experiment-run-loop)
```

Cuts implied: same as Option B plus an explicit handoff pattern between the loops.
Justification: separates the cognitive modes the user described in grilling
("designing the formal spec" vs. "running and understanding the experiments").
Cleanest mapping to user's stated goal.

Audit work under Option C: heaviest — two-loop pattern requires explicit
inter-loop handoff design; methodology skill survives as the cross-cutting
NCT/NACT/NSCT framing.

---

## Section 2 — Skills (14 entries)

Verdicts under the locked mode-first taxonomy. Confidence: HIGH = read in
full; MED = read frontmatter + body sample; LOW = inferred from inventory.

| Skill | Lines (body+refs) | Verdict | New role | Lens defended | Confidence | Action |
|---|---|---|---|---|---|---|
| `ivy` (orchestrator) | 197 + 10 critic_prompts (~1k) | **KEEP, RESHAPE** | Orchestrator entry, mode dispatch | L2 (presents AskUserQuestion mode pick), L3 (iron-law primer) | HIGH | Rename routing terminology from workflow-verbs to modes (scaffold/refine/experiment); fold g0+g0b critic prompts (overlap) and demote g7+g8 to maintainer |
| `build-ops` | 344 + 5 refs (~250) | **KEEP, RENAME** | scaffold-mode-ops | L1 (Ivy gap), L3 (NO_LAYER_WITHOUT_SCAFFOLD), L5 (NCT phase 2-7) | HIGH | Rename to `scaffold-ops`; phase numbering re-labeled to NCT phases 2–7 instead of generic Phase 1–7 |
| `verify-ops` | 461 + 6 refs (~400) | **KEEP, SPLIT** | refine-mode-ops + experiment-mode-ops | L1 (counterexample teach), L3 (NO_FIX_WITHOUT_VERIFY), L5 (NCT phases 8–10) | HIGH | Split: phases 8–9 (verify cycle) become `refine-ops`; phase 10 (IUT execution + analysis) becomes `experiment-ops`. Or document the split inline and rename — depends on how clean the section boundary is in the current 461-line body |
| `review-ops` | 364 + 0 refs | **KEEP, FOLD** | distributed across modes | L3 (NO_QUALITY_WITHOUT_COVERAGE), L5 (RFC coverage from formal-spec survey) | HIGH | Fold: phase-1 RFC analysis → scaffold-ops (NCT phase 1); phase-2 coverage gaps → refine-ops (NCT phase 9); G5 trace dispatch → experiment-ops (NCT phase 10). Does not stand alone as a mode but lives as cross-cutting capability |
| `triage-ops` | 387 + 1 ref (396) | **KEEP** (hidden) | Maintainer specialist | L3 (recovery contract), `mcp-tool-reliability.md` retry path | HIGH | No change. Already `user-invocable: false`. Backs `ivy-triage-agent`. |
| `meta-self-mod-ops` | 225 | **KEEP** (hidden) | Maintainer specialist | L3 (PLUGIN_3LOOP iron-law) | HIGH | No change. Already `user-invocable: false`. Backs `ivy-meta-agent`. |
| `methodology` | 36 + 5 refs (~850) | **KEEP, RESHAPE refs** | Knowledge skill | L1 (NCT/NACT/NSCT for non-expert), L5 (literature-anchored) | HIGH | `references/comprehensive-methodology-detail.md` (526 lines) duplicates content in `~/.claude/projects/<project>/memory/reference_nct_methodology.md`. Trim to a thin pointer or delete. Body is fine. |
| `ivy-syntax` | 65 + 5 refs (~870) | **KEEP** | Knowledge skill, auto-loaded on `.ivy` paths | L1 (Ivy 1.7 syntax for non-expert) | HIGH | No change. `paths: **/*.ivy` is correct; references are sized to what they teach. |
| `ivy-toolkit` | 36 + 7 refs (~1.4k) | **KEEP body, AUDIT refs** | Knowledge skill, single MCP tool source of truth | L3 (tool selection discipline) | HIGH (body), MED (refs) | Body is 36 lines and well-anchored. Refs total ~1.4k lines — the 528-line `tool-catalog.md` is a per-tool reference (parameters, returns, errors) and is appropriate at that size for 18 tools. Audit if any individual ref duplicates content in `.claude/rules/`. |
| `specification-patterns` | 77 + 2 refs (~270) | **KEEP** | Knowledge skill | L1 (14-layer template + 7-pattern library), L5 (literature) | HIGH | No change. Boundary with `ivy-syntax` is explicitly documented. |
| `propagation-patterns` | 81 + 1 ref (~91) | **KEEP** | Knowledge skill | L1 (ser/deser asymmetry teaching) | HIGH | No change. Loaded only when type changes affect serializers — appropriately on-demand. |
| `verification-failures` | 46 + 9 refs (~1.8k) | **KEEP, AUDIT one ref** | Knowledge skill, primary refine-mode reference | L1 (counterexamples opaque to non-expert), L3 (debugging methodology IS the fact-check) | HIGH | The 714-line `verifier_patterns.md` is a numbered append-only catalog cited by adversarial gates (#100s G1, #200s G2-G4, #300s G3, #400s G4, #500s G5) — appropriately large; do not trim. The other 8 refs map to specific lifecycle moments. KEEP all. |
| `apt-attack-patterns` | 34 + 2 refs (~280) | **KEEP** | Knowledge skill, experiment-mode for NACT | L1 (NACT for non-expert), L5 (NACT methodology paper) | HIGH | No change. `context: fork` already constrains loading to NACT work. |
| `reference-drift` | 200 | **KEEP** | Maintainer self-audit tool | L3 (the audit tool that catches the kind of staleness flagged in Section 0) | HIGH | No change. `user-invocable: true` correctly exposes to maintainer; protocol-engineer end user never sees it. |

**Section 2 net change:** 0 deletions, 1 split (verify-ops → refine-ops + experiment-ops), 1 rename (build-ops → scaffold-ops), 1 fold (review-ops distributes), 1 reshape (methodology refs trim by ~526 lines). The skill bloat hunt finds **less than expected** in skill bodies — most of the heavy machinery is well-defended infrastructure, not bloat. The real cuts live in scaffolding (Section 6) and the orchestrator's critic_prompts (Section 5).

## Section 3 — `.claude/rules/` (17 entries)

Auto-loaded rules. Verdicts measure whether each rule earns its always-on
context cost.

| Rule | Lines | Verdict | Lens defended | Confidence | Action |
|---|---|---|---|---|---|
| `iron-laws.md` | 230 | **KEEP** | L3 (NO_FIX_WITHOUT_VERIFY, NO_LAYER_WITHOUT_SCAFFOLD, NO_QUALITY_WITHOUT_COVERAGE, STALENESS_RULE), L5 (formal-spec verifier-in-the-loop) | HIGH | No change. Load-bearing. The `<iron-law>` blocks with `<branch>`/`<context>`/`<instructions>` and worked-application examples are exactly what the SWE-agent doc §5 prescribes for deterministic gates. |
| `journaling-contract.md` | 202 | **KEEP** | L4 (continuous-dev memory infrastructure) | HIGH | No change. Defines the workflow journal + active-workflow contract. Already implements per-protocol persistent memory under `.panther-ivy/`. |
| `agent-dispatch.md` | 154 | **KEEP** | L3 (failure recovery contract for agents) | HIGH | No change. Includes canonical `<dispatch-context>` schema, per-tier timeouts, AskUserQuestion-on-failure protocol. |
| `gate-verdicts.md` | 106 | **KEEP** | L3 (calibrated SOUND/UNSOUND/ABSTAIN), L5 (gate-discipline endorsement) | HIGH | No change. Anti-paraphrase rule is correctly phrased. |
| `mcp-tool-reliability.md` | 80 | **KEEP** | L3 (MCP failure recovery via ToolSearch + AskUserQuestion) | HIGH | No change. The auto-retry-via-ToolSearch pattern matches the user's auto-memory `feedback_mcp_deferred_tool_registry.md`. |
| `gap-markers.md` | 79 | **KEEP** | L3 (`[GAP: #NN]` contract for UNSOUND verdicts) | HIGH | No change. Per-format placement rules (`.ivy` `#`, `.yaml` comment, `.md` HTML comment, `.json` no-write) are exactly the discipline a non-expert needs. |
| `ivy-formatting.md` | 64 | **KEEP** | L1 (RFC citation discipline + Considerations block) | HIGH | No change. Currently auto-loaded; severity-systems table is canonical. |
| `plan-mode.md` | 55 | **KEEP** | L2 (plan-mode handling in human-control flow), L3 (G0 plan-gate) | HIGH | No change. |
| `output-style.md` | 36 | **KEEP** | L2 (hook-output prefixes give human visibility into what's happening) | HIGH | No change. Documents the 16-prefix marker table for hook injectors. |
| `postuse-hook-ordering.md` | 38 | **KEEP** | L3 (PostToolUse hook ordering contract) | HIGH | No change. Defines the strict 6-position hook order and why each position matters. |
| `review-anti-patterns.md` | 23 | **KEEP** | L2/L3 (red-flags table for review-ops) | HIGH | No change. Promoted from skill body per `feedback_autoload_rule_no_pointer_stub` — correct pattern. |
| `verify-anti-patterns.md` | 22 | **KEEP** | L2/L3 (red-flags table for verify-ops) | HIGH | No change. Same correct pattern. |
| `build-anti-patterns.md` | 22 | **KEEP** | L2/L3 (red-flags table for build-ops) | HIGH | No change. Same correct pattern. |
| `propagation-authority.md` | 13 | **KEEP** | L3 (`ivy_propagation` is single source of truth) | HIGH | No change. Tiny but content-bearing (3 specific rules), not a pointer-stub. |
| **`nct-methodology.md`** | 9 | **CUT or RESHAPE** | (none — pointer-stub) | HIGH | **Pointer-stub violating `feedback_autoload_rule_no_pointer_stub`.** Body is `invoke Skill(panther-ivy-plugin:methodology)`. Either delete the rule (rely on the user/agent invoking the skill themselves on intent) or fold the rule's `paths: **/*.ivy` glob into a thicker rule that has actual content. Confidence: HIGH for the violation; MED for the action (cut vs. fold). |
| **`ivy-patterns.md`** | 9 | **CUT or RESHAPE** | (none — pointer-stub) | HIGH | Same pattern as `nct-methodology.md`. Body is `invoke Skill(panther-ivy-plugin:ivy-syntax)`. Same fix. |
| **`insights.md`** | 7 | **CUT** | (none — empty placeholder) | HIGH | Empty placeholder ("Uncategorized learnings that may graduate"). Currently has no content under the heading. Either delete until first insight is captured, or convert to a `.gitkeep`-style placeholder without the auto-load `paths:` (so it doesn't burn context budget). |

**Section 3 net change:** 3 candidate cuts (nct-methodology, ivy-patterns, insights — all <10 lines each, total ~25 lines). Small absolute cut but cleans up a pattern violation that would otherwise mask future drift. 14 KEEPs are well-defended.

## Section 4 — Hooks (31 registrations across 12 events)

`hooks/hooks.json` declares 31 registrations using ~25 distinct scripts.
`observability/observe.py` is registered 11 times (one per event type) for
JSONL event capture. All hooks have a defended purpose; none are obvious
bloat. Verdicts grouped by function rather than per-script (per CLAUDE.md
"surface every issue with confidence" — repeated per-script KEEPs would
add noise without information).

| Hook group | Scripts | Verdict | Lens defended | Confidence |
|---|---|---|---|---|
| **Iron-law enforcement & gates** | `block-direct-ivy.sh` (PreToolUse:Bash), `post-write-ivy-lint.sh`, `assess-modeling.py` (G2), `assess-testspec.py` (G3), `record-workflow-error.py` (G4 + error journal), `assess-trace.py` (G5) | **KEEP all** | L3 (iron-law deterministic gate, anti-pattern catalog dispatches G2-G5 critics) | HIGH |
| **MCP / LSP health** | `check-mcp-health.py` (PreToolUse:mcp__.*ivy), `check-indexing-ready.sh`, `retry-ivy-mcp.py` (PostToolUseFailure), `cleanup-stale-pids.sh`, `wait-for-indexing.sh`, `cleanup-ivy-lsp.sh` (SessionEnd) | **KEEP all** | L3 (MCP-tool-reliability recovery contract), defends against the "MCP server disconnected" pattern from MEMORY.md | HIGH |
| **Workspace detection** | `detect-ivy-workspace.sh` (SessionStart), `check-workspace-scope.py` (PreToolUse:Write\|Edit) | **KEEP both** | L4 (continuous-dev workspace memory across sessions) | HIGH |
| **Journaling infrastructure** | `check-journaling-contract.py` (SessionStart), `cleanup-stale-workflow.py`, `inject-journaling-contract.py` (SubagentStart) | **KEEP all** | L4 (per-protocol persistent memory; this IS the PROJECT.md analog) | HIGH |
| **Tool-result rendering** | `render-tool-result.py` (PostToolUse on ivy_*) | **KEEP** | L1 (formats raw MCP output for non-expert), L3 (severity-system normalization) | HIGH |
| **Session lifecycle** | `record-session-end.py` (Stop), `render-summary.py` (Stop), `notify-mcp-disconnect.py` (Notification) | **KEEP all** | L4 (handoff memory), L3 (MCP disconnect notification) | HIGH |
| **Status line + context injection** | `post-write-workflow-aware.py` (PostToolUse:Write\|Edit\|Agent), `inject-using-plugin.sh` (SessionStart, 10 lines) | **KEEP both** but VERIFY `inject-using-plugin.sh` | L2 (mode/phase visibility via statusline), L4 (post-write workflow nudges) | HIGH (post-write-workflow-aware), MED (inject-using-plugin) |
| **Observability** | `observability/observe.py` (registered 11×), `observability/log_event.py` | **KEEP** | L4 (JSONL audit trail enables continuous-dev review), L5 (SWE-agent doc §5 functional eval gate analog — all tool calls captured for replay) | HIGH |

**`inject-using-plugin.sh` (10 lines)** — only one MED-confidence verdict. The
script is tiny (10 lines per inventory) and runs at SessionStart. Without
reading the script body I can't confirm whether it does meaningful work
or is a pre-refactor leftover. Recommendation: read it and either KEEP
with documentation in `output-style.md` (which already lists hook prefixes)
or CUT if it's a no-op. Confidence on KEEP: MED. Will be confirmed in
Section 7 cross-mode implications below.

**Section 4 net change:** 0 cuts pending the `inject-using-plugin.sh`
verification. The hook surface is well-disciplined. The 31 registrations
across 12 events is justified by infrastructure responsibility, not bloat.

## Section 5 — Agents (8 entries)

| Agent | Lines | Type | Verdict | Lens defended | Confidence |
|---|---|---|---|---|---|
| `ivy-builder-agent` | 60 | Specialist (opus) | **KEEP** | L1, L3 | HIGH — well-formed `<role>` + `<dispatch-context>` + output schema; preloads build-ops + 4 knowledge skills |
| `ivy-verifier-agent` | 60 | Specialist (opus) | **KEEP** | L1, L3 | HIGH — same shape; read-only on specs; preloads verify-ops + verification-failures |
| `ivy-reviewer-agent` | 64 | Specialist (opus, xhigh effort, local memory) | **KEEP** | L3, L5 | HIGH — same shape; renders verdicts only, file edits forbidden |
| `ivy-triage-agent` | 57 | Specialist (opus, background) | **KEEP** | L3 | HIGH — backgrounded for parallel infrastructure repair; backed by triage-ops |
| `ivy-meta-agent` | 50 | Maintainer (opus) | **KEEP** | L3 (PLUGIN_3LOOP) | HIGH — only agent allowed to write inside plugin source; backed by meta-self-mod-ops |
| `g-plan-critic` | 82 | Critic (opus) | **KEEP** | L2 (calibrated abstain), L3 (CITATION_PASS/FAIL/ABSTAIN spot-check mandate) | HIGH |
| `g-fidelity-critic` | 79 | Critic (sonnet) | **KEEP** | L2, L3 | HIGH — same spot-check methodology |
| `g-knowledge-critic` | 65 | Critic (sonnet) | **KEEP** | L4 (continuous-dev knowledge capture), L2 | HIGH — KEEP/DROP/DEFER per candidate + batch verdict |

**Section 5 net change:** 0 cuts. All 8 agents have well-formed capability
contracts per `feedback_agent_orchestrator_three_layer_split.md`. The 5 specialists
+ 3 critics is the right shape under the locked mode-first design. The
README claim of "3 agents" is stale (Section 0 finding).

## Section 6 — Commands and scaffolding

### Section 6a — Commands (2 + README)

| Artifact | Lines | Verdict | Lens | Confidence | Action |
|---|---|---|---|---|---|
| `commands/nct-iut-test.md` | 110 | **KEEP** | L1 (PASS/FAIL templates aid non-expert), L3 (MCP-tool-reliability error handling) | HIGH | No change. Outcome templates are pedagogical. |
| `commands/nct-health.md` | 31 | **KEEP** | L3 (dispatches triage agent for 9-step runbook) | HIGH | No change. |
| `commands/README.md` | 31 | **CUT or RESHAPE** | (none — stale, claims 7 commands, only 2 exist) | HIGH | Same staleness pattern as plugin README (Section 0). Either delete (let Claude listing the directory be authoritative) or regen from on-disk truth. Better: regen at install/build time so it cannot drift again. |

### Section 6b — `output-styles/`

| Artifact | Lines | Verdict | Lens | Confidence | Action |
|---|---|---|---|---|---|
| `output-styles/ivy-guided.md` | 35 | **KEEP** | L1/L2 (verbose pedagogical output style; this conversation runs under it) | HIGH | No change. Active output style; harness loads it. |

### Section 6c — `styles/` (rendering machinery)

| Artifact | Lines | Verdict | Lens | Confidence | Action |
|---|---|---|---|---|---|
| `styles/README.md` | 34 | **KEEP** (verify) | L1 (style system index) | MED | Read to confirm contents |
| `styles/overlays/workflow-{navigate,build,verify,review,triage}.md` (5 files, ~150 lines total) | 27–38 each | **CUT or RENAME** | (failed — keys to dead workflow names) | HIGH | All 5 files are keyed to pre-refactor workflow verbs. Under mode-first design, the keys should be `mode-{scaffold,refine,experiment}.md` plus a maintainer-mode entry. Rename + content rewrite, OR cut entirely if styles are no longer driven from these files. |
| `styles/summaries/workflow-{navigate,build,verify,review,triage}.md` (5 files, ~95 lines total) | 15–23 each | **CUT or RENAME** | (failed — same dead-name issue) | HIGH | Same as overlays. |
| `styles/tool-renderers/ivy_{compile,quality,verify,verdict,diagnostics,coverage}.md` (6 files, ~190 lines total) | 23–68 each | **KEEP** | L1 (per-tool rendering rules for `render-tool-result.py`) | HIGH | No change. These are tool-result formatting templates and are independent of workflow-name drift. |

**Status note (2026-05-01):** Beyond the rename, the styles pipeline
itself is dormant: `hooks/scripts/compose-style.py` is in
`.backup/2026-04-28/`, no hook invokes style composition, and the
seven mode-first files do not exist. The "CUT or RENAME" verdict on
the five overlay and five summary files stands; the additional revive
work is documented in Review-side correction 8 and Section 7 row 4.

### Section 6d — `evals/`

| Artifact | Lines | Verdict | Lens | Confidence | Action |
|---|---|---|---|---|---|
| `evals/g{1..5}_trigger_eval.json` (5 files, 28 lines each) | 28 | **CUT or RESHAPE** | (per `reference_panther_ivy_evals_manual.md`, manual-only adversarial-gate dispatch tests, not pytest-runnable) | HIGH | Per MEMORY.md, these are NOT automated evals; they're manual probes. Either fold into a single `evals/README.md` documenting the manual procedure, or cut. The current 5-file × 28-line structure implies automation that doesn't exist. |

### Section 6e — `docs/`

| Artifact | Lines | Verdict | Lens | Confidence | Action |
|---|---|---|---|---|---|
| `docs/skill-audit-2026-04-27.md` | 263 | **CUT (move to .backup/)** | (pre-refactor audit draft) | HIGH | Per-file approval required (`feedback_no_relocate_backup_files.md`). User approves move to `.backup/2026-05-01/`. |
| `docs/superpowers-audit-2026-04-27.md` | 315 | **CUT (move to .backup/)** | (pre-refactor audit draft, references superpowers/specs/ which is forbidden in plugin per `feedback_no_superpower_specs_in_skills.md`) | HIGH | Same per-file approval. |

### Section 6f — `tests/`

| Artifact | Lines | Verdict | Lens | Confidence | Action |
|---|---|---|---|---|---|
| `tests/*.py` (18 test files, ~3,500 lines) | varies | **KEEP** | L3 (pytest test suite for hook scripts and rendering machinery) | MED | No change recommended without deeper read. The tests are scoped to hook scripts (`test_hooks.py` 442, `test_workflow_state.py` 426, `test_observability.py` 415, `test_routing.py` 264, `test_render_*` 265+133, `test_gate_hooks.py` 294, `test_workspace_detection.py` 393, etc.) — they earn their keep as the deterministic eval layer the SWE-agent doc §5 prescribes. Confidence on KEEP: MED until any specific test is shown to be testing dead code. |
| `tests/statusline/run-tests.sh` | 395 | **KEEP** | L3 (statusline integration tests) | MED | Same justification. |

### Section 6g — `scripts/`

| Artifact | Lines | Verdict | Lens | Confidence | Action |
|---|---|---|---|---|---|
| `scripts/migrate_legacy_workflow.py` | 151 | **CUT (after a deprecation window)** | (one-shot migration script per `feedback_no_backward_compat_shims`) | MED | Migration scripts are intentionally one-shot. If the migration has been applied to all live PROJECT.md files, this can be cut. If unsure, leave for one more cycle then cut. |
| `scripts/start-{ivy-server,serena}.sh` | 228, 144 | **KEEP** | L3 (MCP server startup) | HIGH | No change. |
| `scripts/workspace-common.sh` | 138 | **KEEP** | L3 (shared workspace functions for hook scripts) | HIGH | No change. |
| `scripts/statusline/*` (multiple) | varies | **KEEP** | L2 (status line widget producing Mode/Phase visibility) | HIGH | No change. Backs the locked mode-first status line from Section 1. |

**Section 6 net change:** ~5–6 candidate cuts: Commands README (regen), 5
overlays + 5 summaries (rename or cut, ~245 lines), evals/ (consolidate
or cut, ~140 lines), 2 audit drafts in docs/ (move to .backup/, ~580 lines),
migrate_legacy_workflow.py (cut after deprecation, 151 lines). Total
~1,100 lines of identifiable bloat in scaffolding alone.

## Section 7 — Cross-mode implications under the locked taxonomy

The mode-first design (scaffold / refine / experiment + hidden triage,
meta) requires the following non-cut work to operationalize the audit's
verdicts:

1. **Rename `build-ops` → `scaffold-ops`**, update all citations in
   rules (`build-anti-patterns.md` paths glob, `journaling-contract.md`
   surface taxonomy, `iron-laws.md` workflow column, `agent-dispatch.md`
   per-tier table, `output-style.md` marker prefix `[ivy-build]` →
   `[ivy-scaffold]`).
2. **Split `verify-ops` → `refine-ops` + `experiment-ops`**, update all
   citations in rules and the orchestrator's routing table. The verify
   anti-patterns rule splits accordingly.
3. **REFUTED — see Review-side correction 7.** `review-ops` stands
   alone as a workflow with a load-bearing `ivy-reviewer-agent`. The
   remaining work is normalizing drifted `model-reviewer` citations
   (rename residue) to `ivy-reviewer-agent`. `review-anti-patterns.md`
   was already moved to
   `.backup/rules-anti-patterns-fold-2026-05-01/` in an earlier
   commit; no further action required on the rule file.
4. **Revive the styles pipeline.** See Review-side correction 8. The
   work is: (a) restore `hooks/scripts/compose-style.py` from
   `.backup/2026-04-28/`, (b) register a UserPromptSubmit matcher in
   `hooks/hooks.json` invoking it, (c) create seven mode-first overlay
   files (`overlays/{navigate,scaffold,refine,experiment,review,triage,meta}.md`)
   and seven mode-first summary files
   (`summaries/{navigate,scaffold,refine,experiment,review,triage,meta}.md`),
   (d) retire the five orphan `workflow-*.md` overlays and five orphan
   `workflow-*.md` summaries to `.backup/`.
5. **Add `experiment-mode` skill body** (currently this work lives
   distributed across verify-ops + review-ops + methodology refs).
6. **Update `routing-rules.json`** if it survives Section 1c Axis 7 —
   from workflow-verb cold-start classification to mode cold-start
   classification.
7. **Regenerate `README.md`, `commands/README.md`, `skills/README.md`,
   `agents/README.md`, `hooks/README.md`** from on-disk truth. Section 0
   findings.
8. **Verify `inject-using-plugin.sh`** is not a pre-refactor leftover
   (Section 4 MED-confidence).

This is **NOT a series of cuts** — it is the rename + reshape work that
the locked taxonomy requires. The audit's value is the kill list **plus**
this transition checklist. Per `feedback_no_relocate_backup_files.md`,
every cut and every rename moving content to `.backup/` requires per-file
user approval before execution.

## Section 8 — Parking lot (capabilities requiring `ivy-tools` MCP changes)

The change envelope (Phase B Section 1c) included `plugin + ivy-tools MCP`.
The items below are **missing capabilities** that would lift plugin behavior
under the locked mode-first design but require touching the upstream
`ivy-lsp` repo (where ivy-tools MCP lives), not the plugin tree. Each item
is anchored to a citation in the SWE-agent doc or the formal-spec survey.

### Item A — Machine-readable counterexample envelope

**Citation:** Formal-spec survey §3 (Theoretical Foundations of Verifier-in-
the-Loop Architectures), §4 (Machine-Readable Error Feedback and Type Systems).

**Current state (Agent D finding):** `ivy_check` emits human-readable
counterexample text. `ivy_analysis_mixin.py` parses via `assumption_failed`
regex and reduces to a four-value verdict enum. Z3 emits S-expressions
internally but they're not surfaced.

**Proposed:** New MCP tool `ivy_verify(... compact=False)` returns a
structured envelope:

```json
{
  "verdict": "FAIL",
  "isolate": "quic_server_test_handshake",
  "failing_invariant": "conn_established",
  "witness_path": [
    {"action": "init", "state": {...}},
    {"action": "handle_initial", "state": {...}},
    {"action": "handle_retry", "state": {...}}
  ],
  "var_bindings": {"scid": 0x1234, "dcid": 0x5678},
  "rfc_clause_hint": "[rfc9000:7.2.4]",
  "last_action_before_fail": "handle_retry",
  "raw_human_readable": "<original ivy_check output>"
}
```

**Lift:** Refine-mode's counterexample interpreter (per the locked g4-verify
critic) consumes structured fields directly. LLM-driven refinement loops
the formal-spec survey §3 prescribes converge faster on structured input.

**Blast radius:** Changes to `ivy_lsp/mcp/tools/verify.py` + a new
counterexample parser. Not a plugin tree change.

### Item B — RFC retrieval as a structured MCP tool

**Citation:** Formal-spec survey §RAG vs. Fine-Tuning ("RAG modulates model
competence by surfacing the exact normative text the model needs"); SWE-agent
doc §1 (graph-based retrieval over structural indexes).

**Current state:** Plugin asks the agent to grep RFC files in the worktree
or to use WebFetch. Section 0c Agent B literature says citation discipline
is core to NCT (every monitor cites `[rfcNNNN:X.Y]`). Currently the
discipline is enforced by the `ivy-formatting.md` rule but the retrieval
step is ad-hoc.

**Proposed:** Existing `ivy_rfc(mode="get|search|section")` tool already
covers some of this — see if it exposes structured chunks with citation
metadata. If not, extend it. Schema:

```json
ivy_rfc(query="hold time validation", rfc_id="4271", section="6.5")
→ {
  "chunks": [
    {
      "rfc_id": "4271",
      "section": "6.5",
      "title": "Hold Timer Expired Error Handling",
      "verbatim": "If a system does not receive successive KEEPALIVE...",
      "normative_terms": ["MUST", "SHOULD"],
      "citation_handle": "[rfc4271:6.5]"
    }
  ]
}
```

**Lift:** Scaffold-mode Phase 1 (RFC ingestion) becomes a precise tool call
instead of grep + paraphrase. Anti-paraphrase enforcement gets easier.

**Blast radius:** Already partially implemented in `ivy_rfc`. Verify by
reading `ivy_lsp/mcp/tools/rfc.py`. Likely a small extension.

### Item C — Compile-error semantic re-shaping

**Citation:** Formal-spec survey §Local Granularity and Credit Assignment
("verifier feedback most useful when localized to specific Ivy construct").

**Current state:** `ivy_compile` returns raw `ivyc` output as a `raw_output`
field. The 8-step pre-fix debugging methodology in
`verification-failures/references/debugging-methodology.md` parses this
manually.

**Proposed:** New MCP tool field `error_summary` (already partially present
per `ivy_compile` schema in tool-catalog.md):

```json
{
  "error_summary": [
    {
      "isolate": "quic_packet_parse",
      "construct": "before action handle_initial",
      "pattern_id": "#205",
      "pattern_name": "Type mismatch on action parameter",
      "file_line": "quic_packet.ivy:127",
      "suspected_fix_class": "type_coercion | guard_addition | invariant_relaxation",
      "raw_excerpt": "..."
    }
  ]
}
```

**Lift:** Build/scaffold and refine modes get a pre-classified failure
shape that maps directly to `verification-failures/references/verifier_patterns.md`
catalog entries. The 8-step debugging methodology becomes a 3-step lookup.

**Blast radius:** `ivy_lsp/mcp/tools/compile.py`. A pattern-id classifier
trained on the existing `verifier_patterns.md` catalog (~714 entries covering
G1–G5).

### Item D — Async-drafting HITL surface

**Citation:** SWE-agent doc §4 (HITL UX Patterns: synchronous blocking vs.
asynchronous drafting).

**Current state:** Plugin HITL is fully synchronous via `AskUserQuestion`.
Per the locked Section 1b, fact-check critics surface FAIL on the same
turn. For continuous dev across sessions, the user might want to leave
work in a draft state and come back hours later.

**Proposed:** Not strictly an `ivy-tools` MCP change; this is a Claude Code
harness limitation. The plugin's existing `pending_dispatch` mechanism in
the journal-contract is the closest analog — it persists work intent across
turn boundaries. Could be extended to support a "draft-and-review" pattern:
the orchestrator emits a `draft_pending_review` journal event with a
proposed diff, and the user picks it up in the next session. Not blocked
on MCP; blocked on plugin-side discipline.

**Lift:** Cross-session continuity (lens L4) at higher fidelity.

**Blast radius:** Plugin-tree only — but listed here because the SWE-agent
doc §4 framing is the motivation. Demote to Phase C reshape candidate?

### Item E — Functional eval gate for proposed model edits

**Citation:** SWE-agent doc §5 (LLMOps Quality Assurance: deterministic
linting + functional evaluation + LLM-as-judge hybrid).

**Current state:** `NO_FIX_WITHOUT_VERIFY` iron law forces a fresh
`ivy_verify` per turn, which is the closest analog. Plus 18 tests in
`tests/` exercise hook scripts. But there's no "diff this proposed model
edit against the working tree, run only the affected verifies in a sandbox,
report PASS/FAIL before committing" tool.

**Proposed:** New MCP tool `ivy_verify_diff(target_path, since_ref="HEAD")`:

```json
ivy_verify_diff(target_path="protocol-testing/bgp/bgp_stack/bgp_connection.ivy",
                since_ref="HEAD")
→ {
  "affected_isolates": ["bgp_connection_test", "bgp_speaker_test"],
  "verify_results": [
    {"isolate": "bgp_connection_test", "verdict": "PASS"},
    {"isolate": "bgp_speaker_test", "verdict": "FAIL", "counterexample": {...}}
  ],
  "regression": true,
  "duration_seconds": 14.2
}
```

**Lift:** A pre-commit gate analogous to the SWE-agent doc §5
"Functional Evaluation: Sandboxed code execution and unit tests".
Catches regressions automatically before the human reviews the diff.

**Blast radius:** Significant new logic in `ivy_lsp/mcp/tools/`. Could
build on top of existing `ivy_verify` plus a git-aware include-closure
analyzer (the existing `ivy_analysis(mode=includes)` is the start).

### Item F — Distilled RAG over the verifier-pattern catalog

**Citation:** Formal-spec survey §"The Synergy of Distilled RAG"
("retrieve the closest precedent fix from a curated catalog of past
counterexamples").

**Current state:** `verification-failures/references/verifier_patterns.md`
is a 714-line append-only numbered catalog. The agent reads the whole file
on entry; pattern lookup is by string match.

**Proposed:** New MCP tool `ivy_pattern_match(counterexample_envelope)`:

```json
ivy_pattern_match({"isolate": "...", "failing_invariant": "...", ...})
→ {
  "best_match": {
    "pattern_id": "#412",
    "pattern_name": "Incorrect Monitor Scope",
    "similarity_score": 0.87,
    "canonical_fix_excerpt": "..."
  },
  "near_matches": [...]
}
```

**Lift:** Refine-mode's counterexample interpreter consumes a top-N
match list directly instead of grepping the catalog. Especially valuable
when the catalog grows past 1k entries.

**Blast radius:** New tool + an embedding/index over `verifier_patterns.md`.
Requires upstream MCP change; current MCP doesn't have an embedding stack.

**Section 8 net additions to backlog:** 6 items (A–F). Items A, B, C, F
are direct ivy-tools MCP work. Item D is plugin-side (move under Phase C
reshape). Item E is significant new MCP tool work but builds on existing
primitives. None block the audit's cut list — they're forward-looking
capability extensions.

## Phase E — Self-review of the audit report

Run against the spec checklist from the plan file:

| Check | Result |
|---|---|
| 1. Placeholders / TODOs gone | PASS — no `TBD`, `TODO`, or `FIXME` markers in the report. |
| 2. Verdict table internally consistent | PASS — no file appears in both KEEP and CUT. The verify-ops SPLIT verdict is internally consistent (refine + experiment ops). |
| 3. Reference-doc citations resolve | PASS — Section 0c citations were verified by Agent B (McMillan & Zuck SIGCOMM'19, Rousseaux et al FORTE'24, Crochet et al NordSec'24). Section 8 citations to formal-spec survey §3, §4, §RAG and SWE-agent doc §1, §4, §5 match the headings I extracted from the survey markdown. |
| 4. Each KEEP defends ≥1 lens | PASS — every KEEP cell in Sections 2–6 cites at least one of L1–L5. |
| 5. Each CUT names the failed lens AND the endorsement-or-misalignment | PASS — `nct-methodology.md`, `ivy-patterns.md`, `insights.md` cuts cite `feedback_autoload_rule_no_pointer_stub`. The 5 styles/overlays + 5 summaries cuts cite "keys to dead workflow names" (Section 0b). The 2 docs/ audit drafts cite pre-refactor + `feedback_no_superpower_specs_in_skills`. README cuts cite Section 0 staleness. evals/ cut cites `reference_panther_ivy_evals_manual.md`. |

**Self-review verdict:** SOUND. The audit report is internally consistent
and ready for user review (Phase F).

**Open MED-confidence items still to verify** before any cut is executed:
1. `inject-using-plugin.sh` (Section 4) — verify it's not a pre-refactor
   leftover. Read the 10-line script body in Phase F.
2. `routing-rules.json` (Section 1d) — verify it earns its keep under
   the mode-first cold-start fallback. Read in Phase F.
3. Tests directory (Section 6f) — KEEP at MED confidence; spot-check
   that no specific test exercises dead code.
4. `ivy-toolkit/references/tool-catalog.md` (528 lines) — verify the
   18-tool catalog still matches `ivy_lsp/mcp/tools/__init__.py` (the
   tool-catalog itself says "Timeout, Tier, and Rendering values come
   from `_TOOL_TIMEOUTS` and `_TOOL_METADATA`"; drift check possible).

## Considerations

**Pro:**
- Audit's actual cut list (~1,100 lines of identifiable bloat in
  scaffolding + 25 lines in pointer-stub rules) is concrete and per-file
  approvable.
- The locked mode-first taxonomy is empirically grounded in four agent
  investigations (panther_ivy git history, NCT literature, PANTHER core,
  Ivy test-gen pipeline) instead of synthesized from generic reference
  docs.
- Per-file confidence levels let the user prioritize approval review.
- Parking lot (Section 8) gives an actionable backlog for the upstream
  `ivy-lsp` repo without polluting the plugin-tree audit with
  unactionable wishes.

**Con:**
- Bigger lift than I initially scoped: rename + reshape work in
  Section 7 is non-trivial and requires coordinated edits across rules,
  hooks, agent files, and skill bodies. The audit's value is the kill
  list **plus** this transition checklist.
- Five MED-confidence verdicts remain (`inject-using-plugin.sh`,
  `routing-rules.json`, tests/, tool-catalog.md drift, `methodology`
  comprehensive-detail trim). These need spot-checks before any cut.
- The audit does not propose adding any new skills, hooks, or agents
  for the experiment-mode work; that's a Phase-7 reshape that needs its
  own design pass, not a cut decision.

**Alternatives considered:**
- Compressed Phase C (8–12 highest-confidence cuts only) was offered
  earlier and declined; the user explicitly chose the full-coverage
  audit. This report honors that choice.
- A pure scorecard against the SWE-agent doc was the third audit shape
  offered in Q6 grilling and declined — would have produced citation-heavy
  defensive review without identifying actionable cuts.
- An upstream-only audit focused on the parking lot was offered in the
  pivot question and declined — the user wanted the cut list inside
  the plugin tree first.
