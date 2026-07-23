# Skill Directory Taxonomy Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move panther-ivy-plugin's 21 skills from a flat `skills/<name>/` layout into a 2-level taxonomy `skills/<category>/<name>/` (workflow / knowledge / cross-cutting / meta), update ~80–95 cross-references, and fix the verify auto-discovery bug as a side-effect.

**Architecture:** Sequential phased migration, one PR per phase. Phase 0 backs up the tree and verifies prerequisites. Phases 1–4 migrate one category each. Phase 5 cleans up and runs the integration test. Naming follows Zoom-validated `name: <category>/<leaf>` convention requiring a single-character amendment to `skill-conventions.md`.

**Tech Stack:** git, `grep -rn`, `sed`, manual editing of YAML frontmatter and Markdown bodies. No tooling built; this is a one-shot migration.

**Conventions used in this plan:**
- `$PLUGIN` shell variable abbreviates `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin` from the worktree root. Set it once at the top of each task with `PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin`.
- All shell commands run from the worktree root (`/Users/elniak/Documents/Documents/Work/Project/Protocol-Testing-Security/PANTHER/master/.claude/worktrees/lsp-to-claude`).
- Spec reference: `docs/superpowers/specs/2026-04-27-skill-directory-taxonomy-restructure-design.md` — read this before starting any task.
- Companion audit: `panther-ivy-plugin/docs/skill-audit-2026-04-27.md` — context for why this work exists.
- Companion in-flight refactor: `panther-ivy-plugin/docs/superpowers-audit-2026-04-27.md` — Batches 1.A–1.D MUST be merged before Phase 1 (see Task 0.1).

---

## File structure

This migration touches every directory under `$PLUGIN`. Concrete file inventory:

**Files moved (21 directories):**
- `$PLUGIN/skills/{navigate,build,review,triage}/` → `$PLUGIN/skills/workflow/{navigate,build,review,triage}/` (4 moves)
- `$PLUGIN/skills/workflow/verify/` stays in place (already nested) but `name:` field changes
- `$PLUGIN/skills/{apt-attack-patterns,counterexample-guide,ivy-debugging-methodology,ivy-error-patterns,ivy-toolkit,ivy-writing-guide,methodology-reference,propagation-patterns,specification-patterns,claim-discussion}/` → `$PLUGIN/skills/knowledge/<name>/` (10 moves)
- `$PLUGIN/skills/{completion-gate,reflection-patterns,parallel-dispatch,knowledge-capture}/` → `$PLUGIN/skills/cross-cutting/<name>/` (4 moves)
- `$PLUGIN/skills/{using-panther-ivy-plugin,plugin-self-mod}/` → `$PLUGIN/skills/meta/<name>/` (2 moves)

**Files modified (per phase):**
- 21 × `SKILL.md` files (`name:` field rename)
- `$PLUGIN/routing-rules.json` (top-level keys rename)
- `$PLUGIN/.claude/rules/*.md` (Skill invocations)
- `$PLUGIN/agents/*.md` (Skill loads)
- `$PLUGIN/commands/*.md` (Skill invocations)
- `$PLUGIN/hooks/scripts/*.{sh,py}` (skill name string literals — particularly `inject-using-plugin.sh`)
- `$PLUGIN/skills/README.md` (Phase 5)
- `$PLUGIN/docs/*.md` (cross-doc references)
- Worktree-level: `.claude/rules/skill-conventions.md` (one-line amendment in Phase 0)

**File created:**
- `$PLUGIN/.backup/skills-restructure-2026-04-27/` (Phase 0; deleted in Phase 5)

---

## Phase 0 — Preflight backup

### Task 0.1: Verify all prerequisites

**Files:** None modified. Read-only verification.

**Per-task options for verification mode:**

- **Option A — One-shot script (Recommended):** Run all four verification checks in a single bash block; abort on first failure. Fastest if everything is green; less helpful if you need to diagnose one specific failure.
- **Option B — Step-by-step:** Run each verification as its own step; record outcome before continuing. Slower but every check has a visible verdict before the next runs.

Option A chosen for the plan; switch to B only if a check fails and you need to isolate.

- [ ] **Step 1: Verify F1–F10 Batches 1.A–1.D have merged**

```bash
# F1-F10 lands description-style + Type marker + HARD-GATE on workflow skills first.
# Batch 1.A-1.B: build/verify/review/triage. Batch 1.C: navigate, knowledge-capture.
# Batch 1.D: 11 pattern skills. Confirm by spot-check on navigate (Batch 1.C target).
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
grep -q "^\*\*Type:\*\*" "$PLUGIN/skills/navigate/SKILL.md" \
  && echo "F1-F10 Batch 1.C: PRESENT" \
  || { echo "F1-F10 Batch 1.C: MISSING — abort, wait for refactor"; exit 1; }
```

Expected: `F1-F10 Batch 1.C: PRESENT`. If MISSING, stop the entire migration; coordinate with the refactor owner before proceeding.

- [ ] **Step 2: Verify R5 — routing-rules.json `workflows.*` keys are skill names**

The file has skill names nested one level under a `"workflows"` object, not at the top level. Verified empirically on 2026-04-27.

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
python3 -c "
import json
d = json.load(open('$PLUGIN/routing-rules.json'))
top = list(d.keys())
print('Top-level keys:', top)
workflows = d.get('workflows', {})
print('workflows.* keys:', list(workflows.keys()))
expected = {'navigate','build','verify','review','triage','plugin-self-mod'}
missing = expected - set(workflows.keys())
extra = set(workflows.keys()) - expected
print('missing skill names under workflows:', missing)
print('unexpected workflows keys:', extra)
"
```

Expected: top-level keys are `['_comment', 'workflows', 'learning_injection']`; `workflows.*` keys include all 6 expected skill names; `missing` is empty. If `missing` is non-empty, abort and revisit Section 3 row 3 of the spec.

- [ ] **Step 3: Verify R6 — `.backup/` is excluded from skill auto-discovery**

```bash
# Existing .backup/ directories already contain SKILL.md files.
# If the harness auto-discovers them, they would appear in the available-skills list.
# Check by parsing the system-reminder available-skills block from the most recent session log.
ls panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/.claude/.backup/ 2>/dev/null \
  | head -3
echo "---"
echo "Manual check: open a fresh Claude Code session, inspect the available-skills"
echo "system-reminder, and confirm no entries reference content under .claude/.backup/."
echo "If backups are auto-discovered, abort and use a different backup location."
```

Expected: backup directories listed; manual confirmation that they don't appear in available-skills.

- [ ] **Step 4: Verify the worktree is clean and on the right branch**

```bash
git status --short
git branch --show-current
```

Expected: working tree clean (no uncommitted changes); current branch is `production` or a feature branch off `production`. If dirty, stash or commit unrelated changes first.

- [ ] **Step 5: Read the spec one more time before proceeding**

Read `docs/superpowers/specs/2026-04-27-skill-directory-taxonomy-restructure-design.md` end-to-end. Section 4 (migration plan) and Section 7 (risks) are the load-bearing pieces for execution.

---

### Task 0.2: Amend `skill-conventions.md` to permit nested-skill slash naming

**Files:**
- Modify: `.claude/rules/skill-conventions.md`

- [ ] **Step 1: Locate the `name` rule line**

```bash
grep -n "^| \`name\` " .claude/rules/skill-conventions.md
```

Expected: one match around line 11.

- [ ] **Step 2: Edit the rule to permit nested slash naming**

In `.claude/rules/skill-conventions.md`, change the `name:` row of the Frontmatter table from:

```
| `name` | Required. 1-64 chars. Lowercase, numbers, hyphens. No leading/trailing/consecutive hyphens. Must match directory name. |
```

To:

```
| `name` | Required. 1-64 chars. Lowercase, numbers, hyphens. No leading/trailing/consecutive hyphens. Must match directory name. A single forward slash `/` is permitted iff the SKILL.md sits at a 2-level nested path under `skills/` (e.g. `skills/<group>/<leaf>/SKILL.md` registers as `name: <group>/<leaf>`). Top-level skills retain the no-slash rule. |
```

- [ ] **Step 3: Commit the rule amendment as the first preflight commit**

```bash
git add .claude/rules/skill-conventions.md
git commit -m "docs(rules): permit single slash in name for nested SKILL.md

Empirically validated by Zoom plugin (~25 nested skills using
name: <group>/<leaf>). Required to support the panther-ivy-plugin
skill directory taxonomy restructure (see
docs/superpowers/specs/2026-04-27-skill-directory-taxonomy-
restructure-design.md)."
```

---

### Task 0.3: Create the backup directory

**Files:**
- Create: `panther-ivy-plugin/.backup/skills-restructure-2026-04-27/`

**Per-task options for backup mechanism:**

- **Option A — `cp -r` snapshot (Recommended):** Filesystem-level copy. Survives `git revert`. Matches the plugin's existing `.backup/` convention (other audit backups already use this pattern). Easy to inspect.
- **Option B — Git stash with named ref:** `git stash push -m "skills-restructure-2026-04-27"`. Lighter weight, lives in git. Risk: stashes are not durable across `git stash drop`; one accidental drop loses the safety net.
- **Option C — Tar archive:** `tar czf .backup/skills-2026-04-27.tar.gz panther-ivy-plugin/skills/`. Smallest size; opaque to inspect; harder to spot-check during phases.

Option A chosen for the plan to match existing convention.

- [ ] **Step 1: Create the backup**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
mkdir -p "$PLUGIN/.backup"
cp -r "$PLUGIN/skills" "$PLUGIN/.backup/skills-restructure-2026-04-27"
```

- [ ] **Step 2: Verify backup is complete**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
diff -rq "$PLUGIN/skills" "$PLUGIN/.backup/skills-restructure-2026-04-27" | head
```

Expected: no output (directories are identical).

- [ ] **Step 3: Commit the backup**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
git add "$PLUGIN/.backup/skills-restructure-2026-04-27/"
git commit -m "chore(skills): backup pre-restructure tree for 2026-04-27 migration

Snapshot of $PLUGIN/skills/ before the
directory taxonomy restructure begins. Will be deleted in
Phase 5 after the final integration smoke test passes.

See docs/superpowers/specs/2026-04-27-skill-directory-taxonomy-
restructure-design.md for the migration plan."
```

- [ ] **Step 4: Capture pre-state available-skills baseline**

```bash
# Open a fresh Claude Code session in the worktree.
# Save the system-reminder available-skills block to a baseline file:
mkdir -p docs/superpowers/plans/captures
# Paste the available-skills block from the system-reminder into:
#   docs/superpowers/plans/captures/2026-04-27-pre-restructure-available-skills.txt
# (This is a manual paste; the system-reminder is read-only at session start.)
```

Expected: baseline file contains all 21 current skill entries with their pre-restructure names. You'll diff against this after each phase.

- [ ] **Step 5: Open Phase 0 PR**

Recommended branch name: `refactor/skills-taxonomy-2026-04-27`. Create the branch and push:

```bash
# If you have not yet created a feature branch off production:
git checkout -b refactor/skills-taxonomy-2026-04-27
git push -u origin refactor/skills-taxonomy-2026-04-27
gh pr create --title "chore(skills): Phase 0 preflight — backup and conventions amendment" \
  --body "$(cat <<'EOF'
## Summary
- Amend skill-conventions.md to permit nested slash naming
- Backup skills/ tree before Phase 1
- Capture pre-state available-skills baseline

## Test plan
- [x] F1-F10 Batches 1.A-1.D verified merged
- [x] R5 verified (routing-rules.json keys are skill names)
- [x] R6 verified (.backup/ excluded from auto-discovery)
- [x] Backup directory matches source tree (diff -rq returns no output)

## Next phase
Phase 1: workflow/ migration (5 skills). See docs/superpowers/plans/2026-04-27-skill-directory-taxonomy-restructure.md
EOF
)"
```

Wait for PR review and merge before starting Phase 1.

---

## Phase 1 — workflow/ migration (5 skills, ~30 cross-references)

### Task 1.1: Move workflow directories and rename frontmatter

**Files:**
- Move: `$PLUGIN/skills/{navigate,build,review,triage}/` → `$PLUGIN/skills/workflow/<name>/`
- Modify: 5 × `SKILL.md` (`name:` field): navigate, build, verify, review, triage

- [ ] **Step 1: Move 4 directories with `git mv`**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
cd "$PLUGIN"
# verify is already at workflow/verify; only its name field changes
git mv skills/navigate skills/workflow/navigate
git mv skills/build    skills/workflow/build
git mv skills/review   skills/workflow/review
git mv skills/triage   skills/workflow/triage
cd -
```

- [ ] **Step 2: Verify the moves**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
ls "$PLUGIN/skills/workflow/"
```

Expected: `build  navigate  review  triage  verify` (5 entries, alphabetical).

- [ ] **Step 3: Rename `name:` field in each workflow SKILL.md**

For each of the 5 workflow skills, edit the SKILL.md frontmatter `name:` field:

`skills/workflow/navigate/SKILL.md` line ~2:
```yaml
# before
name: navigate
# after
name: workflow/navigate
```

`skills/workflow/build/SKILL.md` line ~2:
```yaml
name: workflow/build
```

`skills/workflow/verify/SKILL.md` line ~2:
```yaml
name: workflow/verify
```

`skills/workflow/review/SKILL.md` line ~2:
```yaml
name: workflow/review
```

`skills/workflow/triage/SKILL.md` line ~2:
```yaml
name: workflow/triage
```

- [ ] **Step 4: Verify all 5 frontmatter renames**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
for s in navigate build verify review triage; do
  grep "^name: " "$PLUGIN/skills/workflow/$s/SKILL.md" | head -1
done
```

Expected output:
```
name: workflow/navigate
name: workflow/build
name: workflow/verify
name: workflow/review
name: workflow/triage
```

---

### Task 1.2: Update routing-rules.json keys

**Files:**
- Modify: `$PLUGIN/routing-rules.json`

- [ ] **Step 1: Inspect current `workflows.*` keys**

The skill names are nested under a `"workflows"` object, not at the top level (verified 2026-04-27).

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
python3 -c "import json; d=json.load(open('$PLUGIN/routing-rules.json')); print('top:', list(d.keys())); print('workflows.*:', list(d.get('workflows', {}).keys()))"
```

Expected: top-level `['_comment', 'workflows', 'learning_injection']`; `workflows.*` keys include `navigate`, `build`, `verify`, `review`, `triage` (plus `plugin-self-mod` not in this phase).

- [ ] **Step 2: Edit routing-rules.json — rename 5 keys inside `workflows`**

In `$PLUGIN/routing-rules.json`, rename the keys inside the `workflows` object. Top-level structure (`_comment`, `workflows`, `learning_injection`) is unchanged; only the keys inside `workflows` change.

```json
// before
{
  "_comment": "...",
  "workflows": {
    "navigate": { ... },
    "build":    { ... },
    "verify":   { ... },
    "review":   { ... },
    "triage":   { ... },
    "plugin-self-mod": { ... }
  },
  "learning_injection": { ... }
}
// after
{
  "_comment": "...",
  "workflows": {
    "workflow/navigate": { ... },
    "workflow/build":    { ... },
    "workflow/verify":   { ... },
    "workflow/review":   { ... },
    "workflow/triage":   { ... },
    "plugin-self-mod":   { ... }
  },
  "learning_injection": { ... }
}
```

The values (intentPatterns, fileTriggers, priority, etc.) are unchanged. `plugin-self-mod` is not migrated this phase (see Phase 4).

- [ ] **Step 3: Validate JSON**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
python3 -m json.tool "$PLUGIN/routing-rules.json" > /dev/null && echo "JSON valid" || echo "JSON BROKEN"
```

Expected: `JSON valid`.

- [ ] **Step 4: Verify renamed keys are present inside `workflows`**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
python3 -c "
import json
workflows = json.load(open('$PLUGIN/routing-rules.json')).get('workflows', {})
expected = {'workflow/navigate','workflow/build','workflow/verify','workflow/review','workflow/triage'}
present = expected & set(workflows.keys())
old_present = {'navigate','build','verify','review','triage'} & set(workflows.keys())
print('new keys present:', present)
print('old keys still present (should be empty):', old_present)
print('missing:', expected - present)
"
```

Expected: `present` is the full set of 5 new names; `old_present` is empty; `missing` is empty.

---

### Task 1.3: Update cross-references across all source types (workflow names)

**Files:**
- Modify: any file under `$PLUGIN` referencing `panther-ivy-plugin:{navigate,build,verify,review,triage}` by old name.

**Per-task options for cross-reference update strategy:**

- **Option A — Per-source-type pass with manual review (Recommended):** `grep -rn` per source type, edit each match individually. Slower (~20-30 minutes for Phase 1) but every edit is reviewed in context; lowest miss rate.
- **Option B — Single ripgrep + sed pass:** `rg -l "panther-ivy-plugin:(navigate|build|verify|review|triage)\b" | xargs sed -i 's/panther-ivy-plugin:\(navigate\|build\|verify\|review\|triage\)\b/panther-ivy-plugin:workflow\/\1/g'`. Fastest (~2 minutes) but no per-match review; higher chance of regex catching a false match (e.g., a string in a code block that mentions the old name as an example).
- **Option C — Per-skill pass:** Loop one old name at a time. Predictable but slowest.

Option A chosen for Phase 1 (highest review burden phase given workflow skills are most heavily cross-referenced). Option B can be used in later phases once Phase 1 confidence is high.

- [ ] **Step 1: Update cross-references in `$PLUGIN/skills/`**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
grep -rn "panther-ivy-plugin:\(navigate\|build\|verify\|review\|triage\)\b" "$PLUGIN/skills/"
```

For each match, edit the file replacing `panther-ivy-plugin:<old>` with `panther-ivy-plugin:workflow/<old>`. Common forms:
- `Skill(skill="panther-ivy-plugin:verify")` → `Skill(skill="panther-ivy-plugin:workflow/verify")`
- `Skill(panther-ivy-plugin:verify)` → `Skill(panther-ivy-plugin:workflow/verify)`
- `pending_dispatch(target_workflow="verify", …)` → `pending_dispatch(target_workflow="workflow/verify", …)` (note: target_workflow values may also need this update; check the journal-events schema)

- [ ] **Step 2: Update cross-references in `$PLUGIN/.claude/rules/`**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
grep -rn "panther-ivy-plugin:\(navigate\|build\|verify\|review\|triage\)\b" "$PLUGIN/.claude/rules/"
```

Apply the same replacement pattern.

- [ ] **Step 3: Update cross-references in `$PLUGIN/agents/`**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
grep -rn "panther-ivy-plugin:\(navigate\|build\|verify\|review\|triage\)\b" "$PLUGIN/agents/"
```

Apply the same replacement.

- [ ] **Step 4: Update cross-references in `$PLUGIN/commands/`**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
grep -rn "panther-ivy-plugin:\(navigate\|build\|verify\|review\|triage\)\b" "$PLUGIN/commands/"
```

Apply the same replacement.

- [ ] **Step 5: Update cross-references in `$PLUGIN/hooks/scripts/`**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
grep -rn "panther-ivy-plugin:\(navigate\|build\|verify\|review\|triage\)\b\|['\"]\\(navigate\\|build\\|verify\\|review\\|triage\\)['\"]" \
  "$PLUGIN/hooks/scripts/"
```

The second alternation catches bare-string skill name references in shell/python (e.g., `WORKFLOW="verify"`). Apply the replacement, careful to also update bare strings to `"workflow/verify"` where they refer to the skill name.

- [ ] **Step 6: Update cross-references in `$PLUGIN/README.md`, `$PLUGIN/skills/README.md`, and `$PLUGIN/docs/`**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
grep -rn "panther-ivy-plugin:\(navigate\|build\|verify\|review\|triage\)\b\|skills/\(navigate\|build\|review\|triage\)/" \
  "$PLUGIN/README.md" "$PLUGIN/skills/README.md" "$PLUGIN/docs/"
```

The second alternation catches path-form references (e.g., `skills/navigate/SKILL.md`). Apply replacements:
- `panther-ivy-plugin:navigate` → `panther-ivy-plugin:workflow/navigate`
- `skills/navigate/` → `skills/workflow/navigate/`

- [ ] **Step 7: Final scan — verify no old workflow names remain**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
grep -rn "panther-ivy-plugin:\(navigate\|build\|verify\|review\|triage\)\b" \
  "$PLUGIN" 2>/dev/null \
  | grep -v "\.backup/" \
  | grep -v "\.git/" \
  | grep -v "docs/skill-audit-2026-04-27.md" \
  | grep -v "docs/superpowers-audit-2026-04-27.md"
```

Expected: no matches. The greps for `.backup/` and `docs/skill-audit-*` are excluded because:
- `.backup/` is the pre-restructure snapshot (intentionally not migrated)
- The audit documents reference old names historically (intentionally preserved)

If any other matches appear, edit them and re-run Step 7 until clean.

---

### Task 1.4: Phase 1 smoke test, commit, and PR

**Files:** None modified. Verification only, then commit/PR.

- [ ] **Step 1: Capture post-Phase-1 available-skills**

```bash
# Open a fresh Claude Code session in the worktree.
# Paste the system-reminder available-skills block to:
#   docs/superpowers/plans/captures/2026-04-27-after-phase-1-available-skills.txt
```

- [ ] **Step 2: Run smoke test assertions**

```bash
CAP=docs/superpowers/plans/captures/2026-04-27-after-phase-1-available-skills.txt
echo "=== New names should appear ==="
for s in navigate build verify review triage; do
  if grep -q "panther-ivy-plugin:workflow/$s\b" "$CAP"; then
    echo "OK:   workflow/$s present"
  else
    echo "MISS: workflow/$s NOT FOUND"
  fi
done
echo
echo "=== Old names should NOT appear ==="
for s in navigate build verify review triage; do
  if grep -q "panther-ivy-plugin:$s\b" "$CAP"; then
    echo "OLD STILL PRESENT: $s"
  else
    echo "OK:   $s gone"
  fi
done
```

Expected: 5 × `OK: workflow/<name> present`; 5 × `OK: <name> gone`. Any `MISS` or `OLD STILL PRESENT` line is a smoke-test failure — see Step 5.

- [ ] **Step 3: Run integration probe — invoke verify once**

```bash
# In the same Claude Code session, type:
#   /verify --help     OR   verify a sample Ivy spec
# Confirm Claude dispatches into the workflow/verify skill (no "skill not found" error).
# This catches Skill() call sites that may not have been updated.
```

Expected: `panther-ivy-plugin:workflow/verify` activates without error.

- [ ] **Step 4: Commit Phase 1**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
git add "$PLUGIN/skills/workflow/" \
        "$PLUGIN/routing-rules.json" \
        "$PLUGIN/.claude/rules/" \
        "$PLUGIN/agents/" \
        "$PLUGIN/commands/" \
        "$PLUGIN/hooks/scripts/" \
        "$PLUGIN/README.md" \
        "$PLUGIN/skills/README.md" \
        "$PLUGIN/docs/"
# Use git status to review what's staged before committing
git status
git commit -m "refactor(skills): Phase 1 — migrate workflow/ category to nested layout

Move navigate, build, review, triage from skills/<name>/ to
skills/workflow/<name>/. verify stays in workflow/ (already
nested) but its name field changes from 'verify' to
'workflow/verify' (fixes the auto-discovery bug per
docs/superpowers/specs/2026-04-27-skill-directory-taxonomy-
restructure-design.md §2).

Cross-references updated across SKILL.md bodies, .claude/rules/,
agents/, commands/, hooks/scripts/, routing-rules.json,
README.md, and docs/.

Smoke test: 5/5 new workflow/<name> entries appear in
available-skills; 0/5 old names remain.
"
```

- [ ] **Step 5: On smoke-test failure — rollback**

If Step 2 or Step 3 failed:

```bash
# Revert the phase commit (assumes nothing was pushed yet)
git reset --hard HEAD~1     # only if Step 4 already committed
# OR if not yet committed:
git restore --staged .
git restore .
```

Then diagnose: which name is missing or which one is still present? Re-read the spec's Section 7 risks. If R1 fires (harness rejects slashes for panther specifically), abort the entire restructure and switch to hyphen convention per the spec's deferred test path.

- [ ] **Step 6: Open Phase 1 PR**

```bash
git push
gh pr create --title "refactor(skills): Phase 1 — workflow/ migration" \
  --body "$(cat <<'EOF'
## Summary
- Migrate 5 workflow skills (navigate, build, verify, review, triage) to skills/workflow/<name>/ with name: workflow/<name>
- Fix verify auto-discovery bug as side-effect (path/name now match)
- Update routing-rules.json keys + ~30 cross-references

## Test plan
- [x] All 5 new workflow/<name> entries appear in available-skills
- [x] No old workflow skill names remain in available-skills
- [x] /verify command dispatches into workflow/verify successfully
- [x] grep for old names across plugin tree returns 0 matches (excluding .backup/ and audit docs)

## Next phase
Phase 2: knowledge/ migration (10 skills). Will not start until this PR merges.
EOF
)"
```

Wait for PR review and merge before Phase 2.

---

## Phase 2 — knowledge/ migration (10 skills, ~40 cross-references)

### Task 2.1: Move knowledge directories and rename frontmatter

**Files:**
- Move: 10 directories from `$PLUGIN/skills/<name>/` to `$PLUGIN/skills/knowledge/<name>/`
- Modify: 10 × `SKILL.md` (`name:` field)

The 10 skills: `apt-attack-patterns`, `counterexample-guide`, `ivy-debugging-methodology`, `ivy-error-patterns`, `ivy-toolkit`, `ivy-writing-guide`, `methodology-reference`, `propagation-patterns`, `specification-patterns`, `claim-discussion`.

- [ ] **Step 1: Move 10 directories**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
cd "$PLUGIN"
mkdir -p skills/knowledge
for s in apt-attack-patterns counterexample-guide ivy-debugging-methodology \
         ivy-error-patterns ivy-toolkit ivy-writing-guide methodology-reference \
         propagation-patterns specification-patterns claim-discussion; do
  git mv "skills/$s" "skills/knowledge/$s"
done
cd -
```

- [ ] **Step 2: Verify the moves**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
ls "$PLUGIN/skills/knowledge/" | wc -l
```

Expected: `10`.

- [ ] **Step 3: Rename `name:` field in each knowledge SKILL.md**

For each of the 10 knowledge skills, edit the `name:` line. Pattern: `name: <leaf>` → `name: knowledge/<leaf>`.

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
for s in apt-attack-patterns counterexample-guide ivy-debugging-methodology \
         ivy-error-patterns ivy-toolkit ivy-writing-guide methodology-reference \
         propagation-patterns specification-patterns claim-discussion; do
  # Show the current line first for sanity
  grep -n "^name: " "$PLUGIN/skills/knowledge/$s/SKILL.md" | head -1
done
```

For each file, edit `name: <leaf>` → `name: knowledge/<leaf>`.

- [ ] **Step 4: Verify all 10 frontmatter renames**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
for s in apt-attack-patterns counterexample-guide ivy-debugging-methodology \
         ivy-error-patterns ivy-toolkit ivy-writing-guide methodology-reference \
         propagation-patterns specification-patterns claim-discussion; do
  grep "^name: " "$PLUGIN/skills/knowledge/$s/SKILL.md" | head -1
done
```

Expected: 10 lines, each `name: knowledge/<leaf>`.

---

### Task 2.2: Update cross-references for knowledge skills

**Files:** any file under `$PLUGIN` referencing the 10 knowledge skill names.

**Per-task options for cross-reference update strategy:**

- **Option A — Per-source-type pass with manual review (Recommended for Phase 2):** Run `grep -rn` per source type, edit each match individually. ~30-40 minutes for Phase 2's volume. Lowest miss rate; every edit reviewed in context.
- **Option B — Single ripgrep + sed pass:** `rg -l "panther-ivy-plugin:(<10 names alternation>)\b" | xargs sed -i 's/panther-ivy-plugin:\(<names>\)\b/panther-ivy-plugin:knowledge\/\1/g'`. Fastest (~3 minutes) but no per-match review; higher false-match risk on regex.
- **Option C — Per-skill pass:** Loop one old name at a time, ten times. Predictable but slowest.

Recommended: Option A in Phase 2 still (volume of 10 skills warrants careful review); switch to Option B in Phase 3 if Phase 2 surfaces no surprises.

- [ ] **Step 1: List all old-name references**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
NAMES="apt-attack-patterns\|counterexample-guide\|ivy-debugging-methodology\|ivy-error-patterns\|ivy-toolkit\|ivy-writing-guide\|methodology-reference\|propagation-patterns\|specification-patterns\|claim-discussion"
grep -rn "panther-ivy-plugin:\($NAMES\)\b" "$PLUGIN" 2>/dev/null \
  | grep -v "\.backup/" \
  | grep -v "\.git/" \
  | grep -v "docs/skill-audit-2026-04-27.md" \
  | grep -v "docs/superpowers-audit-2026-04-27.md"
```

Expected: ~30-40 lines listing matches across SKILL.md bodies, rules, agents, commands, hooks, README, docs.

- [ ] **Step 2: Edit each match**

For each match, replace `panther-ivy-plugin:<old>` with `panther-ivy-plugin:knowledge/<old>`. Path-form references (`skills/<name>/`) become `skills/knowledge/<name>/`.

- [ ] **Step 3: Final scan — verify no old knowledge names remain**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
NAMES="apt-attack-patterns\|counterexample-guide\|ivy-debugging-methodology\|ivy-error-patterns\|ivy-toolkit\|ivy-writing-guide\|methodology-reference\|propagation-patterns\|specification-patterns\|claim-discussion"
grep -rn "panther-ivy-plugin:\($NAMES\)\b" "$PLUGIN" 2>/dev/null \
  | grep -v "\.backup/" \
  | grep -v "\.git/" \
  | grep -v "docs/skill-audit-2026-04-27.md" \
  | grep -v "docs/superpowers-audit-2026-04-27.md"
```

Expected: empty.

---

### Task 2.3: Phase 2 smoke test, commit, and PR

**Files:** None modified. Verification then commit/PR.

- [ ] **Step 1: Capture post-Phase-2 available-skills**

Manual: paste system-reminder block to `docs/superpowers/plans/captures/2026-04-27-after-phase-2-available-skills.txt`.

- [ ] **Step 2: Run smoke test assertions**

```bash
CAP=docs/superpowers/plans/captures/2026-04-27-after-phase-2-available-skills.txt
NAMES="apt-attack-patterns counterexample-guide ivy-debugging-methodology ivy-error-patterns ivy-toolkit ivy-writing-guide methodology-reference propagation-patterns specification-patterns claim-discussion"
echo "=== Knowledge new names should appear ==="
for s in $NAMES; do
  grep -q "panther-ivy-plugin:knowledge/$s\b" "$CAP" && echo "OK:   knowledge/$s" || echo "MISS: knowledge/$s"
done
echo
echo "=== Knowledge old names should NOT appear ==="
for s in $NAMES; do
  grep -q "panther-ivy-plugin:$s\b" "$CAP" && echo "OLD: $s STILL PRESENT" || echo "OK:   $s gone"
done
echo
echo "=== Phase 1 entries should still be present (regression check) ==="
for s in navigate build verify review triage; do
  grep -q "panther-ivy-plugin:workflow/$s\b" "$CAP" && echo "OK:   workflow/$s" || echo "REGRESSION: workflow/$s MISSING"
done
```

Expected: 10 × `OK: knowledge/<name>`, 10 × `OK: <name> gone`, 5 × `OK: workflow/<name>`.

- [ ] **Step 3: Commit Phase 2**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
git add "$PLUGIN/skills/knowledge/" \
        "$PLUGIN/.claude/rules/" \
        "$PLUGIN/agents/" \
        "$PLUGIN/commands/" \
        "$PLUGIN/hooks/scripts/" \
        "$PLUGIN/README.md" \
        "$PLUGIN/skills/README.md" \
        "$PLUGIN/docs/"
git status
git commit -m "refactor(skills): Phase 2 — migrate knowledge/ category to nested layout

Move 10 knowledge skills from skills/<name>/ to skills/knowledge/<name>/
with name: knowledge/<name> per the slash naming convention.

Cross-references updated across all source types. Phase 1 (workflow/)
entries verified still present (regression check passed).
"
```

- [ ] **Step 4: Open Phase 2 PR**

```bash
git push
gh pr create --title "refactor(skills): Phase 2 — knowledge/ migration" \
  --body "$(cat <<'EOF'
## Summary
- Migrate 10 knowledge skills to skills/knowledge/<name>/ with name: knowledge/<name>
- Update ~40 cross-references

## Test plan
- [x] All 10 knowledge/<name> entries in available-skills
- [x] No old knowledge skill names remain
- [x] Phase 1 workflow/<name> entries still present (regression)
- [x] grep for old knowledge names across plugin tree returns 0 matches

## Next phase
Phase 3: cross-cutting/ migration (4 skills).
EOF
)"
```

Wait for merge before Phase 3.

---

## Phase 3 — cross-cutting/ migration (4 skills, ~15 cross-references)

### Task 3.1: Move cross-cutting directories and rename frontmatter

**Files:**
- Move: 4 directories from `$PLUGIN/skills/<name>/` to `$PLUGIN/skills/cross-cutting/<name>/`
- Modify: 4 × `SKILL.md` (`name:` field)

The 4 skills: `completion-gate`, `reflection-patterns`, `parallel-dispatch`, `knowledge-capture`.

- [ ] **Step 1: Move 4 directories**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
cd "$PLUGIN"
mkdir -p skills/cross-cutting
for s in completion-gate reflection-patterns parallel-dispatch knowledge-capture; do
  git mv "skills/$s" "skills/cross-cutting/$s"
done
cd -
```

- [ ] **Step 2: Verify the moves**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
ls "$PLUGIN/skills/cross-cutting/" | wc -l
```

Expected: `4`.

- [ ] **Step 3: Rename `name:` field in each cross-cutting SKILL.md**

For each, edit `name: <leaf>` → `name: cross-cutting/<leaf>`.

- [ ] **Step 4: Verify all 4 frontmatter renames**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
for s in completion-gate reflection-patterns parallel-dispatch knowledge-capture; do
  grep "^name: " "$PLUGIN/skills/cross-cutting/$s/SKILL.md" | head -1
done
```

Expected: 4 lines, each `name: cross-cutting/<leaf>`.

---

### Task 3.2: Update cross-references for cross-cutting skills

**Files:** any file under `$PLUGIN` referencing the 4 names.

**Per-task options:** Phase 3 is a good place to switch to Option B (single ripgrep + sed) if Phases 1 and 2 had no surprises. Reflection-patterns is referenced by every workflow skill, so the volume is real (~15) but mechanical.

- [ ] **Step 1: List all old-name references**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
NAMES="completion-gate\|reflection-patterns\|parallel-dispatch\|knowledge-capture"
grep -rn "panther-ivy-plugin:\($NAMES\)\b" "$PLUGIN" 2>/dev/null \
  | grep -v "\.backup/" \
  | grep -v "\.git/" \
  | grep -v "docs/skill-audit-2026-04-27.md" \
  | grep -v "docs/superpowers-audit-2026-04-27.md"
```

Expected: ~15 lines.

- [ ] **Step 2: Edit each match**

Replace `panther-ivy-plugin:<old>` with `panther-ivy-plugin:cross-cutting/<old>`. Path-form references become `skills/cross-cutting/<name>/`.

- [ ] **Step 3: Final scan**

Same scan as Step 1; expected empty.

---

### Task 3.3: Phase 3 smoke test, commit, and PR

**Files:** None modified.

- [ ] **Step 1: Capture post-Phase-3 available-skills**

Manual: paste system-reminder to `docs/superpowers/plans/captures/2026-04-27-after-phase-3-available-skills.txt`.

- [ ] **Step 2: Run smoke test assertions**

```bash
CAP=docs/superpowers/plans/captures/2026-04-27-after-phase-3-available-skills.txt
NAMES="completion-gate reflection-patterns parallel-dispatch knowledge-capture"
echo "=== cross-cutting new names should appear ==="
for s in $NAMES; do
  grep -q "panther-ivy-plugin:cross-cutting/$s\b" "$CAP" && echo "OK:   cross-cutting/$s" || echo "MISS: cross-cutting/$s"
done
echo "=== cross-cutting old names should NOT appear ==="
for s in $NAMES; do
  grep -q "panther-ivy-plugin:$s\b" "$CAP" && echo "OLD: $s STILL PRESENT" || echo "OK:   $s gone"
done
echo "=== Phase 1+2 regression check ==="
for s in workflow/navigate workflow/build workflow/verify workflow/review workflow/triage \
         knowledge/ivy-toolkit knowledge/methodology-reference; do
  grep -q "panther-ivy-plugin:$s\b" "$CAP" && echo "OK:   $s" || echo "REGRESSION: $s"
done
```

Expected: 4 × OK new, 4 × OK gone, 7 × OK regression.

- [ ] **Step 3: Commit Phase 3**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
git add "$PLUGIN/skills/cross-cutting/" \
        "$PLUGIN/.claude/rules/" \
        "$PLUGIN/agents/" \
        "$PLUGIN/commands/" \
        "$PLUGIN/hooks/scripts/" \
        "$PLUGIN/skills/" \
        "$PLUGIN/README.md" \
        "$PLUGIN/skills/README.md" \
        "$PLUGIN/docs/"
git status
git commit -m "refactor(skills): Phase 3 — migrate cross-cutting/ category to nested layout

Move completion-gate, reflection-patterns, parallel-dispatch,
knowledge-capture from skills/<name>/ to skills/cross-cutting/<name>/.

reflection-patterns is loaded by every workflow skill; its rename
touches all 5 workflow SKILL.md bodies (now at skills/workflow/...).
Phase 1+2 regression checks passed.
"
```

- [ ] **Step 4: Open Phase 3 PR**

```bash
git push
gh pr create --title "refactor(skills): Phase 3 — cross-cutting/ migration" \
  --body "$(cat <<'EOF'
## Summary
- Migrate 4 cross-cutting skills to skills/cross-cutting/<name>/
- Update ~15 cross-references

## Test plan
- [x] 4/4 cross-cutting/<name> entries appear
- [x] 0/4 old names remain
- [x] Phase 1+2 entries still present

## Next phase
Phase 4: meta/ migration (2 skills + R4 mitigation for inject-using-plugin.sh).
EOF
)"
```

---

## Phase 4 — meta/ migration (2 skills, ~10 cross-references, R4 mitigation)

### Task 4.1: Move meta directories and rename frontmatter

**Files:**
- Move: 2 directories
- Modify: 2 × `SKILL.md`

The 2 skills: `using-panther-ivy-plugin`, `plugin-self-mod`.

- [ ] **Step 1: Move 2 directories**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
cd "$PLUGIN"
mkdir -p skills/meta
git mv skills/using-panther-ivy-plugin skills/meta/using-panther-ivy-plugin
git mv skills/plugin-self-mod          skills/meta/plugin-self-mod
cd -
```

- [ ] **Step 2: Rename `name:` field**

`skills/meta/using-panther-ivy-plugin/SKILL.md` line ~2: `name: meta/using-panther-ivy-plugin`
`skills/meta/plugin-self-mod/SKILL.md` line ~2: `name: meta/plugin-self-mod`

- [ ] **Step 3: Verify**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
for s in using-panther-ivy-plugin plugin-self-mod; do
  grep "^name: " "$PLUGIN/skills/meta/$s/SKILL.md" | head -1
done
```

Expected: `name: meta/using-panther-ivy-plugin`, `name: meta/plugin-self-mod`.

---

### Task 4.2: Update cross-references AND `inject-using-plugin.sh` (R4 mitigation)

**Files:**
- Modify: any file referencing `using-panther-ivy-plugin` or `plugin-self-mod` by old name
- **Critical:** `$PLUGIN/hooks/scripts/inject-using-plugin.sh`

**Per-task options for R4 mitigation:**

- **Option A — Rename the hook script too (Recommended):** `inject-using-plugin.sh` references the old skill name. Update the hook to reference `meta/using-panther-ivy-plugin`. The script filename itself can stay `inject-using-plugin.sh` (no rename needed; the file's content is what matters).
- **Option B — Update content only, keep filename:** Same as A but emphasizes that the filename has no semantic relationship to the skill name; the SessionStart-injection mechanism reads the SKILL.md by name from the script's content.
- **Option C — Rename script + content:** Rename to `inject-meta-using-plugin.sh` for symmetry. Adds churn for cosmetic value; rejected as YAGNI.

Option A/B chosen (effectively the same) — content-only update.

- [ ] **Step 1: Inspect `inject-using-plugin.sh`**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
cat "$PLUGIN/hooks/scripts/inject-using-plugin.sh"
```

Expected: shell script that injects the `using-panther-ivy-plugin` skill content as a SessionStart additionalContext block. Look for any string literal `using-panther-ivy-plugin` or path reference to the SKILL.md.

- [ ] **Step 2: Update the hook script**

In `$PLUGIN/hooks/scripts/inject-using-plugin.sh`, update:
- Any string literal `using-panther-ivy-plugin` → `meta/using-panther-ivy-plugin` (where it refers to the skill name)
- Any path reference `skills/using-panther-ivy-plugin/SKILL.md` → `skills/meta/using-panther-ivy-plugin/SKILL.md`

- [ ] **Step 3: Update other cross-references**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
grep -rn "panther-ivy-plugin:\(using-panther-ivy-plugin\|plugin-self-mod\)\b" "$PLUGIN" 2>/dev/null \
  | grep -v "\.backup/" \
  | grep -v "\.git/" \
  | grep -v "docs/skill-audit-2026-04-27.md" \
  | grep -v "docs/superpowers-audit-2026-04-27.md"
```

Edit each match: replace `panther-ivy-plugin:<old>` with `panther-ivy-plugin:meta/<old>`.

- [ ] **Step 4: Final scan for meta-skill old names**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
grep -rn "using-panther-ivy-plugin\|plugin-self-mod" "$PLUGIN/hooks/scripts/" "$PLUGIN/.claude/rules/" "$PLUGIN/agents/" "$PLUGIN/commands/" 2>/dev/null \
  | grep -v "meta/using-panther-ivy-plugin" \
  | grep -v "meta/plugin-self-mod"
```

Expected: empty (all references now use `meta/` prefix).

---

### Task 4.3: Phase 4 smoke test (with R4 verification), commit, and PR

**Files:** None modified.

- [ ] **Step 1: Capture post-Phase-4 available-skills AND SessionStart system-reminder**

Manual: open a fresh Claude Code session in the worktree. Capture:
- Available-skills block → `docs/superpowers/plans/captures/2026-04-27-after-phase-4-available-skills.txt`
- The SessionStart `[ivy-workspace]` and any `EXTREMELY_IMPORTANT` injection block (R4 evidence) → `docs/superpowers/plans/captures/2026-04-27-after-phase-4-sessionstart.txt`

- [ ] **Step 2: Run smoke test assertions for meta/**

```bash
CAP=docs/superpowers/plans/captures/2026-04-27-after-phase-4-available-skills.txt
echo "=== meta new names should appear ==="
for s in using-panther-ivy-plugin plugin-self-mod; do
  grep -q "panther-ivy-plugin:meta/$s\b" "$CAP" && echo "OK:   meta/$s" || echo "MISS: meta/$s"
done
echo "=== meta old names should NOT appear ==="
for s in using-panther-ivy-plugin plugin-self-mod; do
  grep -q "panther-ivy-plugin:$s\b" "$CAP" && echo "OLD: $s STILL PRESENT" || echo "OK:   $s gone"
done
```

Expected: 2 × OK new, 2 × OK gone.

- [ ] **Step 3: R4 mitigation — verify SessionStart injection still fires**

```bash
SS=docs/superpowers/plans/captures/2026-04-27-after-phase-4-sessionstart.txt
grep -q "EXTREMELY_IMPORTANT\|using-panther-ivy-plugin\|panther-ivy-plugin" "$SS" \
  && echo "OK: SessionStart injection of using-panther-ivy-plugin still fires" \
  || echo "R4 FIRED: SessionStart injection BROKEN — inject-using-plugin.sh did not fire"
```

Expected: `OK: SessionStart injection ...`. If R4 fires, immediately revert Phase 4 and diagnose `inject-using-plugin.sh`.

- [ ] **Step 4: Full regression check**

```bash
CAP=docs/superpowers/plans/captures/2026-04-27-after-phase-4-available-skills.txt
echo "=== All 21 expected entries ==="
for s in workflow/navigate workflow/build workflow/verify workflow/review workflow/triage \
         knowledge/apt-attack-patterns knowledge/counterexample-guide \
         knowledge/ivy-debugging-methodology knowledge/ivy-error-patterns \
         knowledge/ivy-toolkit knowledge/ivy-writing-guide knowledge/methodology-reference \
         knowledge/propagation-patterns knowledge/specification-patterns \
         knowledge/claim-discussion \
         cross-cutting/completion-gate cross-cutting/reflection-patterns \
         cross-cutting/parallel-dispatch cross-cutting/knowledge-capture \
         meta/using-panther-ivy-plugin meta/plugin-self-mod; do
  grep -q "panther-ivy-plugin:$s\b" "$CAP" && echo "OK:   $s" || echo "MISS: $s"
done
```

Expected: 21 × OK. Any MISS is a regression.

- [ ] **Step 5: Commit Phase 4**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
git add "$PLUGIN/skills/meta/" \
        "$PLUGIN/hooks/scripts/" \
        "$PLUGIN/.claude/rules/" \
        "$PLUGIN/agents/" \
        "$PLUGIN/commands/" \
        "$PLUGIN/skills/" \
        "$PLUGIN/README.md" \
        "$PLUGIN/skills/README.md" \
        "$PLUGIN/docs/"
git status
git commit -m "refactor(skills): Phase 4 — migrate meta/ category and update inject-using-plugin.sh

Move using-panther-ivy-plugin and plugin-self-mod to skills/meta/<name>/.
Update inject-using-plugin.sh hook script to reference the new skill name
(R4 mitigation per spec §7).

R4 verification: SessionStart [ivy-workspace] + EXTREMELY_IMPORTANT
injection still fires after rename.

Full regression check: all 21 expected entries present in available-skills.
"
```

- [ ] **Step 6: Open Phase 4 PR**

```bash
git push
gh pr create --title "refactor(skills): Phase 4 — meta/ migration + R4 mitigation" \
  --body "$(cat <<'EOF'
## Summary
- Migrate 2 meta skills to skills/meta/<name>/
- Update inject-using-plugin.sh hook script (R4 mitigation)
- Full regression check: all 21 entries verified in available-skills

## Test plan
- [x] meta/using-panther-ivy-plugin and meta/plugin-self-mod appear
- [x] Old meta names absent
- [x] SessionStart injection still fires (R4 mitigated)
- [x] All 4 phases' entries present (full regression)

## Next phase
Phase 5: cleanup (worktree-wide final scan, README rewrite, integration test, backup deletion).
EOF
)"
```

---

## Phase 5 — Cleanup

### Task 5.1: Worktree-wide final old-name scan

**Files:** None modified initially. May need follow-up edits.

- [ ] **Step 1: Run a worktree-wide scan for any remaining old skill names**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
ALL_NAMES="navigate\|build\|verify\|review\|triage\|apt-attack-patterns\|counterexample-guide\|ivy-debugging-methodology\|ivy-error-patterns\|ivy-toolkit\|ivy-writing-guide\|methodology-reference\|propagation-patterns\|specification-patterns\|claim-discussion\|completion-gate\|reflection-patterns\|parallel-dispatch\|knowledge-capture\|using-panther-ivy-plugin\|plugin-self-mod"

# Look in the WHOLE worktree, not just the plugin
grep -rn "panther-ivy-plugin:\($ALL_NAMES\)\b" . 2>/dev/null \
  | grep -v "\.backup/" \
  | grep -v "\.git/" \
  | grep -v "docs/skill-audit-2026-04-27.md" \
  | grep -v "docs/superpowers-audit-2026-04-27.md" \
  | grep -v "docs/superpowers/specs/2026-04-27-skill-directory-taxonomy-restructure-design.md" \
  | grep -v "docs/superpowers/plans/2026-04-27-skill-directory-taxonomy-restructure.md"
```

The exclusions for the spec and plan files are because they document the migration with both old and new names. Expected: empty result. Any non-empty match needs a fix.

- [ ] **Step 2: Fix any leftover references**

For each match, edit the file to use the new `<category>/<name>` form. After fixing, re-run Step 1 until empty.

---

### Task 5.2: Rewrite `skills/README.md` to the new tree

**Files:**
- Modify: `$PLUGIN/skills/README.md`

- [ ] **Step 1: Replace the README skill index**

Rewrite `$PLUGIN/skills/README.md` to reflect the 4-category tree. Use this template (replace the existing content):

```markdown
# Skills

## Overview

Skills provide reference material and domain knowledge for Ivy protocol testing within the PANTHER framework. The tree is organised into four categories: workflow (user-facing entry points), knowledge (reference material), cross-cutting (gates and patterns invoked by multiple workflows), and meta (plugin-internal skills).

## Workflow Skills (5)

User-facing entry points activated by the routing system or natural language.

| Skill | Purpose |
|-------|---------|
| [workflow/navigate](workflow/navigate/) | Session entry point — detect intent, resume context, route to the right workflow |
| [workflow/verify](workflow/verify/) | Verify, compile, diagnose failures in Ivy specifications |
| [workflow/build](workflow/build/) | Create models, add layers, propagate type changes |
| [workflow/review](workflow/review/) | Audit quality, check RFC coverage, run multi-agent review |
| [workflow/triage](workflow/triage/) | Diagnose toolchain issues, health check LSP + MCP stack |

## Knowledge Skills (10)

Reference material loaded by workflows and agents on demand.

| Skill | Purpose |
|-------|---------|
| [knowledge/apt-attack-patterns](knowledge/apt-attack-patterns/) | APT-layer pattern library for NACT |
| [knowledge/counterexample-guide](knowledge/counterexample-guide/) | Interpreting ivy_verify counterexample traces |
| [knowledge/ivy-debugging-methodology](knowledge/ivy-debugging-methodology/) | Pre-fix research workflow for Ivy errors |
| [knowledge/ivy-error-patterns](knowledge/ivy-error-patterns/) | Numbered verifier-patterns catalog and Ivy error lookup |
| [knowledge/ivy-toolkit](knowledge/ivy-toolkit/) | MCP tool documentation and tool selection guidance |
| [knowledge/ivy-writing-guide](knowledge/ivy-writing-guide/) | Ivy 1.7 syntax reference and RFC annotation conventions |
| [knowledge/methodology-reference](knowledge/methodology-reference/) | NCT, NACT, NSCT methodology reference |
| [knowledge/propagation-patterns](knowledge/propagation-patterns/) | Patterns for propagating type changes across spec layers |
| [knowledge/specification-patterns](knowledge/specification-patterns/) | 14-layer structural template and formal model patterns |
| [knowledge/claim-discussion](knowledge/claim-discussion/) | Decision trees for verification claim resolution |

## Cross-cutting Skills (4)

Patterns and gates invoked by multiple workflows.

| Skill | Purpose |
|-------|---------|
| [cross-cutting/completion-gate](cross-cutting/completion-gate/) | 5-step IDENTIFY→RUN→READ→VERIFY→THEN-claim gate |
| [cross-cutting/reflection-patterns](cross-cutting/reflection-patterns/) | Reflection Gate, MPE, Situation Briefing, G0–G5 patterns |
| [cross-cutting/parallel-dispatch](cross-cutting/parallel-dispatch/) | Multi-Agent dispatch composition pattern |
| [cross-cutting/knowledge-capture](cross-cutting/knowledge-capture/) | Session learnings extraction at workflow phase boundaries |

## Meta Skills (2)

Plugin-internal: not user-invocable.

| Skill | Purpose |
|-------|---------|
| [meta/plugin-self-mod](meta/plugin-self-mod/) | 3-agent loop for plugin source modifications |

Plus 1 SessionStart-injected meta-skill: see [meta/using-panther-ivy-plugin/SKILL.md](meta/using-panther-ivy-plugin/SKILL.md).
```

- [ ] **Step 2: Verify all 21 skills are linked**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
grep -c "^| \[" "$PLUGIN/skills/README.md"
```

Expected: `21` rows in tables (5+10+4+2). If less, add the missing one (likely `meta/using-panther-ivy-plugin` was excluded from a table because it's footnoted; check the file).

---

### Task 5.3: Integration test — end-to-end workflow exercise

**Files:** None modified. Verification only.

- [ ] **Step 1: Open a fresh Claude Code session in the worktree**

Capture the system-reminder available-skills block one more time → `docs/superpowers/plans/captures/2026-04-27-final-available-skills.txt`.

- [ ] **Step 2: Exercise the workflow chain**

In the same Claude Code session:
1. Run `/triage` and confirm preflight mode dispatches.
2. Run `/verify --help` (or invoke verify on a sample Ivy spec) and confirm dispatch into `workflow/verify`.
3. Type a natural-language prompt that should route to build, e.g. "create a new BGP spec layer", and confirm `workflow/build` dispatches.

- [ ] **Step 3: Verify all dispatched skills loaded their references**

Inspect the conversation: each dispatched skill should have loaded its references (visible via the system-reminder additionalContext blocks). No "skill not found" or "reference path invalid" errors.

- [ ] **Step 4: Re-run the suite-level skill audit**

```bash
# Manually invoke the audit, OR run /skill-creator:skill-creator with the same args
# as the 2026-04-27 audit to compare findings
```

Expected deltas vs `panther-ivy-plugin/docs/skill-audit-2026-04-27.md`:
- P0 verify auto-discovery: RESOLVED
- S2 workflow asymmetry: RESOLVED
- S1 README index lag: RESOLVED for the 21 listed skills

Document any remaining findings as a follow-up issue.

---

### Task 5.4: Delete backup, final commit, final PR

**Files:**
- Delete: `$PLUGIN/.backup/skills-restructure-2026-04-27/`
- Modify: `$PLUGIN/skills/README.md` (already done in Task 5.2)

**Per-task options for backup deletion:**

- **Option A — Delete in this PR (Recommended):** Backup served its purpose; it's in git history. Deleting reduces repo size and signals the migration is complete.
- **Option B — Defer deletion:** Keep the backup for one release cycle in case a regression surfaces in a downstream session. Re-evaluate in 2 weeks.
- **Option C — Move to long-term archive:** Tar it and move to `panther-ivy-plugin/.backup/archive/`. Useless ceremony if it's already in git history; rejected.

Option A chosen.

- [ ] **Step 1: Delete the backup**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
git rm -rf "$PLUGIN/.backup/skills-restructure-2026-04-27/"
```

- [ ] **Step 2: Stage the README rewrite**

```bash
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
git add "$PLUGIN/skills/README.md"
git status
```

- [ ] **Step 3: Commit**

```bash
git commit -m "refactor(skills): Phase 5 — cleanup (delete backup, rewrite README)

Migration complete: all 21 skills now nested under skills/<category>/<name>/
with name: <category>/<leaf>. Verify auto-discovery bug resolved as
side-effect of Phase 1.

Skills inventory rewritten in skills/README.md to reflect the new tree:
5 workflow / 10 knowledge / 4 cross-cutting / 2 meta = 21 skills.

Backup deleted (preserved in git history as commit
<Phase 0 commit SHA> via the .backup/skills-restructure-2026-04-27/
snapshot).

Full integration test passed: workflow chain (triage / verify / build)
dispatches correctly; SessionStart injection still fires; suite-level
audit confirms verify auto-discovery and S2 asymmetry resolved.

Companion specs:
- docs/superpowers/specs/2026-04-27-skill-directory-taxonomy-restructure-design.md
- panther-ivy-plugin/docs/skill-audit-2026-04-27.md
"
```

- [ ] **Step 4: Open Phase 5 PR**

```bash
git push
gh pr create --title "refactor(skills): Phase 5 — cleanup" \
  --body "$(cat <<'EOF'
## Summary
- Worktree-wide final scan: 0 old skill name references remain (excluding audit/spec/plan docs)
- skills/README.md rewritten to reflect 4-category tree
- Integration test: workflow chain dispatches end-to-end
- Audit re-run: P0 verify discovery RESOLVED, S2 asymmetry RESOLVED
- Backup deleted (preserved in git history via Phase 0 commit)

## Test plan
- [x] Worktree-wide grep returns 0 old skill name matches
- [x] /triage dispatches
- [x] /verify dispatches into workflow/verify
- [x] /build dispatches via natural-language prompt
- [x] All 21 skills appear in available-skills under new names
- [x] Suite-level audit confirms expected deltas

## Migration complete
After this PR merges, the panther-ivy-plugin skills/ tree is fully migrated
to the 4-category nested taxonomy. Layer 1 (Mental model) artifact 1 of 4
delivered. Future Layer 1 work tracked in spec §9 (generated Plugin Map,
frontmatter lint hook, K3 split).
EOF
)"
```

- [ ] **Step 5: Update the audit's open-question status**

After Phase 5 PR merges, update `panther-ivy-plugin/docs/skill-audit-2026-04-27.md` to mark P0 (verify auto-discovery) and S2 (workflow asymmetry) as RESOLVED. The `context: fork` open question remains pending the harness-owner conversation; this restructure does not affect it.

---

## Self-review checklist (run before declaring done)

- **Spec coverage:** Every section of `docs/superpowers/specs/2026-04-27-skill-directory-taxonomy-restructure-design.md` maps to at least one task here. §2 architecture → Task 1.1+2.1+3.1+4.1+5.2. §3 cross-references → Task 1.3+2.2+3.2+4.2. §4 migration plan → Phases 0-5 task structure. §5 error handling → smoke-test failure rollback steps in each phase. §6 testing → smoke tests + Task 5.3 integration. §7 risks → R1 (Phase 1 Step 5 rollback), R2 (Task 5.1 worktree scan), R3 (Task 0.1 Step 1), R4 (Task 4.2 + 4.3 Step 3), R5 (Task 0.1 Step 2), R6 (Task 0.1 Step 3). ✓
- **Placeholder scan:** No "TBD", "TODO", "implement later", "fill in details" appears in any task content. The shell scripts include exact commands; the bash assertions include exact expected output. ✓
- **Type consistency:** Skill names use the same form throughout (e.g. `workflow/verify` always with the slash; never `workflow-verify` mid-document). Path references are consistently `<plugin-root>/skills/<category>/<leaf>/`. ✓

If any issue surfaces during execution, fix it inline and continue.

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-27-skill-directory-taxonomy-restructure.md`. Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task (or per phase), review between tasks, fast iteration. Good for this plan because phases are independent and each phase's smoke test is a clean review boundary.
2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints. Good if you want to ride along with each step, especially for Phase 1 (where R1 risk is concentrated).

Which approach?
