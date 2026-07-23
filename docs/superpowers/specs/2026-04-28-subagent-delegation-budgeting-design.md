# Subagent Delegation Budgeting — Design Spec

- **Date**: 2026-04-28
- **Status**: Approved (brainstorming → spec). Implementation plan pending.
- **Owner**: ElNiak
- **Scope**: User-level config at `~/.claude/` (applies across all projects).
- **Author trail**: Brainstormed via `superpowers:brainstorming` on 2026-04-28; four decision points resolved (estimation style, role model, placement, autonomy).

## 1. Problem

Today, the global Claude config (`~/.claude/CLAUDE.md` + `~/.claude/rules/*.md` + `~/.claude/skills/*`) tells Claude *when* to delegate to subagents and *roughly* how many to spawn, but gives no quantitative model for:

1. **Decomposing** a task into subagent-sized slices.
2. **Estimating** the per-phase cost (explore / implement / verify) of each slice.
3. **Choosing K** (the number of parallel subagents) as a function of slice count, per-subagent budget, and the controller's remaining context window.
4. **Gating** the spawn behind explicit approval when the swarm crosses a risk threshold.

The current heuristic — "3-5 parallel sub-agents for tasks touching >5 files" in `rules/context-and-edit-safety.md` — is a useful trigger but provides no budget arithmetic. Sessions have hit symptoms attributable to this gap: swarms that ran out of context mid-task, redundant cross-subagent exploration, and rate-limit friction at K≥5 (already documented in `rules/agent-teams.md` "Known Limitations").

## 2. Existing scaffolding (analyzed before designing)

| File | What it covers today | Why it isn't enough |
|---|---|---|
| `~/.claude/CLAUDE.md` | High-level workflow rules, sub-agent strategy bullet | No quantitative model |
| `~/.claude/rules/context-and-edit-safety.md` | `SUB-AGENT STRATEGY` heuristic, file-read 2k cap, tool-output 50k truncation, 150k compact threshold | Single-line heuristic; no per-phase decomposition |
| `~/.claude/rules/agent-teams.md` | Persistent teammates, file ownership, K≤5 ceiling, cost optimization | Concerns Teams not subagents; no per-phase cost model |
| `~/.claude/rules/feature-pipeline.md` | Brainstorm → Spec → Plan → Execute pipeline | Step 5 says "implement with subagents" without sizing them |
| `superpowers/skills/dispatching-parallel-agents` | When to dispatch, prompt structure | No per-subagent budget |
| `superpowers/skills/subagent-driven-development` | Implementer + spec-reviewer + code-quality-reviewer triad, model selection by complexity | Per-task triad, not per-swarm sizing |

## 3. Decisions

These four were resolved interactively during the brainstorm:

| Decision | Choice | Rationale |
|---|---|---|
| **Estimation style** | T-shirt sizes (XS/S/M/L/XL with token bands) | Robust to model upgrades; no formula maintenance; Claude reasons over bands |
| **Role model per subagent** | All three phases per subagent (explore + implement + verify, end-to-end) | Slices are independent end-to-end; cleanest parallelism; matches user's literal prompt |
| **Placement** | Rule-only — extend `rules/context-and-edit-safety.md`; one-line pointer in `CLAUDE.md` | Cheapest baseline tokens; auto-loaded everywhere; no new skill overhead |
| **Autonomy** | Threshold-based — auto-spawn for K≤2 and total<80k; AskUserQuestion for K≥3 or any L-phase or total>80k | Matches existing `agent-teams.md` "confirm before 3+ teammates" precedent |

## 4. Architecture

### 4.1 Files touched

- **`~/.claude/rules/context-and-edit-safety.md`** — gains a new top-level section `## Delegation Budgeting` directly after `## Context Management`. The existing `SUB-AGENT STRATEGY` bullet inside `## Context Management` is reduced to a one-line teaser pointing down to the new section, so we don't have two competing heuristics in the same file.
- **`~/.claude/CLAUDE.md`** — gains one bullet under `## Workflow Rules` pointing to the new section.

### 4.2 Files NOT touched

- No new rule file.
- No new skill (no `~/.claude/skills/delegation-planning/`).
- `agent-teams.md`, `feature-pipeline.md`, `prompting-best-practices.md` unchanged.
- Superpowers skills unchanged — they read from baseline rule context at invocation time.

### 4.3 Trigger condition (in the rule body)

The framework fires whenever Claude is about to:
1. Call `Agent` with `subagent_type` (one or more times in a turn), OR
2. Call `TeamCreate` followed by `Agent(team_name=...)` spawns, OR
3. Plan multi-step fan-out work that *might* be delegated.

It explicitly does **not** fire for single-shot reads, single greps, or single-file edits.

### 4.4 Integration with existing rules

- `agent-teams.md` "confirm before 3+ teammates" gate becomes the same rule, generalized to subagents and quantified (K≥3 OR total>80k OR any L-phase).
- The 80k per-subagent ceiling and K≤5 ceiling sit alongside existing ceilings (file-read 2k, tool-output 50k, compact 150k) in the same file.
- `subagent-driven-development` skill behavior unchanged at the procedural level; its implementer/reviewer dispatches now read the budgeting rule from baseline context.

## 5. The framework (literal rule content to be inserted)

The text below is the exact body that will be appended to `~/.claude/rules/context-and-edit-safety.md`. The implementation plan will translate this into a concrete edit.

```markdown
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

For each slice S: `cost(S) = explore + implement + verify`. Apply **+20% headroom** for tool truncation re-reads and review loops. Hard ceiling: `1.2 * cost(S) ≤ 80k`. If exceeded, split before dispatching.

The 80k figure is ~40% of a 200k window — leaves room for the subagent's system prompt, CLAUDE.md reload, tool overhead, and reply.

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
K_window = floor(remaining_controller_window / 12k)   # ~12k per subagent reply
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
```

### 5.1 CLAUDE.md pointer (literal content)

Single bullet to be added under `## Workflow Rules` in `~/.claude/CLAUDE.md`:

```markdown
- DELEGATION BUDGETING: Before dispatching subagents (Agent tool) or teammates (TeamCreate), apply the t-shirt sizing, K formula, and 80k per-subagent ceiling from `rules/context-and-edit-safety.md` § Delegation Budgeting. Auto-spawn only when K≤2 and total<80k and no slice has an L-phase; otherwise gate on AskUserQuestion.
```

### 5.2 Existing SUB-AGENT STRATEGY bullet — reduction

The current paragraph in `~/.claude/rules/context-and-edit-safety.md`:

```
- SUB-AGENT STRATEGY: Actively consider delegating to sub-agents when work fans out
  across independent items (auditing N files, researching M questions, running K parallel
  searches). Sub-agents are desirable when the parts of the task don't share state — each
  gets a clean context window, which is usually faster and cheaper than doing everything
  in the main thread. For tasks touching >5 independent files, propose a split into 3–5
  parallel sub-agents (or sequential phases if preferred). Each sub-agent gets its own
  clean context. For tasks requiring persistent coordination, shared state, or peer-to-peer
  communication between workers, escalate to Agent Teams instead (see `rules/agent-teams.md`).
  Think carefully about how to split the work and design their prompt preciselly: ideally,
  each sub-agent should have a clear, independent goal that can be completed with minimal
  cross-agent communication. Avoid splitting work in a way that creates tight coupling or
  requires constant synchronization between agents.
```

is reduced to one line that points down:

```
- SUB-AGENT STRATEGY: When work fans out across independent items, delegate. See
  § Delegation Budgeting below for slice sizing, K formula, and the 80k per-subagent
  ceiling. Escalate to Agent Teams when workers need persistent coordination or
  peer-to-peer messaging (see `rules/agent-teams.md`).
```

This avoids two heuristics fighting each other in the same file.

## 6. Validation

Because the change is purely instructional, validation is empirical.

1. **Static review against `prompting-best-practices.md`** — auto-loaded for any rule edit. The new section will be checked for: clear and direct, states why, positive examples, literal-Opus phrasing, XML-tags-where-needed, examples present.
2. **Spec self-review** — placeholder scan, internal consistency on edge cases (K=2 borderline, cost=79k borderline, remaining_window=60k borderline), scope check, ambiguity check. Done inline before commit.
3. **Smoke-test in real session** — pick a fan-out task in the PANTHER worktree (e.g., delta-audit work tracked in `memory/handoff-2026-04-28.md`), run through the new framework, and confirm: (a) Claude computed K and slice sizes before spawning, (b) the AskUserQuestion gate fired when expected, (c) actual total cost matched estimate within ±30%.
4. **Long-horizon check** — after one week of sessions, look for memory entries of "swarm ran out of context" or "rate-limit hit". Both should drop to zero. If not, the ceilings are too loose.

If smoke-test calibration error exceeds ±30% systematically (e.g. token bands always under-predict), the implementation plan must include a follow-up task to recalibrate the bands; this spec does not freeze the bands as final.

## 7. Out of scope

Explicitly **not** part of this design:

- Per-project overrides (project-level CLAUDE.md, project-level rules). The framework lives at user level only; projects can override individually if needed.
- A new `delegation-planning` skill. Decision was rule-only.
- Changes to `superpowers:subagent-driven-development` or `superpowers:dispatching-parallel-agents`. They consume the rule passively.
- Telemetry / token-counting tooling. The framework is heuristic; no instrumentation.
- Automatic recalibration of bands. Manual sweep based on smoke-test results, if needed.

## 8. Risks and open questions

| Risk | Mitigation |
|---|---|
| T-shirt bands miscalibrated for new model context sizes (Opus 4.7 1M variant) | Bands are token-based, not %-based; 80k ceiling stays same in absolute terms regardless of window size. Adjust K_window divisor if needed. |
| Rule body adds ~150 lines to every CLAUDE.md/rules-loaded context | Worth the cost: prevents per-session context exhaustion that costs more than 150 lines of rule. Pointer-from-CLAUDE.md keeps CLAUDE.md itself small. |
| Claude treats AskUserQuestion gate as ceremonial and skips it | Gate is in baseline rule context; `prompting-best-practices.md` already enforces "ALWAYS use AskUserQuestion for choices". Reinforced. |
| Smoke-test reveals overhead of running the framework on small tasks | Trigger condition explicitly excludes single-shot reads / greps / single-file edits. If still excessive, raise the activation threshold (e.g., from "≥2 slices" to "≥3 slices"). |

Open questions (non-blocking; resolved during implementation if needed):

1. Should the K_window divisor (12k per reply) be tunable per subagent type? (Reviewer subagents return shorter replies than implementers.) — Defer; treat 12k as conservative average.
2. Should the autonomy threshold also gate on `remaining_controller_window`? — Already covered: ceiling table includes "Controller remaining context before dispatch ≥ 60k".

## 9. Implementation plan placeholder

After spec approval, I invoke `superpowers:writing-plans` to produce a numbered task plan. Expected tasks:

1. Edit `~/.claude/rules/context-and-edit-safety.md` — append `## Delegation Budgeting` section, reduce existing `SUB-AGENT STRATEGY` bullet to pointer.
2. Edit `~/.claude/CLAUDE.md` — append `DELEGATION BUDGETING` bullet under `## Workflow Rules`.
3. Self-review against `prompting-best-practices.md`.
4. Smoke-test on a real fan-out task; record actual vs estimated cost.
5. Capture lessons learned into auto-memory if calibration drift > 30%.

No code changes, no test changes, no submodule changes.
