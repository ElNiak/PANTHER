# SP6 deviation log

Row: SP6 — PANTHER side, stop both build paths destroying tracked work.
Plan: `docs/superpowers/plans/2026-09-15-panther-sp6.md`
Branch: `feat/arfc-pipeline-and-runtime-anchors`, opened at `e4b1a7d61`.

One numbered entry per deviation, added as it occurs. D1-D4 are premise corrections
measured before Task 1; D5-D13 come from the single `review-plan` pass on the finished
plan, all fixed in the plan file before Task 1 ran.

## Premise corrections (measured before Task 1)

- **D1** — Four rmtree-of-`docs/` sites, not the two the brief named: it missed
  `panther/cli/commands/docs.py:61-64` and `panther_builder.py:57`.
- **D2** — `panther_builder.py clean` never forwards to the CLI (`main()` handles it at
  `:126-127`, before `_try_forward_to_cli`), so a CLI-only fix leaves the bootstrap path
  fully destructive.
- **D3** — A fifth destroyer, outside `docs/`: `docs.py:48-54` reverts the tracked
  `mkdocs.yml` from a stale tracked `panther/tools/docs_gen/mkdocs.yml.bak`. Measured
  difference is exactly one line — live `mkdocs.yml:78` carries
  `- ai_rfc (reconstructed specs): reference/ai_rfc.md`, the backup does not. Ruled in
  scope by the user.
- **D4** — Two untracked-and-ignored files live in the corpus directory
  (`2026-09-05-arfc-gepa-no-key-executor-prompt.md`,
  `2026-09-09-arfc-sp-closure-executor-prompt.md`), so a tracked-path predicate would not
  have saved them. Decisive for choosing Option B over Option A.

## From the `review-plan` pass (2 Critical, 6 Warning, 2 Info)

- **D5** (Critical) — The worktree guard refuses git in scripted form, which would have
  blocked Task 1 and the gate at their first command. Procedure rewritten to plain,
  literal-path, one-git-command-per-invocation.
- **D6** (Critical) — The clone supplies data while the editable-installed worktree
  supplies code, and `git clone` carries committed state only. Task 1 must precede all
  edits; the gate must follow all commits.
- **D7** (Warning) — `pyproject.toml:408` is `[tool.pyright] exclude`, not vulture as the
  plan's first draft claimed.
- **D8** (Warning) — The first draft claimed `panther_builder.py`'s docstring advertises
  removing `docs/`; it does not. Only `build.py:309` enumerates `docs/`.
- **D9** (Warning) — Task 1 originally used one clone for both commands; `build clean`
  deletes the `htmlcov/` seed that `docs build` needs, and cross-contaminates the counts.
  Split into two clones, and the same split applied to the gate.
- **D10** (Warning) — `docs build` in a clone attempts a doomed `pip install -e` on the
  empty `panther_ivy/` directory. Documented as expected non-fatal noise.
- **D11** (Warning) — The git-auto-commit-action default `file_pattern` was asserted
  without verification; downgraded to an explicitly-unverified external claim.
- **D12** (Warning) — Task 3's RED would have been reported as an `AttributeError`.
  Tightened to require the behavioural assertion be seen failing against an empty-bodied
  function.
- **D13** (Info, no action) — The mkdocs non-nav publication claim was upgraded from
  asserted to measured; `tests/pytest.ini:23` already lists `docs`, harmless to leave.

## Execution deviations

- **D14** — Task 1 (reproduce the destruction) is executed by the controller rather than
  dispatched to an implementer. The row's central constraint is that no destructive
  command runs in the working tree; handing a subagent a brief that contains
  `panther build clean` and `panther docs build` creates exactly the failure mode the
  constraint exists to prevent. Task 1 edits no source, so no code is written inline.
  *Cost if wrong:* the controller spends context on evidence capture that a subagent
  could have isolated.

- **D15** — `-n auto` hangs intermittently in this worktree while peer sessions are busy:
  the first `tests/ -m unit -n auto` run completed in 21.57 s, two immediately-following
  runs hung past 420 s at ~98%, and `-n 4` completed the same selection in 14.85 s with
  an identical failure set. The row therefore runs pytest at `-n 4`, not `-n auto`.
  *Cost if wrong:* the hang has a different cause and `-n 4` merely hides it. Ruled
  acceptable — the failure set is identical either way, so the comparison is sound.
- **D16** — The tracked corpus is **40 files, not 38**, as of commit `40bb8d06d`: the
  plan and its deviation log were themselves committed under `docs/superpowers/plans/`,
  joining the corpus this row exists to protect. Every before/after count in Task 1 and
  the Phase 4 gate reads 40, not the 38 the plan and the brief state. The 38 figure
  remains correct for the tree as it stood at `e4b1a7d61`.
- **D17** — The PANTHER suite is **not green at baseline**: 20 pre-existing failures.
  18 are in `tests/unit/test_webapp/` (17 in `test_web_observer.py`, 1 in
  `test_plugin_forms.py`) and 2 in
  `tests/unit/plugins/environments/network_environment/docker_compose/`. None touch the
  docs or build commands. The row's gate therefore compares against 20 known failures
  rather than against green, and any 21st failure is mine.

## Task 1 — reproduction evidence (observed, not inferred)

Two throwaway clones of `40bb8d06d`, each seeded with an untracked sentinel under
`docs/superpowers/plans/` and a non-placeholder `htmlcov/index.html`.

`panther build clean` in `/tmp/claude-501/sp6/repro-clean`:
  echoed `Removing /private/tmp/claude-501/sp6/repro-clean/docs`;
  docs files on disk 41 -> 0; `git status --short | grep -c '^ D'` = **40**;
  sentinel **destroyed, unrecoverable**.

`panther docs build` in `/tmp/claude-501/sp6/repro-docs`:
  docs files on disk 41 -> regenerated without the corpus;
  `git status --short | grep -c '^ D'` = **40**; sentinel **destroyed, unrecoverable**;
  `git diff --stat mkdocs.yml` = `1 file changed, 1 deletion(-)`, and the line
  `- ai_rfc (reconstructed specs): reference/ai_rfc.md` is **gone from mkdocs.yml** —
  destroyer 5 confirmed live, not theoretical.

- **D18** — `docs.py` invokes a bare `mkdocs` from `PATH` (`:238` build, `:294`
  version, `:311` serve, `:337-346` gh-deploy) rather than `sys.executable -m mkdocs`.
  On this machine `which mkdocs` is `/Users/elniak/.pyenv/shims/mkdocs`, a pyenv shim
  whose site-packages differ from the project venv, so `panther docs build` aborted with
  `Failed to load extension 'mkdocs-click'` even after that package was installed into
  `.venv`. Prepending `.venv/bin` to `PATH` made the same command succeed: rc=0,
  "Documentation built in 125.75 seconds", 467 HTML pages. **Pre-existing defect,
  reported not fixed** — it is neither the wipe nor the builder, so fixing it is scope
  expansion. The Phase 4 gate prepends `.venv/bin` to `PATH` instead.
  *Cost if wrong:* the gate proves the property under a PATH the user does not normally
  have. Mitigated by reporting the defect and its one-line fix.
- **D19** — `mkdocs-click` (declared at `pyproject.toml:168` in the `[doc]` extra) was
  missing from `.venv` and was installed. This completes the declared environment rather
  than changing it, and was needed so the gate can prove mkdocs actually reads the new
  `docs_dir` rather than aborting before it gets there.
  *Cost if wrong:* a shared venv was mutated while two peer sessions were active; the
  change is additive and the package is a declared dependency.

- **D22** — **Infrastructure, not this row, and not any agent.** Partway through Phase 4,
  `git status` reported all 1134 tracked files as staged deletions. Cause: an external
  macOS process had renamed the git index files on collision —
  `.git/worktrees/iut-ai-rfc/index` to `index 2` (145,528 bytes, Sep 15 12:56) and
  `.git/index` to `index 2` (159,376 bytes, **Jan 15 2026**). With no file named `index`,
  git reads an empty index, so every tracked file compares as deleted. Both renamed files
  carry valid `DIRC` magic. HEAD (1134 files, 42 under `docs/`) and the working tree were
  never touched, and no commit captured the deletions.
  Repaired with the user's approval by renaming this worktree's `index 2` back to `index`,
  which restores the real index rather than rebuilding from HEAD; `git status` then showed
  0 staged deletions. The main checkout's January-dated `index 2` was left alone — an
  8-month-stale index is a separate decision for the user.
  This is the same family as the project's known issue that a watcher hides every `.pth`
  file under this tree within ~90 s. The repository lives under `~/Documents/`, which
  macOS syncs by default, and rename-on-collision to "name 2" is that behaviour's
  signature. **The hazard was live**: any `git commit` without an explicit pathspec, by
  this session or by the SP7d peer sharing the worktree, would have committed the deletion
  of the entire repository. Explicit-pathspec staging is what made it survivable.

## Phase 4 gate — observed, in throwaway clones of `415242c19`

Both clones seeded with an untracked `GATE-SENTINEL.md` under `docs/superpowers/plans/`
and a non-placeholder `htmlcov/index.html`. Counts are invariance checks, not fixed
figures (D16): the corpus keeps growing while peers commit.

`panther build clean` in `/tmp/claude-501/sp6/gate-clean` — rc=0:

    echoed: Removing .../docs_build
            Removing .../htmlcov          (docs/ NOT mentioned)
    tracked under docs/   42  ->  42
    docs files on disk    43  ->  43
    git status ' D' count  0
    untracked sentinel    SURVIVED
    docs_build/           removed, correctly

`panther docs build` in `/tmp/claude-501/sp6/gate-docs` — rc=0,
"Documentation built in 118.61 seconds":

    tracked under docs/   42  ->  42
    docs files on disk    43  ->  43
    git status ' D' count  0
    untracked sentinel    SURVIVED
    git diff --stat mkdocs.yml   EMPTY  <- destroyer 5 is dead
    ai_rfc nav line in mkdocs.yml   still present (1 occurrence)
    docs_build/           21 files generated   <- the build really produced output
    site/                 468 HTML pages built
    corpus paths in site/  0   <- no superpowers/ or research/ page published

That last line matters beyond the row's stated goal: it confirms the design choice closed
the publication exposure that the rejected option would have opened. Before this row the
corpus was never published only because it was deleted first.

Compare with the Task 1 reproduction of the same two commands, which gave 40 tracked
deletions each, a destroyed sentinel, and `mkdocs.yml | 1 -`.

## Suite

Selection `tests/unit/ -m unit -n 4`:
  baseline 20 failed / 1138 passed / 4 skipped / 1 xfailed / 1 error
  now      20 failed / 1164 passed / 5 skipped / 1 xfailed / 1 error
  passed 1138 + 27 new - 1 flipped = 1164; skipped 4 + 1 = 5; failed unchanged at 20.
  The row's 27 new tests all pass in isolation. Two pre-existing tests flipped, both in
  the picoquic-importability family and neither attributable to this row's production
  code — see the ledger's "Suite measurement" block for the decomposition and for what
  could NOT be proven.

## MIGRATION NOTE — read before pulling this row into an existing checkout

Raised by the final whole-row review as its one must-handle item. It needs no code change.

Before this row, a stale generated tree under `docs/` was covered by `.gitignore:54` and was
cleared by every `panther build clean` and every `panther docs build`. This row removes both
of those: `.gitignore:54` is now `docs_build/`, `build clean` no longer touches `docs/`, and
`docs build` writes to `docs_build/`. **So the row removes the only two things that cleared
those files and simultaneously stops hiding them.**

Measured: the main checkout at `…/PANTHER/master` holds **2,199 files under `docs/`** with the
`build_dict` and `gen_ref_pages` output shape (`INSTALL.md`, `changelog.md`, `cli_click.md`,
`core_*.md`). Four further worktrees exist beside this one. After pulling, every one of those
files becomes a plain untracked entry in `git status`, and a single `git add .` or `git add -A`
would commit a 2,199-file generated tree. `origin/production` tracks zero files under `docs/`
today, so the merge lands this on every developer at once.

**The natural cleanup is the shape this row rejected.** `git clean -fd docs/` is a tracked-path
predicate — exactly what Option A was rejected for — and in any worktree holding untracked
corpus files it deletes them. In this worktree those are
`docs/superpowers/plans/2026-09-05-arfc-gepa-no-key-executor-prompt.md` and
`2026-09-09-arfc-sp-closure-executor-prompt.md`, the two files whose existence decided Option B
over Option A (D4). Ordering matters: while `docs/` was still ignored they were skipped by
`git clean -fd` and needed `-x`; the moment this row's `.gitignore` lands, `-fd` takes them.

**Procedure after pulling, per checkout:**

1. `git clean -nd docs/` — **dry run first, never blind.**
2. Read the listing. Anything hand-authored — anything under `docs/superpowers/` or
   `docs/research/` that is not tracked — must be moved or committed before step 3.
3. Only then `git clean -fd docs/`.

Do not skip step 1. Untracked plan files live under `docs/superpowers/plans/`.
