# `ai_rfc` whole-codebase code review

**Date:** 2026-09-02 · **Branch:** `feat/arfc-pipeline-and-runtime-anchors`, 162 commits
ahead of `production`, no PR · **Plan:** `docs/superpowers/plans/2026-09-02-ai-rfc-code-review.md`

This reviews all 18,443 lines of the `ai_rfc` substrate across both repositories — the
PANTHER-side package (55 files, 6,933 LOC) and the `harness/` git submodule (59 files,
11,510 LOC, pinned at `0b62bf3`) — plus both test trees. It answers three questions: is
the code sound, is technical debt hiding in it, and are the commands and features
finished.

Three decisions frame it. Both repositories are reviewed, but **fixes may land only on
the PANTHER side**, because the submodule's strings are the completed pilot's instrument.
This run **stops at the report**; no source file is edited. And **registered gaps count as
debt** rather than as accepted design, so the prose register is itself under review.

Severity throughout follows one rule: a finding's *existence* is a claim about code, but
its *severity* is a claim about consequence, which usually depends on runtime state. Every
severity line therefore either names the artifact that confirmed it, or carries the check
that would settle it. There is no separate confidence field, deliberately.

## Baseline, 2026-09-02

Everything below was run in this session, in the worktree, before any reviewer read a line.

| Check | Command | Result |
|---|---|---|
| PANTHER `ai_rfc` suite | `pytest tests/unit/…/ai_rfc/ tests/unit/test_cli/test_ai_rfc_commands.py -n auto` | **390 passed**, 11 warnings, 17.26s |
| harness experiment suite | `pytest harness/experiment/tests/` | **339 passed**, 92.80s |
| harness server suite | `pytest harness/plugins/ai-rfc/server/tests/` | **40 passed**, 24.37s |
| mypy, PANTHER-side | `mypy --follow-imports=silent` on the 8 non-harness subtrees | **10 errors in 6 files**, 55 source files checked |
| mypy, whole tree | same, including `harness/` | 24 errors in 17 files, 114 checked |
| black, PANTHER-side | `black --check` on the 8 non-harness subtrees | **clean — 55 files unchanged** |
| black, whole tree | same, including `harness/` | 4 would reformat, all under `harness/` |
| flake8, PANTHER-side | `flake8 --max-line-length=88` on the 8 non-harness subtrees | **clean — 0 findings** |
| flake8, whole tree | same, including `harness/` | 49 findings, all under `harness/` |

**All three suites pass with zero failures**, totalling 769 tests.

Two invocation notes, both of which cost time to rediscover. `ruff` is *not* installed in
`.venv` — it exists only as a `.pre-commit-config.yaml:32-35` hook that fetches its own
environment, so `.venv/bin/ruff` fails outright. And `flake8` must be given
`--max-line-length=88` explicitly, because it defaults to 79 and runs at
`stages: [manual]`, so its bare output is dominated by E501s that pre-commit would never
raise.

### Three corrections to the expected baseline

**The "587" figure this review expected for the PANTHER suite was a misattribution.** It
was a cross-suite sum recorded at an earlier date, not the count of one suite. Measured
today, every suite has *grown*: 390 / 339 / 40 against the remembered 286 / 263 / 38. No
tests were lost, and nothing regressed.

**PANTHER-side formatting and linting are spotless.** All 4 black reformats and all 49
flake8 findings are inside the `harness/` submodule, a separate repository with its own
conventions that is out of scope for fixes. A single tree-wide number would have
understated the package and overstated the submodule.

**`types-PyYAML` is neither declared nor installed, and it degrades the type baseline.**
`pyproject.toml:98` declares `PyYAML>=6.0,<7.0` as a runtime dependency, but no stub
package accompanies it and `.venv` contains none. Eight of the ten PANTHER-side mypy
errors trace to this one gap: four are `Library stubs not installed for "yaml"`
(`schema.py:14`, `report.py:14`, `coverage/cli.py:11`, `draft/gate.py:18`), and four more
are `Returning Any from function declared to return "str"` at exactly the points where a
`yaml.safe_load` result is returned (`schema.py:207`, `report.py:128`,
`draft/questions.py:153`, `timeline/store.py:87`) — which is what an untyped `yaml` module
produces downstream. The consequence is that **mypy is not checking any YAML-handling path
in a package whose central artifact is a YAML manifest.** The two remaining errors are
independent: a missing annotation for `fragment` at `coverage/cli.py:109`, and one further
`Returning Any`.

SEVERITY: Important — confirmed against `pyproject.toml`, which declares `PyYAML` at line
98 with no `types-PyYAML` beside it, and against `.venv/lib/python3.10/site-packages/`,
which holds `pyyaml-6.0.3.dist-info` and no `types_pyyaml`.

## Established facts

Exploration produced six claims that were never checked, by the same agent pair that also
produced one fabricated quotation and one wrong marker count. Every row below was
re-derived by running the command shown. They are stated here as fact so that the slice
reviewers receive them as settled and spend their budget elsewhere.

| # | Claim | How it was checked | Verdict |
|---|---|---|---|
| F-1 | No `TODO`/`FIXME`/`HACK`/`XXX`/`NotImplementedError`/skip/xfail/`type: ignore` anywhere | `grep -rnE` over the package and both test trees | **Confirmed.** Zero of every one of those classes. |
| F-2 | Zero lint suppressions | same grep | **Refuted.** Seven `# noqa`, all under `harness/`, each with a stated reason. See *Debt backlog*. |
| F-3 | All 13 PANTHER-side verbs have tests | grep each verb across `tests/unit/…/ai_rfc/` | **Confirmed.** |
| F-4 | 8 of 16 MCP tools have no test at the tool boundary | grep each `ai_rfc_*` symbol across the server test tree | **Confirmed exactly.** |
| F-5 | 4 verbs have no test at either layer | grep each verb string across the server test tree | **Confirmed.** |
| F-6 | `preflight`, `render`, `workspace reseal` never reached through `cli.main` | grep `main([...])` invocations across `harness/experiment/tests/` | **Confirmed.** |
| F-7 | No flag is defined but never read | extract every `"--flag"`, then grep its `args.*` consumption | **Confirmed**, after correcting a naive check — see below. |

### F-2: the seven suppressions

`experiment/guard.py:15` (E402) · `experiment/guard.py:59` (BLE001, "blocking is the only
safe exit") · `experiment/workspace.py:126` (ANN202) · `server/tests/conftest.py:13`
(E402) · `server/cli.py:303` (BLE001, "substrate errors surface verbatim") ·
`core/claims.py:41` (ANN202) · `core/questions.py:13` (ANN202, the only one with no
stated reason).

### F-4 and F-5: the untested surfaces

The eight tools with no test at the tool boundary are `ai_rfc_status`,
`ai_rfc_corpus_query`, `ai_rfc_cluster_get`, `ai_rfc_question_draft`,
`ai_rfc_question_export`, `ai_rfc_answer_record`, `ai_rfc_gate` and
`ai_rfc_citation_gate`. Their *core* functions are tested in `test_core.py`; what is
untested is the wrapper each MCP client actually calls, and its registration through
`server.py`'s `ALL_TOOLS` loop.

Four of those are untested at the CLI layer too, so they have no test on **either**
surface a user or an agent can reach: `cluster-get`, `question-draft`, `question-export`
and `answer-record`.

SEVERITY: Important — confirmed against the server test tree, where a grep for each of
the sixteen tool symbols and each of the sixteen verb strings returns no file for these
four. `answer-record` is the load-bearing one: it is the human sign-off path, and the
package README names developer sign-off as one of only two mechanisms that can move
`checked_fraction` off zero. Both of its entry points are unexercised.

### F-6: the three unreached experiment verbs

`preflight`, `render` and `workspace reseal` have tested functions
(`test_preflight.py`, `test_render.py`, `test_workspace.py:207`) but no test that reaches
them through argparse. Only one of the three declares this: `experiment/preflight.py:1-7`
states "Nothing here runs under pytest; the pure parts are tested, the calls are made once
by hand." `render` and `workspace reseal` carry no such statement, so two of the three
gaps are undeclared.

### F-7: the correction, recorded because the naive check was wrong

A first pass extracting every `"--flag"` and grepping for `args.<flag>` reported three
unread flags: `--from`, `--json` and `--version`. All three were false positives.
`pipeline/cli.py:61,93` give `--from` and `--json` explicit `dest="start"` and
`dest="as_json"` — `from` is a Python keyword and cannot be an attribute name — and
`args.start`, `args.until` and `args.as_json` are read 3, 2 and 2 times respectively.
`--version` is `action="version"`, which argparse consumes internally. The four `dest=`
declarations PANTHER-side are `as_json`, `start`, `until` and `verb`, and every one is
read. **No flag is defined but never read.**
