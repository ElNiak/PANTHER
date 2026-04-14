# Knowledge Capture Skill for panther-ivy-plugin

**Date**: 2026-04-14
**Status**: Draft
**Scope**: New internal skill + inline knowledge gates across all 5 workflow skills

## Problem

The panther-ivy-plugin's workflow skills generate valuable knowledge during sessions — bug patterns, Ivy modelisation patterns, architecture decisions, workflow refinements — but this knowledge lives only in the conversation context and is lost when the session ends. Users must manually extract and persist learnings to rules files or memory, which rarely happens. Over time, the same mistakes are repeated, the same patterns are rediscovered, and the same debugging sequences are re-derived from scratch.

## Goals

1. **Automatic knowledge detection**: Identify learnable moments during workflow execution without user prompting.
2. **Persistent session history**: Save full conversation transcripts and structured digests for cross-session analysis.
3. **Smart classification**: Route knowledge to the right persistence target (plugin rules, CLAUDE.md, user memory) based on recurrence and generality.
4. **User-confirmed writes**: Never persist knowledge without explicit user approval.
5. **Incremental improvement**: Plugin rules and documentation improve organically over time as sessions accumulate.

## Approach

Single orchestrator skill (`knowledge-capture`) with a classification reference file (`references/knowledge-taxonomy.md`). Memory gates embedded inline in each workflow SKILL.md trigger the skill at strategic points. A classification reviewer agent analyzes candidates against past sessions and existing rules before presenting to the user.

## Skill Structure

```
skills/knowledge-capture/
├── SKILL.md                              # Orchestrator (~150-200 lines)
└── references/
    └── knowledge-taxonomy.md             # Classification rules, targets, examples (~200-300 lines)
```

Additionally:
- `commands/nct-learn.md` — manual trigger command
- Inline knowledge gates in all 5 workflow SKILLs (5-10 lines each)
- Small addition to `hooks/scripts/render-summary.py` for end-of-session gate

## Session Storage

```
.panther-ivy/session-logs/
├── {timestamp}.json              # Full conversation transcript
├── {timestamp}.digest.yaml       # Lightweight index/summary
└── ...
```

### Full Transcript Format

The full transcript (`.json`) is assembled from the observability JSONL events already collected by `observe.py`. At each knowledge gate, the skill reads the current session's `events.jsonl` and writes a consolidated JSON file containing all tool calls, tool outputs, errors, and user prompts captured so far. This reuses existing infrastructure — no new data collection needed.

### Digest Format

```yaml
timestamp: "2026-04-14T14:30:00Z"
transcript: "2026-04-14T14-30-00Z.json"
workflow: verify
protocol: quic
phases_reached: [compile, execute, diagnose, fix]
files_modified:
  - protocol-testing/quic/quic_stack/quic_connection.ivy
  - protocol-testing/quic/quic_tests/server_tests/quic_server_test.ivy
errors:
  - type: verification_failure
    file: quic_connection.ivy
    error: "invariant conn_seen violated"
    resolution: "added after init block for conn_seen relation"
patterns_applied:
  - "after init for relation defaults"
verification_outcomes:
  - file: quic_server_test.ivy
    result: pass
    attempts: 2
knowledge_candidates:
  - category: ivy-pattern
    content: "Always add after init for relation defaults"
    status: approved  # or rejected, deferred
    target: .claude/rules/ivy-patterns.md
```

The classification reviewer agent scans digests for quick pattern matching, then drills into full JSON transcripts when it needs richer context for a specific candidate.

## Orchestrator Flow (SKILL.md)

### Step 1 — Scan Existing Knowledge

Read all target files that could already contain the learning:
- `.claude/rules/ivy-patterns.md`
- `.claude/rules/debugging.md`
- `.claude/rules/tool-reference.md`
- `.claude/rules/nct-methodology.md`
- `.claude/rules/insights.md`
- `CLAUDE.md` (plugin root)

### Step 2 — Reflect on Session

Review what happened since the last knowledge gate (or session start). Look for:
- Errors that were diagnosed and fixed (bug patterns)
- Ivy code written that revealed a non-obvious pattern (modelisation patterns)
- Design choices made during build/review workflows (architecture decisions)
- Multi-step sequences refined through trial and error (workflow refinements)
- Anything unexpected that doesn't fit the above (emergent insights)

If nothing learnable is found, the gate exits silently with no user interruption.

### Step 2b — Save Session Log

Write both:
1. Full conversation transcript to `.panther-ivy/session-logs/{timestamp}.json`
2. Structured digest to `.panther-ivy/session-logs/{timestamp}.digest.yaml`

This runs unconditionally at every gate, regardless of whether learnable knowledge was found.

### Step 3 — Classify Using Taxonomy

Load `references/knowledge-taxonomy.md` and match each candidate learning against the five categories. The taxonomy provides recognition heuristics and maps each category to its target file.

### Step 4 — Diff Against Existing

For each candidate, check whether the target file already contains equivalent knowledge:
- If existing rule covers the same ground: skip.
- If existing rule is incomplete or outdated: propose update rather than new entry.

### Step 4b — Spawn Classification Reviewer Agent

Dispatch a parallel agent that:

1. Reads the last 10-20 session digests to check recurrence. If the same pattern appeared in 3+ sessions, it's likely generic and belongs in plugin rules.
2. Reads all existing plugin rules and relevant `.ivy` model files to gauge generality — does it apply to one protocol or all?
3. Can drill into full conversation JSON transcripts for richer context when digest summaries are insufficient.
4. Returns a placement recommendation per candidate:
   - **plugin-rule** (generic, protocol-agnostic, recurring) + which rule file
   - **protocol-rule** (generic but scoped to one protocol)
   - **user-memory** (specific to current work, unlikely to recur)

Agent prompt template:

```
You are a Knowledge Classification Reviewer for the panther-ivy-plugin.

Review these candidate knowledge entries against:
1. Past session digests in .panther-ivy/session-logs/*.digest.yaml (check recurrence)
2. Full transcripts in .panther-ivy/session-logs/*.json (drill into when digests insufficient)
3. Existing plugin rules in .claude/rules/ (check for duplicates/updates)
4. Ivy model files in protocol-testing/ (check generality across protocols)

For each candidate, recommend placement:
- "plugin-rule" (generic, recurring, protocol-agnostic) + which rule file
- "protocol-rule" (generic but protocol-scoped) + which protocol
- "user-memory" (specific to current work context)

Include: recurrence count across sessions, similar existing rules found,
protocols where the pattern applies. Under 200 words per candidate.
```

### Step 5 — Draft and Confirm

Present each proposed addition/update via `AskUserQuestion`:

```
[Knowledge Gate] 2 learnings detected:

1. "Always add `after init` for relation defaults — omitting causes
    arbitrary initial values"
   -> Agent recommends: plugin-rule (.claude/rules/ivy-patterns.md)
   -> Reason: appeared in 4/10 recent sessions, applies to all protocols
   -> (a) Approve  (b) Edit  (c) Reject  (d) Change target  (e) Defer

2. "FRR BGP OPEN message includes 86 bytes of capabilities that
    bgp_deser_open doesn't handle"
   -> Agent recommends: user-memory (project-specific bug)
   -> Reason: first occurrence, BGP-specific, active debugging
   -> (a) Approve  (b) Edit  (c) Reject  (d) Change target  (e) Defer
```

Only approved entries get written. Deferred entries are noted in the digest and re-presented at the next gate.

## Knowledge Taxonomy (5 Categories)

### Category 1: Bug Patterns

- **Recognition**: An error was encountered, root-caused, and fixed during the session. The fix involved understanding something non-obvious about Ivy, MCP, Docker, or protocol behavior.
- **Target (generic)**: `.claude/rules/debugging.md` — append to "Common failures" or add new subsection
- **Target (specific)**: User memory
- **Entry format**: One-liner problem statement, root cause, fix.
- **Example**: `- Z3 import error on ARM: stale libz3.so from apt conflicts with pip z3-solver. Fix: rm /usr/lib/libz3* before pip install.`

### Category 2: Ivy Modelisation Patterns

- **Recognition**: A non-obvious Ivy language construct was used, an anti-pattern was discovered, or a pattern was refined through verification feedback. Detectable when `.ivy` files were edited and `ivy_verify` or `ivy_diagnostics` was called.
- **Target**: `.claude/rules/ivy-patterns.md` — add to existing pattern sections or create new subsection
- **Entry format**: Pattern name, code snippet, when to use. Follows existing format in `ivy-patterns.md`.

### Category 3: Architecture Decisions

- **Recognition**: A structural choice was made during the build workflow about layer organization, module composition, include graph structure, or shim design. Detectable when build-state.yaml was updated or when MPE agents were consulted.
- **Target (generic)**: Plugin `CLAUDE.md` or `.claude/rules/nct-methodology.md`
- **Target (protocol-specific)**: Protocol-level documentation or new rule file
- **Entry format**: Decision statement with rationale.
- **Example**: `Shim isolates must re-export all actions from the entity layer — direct include from test specs breaks the assume-guarantee boundary.`

### Category 4: Workflow Refinements

- **Recognition**: A multi-step sequence was attempted, failed, then refined into a better sequence. Or a tool ordering was discovered to be important. Detectable when the same tool was called multiple times with different parameters, or when workflow phases were revisited.
- **Target**: `.claude/rules/tool-reference.md` or `.claude/rules/debugging.md`
- **Entry format**: Sequence description with ordering rationale.
- **Example**: `Always run ivy_diagnostics(mode="structural") before ivy_verify — catches syntax errors in milliseconds vs seconds of wasted verification time.`

### Category 5: Emergent Insights

- **Recognition**: Anything that doesn't fit categories 1-4 but represents knowledge worth preserving. Unexpected tool behaviors, cross-cutting observations, correlations between unrelated components, performance characteristics discovered empirically, or "I wish I'd known this at the start" moments.
- **Detection heuristic**: The classification reviewer agent flags a candidate as "emergent" when it doesn't match primary category recognition patterns but still scores as recurring (2+ sessions) or high-impact (would have saved significant debugging time).
- **Target**: `.claude/rules/insights.md` (new file)
- **Entry format**: Free-form observation with context tag.
- **Example**: `- [cross-cutting] ivy_coverage reports 0% on files that use include chains deeper than 4 levels — the include graph resolver silently truncates. Workaround: flatten includes or use test_file scoping.`
- **Graduation rule**: When the classification reviewer agent sees 3+ entries in `insights.md` clustering around the same theme, it recommends promoting them into a proper category and moving them to the appropriate rule file.

### Negative Examples (do NOT capture)

- Ephemeral debugging steps that only apply to the current file state
- Patterns already documented in existing rules (detected by diff step)
- One-off workarounds for infrastructure state that was subsequently fixed
- Task-specific progress notes (these belong in user memory project entries, not plugin rules)

## Knowledge Gate Placement

Gate trigger rule: A Knowledge Gate (KG) fires at moments where Claude has just completed a meaningful unit of work that could contain learnings. KGs look backward at what was learned.

### Per-Workflow Placement (8 gates)

| Workflow | Location | Trigger Signal |
|----------|----------|----------------|
| **verify** | After Phase 4 (execution results) | Verification passed or failed — either outcome may reveal patterns |
| **verify** | After Phase 7 (fix applied + re-verified) | A bug was diagnosed and fixed — prime candidate for bug/pattern capture |
| **build** | After Phase 3 (every 3 layers written) | Ivy patterns discovered while writing layers |
| **build** | After Phase 5 (quality gate) | Architecture decisions solidified after quality review |
| **review** | After Phase 2 (agent findings returned) | Cross-model patterns identified by model-reviewer and traceability-agent |
| **review** | After Phase 3 (findings resolved) | Workflow refinements from the resolution process |
| **triage** | After Phase 3 (fix applied) | Debugging patterns from infrastructure troubleshooting |
| **navigate** | After Phase 1 (context scan, warm resume) | Check if last session's digest had deferred candidates to re-present |

### Stop Hook Gate

`hooks/scripts/render-summary.py` gets a small addition: inject a prompt telling Claude to run one final knowledge gate before ending, ensuring nothing is lost even if the session ends mid-workflow.

### Inline Gate Template (added to each SKILL.md)

Each gate is 5-10 lines in the workflow SKILL.md:

```markdown
### Knowledge Gate: [location description]

**KNOWLEDGE GATE (KG)**: Pause and invoke the `knowledge-capture` skill.
- Reflect on what was learned in the preceding phase(s)
- Save session log (full transcript + digest)
- If candidates found, classify and present for user confirmation
- If deferred candidates exist from prior gates, re-present them
- Resume workflow after gate completes
```

## Implementation Files

| File | Action | Description |
|------|--------|-------------|
| `skills/knowledge-capture/SKILL.md` | Create | Orchestrator skill (~150-200 lines) |
| `skills/knowledge-capture/references/knowledge-taxonomy.md` | Create | 5-category taxonomy with heuristics, targets, formats (~200-300 lines) |
| `.claude/rules/insights.md` | Create | Empty file for emergent insights category |
| `commands/nct-learn.md` | Create | Manual trigger command for knowledge capture |
| `skills/verify/SKILL.md` | Edit | Add 2 knowledge gates (after Phase 4, after Phase 7) |
| `skills/build/SKILL.md` | Edit | Add 2 knowledge gates (after Phase 3, after Phase 5) |
| `skills/review/SKILL.md` | Edit | Add 2 knowledge gates (after Phase 2, after Phase 3) |
| `skills/triage/SKILL.md` | Edit | Add 1 knowledge gate (after Phase 3) |
| `skills/navigate/SKILL.md` | Edit | Add 1 knowledge gate (after Phase 1) |
| `hooks/scripts/render-summary.py` | Edit | Add final knowledge gate prompt injection |

## Interaction with Reflection Gates Spec

This spec is complementary to the reflection/interaction/MPE spec (`2026-04-14-reflection-interaction-multi-agent-design.md`). The two systems operate at different moments:

- **Reflection Gates (RG)**: Look forward — "should we change direction?"
- **Knowledge Gates (KG)**: Look backward — "what did we learn?"

When both fire at the same workflow point, KG runs after RG. The reflection gate may change the workflow direction, and the knowledge gate captures what was learned before the direction change.

## Constraints

- Skills must stay under 500 lines (per skill-conventions rule). Heavy taxonomy goes in `references/`.
- Each SKILL.md gate addition is 5-10 lines referencing the shared skill.
- The classification reviewer agent uses an ad-hoc prompt — no new agent definition in `agents/`.
- Knowledge gates must not block sub-workflow calls (when `invocation_depth > 0`, skip KG to avoid interrupting parent workflow flow).
- Session logs stored in `.panther-ivy/session-logs/` — this directory should be gitignored.
- User confirmation is mandatory — no silent writes to rule files.

## Non-Goals

- No new hooks beyond the `render-summary.py` addition (using inline skill instructions)
- No changes to `routing-rules.json` or `hooks.json`
- No changes to the style system
- No automated rule file cleanup/pruning (manual for now)
- No cross-project knowledge sharing (scoped to this plugin instance)
