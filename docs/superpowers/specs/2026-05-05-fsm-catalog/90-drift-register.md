# 90 — Drift Register

This file consolidates every audit-only drift finding from Wave 1 (Explorers A/B/D) and Wave 2 (Explorers C/E). Categories are a closed set:

1. **Vocabulary + state drift** — same concept named differently across surfaces; states present in code but unenumerated in any doc.
2. **Transition drift** — transitions in code but not in prose; or in prose without code wiring.
3. **Guard drift** — undocumented preconditions on transitions.
4. **Recovery drift** — failure-mode edges in rules without ops-skill prose, or vice versa.

`severity_note` values: `doc-gap` (documentation completeness), `runtime-ambiguity` (could cause confusion at runtime), `unimplemented-feature` (documented in design but no visible code path), `intentional` (acknowledged-as-intentional design decision; recorded for traceability). No fix proposals.

## Drift table

| ID | category | title | locations | evidence_quote | severity_note | fsm_refs | closed_by |
|---|---|---|---|---|---|---|---|
| DR-01 | Vocabulary + state drift | `navigate` identity in enum but absent from mode picker | `hooks/scripts/lib/workflow_state/context.py:103-109` ↔ `skills/ivy/SKILL.md:89-91` | `_KNOWN_WORKFLOWS = frozenset({"navigate", "scaffold", "refine", "experiment", "review", "triage", "meta"})` vs `> Which mode?\n> - **Scaffold** (NCT phases 1–7)\n> - **Refine** (NCT phases 8–9)\n> - **Experiment** (NCT phase 10)` | doc-gap | fsm-w0 | |
| DR-02 | Transition drift | warm-resume `phase_hint` consumption rules undocumented | `.claude/rules/journaling-contract.md:84-86` ↔ §2 lifecycle DOT | `phase_hint (str)` declared optional with no consumer-side rule for inferring resume phase when absent | doc-gap | fsm-w0 | |
| DR-03 | Guard drift | G4 dispatch responsibility split inline vs hook backstop | `skills/refine-ops/SKILL.md:126-140` ↔ `hooks/scripts/record/workflow-error.py:105-132` | `<HARD-GATE> The PostToolUse hook on ivy_verify is a backstop — the refiner is responsible for inline dispatch and must not defer to the hook for the primary G4 invocation. </HARD-GATE>` | runtime-ambiguity | fsm-w1-scaffold, fsm-w2-refine, fsm-g4 | |
| DR-04 | Recovery drift | attempt-counter cap split between Phase 3 (recompile) and Phase 7 (fix) | `skills/refine-ops/SKILL.md:98-104` ↔ `skills/refine-ops/SKILL.md:220-256` | `If the user agrees, apply the fix, then loop back to Phase 3 (recompile). The Phase 7 attempt-counter applies to recompile loops as well — increment on each retry.` (Phase 3 references the counter without integrating with Phase 7's formal evaluation) | runtime-ambiguity | fsm-w2-refine | |
| DR-05 | Vocabulary + state drift | `progress` event payload `{detail}` vs `{kind, ...}` mutual-exclusivity unspecified | `.claude/rules/journaling-contract.md:73-77` | `\| progress \| detail (str) OR kind (str) + kind-specific fields \| varies by kind \| ops-skill \|` (no rule on what happens if both are provided) | doc-gap | fsm-w0 |
| DR-06 | Vocabulary + state drift | ABSTAIN as first-class verdict but absent from eval expectations | `.claude/rules/journaling-contract.md:82` + `.claude/rules/ivy-formatting.md` Severity Systems ↔ `evals/gate_critic_outcome_eval.json` | `verdict` documented as `sound|unsound|abstain`; eval JSON only lists SOUND/UNSOUND outcomes | doc-gap | fsm-g0c-canonical |
| DR-07 | Transition drift | G0b plan-fidelity gate documented but no dispatch code path | `skills/ivy/SKILL.md:143` (narrative) + `agents/g-fidelity-critic.md:2` ↔ no explicit code path | "First action after G0 SOUND" narrative without `if plan_approved and not g0_verdict` guard in visible code | unimplemented-feature | fsm-g0b | Closed 2026-05-05 by `docs/superpowers/specs/2026-05-05-g0b-g6-design.md`; impl: plugin commit 474f2da (G0b PostToolUse dispatcher + `hooks.json` restructure); full plan in `docs/superpowers/plans/2026-05-05-g0b-g6-wiring.md`. |
| DR-08 | Transition drift | G6 knowledge gate documented but no Stop-hook dispatch | `skills/ivy/SKILL.md:243` + `.claude/rules/journaling-contract.md:85` ↔ `hooks/scripts/record/session-end.py`, `render/summary/main.py` | Documented as "before exiting / Stop hook context"; no Stop hook dispatches `g-knowledge-critic`; orchestrator owns G6 implicitly | unimplemented-feature | fsm-g6 | Closed 2026-05-05 by `docs/superpowers/specs/2026-05-05-g0b-g6-design.md`; impl: plugin commit e3dcb4b (SKILL.md G6 detection branch in Phase 1.5); full plan in `docs/superpowers/plans/2026-05-05-g0b-g6-wiring.md`. |
| DR-09 | Transition drift | G7/G8 critic-prompt templates cited but wiring unverified | `evals/gate_critic_outcome_eval.json:62, 71` ↔ `skills/triage-ops/SKILL.md` | `verbatim_prompt_template: skills/ivy/references/critic_prompts/g7_triage_diag.md` referenced in eval but no code in triage-ops confirms template loading | doc-gap | fsm-g7, fsm-g8, fsm-w5-triage | |
| DR-10 | Transition drift | G4 dual dispatch | `hooks/scripts/record/workflow-error.py:110` (hook) ↔ `skills/refine-ops/SKILL.md:127` (ops-skill) | Both surfaces write `gate_dispatched` events for the same `ivy_verify` return; idempotency unclear | runtime-ambiguity | fsm-g4 | |
| DR-11 | Guard drift | G2 vs G3 catalog slice ranges differ; precondition documentation absent | `gate_handlers.py:188` (G2: #200-249, #250-299, #260-289 NSCT) ↔ `gate_handlers.py:266` (G3: #200-208, #256-259, #300-399) | Same `verification-failures` skill but different slice ranges; precondition not documented in dispatch code | doc-gap | fsm-g2, fsm-g3 | |
| DR-12 | Guard drift | G4 status-field mapping inconsistency | `hooks/scripts/record/workflow-error.py:32` (`"success":"false"`) ↔ `ivy_verify` returns `{status: OK|FAIL}` | Hook checks `success` field; `ivy_verify` returns `status` field | runtime-ambiguity | fsm-g4 |
| DR-13 | Guard drift | G5 critic context artifact-rich but verdict spec-only | `gate_handlers.py:360-365` (artifact dict to critics) ↔ `gate_handlers.py:372` (verdict targets spec file) | "write [GAP:] markers at spec file:line locations (not artifact paths)"; instruction-order ("analysis_results.json → compile log → ivy_tester.log → IUT log → pcaps") not enforced by guard | doc-gap | fsm-g5 | |
| DR-14 | Recovery drift | G0b UNSOUND branch undocumented | `agents/g-fidelity-critic.md` ↔ `skills/ivy/SKILL.md` (no UNSOUND branch for G0b) | "≥2 UNSOUND → halt" per `parallel-dispatch.md:21` but no ops-skill code halts on G0b UNSOUND; orchestrator logic exists undocumented | doc-gap | fsm-g0b | Closed 2026-05-05 by `docs/superpowers/specs/2026-05-05-g0b-g6-design.md`; impl: plugin commit d78de2b (gate-verdicts.md G0b H3 section documenting UNSOUND routing prose); full plan in `docs/superpowers/plans/2026-05-05-g0b-g6-wiring.md`. |
| DR-15 | Recovery drift | G4 ABSTAIN routing missing from refine-ops | `skills/refine-ops/SKILL.md:179-181` ↔ `.claude/rules/gate-verdicts.md` | `gate-verdicts.md` documents "refine-ops: ABSTAIN on G4 → Phase 6 Diagnose using `abstain_reason`"; refine body reads as if only PASS/FAIL exist | doc-gap | fsm-w2-refine, fsm-g4 | |
| DR-16 | Recovery drift | critic-timeout handling split between ops-skills and hooks | `.claude/rules/agent-dispatch.md` (canonical recovery) ↔ `gate_handlers.py` (hook-dispatched G2/G3/G5 lack timeout-recovery code) | Ops-skill inline dispatches implement recovery; hook-dispatched gates emit directives but no timeout-recovery logic visible — deferred to Claude agent | doc-gap | fsm-g2, fsm-g3, fsm-g5 | |
| DR-17 | Vocabulary + state drift | `subagent_type` orchestrator-to-hook signal absent from `<dispatch-context>` schema | `hooks/scripts/journaling/contract-inject.py:76` ↔ `.claude/rules/agent-dispatch.md:10-55` | Hook gates injection on `subagent_type`; schema documents agent-author-facing fields without cross-referencing the orchestrator-to-hook signal | doc-gap | fsm-d1-dispatch | |
| DR-18 | Guard drift | `ivy-reviewer-agent` retry-narrowing on `context_exhaustion` documented in rule but not agent file | `.claude/rules/agent-dispatch.md:111` ↔ `agents/ivy-reviewer-agent.md` (no Failure Modes section) | "Per-agent Failure Modes sections may narrow the transient set (e.g., ivy-reviewer-agent disables auto-retry on context_exhaustion...)" referenced but agent file omits the section | doc-gap | fsm-d2 | |
| DR-19 | Transition drift | `tool_not_found` boundary between agent-dispatch and mcp-tool-reliability not formally defined | `.claude/rules/agent-dispatch.md:89-90` ↔ `.claude/rules/mcp-tool-reliability.md:23-30` | Two rules document overlapping failure space without explicit partition; `agent-dispatch.md` §6 line 160 acknowledges overlap but doesn't formalise | doc-gap | fsm-d3-recovery | |
| DR-20 | Recovery drift | agent-level vs MCP-level retry layer ordering unstated | `.claude/rules/agent-dispatch.md:111` ↔ `.claude/rules/mcp-tool-reliability.md:65-69` | Agent-dispatch documents agent-level auto-retry; mcp-tool-reliability documents tool-level auto-retry; reader cannot tell whether layers are sequential or parallel | doc-gap | fsm-d3-recovery | |
| DR-21 | Vocabulary + state drift | `explicit_error` vs `malformed_output` classification ambiguous | `.claude/rules/agent-dispatch.md:90` ↔ `.claude/rules/agent-dispatch.md:88` | "the agent raised an error or emitted a failure message" lacks operational distinction from "malformed_output (output unparseable)" | doc-gap | fsm-d3-recovery | |
| DR-22 | Vocabulary + state drift | specialist agents do not cross-reference critic VERDICT shape | All six `agents/ivy-*-agent.md` Output schema sections ↔ `.claude/rules/journaling-contract.md` §6.2 | Specialists cite §6.1 specialist JSON shape; no cite of §6.2 critic VERDICT shape | doc-gap | fsm-d2, fsm-d4-return-shape | |
| DR-23 | Vocabulary + state drift | `_VALID_EVENT_TYPES` parity between hook-side and MCP-side | `hooks/scripts/lib/workflow_state/context.py:80-94` ↔ `ivy_lsp/mcp/tools/workflow_state.py:27-43` | Both contain 13 active types; parity enforced by `tests/test_event_types_parity.py` (referenced in context.py docstring line 4); cardinality OK; runtime rejection of invalid type is silent (`append_journal_event` returns False) — drift caught by review, not validator | intentional | fsm-h0-canonical, fsm-p2-journal, fsm-m3-workflow-state | |
| DR-24 | Guard drift | `append_journal_event` read-modify-write without fcntl locking | `hooks/scripts/lib/workflow_state/journal.py:22-71` ↔ `.claude/rules/journaling-contract.md` §4.2 | Sequential-write assumption explicit in contract; `append_journal_event` does read, modify, write without locking; under parallel dispatch, later write silently drops earlier entry | runtime-ambiguity | fsm-p2-journal | |
| DR-25 | Guard drift | `is_workflow_stale` returns True on ValueError | `hooks/scripts/lib/workflow_state/active.py:158-176` ↔ `.claude/rules/journaling-contract.md` §9 | `datetime.fromisoformat(str(started_raw))` returns True on parse failure (fail-safe); not listed as known error path in `journaling-contract.md` §9 | doc-gap | fsm-p1-active-workflow | |
| DR-26 | Vocabulary + state drift | PROJECT.md `VALID_MODES` is 4-member subset of `_KNOWN_WORKFLOWS` | `hooks/scripts/lib/project_md_state.py:50` ↔ `hooks/scripts/lib/workflow_state/context.py:103-109` | `VALID_MODES = {scaffold, refine, experiment, idle}` (4) vs `_KNOWN_WORKFLOWS = {navigate, scaffold, refine, experiment, review, triage, meta}` (7); navigate/review/triage/meta not representable in mode field | doc-gap | fsm-p3-projectmd | |
| DR-27 | Guard drift | journal rotation splits asymmetrically | `hooks/scripts/lib/workflow_state/journal.py:447-471` (alt: `ivy_lsp/mcp/tools/workflow_state.py:447-471`) | `split_at = len(entries) // 2` archives oldest half, keeps newest; for 201 entries archives 100, keeps 101 — intentional recency favoring | intentional | fsm-p2-journal, fsm-m3-workflow-state | |
| DR-28 | Transition drift | read-only auto-retry covers only 4 of 18 ivy_* tools | `hooks/scripts/mcp/retry.py:22-27` ↔ `ivy_lsp/mcp/tools/__init__.py:58-189` (18 tools) | `_ALLOWLIST = {"ivy_status", "ivy_diagnostics", "ivy_model_info", "ivy_coverage"}`; other read-only tools (`ivy_rfc`, `ivy_extract_requirements`, `ivy_manifest`, ...) surface failures immediately | intentional | fsm-m1-canonical | |
| DR-29 | Transition drift | deferred-schema reload assumes Claude Code native ToolSearch | `.claude/rules/mcp-tool-reliability.md:26` | "Call ToolSearch({query: 'select:<tool_name>'}) to re-load the schema" — protocol boundary intentional but not visually delineated in rule | intentional | fsm-m4-deferred-reload | |
| DR-30 | Vocabulary + state drift | role-pair workspace granularity uses placeholder metadata | `ivy_lsp/mcp/tools/workspace.py:114-120` | `# For now we store the role filter in active_tests as metadata`; `active_tests = [f"role:{r}" for r in role_list]`; future-work TODO acknowledged at line 116 | unimplemented-feature | fsm-m2-workspace | |
| DR-31 | Recovery drift | `knowledge_captured` event write path not found | `.claude/rules/journaling-contract.md:85` ↔ no visible code path | `knowledge_captured` event documented as "written by orchestrator after G6 SOUND verdict"; no ops-skill or hook writes this event in visible code (sub-issue of DR-08 G6 wiring) | unimplemented-feature | fsm-g6, fsm-w0 | Closed 2026-05-05 by `docs/superpowers/specs/2026-05-05-g0b-g6-design.md`; impl: plugin commit f850c41 (`lib/workflow_state/knowledge_capture.py` library + 14 unit tests); full plan in `docs/superpowers/plans/2026-05-05-g0b-g6-wiring.md`. |

## Counts

| category | count |
|---|---|
| Vocabulary + state drift | 9 |
| Transition drift | 8 |
| Guard drift | 8 |
| Recovery drift | 6 |
| **total** | **31** |

| severity_note | count |
|---|---|
| doc-gap | 18 |
| runtime-ambiguity | 5 |
| unimplemented-feature | 4 |
| intentional | 4 |
| **total** | **31** |

## Per-FSM cross-reference table

| FSM | drift IDs | citation |
|---|---|---|
| fsm-w0 (top-level workflow) | DR-01, DR-02, DR-05, DR-31 | `10-workflow-fsms.md#fsm-w0` |
| fsm-w1-scaffold | DR-03, DR-04 | `10-workflow-fsms.md#fsm-w1-scaffold` |
| fsm-w2-refine | DR-03, DR-04, DR-15 | `10-workflow-fsms.md#fsm-w2-refine` |
| fsm-w3-experiment | DR-13, DR-16 | `10-workflow-fsms.md#fsm-w3-experiment` |
| fsm-w4-review | DR-13, DR-18 | `10-workflow-fsms.md#fsm-w4-review` |
| fsm-w5-triage | DR-09, DR-16 | `10-workflow-fsms.md#fsm-w5-triage` |
| fsm-w6-meta | DR-18 | `10-workflow-fsms.md#fsm-w6-meta` |
| fsm-g0c-canonical | DR-06 | `20-gate-fsms.md#fsm-g0c-canonical` |
| fsm-g0 | DR-14 | `20-gate-fsms.md#fsm-g0` |
| fsm-g0b | DR-07, DR-14 | `20-gate-fsms.md#fsm-g0b` |
| fsm-g2 | DR-11, DR-16 | `20-gate-fsms.md#fsm-g2` |
| fsm-g3 | DR-11, DR-16 | `20-gate-fsms.md#fsm-g3` |
| fsm-g4 | DR-03, DR-10, DR-12, DR-15 | `20-gate-fsms.md#fsm-g4` |
| fsm-g5 | DR-13, DR-16 | `20-gate-fsms.md#fsm-g5` |
| fsm-g6 | DR-08, DR-31 | `20-gate-fsms.md#fsm-g6` |
| fsm-g7 | DR-09 | `20-gate-fsms.md#fsm-g7` |
| fsm-g8 | DR-09 | `20-gate-fsms.md#fsm-g8` |
| fsm-d1-dispatch | DR-17 | `30-dispatch-fsms.md#fsm-d1-dispatch` |
| fsm-d2 (per-specialist) | DR-18, DR-22 | `30-dispatch-fsms.md#fsm-d2` |
| fsm-d3-recovery | DR-19, DR-20, DR-21 | `30-dispatch-fsms.md#fsm-d3-recovery` |
| fsm-d4-return-shape | DR-22 | `30-dispatch-fsms.md#fsm-d4-return-shape` |
| fsm-h0-canonical | DR-23 | `40-hook-fsms.md#fsm-h0-canonical` |
| fsm-p1-active-workflow | DR-25 | `50-persistence-fsms.md#fsm-p1-active-workflow` |
| fsm-p2-journal | DR-23, DR-24, DR-27 | `50-persistence-fsms.md#fsm-p2-journal` |
| fsm-p3-projectmd | DR-26 | `50-persistence-fsms.md#fsm-p3-projectmd` |
| fsm-m1-canonical | DR-28 | `60-mcp-tool-fsms.md#fsm-m1-canonical` |
| fsm-m2-workspace | DR-30 | `60-mcp-tool-fsms.md#fsm-m2-workspace` |
| fsm-m3-workflow-state | DR-23, DR-27 | `60-mcp-tool-fsms.md#fsm-m3-workflow-state` |
| fsm-m4-deferred-reload | DR-29 | `60-mcp-tool-fsms.md#fsm-m4-deferred-reload` |

## Audit posture reminder

This register is audit-only. No fix proposals are listed. `severity_note` annotations are advisory ranking for future fix-proposal sessions, not commitments to act. The closed four-category set is the canonical taxonomy; if a future drift finding does not fit, the category set must be revised in this file (and cross-checked against `00-index.md`) before adding the entry.
