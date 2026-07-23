# Claude config review framework (Opus 4.7-aware)

**Date:** 2026-04-22
**Model context at authoring:** claude-opus-4-7 (1M)
**Status:** Approved framework. Execution runbook lives at `~/.claude/plans/i-need-to-evaluate-unified-moonbeam.md`.

## Context

This document is a reusable methodology for reviewing the Claude Code instruction surface (`CLAUDE.md` files, `~/.claude/rules/`, every `SKILL.md`, plugin manifests, settings, hooks, and persistent memory) against a specific Claude model's behavior and Anthropic's then-current best practices. It was first applied to the Opus 4.6 → 4.7 migration; the same scaffolding can be re-run for any future model release by swapping the anti-pattern catalog (Section 2) and re-running the checklist (Section 3).

The framework has three pieces: a per-file scoring rubric that produces a numeric grade so files can be triaged into "rewrite", "tune", or "leave alone" buckets; a catalog of patterns that became anti-patterns under the target model, with sourced explanations and concrete remediations; and an executable shell checklist that emits a baseline before any edits and a regression check after.

## 1. Per-file scoring rubric

Each instruction file is scored on six axes, 0–2 each (12 max).

| Axis | 0 (bad) | 1 (ok) | 2 (good) |
|---|---|---|---|
| **Explicitness** | Hints, soft modifiers ("if possible", "ideally"), inferred steps | Mixed; some explicit, some vague | Every directive is unambiguous; positive forms preferred over negatives |
| **Scope clarity** | Always-on prose; no condition for when it fires | Implicit scope ("for Python files") | `paths:` frontmatter or first-line "Applies to: …" |
| **Token weight** | CLAUDE.md > 200 lines, SKILL.md `description + when_to_use` > 1,536 chars | Within 25% of cap | Lean: ≤ 80% of cap |
| **Enforcement layer** | Prose ban for behavior that must hold every time | Prose + sometimes a hook | Hook (PreToolUse/PostToolUse) for non-negotiables; prose only for advisory |
| **Redundancy** | Stated more than once in same file or duplicated across files | One near-duplicate elsewhere | Single source of truth; cross-refs use the Skill tool |
| **Currency** | References removed APIs (`temperature`, `top_p`, `budget_tokens`), old model ids, dead skills | Some stale phrasing | All references valid in the target model |

**Triage bands:**

- Score < 7/12 → **Rewrite**: file's primary contract is broken; full pass needed.
- Score 7–10 → **Tune**: targeted edits restore alignment.
- Score 11–12 → **Leave**: in good shape.

The rubric assumes a target model. The "Currency" and "Enforcement layer" axes are the most model-sensitive; "Token weight" thresholds (200 lines, 1,536 chars) are Anthropic's published Opus 4.7 caps and may shift in future releases — verify against `code.claude.com/docs/en/memory` and `…/skills` before re-running on a new model.

## 2. Anti-pattern catalog (Opus 4.7)

Each entry: pattern, why it is an anti-pattern under this model, source, remediation.

1. **Mandatory-skill-routing prose** — phrasing like "You MUST always use /superpowers:executing-plans" or "You MUST always use TaskList". 4.7 follows literally and routes to the skill even on trivial single-file edits, wasting a turn. *Source:* "Treat Claude like a capable engineer you're delegating to" — Anthropic Claude Code best-practices blog. *Remediation:* phrase as advisory ("for multi-file work, prefer …") and let the model judge; reserve `MUST` only for genuinely zero-exception rules backed by hooks.

2. **Soft modifiers used as emphasis** — "try to", "if possible", "ideally", "consider". In 4.6 these were polite ways to say "do this". Under 4.7 the migration guide states they are interpreted literally as optional and are routinely skipped. *Source:* Anthropic migration guide (April 2026). *Remediation:* if you mean "do this", write the imperative; if you mean "consider", say "consider" and accept it is sometimes skipped.

3. **Hint-based skills** — short SKILL.md bodies that gesture at a workflow and expect the model to fill gaps. Under 4.7 these underperform compared to longer, prescriptive bodies. *Source:* community regression study by Mohit Aggarwal (re-tested 90 skills on 4.7), April 2026. *Remediation:* add explicit examples, fully-formed snippets, and prescriptive sequences.

4. **Verbatim duplication across skills** — the same rule block restated in multiple SKILL.md files. Doubles token cost and risks divergence. *Remediation:* extract to a shared resource file (no frontmatter, not a SKILL.md), referenced from each skill.

5. **Prose Iron Laws for behavior with deterministic checks available** — "NEVER invoke `ivyc` directly" relies on the model to remember. A `PreToolUse` hook matching `Bash(ivyc:*)` cannot be forgotten. *Source:* Anthropic best-practices blog: "Use hooks for actions that must happen every time with zero exceptions." *Remediation:* convert one-line shell-detectable bans to hooks; keep prose only as the *explanation* of why the hook exists.

6. **Implicit reliance on auto-subagents** — phrases like "spawn subagents to investigate" without the explicit verb. 4.7 spawns fewer subagents by default than 4.6. *Source:* Anthropic Claude Code best-practices blog. *Remediation:* prepend "Use subagents to …" or "parallelize across …" wherever subagent fan-out is required.

7. **Removed-API references** — `temperature`, `top_p`, `top_k`, `thinking.budget_tokens`. Return 400 in 4.7. *Source:* Anthropic API migration guide. *Remediation:* delete; use `effort` (settings key `effortLevel`) and `thinking.adaptive`.

8. **CLAUDE.md > 200 lines** — auto-truncated past line 200 / 25 KB. *Source:* `code.claude.com/docs/en/memory`. *Remediation:* split overflow into rules with `paths:` frontmatter or into skills.

9. **Long SKILL.md description+when_to_use** — the listing cap is 1,536 chars. Beyond that, the skill is harder to trigger. *Source:* Anthropic skills docs. *Remediation:* tighten descriptions, push detail into the body.

10. **Dual-purpose rule and skill** — a `rules/foo.md` file and a `skills/foo/SKILL.md` file covering the same material. Two sources of truth. *Remediation:* keep the skill (richer body, lazy loaded), and either delete the rule or convert it to a one-line pointer using the Skill tool.

11. **Memory entries past 30 days self-flagged "likely stale"** — when a `MEMORY.md` index already says "verify before acting", the entries consume index space on every session for negative value. *Remediation:* move to `memory/historical/` (move, don't delete — destructive ops should be reserved for end of phase, after smoke tests pass).

## 3. Audit checklist (rerunnable per model release)

Each step is a single shell or grep invocation; results pipe into a scratch file. Order surfaces the largest-leverage findings first.

```bash
# 1. CLAUDE.md size budget (target: every file ≤ 200 lines)
for f in ~/.claude/CLAUDE.md $(git ls-files '**/CLAUDE.md' 2>/dev/null); do
  printf "%5d  %s\n" $(wc -l < "$f") "$f"
done | awk '$1 > 200 {print "OVER  "$0; next} {print "ok    "$0}'

# 2. Skill description budget (target: every description ≤ 1,536 chars)
for f in $(find ~/.claude/skills */skills -name SKILL.md 2>/dev/null); do
  desc=$(awk '/^description:/{flag=1} /^---/{flag=0} flag' "$f" | wc -c)
  [ "$desc" -gt 1536 ] && echo "OVER  $desc  $f"
done

# 3. Soft-modifier scan (anti-pattern #2)
grep -niE '\b(if possible|ideally|try to|consider whether|when convenient)\b' \
  ~/.claude/CLAUDE.md ~/.claude/rules/*.md 2>/dev/null

# 4. Mandatory-skill-routing scan (anti-pattern #1)
grep -niE 'MUST always use|always invoke .*skill|MUST always.*Task' \
  ~/.claude/CLAUDE.md ~/.claude/rules/*.md 2>/dev/null

# 5. Removed-API scan (anti-pattern #7)
grep -nE '\b(temperature|top_p|top_k|budget_tokens)\b' \
  ~/.claude ~/.claude/skills 2>/dev/null

# 6. Verbatim duplication across skills (anti-pattern #4) — run via subagent
#    Emits pairs with > 80% line overlap.

# 7. Memory staleness (anti-pattern #11) — files with mtime > 30 days
ls -lt ~/.claude/projects/*/memory/*.md | awk '$6 < "'$(date -v-30d +%Y-%m-%d)'"'
```

**Success metric:** every file lands in score band 11–12, every checklist step returns empty.

## 4. How to apply to a future model release

When a new Claude model ships, the framework re-runs in four steps:

1. **Refresh anti-pattern catalog (Section 2).** Read the model's release notes, migration guide, and Claude Code best-practices blog. Add patterns that became anti-patterns; mark patterns that are no longer problems. Cite sources verbatim.
2. **Verify rubric thresholds (Section 1).** Confirm CLAUDE.md max-lines and SKILL.md description-cap against the latest `code.claude.com/docs/en/memory` and `/skills` pages. Update if changed.
3. **Verify checklist commands (Section 3).** New keys (e.g., `effortLevel` for Opus 4.7, may differ for Opus 4.8) need new grep targets. Removed API names get added to the removed-API scan.
4. **Re-run the checklist** to capture a new baseline. Diff against the previous baseline to surface drift introduced since the last review. Triage with the rubric. Plan the targeted edits in a separate execution document.

The framework is the methodology; the execution document is the runbook for one specific application of it. Keep them separate so the methodology stays reusable.
