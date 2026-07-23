# Skill Directory Taxonomy Restructure — Design Spec

**Date:** 2026-04-27
**Plugin:** panther-ivy-plugin
**Layer:** 1 (Mental model) of the broader simplification roadmap (Layer 1 = mental model, Layer 2 = behaviour, Layer 3 = surface)
**Driver:** Cognitive-load reduction
**Status:** Design approved; pending implementation plan via `superpowers:writing-plans`
**Companion specs:**
- `panther-ivy-plugin/docs/skill-audit-2026-04-27.md` — audit findings that surfaced the verify auto-discovery bug + structural drift
- `panther-ivy-plugin/docs/superpowers-audit-2026-04-27.md` — in-flight F1–F10 description-style refactor (must complete Batches 1.A–1.D before this restructure ships)

---

## 1. Overview

### Goal

Reduce cognitive load on the question "what is in panther-ivy-plugin?" by giving its 21 skills physical category boundaries that match how a maintainer thinks about them. Today the `skills/` tree is flat (`skills/<name>/`), four skills are unindexed in README, and `verify` is silently broken because it sits at `skills/workflow/verify/` with `name: verify` — a leaf-name/path mismatch the harness rejects.

### Non-goals

- **Layer 2 (behaviour):** routing, hooks, agents, gate dispatch — separate sub-project.
- **Layer 3 (surface):** output styles, tool renderers, overlays — separate sub-project.
- **Skill body content:** description style, HARD-GATE markup, Type markers — handled by the in-flight F1–F10 refactor.

### Out of scope explicitly

- The `knowledge-capture` → `knowledge-audit` Skill-tool sub-load split (K3 decision in audit) is a separate Layer 1 sub-project. This restructure works whether K3 lands before or after.
- Restructure of `agents/`, `hooks/`, `commands/`, `output-styles/`, `.claude/rules/`. Those directories stay flat; only `skills/` gets the taxonomy treatment.

---

## 2. Architecture

### New directory tree

```
skills/
├── workflow/
│   ├── navigate/          name: workflow/navigate
│   ├── build/             name: workflow/build
│   ├── verify/            name: workflow/verify    ← fixes auto-discovery bug
│   ├── review/            name: workflow/review
│   └── triage/            name: workflow/triage
├── knowledge/
│   ├── apt-attack-patterns/         name: knowledge/apt-attack-patterns
│   ├── counterexample-guide/        name: knowledge/counterexample-guide
│   ├── ivy-debugging-methodology/   name: knowledge/ivy-debugging-methodology
│   ├── ivy-error-patterns/          name: knowledge/ivy-error-patterns
│   ├── ivy-toolkit/                 name: knowledge/ivy-toolkit
│   ├── ivy-writing-guide/           name: knowledge/ivy-writing-guide
│   ├── methodology-reference/       name: knowledge/methodology-reference
│   ├── propagation-patterns/        name: knowledge/propagation-patterns
│   ├── specification-patterns/      name: knowledge/specification-patterns
│   └── claim-discussion/            name: knowledge/claim-discussion
├── cross-cutting/
│   ├── completion-gate/             name: cross-cutting/completion-gate
│   ├── reflection-patterns/         name: cross-cutting/reflection-patterns
│   ├── parallel-dispatch/           name: cross-cutting/parallel-dispatch
│   └── knowledge-capture/           name: cross-cutting/knowledge-capture
└── meta/
    ├── using-panther-ivy-plugin/    name: meta/using-panther-ivy-plugin
    └── plugin-self-mod/             name: meta/plugin-self-mod
```

Counts: 5 + 10 + 4 + 2 = 21 ✓.

### Naming convention

Nested skills use a forward slash in their `name:` field, mirroring the relative path under `skills/`. Empirically validated by Zoom plugin (~25 nested skills in production using e.g. `name: contact-center/android` at `skills/contact-center/android/SKILL.md`). Top-level skills retain the canonical lowercase + numbers + hyphens-only form.

### `skill-conventions.md` amendment

The worktree-level rule at `.claude/rules/skill-conventions.md` currently says:

> `name`: Required. 1-64 chars. Lowercase, numbers, hyphens. No leading/trailing/consecutive hyphens. Must match directory name.

Amend to:

> `name`: Required. 1-64 chars. Lowercase, numbers, hyphens. No leading/trailing/consecutive hyphens. Must match directory name. **A single forward slash is permitted iff the SKILL.md sits at a 2-level nested path under `skills/`** (e.g., `skills/<group>/<leaf>/SKILL.md` registers as `name: <group>/<leaf>`). Top-level skills retain the no-slash rule.

### Verify auto-discovery fix as side-effect

The current `skills/workflow/verify/SKILL.md` has `name: verify` — a leaf-name/path mismatch that causes the harness to silently drop the skill from available-skills. After this restructure, the file's `name:` becomes `workflow/verify`, matching the registered name format Zoom uses. The verify skill becomes discoverable as a side-effect of Phase 1 — no separate fix commit needed.

---

## 3. Components: cross-reference inventory

Seven source types carry skill references and need updating per phase:

| # | Source | What references look like | Update pattern |
|---|---|---|---|
| 1 | `skills/**/SKILL.md` bodies | `Skill(skill="panther-ivy-plugin:<old>")` | Replace `<old>` with `<category>/<old>`. Plus rename the skill's own `name:` frontmatter |
| 2 | `.claude/rules/*.md` | Skill invocations within rule prose, e.g. `invoke Skill(panther-ivy-plugin:methodology-reference)` | Same replacement |
| 3 | `routing-rules.json` | Keys nested under `"workflows"` object, not top-level. Structure is `{"workflows": {"verify": {...}, "build": {...}, ...}}`. Verified 2026-04-27 — empirical inspection of the file | Keys inside `workflows` rename: `workflows.verify` → `workflows."workflow/verify"`, etc. The top-level structure (`_comment`, `workflows`, `learning_injection`) is unchanged |
| 4 | `commands/*.md` | Slash commands that invoke skills | Same as rules |
| 5 | `hooks/scripts/*.{sh,py,bash}` | Skill names as string literals (e.g., `inject-using-plugin.sh` referencing `using-panther-ivy-plugin`) | Same replacement; pay close attention to the SessionStart-injection script |
| 6 | `agents/*.md` | Agent bodies that pre-load skills | Same replacement |
| 7 | `README.md` + `docs/**/*.md` | Path links + Skill names in prose | Same replacement |

**Update mechanism:** manual `grep -rn "panther-ivy-plugin:<old-name>"` across the seven source types per phase, edit each match, review diff, commit. No tool — at 21 skills × ~3-5 references each (~80 total), the manual pace is faster than building a migration tool that would only run once.

---

## 4. Migration plan (5 phases, 5 PRs)

### Phase 0 — Preflight (1 PR)

```bash
cp -r panther-ivy-plugin/skills \
      panther-ivy-plugin/.backup/skills-restructure-2026-04-27/
git add panther-ivy-plugin/.backup/skills-restructure-2026-04-27/
git commit -m "chore(skills): backup pre-restructure tree"
```

The PR contains only the backup commit. Confirms backup is durable in git before any move. Open as the parent of subsequent phase PRs.

### Phase 1 — workflow/ (5 skills, ~30 cross-refs)

**Moves:**
```bash
cd panther-ivy-plugin/skills
git mv navigate workflow/navigate
git mv build    workflow/build
# verify directory is already at workflow/verify; only the name: field changes
git mv review   workflow/review
git mv triage   workflow/triage
```

**Frontmatter renames:** Edit each moved SKILL.md's `name:` field from `<leaf>` to `workflow/<leaf>`.

**Cross-reference updates** (use `grep -rn "panther-ivy-plugin:navigate\|panther-ivy-plugin:build\|panther-ivy-plugin:verify\|panther-ivy-plugin:review\|panther-ivy-plugin:triage"`):
- Update each match to include `workflow/` prefix.
- Update `routing-rules.json` top-level keys.
- Sanity check: `grep -rn "panther-ivy-plugin:navigate\b"` returns zero post-edit.

**Smoke test:**
```bash
# Restart Claude Code session, capture available-skills from system-reminder
# Then assert:
for s in navigate build verify review triage; do
  grep -q "panther-ivy-plugin:workflow/$s" "$skills_capture" || echo "MISS: $s"
  grep -q "panther-ivy-plugin:$s\b"          "$skills_capture" && echo "OLD STILL PRESENT: $s"
done
```

**Commit + PR + merge.** Subsequent phases require this to be merged.

### Phase 2 — knowledge/ (10 skills, ~40 cross-refs)

Same pattern as Phase 1. Skills moved:
- `apt-attack-patterns`, `counterexample-guide`, `ivy-debugging-methodology`, `ivy-error-patterns`, `ivy-toolkit`, `ivy-writing-guide`, `methodology-reference`, `propagation-patterns`, `specification-patterns`, `claim-discussion`

Smoke test scoped to those 10 names with `knowledge/` prefix.

### Phase 3 — cross-cutting/ (4 skills, ~15 cross-refs)

Same pattern. Skills:
- `completion-gate`, `reflection-patterns`, `parallel-dispatch`, `knowledge-capture`

Note: `reflection-patterns` is loaded by every workflow skill (navigate, build, verify, review, triage). Phase 3's cross-reference update therefore touches all 5 workflow SKILL.md bodies — but those bodies were already moved in Phase 1, so the updates land on the new locations.

### Phase 4 — meta/ (2 skills, ~10 cross-refs)

Same pattern. Skills:
- `using-panther-ivy-plugin`, `plugin-self-mod`

**Critical cross-reference:** `hooks/scripts/inject-using-plugin.sh` references `using-panther-ivy-plugin` by name. Phase 4 must update this script and re-test SessionStart injection (R4 mitigation).

### Phase 5 — Cleanup (1 PR)

```bash
rm -rf panther-ivy-plugin/.backup/skills-restructure-2026-04-27/
```

Update `panther-ivy-plugin/skills/README.md` to reflect the new tree (auto-generation from filesystem is a Layer 1 future enhancement; for now this is a hand-edit reflecting the post-restructure state).

**Final integration smoke test:**
- Run `/triage` (preflight mode) and confirm dispatcher resolves.
- Run `/verify` on a sample Ivy spec and confirm the workflow chain functions end-to-end.
- Run `/build` Phase 0 and confirm it dispatches.
- Re-run the suite-level skill audit (`docs/skill-audit-2026-04-27.md`); confirm verify auto-discovery is resolved.

Phases are sequential. Each phase requires the previous phase's PR merged before starting. The harness sees a functionally consistent state after every phase (each skill has exactly one location and one name; see §5), so phases could technically run in any order. We sequence them for **review tractability** (each PR diff is bounded by category) and **rollback isolation** (a failed smoke test reverts only that category's changes, not a multi-category bundle).

---

## 5. Error handling & rollback

### Per-phase failure mode

Smoke test fails: a renamed skill doesn't appear in available-skills, OR an old name still appears, OR a cross-reference still points at an old name.

### Rollback procedure

1. `git revert <phase-commit>` on the failing phase PR.
2. The `.backup/skills-restructure-2026-04-27/` is for catastrophic loss only (e.g., uncommitted `git mv` corrupted the tree).
3. Restart session, re-run smoke test on the reverted state. Expect all old names present and no new ones.
4. Diagnose the failure (Section 7 risks list narrows the cause), fix, re-attempt the phase.

### Cross-phase safety

Phases are independent at the harness level — the harness reads what's on disk, so a half-migrated state (Phase 1 done, Phase 2 not started) is functionally consistent: every skill exists at exactly one location with one name. No shim SKILL.md files at old paths needed.

### Coordination with in-flight F1–F10 refactor

The `superpowers-audit-2026-04-27.md` Batches 1.C and 1.D modify SKILL.md bodies for the same skills this restructure moves. Restructure ships **after** F1–F10 Batches 1.A–1.D land; this avoids merge conflicts and content rewrite churn during phase migration. If F1–F10 needs further batches after Batch 1.D, they wait for restructure Phase 5.

---

## 6. Testing

### Per-phase smoke test (deterministic)

After each phase commit:
1. Open a fresh Claude Code session in the worktree.
2. Capture the `system-reminder` block listing available skills.
3. Run the Bash assertion (Section 4 Phase 1 example) scoped to the phase's skills.
4. Assertion result determines pass/fail; failure triggers rollback.

### Cross-reference scan (per phase)

After each phase's edits:
```bash
# Confirm no old names remain anywhere in the worktree
grep -rn "panther-ivy-plugin:<old-name>\b" \
  panther-ivy-plugin/skills \
  panther-ivy-plugin/.claude/rules \
  panther-ivy-plugin/agents \
  panther-ivy-plugin/commands \
  panther-ivy-plugin/hooks \
  panther-ivy-plugin/routing-rules.json \
  panther-ivy-plugin/README.md \
  panther-ivy-plugin/docs/
# Expect: no matches
```

### Final integration test (Phase 5)

End-to-end exercise of the workflow chain via slash commands; confirms cross-references resolve at runtime, not just at static-grep time.

### Re-run audit (Phase 5)

Re-run the suite-level skill audit. Expected deltas vs `docs/skill-audit-2026-04-27.md`:
- P0 verify auto-discovery: RESOLVED
- S2 workflow asymmetry: RESOLVED (asymmetry is the new norm — every workflow skill nests under workflow/)
- S1 README index lag: PARTIALLY RESOLVED (Phase 5 hand-edit; full automation deferred to Layer 1 future work)

---

## 7. Risks & mitigations

| ID | Risk | Probability | Severity | Mitigation |
|---|---|---|---|---|
| R1 | Harness rejects slash-names for panther specifically (Zoom validates the pattern but plugin behaviour may differ) | Low | High | Phase 1 IS the smoke test for this risk. If Phase 1 smoke fails, revert and switch to hyphen-prefix convention (`workflow-verify` instead of `workflow/verify`) — requires a re-run of the design with the test we deferred originally |
| R2 | Hidden cross-reference (skill name appears in unexpected location like a comment, test, or interpolated string) | Medium | Medium | Phase 5 final scan greps for any remaining old name across the entire worktree, not just plugin source. Failures get a follow-up commit |
| R3 | F1–F10 in-flight refactor conflicts with restructure | Medium | Medium | Sequencing: restructure ships after F1–F10 Batches 1.A–1.D land. Coordinate explicitly via the superpowers-audit-2026-04-27.md tracker |
| R4 | `hooks/scripts/inject-using-plugin.sh` breaks SessionStart injection silently when `using-panther-ivy-plugin` renames | High | High | Phase 4 smoke test specifically verifies SessionStart injection still fires by checking for `[ivy-workspace]` and `[ivy-indexing]` system-reminders in a fresh session |
| R5 | `routing-rules.json` keys may not be skill names but workflow names (semantic difference) | Low | Medium | Verify before Phase 1: read `routing-rules.json`, confirm keys map 1:1 to skill names (not to e.g. workflow groups). If they don't, the update pattern in §3 row 3 needs adjustment |
| R6 | Backup directory inside `panther-ivy-plugin/.backup/` interferes with auto-discovery of skills (could the harness scan `.backup/skills-restructure-*/skills/<name>/SKILL.md`?) | Low | Medium | The `.backup/` prefix should be excluded by harness discovery (other backup dirs already exist there). Verify by checking that current `.backup/superpowers-audit-2026-04-27/skills/...` content does not appear in available-skills |

---

## 8. Open items (post-design, pre-implementation)

- **R5 verification.** Confirm `routing-rules.json` keys are skill names. (Quick check during Phase 0 prep.)
- **R6 verification.** Confirm `.backup/` directories are excluded from auto-discovery. (Same.)
- **F1–F10 sequencing.** Confirm Batches 1.A–1.D landed before kicking off Phase 1.
- **Smoke-test capture mechanism.** The system-reminder content is read-only at session start; we need a stable way to capture it for assertion. Investigate during Phase 0 prep — likely a manual screenshot/grep of the session log.

---

## 9. Future work (out of scope here)

These are Layer 1 follow-ups that this restructure unblocks but does not deliver:

1. **Generated Plugin Map.** Auto-generate `README.md` from filesystem scan + per-skill frontmatter. Removes manual sync.
2. **Frontmatter lint hook.** PreToolUse on Write to SKILL.md: enforce per-category schema (workflow rigid + `You MUST use this when...`, knowledge flexible + `Use when...`, etc.).
3. **K3 split.** Extract `knowledge-capture`'s audit half to `cross-cutting/knowledge-audit/`. Independent of this restructure.
4. **Layer 2 work.** Routing, hooks, agents, gates simplification.
5. **Layer 3 work.** Output styles, renderers, overlays consolidation.

---

## 10. Considerations

**Pro.** The design fixes the verify auto-discovery bug as a free side-effect. Categorisation makes "what is in this plugin?" answerable by `cd skills/` and reading directory names. The slash naming convention is empirically validated by Zoom in production. Phased migration with backup discipline matches the plugin's `feedback_backup_before_delete` rule.

**Con.** The slash convention contradicts the worktree's `skill-conventions.md` rule and requires an amendment. Every existing `Skill(panther-ivy-plugin:<name>)` call site changes — ~80 references. The `inject-using-plugin.sh` rename (R4) is high-severity if missed. The migration touches plugin source extensively; coordination with the in-flight F1–F10 refactor is a real scheduling constraint.

**Alternatives considered.**
1. Big-bang single-PR migration — rejected for review burden and rollback complexity.
2. Scripted migration tool — rejected for YAGNI; ~80 manual edits beat ~2 days of tool build for a one-shot operation.
3. Hyphen naming convention (`workflow-verify`) — rejected because it's empirically untested for nested paths and would require a smoke-test detour before designing.
4. Flat-with-prefix (`skills/workflow-navigate/`, `skills/knowledge-ivy-toolkit/`) — rejected because it doesn't deliver the "cd skills/<category>/ to see all skills in that category" mental model that motivated the restructure.

---

*Generated 2026-04-27 via superpowers:brainstorming. Next step: invoke `superpowers:writing-plans` to produce the implementation plan.*
