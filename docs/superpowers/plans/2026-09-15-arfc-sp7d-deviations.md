# SP7d deviation log

One entry per deviation from `docs/superpowers/plans/2026-09-15-arfc-sp7d.md`.
Three fields each: what the plan said, what the code or the tool showed, what I did.

**Entry 0 — the user decisions (U1–U3), the rulings (R1–R8), the Phase 1 baselines, and the
review findings D-1 through D-45 — lives in the plan file itself**, under "Entry 0 — rulings and
decisions carried into the row" and "Measured baselines". It is recorded there rather than
duplicated here so the two cannot drift: the plan is the artifact a reviewer reads, and every
ruling is a constraint on a task in it.

**Plan-mode transplant (CLI-2's R9 / CLI-3's precedent).** The plan was written under plan mode,
which permits writing only the harness plan file. On approval it was copied **verbatim** to
`docs/superpowers/plans/2026-09-15-arfc-sp7d.md` — verified byte-identical by sha256
`86c8cb432ff6729c9ee08123135dfa438288c68403933f255abc1e6d5db45273` — this log was opened beside it,
and both were committed in PANTHER with `git add -f` **before Task 1 ran**. The single `review-plan`
invocation was made against the harness file and is **not** repeated after the transplant.

**Summary of what entry 0 settles, for a reader who wants the shape before the detail:**

- **Three user decisions (2026-09-15).** U1 takes the **union** of the spec's judge argv and the
  codebase's hardened `ClaudeCliCall.argv()`, neither being a superset of the other. U2 makes the
  before/after table's "after" column a **pilot draft re-linted by the final instrument** — which
  D44 already designates as the free old-instrument reference, so the instrument-drift confound the
  spec's re-lint rule prevents is absent, and only a content confound remains. U3 scores
  ground-truth by **anchored fact plus value match**, which yields two zero-cost REDs.
- **Eight rulings I made** (R1–R8), each with its cost if wrong. The load-bearing ones: reuse
  `ClaudeCliCall` but **not** `build_judge`, which is welded to a three-value scale (R1); the init
  assertion and cost capture go **inside** the transport (R2); lint per revision uses the **frozen**
  checkpoint manifest, never the live one (R3); and new logic is a **module, never a `cli.py`**,
  because `test_cli_conventions.py:148-178` rglobs for those (R6).
- **One spec correction (D-1).** The spec frames the blinding leak as lasting "until an API key is
  provisioned". This project never uses one, so the leak is **permanent**, and the manifest says so.
- **Forty-five findings fixed before any task ran** (D-1 … D-45): 13 Critical and 10 Warning from
  one `review-plan` invocation, plus 12 from a following adversarial re-read.
  **Five of the thirteen Criticals were REDs that could never have gone red, or could never have
  gone green** — and the adversarial re-read caught **three more of the same classes reintroduced by
  the fixes themselves** (D-34, D-35, D-36).

**Measured at the gate, not inherited.** The installed `claude` is **2.1.272** — newer than the
spec's 2.1.259, `ClaudeCliCall`'s 2.1.260 and the memory's 2.1.268 — and **all eight union flags are
accepted** (D-37). The envelope shape on 2.1.272 is **not** measured; it moved once already.

**Operational hazard noted at the Phase 0 gate.** Two peer sessions were live (`iut-ai-rfc-7f`
interactive, `cli-one-core-refactor` background). Both repositories were clean, so nothing was
attributable to them. `git status --short` is checked in both repositories immediately before every
commit, and BASE is recorded before every dispatch.

---

# Execution-phase deviations (D46 onward)

One entry per task, added as tasks run.

**Numbering, so two namespaces are not confused.** This plan's own findings are written `D-nn` with
a hyphen; the *design spec's*, which the plan quotes (`D44`, `D47`, `D52`), are written without one.
Execution-phase entries continue the plan's namespace from **D-46**, one per task, each giving what
the plan said, what the code or the tool showed, and what I did.

---

## D-46 — Task 1: the escaper the plan wrote was an enumeration where a predicate existed

**The plan said** flatten line breaks with `.replace("\n", " ")`.

**The tool showed** `ai_rfc.driver.printable` already existed — a predicate over the whole unprintable
category. Measured: every character `str.splitlines()` breaks on is `isprintable() == False`, so the
predicate covers all of them including the CR that `\n` alone leaves behind, while spaces and accented
letters pass through untouched.

**What I did** — replaced the enumeration with the predicate, and amended the plan before Task 1 ran.
This became the row's most-repeated finding: an enumeration where a predicate belongs, found roughly
seven times, the fix almost always being to delete the list rather than maintain it. A follow-on fell
out of the same rule — a docstring saying *"All three of its callers"* was itself a stale enumeration
(eight call sites in four modules), and the adopted shape was to **drop the numeral and keep the path
list**, because a numeral is an enumeration too.

**Landed:** `166e764..421e956`, 2 commits, review clean.

## D-47 — Task 2: a mutant left ten tests green, and the tests were not at fault

**The plan said** lint each revision against its own frozen checkpoint manifest (R3).

**The tool showed** worse than a wrong test. Swapping the checkpoint roots made every frozen manifest
unreadable, and all ten tests still passed — because with no manifest `draft/lint.py` returns
`"uncited": []` unconditionally. The assertion was true both when the lint was correct and when it had
no manifest at all, so it discriminated nothing.

**What I did** — rebuilt the discriminator to compare *statuses* rather than values, which differ
exactly when manifest resolution differs. This produced the row's first standing rule: **a test can
only discriminate a condition its inputs actually vary.**

**Landed:** `421e956..038bd3c`, 10 commits, review clean, 1 deferred minor.

## D-48 — Task 3: one unreadable revision aborted an entire campaign's aggregate

**The plan said** `analyze_run` gains a `quality` key; `analyze_campaign` unchanged in shape.

**The code showed** `analyze_campaign` builds its result with a dict comprehension over runs, so a
raise inside one run destroys the whole campaign's aggregate. Four instances of this one class were
found: an absent tag, a malformed revision map, a deleted map, and a `BuildError` under `--build`.

**What I did** — ruled all four the same way, **report, don't raise**, following the precedent already
at `metrics.py:308-314`. Each failure becomes a status plus an error on its own row, so the run that
failed is the one row a reader most needs. `build` defaults **off at the function level**, not merely
behind a CLI flag, because the fixture supplies a real toolchain and would otherwise clone and build
across ~8 test modules.

**Landed:** `038bd3c..070a2e7`, 7 commits, review clean.

## D-49 — Task 4: the report had to render the runs that failed to measure

**The plan said** `render_report` gains a `## Quality` section, guarded.

**The code showed** the payload carries six status/error fields, and an honest rendering needs all of
them: `None` means *unmeasured*, and only the status beside it says why. One universal was checked
rather than assumed — `cited_fraction` really is the only metric null on a row whose two statuses both
read `read`, because a fraction over zero claims is not a number.

**What I did** — kept one uniform rule, ***`None` means unmeasured, everywhere in this payload***,
rather than grouping fields by measuredness. In the rendered table the em dash beside a measured `0`
is what tells a reader the zero was real.

**Landed:** `070a2e7..300969d`, 17 commits, review clean, 2 deferred minors.

## D-50 — Task 5: a fake that cannot lie cannot test an assertion

**The plan said** port the argv-derived init preamble so the stub stops emitting a hardcoded
`tools: []`.

**The tool showed** argv-derivation *alone* would make Task 6's surface test a permanent red:
`argv()` always passes `--tools ""`, so a purely argv-derived `tools` is `[]` forever.

**What I did** — made argv the **default** and a control-file key the **override**. Only an overridable
fake can lie the way the spec's third settled fact requires. Recorded, not fixed: the stub's init
carries eight keys where a real captured init carries six more, including `cwd` and `skills`, and
`skills` is the blinding leak's actual substance.

**Landed:** `300969d..cef8db1`, 6 commits, review clean, 5 deferred minors.

## D-51 — Task 6: hardening the transport without changing the proposer's argv

**The plan said** take the union of both argv sets (U1) and put the init assertion and cost capture
inside the transport (R2).

**The code showed** my own dispatch brief was wrong twice: I told the implementer to reuse
`stream.mcp_servers` and mirror `preflight._arm_surface_check`, and **both are built on `or []`**, with
`mcp_servers()` reading bare names as `{}`. Following my brief would have reintroduced the defect being
fixed.

**What I did** — gated the added flags on a `union_argv` argument so the proposer's argv is unchanged
(D-44), and wrote the surface check without the vacuous helpers. Added `unpriced_calls`, incremented
wherever a child ran and left no figure, while deliberately **excluding** `OSError`, where no child was
launched and nothing could have been billed — counting that would be the mirror defect.

**Landed:** `cef8db1..4d21d47`, 7 commits, review clean. Suite 2214; 3.11 260.

## D-52 — Task 7: blinding is a property of construction, not of intention

**The plan said** the judge grades the body only and verifies its own quotes.

**The code showed** "body only" is not blinded: the body carries front matter with `docname:` and an
`author:` block, and harness names appear in prose.

**What I did** — reused lint's existing front/middle splitter rather than writing a second one, and
made the harness sweep a **predicate over case and both separators** instead of a list. Stated rather
than hidden: `ai.rfc` or `airfc` would still pass, and neither is emitted anywhere in this codebase.
The neutral-directory guard is `judge_draft`'s first statement; the mutant that moves it after the call
still raises and still matches, so what kills it is asserting the stub recorded **no call**.

**Landed:** `4d21d47..12c885e`, 9 commits, review clean. Suite 2297; 3.11 270.

## D-53 — Task 8: the artifact built to prevent a measured zero was writing one

**The plan said** the verb writes a manifest recording argv, model, version, rubric hash and the
blinding regime, with D-1's correction that the leak is permanent.

**The code showed** two defects of exactly the kind this row exists to catch. A timed-out judge call
wrote `spend_usd: 0.0, unpriced_calls: 0` — *"nothing was billed, and we measured that"* — into the
very artifact whose purpose is to say what the numbers are worth. And `JUDGE_TIMEOUT_S = 120` was
derived from a 112 s measurement taken on a **short per-claim** call at default effort, while the verb
runs `--effort high` over a **166,554-byte** draft: a measurement generalised past its sample.

**What I did** — made a launched-and-unpriced call increment `unpriced_calls` on every such path, and
split the constant, raising the whole-draft budget to `JUDGE_DRAFT_TIMEOUT_S = 600` with a comment
opening **"not a measurement"**. **A real judge call against a real draft is owed before the pilot** —
that spends, so it is a Phase 5 item requiring approval, not something taken here.

**Landed:** `12c885e..a6b8284`, 6 commits, review clean, 1 residual minor. Suite 2324; 3.11 275.

## D-54 — Task 9: the dataset, a dead implementer, and a citation I "fixed" wrongly

**The plan said** author the aioquic w02-11 dataset plus `load_dataset`, with D-8's packaging entry.

**The tool showed** the implementer's session ended with a controller compaction and **never returned a
verdict**; the work sat finished but uncommitted, diagnosed by artifact. All **41 of 41** anchors
resolved against the pinned checkout, present at the pinned commit — so the anchor tests *run* rather
than skip. But the one property no test can check, the RFC doc/section mapping, had never been checked.

**What I did** — audited the citations against RFC text fetched under **U4**, in two independent passes.
Of 41 entries, **34 were right and untouched, 6 corrected, 1 statement rewritten**.

**I got one ruling wrong and shipped it.** I moved `h3-const-reserved-settings` from §11.2.2 to
§7.2.4.1 because the statement's MUST-NOT language is there. §7.2.4.1's rule is **scoped** to settings
"defined in [HTTP/2]", and Appendix A.3 enumerates those as 0x01–0x06 with `0x00` appearing **zero**
times — so the section I moved it to does not cover one fifth of the entry's own value. Reverted; the
real defect was the *statement*, which claimed the identifiers are reserved "because they were assigned
in HTTP/2" — false for 0x0, and wrong generally since 0x01 and 0x06 were HTTP/2 settings and are not
reserved in HTTP/3.

This sharpened a standing rule: **"the cited section contains the words" is not "the cited section
supports the claim"** — read the scoping clause, not only the operative one. And my mechanical checker
could not have caught it: it compares values as integers and skips non-numeric ones, reporting exactly
two entries as untested, **one of which was the defective one**. An instrument's blind spot is where a
defect hides, not evidence one is absent.

**Landed:** `a6b8284..827e820`, 5 commits.

## D-55 — Task 10: the matcher, and a metric that credited claims nobody made

**The plan said** `resolve_anchors`, `score_draft` with `recall` and `precision`, and the verb.

**The code showed** the plan left `precision` undefined, and the name was already taken — the judge
grades a 1-to-5 dimension called `precision`. Two different quantities under one word in one
experiment's output is the confusion this row exists to prevent.

**What I did** — pinned the ratio as **`claim_accuracy`**, `None` when nothing was attempted, never
0.0 or 1.0 for a draft that made no checkable claim. The implementer extended the same principle to
`recall` unprompted, reasoning that reporting 0.0 for an unscoreable dataset *"would say the draft
failed a test nobody set."*

**Two false-positive classes were then found and fixed.** A symbol matching as the **suffix of a longer
symbol** (`SETTINGS` out of `RESERVED_SETTINGS`), fixed by disambiguating against the dataset's own
symbols rather than a prefix list — which also caught four spaced-form cases my collision enumeration
had missed, because I enumerated on underscore spellings while the matcher accepts spaces too. And,
found by the reviewer and worse, **the four entries whose value is a bare decimal digit were scored by
prose making no claim**: *"The flow control window starts at 0"* credited a stream type, and *"the
CANCEL_PUSH frame has type 0x3 (RFC 9114 Section 7.2.3)"* **invented a wrong claim from the citation's
9114** — systematic in a document that cites RFC 9114 on every page. Ruled excluded: `scored` 39 → 35,
with the reason carried per entry and printed where an operator reads it.

**Landed:** `5f98392..0271c8e`, 4 commits, **+35 tests**. **Owed and recorded:** the fix-round
re-review died on a network error mid-mutation, so no independent mutation pass covered those 35 tests.

## D-56 — Task 11: the gate, and two of the plan's three stale counts were not stale

**The plan said** re-lint both sides, write the artifact, exercise every verb, run three suites, and
correct stale counts in `cli.py` and `entrypoints.py`.

**The tool showed** the plan was wrong about two of the three. Measured over the tree `build_parser()`
actually returns, `cli.py`'s "**27** leaves" and "**13** that have one" are **still 27 and 13** —
Tasks 9 and 10 added *sub-verbs under `experiment`*, not top-level commands. Applying the plan as
written would have put two wrong numbers into a docstring whose whole point is that it was measured.
Only `entrypoints.py`'s count was stale, and its companion figures with it (the list is 112 characters,
not 139). Both numerals were **dropped rather than corrected**.

**What I did** — produced `docs/experiments/2026-09-18-sp7d-instrument.md`, dated for the day it was
measured rather than the day the row opened. Every revision on both sides read (37/37 and 10/10), so
every figure is a measurement. **Zero figures, zero tables and zero structures on both sides, and both
abstracts left as the same 47-word template stub** — the design spec's opening assertion, measured.
The artifact states in prose that the two columns are **not** a controlled comparison: a 10–18× size
gap over different corpora means the citation-density difference is content drift, which only a paid
run could remove.

Three suites, mandated serial form: 3.10 **1 failed / 2372 passed / 12 skipped**, collecting **2373** —
exactly the predicted `2324 + 9 + 2 + 35 + 3`, every term attributable to a commit range. The single
failure is the known load flake, verified to pass alone in 7.94 s. 3.11 **275 / 2 / 3**, unchanged, as
expected since nothing under `optimize/` was touched. PANTHER **6 passed**, which required one command
outside the sandbox because `nicegui`'s pytest plugin binds a local port at configure time.

All three new verbs exercised at zero cost, `ground-truth` against the **real pilot draft**:
`recall: 8 of 35 scored`, `claim accuracy: 8 of 8`, six exclusions each with its reason.

**Landed:** `df7a87e`.
