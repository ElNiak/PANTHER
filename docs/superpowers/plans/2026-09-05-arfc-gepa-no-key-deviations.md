# GEPA-NO-KEY — deviation log

One entry per deviation: what the plan said, what the code or the tool showed, what I did.
Plan `2026-09-05-arfc-gepa-no-key.md` was drafted in plan mode on 2026-09-05 against ai_rfc
`07a02fb` / PANTHER `5f7a268b8`, approved as a draft, and adopted verbatim by the executor session
(iut-ai-rfc-a6, https://claude.ai/code/session_016hpQGFhfyBMcF2zMx1jnAU) on 2026-09-05 at
09:31 against ai_rfc `7a4d6f9` / PANTHER `1416d9a3d`. Entry 0 records the plan's own rulings;
every later entry was verified against the file or the tool before the plan was edited. Rulings
carry what they cost if wrong.

---

## D0 — The twelve rulings taken in plan mode (plan section *Rulings taken in plan mode*)

Three confirmed with the user on 2026-09-05, each a departure from the GEPA-NO-KEY design
paragraph (`2026-09-05-plan-executor-prompt.md:77`):

1. Isolation flags: the argv carries `--safe-mode --setting-sources "" --permission-mode dontAsk --tools "" --no-session-persistence` beyond the paragraph's bare `-p --output-format … --model` (measured leak on 2.1.260; Task 4's probe detects an auth failure).
2. Output format: `--output-format stream-json --verbose` parsed with the existing `stream.parse_stream` / `result_event` / `assistant_text`, not the paragraph's `text` (no parser, no error signal, no quota event).
3. Effort and timeout per role: `ClaudeCliCall` takes `effort`; the proposer inherits `--effort` and `--timeout-s`; the judge is fixed at `JUDGE_EFFORT = "low"` / `JUDGE_TIMEOUT_S = 120`; the constructor default stays `timeout_s=120`.

Nine taken by the planner alone:

4. `__call__` accepts `str | list[dict[str, Any]]` (gepa's `LanguageModel` protocol); a message list is flattened to one stdin string.
5. `__repr__` is exactly `claude-cli:<model>` (`run.py:329` records `repr()`); the class holds only `str`, `Path` and `int` attributes (`asdict` deep-copies it, `run.py:365`).
6. The five-variable environment is lifted from `preflight._base_env` into `profile.profile_env`, not copied a third time; `USER` is load-bearing.
7. The fake stage refuses any given `--reflection-lm` or `--judge-model`, not only the `claude-cli:` form.
8. The new refusals live in the pilot block before the consent print, so `--max-token-cost` beside a CLI proposer fails before `--yes` is read.
9. The consent text says "one judge call per anchored claim per evaluation", not the paragraph's "fourteen".
10. No call cap in the wrapper (gepa calls the reflection LM once per iteration; `--max-evals` bounds it). Recorded as a ruling not taken.
11. `cwd` is a required keyword argument; the CLI passes `<root>/optimize/<name>`, created lazily on the first call.
12. The stub's control channel is `$CLAUDE_CONFIG_DIR/fake-lm.json` and its record `$CLAUDE_CONFIG_DIR/fake-lm-calls/`, not an environment variable the test sets (the wrapper's environment would strip it).

---

## D1 — The dirty PANTHER tree is the SP7b peer's, under different names than the plan expected

**Plan said.** Task 0 Step 1 and Global Constraints: PANTHER `git status --short` shows only
`M docs/superpowers/plans/2026-09-03-arfc-draft-quality-sp7b.md`, the file the peer
`land-structures-registry-sp7b` holds uncommitted.

**Tool showed.** At 09:2x the peer had committed that plan file (`e10fa3625`, `1416d9a3d`) and
now holds `M docs/superpowers/plans/2026-09-03-arfc-draft-quality-sp7b-deviations.md`; the
gitlink `panther/plugins/services/testers/ai_rfc` also shows `M` because the peer's two ai_rfc
commits (`6e06ac2`, `7a4d6f9`, SP7b Task 1) are not yet bumped (recorded gitlink `07a02fb`).
`ListAgents` shows the peer busy in this checkout with nine SP7b tasks to go.

**What I did.** Attributed both lines to the peer and proceeded (not a stop). The PANTHER commit
of the plan and this log is held while the peer's deviations file shows modified. Ruling R1
(ledger): the modified gitlink alone does not block a PANTHER commit, because pre-commit's stash
runs `git diff-index --ignore-submodules`
(`.venv/lib/python3.10/site-packages/pre_commit/staged_files_only.py:54`); cost if wrong, a
re-checked-out index entry that never touches the submodule worktree. Global Constraints' peer
clause is corrected to name the deviations file and to add that the peer's SP7b Task 10 edits
`README.md`, which Task 5 also edits (ruling R3: Task 5's README anchors are sentences, not line
numbers; one factual note to the peer before Task 5 is dispatched).

---

## D2 — The flag grep prints 5, not 4

**Plan said.** Task 0 Step 2: `claude --help | grep -c -E -- '--safe-mode|--setting-sources|--tools|--no-session-persistence'` prints `4`.

**Tool showed.** On 2.1.261 it prints `5`: the four flags are documented at their own help lines
(137 `--no-session-persistence`, 206 `--safe-mode`, 219 `--setting-sources`, 250 `--tools`),
and line 192 mentions `--tools` inside another flag's description. `--permission-mode` (145),
`--effort` (77), `--verbose` (255), `--output-format` (140) and `--model` (128) are present too,
so every flag the argv test pins exists.

**What I did.** Recorded the count; changed Task 0 Step 2 to "prints `4` or more, and each flag
appears at the start of its own help line". No code impact.

---

## D3 — The baseline is 1129 + 10 on 3.10, not 1118 + 10

**Plan said.** Task 0 Step 3 expects `1118 passed, 10 skipped` and `189 passed, 2 skipped` at
`07a02fb`; the Verification section derives `1158 passed and 11 skipped` from the former.

**Tool showed.** At `7a4d6f9`: `SSLKEYLOGFILE= .venv/bin/python -m pytest tests -q -n auto -p no:cacheprovider` → **1129 passed, 10 skipped in 56.89s**; the 3.11 selection → **189 passed, 2 skipped, 2 deselected in 55.42s**. The eleven extra tests are the SP7b peer's Task 1 (its ledger records 1118 → 1127 → 1129).

**What I did.** Recorded the measured numbers in the ledger; rewrote the Verification
expectation as a delta over the measured baseline: 3.10 baseline + 40 passed and + 1 skipped
(1169 / 11 if nothing else lands), 3.11 baseline + 29 (218 / 2). Peer commits landing mid-run
move the totals again, so each task boundary attributes its delta by commit; a count is never
reconciled by skipping or weakening a test.

---

## D4 — The plan's shell variables and the gate's `$PANTHER` are spelled literal

**Plan said.** `$PY`, `$PY311`, `$PANTHER` and `AIRFC` throughout; the gate's dry pilot form
passes `--panther-repo $PANTHER`.

**Tool showed.** The worktree guard refuses a Bash command whose interpreter is a variable and
any compound command naming git (memory `feedback_worktree_guard_refuses_git_in_compound_commands`).

**What I did.** Ruling R2: every command this session and its implementers run spells the
interpreters and the worktree as literal absolute paths; the plan's text keeps the short names as
notation. Cost if wrong: none.

---

## D5 — The README paragraph after the replaced block would read as Stage `fake`

**Plan said.** Task 5 Step 3 (i): replace README `:198-212` (the two "Stage `pilot`" paragraphs)
with a bullet list ending in a "Stage `fake` sets `LITELLM_LOCAL_MODEL_COST_MAP=True` … rates
every claim itself." paragraph.

**Code showed.** README `:214-215` continues "It builds each\ndraft for real, so its
`--toolchain` record must name executables that exist:". Today "It" follows a sentence about
Stage `fake` already, but the pilot paragraph is adjacent; after the rewrite the nearest
antecedent is the whole Stage `fake` paragraph, and a rehearsal stubs the build.

**What I did.** Added to Task 5 Step 3 (i): change that opening to "A pilot builds each draft
for real, so its `--toolchain` record …". One line inside a file the task already edits.

---

## D6 — Task 1's "append the import" would place an import below code

**Plan said.** Task 1 Step 1: "Append to `tests/experiment/test_profile.py`" a block starting
with `from ai_rfc.experiment.profile import profile_env`.

**Code showed.** `tests/experiment/test_profile.py:5` already reads
`from ai_rfc.experiment.profile import init_profile, login_command`; an import appended after
the existing tests fails flake8 E402 and isort, which the task lints.

**What I did.** Task 1 Step 1 now says to add `profile_env` to the existing import line and
append only the three tests.

---

## Review record (Phase 3, 2026-09-05 09:33-09:45)

`review-plan` run once over the adopted plan at ai_rfc `7a4d6f9` → `d3c6021` (the SP7b peer's
third commit landed at 09:32:18 during the review; it touches `schema.py` and its tests, none
of this plan's files). Verified against the live code: `parse_stream` raises `ExperimentError`
on a non-JSON line (`stream.py:28-47`, so the "garbage" path works); `result_event` returns
`None` when absent (`:166`); `assistant_text` (`:401`); `build_judge`'s prompt starts with
`RUBRIC` (`judge.py:170-180`), its verdict parse yields `Judgement(id, 0.5, "stub verdict")`
(`:183-204`), and every-call-failure raises `JudgeError("… the first failure was: <str(error)>")`
(`:255-259`, so `match="exited 3: down"` holds); `anthropic_transport` raises `JudgeError`
naming `ANTHROPIC_API_KEY` at construction (`:104-108`); `_write_result` has no test caller yet
and serialises with `default=_readable` (`run.py:329, :382-384`); `RunSettings.reflection_lm:
str | Callable[[str], str]` (`:121`); `_settings` in `test_run.py:95` takes overrides and no
`root`; `_pilot` passes `--root <tmp>/root --name pilot-1` and no `--profile-dir`
(`test_cli_optimize.py:140`), so the `with_gepa` test's `cwd` and `profile_dir` expectations
hold; nothing prints to stdout before the consent block; `EFFORTS` carries `xhigh`
(`__init__.py:21`); `_base_env` has exactly one caller and `os` no other use in `preflight.py`;
`tests/experiment/__init__.py` and `optimize/__init__.py` exist for the relative conftest
imports; the fake `claude` stub uses the same `#!/usr/bin/env python3` shebang and both venvs
carry `python3`; the four pinned isolation flags plus `--permission-mode`, `--effort`,
`--verbose`, `--output-format` and `--model` are documented on 2.1.261. Siblings searched: no
second README, `pytest.ini` or conftest mirrors the edited spans; `docs/spike-s0.md` mentions
the key as history and stays. Verdict: no Critical, two Warnings (D5, D6), ready to execute.

---

## D7 — Three lint-forced edits to Task 3's verbatim snippets

**Plan said.** Task 3 Step 3 gives `claude_cli.py` verbatim with `model = value[len(PREFIX) :].strip()`; Step 1 gives `test_claude_cli.py` verbatim, importing `from dataclasses import asdict` and `from pathlib import Path`, and one assert of 91 characters.

**Tool showed.** flake8 (no repository config suppresses E203) rejects black's slice spacing; F401 on the two imports the tests never use (`asdict` appears only in a test name; `copy.deepcopy` is what the test calls); E501 on the assert.

**What I did.** Accepted the implementer's equivalents (commit `4897996`): `value.removeprefix(PREFIX).strip()` under the same `startswith` guard (Python 3.9+, the package requires 3.10); the two unused imports dropped; the assert wrapped by black. Behaviour identical; the tests pass. Ruling R7 — cost if wrong: none, the expressions are equivalent under the guard.

---

## D8 — The plan's README snippet asserts a judge cache the CLI does not wire

**Plan said.** Task 5 Step 3 (i), the `claude-cli:` bullet: "the judge cache dedups only identical
level, text and hunk triples"; the plan's own *Out of scope* section: determinism "rests on the
judge cache (not wired in the CLI, a known follow-up)".

**Code showed.** `cli.py` calls `build_judge(...)` twice with no `cache` argument, so the judge
sends one call per hunk (`judge.py`, `build_judge` docstring). Found by the whole-branch review
(Minor 5) after the implementer copied the snippet faithfully.

**What I did.** Ruling R12: the clause is replaced by "so a rerun may grade a hunk differently; no
judge cache is wired in the CLI today" in the fix wave (commit B). Cost if wrong: one README
clause. Recorded here because the defect is the plan text's, not the implementation's.

---

## D9 — Two fixes the whole-branch review asked for beyond the plan's verbatim snippets

**Plan said.** Task 3's `__call__` catches `FileNotFoundError` only, with `cwd.mkdir` outside the
`try`; a non-zero exit raises before the stream is parsed; Task 5's credential-check comment and
message (added under R9, D-less because R9 was a ruling) were written in the past tense.

**Code showed.** A non-executable `--claude-bin` (`PermissionError`) or a `cwd` that is a file
(`FileExistsError`) escaped as a raw `OSError` against the docstring's promise; a hard usage-limit
trip that exits non-zero would lose the `rate_limit_event` on stdout, the only meter the no-key
design has; the R9 wording referenced code as it used to be (style rule) and was inaccurate in the
present.

**What I did.** Rulings R10 and R11 (fix wave, commit A: `except OSError` with the `mkdir` inside
the try; lenient stdout parse on a non-zero exit with the quota suffix; the stub's `nonzero` reply
emits init + `rate_limit_event` when given `rate_limit`; four RED tests) and the present-tense
rewrite plus the README scoping (commit B). Costs if wrong: one broader except clause, one lenient
parse on an error path and one stub option, wording only. Ruling R13 records the R9 refusal as
Anthropic-specific by design.

---

## D10 — Task 5's snippet skipped the credential check for a LiteLLM proposer beside a `claude-cli:` judge

**Plan said.** Task 5 Step 3 (c): `judge = build_judge(anthropic_transport(args.judge_model))` only
when `cli_judge is None`; no other check of `ANTHROPIC_API_KEY` in the pilot block. The design
paragraph (`2026-09-05-plan-executor-prompt.md:77`): the key "is required only if some component
still names the API path".

**Code showed.** `anthropic_transport` is the package's only credential gate (`judge.py`, raises at
construction). With a `claude-cli:` judge it is never built, so a LiteLLM `--reflection-lm`
(which names the API path) passed every refusal and the consent print without a key and would have
spent subscription sessions on the seed evaluation before failing on the first proposer call.
Raised by the Task 5 implementer, confirmed Important (plan-mandated) by the Task 5 reviewer.

**What I did.** Ruling R9: the pilot block refuses, before the consent print, a LiteLLM proposer
beside a `claude-cli:` judge when the key is absent (presence check, value never printed), with a
RED test first — commit `2797df0`. The two pairings the plan's tests cover are unchanged. Not the
alternative of forbidding the pairing (the paragraph allows it with the key). Cost if wrong: one
four-line refusal and one test to remove if the user later forbids the pairing. R13 records that
the check is Anthropic-specific, as the paragraph and the plan treat the API path.

---

## D11 — The probe's stop condition did not allow for the CLI's rotating config backup

**Plan said.** Task 4 Step 2: "what must not appear is a new transcript under `projects/` … or any
other new file"; Step 3: "a new transcript under `profile/projects/` or any other new file in the
profile: stop, report".

**Tool showed.** After the two probe calls, `.claude.json` was rewritten (as the plan expects) and
`backups/.claude.json.backup.1788598226298` appeared while an older backup rotated out (entry
count 7 → 7, total files 56 → 56); `sessions/` stayed empty; nothing under `projects/`.

**What I did.** Ruling R8: the rotated backup is the CLI's launch housekeeping of the file the
plan already expects rewritten, not a persisted session artifact; not a stop. Task 4 Step 2's
paragraph now says the CLI also rotates a backup of `.claude.json` under `backups/`. Cost if
wrong: one backup file of the CLI's own config in the profile's backups directory.

## D12 — The 3.11 environment cannot live inside the worktree (found after landing, 2026-09-08)

**Plan said.** Global Constraints and the executor prompt (line 17): the 3.11 interpreter is
`.superpowers/venv-optimize/bin/python`; Verification: the 3.11 selection runs from it.

**Tool showed.** On 2026-09-08 the selection was 11 failed / 211 passed from that venv at ai_rfc
bc4a603 while 3.10 passed; `python -v -c pass` printed `Skipping hidden .pth file` for both of its
`.pth` files; `ls -lO` showed the `hidden` flag; `chflags nohidden` was reverted within a minute
(ctime 09:32:57 after a peer's repair, 09:52:31 after mine); a 90 s probe hid every `*.pth`
planted under the worktree (import line, path line, outside `site-packages/`) and none under
`$TMPDIR`; pyenv's global site-packages carry no flags. The failing gate is
`server/core/gates.py::_run` (`sys.executable -m ai_rfc.check` from the scratch workspace →
`No module named 'ai_rfc'` → `not_completed`). The 3.10 `.venv`'s `.pth` files are hidden too and
its suite passes: 3.10.12 does not honour the flag, 3.11.9 does. The process setting the flag is
not identified.

**What I did.** User ruling 2026-09-08: the venv is rebuilt at `~/ai-rfc-experiments/venv-optimize`
(pyenv 3.11.9, the old venv's `pip freeze` replayed, `pip install -e '<ai_rfc>[optimize,tests]'`,
gepa git `0632cdb`, `pip check` clean). Proven there at ai_rfc 587fcf2: 3.11 selection 222 / 2,
slow `test_run.py` 2 passed, 3.10 whole tree 1307 / 11. The in-tree venv is left in place and is
broken; every path to it in this plan (line 23, `PY311`) and in
`2026-09-05-arfc-gepa-no-key-executor-prompt.md` (line 17) is superseded by the new path, and the
`chflags` remedy recorded on 2026-09-07 is retracted. Landed: ai_rfc `587fcf2` (README +
`test_run.py` docstring), `3940b13` (README scope); PANTHER `a09530f5b` (executor prompt path and
Phase 1 checks). Cost if wrong: one venv rebuilt and one path in two documents.

**Caveat on the bump `3c103ea18`.** Its message says "Tested at 2abe8ab: 3.10 whole tree 1228 /
11 with the peer's then in-progress `tests/substrate/draft/test_cli.py` excluded". The working
tree during that run also carried the peer's uncommitted edits to `ai_rfc/draft/cli.py` and
`ai_rfc/entrypoints.py` (committed as e609cf0 at 09:30, eight minutes before the bump), so the
count is for that mixed tree, not for 2abe8ab alone. Neither module is imported by
`experiment/optimize`; the optimize evidence is unaffected. The message is not amended.
