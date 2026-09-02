# `ai_rfc` Provenance Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement
> this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Revision 2**, after code review. Revision 1 carried five Critical defects, one of which
> would have made the code worse rather than better. See *What review changed* at the end;
> read it before executing, because two of those defects were in tests that would have
> passed against unfixed code.

**Goal:** Close the PANTHER-side half of the provenance gap that the 2026-09-02 review
found — the absence that produced all six of its Critical findings.

**Architecture:** Five tasks, each a small change to one module plus its test. The
diagnosis behind them is one sentence: this codebase is careful about *statistical*
honesty and has no notion of *provenance* honesty — it never asks who produced a thing,
under what code, and whether they were entitled to. Each task adds one such question at
the point where the answer is cheapest to obtain.

**Tech Stack:** Python 3.10+, pytest 8 with `pytest-xdist`, mypy, black, flake8, git.

**Spec:** `docs/research/2026-09-02-ai-rfc-code-review.md`, the review this repairs. Read
its *Confirmed defects* and *Assessment* sections before starting; every task cites the
finding it closes.

## Global Constraints

- **Nothing under `harness/` is modified.** It is a submodule whose strings are the
  completed pilot's instrument, and the decision this cycle is PANTHER-side fixes only.
  Three Criticals (C-1's input half, C-5, C-6) stay open by design; see *Deferred*.
- **Tasks 1 and 5 both touch `schema.py` and `test_schema.py`, so do them in order.**
  Every other pair is independent. Revision 1 claimed all five were independently
  revertible; that was wrong.
- **The code moves under you.** During the review the harness advanced six commits and
  1,120 lines while being read, and another session commits to this branch. Run
  `git log -1 --format='%h %ad %s' --date=format:'%H:%M:%S'` before each task; treat HEAD
  moving between two of your own commands as concurrent work, not your own doing, and
  re-check any line number this plan cites before editing at it.
- **`ruff` is not in `.venv`** — it exists only as a pre-commit hook. Use
  `.venv/bin/black --check` and `.venv/bin/flake8 --max-line-length=88`.
- **`mypy` needs `--follow-imports=silent`**, or it reports ~1,100 pre-existing errors.
- **Disable the sandbox for `pytest`** (it blocks an SSL-keylog write during collection).
- **Never run `panther docs build` or `panther_builder.py clean|package-dev`** — both
  `shutil.rmtree` the `docs/` directory, which holds 13 tracked files including this plan.
  `docs/` is gitignored, so committing there needs `git add -f`.
- **Do not run `python -m experiment audit|analyze` against the pilot campaign.** Per C-5
  it rewrites all six audit records with fabricated integrity violations, then crashes.
- Line length 88. Google-style docstrings. Commit format `type(scope): lowercase summary`,
  no trailing period. No backward-compatibility shims.

**Baseline to preserve:** 390 passing in `tests/unit/plugins/services/testers/ai_rfc/`
plus `tests/unit/test_cli/test_ai_rfc_commands.py` (verified by `--collect-only`). Only
that suite should change, and only by the tests these tasks add.

## File Structure

| File | Task | Responsibility after the change |
|---|---|---|
| `…/ai_rfc/promotion.py` | 1 | A sign-off promotes only alongside a primary anchor |
| `…/ai_rfc/schema.py` | 1, 5 | Refuses a blank signer and a duplicate requirement id |
| `…/ai_rfc/pipeline/cli.py` | 2 | Performs the re-derivable checks by state, not by ordinal |
| `…/ai_rfc/draft/checkpoint.py` | 3 | Reads every input before creating anything |
| `…/ai_rfc/forge/fetch.py` | 4 | Will not follow a remote off-host, unbounded, or untimed |
| `…/ai_rfc/coverage/propose.py` | 5 | Returns the resolved sha it already computed |
| `…/ai_rfc/coverage/cli.py` | 5 | Records that sha, not the ref as typed |

---

## Task 1: A sign-off requires a primary anchor

**Closes:** the PANTHER-side half of **C-1**, plus **core-09**.

**Files:**
- Modify: `panther/plugins/services/testers/ai_rfc/promotion.py:67-71`
- Modify: `panther/plugins/services/testers/ai_rfc/schema.py` (the `signed_off_by` read)
- Test: `tests/unit/plugins/services/testers/ai_rfc/test_promotion.py`
- Test: `tests/unit/plugins/services/testers/ai_rfc/test_schema.py`

**Interfaces:** no new names. `adjudicate`'s signature is unchanged; only its rule changes.

**Why this shape.** `adjudicate`'s docstring already argues that two narrative sources "may
be one person speaking twice", and the two-class route enforces that by requiring a primary
anchor. The sign-off route bypasses the same concern: one person's assertion over one ADR
anchor reaches `confirmed`. Requiring a primary anchor there too makes the rule internally
consistent. No manifest under `reconstructions/` or in any pilot workspace sets
`signed_off_by`, so **no existing number moves.**

- [ ] **Step 1: Invert the test that pins the old behaviour**

In `test_promotion.py`, replace `test_signoff_with_an_anchor_reaches_confirmed` (line 72)
with:

```python
def test_signoff_over_narrative_evidence_is_capped_at_inferred():
    """A sign-off is one person's assertion; so is an ADR.

    The two-class route already refuses two narrative sources because they may
    be one person counted twice. A sign-off over narrative-only evidence is that
    same person counted twice, so it is capped the same way.
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

- [ ] **Step 2: Run them and watch exactly one fail**

Run: `.venv/bin/pytest tests/unit/plugins/services/testers/ai_rfc/test_promotion.py -v`
Expected: `test_signoff_over_narrative_evidence_is_capped_at_inferred` FAILS with
`assert <Status.CONFIRMED> is <Status.INFERRED>`. The second passes already — the current
rule confirms it for the wrong reason, which is why the first is the gate. **Every other
test in the file must still pass**; a reviewer traced all of them against the new rule and
only line 72's breaks.

- [ ] **Step 3: Change the rule**

In `promotion.py`, replace lines 67-71 — currently:

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

- [ ] **Step 4: Amend the docstring, which states the old rule**

`promotion.py:44-46` currently says a claim reaches `confirmed` "through developer
sign-off, runtime corroboration, or two distinct evidence classes at least one of which is
primary". Replace that sentence with:

```
    A claim reaches ``confirmed`` through runtime corroboration, through two
    distinct evidence classes at least one of which is primary, or through
    developer sign-off **beside a primary anchor** — code or runtime, not
    somebody's account of the system. A sign-off over narrative evidence alone
    is capped at ``inferred``, whether that evidence is a decision record, a
    paper or an interview: a signature over one person's account is that person
    counted twice, which is the circularity the two-class route already refuses.
```

The mention of interviews is deliberate — `EvidenceClass.INTERVIEW` is in neither
`WEAK_EVIDENCE` nor `PRIMARY_EVIDENCE` (`models.py:21,28`), so a sign-off over
`{INTERVIEW}` or `{ADR, INTERVIEW}` is now capped too, and a docstring naming only decision
records and papers would understate the change.

- [ ] **Step 5: Refuse a blank signer**

`core-09` established that `signed_off_by="   "` adjudicates to `confirmed`, because the
field is stored unstripped while `text` is stripped at `schema.py:104`. **Raise
`SchemaError`** — do not silently treat whitespace as absent. `schema.py`'s stated contract
is to refuse a malformed document rather than to repair it, and a signer is the strongest
lever in the rule.

`test_schema.py` defines no module-level helpers, so write the test self-contained, using
whatever `load`-from-disk idiom the neighbouring tests in that file already use:

```python
def test_a_whitespace_only_signer_is_refused():
    """`signed_off_by` is the strongest lever in the promotion rule.

    Blanks are not names, and `schema` refuses a malformed document rather than
    repairing it — treating whitespace as absent would silently downgrade a
    claim the author believed they had signed.
    """
    document = _valid_manifest_text().replace(
        "signed_off_by: dev-01", "signed_off_by: '   '"
    )
    with pytest.raises(SchemaError):
        load(_written(tmp_path, document))
```

Both `_valid_manifest_text` and `_written` are placeholders for whatever that file already
does — **read `test_schema.py` first and follow its existing construction**; do not add a
helper it does not have.

- [ ] **Step 6: Run both suites**

```bash
.venv/bin/pytest tests/unit/plugins/services/testers/ai_rfc/test_promotion.py tests/unit/plugins/services/testers/ai_rfc/test_schema.py -v
```

Expected: all pass. `test_signoff_without_any_anchor_is_still_a_gap` (line 38) must pass
untouched — the no-anchor gap rule is unaffected, and it is the property proving this
change is not a loosening anywhere.

- [ ] **Step 7: Confirm no recorded number moved**

```bash
grep -rn "signed_off_by" reconstructions --include="*.yaml" | grep -v "null"
```

Expected: no output, as measured on 2026-09-02. If rows appear, a manifest started using
sign-offs since; re-adjudicate and report the delta before committing.

- [ ] **Step 8: Commit**

```bash
git add panther/plugins/services/testers/ai_rfc/promotion.py \
        panther/plugins/services/testers/ai_rfc/schema.py \
        tests/unit/plugins/services/testers/ai_rfc/test_promotion.py \
        tests/unit/plugins/services/testers/ai_rfc/test_schema.py
git commit -m "fix(ai_rfc): a sign-off confirms only beside a primary anchor"
```

---

## Task 2: Perform the re-derivable checks by state, not by ordinal

**Closes: C-2.**

**Files:**
- Modify: `panther/plugins/services/testers/ai_rfc/pipeline/cli.py` (`_run`)
- Test: `tests/unit/plugins/services/testers/ai_rfc/pipeline/conftest.py` (new fixture)
- Test: `tests/unit/plugins/services/testers/ai_rfc/pipeline/test_cli.py`

**Interfaces:**
- Consumes: `state`, `State`, `BY_NAME`, `perform` — `State` must be added to the `.state`
  import at `pipeline/cli.py:14`.
- Produces: one module-private helper, `_perform_rederivable`.

**Why this shape — and why the obvious fix is a regression.** Revision 1 proposed deriving
the walk's start ordinal from `state(ws)` instead of `next_stage`. **That makes the code
worse.** `check` sits at ordinal 6 and is `RECOMPUTED` when mining is done, `BLOCKED`
otherwise — it is *never* `DONE`. So a "first stage that is not DONE" start can never
exceed 6, the walk always reaches the agent boundary `prose` at 7 and stops, and
`checkpoint`(8) and `gate`(9) become unreachable. They are reachable today under
`run --cluster <id>`, where `next_stage` skips the re-derivable `check` and returns
`checkpoint`. A second proposed fix — skipping an already-`DONE` boundary — fails
differently: `run.py:126` raises `PipelineError("checkpoint needs --cluster")` and
`cli.py:254` turns that into exit 1, so a workspace that exits 0 today would exit 1.

The working fix stops conflating two things. The stage *walk* answers "what should be done
next, and who does it"; that logic is correct and stays untouched. The re-derivable checks
are a different question — `check` and `gate` are exactly the two `RECOMPUTED` stages,
neither mutates the workspace beyond its own report, and both should run whenever their
inputs exist. Perform them by state, after the walk, and the boundary rule never has to
change.

- [ ] **Step 1: Add the fixture the test needs**

`pipeline/conftest.py` defines only `workspace` (a clone). Do **not** extend it — making
mining `DONE` there would break `test_run_chains_..._stops_at_mining` and
`test_run_json_names_where_it_halted`, which depend on mining being pending. Add a second
fixture beside it:

```python
@pytest.fixture
def mined_workspace(workspace: Path) -> Path:
    """A workspace carrying a manifest whose stored status its evidence denies.

    `check` is re-derivable and so never `DONE`; the point of this fixture is a
    workspace where the walk stops at an agent boundary while a manifest sits on
    disk overstating a claim. If `check` does not run, nothing notices.
    """
    ...
```

Fill the body by following how `test_state.py:96-105` builds a workspace with a manifest —
it is the only existing test that writes one. The manifest must hold a claim with
`status: confirmed` resting on a single ADR anchor, which `promotion.adjudicate` caps at
`inferred` (after Task 1, and today).

- [ ] **Step 2: Write the failing test**

```python
def test_a_default_run_performs_the_manifest_check(mined_workspace, capsys):
    """The default path must not step over the one gate that reads the manifest.

    `next_stage` skips re-derivable stages, which is right for a driver asking
    what is outstanding and wrong as a description of what a run performs:
    `check` sits before the `prose` boundary and `gate` after it, so the walk
    reaches neither.
    """
    code = cli.main(["run", str(mined_workspace), "--strict", "--json"])

    assert code == 3
    performed = json.loads(capsys.readouterr().out)["performed"]
    assert "check" in [entry["stage"] for entry in performed]
```

**The `"run"` verb is required** — `pipeline/cli.py:40` is
`add_subparsers(dest="verb", required=True)`, so omitting it raises `SystemExit(2)` and the
test never reaches its assertions. Revision 1 omitted it.

- [ ] **Step 3: Run it to verify it fails**

Run: `.venv/bin/pytest tests/unit/plugins/services/testers/ai_rfc/pipeline/test_cli.py -k performs_the_manifest_check -v`
Expected: FAIL with `assert 0 == 3` — the run exits 0 having performed nothing, which is
the defect.

- [ ] **Step 4: Perform the re-derivable stages after the walk**

Add to `pipeline/cli.py`:

```python
def _perform_rederivable(args, ws, performed: list[dict]) -> int:
    """Run the checks the stage walk cannot reach, and return the worst exit code.

    ``check`` and ``gate`` are the only re-derivable stages: neither records
    doneness and neither mutates the workspace beyond its own report, so both
    are safe to run whenever their inputs exist. The walk cannot reach them
    reliably — ``check`` sits at ordinal 6 but the agent boundary ``prose`` at 7
    ends the walk, and ``gate`` at 9 needs the draft ``prose`` produces — so
    they are performed by state instead.

    Args:
        args: The parsed arguments; ``strict`` decides whether findings exit 3.
        ws: The workspace to check.
        performed: The record the walk appended to; extended in place.

    Returns:
        The highest exit code any check returned, or 0.
    """
    states = {entry.stage.name: entry.state for entry in state(ws)}
    worst = 0
    for name in ("check", "gate"):
        if states.get(name) is not State.RECOMPUTED:
            continue
        if name == "gate" and states.get("prose") is not State.DONE:
            # `gate` reads the draft repository, the question register and the
            # revision log, none of which exist until `prose` has been written.
            continue
        result = perform(BY_NAME[name], ws, strict=args.strict, cluster=args.cluster)
        performed.append(
            {
                "stage": name,
                "exit_code": result.exit_code,
                "argv": list(result.argv),
            }
        )
        worst = max(worst, result.exit_code)
    return worst
```

Match `perform`'s keyword arguments to its real signature at `run.py:178` — the call above
shows the two this helper needs, and `perform` may require others with defaults.

- [ ] **Step 5: Call it on every exit path**

`_run` currently returns `_finish(...)` from three places: the boundary branch, the
stage-error branch, and the end of the loop. Restructure `_run` so the loop sets
`halted_at` and `code` and breaks, leaving **one** exit path, then:

```python
    rederived = _perform_rederivable(args, ws, performed)
    if code == 0:
        code = rederived
    return _finish(args, performed, halted_at=halted_at, code=code)
```

A stage that errored keeps its own exit code — re-derived findings must not mask a stage
failure, and a failed stage may have left the inputs the checks read in a state worth
reporting on rather than trusting.

- [ ] **Step 6: Run the pipeline suite**

Run: `.venv/bin/pytest tests/unit/plugins/services/testers/ai_rfc/pipeline/ -v`
Expected: all pass, including the new test. If `test_run_chains_..._stops_at_mining` or
`test_run_json_names_where_it_halted` fails, `_perform_rederivable` is running when it
should not — `check` is `BLOCKED`, not `RECOMPUTED`, while mining is pending.

- [ ] **Step 7: Prove it against the real command**

On the `mined_workspace` shape, from a shell:

```bash
.venv/bin/python -m panther.plugins.services.testers.ai_rfc.pipeline run WS --strict
.venv/bin/python -m panther.plugins.services.testers.ai_rfc.pipeline run WS --from check --strict
```

Expected: **both exit 3.** Before this change the first exited 0. Then confirm the
regression revision 1 would have introduced is absent:

```bash
.venv/bin/python -m panther.plugins.services.testers.ai_rfc.pipeline run WS --cluster c0001
```

Expected: whatever it did before this change, unchanged — not exit 1.

- [ ] **Step 8: Commit**

```bash
git add panther/plugins/services/testers/ai_rfc/pipeline/cli.py \
        tests/unit/plugins/services/testers/ai_rfc/pipeline/conftest.py \
        tests/unit/plugins/services/testers/ai_rfc/pipeline/test_cli.py
git commit -m "fix(ai_rfc): perform the re-derivable checks a run steps over"
```

---

## Task 3: A failed checkpoint leaves nothing behind

**Closes: C-3.**

**Files:**
- Modify: `panther/plugins/services/testers/ai_rfc/draft/checkpoint.py:65-98`
- Test: `tests/unit/plugins/services/testers/ai_rfc/draft/test_checkpoint.py`

**Interfaces:** none new.

**Why this shape.** `write_checkpoint` reads the manifest and the cluster row up front, but
reads `timeline.json` only at the end, for `timeline_sha256`. The directory is created at
`:74` and `manifest.yaml` written at `:77`, so an unreadable `timeline.json` raises after
both. The write-once guard at `:69` then refuses the retry forever, and
`state.py:221-224` counts the bare directory as unfrozen and routes the operator back into
the stage that will refuse them.

**The input that reaches the bug is `timeline.json`, not `clusters.jsonl`.** `_cluster_row`
reads `clusters.jsonl` at `:35`, before the `mkdir`; breaking that file fails early and
leaves nothing behind, which is the current correct behaviour. Revision 1's test broke the
wrong thing and would have passed against unfixed code.

- [ ] **Step 1: Write the failing test**

```python
def test_an_unreadable_timeline_leaves_no_checkpoint_behind(draft_workspace, tmp_path):
    """A half-written checkpoint is worse than none.

    The write-once guard refuses the retry forever and `pipeline status` reads
    the bare directory as unfrozen, so the operator is routed back into the
    stage that will refuse them, with no documented recovery.
    """
    out = tmp_path / "fresh-checkpoints"
    cluster_id = json.loads(
        (draft_workspace["timeline"] / "clusters.jsonl").read_text().splitlines()[0]
    )["id"]
    (draft_workspace["timeline"] / "timeline.json").unlink()

    with pytest.raises(OSError):
        write_checkpoint(
            draft_workspace["manifest"],
            draft_workspace["timeline"],
            cluster_id,
            out,
        )

    assert not (out / cluster_id).exists()
```

Three things this gets right that revision 1 did not: a **fresh** `out` directory, because
`draft_workspace` already populates its own and both clusters are checkpointed there
(`draft/conftest.py:100-114`); a **real** cluster id read from `clusters.jsonl`, because a
fake one raises at `_cluster_row` before the `mkdir`; and `timeline.json` as the broken
input. Match the fixture's dict keys to what `draft/conftest.py` actually returns.

- [ ] **Step 2: Run it to verify it fails**

Run: `.venv/bin/pytest tests/unit/plugins/services/testers/ai_rfc/draft/test_checkpoint.py -k unreadable_timeline -v`
Expected: FAIL on the final assertion — the directory exists and holds `manifest.yaml`.
If it fails earlier, on `pytest.raises`, the test is not reaching the bug; re-check that
the cluster id is real and `out` is fresh.

- [ ] **Step 3: Read every input before creating anything**

After `row, prev_cluster_id = _cluster_row(timeline_dir, cluster_id)` at `:66`, insert:

```python
    # Every input is read before anything is created. A failure after `mkdir`
    # leaves a directory the write-once guard below then refuses forever, and
    # `pipeline status` reads it as unfrozen and routes the operator straight
    # back into the stage that will refuse them.
    timeline_sha256 = _digest_bytes((timeline_dir / "timeline.json").read_bytes())
    normalized = dump(manifest).encode()
```

Delete the later `normalized = dump(manifest).encode()` line, and replace the record's
`"timeline_sha256": _digest_bytes(...)` entry with `"timeline_sha256": timeline_sha256`.

- [ ] **Step 4: Run the draft suite**

Run: `.venv/bin/pytest tests/unit/plugins/services/testers/ai_rfc/draft/ -v`
Expected: all pass. Checkpoint contents must be byte-identical to before — the record's
keys and values are unchanged, only the order in which they were computed.

- [ ] **Step 5: Commit**

```bash
git add panther/plugins/services/testers/ai_rfc/draft/checkpoint.py \
        tests/unit/plugins/services/testers/ai_rfc/draft/test_checkpoint.py
git commit -m "fix(ai_rfc): read every checkpoint input before creating anything"
```

---

## Task 4: The forge will not follow a remote off-host

**Closes: C-4, S-3, S-4, evidence-15.**

**Files:**
- Modify: `panther/plugins/services/testers/ai_rfc/forge/fetch.py:26-31,97,112,131-136,145`
- Test: `tests/unit/plugins/services/testers/ai_rfc/forge/test_fetch.py`

**Interfaces:**
- Produces: `ForgeDenied`, a new exception. **It must inherit `ForgeAuthError`, not
  `ForgeError`** — see below.

**Why this shape.** Four defects, all the same: trusting what the remote said.
`_paginated_github` takes the next URL from the `Link` header and hands it to `_get_json`,
which attaches `Authorization` with no host check; a reviewer confirmed a bearer token sent
to `evil.example`. The loop has no page bound. `urlopen` has no timeout. And 403 and 429
raise one type despite opposite remedies.

**The inheritance is load-bearing.** The hierarchy is
`ForgeError` → `ForgeAuthError` → `ForgeThrottled`, and the three sub-fetch handlers at
`:291,311,341` catch `ForgeAuthError`, increment `denied`, then set
`throttled |= isinstance(error, ForgeThrottled)`. A `ForgeDenied(ForgeError)` would escape
those handlers and abort the whole fetch, so `denied_subfetches` would stop counting 403s.
`ForgeDenied(ForgeAuthError)` keeps the count *and* fixes S-4: a 403 is still counted
denied but no longer sets `throttled`, which is exactly the distinction
`forge/cli.py:213` grades on.

- [ ] **Step 1: Declare the exception**

At `fetch.py:31`, after `ForgeThrottled`:

```python
class ForgeDenied(ForgeAuthError):
    """A forge refused a request permanently.

    Distinct from :class:`ForgeThrottled` because the remedies differ and the
    snapshot's fidelity grading reads which one occurred: waiting clears a 429
    and never clears a 403. Inherits ``ForgeAuthError`` so the per-pull handlers
    keep counting it as a denied sub-fetch.
    """
```

- [ ] **Step 2: Write the failing tests**

`forge/test_fetch.py:1-9` imports only `fetch_pull_data`, `parse_url` and `ForgeError`;
extend that import to include `_paginated_github`, `_get_json`, `_default_transport`,
`ForgeThrottled` and `ForgeDenied`. Then add:

```python
def test_pagination_will_not_follow_a_link_to_another_host():
    """The Link header is remote-controlled and the request carries a token."""
    calls = []

    def transport(url, headers):
        calls.append(url)
        return 200, {"Link": '<https://evil.example/steal>; rel="next"'}, b"[]"

    with pytest.raises(ForgeError):
        list(_paginated_github(
            "https://api.github.com/repos/o/p/pulls", transport, "SECRET"
        ))

    assert calls == ["https://api.github.com/repos/o/p/pulls"]


def test_pagination_is_bounded():
    """A self-referential Link must raise, not loop.

    Counts calls and raises from the transport itself, so a missing bound fails
    this test rather than hanging the suite.
    """
    calls = []

    def transport(url, headers):
        calls.append(url)
        if len(calls) > 50:
            raise AssertionError("unbounded pagination")
        return 200, {"Link": f'<{url}>; rel="next"'}, b"[]"

    with pytest.raises(ForgeError):
        list(_paginated_github(
            "https://api.github.com/repos/o/p/pulls", transport, None
        ))


def test_a_rate_limit_is_distinguishable_from_a_denial():
    """429 recovers by waiting; 403 does not. One type cannot say which."""
    with pytest.raises(ForgeDenied):
        _get_json("https://api.github.com/x", lambda u, h: (403, {}, b""), None)
    with pytest.raises(ForgeThrottled):
        _get_json("https://api.github.com/x", lambda u, h: (429, {}, b""), None)


def test_the_default_transport_sets_a_timeout():
    """A hung forge must not block the only networked stage forever."""
    import inspect

    assert "timeout=" in inspect.getsource(_default_transport)
```

`_paginated_github` may be a generator; the `list(...)` wrappers force it either way. Drop
them if it returns a list.

- [ ] **Step 3: Run them — expect a collection error first**

Run: `.venv/bin/pytest tests/unit/plugins/services/testers/ai_rfc/forge/test_fetch.py -v`
Expected: after Step 1 the import resolves and the four tests FAIL. **Before Step 1 the
module fails at collection**, because `ForgeDenied` does not exist — that is why the
exception is declared first rather than last.

- [ ] **Step 4: Bound the loop and pin the host**

In `_paginated_github` at `:131-136`, capture the host of the starting URL with
`urllib.parse.urlsplit(...).netloc` before the loop. Inside it, before following a `next`
link, compare that link's netloc to the captured one and raise `ForgeError` naming both on
mismatch. Add a module constant `_PAGE_CAP = 1000` beside the other module constants and
raise `ForgeError` when the loop reaches it — announcing the cap rather than truncating,
matching how the package treats caps elsewhere.

For the GitLab loop at `:145`, there is **no remote-supplied host to compare** — it builds
its own URL from a page integer — so apply only the cap and wrap `int(next_page)` so a
non-numeric `x-next-page` raises `ForgeError` rather than `ValueError`.

- [ ] **Step 5: Split the throttle from the denial**

At `:112`, currently `if status in (403, 429): raise ForgeThrottled(...)`. Split into two
branches: 429 raises `ForgeThrottled` naming waiting as the remedy, 403 raises
`ForgeDenied` naming credentials or access as the remedy. Leave `:119`'s 401 →
`ForgeAuthError` alone.

- [ ] **Step 6: Give `urlopen` a timeout**

At `:97`, `urllib.request.urlopen(request, timeout=30)`, with a comment: a forge that
accepts the connection and never answers would otherwise block indefinitely, and `forge` is
the only networked stage in the pipeline.

- [ ] **Step 7: Run the forge suite**

Run: `.venv/bin/pytest tests/unit/plugins/services/testers/ai_rfc/forge/ -v`
Expected: all pass. Any existing test asserting `ForgeThrottled` for a 403 must become
`ForgeDenied` — a deliberate contract change, not a regression. Check `test_cli.py` too:
`forge/cli.py:213` grades on `result.throttled`, and a 403 no longer sets it.

- [ ] **Step 8: Commit**

```bash
git add panther/plugins/services/testers/ai_rfc/forge/ \
        tests/unit/plugins/services/testers/ai_rfc/forge/
git commit -m "fix(ai_rfc): the forge will not follow a remote to another host"
```

---

## Task 5: A record names what actually produced it

**Closes: evidence-04, evidence-05, core-03.** Do this **after Task 1** — both touch
`schema.py` and `test_schema.py`.

**Files:**
- Modify: `panther/plugins/services/testers/ai_rfc/coverage/propose.py:52,76`
- Modify: `panther/plugins/services/testers/ai_rfc/coverage/cli.py:103,131`
- Modify: `panther/plugins/services/testers/ai_rfc/schema.py:141`
- Test: `tests/unit/plugins/services/testers/ai_rfc/coverage/test_propose.py:93-104`
- Test: `tests/unit/plugins/services/testers/ai_rfc/test_schema.py`

**Interfaces:**
- Changes: `propose`'s return type. It currently returns a 2-tuple (`propose.py:52`) and
  must also return the resolved sha it computes at `:76`. Its sole caller is
  `coverage/cli.py:103`. **Revision 1 claimed "Interfaces: none new" and omitted
  `propose.py` from the file list; both were wrong.**

**Why this shape.** `coverage/cli.py:131` writes `"commit": args.commit` — the ref as typed
— while `propose.py:73-76` argues that only the resolved sha may be recorded, so
`--commit main` yields an artifact with `"commit": "main"` beside proposals pinned to a
sha. The resolved value is local to `propose`, so it must be returned rather than
re-resolved; re-resolving is the drift this task removes. `proposals[0].commit` is not a
substitute — it fails on zero proposals, which is MARK's measured case.

Separately, `schema.py:141` lets `yaml.safe_load` keep the last of two identically-keyed
requirements, so a duplicated id silently loses a claim.

- [ ] **Step 1: Make the coverage test able to fail**

`test_propose.py:93-104` passes an already-resolved sha, so it cannot distinguish
`args.commit` from `proposal.commit`. Change it to pass `HEAD`, keeping every argument the
existing test passes — including `--coverage`, which `_argv` requires and revision 1
dropped — and keeping its existing assertions:

```python
    record = json.loads((out / "runtime-anchors.json").read_text())
    assert record["commit"] != "HEAD"
    assert len(record["commit"]) == 40
```

- [ ] **Step 2: Add the duplicate-id test**

In `test_schema.py`, following that file's own construction idiom:

```python
def test_a_duplicated_requirement_id_is_refused():
    """Two claims, one id: safe_load keeps the last and the count under-reports."""
    document = "requirements:\n  R1:\n    text: first\n  R1:\n    text: second\n"
    with pytest.raises(SchemaError):
        load(_written(tmp_path, document))
```

- [ ] **Step 3: Run both to verify they fail**

Expected: the coverage test fails asserting `"HEAD" != "HEAD"`; the schema test fails
because `load` returns one claim rather than raising.

- [ ] **Step 4: Return and record the resolved sha**

Change `propose`'s return at `propose.py:52` to include the resolved commit it computes at
`:76`, update its docstring's `Returns:`, update the unpack at `coverage/cli.py:103`, and
write that value at `:131` in place of `args.commit`. Do not re-resolve.

- [ ] **Step 5: Refuse duplicate keys**

A post-parse check cannot work — `safe_load` discards the duplicate before
`sorted(requirements.items())` at `:152` sees it. Add to `schema.py`:

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

Then change the load at `:141` to use `_StrictLoader`. **Read that line first** — it reads
the file inline rather than from a `text` variable, so the edit is
`yaml.load(Path(path).read_text(), _StrictLoader)` or whatever shape is actually there.
A reviewer confirmed `SchemaError` propagates out of `yaml.load` and nested mappings
construct correctly. One accepted consequence: YAML merge keys (`<<:`) now raise
`ConstructorError`; no file in this repository uses one.

- [ ] **Step 6: Run both suites**

```bash
.venv/bin/pytest tests/unit/plugins/services/testers/ai_rfc/coverage/ tests/unit/plugins/services/testers/ai_rfc/test_schema.py -v
```

Expected: all pass. Every other manifest in the suite must still load — a strict loader
rejecting a valid document would surface here immediately.

- [ ] **Step 7: Commit**

```bash
git add panther/plugins/services/testers/ai_rfc/coverage/ \
        panther/plugins/services/testers/ai_rfc/schema.py \
        tests/unit/plugins/services/testers/ai_rfc/coverage/ \
        tests/unit/plugins/services/testers/ai_rfc/test_schema.py
git commit -m "fix(ai_rfc): record the resolved commit, and refuse a duplicated id"
```

---

## Final verification

```bash
.venv/bin/pytest tests/unit/plugins/services/testers/ai_rfc/ tests/unit/test_cli/test_ai_rfc_commands.py -n auto -q
.venv/bin/mypy --follow-imports=silent panther/plugins/services/testers/ai_rfc/
git log --oneline -6
```

Expected: **more than 390 passing** — 390 is the baseline and this plan adds about nine
tests — with zero failures. `mypy` reported 10 PANTHER-side errors before; the count must
not rise. `black` and `flake8` were clean PANTHER-side and must stay clean. Five commits.

Then the two probes a unit test cannot replace, on a workspace whose manifest overstates a
claim: `pipeline run WS --strict` must exit **3**, not 0; and `pipeline run WS --cluster
c0001` must behave exactly as it did before this plan, proving Task 2 introduced no
regression.

## What review changed

Revision 1 was reviewed against the codebase before execution. Five Critical defects, of
which one would have made the code worse:

- **Task 2's fix was a regression.** Deriving the start ordinal from `state(ws)` looked
  right and is not: `check` at ordinal 6 is never `DONE`, so the walk would always halt at
  the `prose` boundary and `checkpoint`/`gate` — reachable today under `run --cluster` —
  would become unreachable. A second attempt, skipping an already-`DONE` boundary, exits 1
  at `checkpoint` because it needs `--cluster`. The task is now a different design
  entirely: perform the re-derivable checks by state, leave the walk alone.
- **Task 2's test omitted the `run` verb**, so it would have died at `SystemExit(2)`.
- **Task 3's test would have passed against unfixed code** — it reused a directory the
  fixture already fills and broke the wrong input, so both failure paths preceded the
  `mkdir` it was meant to catch. Two of this review's own findings are tests that pass
  against defects; revision 1 wrote a third.
- **Task 1 Step 5 contradicted itself**, instructing "treat as absent" while asserting a
  raise.
- **Task 4's `ForgeDenied(ForgeError)`** would have escaped the handlers that count denied
  sub-fetches. It inherits `ForgeAuthError`.

Also corrected: `propose.py` was missing from Task 5 and its return type does change; three
fixtures the plan named do not exist; several steps gave prose where the convention
requires code; Tasks 1 and 5 are not independent; and two file-list line ranges were wrong.

## Deferred, and why

Harness-side, blocked on the main experiment run, all recorded in the review with evidence:

1. **Close C-1 at its narrow end** — resolve the transcript path and check workspace
   containment at `core/questions.py:157`, and require a non-empty `quote` at `:163`. The
   `Write` grant reaches `record_answer`'s transcript argument, so those two lines are the
   shared mechanism behind both the empty-quote and self-certifying-transcript findings.
   This closes the chain **without** touching `arms.py`, which the experiment's independent
   variable depends on.
2. **Stop calling a tuple containing `Edit` and `Write` `READ_TOOLS`** (`arms.py:21`), and
   record in `enforcement.py`'s docstring which tools are therefore unconfined. Legibility,
   not containment; item 1 does the containing.
3. **Bind a computation to its revision** (C-5) — `load_campaign` should compare the frozen
   campaign's `git`/`prompt_sha256`/`plugin_root` against the live checkout and raise, and
   `audit_run`/`analyze_run` should refuse to overwrite a record produced under a different
   revision. Until then, do not run those verbs against the pilot.
4. **Check a question id for collision before writing** (C-6).
5. **Digest `guard.py` and `enforcement.py`, not only `guard.json`** (S-7 / runner-11).
6. **Validate that a checkpoint directory holds a manifest** (`queries.py:71-75`). Until
   that lands, make the 2,052-directory sweep part of the post-run audit: it is the only
   reason the pilot's progress figures can be left standing, and a future campaign without
   it would have no equivalent guarantee.

Task 1 is the PANTHER-side half of the same defence as item 1: even with the harness input
unfixed, a fabricated sign-off over narrative-only evidence no longer reaches `confirmed`.
Either alone narrows C-1; the two together close it.
