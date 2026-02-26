# Task 22: ivy-lsp v0.7.0 Version Bump, Merge, and Tagged Release

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** After Task 12 integration tests pass, bump ivy-lsp from 0.6.1 to 0.7.0, merge the feature branch into main, create an annotated tag, push, and update the PANTHER submodule pointer.

**Architecture:** Version bump in `pyproject.toml`, fast-forward merge of `feat/scoped-code-lenses` into `main`, annotated tag `v0.7.0`, push to origin, then update the PANTHER worktree submodule reference.

**Tech Stack:** Python (pyproject.toml), git.

**Status:** pending
**Depends on:** Task 12 (integration tests pass)

**Base paths:**
- **ivy-lsp submodule:** `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/`
- **PANTHER worktree:** `.` (root of the ivy-lsp-integration worktree)

---

## Version Bump Proposal

### Why `0.7.0` (not `0.6.2`)

This is a **minor version bump** (semver: backward-compatible new functionality):

| Category | Count | Details |
|----------|-------|---------|
| New data structures | 4 | `ExportImportInfo`, `TestScope`, `NctClassification`, `ActionClassification` |
| New model class | 1 | `ScopedRequirementModel` (subclass of `RequirementGraph`) |
| New LSP commands | 3 | `ivy/setActiveTest`, `ivy/listTests`, `ivy/compileTest` |
| Enhanced features | 2 | Scope-aware code lenses, scope-aware diagnostics |
| New symbol extraction | 1 | `ExportDecl`/`ImportDecl` as `Event` symbols |
| New test files | 8 | 7 unit test files + 1 integration test file |
| New tests | ~100 | 92 unit + 7 integration regression tests |
| Commits since v0.6.1 | 22+ | All backward-compatible additions |

**Backward compatibility preserved:** `ScopedRequirementModel` subclasses `RequirementGraph`. All existing unscoped query methods work unchanged. No public API removed.

### Tag convention

Existing tags follow `v{major}.{minor}.{patch}`: `v0.6.1`, `v0.5.5`, `v0.5.0`, etc.

New tag: **`v0.7.0`**

---

## Step 1: Bump version in pyproject.toml

In `ivy_lsp` submodule, edit `pyproject.toml` line 7:

```toml
# Before
version = "0.6.1"

# After
version = "0.7.0"
```

## Step 2: Verify full test suite passes

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
python -m pytest tests/ -v --tb=short
```

Expected: ALL PASS (including the new `test_scoped_integration.py` from Task 12).

## Step 3: Commit version bump

```bash
git add pyproject.toml
git commit -m "chore: bump version to 0.7.0 for scoped requirement model"
```

## Step 4: Merge feature branch into main

```bash
git checkout main
git merge feat/scoped-code-lenses --ff-only
```

Expected: Fast-forward merge succeeds (main is an ancestor of feat/scoped-code-lenses).

If fast-forward fails (main has diverged), use:

```bash
git merge feat/scoped-code-lenses -m "feat: merge scoped requirement model (Tasks 1-12)"
```

## Step 5: Create annotated tag

```bash
git tag -a v0.7.0 -m "v0.7.0: Scoped Requirement Model

New features:
- ScopedRequirementModel with per-test requirement scoping
- ExportImportInfo extraction (light-mode regex + full-mode AST)
- TestScope computation with role detection
- NCT classification (assumption/guarantee/tester-only)
- Scope-aware code lenses and diagnostics
- 3 new LSP commands: ivy/setActiveTest, ivy/listTests, ivy/compileTest
- ExportDecl/ImportDecl symbol extraction
- Integration regression tests verifying triple-counting fix

Backward compatible: ScopedRequirementModel subclasses RequirementGraph."
```

## Step 6: Push main and tag to origin

```bash
git push origin main
git push origin v0.7.0
```

## Step 7: Update PANTHER submodule pointer

Back in the PANTHER worktree root:

```bash
cd /path/to/panther/worktree/root
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git checkout main  # ensure submodule points to main (with the tag)
cd /path/to/panther/worktree/root
git add panther/plugins/services/testers/panther_ivy
```

Also commit the reviewed task 11 plan:

```bash
git add docs/plans/tasks/scoped-requirement-model/11-export-import-symbols.md
git commit -m "chore: update panther_ivy submodule to ivy-lsp v0.7.0 (scoped requirement model)"
```

## Step 8: Push PANTHER worktree

```bash
git push origin HEAD
```

---

## Verification Checklist

After all steps:

```bash
# In ivy-lsp submodule
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git log --oneline -3           # Should show version bump commit on main
git describe --tags             # Should show v0.7.0
python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"
                                # Should print 0.7.0

# In PANTHER worktree
cd /path/to/panther/worktree/root
git submodule status panther/plugins/services/testers/panther_ivy
                                # Should show the v0.7.0 commit hash
```
