# SP7a — deviation log

One entry per deviation: what the plan said, what the code showed, what I did.
Anchors verified against PANTHER `b50e569d0` / ai_rfc `abc07a3` (SP1 landed 2026-09-03 19:36).
Re-verified 2026-09-04 against PANTHER `d13633459` / ai_rfc `89c4bd5` (the fix wave): entries D6–D12.

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

---

## D6 — The README verb rows lost their `panther ai-rfc` prefix in the fix wave

**Plan said.** Task 1 Step 10: the existing rows "carry a `panther ai-rfc` prefix and backtick the
whole command (`ai_rfc/README.md:104-105`)", so write `| \`panther ai-rfc draft build …\` |`; the
`_git` prose sits at `:494-495` and the README's warning at line 511. Task 2 Step 7's row was written
without backticks.

**Code showed.** ai_rfc `89c4bd5` ("document the ai-rfc door") rewrote every row to a bare `ai-rfc`
prefix, still backticking the whole command (`ai_rfc/README.md:104-105`); the duplication-table row
is at `:476`, the prose at `:493-495`, "discovered twice" at `:507` and the "Adding a subpackage" rule
at `:512`.

**What I did.** Both new rows now read `` `ai-rfc draft build …` `` / `` `ai-rfc draft lint …` `` with
the whole command backticked, and the line anchors were updated. Followed literally, the old text
would have produced the table's only `panther`-prefixed row.

---

## D7 — The root README's environment contract is prose, and it has no scaffold sentence

**Plan said.** Task 10 Step 1: add `AI_RFC_TOOLCHAIN` "to the environment-contract table" and
"replace the sentence about the draft being scaffolded from the template root".

**Code showed.** At `89c4bd5` the *Environment contract* section is one paragraph ("Two variables:
`AI_RFC_PYTHON`, … and `AI_RFC_WORKSPACE`, … Missing either fails loudly"); `README.md` contains no
sentence about scaffolding — the only such text is in `plugins/ai-rfc/skills/ai-rfc-rfc-style/SKILL.md`,
which Task 9 replaces whole.

**What I did.** Task 10 Step 1 now extends the paragraph to a third, optional variable and adds the
adopter-layout sentence plus `toolchain provision|verify` and `workspace migrate-draft` to the
*Experiment harness* paragraph's verb list.

---

## D8 — The repository is not lint-clean, so directory-scoped lint lines reach outside the task

**Plan said.** Every task's lint step ran `black <package dir> <tests dir> && flake8 … && mypy …`,
without isort.

**Code showed.** At `89c4bd5`, `pyproject.toml` configures `[tool.isort] profile = "black"` and lists
isort under `dev`, but the tree carries debt SP5 owns: `black --check ai_rfc tests` would reformat
4 files (`ai_rfc/server/cli.py`, `ai_rfc/server/core/gates.py`, `ai_rfc/server/core/questions.py`,
`tests/server/test_core.py`); `isort --check-only` flags 5 test modules
(`tests/substrate/timeline/test_build.py`, `tests/substrate/coverage/test_commit.py`,
`tests/server/test_core.py`, `tests/experiment/test_per_cluster.py`, `tests/experiment/test_workspace.py`);
`flake8 --max-line-length=88 ai_rfc tests` reports 51 findings — none under `draft/` or `pipeline/`;
`ai_rfc/experiment/render.py` 5, `ai_rfc/experiment/config.py` 2, `ai_rfc/server/core/queries.py` 1,
the rest in `experiment/{report,metrics,preflight,enforcement,audit}.py` and five experiment test
modules. A directory-scoped `black ai_rfc/server` reformats three files Task 4 does not own, and a
directory-scoped `flake8 ai_rfc/experiment` fails on old debt.

**What I did.** Added a Global Constraints bullet and rewrote every lint line to name the task's own
files, with `isort --profile black` added; where a task file already carries flake8 findings
(`config.py`: 2 in Tasks 5 and 8; `render.py`: 5 in Task 9) the line counts them and requires no
increase. Reformatting a task-owned file that was already dirty (`server/cli.py`,
`test_per_cluster.py`, `test_workspace.py`) is accepted, since the file is in the task's list.

---

## D9 — `verify()` built its scratch inside the toolchain root

**Plan said.** Task 5 Step 3: `scratch = tools / "verify"`, removed and recreated on every call.

**Code showed.** A plan defect rather than a code fact: `tools/` (`~/ai-rfc-experiments/tools`) is
read-only evidence under the executor prompt, and `init_campaign` calls `verify` on every campaign,
so every init would have written a clone and two builds into it.

**What I did.** The scratch is now a `tempfile.TemporaryDirectory`, removed on exit; `import tempfile`
added. No test asserts the scratch location.

---

## D10 — The hand-made toolchain record cannot pass the plan's `verify`, and re-provisioning changes the cache

**Plan said.** Task 5 Step 6 re-provisions the production record "so the production record is the
command's own output"; Task 10 Step 3 expects `toolchain verify --root ~/ai-rfc-experiments` to print
`ok`.

**Code showed.** The 2026-09-03 `~/ai-rfc-experiments/tools/refcache.sha256` lists absolute paths
(`<sha256>  /Users/…/.refcache/reference.….xml`), while `_digest_refcache` writes and `verify`
compares `<sha256>  <name>` — so `verify` refuses the hand-made record on format alone. The hand-made
cache holds 17 entries (13 RFCs plus `I-D.ietf-quic-qlog-main-schema`, `I-D.ietf-quic-qlog-quic-events`,
`I-D.ietf-quic-http-22`, `I-D.ietf-quic-transport-22`); `DEFAULT_REFERENCES` seeds 15 RFCs, adding
`RFC9110` and `RFC8259` (MARK's `Target.references`, absent from the hand-made cache) and no I-D (no
`Target.references` names one).

**What I did.** Recorded the dependency in Task 5 Step 6 and Task 10 Step 3. Decided with the user on
2026-09-04: re-provision as planned; the production cache becomes 15 entries and the four I-Ds survive
only in `tools.manual-2026-09-03`.

---

## D11 — Task 9's allowed-tools edit was already done by SP1

**Plan said.** Task 9 Step 3: replace the `python -m panther…` pattern in `SKILL_FRONTMATTER`'s
`allowed-tools` "if SP1 did not already".

**Code showed.** `ai_rfc/experiment/render.py:30` at `89c4bd5` already reads `Bash(python -m ai_rfc*)`.

**What I did.** Marked the step a no-op.

---

## D12 — Anchors re-verified on the fix-wave tree

The D1–D5 anchors were verified at PANTHER `b50e569d0` / ai_rfc `abc07a3`. Since then ai_rfc gained
`89c4bd5` (fix wave) and PANTHER `ddfee0af8`, `80e6a19e4`, `e22dad825`, `d13633459` and `e2f07b288`.
The only plan-named files that changed are `README.md`, `ai_rfc/README.md` and
`ai_rfc/experiment/render.py` (D6, D7, D11), plus `pyproject.toml` (D8). Spot-checked and unchanged:
`server/paths.py`'s `Context` (`workspace`, `manifest`); `pipeline/cli.py`'s `--from` (`dest="start"`)
and the forge skip at lines 185–193; `server/core/gates._run(ctx, module, *args)`; `CoreError` in
`server/core/__init__.py`; `server/cli._emit -> None` and the `gate` branch at `cli.py:283`;
`render.arm_prompt(arm, plugin_root)`; `docs/parity.md` ending with the `ai_rfc_revision_tag` row;
16 entries in `ALL_TOOLS`. Baselines re-measured on 2026-09-04: ai_rfc 808 passed in 22.9 s;
PANTHER door tests 5 passed.

Log-only observations: `test_toolchain.py`'s `provision` tests need `ruby` and `node` on `PATH`
(`shutil.which` inside `provision`) — true on this machine, a note for SP5's CI; Task 9 Step 7 and
Task 10 Step 4 clone the template from GitHub (network, no spend); the MARK `Target.references`
(`RFC9110`, `RFC8259`) are absent from the hand-made cache, which only matters to a future `prepare`
(SP7d), not to SP7a.

---

## D13 — Task 1's `test_load_toolchain_names_the_missing_key` fixture failed on the wrong key

**Plan said.** Task 1 Step 5: the fixture writes `{"template_home": "/x"}` and the test asserts
`"'make'" in str(excinfo.value)`.

**Code showed.** `Toolchain(...)`'s keyword arguments are evaluated left to right in the plan's own
Step 7 code (`template_home`, `template_commit`, `refcache`, `make`, …), so
`record["refcache"]["dir"]` raises `KeyError('refcache')` before `record["make"]["path"]` is
reached: the error named `'refcache'`, not `'make'`.

**What I did.** The implementer added `"refcache": {"dir": "/x"}` to the fixture so `make` really is
the first gap, and the assertion passes for the reason it claims. `build.py` is as the plan wrote it.

---

## D14 — The real offline stub names the refcache file; the finding now names the citation key

**Plan said.** Task 1's fixtures, Task 4's `tag_revision` test and Task 9's slot text all expect a
broken reference to be reported as the citation key (`broken reference RFC9999 (not in the
refcache)`). The Global Constraints asked for one real build against an unresolvable reference
before Task 10 to confirm the path fires.

**Code showed.** The real kramdown-rfc 1.7.43 stub reads
`*** KRAMDOWN_OFFLINE: Inserting broken reference for reference.RFC.9999.xml` — the cache file it
tried to fetch, not the key the front matter cited. `_OFFLINE_STUB` matched and the hard gate fired
(verified on 2026-09-04 with the real toolchain: `exit_code 0`, one finding), but the finding named
`reference.RFC.9999.xml`.

**What I did.** Ruling R1 (the crashed session's controller, carried out by this one):
`build.py` gained `_reference_key()`, which strips `reference.`/`.xml` and folds a numbered series
(`RFC.9999` → `RFC9999`) while leaving I-D names and bare keys unchanged, applied at both the
kramdown-rfc and xml2rfc captures; a parametrized test covers the three shapes and the real-wording
test asserts `RFC9999`. Committed separately as ai_rfc `1c289b2` on top of Task 1's `ae435fd`. Task
4's expected finding string and Task 9's prompt text are literally true because of it. Only
`_OFFLINE_STUB` has been validated against real output; `_XML2RFC_UNRESOLVED`, `_KRAMDOWN_WARNING`
and `_IDNITS_SUMMARY`, and the `lint`/`idnits` make targets, remain for Task 10 (see the ledger).

---

## D15 — RED surfaced as `ImportError`, not `ModuleNotFoundError` (cosmetic)

**Plan said.** Task 1 Step 6: every build test fails at import with
`ModuleNotFoundError: No module named 'ai_rfc.draft.build'`.

**Code showed.** The test module imports `from ai_rfc.draft import build as build_module` first,
and that form raises `ImportError: cannot import name 'build' from 'ai_rfc.draft'` for a missing
submodule. Same cause, different exception class.

**What I did.** Nothing in the code; recorded so the next plan predicts the right exception for
this import form.

---

## D16 — The scratch clone re-rooted relative paths through `git -C`

**Plan said.** Task 1 Step 7: `cloned = _git(draft_repo.parent, "clone", "-q", "--no-hardlinks",
str(draft_repo), str(scratch))`, with the note that `-C` on the parent keeps git from treating the
scratch path as inside the source repository.

**Code showed.** The task review reproduced that `git -C <dir>` re-roots every relative argument:
with a relative `draft_repo` the clone fails outright, and with an absolute `draft_repo` but a
relative `--out out/` (the natural invocation) the clone lands at `<parent>/out/build/scratch` —
a stray clone beside the draft repository, inside the workspace tree — and the verb then fails at
`checkout` with a misleading "could not check out" error. The stated rationale does not hold:
the scratch lives under `out/`, never inside the source repository. Every existing caller passes
absolute `tmp_path`-derived paths, which is why no test noticed.

**What I did.** Ruling R2: `build()` resolves `draft_repo` and `out` once at its top, and the
clone receives only absolute paths (via `_git(build_dir, "clone", …)`), so `-C` has nothing to
re-root. A RED test runs `build()` from another working directory with relative paths and asserts
the scratch lands under `out/build/scratch`. The same fix round adds the missing fake-`make` test
for the xml2rfc unresolved-request branch, which the R1 change touched without coverage.

---

## D17 — The narration detector's `break` contradicted its own test, and the count named the wrong unit

**Plan said.** Task 2 Step 3: `_narration` appends one entry per Introduction line and `break`s at
the first matching pattern; the finding reads "introduction: narrates the reconstruction (N
line(s), e.g. line X)" with N = `len(self.narration)`. Step 1's
`test_narration_is_detected_in_the_introduction_only` puts an ordinal-cluster sentence and an
added/withdrawn sentence on **one** line and asserts both patterns are reported.

**Code showed.** With the `break` the test cannot pass (one entry per line). Without it, the generic
`cluster` pattern co-fires on every ordinal-cluster line by construction (the ordinal regex requires
the word "cluster"), so `len(self.narration)` counts pattern matches, not lines: on the MARK A1 draft
121 entries over 87 distinct lines.

**What I did.** Ruling R3: entries are per (line, pattern) for the specific patterns, the generic
`cluster` pattern fires only when no specific pattern matched the line, and the finding counts
distinct lines. The brief's test passes unchanged; two tests pin the new semantics.

---

## D18 — The skeleton-stub marker never matched a wrapped abstract

**Plan said.** Task 2 Step 3: `"is_stub": STUB_ABSTRACT_MARKER in abstract_text` — a literal
substring test on the marker sentence "Each revision reflects the implementation as it stood at one
cluster". Step 6 predicts `abstract: still the skeleton stub` among the MARK draft's findings.

**Code showed.** Real drafts hard-wrap the abstract; in the MARK draft the wrap falls between "it"
and "stood", inside the marker, so the check silently never fired and Step 6 produced three of the
four predicted findings. The plan's own Task 9 skeleton wraps the sentence at the same place
("as it\nstood"), so Task 9's `is_stub is True` assertion would have failed too. The brief's `STUB`
fixture wraps outside the marker, which is why twelve green tests hid it.

**What I did.** The implementer whitespace-normalises the abstract before the check; the fix round
adds the RED test the constraints require (marker wrapped between "it" and "stood").

---

## D19 — A malformed manifest crashed `draft lint` instead of becoming a finding

**Plan said.** Task 2 Step 4: the lint branch catches `(SchemaError, OSError)` around
`load(args.manifest)`; `--manifest`'s help promises "unloadable → a finding, not an error".

**Code showed.** `ai_rfc/schema.load` calls `yaml.load` unguarded, so a YAML syntax error escapes as
`yaml.YAMLError`, which is neither. Neither CLI test passes `--manifest`, so the branch was
unreachable by the suite. The checkpoint branch of the same file carries the same pre-existing gap.

**What I did.** Ruling R4: the lint branch also catches `yaml.YAMLError`, with a CLI test on a
broken manifest. The root fix — `schema.load` wrapping `YAMLError` into `SchemaError`, which also
cures the checkpoint branch — touches `ai_rfc/schema.py`, outside this plan's File Structure, and is
deferred to the final review for the user's decision.

---

## D20 — Three number defects in the plan's lint code, fixed before Task 10 records the baseline

**Plan said.** Task 2 Step 3: the figure window slice takes `FIGURE_CITATION_WINDOW + 1` lines
while the finding says "within 3 lines"; `body = parts["middle"] + parts["back"]` after `_parts`
drops the `--- back` marker line; `_HEADING` captures a heading's trailing kramdown attribute list
as part of its title.

**Code showed.** A citation on the fourth line after a closing fence counted as within three;
every back-matter figure reported a line number one too low; `# Introduction {#intro}` read as a
missing required section and switched the narration detector off — the same false-negative class
as D18.

**What I did.** Rulings R5 and R6: the window is exactly three lines, one empty line stands in for
the dropped marker so back-matter numbers align, and a trailing `{#…}`/`{:…}` is stripped from
heading titles; each RED-first. Done in Task 2's fix round rather than the final review so Task 10's
MARK baseline is measured with the corrected instrument.

---

## D21 — A re-derivable `lint` would have run on a draft repository with no commit

**Plan said.** Task 3 Step 4: `lint` is RECOMPUTED whenever `prose` is DONE; Step 5 adds `"lint"`
to the re-derivable tuple in `pipeline/cli.py`'s `_perform_rederivable`, so a finished workspace
lints after the walk. The HEAD helper is `_draft_head`.

**Code showed.** `_prose` grades doneness from the draft repository's `.git` and `revisions.yaml`
alone; the suite's shared `finished_workspace` fixture `git init`s the draft with no commit and
asserts `next_stage(ws) is None`. Performing `lint` there makes `draft lint` print `error: …` and
return 1, which fails `test_gate_is_skipped_when_the_question_register_is_missing`'s
`"error:" not in captured.err`. Grading `lint` BLOCKED without a commit instead would break the
fixture's `next_stage` assertion.

**What I did.** Ruling R7: `_perform_rederivable` skips `lint` when the draft has no HEAD commit,
checked directly there like the existing gate guard on the question register, with a test beside
that guard's; `lint`'s state stays as the plan wrote it. The helper is public `draft_head(ws)`
because `state._build` and the CLI guard both use it.

---

## D22 — Three plan-mandated defects in the build stage's state and runner code

**Plan said.** Task 3 Step 4: `_build` reads the report with a bare `json.loads` and grades a
missing report BLOCKED ("no build report yet; run with --toolchain"); Step 5: `_build` in `run.py`
stringifies `req.toolchain` into the argv with no guard.

**Code showed.** `state.py` already has `_read_json`, whose docstring says a malformed artifact is
a stage to re-run, not an error to raise, and a tested invariant exists for the timeline; the
`State` enum defines PENDING as "not produced yet, and everything it needs is ready" — which is the
only way that branch is reached, since prose is DONE there; and `perform()`'s docstring promises a
`PipelineError` for a missing required argument, which `_forge` and `_checkpoint` honour and
`_build` did not (`--toolchain None`).

**What I did.** `_build` uses `_read_json` (an unreadable report is STALE), a missing report with
prose DONE is PENDING, and `run._build` raises `PipelineError("build needs --toolchain")`; the
plan's state test now asserts BLOCKED without prose, PENDING before a report and STALE after a
mismatching one, and a refusal test joins `test_run.py`'s existing three.

---

## D23 — A stale build was unreachable by `run --toolchain`

**Plan said.** Task 3's design: `next_stage` steps over optional stages and the runner skips them
without their flag — "one rule, two callers" — and the README sentence the task writes says the two
therefore agree.

**Code showed.** They agree on skipping, not on reaching: `_run` derives its start from
`next_stage`, which steps over `build` unconditionally, so a workspace whose only outstanding item
is a STALE or PENDING build makes `status` say so while `run --toolchain X` reports nothing
outstanding and rebuilds nothing; only `--from build` reached it. Inherited from `forge`, and fatal
to D49's purpose once a report goes stale.

**What I did.** Ruling R9: `next_stage(ws, *, enabled=())` steps over only the optional stages
whose flag was not given, and `run` passes the flags it received; `status` passes none. Forge
gets the same semantics. The README paragraph now claims exactly that.

---

## D24 — The `tag_revision` build-gate test needed a context resolved after its env

**Plan said.** Task 4 Step 1's review correction: the `workspace` fixture is a resolved `Context`,
"which is what every other test in this file passes straight into `tag_revision`, so
`resolve_context()` is unnecessary here".

**Code showed.** `Context` is frozen and the fixture resolves it before the test body runs; the
test then sets `AI_RFC_TOOLCHAIN` with `monkeypatch.setenv`, so the fixture's `ctx.toolchain` is
still `None` and the build stage the test exists to exercise never fires. The tool wrappers and the
CLI both resolve a fresh context per call, which is why they see the variable.

**What I did.** The test re-resolves the context after setting the variable and passes that to
`tag_revision`; nothing in the production code changed.

---

## D25 — The server cores read whatever report was on disk, not the one this run wrote

**Plan said.** Task 4 Step 4: `draft_build` and `draft_lint` read `out/build/build-report.json` /
`out/lint-report.json` "if `report_path.exists()`", with `findings` falling back to stderr "when no
report was written".

**Code showed.** The substrate verbs never clear an old report and abort before writing one on a
bad `--ref`, an incomplete toolchain, a clone or checkout failure, or an unreadable draft (exit 1).
After one successful run, a failed build therefore returned the previous run's `commit`, `outputs`
and `findings`, and `tag_revision`'s refusal carried `findings: []` with no reason.

**What I did.** Ruling R10: both cores unlink the previous report before running the verb, so an
existing file means this run wrote it; tests pair a stale report with a failing fake run. The
substrate-level twin (`draft/build.py` never clears `build-report.json`, so the pipeline's
`state._build` could grade a failed rebuild from the old report) lives in Task 1's file and is
deferred to the final review with the recommendation to unlink at the start of `build()`.

---

## D26 — The sealing loop shadowed `prepare()`'s `source`

**Plan said.** Task 6 Step 4 point 4: inside `prepare`, the loop over `target.references` binds
`source = record_toolchain.refcache / name` before copying each cached reference.

**Code showed.** `prepare()` already binds `source` to the substrate directory it copies from, and
reads it again afterwards for `record["source"]`; transcribed verbatim, any target declaring
references — both real targets after this task — would have recorded the last refcache file as its
source. None of the brief's tests asserted `record["source"]`.

**What I did.** The loop-local is `ref_source`; nothing else changed. The review checks the
`pristine.json` record for the real targets' `source`.

---

## D27 — Four defects in the plan's adopter-scaffold and sealing code

**Plan said.** Task 6 Step 4: `prepare` resolves and loads the toolchain and scans for uncached
references *after* the substrate copy and the scaffold; `scaffold_draft` filters `draft-*` out of the
copied `.gitignore`; Step 2's sealing test ends with a bare `verify_digest(pristine)`, and its
scaffold test asserts `"draft-*" not in ignored` against a fixture that never contains it.

**Code showed.** `load_toolchain` raises `BuildError`, which the experiment CLI does not catch, so a
stale auto-selected `<root>/tools/toolchain.json` produced a traceback; the three configuration
checks read nothing under `pristine`, so a mistyped `--toolchain` left a half-built tree that
`prepare` then refused to overwrite; `verify_digest` returns a list and never raises, so the bare
call asserted nothing; and the real template's `template/.gitignore` (checked in the toolchain
root) never lists `draft-*` — that line lived in the old library-root ignore — so the filter was
dead code guarded by a vacuous assertion, with no test proving the draft file is committed.

**What I did.** Ruling R11: `prepare` wraps `load_toolchain` into `ExperimentError`; the
configuration checks run before anything is written and the refusal tests assert no pristine
directory remains; the sealing test asserts `refcache/reference.RFC.9000.xml` and
`references.yaml` appear in `pristine.sha256` and that `verify_digest` is empty; the `draft-*`
filter is deleted and the scaffold test asserts the draft is in the commit's tree; an empty
reference list is written as `references: []`. Task 7's `_write_adopter_files` must not reintroduce
the filter.

---

## D28 — Two campaign construction sites the plan did not list needed the toolchain

**Plan said.** Task 5's files: `experiment/{toolchain,cli,config,runner,arms}.py` and
`tests/experiment/{test_toolchain,test_config,test_runner,test_arms}.py` (plus `conftest.py` for the
shared `campaign` fixture, per Step 5).

**Code showed.** `init_campaign` also runs from `tests/experiment/test_per_cluster.py:41`
(`per_cluster_campaign`, a Task 8 file in the plan) and, through the CLI, from four `campaign init`
round-trips in `tests/experiment/test_cli_campaign.py`, a module the plan's File Structure never
names. Step 4's refusal without a verified toolchain fails all of them.

**What I did.** Asked; the user allowed Task 5 to add toolchain plumbing (a record fixture and a
stubbed `verify`) to both modules, test code only, committed with Task 5's own files.

---

## D29 — The migration removed every tracked file before the network clone

**Plan said.** Task 7 Step 3: `migrate_draft` runs `git rm` per tracked non-draft file, then
`_write_adopter_files` (which clones the template) copies the three adopter files.

**Code showed.** On the real A1 draft that is 92 `git rm` subprocesses before the first network
call; a clone error or a template lacking an adopter file raised with the tree gutted and the
deletions staged, and a re-run hit the function's own dirty-tree guard.

**What I did.** Ruling R12: the adopter files are fetched into memory first
(`_fetch_adopter_files`), the removals collapse into one `git rm -q -- …` (git validates every
pathspec before removing anything), and `_write_adopter_files` only writes; `scaffold_draft` fetches
before creating `dest`. A test migrates against a template lacking `.editorconfig` and asserts the
draft is untouched.

---

## D30 — Four defects in the plan's toolchain code, and a fake runner the plan's own code crashed

**Plan said.** Task 5 Step 3: `verify` wraps only `load_toolchain` ("every failure is a reason, not
a crash"); `provision` writes the record and then self-verifies, raising on failure; Step 1's
`_fake_tools` `else` branch handles every non-make program; Step 1's refusal test asserts
`"toolchain" in str(excinfo.value)`; Step 5 says an autouse fixture stubs `verify` for the shared
campaign fixtures.

**Code showed.** Staging and `build()` failures after the load (a `BuildError` is a `RuntimeError`,
not an `ExperimentError`) escaped `toolchain verify` and `campaign init` as tracebacks; a failed
self-verify left `toolchain.json` on disk so a retry hit "provisioned once"; the refusal assertion
also matched the verify-failed message; the autouse stub patched the module global `provision`
calls, making its self-verify unreachable in `test_toolchain.py`; and `provision`'s own
`_version(run, make, "--version")` probe (no `-C`) crashed the brief's fake runner at
`argv.index("-C")`. Also found: `_version` recorded make's last banner line, and `campaign init`
resolved its default unconditionally so the "run provision once" message was unreachable.

**What I did.** Ruling R13: `verify` turns every post-load failure into a reason; a failed
self-verify unlinks the record; the gate test asserts "needs a verified toolchain"; the autouse stub
skips `test_toolchain.py`; the fake runner keys the seed build on `"txt" in argv`; `_version` takes
the first line and needs exit 0; the CLI resolves the default only when the file exists; the digest
reason names the differing entry; a committed CLI test replaces the one-off smoke check. Step 6
(scratch) was run by the controller against the landed code and succeeded: 15-entry cache,
`verify` → `ok`, and a full four-target build validated `_IDNITS_SUMMARY` against real idnits.
