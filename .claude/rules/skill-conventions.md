---
paths:
  - "**/.claude/skills/**/SKILL.md"
  - "**/skills/**/SKILL.md"
  - "**/.claude/skills/**/references/**/*.md"
  - "**/.claude/agents/**/*.md"
  - "**/.claude/commands/**/*.md"
---

## Skill Conventions

When writing or editing Claude Code skills, follow these rules. Source: [Official docs](https://code.claude.com/docs/en/skills), [Agent Skills spec](https://agentskills.io/specification).

### Frontmatter

| Field | Constraints |
|---|---|
| `name` | Required. 1-64 chars. Lowercase, numbers, hyphens. No leading/trailing/consecutive hyphens. Must match directory name. |
| `description` | Required. Front-load key use case in first 250 chars (truncation point). Format: what it does + "Use when..." triggers. Third person. No workflow summaries. |
| `allowed-tools` | Hyphenated key name. Use restricted patterns (`Bash(git *)`) not bare `Bash`. |
| `user-invocable` | Set to `false` for internal knowledge skills. Do not use "Do not invoke directly" in descriptions. |

### Description Format

```yaml
# Good: what it does + when to use it, under 250 chars
description: Trace interpretation and fix strategies for verification failures. Use when counterexample appears in ivy_verify output.

# Bad: workflow summary (Claude follows description instead of reading skill body)
description: Analyzes counterexamples by parsing traces, classifying failures, and suggesting fixes.

# Bad: wastes description space on routing metadata
description: Internal knowledge skill — do not invoke directly; loaded by build workflow.
```

### Body Rules

- SKILL.md under 500 lines. Aim for under 300 for frequently-loaded skills.
- Move heavy reference material to `references/` subdirectory.
- One level of file references from SKILL.md (no nested chains).
- No narrative storytelling or worked examples in SKILL.md body (move to `references/`).
- No duplicate sections within a skill.

### CSO Checklist

Before finalizing a skill description: contains concrete trigger phrases, exact error strings for error-handling skills, third person, no workflow summary, under 250 chars, synonyms covered.
