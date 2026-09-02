# `ai_rfc` Provenance Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement
> this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Each task is
> independently committable and independently revertible; they share no state.

**Goal:** Close the PANTHER-side half of the provenance gap that the 2026-09-02 review
found — the absence that produced all six of its Critical findings.

**Architecture:** Five independent tasks, one per symptom, each a small change to a single
module plus its test. The diagnosis behind them is one sentence: this codebase is careful
about *statistical* honesty and has no notion of *provenance* honesty — it never asks who
produced a thing, under what code, and whether they were entitled to. Each task adds one
such question at the point where the answer is cheapest to obtain.

**Tech Stack:** Python 3.10+, pytest 8 with `pytest-xdist`, mypy, black, flake8, git.

**Spec:** `docs/research/2026-09-02-ai-rfc-code-review.md`, the review this repairs. Read
its *Confirmed defects* and *Assessment* sections before starting; every task below cites
the finding it closes.

## Global Constraints

- **Nothing under `harness/` is modified.** It is a submodule whose strings are the
  completed pilot's instrument, and the user's decision this cycle is PANTHER-side fixes
  only. Three Criticals (C-1's input half, C-5, C-6) therefore stay open by design; see
  *Deferred* at the end.
- **The harness moves under you.** During the review it advanced six commits and 1,120
  lines while being read, and another session commits to this branch. Run
  `git log -1 --format='%h %ad %s' --date=format:'%H:%M:%S'` before each task and compare
  against the previous one; treat HEAD moving between two of your own commands as
  concurrent work, not as your own doing.
- **`ruff` is not in `.venv`** — it exists only as a pre-commit hook. Use
  `.venv/bin/black --check` and `.venv/bin/flake8 --max-line-length=88`.
- **`mypy` needs `--follow-imports=silent`**, or it reports ~1,100 pre-existing errors.
- **Disable the sandbox for `pytest`** (it blocks an SSL-keylog write during collection).
- **Never run `panther docs build` or `panther_builder.py clean|package-dev`** — both
  `shutil.rmtree` the `docs/` directory, which holds 13 tracked files including this plan.
  `docs/` is gitignored, so committing anything there needs `git add -f`.
- **Do not run `python -m experiment audit|analyze` against the pilot campaign.** Per C-5
  it rewrites all six audit records with fabricated integrity violations, then crashes.
- Line length 88. Google-style docstrings. Commit format `type(scope): lowercase summary`,
  no trailing period.

**Baseline to preserve:** 390 (PANTHER) / 339 (harness experiment) / 40 (harness server).
Only the first should change, and only by the tests each task adds.

## File Structure

| File | Task | Responsibility after the change |
|---|---|---|
| `…/ai_rfc/promotion.py` | 1 | A sign-off promotes only alongside a primary anchor |
| `…/ai_rfc/schema.py` | 1, 5 | Rejects a blank signer and a duplicate requirement id |
| `…/ai_rfc/pipeline/cli.py` | 2 | Starts a run at the first stage that is not done, including re-derivable ones |
| `…/ai_rfc/draft/checkpoint.py` | 3 | Reads every input before creating anything |
| `…/ai_rfc/forge/fetch.py` | 4 | Will not follow a remote's redirect off-host, or without bound, or without timeout |
| `…/ai_rfc/coverage/cli.py` | 5 | Records the resolved sha, not the ref as typed |

---

## Task 1: A sign-off requires a primary anchor

**Closes:** the PANTHER-side half of **C-1**, plus **core-09**.

**Files:**
- Modify: `panther/plugins/services/testers/ai_rfc/promotion.py:66-73`
- Modify: `panther/plugins/services/testers/ai_rfc/schema.py` (the `signed_off_by` read)
- Test: `tests/unit/plugins/services/testers/ai_rfc/test_promotion.py`
- Test: `tests/unit/plugins/services/testers/ai_rfc/test_schema.py`

**Interfaces:**
- Consumes: `PRIMARY_EVIDENCE`, `WEAK_EVIDENCE` (already in `promotion.py:22,29`).
- Produces: no new names. `adjudicate`'s signature is unchanged; only its rule changes.

**Why this shape.** `adjudicate`'s docstring already argues that two narrative sources "may
be one person speaking twice", and the two-class route enforces that by requiring a primary
anchor. The sign-off route bypasses the same concern: one person's assertion over one ADR
anchor reaches `confirmed`. Requiring a primary anchor there too makes the rule internally
consistent, and it is the smallest change that does. No manifest under `reconstructions/`
or in any pilot workspace currently sets `signed_off_by`, so **no existing number moves.**

- [ ] **Step 1: Invert the test that pins the old behaviour**

In `test_promotion.py`, replace `test_signoff_with_an_anchor_reaches_confirmed` (lines
72-77) with two tests:

```python
def test_signoff_over_narrative_evidence_is_capped_at_inferred():
    """A sign-off is one person's assertion; so is an ADR.

    The two-class route already refuses two narrative sources on the grounds
    that they may be one person counted twice. A sign-off over narrative-only
    evidence is that same person counted twice, so it is capped the same way.
    """
    claim = _claim(
        anchors=(Anchor(EvidenceClass.ADR, "adr/0007.md"),),
        signed_off_by="dev-01",
    )
    assert adjudicate(claim) is Status.INFERRED


def test_signoff_beside_a_primary_anchor_reaches_confirmed():
    """One code anchor alone is inferred; a developer vouching for it is not."""
    claim = _claim(
        anchors=(Anchor(EvidenceClass.CODE, "src/timer.py", commit=SHA),),
        signed_off_by="dev-01",
    )
    assert adjudicate(claim) is Status.CONFIRMED
```

- [ ] **Step 2: Run them and watch the first one fail**

Run: `.venv/bin/pytest tests/unit/plugins/services/testers/ai_rfc/test_promotion.py -v`
Expected: `test_signoff_over_narrative_evidence_is_capped_at_inferred` FAILS with
`assert <Status.CONFIRMED> is <Status.INFERRED>`. The second test passes already — the
current rule confirms it for the wrong reason, which is why the first test is the gate.

- [ ] **Step 3: Change the rule**

In `promotion.py`, replace lines 66-73 — currently:

```python
    if classes <= WEAK_EVIDENCE and not claim.signed_off_by:
        return Status.INFERRED

    if claim.signed_off_by:
        return Status.CONFIRMED
```

with:

```python
    if classes <= WEAK_EVIDENCE:
        return Status.INFERRED

    if claim.signed_off_by and classes & PRIMARY_EVIDENCE:
        return Status.CONFIRMED
```

The first clause simplifies because a sign-off no longer rescues narrative-only evidence.
The second adds what the sign-off route was missing.

- [ ] **Step 4: Amend the docstring, which currently states the old rule**

`promotion.py:44-46` says a claim reaches `confirmed` "through developer sign-off, runtime
corroboration, or two distinct evidence classes at least one of which is primary". Replace
that sentence with:

```
    A claim reaches ``confirmed`` through runtime corroboration, through two
    distinct evidence classes at least one of which is primary, or through
    developer sign-off **beside a primary anchor** — code or runtime, not
    somebody's account of the system. Claims resting only on decision records
    or paper prose are capped at ``inferred``, sign-off notwithstanding: a
    signature over one person's account is that person counted twice, which is
    the circularity the two-class route already refuses.
```

- [ ] **Step 5: Reject a blank signer in the schema**

`core-09` established that `signed_off_by="   "` adjudicates to `confirmed`, because the
field is stored unstripped while `text` is stripped at `schema.py:104`. Find the
`signed_off_by` read in `schema.py` and strip it, treating an all-whitespace value as
absent rather than as a signer. Add to `test_schema.py`:

```python
def test_a_whitespace_only_signer_is_not_a_signer():
    """`signed_off_by` is the strongest lever in the rule; blanks are not names."""
    with pytest.raises(SchemaError):
        load(_manifest_with(signed_off_by="   "))
```

Match `_manifest_with` to the helper `test_schema.py` already uses; if none exists, follow
the construction in `test_schema.py`'s neighbouring cases rather than inventing one.

- [ ] **Step 6: Run the whole promotion and schema suites**

```bash
.venv/bin/pytest tests/unit/plugins/services/testers/ai_rfc/test_promotion.py tests/unit/plugins/services/testers/ai_rfc/test_schema.py -v
```

Expected: all pass. `test_signoff_without_any_anchor_is_still_a_gap` (line 38) must still
pass untouched — the no-anchor gap rule is unaffected and is the property that stops this
change from being a loosening anywhere.

- [ ] **Step 7: Confirm no recorded number moved**

```bash
grep -rn "signed_off_by" reconstructions --include="*.yaml" | grep -v "null"
```

Expected: no output, as measured on 2026-09-02. If this now returns rows, a manifest
started using sign-offs since; re-adjudicate it and report the delta before committing.

- [ ] **Step 8: Commit**

```bash
git add panther/plugins/services/testers/ai_rfc/promotion.py \
        panther/plugins/services/testers/ai_rfc/schema.py \
        tests/unit/plugins/services/testers/ai_rfc/test_promotion.py \
        tests/unit/plugins/services/testers/ai_rfc/test_schema.py
git commit -m "fix(ai_rfc): a sign-off confirms only beside a primary anchor"
```

---

## Task 2: The pipeline performs the checks it claims to

**Closes: C-2.**

**Files:**
- Modify: `panther/plugins/services/testers/ai_rfc/pipeline/cli.py:147-158`
- Test: `tests/unit/plugins/services/testers/ai_rfc/pipeline/test_cli.py`

**Interfaces:**
- Consumes: `state`, `STAGES`, `Performer` — all already imported at `pipeline/cli.py:13-14`.
- Produces: no new names.

**Why this shape.** `_run` calls `next_stage(ws)` only to pick a starting ordinal.
`next_stage` skips `RECOMPUTED` stages (`state.py:307`) — correctly, because a re-derivable
stage has no doneness and would otherwise make `next_stage` never return `None`. But both
`check` and `gate` are `RECOMPUTED` (`state.py:276,279`), and they sit *before* `prose` in
the stage order. So once mining is done, `next_stage` returns `prose`, `_run` starts at
`prose`'s ordinal, immediately hits the non-deterministic boundary, and returns 0 having
performed nothing. `State.RECOMPUTED`'s own docstring says "the runner just performs it".

The fix belongs in `_run`, not in `next_stage`: the driver-facing "what is outstanding"
answer is right, and it is the *starting point* derivation that is wrong.

- [ ] **Step 1: Write the failing test**

Add to `pipeline/test_cli.py`:

```python
def test_a_default_run_performs_the_manifest_check(mined_workspace, capsys):
    """The default path must not step over the one gate that reads the manifest.

    `next_stage` skips re-derivable stages because they have no doneness; that
    is right for a driver asking what is outstanding, and wrong as a starting
    point for a run, because `check` and `gate` both sit before `prose`.
    """
    code = main([str(mined_workspace), "--json"])

    assert code == 0
    performed = json.loads(capsys.readouterr().out)["performed"]
    assert "check" in [entry["stage"] for entry in performed]
```

Use whatever mined-workspace fixture `pipeline/test_cli.py` already provides; if none
reaches the mining-done state, extend the existing fixture rather than adding a second one.

- [ ] **Step 2: Run it to verify it fails**

Run: `.venv/bin/pytest tests/unit/plugins/services/testers/ai_rfc/pipeline/test_cli.py -k performs_the_manifest_check -v`
Expected: FAIL — `performed` is `[]`, because the run starts at `prose` and stops at the
boundary.

- [ ] **Step 3: Derive the start from state, not from next_stage**

In `pipeline/cli.py`, replace the `if start is None:` block at lines 152-157:

```python
    if start is None:
        action = next_stage(ws)
        if action is None:
            _report("note: nothing outstanding")
            return 0
        start = action.stage.ordinal
```

with:

```python
    if start is None:
        # `next_stage` steps over re-derivable stages, which is right for a
        # driver asking what is outstanding and wrong as a starting point: both
        # `check` and `gate` are re-derivable and both sit before `prose`, so
        # starting where `next_stage` points skips them. A run begins at the
        # first stage that is not done, and performs whatever it passes over.
        outstanding = [
            entry
            for entry in state(ws)
            if entry.stage.name != "forge" and entry.state is not State.DONE
        ]
        if not outstanding:
            _report("note: nothing outstanding")
            return 0
        start = outstanding[0].stage.ordinal
```

Add `State` to the `.state` import on line 14.

- [ ] **Step 4: Run the pipeline suite**

Run: `.venv/bin/pytest tests/unit/plugins/services/testers/ai_rfc/pipeline/ -v`
Expected: all pass, including the new test. If `test_status_reports_the_next_action` or any
sibling fails, check it is asserting on `pipeline status` rather than `run` — `next_stage`
itself is unchanged and `status` output must not move.

- [ ] **Step 5: Prove it end to end, both ways**

Build a workspace whose manifest holds a claim with `status: confirmed` resting on a single
ADR anchor, then:

```bash
.venv/bin/python -m panther.plugins.services.testers.ai_rfc.pipeline run WS --strict
.venv/bin/python -m panther.plugins.services.testers.ai_rfc.pipeline run WS --from check --strict
```

Expected: **both now exit 3.** Before this change the first exited 0. That difference is
the whole defect, and it is the only check that proves the fix.

- [ ] **Step 6: Commit**

```bash
git add panther/plugins/services/testers/ai_rfc/pipeline/cli.py \
        tests/unit/plugins/services/testers/ai_rfc/pipeline/test_cli.py
git commit -m "fix(ai_rfc): a default pipeline run performs the manifest check"
```

---

## Task 3: A failed checkpoint leaves nothing behind

**Closes: C-3.**

**Files:**
- Modify: `panther/plugins/services/testers/ai_rfc/draft/checkpoint.py:65-97`
- Test: `tests/unit/plugins/services/testers/ai_rfc/draft/test_checkpoint.py`

**Interfaces:** none new.

**Why this shape.** `write_checkpoint` reads the manifest and the cluster row up front, but
reads `timeline.json` only at the end, for `timeline_sha256`. The directory is created at
`:74` and `manifest.yaml` written at `:77`, so an unreadable `timeline.json` raises after
both. The write-once guard at `:69` then refuses the retry forever, and
`state.py:221-224` counts the bare directory as unfrozen and routes the operator back into
the stage that will refuse them. Recovery is an undocumented `rm -rf`.

Reading every input before creating anything is a smaller change than writing to a temp
directory and renaming, and it fixes the whole class rather than this one path.

- [ ] **Step 1: Write the failing test**

```python
def test_an_unreadable_timeline_leaves_no_checkpoint_behind(draft_workspace, tmp_path):
    """A half-written checkpoint is worse than none: the write-once guard
    refuses the retry forever, and the operator has no documented recovery."""
    out = tmp_path / "checkpoints"
    (draft_workspace["timeline"] / "timeline.json").unlink()

    with pytest.raises((CheckpointError, OSError)):
        write_checkpoint(
            draft_workspace["manifest"],
            draft_workspace["timeline"],
            "c0001",
            out,
        )

    assert not (out / "c0001").exists()
```

Match the fixture keys to what `draft/conftest.py` actually returns.

- [ ] **Step 2: Run it to verify it fails**

Run: `.venv/bin/pytest tests/unit/plugins/services/testers/ai_rfc/draft/test_checkpoint.py -k unreadable_timeline -v`
Expected: FAIL — the directory exists and holds `manifest.yaml`.

- [ ] **Step 3: Read every input before creating anything**

In `checkpoint.py`, move the timeline digest above the `mkdir`. After
`row, prev_cluster_id = _cluster_row(timeline_dir, cluster_id)` at `:66`, insert:

```python
    # Every input is read before anything is created. A failure after `mkdir`
    # leaves a directory the write-once guard below then refuses forever, and
    # `pipeline status` reads it as unfrozen and routes the operator straight
    # back into the stage that will refuse them.
    timeline_sha256 = _digest_bytes((timeline_dir / "timeline.json").read_bytes())
    normalized = dump(manifest).encode()
```

Delete the later `normalized = dump(manifest).encode()` line, and replace the
`"timeline_sha256": _digest_bytes(...)` entry in the record with
`"timeline_sha256": timeline_sha256`.

- [ ] **Step 4: Run the draft suite**

Run: `.venv/bin/pytest tests/unit/plugins/services/testers/ai_rfc/draft/ -v`
Expected: all pass. The checkpoint contents must be byte-identical to before — the record's
keys and values are unchanged, only the order in which they were computed.

- [ ] **Step 5: Commit**

```bash
git add panther/plugins/services/testers/ai_rfc/draft/checkpoint.py \
        tests/unit/plugins/services/testers/ai_rfc/draft/test_checkpoint.py
git commit -m "fix(ai_rfc): read every checkpoint input before creating anything"
```

---

## Task 4: The forge will not follow a remote off-host

**Closes: C-4, S-3, S-4, and evidence-15.**

**Files:**
- Modify: `panther/plugins/services/testers/ai_rfc/forge/fetch.py:97,112,131-135,150`
- Test: `tests/unit/plugins/services/testers/ai_rfc/forge/test_fetch.py`

**Interfaces:** no new public names. `Transport` is unchanged, which is what makes the
tests injectable.

**Why this shape.** Four defects in one module, all the same shape — trusting what the
remote said. `_paginated_github` takes the next URL from the `Link` header and hands it to
`_get_json`, which attaches `Authorization` with no host check; a reviewer confirmed a
bearer token being sent to `evil.example`. The same loop has no page bound. `urlopen` has no
timeout. And 403 and 429 raise one exception type despite opposite remedies.

- [ ] **Step 1: Write the four failing tests**

```python
def test_pagination_will_not_follow_a_link_to_another_host():
    """The Link header is remote-controlled and the request carries a token."""
    calls = []

    def transport(url, headers):
        calls.append((url, headers))
        if len(calls) == 1:
            return 200, {"Link": '<https://evil.example/steal>; rel="next"'}, b"[]"
        return 200, {}, b"[]"

    with pytest.raises(ForgeError):
        _paginated_github("https://api.github.com/repos/o/p/pulls", transport, "SECRET")

    assert len(calls) == 1, "the off-host page must never be requested"


def test_pagination_is_bounded():
    """A self-referential Link header must not loop forever."""
    def transport(url, headers):
        return 200, {"Link": f'<{url}>; rel="next"'}, b"[]"

    with pytest.raises(ForgeError):
        _paginated_github("https://api.github.com/repos/o/p/pulls", transport, None)


def test_a_rate_limit_is_distinguishable_from_a_denial():
    """429 recovers by waiting; 403 does not. One type cannot say which."""
    def denied(url, headers):
        return 403, {}, b""

    def throttled(url, headers):
        return 429, {}, b""

    with pytest.raises(ForgeDenied):
        _get_json("https://api.github.com/x", denied, None)
    with pytest.raises(ForgeThrottled):
        _get_json("https://api.github.com/x", throttled, None)


def test_the_default_transport_sets_a_timeout():
    """A hung forge must not block the fetch stage forever."""
    import inspect

    source = inspect.getsource(_default_transport)
    assert "timeout=" in source
```

- [ ] **Step 2: Run them to verify they fail**

Run: `.venv/bin/pytest tests/unit/plugins/services/testers/ai_rfc/forge/test_fetch.py -v`
Expected: all four FAIL. The first fails by making a second call rather than raising.

- [ ] **Step 3: Add the host check and the page bound**

In `_paginated_github`, before following a `next` URL, compare its host to the host of the
URL the loop started from and raise `ForgeError` on a mismatch, naming both hosts. Add a
page ceiling — a module constant `_PAGE_CAP = 1000` beside `_ROW`-style constants — and
raise `ForgeError` when it is reached, so the cap announces itself rather than truncating.
Apply the same two guards to the GitLab loop at `:150`, where `int(next_page)` should also
be wrapped so a non-numeric header raises `ForgeError` rather than `ValueError`.

- [ ] **Step 4: Split the throttle from the denial**

Add `class ForgeDenied(ForgeError)` beside the existing `ForgeThrottled`, and at `:112`
raise `ForgeThrottled` for 429 and `ForgeDenied` for 403, each with the remedy that
actually applies. Update `forge/cli.py`'s handler to catch both; `cli.py:213` currently
grades on `result.throttled` and must keep grading a 429 as throttled and a 403 as denied.

- [ ] **Step 5: Give `urlopen` a timeout**

At `:97`, pass `timeout=30` with a comment naming why the value exists — a forge that
accepts the connection and never answers would otherwise block the stage indefinitely, and
`forge` is the only networked stage.

- [ ] **Step 6: Run the forge suite**

Run: `.venv/bin/pytest tests/unit/plugins/services/testers/ai_rfc/forge/ -v`
Expected: all pass, including the four new tests. Existing tests that assert on
`ForgeThrottled` for a 403 must be updated to `ForgeDenied` — that is a deliberate contract
change, not a regression.

- [ ] **Step 7: Commit**

```bash
git add panther/plugins/services/testers/ai_rfc/forge/ \
        tests/unit/plugins/services/testers/ai_rfc/forge/
git commit -m "fix(ai_rfc): the forge will not follow a remote to another host"
```

---

## Task 5: A record names what actually produced it

**Closes: evidence-04, evidence-05, and core-03.**

**Files:**
- Modify: `panther/plugins/services/testers/ai_rfc/coverage/cli.py:131`
- Modify: `panther/plugins/services/testers/ai_rfc/schema.py:141`
- Test: `tests/unit/plugins/services/testers/ai_rfc/coverage/test_propose.py:93-104`
- Test: `tests/unit/plugins/services/testers/ai_rfc/test_schema.py`

**Interfaces:** none new.

**Why this shape.** Two places record something other than what happened.
`coverage/cli.py:131` writes `"commit": args.commit` — the ref as typed — while
`propose.py:73-76` argues at length that only the resolved sha may be recorded; a run with
`--commit main` produces an artifact carrying `"commit": "main"` beside proposals pinned to
a sha. And `schema.py:141` lets `yaml.safe_load` silently keep the last of two
identically-keyed requirements, so a manifest with a duplicated id loses a claim and
`claim_count` under-reports with no diagnostic.

The existing guard for the first, `test_the_provenance_names_what_the_anchor_actually_claims`,
cannot fail: its fixture supplies an already-resolved sha, so `args.commit` and
`proposal.commit` are the same string.

- [ ] **Step 1: Make the coverage test able to fail**

In `coverage/test_propose.py`, change the existing provenance test to pass a symbolic ref
rather than the fixture's resolved sha, and assert the record holds the resolved value:

```python
def test_the_provenance_names_what_the_anchor_actually_claims(java_repo, tmp_path):
    """The fixture used to supply a resolved sha, so this could not distinguish
    the ref as typed from the commit that was resolved. It passes `HEAD` now."""
    out = tmp_path / "out"
    code = main([...,  "--commit", "HEAD", "--out", str(out)])

    assert code == 0
    record = json.loads((out / "runtime-anchors.json").read_text())
    assert record["commit"] != "HEAD"
    assert len(record["commit"]) == 40
```

Fill the elided arguments from the neighbouring tests in the same file.

- [ ] **Step 2: Add the duplicate-id test**

```python
def test_a_duplicated_requirement_id_is_refused():
    """Two claims, one id: safe_load keeps the last and the count under-reports."""
    document = (
        "requirements:\n"
        "  R1:\n"
        "    text: first\n"
        "  R1:\n"
        "    text: second\n"
    )
    with pytest.raises(SchemaError):
        load(_written(document))
```

Match `_written` to however `test_schema.py` gets a document onto disk.

- [ ] **Step 3: Run both to verify they fail**

Expected: the coverage test fails asserting `"HEAD" != "HEAD"`; the schema test fails
because `load` returns one claim instead of raising.

- [ ] **Step 4: Record the resolved sha**

At `coverage/cli.py:131`, write the resolved commit that `propose` already computed rather
than `args.commit`. If the resolved value is not in scope there, thread it out of the same
call that produced the proposals rather than resolving a second time — two resolutions of
one ref is the drift this task exists to remove.

- [ ] **Step 5: Refuse duplicate keys**

In `schema.py`, load through a `SafeLoader` subclass whose mapping constructor raises on a
repeated key, and raise `SchemaError` naming the duplicated id. A post-parse check cannot
work: `safe_load` discards the duplicate before `sorted(requirements.items())` at `:152`
can see it.

```python
class _StrictLoader(yaml.SafeLoader):
    """Refuses a duplicated mapping key.

    ``yaml.safe_load`` keeps the last of two identically-keyed entries, so a
    manifest with a repeated requirement id silently loses a claim and every
    count derived from it under-reports with no diagnostic.
    """


def _no_duplicate_keys(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise SchemaError(f"duplicated key {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicate_keys
)
```

Then replace the `yaml.safe_load` call at `:141` with `yaml.load(text, _StrictLoader)`.

- [ ] **Step 6: Run both suites**

```bash
.venv/bin/pytest tests/unit/plugins/services/testers/ai_rfc/coverage/ tests/unit/plugins/services/testers/ai_rfc/test_schema.py -v
```

Expected: all pass. Every other manifest in the suite must still load — a strict loader
that rejects a valid document would show up here immediately.

- [ ] **Step 7: Commit**

```bash
git add panther/plugins/services/testers/ai_rfc/coverage/cli.py \
        panther/plugins/services/testers/ai_rfc/schema.py \
        tests/unit/plugins/services/testers/ai_rfc/coverage/test_propose.py \
        tests/unit/plugins/services/testers/ai_rfc/test_schema.py
git commit -m "fix(ai_rfc): record the resolved commit, and refuse a duplicated id"
```

---

## Final verification

```bash
.venv/bin/pytest tests/unit/plugins/services/testers/ai_rfc/ tests/unit/test_cli/test_ai_rfc_commands.py -n auto -q
.venv/bin/mypy --follow-imports=silent panther/plugins/services/testers/ai_rfc/
.venv/bin/black --check panther/plugins/services/testers/ai_rfc/*.py panther/plugins/services/testers/ai_rfc/{coverage,draft,forge,history,pipeline,timeline,views}
.venv/bin/flake8 --max-line-length=88 panther/plugins/services/testers/ai_rfc/*.py panther/plugins/services/testers/ai_rfc/{coverage,draft,forge,history,pipeline,timeline,views}
git log --oneline -5
```

Expected: **more than 390 passing** — 390 was the baseline and this plan adds roughly eight
tests — with zero failures. `black` and `flake8` were clean PANTHER-side before this work
and must stay clean. `mypy` reported 10 errors before; the number must not rise. Five
commits, one per task.

Then re-run the review's own probe for C-2, which is the one defect a unit test can pass
while the real command still fails:

```bash
.venv/bin/python -m panther.plugins.services.testers.ai_rfc.pipeline run WS --strict
```

on a workspace whose manifest overstates a claim. Expected: exit 3, not 0.

## Self-review of this plan

**Spec coverage.** C-2, C-3 and C-4 are closed outright by Tasks 2, 3 and 4. C-1 is closed
on the PANTHER side by Task 1 — the promotion rule stops granting top status to a bare
assertion — while its input half (an empty `--quote` passing the transcript check, and
`Write` being unguarded in every arm) is in the harness and deferred below. Task 5 closes
the two provenance defects that are PANTHER-side. C-5 and C-6 are harness-only.

**Placeholders.** Three steps deliberately say "match the fixture to what the file already
provides" rather than inventing a helper — Task 1 Step 5, Task 3 Step 1, Task 5 Steps 1-2.
That is an instruction to read, not a gap: guessing a fixture's shape is how a plan produces
a test that cannot run.

**Type consistency.** `ForgeDenied` is introduced in Task 4 Step 4 and used in its Step 1
test; no other task references it. `_StrictLoader` and `_no_duplicate_keys` are Task 5's
alone. `State` is added to an existing import in Task 2 Step 3 and used one line later.

**What this plan does not do.** It adds no compatibility shim, per CLAUDE.md. Task 4's
403/429 split is a deliberate contract change and existing tests are updated rather than
kept passing alongside the old behaviour.

## Deferred, and why

All harness-side, all blocked on the main experiment run finishing, all recorded in the
review with evidence:

1. **Close C-1 at its narrow end** — the `server` reviewer's recommendation, and better
   scoped than changing the arm definitions. Two changes in one file: resolve the
   transcript path and check workspace containment at `core/questions.py:157`, and require
   a non-empty `quote` at `:163`. The `Write` grant reaches `record_answer`'s transcript
   argument, so those two lines are the shared mechanism behind both the empty-quote
   finding and the self-certifying-transcript one. This closes the chain **without**
   touching `arms.py`, which the experiment's independent variable depends on — which is
   precisely why it is the right harness-side fix to make first.
2. **Stop calling a tuple containing `Edit` and `Write` `READ_TOOLS`** (`arms.py:21`), and
   record in `enforcement.py`'s docstring which tools are therefore unconfined. This is a
   legibility fix, not a containment one: item 1 does the containing.
3. **Bind a computation to its revision** (C-5) — `load_campaign` should compare the frozen
   campaign's `git`/`prompt_sha256`/`plugin_root` against the live checkout and raise, and
   `audit_run`/`analyze_run` should refuse to overwrite a record produced under a different
   revision. Until then, do not run those verbs against the pilot.
4. **Check a question id for collision before writing** (C-6).
5. **Digest `guard.py` and `enforcement.py`, not only `guard.json`** (S-7 / runner-11).
6. **Validate that a checkpoint directory holds a manifest** (`queries.py:71-75`), which
   counts any directory as a processed cluster. Until that lands, **make the sweep part of
   the post-run audit**: this review walked all 2,052 pilot checkpoint directories and
   found every one genuine, and that sweep is the only reason the pilot's progress figures
   can be left standing. A future campaign without it would have no equivalent guarantee.

Task 1 is deliberately the PANTHER-side half of the same defence as item 1: even with the
harness input unfixed, a fabricated sign-off over narrative-only evidence no longer reaches
`confirmed`. The two together are what close C-1; either alone narrows it.
