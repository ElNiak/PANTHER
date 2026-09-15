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
