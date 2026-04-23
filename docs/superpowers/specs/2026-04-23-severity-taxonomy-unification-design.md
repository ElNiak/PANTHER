# Design — panther-ivy-plugin Severity-Taxonomy Unification

Status: proposed
Author: workflow-audit follow-up (cluster-6 grilling session)
Date: 2026-04-23
Scope: close audit cluster 6 (severity-taxonomy drift across workflows, agents, gate outputs, and tool outcomes).

## Context

The workflow audit on 2026-04-23 identified four parallel severity systems in use across the plugin:

1. `PASS` / `FAIL` / `WARN` — tool-outcome vocabulary (triage, /nct-health, verify compile).
2. `SOUND` / `UNSOUND` / `ABSTAIN` — gate-verdict vocabulary (G0-G5 adversarial gates).
3. `ERROR` / `WARNING` / `INFO` — finding-severity vocabulary (model-reviewer agent interactive mode, `.claude/rules/ivy-formatting.md:4` canonical error format).
4. `Critical` / `Important` / `Suggestion` — another finding-severity vocabulary (review SKILL.md Phase 3, build SKILL.md Phase 5).

The audit classified this as Major because systems 3 and 4 label the same concept (severity of a file:line-attached finding) with different words. Users reading review's output and then the raw agent output see drift. A separate Major finding lives inside `agents/model-reviewer.md:186` where `UNSURE` is used in place of the canonical `ABSTAIN` for gate-critic-mode output.

## Decisions

1. **Retire `Critical` / `Important` / `Suggestion`** from review SKILL.md Phase 3 and build SKILL.md Phase 5. Replace with `ERROR` / `WARNING` / `INFO`.
2. **Fix `agents/model-reviewer.md:186`**: gate-critic-mode output enum changes `UNSURE` to `ABSTAIN`, matching `reflection-patterns/references/gates.md` canonical verdict schema.
3. **Retain `PASS` / `FAIL` / `WARN`** as tool-outcome vocabulary. Different concept; no conflict.
4. **Retain `SOUND` / `UNSOUND` / `ABSTAIN`** as gate-verdict vocabulary. Different concept; no conflict.
5. **Document the three orthogonal systems** in a new "Severity Systems" section of `.claude/rules/ivy-formatting.md`, adjacent to the existing canonical `ERROR: {file}:{line} -- {message}` format rule.

## Architecture

The three systems remain orthogonal. Concrete text to append to `.claude/rules/ivy-formatting.md` (placed after the existing Self-Review section):

```
## Severity Systems

Three orthogonal severity systems exist in the plugin. Use the system that
matches the concept being labeled.

1. **Tool-outcome**: PASS / FAIL / WARN.
   Use for the result of a mechanical tool run (ivy_verify returning
   success/failure, a health-check step, a compile result). PASS/FAIL are
   binary outcomes; WARN signals a tool succeeded but produced advisory
   output. Used by: triage Phase 1-3, /nct-health runbook, verify Phase 3
   compile result, /nct-check output.

2. **Gate verdict**: SOUND / UNSOUND(#NN, reason, file:line) / ABSTAIN.
   Use for the calibrated verdict of an adversarial quality gate (G0-G5).
   ABSTAIN is a first-class output signalling insufficient evidence, not a
   synonym for WARN or UNSURE. Used by: reflection-patterns gates;
   gate_verdict journal entries; model-reviewer gate-critic mode.

3. **Finding severity**: ERROR / WARNING / INFO.
   Use for the severity of a code-level or workflow-level finding that has
   a file:line locator. Format per the existing canonical rule above
   (`ERROR: {file}:{line} -- {message}`). Used by: model-reviewer
   interactive mode, build Phase 5 findings, review Phase 3 findings,
   spec-analyst diagnostic reports.

These systems do not map onto each other. A FAIL tool-outcome may correspond
to multiple ERROR findings; an UNSOUND gate verdict may cite one or more
ERROR-severity patterns; and an ABSTAIN is not a WARN.
```

## File change inventory (5 files)

| File | Change |
|---|---|
| `.claude/rules/ivy-formatting.md` | Append new "Severity Systems" section per the text above. No existing rules modified. |
| `skills/review/SKILL.md` | Line 205-208 Phase 3 Step 1 ("Present findings"): replace three-tier labels `Critical:` / `Important:` / `Suggestion:` with `ERROR:` / `WARNING:` / `INFO:`, preserving definition text. Update Step Tracking references (if any) that mention severity wording. Update line 213 gate-checkpoint text ("These critical issues were found") → "These ERRORs were found". |
| `skills/build/SKILL.md` | Line 237 Phase 5 Step 2 "Classify by severity: critical, important, suggestion" → "Classify by severity: ERROR, WARNING, INFO". Line 240 gate-checkpoint text ("These critical issues were found") → "These ERRORs were found". |
| `agents/model-reviewer.md` | Line 186: change `UNSURE` to `ABSTAIN` in the gate-critic-mode output enum. No other changes to the file. |
| `agents/spec-analyst.md`, `agents/traceability-agent.md`, `commands/*.md`, `hooks/**/*`, remaining skills | No changes. spec-analyst uses PASS/FAIL (tool-outcome, appropriate). traceability-agent uses RFC 2119 MUST/SHOULD/MAY (RFC priority — separate axis). |

## Migration plan

Trivial: single commit covering 5 files. No tests to update — severity labels appear only in prose content, not as schema fields code reads or matches against.

Commit structure (one commit):

```
docs(plugin): unify severity taxonomy; retire Critical/Important/Suggestion

- .claude/rules/ivy-formatting.md: add Severity Systems section
- skills/review/SKILL.md: Phase 3 findings use ERROR/WARNING/INFO
- skills/build/SKILL.md: Phase 5 classification uses ERROR/WARNING/INFO
- agents/model-reviewer.md: gate-critic-mode verdict UNSURE -> ABSTAIN

Closes audit cluster 6 (severity-taxonomy drift).
```

## Risks

1. **Perceived severity shift**: `Critical` carries more urgency than `ERROR` for some readers. Mitigation: none for correctness; this is a vocabulary choice. The new Severity Systems section explains that `ERROR` is the top-severity finding label.
2. **External references**: any unreviewed spec in `docs/superpowers/specs/` that uses `Critical/Important/Suggestion` in prose will drift. Mitigation: not in scope; later specs use the new convention. Grep the docs folder post-merge to spot-check.
3. **This session's audit report**: the audit I produced earlier today uses `Critical/Major/Minor/Nit` — a *different* four-tier system used for audit-finding ranking, not workflow-finding ranking. That taxonomy is audit-report-specific and remains valid. The spec explicitly leaves that system in place.

## Out of scope

- Merging the tool-outcome `PASS/FAIL/WARN` vocabulary into finding severity (rejected during grilling — they label different concepts).
- Merging the gate-verdict `SOUND/UNSOUND/ABSTAIN` vocabulary into finding severity (rejected for the same reason; also, gate verdicts carry pattern IDs and file:line which findings don't always have).
- Audit-report-specific severities (`Critical/Major/Minor/Nit`) used in the 2026-04-23 workflow audit report. That taxonomy belongs to the audit, not the runtime plugin.

## Verification

- Grep the plugin for `Critical:` and `Important:` as severity labels post-merge: only expected remaining matches are audit-report-specific or historical spec files.
- Run the plugin's existing test suite (if any covers workflow skills' output formatting) — should be unaffected since the change is prose-only.
- Spot-check: invoke `review` workflow in a fresh session against a known protocol; Phase 3 output should now use `ERROR:` / `WARNING:` / `INFO:` labels instead of `Critical:` / `Important:` / `Suggestion:`.
