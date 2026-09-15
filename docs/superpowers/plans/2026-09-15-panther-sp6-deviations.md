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
