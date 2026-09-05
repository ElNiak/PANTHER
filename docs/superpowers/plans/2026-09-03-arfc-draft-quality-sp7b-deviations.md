# SP7b — deviation log

One entry per deviation: what the plan said, what the code showed, what I did.
Plan `2026-09-03-arfc-draft-quality-sp7b.md` was written on 2026-09-03 (`bec576f39`, `55e763f08`)
against the pre-SP1, pre-SP7a tree and never reviewed against the landed code. Reviewed on
2026-09-05 against PANTHER `571cb9c87` / ai_rfc `07a02fb` (SP7a landed with D1–D38; 26 commits
since SP1 touched files the plan names) by the controller plus two read-only `opus` reviewers, one
over Tasks 1–4 and one over Tasks 5–8; every finding below was verified against the file before the
plan was edited. Rulings carry what they cost if wrong.

---

## D1 — The baseline is 1118 + 10, not SP7a's number

**Plan said.** Global Constraints and Task 0 Step 2: read the baseline from SP7a's Task 10 record
(928 + 1) and write it in.

**Code showed.** `SSLKEYLOGFILE= $PY -m pytest tests -n auto -p no:cacheprovider` at ai_rfc
`07a02fb` → **1118 passed, 10 skipped** in 99 s; PANTHER door tests 5 passed. The peer session's
optimizer tests and the post-SP7a `ff6ea7c` account for the difference.

**What I did.** Recorded the measured numbers in Global Constraints, Task 0 Step 2 and Task 10.

---

## D2 — `_manifest_text` was unreachable, mis-called, and bound a claim that does not exist

**Plan said.** Tasks 1, 3 and 4: "`_manifest_text` comes from the suite's `conftest` (C28)";
`_manifest_text()` with no argument at five sites; the `STRUCTURES` fixture and Task 3's inline
block bind `claim: spec:1.2`.

**Code showed.** `_manifest_text(with_second_claim: bool, question_id="q-001")` is a plain module
helper at `tests/substrate/draft/conftest.py:67` with a **required** first parameter; a conftest
exports fixtures, not names, and the repo's precedent is an explicit import (`test_gate.py:130`).
`tests/substrate/test_schema.py`, `test_promotion.py`, `test_report.py` and
`tests/substrate/draft/test_checkpoint.py` do not import it. The helper declares `spec:1.1` and,
with the second claim, `spec:2.1` — no `spec:1.2` — so Task 1 Step 9's own new check would have
raised `SchemaError` in three of the plan's positive tests.

**What I did.** Each module imports it (`from .draft.conftest import _manifest_text` from
`tests/substrate/`, `from .conftest import …` inside `draft/`); every call passes
`with_second_claim=`; the fixtures bind `spec:2.1`. Contract row C28 records the signature, the
declared ids and the import form.

---

## D3 — The `level` enum reaches a peer session's file, and the plan's reader list was wrong

**Plan said.** Task 1 Step 11 expected the readers of `claim.level` in `report.py`,
`draft/lint.py`'s keyword accounting, `server/core/claims.py` and "the fixtures"; Step 12 staged
only `models.py`, `schema.py` and two test modules; Step 3 never changed `RequirementClaim.level`.

**Code showed.** `draft/lint.py` reads no `claim.level` (its `BCP14_TERMS` counts prose keywords
with an eleven-term vocabulary). The real readers: `schema.py:226`, `report.py:186` (untested;
would render `Level.MUST`), and the peer session's `ai_rfc/experiment/optimize/scoring.py` at
`:265` (`claim.level not in LEVELS`, a frozenset of strings — permanently true with an enum, so
every verified claim would be rejected), `:528` and `:804` (two metrics silently zero), `:744`
(`ClaimHunk.level: str`); `judge.py:168/:178` read the hunk's string. Test side: the `_claim()`
helpers at `test_models.py:24`, `test_promotion.py:24`, `test_report.py:30` build
`RequirementClaim(level="MUST")`, so every `to_markdown` test would raise `AttributeError`. That
file belongs to the live session `gepa-optimize-ai-rfc-skills` (its last commit 07:52 the same day).

**What I did.** Asked the user; decided 2026-09-05: `RequirementClaim.level: Level` as the plan and
D52 say, and Task 1 owns the whole migration — `.value` at the four `scoring.py` sites,
`report.py`, `schema.py`, `Level.MUST` in the three fixtures, `report.py`'s row asserted — with the
peer protocol (note first, `git status` clean, hold while dirty, `--only` if a peer has staged
files) written into Task 1 and Global Constraints. Step 3 now changes the field; a "two
vocabularies" paragraph states that the manifest's `level` is D52's five and the prose count stays
eleven. Cost if the peer's file is dirty when Task 1 runs: Task 1 waits, and Tasks 2–8 behind it.

---

## D4 — Three small Task 1 defects

**Plan said.** Step 8's code uses `re.compile`; Step 10 expects `test_json_is_byte_stable` among
`test_schema.py`'s stability tests.

**Code showed.** `schema.py` never imports `re`; `test_json_is_byte_stable` is at
`tests/substrate/test_report.py:88` (the other two are `test_schema.py:114,119`).

**What I did.** Step 8 adds the import; Step 10 runs `test_report.py` too and names the location.

---

## D5 — Task 2's golden step would have failed flake8, and the root conftest does not exist

**Plan said.** Step 6 appends `from pathlib import Path` below the test functions and registers
`pytest_addoption` "in the root test conftest".

**Code showed.** No `tests/conftest.py` and no `tests/__init__.py` exist; an import below
functions is E402 and the repository has no flake8 configuration to relax it. `pytest_addoption`
in a new rootdir conftest is honoured under `--import-mode=importlib` (rootdir is the repository,
`testpaths = ["tests"]`). The renderer and reader (Steps 3–5) were traced by hand and hold: 32-bit
packing, the `(cont.)` split, the 72-column bound, pipe escaping, per-kind legends, the
round-trip identity and the three malformed-delimiter cases.

**What I did.** The import moves to the header; Step 6 says the file is new and why it works.

---

## D6 — Task 3's assertion was vacuous and its imports were missing

**Plan said.** `assert STATUS_RANK[supported] <= STATUS_RANK[stored] or supported is not None`;
`STATUS_RANK` and `load` used unimported; "Import `Manifest` and `STATUS_RANK` at the top".

**Code showed.** The right-hand disjunct is always true. `promotion.py:17` already imports both
names.

**What I did.** The test asserts `supported is min(adjudicate(c) …)` and `stored is min(c.status …)`
with the imports written out; the Step 3 sentence says nothing is to add.

---

## D7 — Task 4's tests used a cluster id the timeline does not contain, and four smaller defects

**Plan said.** `write_checkpoint(…, "c1", out)` in seven tests; `write_text` for the frozen file;
no write-once guard on the consolidation writer; Step 7 names `tests/substrate/test_completeness.py`
and `ai_rfc/completeness.py`; `requirements_digest` annotates `Manifest` unimported.

**Code showed.** `_cluster_row` raises `CheckpointError` for any id absent from `clusters.jsonl`
(`checkpoint.py:39`); the `timeline_dir` fixture's ids look like `c0001-epoch-…` and
`test_checkpoint.py:16` has `_pr_cluster_id(timeline_dir)`. `write_checkpoint` writes
`write_bytes(normalized)` (`:83`) and digests the same bytes; it guards against a second write
(`:76-80`). The completeness files live under `draft/`. `verify_checkpoint` reads only
`manifest_sha256`, so a consolidation record (no `adjudication`/`prev_cluster_id`/
`timeline_sha256`) verifies without change.

**What I did.** Every test takes its id from the timeline; the writer uses `write_bytes` and the
same guard wording as its sibling, with a test; Step 7's paths are corrected; the import is named.

---

## D8 — `run_gate` is five passes, not one loop, and the plan's insertion points did not exist

**Plan said.** Task 5 Step 6: "inside `run_gate`'s per-entry loop, after the existing checkpoint
comparisons", with `record`, `text` and a new `previous` cursor in scope; "hoist one
`draft_text` call above the checks and pass the text into `cited_ids`".

**Code showed.** `run_gate` (`gate.py:179-330`) is five separate `for entry in entries` passes:
registration (`:214`), ordinal increase with `previous_ordinal` (`:228-241`), the checkpoint pass
holding `record` and the loaded `manifest` with `continue`s at `:251/:263/:268` (`:244-275`), the
citation pass guarded by `entry.tag not in tags` and reading through `cited_ids` (`:278-293`), and
the peer session's normative-change pass (`93308a5`, `:296-329`) with its own `previous_entry`
cursor that advances unconditionally. No pass holds both a record and the text. The checkpoint
pass has no tag guard, so a hoisted `draft_text` there would raise `GateError` for a deleted tag
(`test_gate.py:33`). `cited_ids` has other callers (`completeness.py:209`, `summary.py:118`).

**What I did.** Rewrote Step 6 as five placements: the checkpoint pass fills `record_by_tag`,
`manifest_by_tag` and `frozen_by_tag`; check 8 is its own pass reading the predecessor as
`entries[index - 1]` (no new cursor); checks 9–11 sit in the citation pass, which now calls
`draft_text` once (same finding text as `cited_ids` produced) and derives citations and blocks
from one read — check 11 never depends on a checkpoint; `cited_ids` stays. Contract row C19
records the five-pass shape.

---

## D9 — Two existing passes would report every faithful consolidation

**Plan said.** Nothing: the plan added checks 8–11 and left the ordinal-increase pass and the
peer's cited-set-equality pass as they were.

**Code showed.** A consolidation carries its predecessor's cluster id (the plan's own
`_record_consolidation` writes it), so `gate.py:235` reports "cluster ordinal N does not
increase" on every consolidation; and a rendered legend table adds `` `ai_rfc:…` `` tokens, so
`gate.py:317-327` reports "cited claim set differs" on a consolidation that adds a structure. The
plan's fixtures hid both (tag `-02` sits on `-01`'s commit; every gate assertion is `any(...)`).

**What I did.** **Ruling R1.** The ordinal comparison applies to cluster rounds only (check 8
already pins a consolidation's cluster id); for `kind: consolidation` the cited-set check requires
the previous set to be a subset of the current one, per D52's "a consolidation recorded
`normative_change: false` keeps every citation". `test_a_faithful_consolidation_gates_clean` and
`test_a_consolidation_that_drops_a_citation_is_a_finding` pin both. Cost if wrong: a consolidation
that reorders clusters, or adds a citation the spec meant to forbid, passes the gate; both are
recoverable by tightening the two conditions and re-running the gate over existing revisions.

---

## D10 — The check-8 test could not reach check 8

**Plan said.** `test_a_consolidation_whose_requirements_moved_is_a_finding` edits
`consolidations/01/manifest.yaml` in place.

**Code showed.** The edit trips `verify_checkpoint` (`checkpoint.py:129`) and the checkpoint pass
`continue`s at `gate.py:263` before any later check; the only finding lacks the word
"requirements". The plan's tests also called `load_revisions`, `_append_to_draft` and
`_retag_draft_with` without importing them (`test_gate.py:6,8`).

**What I did.** The test builds the consolidation legitimately from the **first** cluster's
checkpoint (the writer accepts it: requirements equal its base) while the revision it follows is
the second cluster's, so nothing is tampered and check 8 fires. `_build_draft_workspace` returns
`first_checkpoint`/`first_cluster` beside the last pair (the fixture's locals already carry those
names); the imports are written out.

---

## D11 — Task 6's tests and its exit code

**Plan said.** Tests call bare `main([...])` and `_manifest_text()`, use `--cluster c1`, and
expect `main(...) == 2` after `_report("error: --consolidation requires --base")`; Step 5: "if
`draft` appears as one entry, no change is needed".

**Code showed.** `test_cli.py:5` imports the module and every test calls `cli.main`; the conftest
import is `git` only; `c1` is not a timeline id (the existing checkpoint test reads
`read_clusters(timeline_dir)[0]["id"]`, `test_cli.py:16`). `main`'s docstring documents 0/1/3
(`cli.py:180-183`) and `docs/parity.md:44` reserves 2 for argparse. `entrypoints.py:92-96`
enumerates the subverbs in the `draft` entry's summary. `render_all`, `STRUCTURES_FILE` and
`write_consolidation_checkpoint` were used but never imported.

**What I did.** **Ruling R2.** The usage error goes through `parser.error(...)`, so argparse itself
exits 2 and `main`'s contract stays 0/1/3; the test asserts `SystemExit` with code 2. Cost if
wrong: a caller that treats 2 as "checkpoint refused" rather than "bad invocation" — none exists.
Tests use `cli.main`, real ids and `with_second_claim=`; Step 5 adds `render` to the summary;
`entrypoints.py` joins the task's commit; the imports are named.

---

## D12 — Task 7 on the landed server

**Plan said.** Every new test imports `ai_rfc_server`; "append to `tests/server/test_revisions.py`";
`FIELDS` binds `spec:1.1`; the revision tests call `record_revision(…, "c1", …)` directly; the
guardrail runs "before writing" above the deferred import; "a cluster entry's bytes are
unchanged"; Step 5 extends an `argv` list with `ctx.timeline`; Step 7 inserts rows after
`ai_rfc_revision_tag` with real raw commands while the preamble says em dashes, and calls the
frozen surface "arm C … 18-tool"; Step 3's imports reverse the house order; Step 8 lints whole
directories.

**Code showed.** The package is `ai_rfc.server` (`test_parity.py:11`). No `test_revisions.py`
exists (revision tests are in `test_core.py` and `test_draft.py`). The server fixture manifest
holds `t:1.1` and `t:2.1` only (`server/testing.py:109,118`), so Task 1's check would refuse
`spec:1.1`. `record_revision` refuses when `checkpoints/<cluster>/checkpoint.json` is absent
(`revisions.py:41-46`) and `build_workspace` writes no checkpoints; `test_core.py:119-128`
checkpoints first. The `load_revisions` import is deferred at `:62`. `"kind": kind` added
unconditionally changes every new cluster entry's bytes. `Context` has no `timeline`
(`paths.py:24-44`); `gates.write_checkpoint` passes positional varargs to `_run` (`:45-56`). The
table's last rows are `draft_build`/`draft_lint` with `— (not available in arm C: frozen at the
pre-v2 surface, spec D42)`; `tools.py:144` states the order contract. `revisions.py:12-14` orders
`..paths` before `. import CoreError`. A directory-scoped `black ai_rfc/server` reformats three
files of pre-existing debt (SP7a D8).

**What I did.** `ai_rfc.server` everywhere; `test_revisions.py` and `test_structures.py` are
created; `FIELDS` binds `t:1.1`; the revision tests checkpoint a cluster first through the server
core; the guardrail follows the (still deferred) import. **Ruling R3:** `kind` is written on every
new entry (an entry says what it is; entries already on disk load with the default) — cost if
wrong: none, the loader tolerates both. Step 5 rewritten on `_run`'s varargs with the output root
and the sha read routed on `consolidation`; Step 7 rows go after `draft_lint` in the em-dash
convention, and the freeze is described as "arm C stays at its pre-v2 surface"; import order
fixed; lint lines name files. Contract rows C30–C32 record the fixture ids, `Context`, `_run` and
the existing verbs' flags.

---

## D13 — A consolidation revision pinned the wrong checkpoint, and the extended cores had no frontend

**Plan said.** `record_revision(…, kind="consolidation", checkpoint="consolidations/01")` reads
its sha exactly as before; Task 7 adds two tools and leaves `ai_rfc_revision_record`,
`ai_rfc_checkpoint`, `revision-record` and `checkpoint` untouched.

**Code showed.** The sha is read from `checkpoints/<cluster_id>/checkpoint.json`
(`revisions.py:41-47`), so a consolidation entry would pin the cluster's manifest and fail the
gate's digest comparison on every consolidation. D42 makes every capability one core function
behind both frontends, and the spec's consolidation round (step 6, "revision_record
kind=consolidation → commit → build → tag") records and checkpoints through the tools — with the
plan as written, SP7c could not.

**What I did.** **Ruling R4:** a consolidation entry pins `<workspace>/<checkpoint>/checkpoint.json`
and refuses a missing one by that path — cost if wrong: none observable, the gate's own comparison
is the oracle. **Ruling R5:** `ai_rfc_revision_record` gains `kind`/`checkpoint`,
`ai_rfc_checkpoint` gains `consolidation`/`base` (workspace-relative), the two `ai_rfc` verbs gain
the matching flags, and a third twin `test_consolidation_checkpoint_and_revision_parity` compares
`revisions.yaml` and `consolidations/01/checkpoint.json` byte-for-byte across arms — cost if wrong:
two optional keywords and four optional flags nobody calls, no behaviour change for existing
callers. Both are spec-mandated (D42, D48), not new features.

---

## D14 — Task 8 against the real `LintReport`, and the wrong call site

**Plan said.** `findings.append(...)` inside `lint()`; `_METRIC_KEYS` gains `"structures"` and
`"data_model_claims_unbound"`, "or if the filter reads the top level … the filter must reach into
`extra`"; the rendering is passed "in the `draft_lint` core".

**Code showed.** `lint()` constructs `LintReport(...)` directly and `findings` is a computed
property on the frozen dataclass (`lint.py:94-136`); `to_json` is `asdict` plus `findings`, so
`extra` is a top-level key; `draft_lint` (`server/core/build.py:74-104`) **shells out** to the
substrate `lint` verb and filters the report's top level with `{key: report[key] …}` (`:103`), so
adding the two names raises `KeyError` and the rendering can only be passed by
`ai_rfc/draft/cli.py`'s `lint` branch (`cli.py:288`). `Manifest.structures`/`Structure.claims`
were an unstated dependency on Task 1.

**What I did.** The findings are derived in the property from `self.extra`; `lint()` fills
`extra`. **Ruling R6 (R-C4):** `_METRIC_KEYS` gains `"extra"`, so the tool's `metrics["extra"]` is
the file's `extra` verbatim; the parity test asserts `metrics["extra"]["structures"]` — cost if
wrong: one level of nesting in the tool's return value that SP7d's instrument reads. The `lint`
verb passes `structures=render_all(manifest)`; `draft/cli.py` and `server/core/build.py` join the
task's files; the dependency is stated.

---

## D15 — Task 10's README, its siblings, the scratch path, and the two user gates

**Plan said.** "add `structure-upsert` and `draft-render` to the verb table" in `README.md`; the
protocol says "the raw arm C stays frozen at the 18-tool surface"; scratch at `/tmp/claude/mark-b`;
"bump the submodule pointer … each push confirmed with the user first".

**Code showed.** The root `README.md` has no per-verb table; its "Three entry names" table says
"eighteen" at `:62-63`; `ai_rfc/server/README.md:21,41` say "eighteen" and its module table has no
`core/structures.py` row; `ai_rfc/experiment/README.md:69` still says "the sixteen `ai_rfc_*` MCP
tools" (already stale). `README.md` was edited by the peer session at 07:47 and 07:52 on
2026-09-05. The executor prompt gates the pointer bump as well as the push on the user; while this
review ran, the peer session bumped PANTHER's gitlink `fc31396` → `07a02fb` (`3f6b738c8`, 08:05) and
revised the executor prompt (`5f7a268b8`), whose SP7b row now also says the GEPA score reads
`BCP14_TERMS` from `lint.py` — consistent with D3.

**What I did.** Step 4 names the three files and the exact lines, with the peer protocol for
`README.md`; the protocol wording says "arm C stays frozen at its pre-v2 surface"; scratch moves
to `/tmp/claude/sp7b/`; Step 6 stops and asks before the bump (after `git ls-tree HEAD`) and again
before any push.

---

## D16 — Log only: `consolidations/` is invisible to the harness audit

**Plan said.** Nothing.

**Code showed.** `ai_rfc/experiment/audit.py:150` classifies an edit under `checkpoints/` as a
register edit (the peer's anti-forgery rule) and will classify one under `consolidations/` as
`other`.

**What I did.** Nothing in this row — `audit.py` is outside the File Structure and consolidation
rounds are SP7c's; recorded here and in the plan's Execution section for SP7c's plan.

---

## D17 — Contract repairs

C4, C6 (order), C10, C11, C19, C23, C27 and C28 (signature, ids, tags) were repaired in the table
with their landed shapes; C30 (server fixture ids and the checkpoint-then-record precedent), C31
(`Context` and `_run`) and C32 (the existing verbs' flags) were added. C1–C3, C5, C7–C9, C12–C18,
C20–C22, C24–C26 and C29 hold as written; `_document`/`_normalize_and_write` are module-level
(`claims.py:60,69`), `gate` is still the unguarded fallthrough (`draft/cli.py:303`), and every
`Manifest(...)` construction site is keyword-only (`schema.py:189` plus eleven test sites).

---

## D18 — Pre-flight: the drop-a-citation test moved both tags

**Plan said.** (After D9's correction) `test_a_consolidation_that_drops_a_citation_is_a_finding`
rewrote the draft through `_retag_draft_with` and then force-moved `draft-test-spec-02`.

**Code showed.** `_retag_draft_with` (Task 5 Step 2) force-moves `draft-test-spec-01` onto the new
commit, so revisions 01 and 02 would have shared one commit and one cited set — no drop for the
gate to see; the test could not fail for its own reason.

**What I did.** The test writes, commits and moves `-02` only, leaving `-01` on the commit that
still cites `spec:2.1`. Found by the SDD pre-flight scan, fixed in the plan before Task 1 was
dispatched.

---

## D19 — Closing `level` made a peer-suite test unreachable (Task 1, ruling R7)

**Plan said.** Task 1 Step 11 (after D3): `tests/experiment/optimize/test_scoring.py:658`
"stays green unchanged"; the file was outside the task's list.

**Code showed.** `test_a_level_outside_the_bcp14_vocabulary_does_not_count` plants a claim with
`level: "OUGHT TO"` and asserts the score's `WHY_BAD_LEVEL` row. Its own helper
`_write_requirements` (`test_scoring.py:69`, `path.write_text(dump(load(path)))`) is the first
thing that loads the manifest, so with the closed enum `SchemaError` fires there and `score()` is
never reached. `WHY_BAD_LEVEL`, the `LEVELS` comparison at `scoring.py:265` and the comment at
`scoring.py:59` ("schema.load takes level as a free string") are now unreachable or false.

**What I did.** Ruling R7: the test is rewritten as
`test_a_level_outside_the_bcp14_vocabulary_is_refused_at_load`, wrapping exactly the
`_write_requirements` call in `pytest.raises(SchemaError)` and asserting the message names
`OUGHT TO` and says `permitted values are`; the planted input is unchanged; the now-unused
`WHY_BAD_LEVEL` import is dropped from the test module; the file joined Task 1's commit. The
three stale items in `scoring.py` stay (the peer session's cleanup — told twice, at dispatch and
with the facts). Cost if wrong: one rewritten test in a peer file, one commit to revert.

---

## D20 — Two interface gaps in the plan's schema code (Task 1, rulings R8 and R9)

**Plan said.** `_structure(structure_id: str, raw)` matches the id against `_STRUCTURE_ID`;
`load` builds structures in document order; the interface says "`schema.SchemaError` still
signals every failure" and the stability tests must hold.

**Code showed.** A YAML key such as `4.1:` arrives as a `float`, and `re.match` raised
`TypeError` at `schema.py:243` (RED seen). `dump` sorts every mapping (`sort_keys=True`), so a
manifest declaring two structures out of id order failed `load(dump(load(x))) == load(x)` (RED:
`['header', 'codes'] == ['codes', 'header']`).

**What I did.** R8: `_structure` type-checks the id first (signature `Any`, the value is
untyped from YAML) with the unquoted-identifier message the `_STRING_FIELDS` check already uses
for `section`/`question-id`; the test asserts `float` and `quote` because `4.1` also appears as
a section in the fixture. R9: `load` sorts the built `Structure` objects by id (after validation,
so every key is a string); `load`'s docstring states the guarantee. Landed as a second commit,
`7a4d6f9` (amended once from `e715a83` to add one assertion — the amend itself broke the no-amend rule and is noted in the ledger), because the rulings crossed the implementer's first commit. Costs: one guard line;
declaration order of structures is lost, which nothing reads.

Implementer-reported deviations also folded in: long snippet lines wrapped to `black`'s shape;
`_sequence`/`_required` defined before their callers; `isort` collapsed two pre-existing
multi-line imports in `test_report.py`/`test_schema.py` (Step 12 mandates `isort`); the two
`scoring.py` lines that would have exceeded 88 columns were hand-wrapped (no formatter on that
file; flake8 count unchanged at 1).

---

## D21 — Two more schema gaps the task review found (Task 1, ruling R10)

**Plan said.** Task 1 Step 9: `structures = tuple(_structure(id, raw) for id, raw in
(document.get("structures") or {}).items())`; Step 8: `_structure` reads only the member key its
kind sanctions (`fields` for the three field kinds, `values` for enum, `transitions` for
state-machine) and `states` for every kind.

**Code showed.** A `structures:` block written as a list or a scalar escaped `load` as
`AttributeError` (`.items()` on a non-dict; RED seen at `schema.py:349`), against the interface
"`SchemaError` signals every failure". A member key valid under another kind — `fields:` on an
enum, `states:` on a wire-format — loaded silently and was dropped or kept meaninglessly by
`dump`; because the server persists every write through `load`/`dump` (C22), the author's block is
destroyed on the next write with no diagnostic — the defect class this task exists to close, one
level down.

**What I did.** The mapping guard mirrors the `requirements` one. **Ruling R10:** `_structure`
refuses any of `fields`, `values`, `transitions`, `states` its kind does not sanction, on key
presence (an empty `fields: []` on an enum is authored confusion), before any member is parsed —
message `"<id>: a structure of kind <kind> does not take <key>"`; the empty-member message uses
the same phrasing so the article is right for every kind. Landed as `d3c6021`; suite 1131 + 10.
Cost if wrong: a manifest carrying a stray member key fails to load; no such manifest exists.
Deferred to the final review (ledger): `structures: []` still loads as empty through `or {}`;
`_structure_to_dict` gates on non-emptiness rather than kind; two parallel kind tables.

Task 1 head: `d3c6021` (three commits after `07a02fb`; the review saw the first two as a package
cut before an amend that added one assertion, then the fix commit).

---

## D22 — Task 2 as landed (`ac471bd`), and the ladder ruling

**Plan said.** Step 5's `parse_blocks` closes the marker branch with a bare `else:`; Step 8
stages `tests/substrate/draft/goldens` as a directory and names black, flake8 and mypy; the
state-machine ladder stacks each state's box in declaration order and lists the edges as text
lines below.

**Code showed.** mypy rejects the bare `else:` (`Item "None" of "Match[str] | None" has no
attribute "group"`); the row's rules forbid staging a directory; `isort --profile black` would
collapse the test module's multi-line `from ai_rfc.models import (…)` while both sibling modules
in that directory keep the same form (pre-existing debt, SP7a D8). A peer commit (`8cdf92b`,
`refactor(experiment): lift the one-shot claude environment into profile.py`) landed between the
task's BASE `d3c6021` and its commit; the peer's files were dirty in the shared tree while the
task ran and clean by its commit, so no `--only` form was needed. The ladder renders adjacent
`+------+` rules between stacked boxes with the edges as `a --event--> b` lines: plain, but
deterministic and readable; the wire-format golden reads as an RFC figure.

**What I did.** `elif end:` (behaviour-identical); goldens staged by file; isort left off for
the new test module; the review range excludes the peer's commit. **Ruling R11:** the ladder
stays as the plan drew it; a redraw is SP7c's editorial decision, to be made before any real
`structures.md` is frozen (no production checkpoint carries structures until then). Cost if
wrong: SP7c regenerates five goldens with `--update-goldens`. Suite 1152 + 10 (1131, plus the
peer's 3, plus 18).

---

## D23 — Two rendering defects in the plan's diagram code (Task 2, rulings R12–R14)

**Plan said.** Step 3's `_diagram` emits one rule above each row sized to that row and a closing
rule sized to the last row; `_rows` reads `int(field.width or 0)`; Step 8 lints with black,
flake8 and mypy.

**Code showed.** With the brief's own 48-bit fixture the rule between the full row and the
16-bit continuation was 16 bits wide, leaving the full row open on the right (probed: 32-bit top
border, 16-bit bottom); the only golden with a diagram has two full rows, which is why the goldens
hid it. A wire-format field without `width` is schema-legal (`width` is optional for every kind)
and was dropped from the diagram while the legend still listed it, shifting every later field.
`isort --profile black` would collapse the new test module's six-name import; the Global
Constraints mandate isort on a task's files and the brief's lint line omitted it.

**What I did.** **R12:** the border above row *i* is `_rule(max(bits(i-1), bits(i)))` and the
closing border `_rule(bits(last))` — the RFC convention for a full row over a partial one; the
fixture's exact 32- and 16-bit rule strings are asserted; the wire-format golden is byte-identical
(re-reviewer reconstructed the pre-fix code and reproduced the RED). **R13:** `schema.py` refuses
a `wire-format` field without `width` (message/record keep it optional; carve-out test) and the
renderer raises `ValueError` for a programmatic `Structure` that breaks the invariant. **R14:**
isort runs on the task's own files. Landed as `2e7b69b`; suite 1165 + 10 (a peer commit,
`d437a9e`, added 9 tests in between). Costs if wrong: a different partial-row look, regenerated
with `--update-goldens` before any real checkpoint; a wire-format author must size every field;
one collapsed import line. Deferred: `width=0` on a programmatic `Structure` still vanishes (the
loader rejects zero); the bit ruler is 32 wide over a partial first row; the ladder's plainness
(R11) is SP7c's editorial call.
