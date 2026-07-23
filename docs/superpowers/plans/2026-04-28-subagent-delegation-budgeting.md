# Subagent Delegation Budgeting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a quantitative delegation-budgeting framework to the user's global Claude config so that fan-out subagent dispatches are sized via t-shirt phase estimates and gated above K=2 or 80k via AskUserQuestion.

**Architecture:** Two file edits in `~/.claude/` — append a new `## Delegation Budgeting` section to `~/.claude/rules/context-and-edit-safety.md` (between the existing `## Context Management` and `## Edit Safety`), reduce the existing multi-paragraph `SUB-AGENT STRATEGY` bullet to a one-line pointer to that section, and add a one-line `DELEGATION BUDGETING` bullet to `~/.claude/CLAUDE.md` at the end of `## Workflow Rules`.

**Tech Stack:** Plain Markdown. No code, no unit tests. The TDD pattern adapts to documentation as: edit → verify with `grep` / re-read → manual checklist. Validation is a static review against `~/.claude/rules/prompting-best-practices.md` plus a real-session smoke test.

**Note on commits:** `~/.claude/` is NOT a git repository on this machine (verified during planning via `git -C ~/.claude rev-parse --git-dir` → fails). All edits persist on disk only; no commit steps are included for the rule and CLAUDE.md edits. The plan itself, and any auto-memory entries written to the project memory directory, are committed inside the PANTHER worktree.

---

## File Structure

| File | Change | Responsibility |
|---|---|---|
| `/Users/elniak/.claude/rules/context-and-edit-safety.md` | Modify (Tasks 1, 2, 4) | Auto-loaded rule body. Receives the new section and the reduced pointer bullet. |
| `/Users/elniak/.claude/CLAUDE.md` | Modify (Task 3) | Top-level user instructions. Gains one bullet pointing to the rule. |
| `docs/superpowers/specs/2026-04-28-subagent-delegation-budgeting-design.md` | Read-only reference | Spec source of truth. |
| `/Users/elniak/.claude/rules/prompting-best-practices.md` | Read-only reference | Static-review checklist for Task 4. |

No new files. No tests. Plan length: 5 tasks (2 edits, 1 pointer, 1 review, 1 smoke test).

---

### Task 1: Reduce the existing SUB-AGENT STRATEGY paragraph to a one-line pointer

**Files:**
- Modify: `/Users/elniak/.claude/rules/context-and-edit-safety.md` (first bullet inside `## Context Management`)

**Why first:** Task 2 inserts a new section that the new pointer references. Doing the reduction first means there is never a window where the pointer points to a non-existent section AND there's never a window where two competing heuristics coexist. (The order is: reduce pointer → insert section. The reduced pointer is a forward reference until step 2 of Task 2 lands; that is OK because no Claude session reads files mid-task.)

- [ ] **Step 1: Read the file to confirm current state**

Use the Read tool on `/Users/elniak/.claude/rules/context-and-edit-safety.md`.

Expected: line 1 is `## Context Management`. Line 3 starts with `- SUB-AGENT STRATEGY: Actively consider delegating to sub-agents when work fans out across independent items` and is a single multi-sentence paragraph that ends with `Avoid splitting work in a way that creates tight coupling or requires constant synchronization between agents.`

- [ ] **Step 2: Edit — replace the multi-paragraph bullet with a one-line pointer**

Use the Edit tool with these arguments. The `old_string` is one long line in the file (no internal newlines).

`old_string`:

```
- SUB-AGENT STRATEGY: Actively consider delegating to sub-agents when work fans out across independent items (auditing N files, researching M questions, running K parallel searches). Sub-agents are desirable when the parts of the task don't share state — each gets a clean context window, which is usually faster and cheaper than doing everything in the main thread. For tasks touching >5 independent files, propose a split into 3–5 parallel sub-agents (or sequential phases if preferred). Each sub-agent gets its own clean context. For tasks requiring persistent coordination, shared state, or peer-to-peer communication between workers, escalate to Agent Teams instead (see `rules/agent-teams.md`). Think carefully about how to split the work and design their prompt preciselly: ideally, each sub-agent should have a clear, independent goal that can be completed with minimal cross-agent communication. Avoid splitting work in a way that creates tight coupling or requires constant synchronization between agents.
```

`new_string`:

```
- SUB-AGENT STRATEGY: When work fans out across independent items, delegate. See § Delegation Budgeting below for slice sizing, K formula, and the 80k per-subagent ceiling. Escalate to Agent Teams when workers need persistent coordination or peer-to-peer messaging (see `rules/agent-teams.md`).
```

- [ ] **Step 3: Verify the edit landed**

Run via the Bash tool:

```bash
grep -c 'SUB-AGENT STRATEGY' /Users/elniak/.claude/rules/context-and-edit-safety.md
```

Expected output: `1`.

```bash
grep 'See § Delegation Budgeting below' /Users/elniak/.claude/rules/context-and-edit-safety.md
```

Expected: prints the new line (one match).

```bash
grep 'Avoid splitting work in a way that creates tight coupling' /Users/elniak/.claude/rules/context-and-edit-safety.md
```

Expected: no output (the old phrase is gone).

- [ ] **Step 4: Skip commit (~/.claude/ is untracked)**

`~/.claude/` is not a git repository. The change is persisted by writing to disk in step 2.

---

### Task 2: Insert the new `## Delegation Budgeting` section between `## Context Management` and `## Edit Safety`

**Files:**
- Modify: `/Users/elniak/.claude/rules/context-and-edit-safety.md`

- [ ] **Step 1: Re-read the file to locate the boundary**

Use the Read tool on `/Users/elniak/.claude/rules/context-and-edit-safety.md`.

Expected: file now contains the reduced SUB-AGENT STRATEGY pointer from Task 1, then `- CONTEXT DECAY AWARENESS`, `- FILE READ BUDGET`, `- TOOL RESULT BLINDNESS`, `- COMPACT AWARENESS` bullets, then a blank line, then `## Edit Safety`. Note the exact line where `## Edit Safety` begins.

- [ ] **Step 2: Edit — insert the new section between COMPACT AWARENESS and `## Edit Safety`**

Use the Edit tool with these arguments. The `old_string` includes the COMPACT AWARENESS bullet, the blank separator line, and the `## Edit Safety` heading so the insertion point is unique.

`old_string`:

```
- COMPACT AWARENESS: Use `/compact` during long sessions to summarize context while preserving CLAUDE.md instructions. Ask user to proactively trigger compaction when approaching ~150k tokens.

## Edit Safety
```

`new_string`:

```
- COMPACT AWARENESS: Use `/compact` during long sessions to summarize context while preserving CLAUDE.md instructions. Ask user to proactively trigger compaction when approaching ~150k tokens.

## Delegation Budgeting

Apply this framework BEFORE spawning subagents (Agent tool) or teammates (TeamCreate). Skip for single-shot lookups; apply when fanning out to ≥2 independent slices or when total work might exceed the controller's remaining context.

### Phase t-shirt sizes (per subagent slice)

| Phase | Size | Token band | Signal | Example |
|---|---|---|---|---|
| Explore | XS | < 2k | 1-2 reads, 1 grep | "Read this file, confirm pattern" |
| | S | 2-8k | 3-5 reads, 1-2 greps | "Trace one function through one module" |
| | M | 8-25k | 5-15 reads, multi-grep | "Audit input validation in one subsystem" |
| | L | 25-60k | 15-30 reads, directory walk | "Map all callers of API X across repo" |
| | XL | > 60k | > 30 reads, recursive expansion | **Split before dispatch.** |
| Implement | XS | < 2k | 1 line in 1 file | Rename, single-line fix |
| | S | 2-12k | 1-3 files, < 200 LOC | Function-level change |
| | M | 12-40k | 3-8 files, < 800 LOC | Multi-file refactor inside one module |
| | L | 40-90k | 8-20 files | **Usually too big — split into M slices.** |
| | XL | > 90k | > 20 files, architecture | **Always split.** |
| Verify | XS | < 2k | 1 test, 1 assertion | Re-run one failing test |
| | S | 2-6k | 1-3 reads, 1 cmd | Targeted test run, lint |
| | M | 6-18k | 3-8 reads, 2-3 cmds | Module suite + cross-check + diff review |
| | L | 18-45k | full suite, cross-cutting | **Split if possible.** |

### Per-subagent budget

For each slice S: `cost(S) = explore + implement + verify`. Apply **+20% headroom** for tool truncation re-reads and review loops. Hard ceiling: `1.2 * cost(S) ≤ 80k`. If exceeded, split before dispatching. The 80k figure is ~40% of a 200k window — leaves room for the subagent's system prompt, CLAUDE.md reload, tool overhead, and reply.

### Hard ceilings (never crossed without explicit user approval)

| Scope | Ceiling | Reason |
|---|---|---|
| Per subagent (estimated work, +20% headroom) | 80k tokens | System prompt + CLAUDE.md + tools + reply |
| Per subagent (files written) | 8 | Beyond this slice is too coarse to verify |
| Per subagent (files read) | 30 | Mirrors Explore-L upper bound |
| Per swarm (parallel K) | 5 | Matches `agent-teams.md`; rate-limit safety |
| Controller remaining context before dispatch | ≥ 60k | Need room to read replies and integrate |

### Computing K

Given N independent slices, after each slice fits the per-subagent ceiling:

```
K_target = N
K_window = floor(remaining_controller_window / 12k)
K_actual = min(K_target, 5, K_window)
```

If K_actual < K_target, run remaining (N − K_actual) slices in a sequential second batch.

### Autonomy threshold

```
if K_actual <= 2
   and total_estimated_cost < 80k
   and no_slice_is_L_in_any_phase:
    announce in one sentence, spawn directly
else:
    AskUserQuestion(
      question = "Proposed delegation: K subagents, cost X, slices Y. Approve?",
      options  = [approve, revise K / slices, abort delegation, run sequentially]
    )
```

### Anti-patterns

1. **Overlapping exploration** — K subagents that each grep the same callers waste K×explore. If explore is M+ and overlap is high, do one shared exploration in the controller (or one explorer subagent) feeding K parallel implementers.
2. **Skipping verify to fit budget** — leaves the controller no way to confirm the slice. Always reserve at least an XS verify; if that pushes over 80k, the slice is too big.
3. **Estimating only the happy path** — no retries, no truncation re-reads, no review loops. The +20% headroom exists for this; do not skip.
4. **Ignoring controller-side cost** — the controller reads back every reply. Five subagents × 12k summary = 60k consumed before integration. K_window accounts for this.
5. **Promoting a sub-task to a slice when it shares state** — two slices both editing a shared registry are one slice, not two. The shared-files rule from `agent-teams.md` applies.
6. **Treating K as a quota** — the formula gives an upper bound, not a target. If K=2 suffices, don't spawn 5.

### Worked examples

**Fits in one subagent.** "Audit input validation in `panther/config/parser.py` and add three missing checks":
- Explore M (read parser + 4 callers + grep tests) → ~15k
- Implement S (3 edits in 1 file) → ~5k
- Verify S (run unit tests + grep regressions) → ~4k
- Raw 24k. With +20% headroom → 28.8k. Under 80k → single subagent, no split.

**Must split before dispatch.** "Refactor 12-file authentication subsystem to use new session API":
- Explore L (15-30 reads across `auth/`, callers in 4 modules) → ~40k
- Implement L (12 files, ~600 LOC changed) → ~50k
- Verify M (suite + cross-module grep + diff review) → ~12k
- Raw 102k. With +20% headroom → 122.4k. **Exceeds 80k → must split.**
- Split: slice A = `auth/core/` (4 files, M+M+S → ~38k), slice B = `auth/middleware/` (4 files, M+M+S → ~36k), slice C = call-site updates (4 files, S+M+S → ~28k). Each slice fits; K_target = 3.

## Edit Safety
```

- [ ] **Step 3: Verify the section landed at the right boundary**

Run via Bash:

```bash
grep -c '^## Delegation Budgeting$' /Users/elniak/.claude/rules/context-and-edit-safety.md
```

Expected output: `1`.

```bash
awk '/^## /{print NR": "$0}' /Users/elniak/.claude/rules/context-and-edit-safety.md
```

Expected: shows three top-level headers in this exact order, on increasing line numbers — `## Context Management`, `## Delegation Budgeting`, `## Edit Safety`.

```bash
grep -c 'Phase t-shirt sizes' /Users/elniak/.claude/rules/context-and-edit-safety.md
```

Expected output: `1`.

```bash
grep -c '80k tokens' /Users/elniak/.claude/rules/context-and-edit-safety.md
```

Expected output: `1` (this anchors the per-subagent ceiling row).

- [ ] **Step 4: Skip commit (~/.claude/ is untracked)**

Persisted on disk by step 2.

---

### Task 3: Add the DELEGATION BUDGETING bullet to `~/.claude/CLAUDE.md`

**Files:**
- Modify: `/Users/elniak/.claude/CLAUDE.md` (end of `## Workflow Rules`, before `## Note on environment`)

- [ ] **Step 1: Read the file to confirm the boundary**

Use the Read tool on `/Users/elniak/.claude/CLAUDE.md`.

Expected: contains a `## Workflow Rules` section. The last paragraph in that section begins with "When encountering obstacles, do not use destructive actions as a shortcut." and ends with "discard unfamiliar files that may be in-progress work." A blank line separates that paragraph from a heading on the next non-blank line.

- [ ] **Step 2: Edit — append the new bullet to the end of the obstacles paragraph**

Anchor on the obstacles paragraph alone; do not include any subsequent heading line in the boundary. Pre-commit hooks may strip trailing whitespace inside code blocks of this plan, which would corrupt heading anchors. The `new_string` adds a blank line and the new bullet immediately after the paragraph; the existing blank line + heading that follow the paragraph in the target file are preserved untouched.

Use the Edit tool with these arguments:

`old_string`:

```
When encountering obstacles, do not use destructive actions as a shortcut. For example, don't bypass safety checks (e.g. --no-verify) or discard unfamiliar files that may be in-progress work.
```

`new_string`:

```
When encountering obstacles, do not use destructive actions as a shortcut. For example, don't bypass safety checks (e.g. --no-verify) or discard unfamiliar files that may be in-progress work.

- DELEGATION BUDGETING: Before dispatching subagents (Agent tool) or teammates (TeamCreate), apply the t-shirt sizing, K formula, and 80k per-subagent ceiling from `rules/context-and-edit-safety.md` § Delegation Budgeting. Auto-spawn only when K≤2 and total<80k and no slice has an L-phase; otherwise gate on AskUserQuestion.
```

- [ ] **Step 3: Verify the bullet landed and the heading order is preserved**

Run via Bash:

```bash
grep -c 'DELEGATION BUDGETING' /Users/elniak/.claude/CLAUDE.md
```

Expected output: `1`.

```bash
grep -c 'Delegation Budgeting' /Users/elniak/.claude/CLAUDE.md
```

Expected output: `2` (one in the bullet name's all-caps form, one in the section reference).

```bash
awk '/^## /{print NR": "$0}' /Users/elniak/.claude/CLAUDE.md | head -20
```

Expected: `## Workflow Rules` appears before `## Note on environment` and the line numbers are consistent with the new bullet inserted between them (Note on environment moved down by ~3 lines).

- [ ] **Step 4: Skip commit (~/.claude/ is untracked)**

Persisted on disk by step 2.

---

### Task 4: Static review against `prompting-best-practices.md`

**Files:**
- Read-only: `/Users/elniak/.claude/rules/context-and-edit-safety.md` (the new section from Task 2)
- Read-only: `/Users/elniak/.claude/rules/prompting-best-practices.md` (the checklist source)
- Conditionally modify: `/Users/elniak/.claude/rules/context-and-edit-safety.md` (only if a principle fails)

- [ ] **Step 1: Read the prompting-best-practices.md checklist**

Use the Read tool on `/Users/elniak/.claude/rules/prompting-best-practices.md`.

Expected: 6 numbered principles followed by a source link to `https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices`.

- [ ] **Step 2: Read the new Delegation Budgeting section in isolation**

Use the Read tool on `/Users/elniak/.claude/rules/context-and-edit-safety.md`.

Locate the `## Delegation Budgeting` heading and read through `## Edit Safety` (exclusive). This is the subject of the review.

- [ ] **Step 3: Apply each principle as a pass/fail check**

For each row, write the verdict (`PASS` / `FAIL: <reason>`) to a scratch note in your reply. Do not edit yet.

| # | Principle | Pass criterion |
|---|---|---|
| 1 | Clear, direct, specific | Every threshold has a concrete number; no "small/large/several" without bounds |
| 2 | Explain WHY | The 80k ceiling has a "Reason" column; the per-subagent budget paragraph explains the 40%-of-200k motivation |
| 3 | Tell what to do, not what not to do | Anti-patterns are negative form, but each one names the counter-pattern; positive guidance dominates |
| 4 | XML tags for structure | N/A for Markdown rules; tables provide structure |
| 5 | Opus 4.7 is literal | Trigger condition states explicit scope ("apply when fanning out to ≥2 independent slices"); does not say "consider" without bound |
| 6 | Data at top, query at bottom | N/A for rule files |

- [ ] **Step 4: Fix any FAIL inline**

For each principle that failed, edit the section using the Edit tool. Re-read the section after each edit to confirm. Do NOT re-run all six checks; only re-check the one(s) you edited.

- [ ] **Step 5: Verify final state**

Run via Bash:

```bash
wc -l /Users/elniak/.claude/rules/context-and-edit-safety.md
```

Expected: line count is unchanged from end-of-Task-2 OR larger by the size of any added clarifications. Should not be smaller.

- [ ] **Step 6: Skip commit (~/.claude/ is untracked)**

Persisted on disk by Task 2 step 2 and Task 4 step 4.

---

### Task 5: Smoke test on a real fan-out task

**Files:**
- None modified (observation only).
- Conditionally write: a feedback auto-memory entry if calibration drifts > 30%.

- [ ] **Step 1: Identify a candidate fan-out task**

Read `/Users/elniak/.claude/projects/-Users-elniak-Documents-Documents-Work-Project-Protocol-Testing-Security-PANTHER-master/memory/MEMORY.md` and pick an open audit / multi-file task.

Recommended candidate (from active work entries): the BGP delta-audit work in `handoff-2026-04-28.md`. Alternative: any open multi-file refactor or audit listed under "Active Work".

If MCP / Ivy tooling is unavailable for the chosen task, pick a task that does not depend on MCP (e.g., a documentation review or grep-driven audit).

- [ ] **Step 2: Start a fresh Claude Code session in this worktree and request the task**

The new rules will load automatically because `~/.claude/rules/*.md` matches the auto-load glob in `prompting-best-practices.md` (`**/.claude/rules/**/*.md`).

Request the task in natural language, for example: "Resume the BGP delta-audit. Decompose into subagents using the delegation-budgeting rule from `rules/context-and-edit-safety.md`."

- [ ] **Step 3: Observe and record three things in a scratch note**

Note in a temporary scratch file (not committed) for each delegation Claude attempts:

1. Did Claude compute K and per-slice phase sizes BEFORE issuing any `Agent` tool call? (Yes / No)
2. Did the AskUserQuestion gate fire when K_actual ≥ 3 OR total estimated cost > 80k OR any slice was L in any phase? (Yes / No / Not applicable for this task)
3. Compare estimated total cost vs observed cost. Observed cost is approximated by `(sum of subagent reply token counts) + (sum of tool-output token counts read by controller)`. Record both numbers and the percentage difference.

- [ ] **Step 4: If calibration drift > 30%, capture as auto-memory entry**

If `|observed − estimated| / estimated > 0.30` for two or more slices, write a feedback auto-memory entry. Use the Write tool to create:

`/Users/elniak/.claude/projects/-Users-elniak-Documents-Documents-Work-Project-Protocol-Testing-Security-PANTHER-master/memory/feedback_delegation_band_drift.md`

with this content:

```markdown
---
name: Delegation t-shirt bands miscalibrated
description: Smoke test on YYYY-MM-DD showed observed cost diverged from estimated by >30% in the <phase> band; recalibrate before next swarm
type: feedback
---

The Delegation Budgeting framework's <phase> bands miscalibrated against the <task name> smoke test on YYYY-MM-DD.

- Estimated: <X>k
- Observed: <Y>k
- Drift: <Z>%
- Probable cause: <one sentence — e.g. "explore phase under-counts grep retries">

**Why:** Empirical recalibration trigger. The framework was authored without prior measurement; the first smoke test is the calibration check.

**How to apply:** Before next swarm, adjust the <phase> token band in `~/.claude/rules/context-and-edit-safety.md` § Delegation Budgeting. Re-run smoke test until drift < 30%.
```

Then update `MEMORY.md` to add a one-line pointer:

```markdown
- [Delegation band drift](feedback_delegation_band_drift.md) — Smoke test 2026-04-28 showed >30% drift in <phase>; recalibrate before next swarm
```

- [ ] **Step 5: Commit the auto-memory entry inside this worktree (if Step 4 ran)**

The PANTHER worktree IS git-tracked. The memory directory is under `/Users/elniak/.claude/projects/...` which is outside this worktree, so it is also untracked. Skip the commit; the memory entry persists on disk.

If no drift was found, Step 4 didn't run and there is nothing to commit. The plan ends here.

---

## Self-Review (run before handing off to executor)

### Spec coverage check

| Spec section | Implemented in |
|---|---|
| §4.1 Files touched | Tasks 1, 2, 3 |
| §4.3 Trigger condition | Task 2 step 2 (rule body intro paragraph) |
| §4.4 Integration with existing rules | Task 1 (reduces existing bullet to pointer) |
| §5 Phase t-shirt table | Task 2 step 2 |
| §5 Per-subagent budget + 20% headroom | Task 2 step 2 |
| §5 Hard ceilings | Task 2 step 2 |
| §5 Computing K | Task 2 step 2 |
| §5 Autonomy threshold | Task 2 step 2 |
| §5 Anti-patterns (six) | Task 2 step 2 |
| §5 Worked examples (under-budget + must-split) | Task 2 step 2 |
| §5.1 CLAUDE.md pointer | Task 3 |
| §5.2 Reduce SUB-AGENT STRATEGY | Task 1 |
| §6.1 Static review against prompting-best-practices | Task 4 |
| §6.3 Smoke test | Task 5 |
| §6.4 Long-horizon check | Out of plan; user runs after one week |

No gaps.

### Placeholder scan

- No "TBD", no "TODO", no "fill in details" anywhere in tasks 1-5.
- Every Edit step gives literal `old_string` and `new_string` content.
- Every verification step gives the exact Bash command and expected output.

### Type / name consistency

- Section name `## Delegation Budgeting` is identical in: spec §5, Task 2 step 2 insertion, Task 3 CLAUDE.md pointer, all `grep` verifications.
- Numerical thresholds 80k / 5 / 60k / 12k / 20% / 30% appear consistently across task body and verifications.
- Phase names `Explore` / `Implement` / `Verify` are consistent across t-shirt table, anti-patterns, and worked examples.
