# Knowledge Capture Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an internal `knowledge-capture` skill for the panther-ivy-plugin that automatically detects, classifies, and persists learnings from Ivy workflow sessions into plugin rules files.

**Architecture:** Single orchestrator skill (`SKILL.md`) with a taxonomy reference file. Knowledge gates embedded inline in each of the 5 workflow SKILLs invoke the skill at strategic phase boundaries. A classification reviewer agent analyzes candidates against past session digests and existing rules before presenting to the user for confirmation.

**Tech Stack:** Claude Code skills (markdown), YAML (digests), JSON (session logs), existing observability JSONL infrastructure.

**Spec:** `docs/superpowers/specs/2026-04-14-knowledge-capture-skill-design.md`

**Plugin root:** `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/`
(All paths below are relative to this root unless prefixed with a different base.)

---

### Task 1: Create the knowledge taxonomy reference file

**Files:**
- Create: `skills/knowledge-capture/references/knowledge-taxonomy.md`

- [ ] **Step 1: Create the taxonomy file**

```markdown
# Knowledge Taxonomy

Reference for the `knowledge-capture` skill. Defines 5 knowledge categories with recognition heuristics, persistence targets, entry formats, and negative examples.

## Category 1: Bug Patterns

**Recognition heuristics:**
- An error was encountered, root-caused, and fixed during the session
- The fix involved understanding something non-obvious about Ivy, MCP, Docker, or protocol behavior
- Detectable when: `ivy_verify` or `ivy_compile` failed, then succeeded after changes; or MCP/LSP errors were diagnosed and resolved

**Persistence targets:**
- Generic (protocol-agnostic, recurring): `.claude/rules/debugging.md` — append under "Common failures" or create a new subsection
- Specific (one-off, project-scoped): User memory (`~/.claude/projects/.../memory/`)

**Entry format:** One-liner: problem statement, root cause, fix.

**Example:**
```
- Z3 import error on ARM: stale libz3.so from apt conflicts with pip z3-solver. Fix: rm /usr/lib/libz3* before pip install.
```

---

## Category 2: Ivy Modelisation Patterns

**Recognition heuristics:**
- A non-obvious Ivy language construct was used or discovered
- An anti-pattern was found and corrected through verification feedback
- Detectable when: `.ivy` files were edited AND `ivy_verify` or `ivy_diagnostics` was called afterward

**Persistence target:** `.claude/rules/ivy-patterns.md` — add to existing sections or create new subsection.

**Entry format:** Pattern name, code snippet, when to use. Follow the existing format in `ivy-patterns.md` (code blocks with inline comments).

**Example:**
```ivy
# Always initialize relations in `after init` — omitting causes arbitrary values
relation conn_seen(C:cid)
after init { conn_seen(C) := false; }
```

---

## Category 3: Architecture Decisions

**Recognition heuristics:**
- A structural choice was made about layer organization, module composition, include graph structure, or shim design
- Detectable when: `build-state.yaml` was updated, MPE agents were consulted, or layer structure was discussed during the build workflow

**Persistence targets:**
- Generic (applies to all protocols): Plugin `CLAUDE.md` or `.claude/rules/nct-methodology.md`
- Protocol-specific: Protocol-level documentation or a new protocol-scoped rule file

**Entry format:** Decision statement with rationale.

**Example:**
```
Shim isolates must re-export all actions from the entity layer — direct include from test specs breaks the assume-guarantee boundary.
```

---

## Category 4: Workflow Refinements

**Recognition heuristics:**
- A multi-step sequence was attempted, failed, then refined into a better sequence
- A tool ordering was discovered to be important
- Detectable when: the same tool was called multiple times with different parameters, or workflow phases were revisited

**Persistence targets:** `.claude/rules/tool-reference.md` or `.claude/rules/debugging.md` (depending on whether it's tool-specific or triage-specific).

**Entry format:** Sequence description with ordering rationale.

**Example:**
```
Always run ivy_diagnostics(mode="structural") before ivy_verify — catches syntax errors in milliseconds vs seconds of wasted verification time.
```

---

## Category 5: Emergent Insights

**Recognition heuristics:**
- Does not fit categories 1-4 but represents knowledge worth preserving
- Unexpected tool behaviors, cross-cutting observations, correlations between unrelated components, performance characteristics discovered empirically
- "I wish I'd known this at the start of the session" moments
- The classification reviewer agent flags a candidate as "emergent" when it doesn't match primary recognition patterns but scores as recurring (2+ sessions) or high-impact

**Persistence target:** `.claude/rules/insights.md`

**Entry format:** Free-form observation with context tag.

**Example:**
```
- [cross-cutting] ivy_coverage reports 0% on files that use include chains deeper than 4 levels — the include graph resolver silently truncates. Workaround: flatten includes or use test_file scoping.
```

**Graduation rule:** When 3+ entries in `insights.md` cluster around the same theme, recommend promoting them to a proper category and moving them to the appropriate rule file.

---

## Negative Examples (do NOT capture)

- Ephemeral debugging steps that only apply to the current file state
- Patterns already documented in existing rules (detected by the diff step)
- One-off workarounds for infrastructure state that was subsequently fixed
- Task-specific progress notes (these belong in user memory project entries, not plugin rules)

---

## Classification Reviewer Agent Prompt

```
You are a Knowledge Classification Reviewer for the panther-ivy-plugin.

Review these candidate knowledge entries against:
1. Past session digests in .panther-ivy/session-logs/*.digest.yaml (check recurrence)
2. Full event logs in .panther-ivy/session-logs/*.json (drill into when digests insufficient)
3. Existing plugin rules in .claude/rules/ (check for duplicates/updates)
4. Ivy model files in protocol-testing/ (check generality across protocols)

For each candidate, recommend placement:
- "plugin-rule" (generic, recurring, protocol-agnostic) + which rule file
- "protocol-rule" (generic but protocol-scoped) + which protocol
- "user-memory" (specific to current work context)

Include: recurrence count across sessions, similar existing rules found,
protocols where the pattern applies. Under 200 words per candidate.
```

---

## Digest Schema

```yaml
timestamp: "ISO-8601 UTC"
event_log: "{timestamp}.json"
workflow: verify|build|review|triage|navigate
protocol: quic|bgp|coap|minip|apt|apt_quic
phases_reached: [list of phase names reached]
files_modified: [list of .ivy file paths]
errors:
  - type: verification_failure|compile_error|mcp_error|lsp_error
    file: relative path
    error: error message summary
    resolution: what fixed it (if resolved)
patterns_applied: [list of pattern descriptions]
verification_outcomes:
  - file: relative path
    result: pass|fail
    attempts: N
knowledge_candidates:
  - category: bug-pattern|ivy-pattern|architecture|workflow|emergent
    content: the learning text
    status: approved|rejected|deferred
    target: target file path
```
```

- [ ] **Step 2: Verify the file was created with correct structure**

Run: `wc -l skills/knowledge-capture/references/knowledge-taxonomy.md`
Expected: ~180-220 lines

- [ ] **Step 3: Commit**

```bash
git add skills/knowledge-capture/references/knowledge-taxonomy.md
git commit -m "feat(knowledge-capture): add knowledge taxonomy reference file

Defines 5 categories (bug patterns, ivy patterns, architecture decisions,
workflow refinements, emergent insights) with recognition heuristics,
persistence targets, entry formats, and the classification reviewer
agent prompt template."
```

---

### Task 2: Create the knowledge-capture SKILL.md orchestrator

**Files:**
- Create: `skills/knowledge-capture/SKILL.md`

- [ ] **Step 1: Create the SKILL.md file**

```markdown
---
name: knowledge-capture
description: "Session knowledge extraction and persistence to plugin rules. Use when a knowledge gate fires at workflow phase boundaries or when manually triggered via /nct-learn."
user-invocable: false
context: fork
allowed-tools:
  - Read
  - Grep
  - Glob
  - Write
  - Edit
  - Agent
  - AskUserQuestion
  - Bash(ls *)
---

# Knowledge Capture

Internal skill invoked by knowledge gates in workflow SKILLs. Extracts learnings from the current session, classifies them, and persists approved entries to plugin rules files or user memory.

## Pre-Check

If `invocation_depth > 0` in the active-workflow state, **skip this gate entirely** and return to the calling workflow. Knowledge gates must not interrupt sub-workflow calls.

## Step 1 — Scan Existing Knowledge

Read all target files to understand what is already documented:

- `.claude/rules/ivy-patterns.md`
- `.claude/rules/debugging.md`
- `.claude/rules/tool-reference.md`
- `.claude/rules/nct-methodology.md`
- `.claude/rules/insights.md`
- `CLAUDE.md` (plugin root)

Note key topics and patterns already covered. This prevents duplicate entries.

## Step 2 — Reflect on Session

Review what happened since the last knowledge gate (or session start). Look for:

1. **Bug patterns**: Errors diagnosed and fixed — what was non-obvious about the root cause?
2. **Ivy patterns**: `.ivy` code written that revealed a non-obvious construct or anti-pattern
3. **Architecture decisions**: Design choices made during build/review — layer organization, module composition, include structure
4. **Workflow refinements**: Multi-step sequences that were refined through trial and error, tool orderings discovered to matter
5. **Emergent insights**: Anything surprising that doesn't fit above — unexpected behaviors, cross-cutting observations

**If nothing learnable is found, exit silently.** Do not interrupt the user.

## Step 2b — Save Session Log

This runs unconditionally at every gate.

1. Read the current session's observability events from the JSONL log (resolve path via `IVY_OBSERVABILITY_DIR`, `IVY_WORKSPACE_ROOT/.observability/`, or `/tmp/ivy-observability/`).
2. Consolidate events into `.panther-ivy/session-logs/{timestamp}.json`.
3. Write a structured digest to `.panther-ivy/session-logs/{timestamp}.digest.yaml` using the schema from `references/knowledge-taxonomy.md`.

The digest captures: workflow type, protocol, phases reached, files modified, errors and resolutions, patterns applied, verification outcomes, and knowledge candidates from this gate.

## Step 3 — Classify Using Taxonomy

Load `references/knowledge-taxonomy.md`. For each candidate learning from Step 2, match against the 5 category recognition heuristics. Assign a primary category and a target file.

## Step 4 — Diff Against Existing

For each candidate, check the target file (read in Step 1):

- **Already documented**: Skip — the rule already covers this.
- **Partially documented**: Propose an update to the existing entry rather than a new one.
- **New knowledge**: Propose a new entry.

## Step 4b — Spawn Classification Reviewer Agent

Dispatch a parallel agent using the prompt template from `references/knowledge-taxonomy.md` (section "Classification Reviewer Agent Prompt"). Pass:

- The candidate list with proposed categories and targets
- The path to session digests: `.panther-ivy/session-logs/`
- The path to plugin rules: `.claude/rules/`

The agent returns a placement recommendation per candidate:
- `plugin-rule` + target file (generic, recurring, protocol-agnostic)
- `protocol-rule` + protocol (generic but protocol-scoped)
- `user-memory` (specific to current work)

Incorporate the agent's recommendations into the presentation.

## Step 5 — Draft and Confirm

Present each candidate via `AskUserQuestion`:

```
[Knowledge Gate] N learning(s) detected:

1. "{learning text}"
   -> Category: {category}
   -> Agent recommends: {placement} ({target file})
   -> Reason: {agent's reasoning summary}
   -> (a) Approve  (b) Edit  (c) Reject  (d) Change target  (e) Defer
```

For each user response:

- **(a) Approve**: Write the entry to the target file using `Edit` (append to the appropriate section). Update the digest's `knowledge_candidates` entry with `status: approved`.
- **(b) Edit**: Ask the user for the revised text via `AskUserQuestion`, then write.
- **(c) Reject**: Update the digest with `status: rejected`. Do not write.
- **(d) Change target**: Ask the user which file, then write there.
- **(e) Defer**: Update the digest with `status: deferred`. Re-present at the next knowledge gate.

## Deferred Candidate Handling

At the start of each gate (before Step 2), check the most recent digest for `status: deferred` candidates. If found, re-present them in Step 5 alongside any new candidates.

## Graduation Check (Emergent Insights)

After writing to `.claude/rules/insights.md`, check whether 3+ entries cluster around the same theme. If so, recommend promoting them: present the cluster to the user and suggest moving to the appropriate primary-category rule file.
```

- [ ] **Step 2: Verify the file is under 500 lines**

Run: `wc -l skills/knowledge-capture/SKILL.md`
Expected: ~150-180 lines (well under 500)

- [ ] **Step 3: Commit**

```bash
git add skills/knowledge-capture/SKILL.md
git commit -m "feat(knowledge-capture): add orchestrator skill

5-step flow: scan existing rules, reflect on session, classify via
taxonomy, diff against existing knowledge, confirm with user.
Includes session log persistence, classification reviewer agent
dispatch, and deferred candidate re-presentation."
```

---

### Task 3: Create the insights.md rule file and nct-learn command

**Files:**
- Create: `.claude/rules/insights.md`
- Create: `commands/nct-learn.md`

- [ ] **Step 1: Create the empty insights rule file**

```markdown
---
paths: ["**/*.ivy"]
---

## Emergent Insights

Uncategorized learnings that may graduate to a primary category when 3+ entries cluster around the same theme.
```

- [ ] **Step 2: Create the nct-learn command**

```markdown
---
name: nct-learn
description: "Manually trigger knowledge capture to extract and persist session learnings to plugin rules"
arguments: []
---

> **Manual trigger** for the knowledge-capture skill. Use this when you want to capture learnings outside of the automatic knowledge gates embedded in workflow skills.

Invoke the `knowledge-capture` skill:

```
Skill(skill="panther-ivy-plugin:knowledge-capture")
```

This runs the full 5-step knowledge capture flow: scan existing rules, reflect on the current session, classify learnings, spawn the classification reviewer agent, and present candidates for user confirmation.
```

- [ ] **Step 3: Commit**

```bash
git add .claude/rules/insights.md commands/nct-learn.md
git commit -m "feat(knowledge-capture): add insights rule file and nct-learn command

Empty insights.md for emergent insight storage with graduation rule.
nct-learn command provides manual trigger for knowledge capture outside
automatic workflow gates."
```

---

### Task 4: Update skills README to include knowledge-capture

**Files:**
- Modify: `skills/README.md`

- [ ] **Step 1: Add knowledge-capture to the Knowledge Skills table**

In `skills/README.md`, add a row to the "Knowledge Skills" table after the last entry. Change the count from 7 to 8.

OLD (line 19):
```markdown
## Knowledge Skills (7)
```

NEW:
```markdown
## Knowledge Skills (8)
```

OLD (after line 31, last row of the table):
```markdown
| [methodology-reference](methodology-reference/) | Comprehensive reference for NCT, NACT, NSCT methodologies |
```

NEW:
```markdown
| [methodology-reference](methodology-reference/) | Comprehensive reference for NCT, NACT, NSCT methodologies |
| [knowledge-capture](knowledge-capture/) | Session knowledge extraction and persistence to plugin rules at workflow phase boundaries |
```

- [ ] **Step 2: Commit**

```bash
git add skills/README.md
git commit -m "docs: add knowledge-capture to skills README"
```

---

### Task 5: Add knowledge gates to verify workflow

**Files:**
- Modify: `skills/verify/SKILL.md`

- [ ] **Step 1: Add knowledge gate after Phase 4 (Execute)**

In `skills/verify/SKILL.md`, after the Reflection Gate section at the end of Phase 4 (after line ~143, before `### On FAIL`), insert:

```markdown

### Knowledge Gate: Post-Execution

**KNOWLEDGE GATE (KG)**: Pause and invoke: `Skill(skill="panther-ivy-plugin:knowledge-capture")`
- Reflect on verification outcome — what patterns led to pass or fail?
- Save session log (observability events + digest)
- If candidates found, classify and present for user confirmation
- Resume workflow after gate completes
```

- [ ] **Step 2: Add knowledge gate at the end of Phase 7 (Fix)**

In `skills/verify/SKILL.md`, after the "On user stopping" section at the end of Phase 7 (after line ~281, before `## On Completion`), insert:

```markdown

### Knowledge Gate: Post-Fix

**KNOWLEDGE GATE (KG)**: Pause and invoke: `Skill(skill="panther-ivy-plugin:knowledge-capture")`
- Reflect on the bug that was diagnosed and fixed — what was non-obvious?
- Capture the error-to-fix pattern for future sessions
- Save session log (observability events + digest)
- If candidates found, classify and present for user confirmation
- Resume workflow after gate completes
```

- [ ] **Step 3: Update the Integration section**

In `skills/verify/SKILL.md`, in the Integration section (line ~296), add `knowledge-capture` to the knowledge skills loaded list:

OLD:
```markdown
- **Knowledge skills loaded:** `counterexample-guide` (Phase 6), `ivy-writing-guide` (Phase 2 option 3, Phase 7), `specification-patterns` (Phase 2 option 3)
```

NEW:
```markdown
- **Knowledge skills loaded:** `counterexample-guide` (Phase 6), `ivy-writing-guide` (Phase 2 option 3, Phase 7), `specification-patterns` (Phase 2 option 3), `knowledge-capture` (Phase 4 post-execution, Phase 7 post-fix)
```

- [ ] **Step 4: Verify the file is still under 500 lines**

Run: `wc -l skills/verify/SKILL.md`
Expected: under 500 lines

- [ ] **Step 5: Commit**

```bash
git add skills/verify/SKILL.md
git commit -m "feat(knowledge-capture): add 2 knowledge gates to verify workflow

Gates fire after Phase 4 (execution results) and at end of Phase 7
(fix applied). Both invoke knowledge-capture skill for session
learning extraction."
```

---

### Task 6: Add knowledge gates to build workflow

**Files:**
- Modify: `skills/build/SKILL.md`

- [ ] **Step 1: Add knowledge gate after Phase 3 (Write)**

In `skills/build/SKILL.md`, after the "Update state" step at the end of Phase 3 (after line ~132, before `## Phase 4 — Verify`), insert:

```markdown

### Knowledge Gate: Post-Write (every 3 layers)

**KNOWLEDGE GATE (KG)**: Pause and invoke: `Skill(skill="panther-ivy-plugin:knowledge-capture")`
- Reflect on Ivy patterns discovered while writing layers
- Capture any non-obvious constructs, anti-patterns, or verification feedback
- Save session log (observability events + digest)
- If candidates found, classify and present for user confirmation
- Resume workflow after gate completes
```

- [ ] **Step 2: Add knowledge gate after Phase 5 (Quality Gate)**

In `skills/build/SKILL.md`, after the "Update state" step at the end of Phase 5 (after line ~193, before `## Phase 6 — Wrap-up`), insert:

```markdown

### Knowledge Gate: Post-Quality-Gate

**KNOWLEDGE GATE (KG)**: Pause and invoke: `Skill(skill="panther-ivy-plugin:knowledge-capture")`
- Reflect on architecture decisions solidified during quality review
- Capture model-reviewer and traceability-agent findings worth remembering
- Save session log (observability events + digest)
- If candidates found, classify and present for user confirmation
- Resume workflow after gate completes
```

- [ ] **Step 3: Update the Integration section**

In `skills/build/SKILL.md`, find the Integration section and add `knowledge-capture` to the knowledge skills loaded list. If no Integration section exists, add one at the end before the closing `---`:

```markdown
- **Knowledge skills loaded:** ..., `knowledge-capture` (Phase 3 post-write, Phase 5 post-quality-gate)
```

- [ ] **Step 4: Verify the file is still under 500 lines**

Run: `wc -l skills/build/SKILL.md`
Expected: under 500 lines

- [ ] **Step 5: Commit**

```bash
git add skills/build/SKILL.md
git commit -m "feat(knowledge-capture): add 2 knowledge gates to build workflow

Gates fire after Phase 3 (layers written) and after Phase 5 (quality
gate). Both invoke knowledge-capture skill for session learning
extraction."
```

---

### Task 7: Add knowledge gates to review workflow

**Files:**
- Modify: `skills/review/SKILL.md`

- [ ] **Step 1: Add knowledge gate at end of Phase 2 (Execute)**

In `skills/review/SKILL.md`, after the "Update state" step at the end of Phase 2 (after line ~105, before `## Phase 3 — Findings`), insert:

```markdown

### Knowledge Gate: Post-Agent-Execution

**KNOWLEDGE GATE (KG)**: Pause and invoke: `Skill(skill="panther-ivy-plugin:knowledge-capture")`
- Reflect on cross-model patterns identified by model-reviewer and traceability-agent
- Capture any recurring quality findings worth remembering
- Save session log (observability events + digest)
- If candidates found, classify and present for user confirmation
- Resume workflow after gate completes
```

- [ ] **Step 2: Add knowledge gate at end of Phase 3 (Findings)**

In `skills/review/SKILL.md`, after the user response handling at the end of Phase 3 (before `## On Completion`), insert:

```markdown

### Knowledge Gate: Post-Findings-Resolution

**KNOWLEDGE GATE (KG)**: Pause and invoke: `Skill(skill="panther-ivy-plugin:knowledge-capture")`
- Reflect on workflow refinements from the resolution process
- Capture fix strategies that worked or didn't work
- Save session log (observability events + digest)
- If candidates found, classify and present for user confirmation
- Resume workflow after gate completes
```

- [ ] **Step 3: Update the Integration section**

In `skills/review/SKILL.md`, update the Integration section (line ~166):

OLD:
```markdown
- **Knowledge skills loaded:** `claim-discussion` (Phase 3 for contested findings)
```

NEW:
```markdown
- **Knowledge skills loaded:** `claim-discussion` (Phase 3 for contested findings), `knowledge-capture` (Phase 2 post-execution, Phase 3 post-findings)
```

- [ ] **Step 4: Verify the file is still under 500 lines**

Run: `wc -l skills/review/SKILL.md`
Expected: under 500 lines

- [ ] **Step 5: Commit**

```bash
git add skills/review/SKILL.md
git commit -m "feat(knowledge-capture): add 2 knowledge gates to review workflow

Gates fire at end of Phase 2 (agent execution complete) and end of
Phase 3 (findings resolved). Both invoke knowledge-capture skill."
```

---

### Task 8: Add knowledge gate to triage workflow

**Files:**
- Modify: `skills/triage/SKILL.md`

- [ ] **Step 1: Add knowledge gate at end of Phase 3 (Fix)**

In `skills/triage/SKILL.md`, after the recovery verification at the end of Phase 3 (after the "If still broken" escalation section, before any completion section), insert:

```markdown

### Knowledge Gate: Post-Fix

**KNOWLEDGE GATE (KG)**: Pause and invoke: `Skill(skill="panther-ivy-plugin:knowledge-capture")`
- Reflect on debugging patterns from infrastructure troubleshooting
- Capture the diagnosis-to-fix sequence for future triage sessions
- Save session log (observability events + digest)
- If candidates found, classify and present for user confirmation
- Resume workflow after gate completes
```

- [ ] **Step 2: Verify the file is still under 500 lines**

Run: `wc -l skills/triage/SKILL.md`
Expected: under 500 lines

- [ ] **Step 3: Commit**

```bash
git add skills/triage/SKILL.md
git commit -m "feat(knowledge-capture): add knowledge gate to triage workflow

Gate fires at end of Phase 3 (fix applied) to capture debugging
patterns from infrastructure troubleshooting."
```

---

### Task 9: Add knowledge gate to navigate workflow

**Files:**
- Modify: `skills/navigate/SKILL.md`

- [ ] **Step 1: Add knowledge gate after Phase 1 (context scan)**

In `skills/navigate/SKILL.md`, after the Situation Briefing section at the end of Phase 1 (after the options presentation, before `## Phase 2 — Branch by Context`), insert:

```markdown

### Knowledge Gate: Session Resume Check

**KNOWLEDGE GATE (KG)**: Pause and invoke: `Skill(skill="panther-ivy-plugin:knowledge-capture")`
- Check if the most recent session digest has deferred candidates to re-present
- On warm resume: review the previous session's learnings that were deferred
- Save session log (observability events + digest)
- If deferred candidates found, present for user confirmation before routing
- Resume workflow after gate completes
```

- [ ] **Step 2: Verify the file is still under 500 lines**

Run: `wc -l skills/navigate/SKILL.md`
Expected: under 500 lines

- [ ] **Step 3: Commit**

```bash
git add skills/navigate/SKILL.md
git commit -m "feat(knowledge-capture): add knowledge gate to navigate workflow

Gate fires after Phase 1 (context scan) to re-present deferred
candidates from the previous session."
```

---

### Task 10: Add Stop hook knowledge gate prompt to render-summary.py

**Files:**
- Modify: `hooks/scripts/render-summary.py`

- [ ] **Step 1: Add knowledge gate prompt to the summary output**

In `hooks/scripts/render-summary.py`, in the `build_summary` function, add a final section after the metrics block (after line ~226, before `return "\n".join(parts)`):

OLD:
```python
    # Metrics
    if metrics:
        parts.append(f"[TOOL METRICS] {metrics}")

    return "\n".join(parts)
```

NEW:
```python
    # Metrics
    if metrics:
        parts.append(f"[TOOL METRICS] {metrics}")

    # Knowledge gate prompt
    parts.append(
        "[KNOWLEDGE GATE] Before ending this session, invoke "
        'Skill(skill="panther-ivy-plugin:knowledge-capture") to capture '
        "any learnings from this session. If no learnable patterns are "
        "found, the skill exits silently."
    )

    return "\n".join(parts)
```

- [ ] **Step 2: Verify the edit**

Run: `grep -n "KNOWLEDGE GATE" hooks/scripts/render-summary.py`
Expected: one match showing the new prompt

- [ ] **Step 3: Commit**

```bash
git add hooks/scripts/render-summary.py
git commit -m "feat(knowledge-capture): add Stop hook knowledge gate prompt

Injects a prompt in the session summary telling Claude to invoke
knowledge-capture before ending, ensuring no learnings are lost
when sessions end mid-workflow."
```

---

### Task 11: Update plugin CLAUDE.md to document knowledge-capture

**Files:**
- Modify: `CLAUDE.md` (plugin root)

- [ ] **Step 1: Add knowledge-capture to the Internal Components section**

In the plugin `CLAUDE.md`, find the "Internal Components" section under "Knowledge skills" and add:

OLD:
```markdown
**Knowledge skills** (loaded by workflows, not user-facing):
`counterexample-guide`, `specification-patterns`, `propagation-patterns`, `ivy-writing-guide`, `ivy-toolkit`, `claim-discussion`, `methodology-reference`, `ivy-debugging-methodology`, `ivy-error-patterns`
```

NEW:
```markdown
**Knowledge skills** (loaded by workflows, not user-facing):
`counterexample-guide`, `specification-patterns`, `propagation-patterns`, `ivy-writing-guide`, `ivy-toolkit`, `claim-discussion`, `methodology-reference`, `ivy-debugging-methodology`, `ivy-error-patterns`, `knowledge-capture`
```

- [ ] **Step 2: Add knowledge-capture to the Quick Reference section**

In the plugin `CLAUDE.md`, find the "Quick Reference" section and update:

OLD:
```markdown
**Internal knowledge**: counterexample-guide, specification-patterns, propagation-patterns, ivy-writing-guide, ivy-toolkit, claim-discussion, methodology-reference, ivy-debugging-methodology, ivy-error-patterns
```

NEW:
```markdown
**Shortcuts**: /nct-check, /nct-compile, /nct-model-info, /nct-iut-test, /nct-health, /nct-observability, /nct-learn
**Internal knowledge**: counterexample-guide, specification-patterns, propagation-patterns, ivy-writing-guide, ivy-toolkit, claim-discussion, methodology-reference, ivy-debugging-methodology, ivy-error-patterns, knowledge-capture
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add knowledge-capture skill and nct-learn command to plugin CLAUDE.md"
```

---

### Task 12: Verify complete integration

- [ ] **Step 1: Count total lines in new files**

Run:
```bash
wc -l skills/knowledge-capture/SKILL.md skills/knowledge-capture/references/knowledge-taxonomy.md .claude/rules/insights.md commands/nct-learn.md
```
Expected: SKILL.md under 200, taxonomy under 250, insights ~5, nct-learn ~15

- [ ] **Step 2: Verify all workflow SKILLs are under 500 lines**

Run:
```bash
wc -l skills/verify/SKILL.md skills/build/SKILL.md skills/review/SKILL.md skills/triage/SKILL.md skills/navigate/SKILL.md
```
Expected: all under 500 lines

- [ ] **Step 3: Verify all knowledge gate markers are present**

Run:
```bash
grep -r "KNOWLEDGE GATE" skills/*/SKILL.md hooks/scripts/render-summary.py
```
Expected: 9 matches (2 verify + 2 build + 2 review + 1 triage + 1 navigate + 1 render-summary)

- [ ] **Step 4: Verify skill references are consistent**

Run:
```bash
grep -r "knowledge-capture" skills/ commands/ CLAUDE.md .claude/rules/ hooks/
```
Expected: references in all 5 workflow SKILLs, README.md, CLAUDE.md, nct-learn command, and render-summary.py

- [ ] **Step 5: Verify .panther-ivy/session-logs/ is gitignored**

Run:
```bash
grep "panther-ivy" .gitignore
```
Expected: `**/.panther-ivy/` is already present (confirmed during review)

- [ ] **Step 6: Final commit (if any fixups needed)**

```bash
git add -A
git commit -m "fix(knowledge-capture): integration fixups from verification pass"
```
