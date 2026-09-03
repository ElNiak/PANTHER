# SP7a — deviation log

One entry per deviation: what the plan said, what the code showed, what I did.
Anchors verified against PANTHER `b50e569d0` / ai_rfc `abc07a3` (SP1 landed 2026-09-03 19:36).

---

## D1 — The post-SP1 baseline is 808, not 769

**Plan said.** Global Constraints and Task 10 Step 2: "baseline after SP1: 769 = 390 substrate +
339 experiment + 40 server". SP1's own goal statement also says 769.

**Code showed.** `SSLKEYLOGFILE= $PY -m pytest tests -n auto` → **808 passed, 0 failed** in 19.47s;
collected as 384 substrate + 45 server + 379 experiment. SP0 and SP1 both added tests after those
numbers were written. (Pre-move, on 2026-09-03 at noon, the same three trees collected 793.)

**What I did.** Recorded 808 as the baseline in Global Constraints and in Task 10 Step 2, with a
note to use the measured number rather than either prediction.

---

## D2 — `panther_repo` survived in the experiment driver, and the plan assumed it had not

**Plan said.** Global Constraints flagged one SP1-contingent case: `server/paths.py`'s `Context`.
Task 5's prose asserted "SP1 drops its `panther_repo` parameter" from `_init`, and Task 6 produced
`prepare(target, *, root, toolchain, template, template_commit)` with no `panther_repo` and three
test calls that omit it.

**Code showed.** SP1 retired `panther_repo` from the **server** only. `ai_rfc/server/paths.py`'s
`Context` is now just `workspace: Path` — so Task 4 Step 3's snippet was right as written. But the
**experiment driver kept it**: `ai_rfc/experiment/workspace.py:449` still declares
`panther_repo: Path` keyword-only with no default; `ai_rfc/experiment/cli.py` still registers a
`required=True` `--panther-repo` (lines 202, 302) and passes `panther_repo=args.panther_repo.resolve()`
(lines 414, 453); and `tests/experiment/test_config.py:50` still declares
`_init(tmp_path, pristine, panther_repo, plugin_root, **overrides)` with a `panther_repo` fixture at
`tests/experiment/conftest.py:19`.

**What I did.** Kept `panther_repo` in Task 6's produced signature and in all three of its new test
calls; added the `panther_repo` fixture to Task 5's and Task 8's new test signatures and to their
`_init(...)` calls. Rewrote the Global Constraints bullet to record all four cases. Retiring
`--panther-repo` stays CLI-1's job — not reopened here.

---

## D3 — Seven plan defects that would each have failed the task that contained them

Found by two independent read-only reviews of the plan against the landed tree, each verified by me
before acting. All fixed in the plan file; the plan now carries a "Review correction" note at each
site.

| # | Task/Step | Plan said | Code showed | Fix |
|---|---|---|---|---|
| a | 3 / 1 + 5 | `_lint`/`_build` argv starts with the draft path | `pipeline/run.py`'s `_checkpoint` and `_gate` both put the **verb** at `argv[0]`; `draft/cli.py` dispatches on it | Prefixed `"lint"`/`"build"` in the builders and in the Step 1 assertions |
| b | 3 / 1 | Use fixture `prepared` | No such fixture. `tests/substrate/pipeline/conftest.py` has `workspace`, `mined_workspace`, `finished_workspace`; the last returns a bare `Path`, and its draft repo has no commit | Added a `drafted_workspace` fixture returning a `Workspace` with a committed draft; rewrote five tests to use it; added `conftest.py` to the task's files and commit |
| c | 4 / 1 | Three tests take `fixture_workspace` | That fixture exists only in the **experiment** suite (`tests/experiment/conftest.py:35`); the server suite has `make_workspace`/`workspace`, and `workspace` is a resolved `Context` | Switched to `workspace`; `(workspace.workspace / "refcache")` for the path |
| d | 4 / 1 | Fixture `recorded`, used as `recorded["tag"]` | `_recorded` is a module-level **function** (`tests/server/test_draft.py:16`) returning the **cluster id string** | Call `_recorded(workspace)`; use the literal tag `"draft-test-spec-00"`; assert via the file's own `git(_draft(workspace), …)` idiom |
| e | 4 / 6 | `tools.ai_rfc_draft_build(args.ref)` in the CLI dispatch | `ai_rfc/server/cli.py` never imports `tools`; every branch calls a `.core` module with the resolved `ctx` | `build.draft_build(ctx, args.ref)`, with `build` added to the deferred `from .core import …` |
| f | 5 + 8 | `init_campaign(_init(...))` at four sites | `_init` **already returns a `Campaign`** (`test_config.py:69`) | Dropped the outer call. Note the two `pytest.raises` cases would have passed *by accident* |
| g | 5 | Step 5 expects `tests/experiment` all green | `test_runner.py:50` asserts `set(env) ==` an exact **six**-key set; the new `AI_RFC_TOOLCHAIN` makes seven | Task 5 now also amends that assertion |

---

## D4 — Six smaller corrections

| # | Task/Step | What changed |
|---|---|---|
| h | 1 / 1 | `draft_workspace["draft"]` → `["repo"]`; the fixture's key is `repo` (`tests/substrate/draft/conftest.py:160`), so the original would `KeyError` |
| i | 1 / 8, 2 / 4 | Made the dispatch insertion point explicit: a **top-level** `if`, before the unguarded `gate` fallthrough — `gate` has no branch of its own, so anything after it never runs |
| j | 1 / 10 | README verb row now matches the existing rows' format (`panther ai-rfc` prefix, backticked command); also updates the "five `_git` copies / only three" prose the plan left stale |
| k | 1 / 3 | Withdrew the claim that the extracted finding strings are byte-identical: `cited_ids` says "at the tag", `draft_text` says "at the ref". Nothing asserts it, so it is safe — but the claim was wrong |
| l | 3 / 5 | Added the missing `import os` and `OPTIONAL`/`is_optional` imports for `pipeline/cli.py` |
| m | 5, 6 | `--toolchain`'s default cannot be "resolved after `_add_root`" (that only adds a `--root` defaulting to `None`; `root` is resolved in `main()`). Now `default=None`, resolved in the dispatch, following `--baseline`'s precedent |
| n | 8 | `all("FROZEN-MARKER 2" in task …)` fails on the first of two clusters (`wide_pristine`'s window is `(1, 2)`); now asserts each session carries **its own** ordinal. Also: importing `per_cluster_campaign` into `test_runner.py` requires importing `wide_pristine` too, or collection fails |
| o | 5 | `tests/experiment/test_config.py` has no `import hashlib`; the new test needs it |

---

## D5 — SP1 produced no deviation log

**Plan said.** Phase 1 reads the preceding plan's `<plan>-deviations.md`.

**Code showed.** No `*-deviations.md` exists beside any plan; SP1's plan predates the convention.

**What I did.** Substituted the submodule log `26e522a..abc07a3` (eleven commits, Tasks 1–6 plus two
style/doc commits) and diffed SP1's File Structure against the landed `ls`. Also noted for whoever
finishes SP1: **Task 8 (push) has not run** — the submodule has 77 unpushed commits on `main`.
