# Reflection, Interaction, and Multi-Agent Exploration Enhancements

**Date**: 2026-04-14
**Status**: Approved
**Scope**: All 5 panther-ivy-plugin workflow skills

## Problem

The panther-ivy-plugin's workflow skills run long multi-phase processes with limited user interaction. Skill routing is only checked at session start (via `route-user-prompt.py` hook) and never re-evaluated mid-workflow. When Claude commits to an approach, it follows a single analysis path without exploring alternatives. Users lose visibility into why decisions are being made and what options exist.

## Goals

1. **Periodic reflection**: Re-check whether the active workflow still matches the user's evolving intent at strategic points during execution.
2. **Richer user interaction**: Explain situations, present options with trade-offs, and confirm next steps before committing — using `AskUserQuestion` at 16 new decision points.
3. **Multi-perspective exploration**: Dispatch parallel agents with divergent role + method combinations to explore multiple approaches before committing to one.

## Approach

**Distributed inline patterns** in each SKILL.md, with a new knowledge skill (`skills/reflection-patterns/SKILL.md`, `user-invocable: false`) defining three reusable pattern templates. Each workflow skill loads this knowledge skill when it reaches an interaction point. This follows the existing convention where shared knowledge lives in dedicated skills (e.g., `methodology-reference`, `counterexample-guide`) rather than a top-level `skills/references/` directory. No new hooks.

## Pattern Definitions

### Pattern A: Reflection Gate (RG)

A structured pause where Claude:

1. Summarizes the current state in 2-3 sentences (phase, findings, pending work).
2. Re-evaluates workflow fit by checking:
   - Has the user's language shifted toward a different workflow's domain?
   - Did findings suggest a different workflow would be more appropriate?
   - Are we in a dead-end loop (same error twice, no progress)?
3. Presents 2-3 options via `AskUserQuestion`:
   - **(a)** Continue current path (explain what happens next)
   - **(b)** Switch to a named alternative workflow (explain why it might be better)
   - **(c)** Pause and explain more before deciding
4. If user picks (b): update `active-workflow` state and dispatch the new workflow skill.

**When to use**: After analysis results that could change direction. After phase completions. After repeated failures.

### Pattern B: Multi-Perspective Exploration (MPE)

At key decision points, dispatch 2-3 parallel agents with divergent role + method prompts:

| Agent | Role | Method | Focus Question |
|-------|------|--------|---------------|
| **Conservative Architect** | Safety-first formal methods expert | Top-down decomposition from spec to implementation | "What could go wrong? What's missing?" |
| **Pragmatic Engineer** | Velocity-focused builder | Bottom-up from working code to abstractions | "What's the fastest path to a working result?" |
| **Adversarial Auditor** | Red-team antagonist | Stress-test via edge cases and counterexamples | "Where does this break? What assumptions are wrong?" |

Each agent receives:
- The same context (current state, files, findings)
- A system prompt encoding its role + method bias
- Instructions to produce a short analysis (under 300 words) with: assessment, recommendation, risks

After all agents return, Claude:
1. Synthesizes findings into a comparison (agreement points, disagreements, unique insights)
2. Presents the synthesis via `AskUserQuestion` with options based on agent recommendations
3. Proceeds with the user's chosen direction

**Agent tool access**: MPE ad-hoc agents must be read-only. Use `subagent_type: "Explore"` (which restricts to Read, Grep, Glob, and similar search tools) to prevent unintended file modifications during exploration. When an MPE slot maps to an existing agent definition (e.g., spec-analyst), use its `subagent_type` instead — those already have curated tool lists.

**When to use**: Before committing to an architectural approach. When diagnosing ambiguous failures. When multiple valid paths exist.

### Pattern C: Situation Briefing (SB)

Before major phase transitions, Claude:

1. Explains the current situation in plain language:
   - What happened in the previous phase
   - What was found (key results, metrics, issues)
   - What it means for the user's goal
2. Lists 2-4 concrete options for the next step, each with:
   - What it involves
   - Expected outcome
   - Trade-off (time, coverage, risk)
3. Uses `AskUserQuestion` to confirm the user's choice before proceeding.

**When to use**: At every major phase transition. Before multi-step operations. After receiving agent results.

## Per-Workflow Placement

### Navigate (3 new points)

| Location | Pattern | Purpose |
|----------|---------|---------|
| After Phase 1 context scan | SB | Explain detected context (warm resume / activity / cold start), present branching options |
| Before dispatching to workflow | RG | Re-check that chosen workflow matches intent before committing |
| Cold start interview (ambiguous goals) | MPE | Dispatch methodology expert, tool expert, testing expert to explore what user might need |

### Verify (4 new points)

| Location | Pattern | Purpose |
|----------|---------|---------|
| After Phase 2 test selection | SB | Explain found tests, their purpose, confirm selection before compiling |
| After Phase 4 execution results | RG | Re-evaluate: continue to IUT testing, switch to review, or go back to build? |
| Phase 6 diagnosis | MPE | Dispatch conservative architect + pragmatic engineer + adversarial auditor for competing failure diagnoses |
| Before Phase 7 fix attempt | SB | Explain diagnosis consensus/disagreement, present fix options, confirm |

### Build (4 new points)

| Location | Pattern | Purpose |
|----------|---------|---------|
| After Phase 1 scope | MPE | Competing architectural proposals: minimal viable vs comprehensive vs security-focused |
| After Phase 2 blueprint | SB | Explain chosen blueprint, compare with agent recommendations, confirm |
| Every 3 layers during Phase 3 | RG | Re-evaluate: is approach working? Adjust remaining layers? User understanding changed? |
| Phase 4 (Verify sub-workflow) | — | No new point needed; verify sub-workflow has its own interaction points |
| After Phase 5 quality gate | SB | Synthesize model-reviewer + traceability-agent findings, explain severity, present fix options |

### Review (3 new points)

| Location | Pattern | Purpose |
|----------|---------|---------|
| After Phase 1 type detection | SB | Explain detected review type and reasoning, confirm before executing |
| Phase 2 execution | MPE | Add adversarial auditor alongside model-reviewer + spec-analyst (3 agents) |
| Phase 3 findings | RG | Re-evaluate: fix inline, switch to verify, or switch to build for structural fixes? |

### Triage (2 new points)

| Location | Pattern | Purpose |
|----------|---------|---------|
| Phase 2 Diagnose entry (unhealthy path only) | SB | Explain what's broken, likely cause, present recovery options. Only fires when Phase 1 detects an unhealthy component — skipped on the healthy/silent-return path. |
| After Phase 3 fix attempt (failed) | RG | Re-evaluate: deeper infrastructure problem? Escalate? Manual steps? |

## Interaction Point Summary

- **Existing gate checkpoints**: 8 (navigate: 2, verify: 2, build: 2, review: 1, triage: 1)
- **New points added**: 16 (5 RG + 4 MPE + 7 SB)
- **Total user-facing decision points**: 24

## Agent Prompt Templates

Each MPE agent gets a structured prompt:

```
You are the {ROLE_NAME} reviewing {CONTEXT}.

**Your role**: {ROLE_DESCRIPTION}
**Your method**: {METHOD_DESCRIPTION}
**Your focus question**: {FOCUS_QUESTION}

Context:
- Current workflow: {workflow}
- Current phase: {phase}
- Protocol: {protocol}
- Key findings so far: {findings_summary}
- Files involved: {file_list}

Produce a short analysis (under 300 words) with:
1. **Assessment**: What do you see in the current state?
2. **Recommendation**: What should we do next and why?
3. **Risks**: What could go wrong with your recommendation?
4. **Dissent**: Where might the other reviewers disagree with you?
```

## Implementation Files

| File | Action | Description |
|------|--------|-------------|
| `skills/reflection-patterns/SKILL.md` | Create | Knowledge skill (user-invocable: false) with pattern definitions (RG, MPE, SB) |
| `skills/navigate/SKILL.md` | Edit | Add 3 interaction points (1 RG, 1 MPE, 1 SB) |
| `skills/verify/SKILL.md` | Edit | Add 4 interaction points (1 RG, 1 MPE, 2 SB) |
| `skills/build/SKILL.md` | Edit | Add 4 interaction points (1 RG, 1 MPE, 2 SB) |
| `skills/review/SKILL.md` | Edit | Add 3 interaction points (1 RG, 1 MPE, 1 SB) |
| `skills/triage/SKILL.md` | Edit | Add 2 interaction points (1 RG, 1 SB) |

## Constraints

- Skills must stay under 500 lines (per skill-conventions rule). Heavy pattern definitions go in the `reflection-patterns` knowledge skill.
- Each SKILL.md adds only brief inline sections (5-15 lines each) referencing the shared patterns.
- MPE agents use existing agent definitions (spec-analyst, model-reviewer) when their specialization matches. Additional perspective agents use ad-hoc prompts with `subagent_type: "Explore"` (read-only) — no new agent definitions in `agents/`.
- Reflection Gates must not block sub-workflow calls (when `invocation_depth > 0`, skip RG to avoid interrupting parent workflow flow). Each SKILL.md's inline RG section must include the conditional: "If `invocation_depth > 0`, skip this Reflection Gate."
- Situation Briefings are always shown regardless of invocation depth — users always see what's happening. Exception: triage's SB only fires on the unhealthy path (when Phase 1 detects a dead component), not on every triage invocation.

## Non-Goals

- No new hooks (using inline skill instructions only)
- No changes to routing-rules.json or hook scripts
- No changes to the style system
- No new agent definitions in `agents/` (MPE agents use ad-hoc prompts)
