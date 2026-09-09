# SP7c — deviation log

How the landed code differed from what `2026-09-03-arfc-draft-quality-sp7c.md` assumed, and
what was done about it. Written so SP7d and CLI-2 are planned against fact rather than against
a plan drafted three rows earlier.

Each entry has three fields: **what the plan said**, **what the code or the tool showed**, and
**what I did**. Entry 0 records the rulings that shaped the row before any task ran.

---

## D0 — the rulings this row runs under

Five are the user's, taken on 2026-09-09. Six are mine, each recorded with what it costs if
wrong. A ruling is a decision made inside the plan's File Structure without a round-trip; a
decision that would change a spec entry other than the pre-authorised gate cell is a stop, not
a ruling.

### The user's rulings

**R1 — sequencing.** The one-door spec's D55 orders SP7c after CLI-2 and CLI-3, and the
2026-09-05 executor prompt says SP7c is not a row it runs. The user ruled that SP7c runs now,
before CLI-2, on the experiment driver as it stands after CLI-1, and that CLI-2 inherits the
migration of the consolidation hook into `ai_rfc/driver/`. *Cost:* the handoff must list, file
by file, what CLI-2 has to move.

**R2 — the prompt-text fix.** `ai_rfc/experiment/render.py` still hands the model the old lax
progress contract. Under the strict ledger rule the raw arm and the MCP arm would compute
different next clusters, and no campaign may run until that is fixed. The user ruled that
Task 4 — which already edits `render.py` and freezes the prompts — corrects the slot texts to
the ledger's rule: a cluster is done when its checkpoint exists under `checkpoints/<id>/`,
`revisions.yaml` holds a `kind: cluster` entry for it, and that entry's tag exists in the draft
repository; the next cluster is the lowest-ordinal in-window cluster that is not done,
pre-seeded clusters counting as done. Source of truth: `ai_rfc.ledger.next_cluster` and
`ClusterState.done`. Each arm says the same rule in its own vocabulary; `test_render.py`'s
golden is re-pinned and `write_plugin_skill` regenerates the loop skill. *Cost:* a prompt change
alters what a campaign measures, and lands in the row that already changes the prompts.

**R3 — the spec edit.** Task 9 Step 3 replaces exactly one cell of the spec's SP7c roadmap row
(the gate cell at line 187). Any other spec edit is a stop.

**R4 — scope.** SP7b's residue rides along only where a task already edits the file and the fix
is small. Nothing else from it enters this row.

**R5 — spend.** Nothing in this row spends. No `claude -p` in any role; the consolidation prompt
is verified by rendering and by the frozen-prompt tests, never by running it.

### My rulings

**R6 — the lax text has three occurrences, not two.** R2 names two slots. The file has three:
`_RAW["cluster_next"]` at `render.py:83-87`, which feeds *both* the `interactive` and the `C`
tables; `SLOT_TABLES["B"]["cluster_next"]` at `:200-203`; and `SLOT_TABLES["A"]["cluster_next"]`
at `:255-258`. I fix all three. *Reasoning:* R2's own justification is that no two arms may
compute a different next cluster, and arm B is an arm; further, B's text describes what
`ai_rfc cluster-next` prints, and that verb now delegates to `ai_rfc.ledger`, so the text is
factually wrong about its own tool. *Cost if wrong:* a third prompt-text change in the same
row — no new class of risk, since R2 already accepts that this row changes prompts. Leaving B
lax would reintroduce exactly the defect R2 exists to prevent.

**R7 — Task 3's metrics half is already satisfied.** See D3. The two metrics RED tests become
regression tests pinning the ledger's filter; `summary.revision_of` is the only genuine RED.
*Cost if wrong:* a test that passes on day one catches a regression only if the ledger filter is
later removed — which is precisely the regression it is there to catch.

**R8 — Task 2 reads through `load_revisions`, not the ledger.** Spec D50 says the scheduler
consumes SP4's ledger if it landed first, and it has. But `ledger._entries` skips every entry
whose `kind` is not `cluster`, which is exactly the set `consolidation_due` must count. Task 2
therefore reads `revisions.yaml` through `ai_rfc.draft.gate.load_revisions`. *Cost if wrong:*
two readers of one file. Mitigated: both go through the same substrate loader for what a
revision *is*, so they cannot disagree about the schema — only about which entries they keep,
which is the point.

**R9 — `consolidation_prompt` reuses `TASK_PROFILES`.** The plan draws a parallel
`CONSOLIDATION_TEXTS` constant plus a standalone `consolidation_prompt`. The landed
`arm_prompt` already routes texts through `TaskProfile` (`render.py:447`), so I add a third
profile and give `TaskProfile` an optional template-name field, keeping a thin
`consolidation_prompt(arm, plugin_root)` for the interface the plan declares. *Cost if wrong:* a
larger `render.py` diff than the plan drew, in exchange for one bundling path instead of two
that can drift apart in how they strip frontmatter.

**R10 — one default, not two.** See D2. *Cost if wrong:* a small coupling from the experiment
CLI to the lifecycle config; the alternative is two defaults of 10 that silently diverge.

**R11 — the interpolation guard.** See D5. *Cost if wrong:* if the guard is over-strict, a
legitimate cluster id is rejected loudly rather than silently forging a prompt.

---

## D1 — the baseline is measured, and the 3.11 selection is green

**What the plan said.** Task 0 Step 1 expects the suite "at SP7b's recorded count". The
executor prompt recorded 1406 passed and 11 skipped under 3.10, and said of the 3.11 optimize
selection that "the CLI-1 session recorded that selection as red for reasons outside its files,
so a failure there that reproduces at your Phase 1 baseline is pre-existing and reported as
such, never fixed in this row."

**What the tool showed.** Measured on 2026-09-09 before any edit:

| Baseline | Command | Result |
|---|---|---|
| ai_rfc suite, 3.10 | `pytest tests -q -n auto -p no:cacheprovider` from the submodule root | **1406 passed, 11 skipped** in 163.94s |
| PANTHER door tests | `pytest tests/unit/test_cli/test_ai_rfc_commands.py -q` from the worktree root | **6 passed** in 13.22s |
| optimize selection, 3.11 | `pytest tests/experiment/optimize tests/experiment/test_cli_optimize.py -q -m "not slow"` | **222 passed, 2 skipped, 2 deselected** in 226.46s |

The 3.11 preconditions both held first: `import ai_rfc` resolved from a cwd outside the package,
and `python -v -c pass | grep -c Skipping` printed `0` on Python 3.11.9.

**What I did.** Recorded all three as this row's baseline. The 3.10 count matches. **The 3.11
selection is green, not red** — so the prompt's "pre-existing failure" allowance does not apply
to this row, and any red in that selection after Task 5 is caused by this row and must be fixed
here rather than written off. That materially raises the stakes on D4 below.

---

## D2 — `sessions.consolidate_every` already exists; CLI-1 landed first

**What the plan said.** Task 1's Interfaces block: "The one-door CLI's `recon.yaml` defines an
operator-facing `sessions.consolidate_every` (default 10) in the new `ai_rfc/config.py` (CLI-1
plan) … Under the agreed order SP7c lands first, so that field must **feed** this one rather
than duplicate its default; whoever writes CLI-1 reconciles the two homes. Nothing to do here."

**What the code showed.** CLI-1 landed on 2026-09-08, before this row. The field is already
present: `ai_rfc/config.py:181` (the `Field` declaration), `:349` (`consolidate_every: int` on
the sessions record), `:573` (built from the parsed values) and `:659` (round-tripped back out).
The plan's note assumes an ordering the user's R1 ruling inverted, so "whoever writes CLI-1
reconciles" names a session that has already finished.

**What I did.** Ruled (R10) that the reconciliation lands in this row instead.
`Campaign.consolidate_every` keeps a literal default because `load_campaign` splats frozen JSON
straight into the dataclass and a field without a default would make every existing
`campaign.json` unloadable — the finished MARK campaign included. But `campaign init
--consolidate-every`'s parser default references `ai_rfc/config.py`'s single source rather than
a second literal `10`, so the two homes cannot drift. Task 1's Interfaces block is rewritten in
the plan to say this, and the third home question (whether `campaign init` should read
`recon.yaml` at all) is handed to CLI-2 rather than settled here.

---

## D3 — Task 3's metrics half was fixed by CLI-1, at the ledger

**What the plan said.** C12: "`cluster_artifacts` joins revisions by
`body.get("cluster_id") == cluster["id"]` and takes `entries[0]`." Task 3 Step 3 narrows that
comprehension with `and body.get("kind", "cluster") != "consolidation"`, and Task 3 Step 1 adds
two RED tests expected to fail with `revision_tag == "draft-t-02"`.

**What the code showed.** `cluster_artifacts` (`ai_rfc/experiment/metrics.py:66`) no longer
joins revisions at all — CLI-1 moved that join into `ai_rfc/ledger.py`, and `metrics.py` now
delegates to `ledger.clusters()`. The filter the plan wants to add is already there, at
`ai_rfc/ledger.py:120`:

```python
if body.get("kind", "cluster") != "cluster":
    continue
```

So the comprehension Task 3 Step 3 edits does not exist in `metrics.py`, and both metrics RED
tests would pass against unfixed code. A RED test that passes before the fix hides a wrong fix,
which is a stop condition — the plan's test is wrong, not the code.

**What I did.** Ruled (R7): rewrote Task 3 in the plan so the metrics half becomes a regression
test that pins the ledger's filter rather than adding a second one, and `summary.revision_of`
(`summary.py:67`, still an unfiltered first-match join) is the task's only genuine RED. Also
rewrote the task's test helper: `_workspace_with_revisions` as drawn writes only
`revisions.yaml`, but `cluster_artifacts` now reaches `ledger.clusters`, which needs
`timeline/clusters.jsonl` and a `draft/` git repository for its `tag_exists` condition, so the
helper must build a real minimal workspace.

---

## D4 — Task 5 moves the 3.11 optimize selection, and the plan never says so

**What the plan said.** Task 5 inserts step 3b into `loop.tmpl.md` with two new slots, and its
"Why this shape" argues the insertion "keeps this a one-line diff rather than a rewrite". The
only consequence it names is that `test_render.py`'s byte-exact pin goes red until
`write_plugin_skill` is re-run.

**What the code showed.** `ai_rfc/experiment/optimize/codec.py`'s `_slot_reasons` validates
every GEPA candidate against the *packaged loop template*, not against the slot tables:

```python
expected = Counter(SLOT_RE.findall(TEMPLATE.read_text()))
counts = Counter(found)
for name in sorted(expected - counts):
    reasons.append(f"loop: missing slot {{{{{name}}}}}")
```

Adding `{{structure_upsert}}` and `{{draft_render}}` to `loop.tmpl.md` therefore changes what
every candidate must contain: any optimize fixture written against the ten-step template will
report `loop: missing slot`. Task 4 alone is safe — its unknown-slot check is
`set(found) - set(SLOT_TABLES["A"])`, which only shrinks as table keys are added — but Task 5
is not.

**What I did.** Recorded it as a Critical against Task 5 and wrote the consequence into that
task's brief, together with D1's finding that the selection is currently green. The 3.11 count
is measured after Task 5 and reported against the D1 baseline; it is never reconciled by
skipping or weakening a test. `TEMPLATE` must also stay exported from `render.py` through
Task 4's refactor, since `codec.py:25` and `apply.py:30` both import it.

---

## D5 — author-controlled text reaching a produced artifact

**What the plan said.** Task 7 builds the consolidation session's task text with
`CONSOLIDATION_TASK.format(ordinal=due.ordinal, base=due.base_cluster)`. The plan treats
`base_cluster` as an opaque identifier.

**What the code showed.** `due.base_cluster` is a `cluster_id` read back out of
`revisions.yaml`, which an agent wrote. It is interpolated unescaped into a string that becomes
a session's task prompt. This is the same class of defect that hid SP7b's only blocker through
nine consecutive reviews: a newline in author-controlled text forged the block delimiters the
gate compared. A `cluster_id` carrying a newline, a backtick run or a heading marker forges
prompt structure the same way. The sibling surface is a consolidation's `note`, which is written
into `revisions.yaml` and read back by `consolidation_due`.

**What I did.** Ruled (R11) that Task 7 constrains `cluster_id` before interpolating it, and
made the question standing for every review brief in this row: *which character or value under
an author's or an agent's control reaches a produced artifact unescaped, and what does the
grammar of that artifact do with it?* The artifacts it applies to here are the rendered
consolidation prompt, the `revisions.yaml` entry a consolidation writes, and the `Due` record
the scheduler derives from disk.
