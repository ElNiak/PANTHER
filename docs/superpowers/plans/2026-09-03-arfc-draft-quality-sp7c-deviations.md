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

---

## D6 — Task 1: `init_campaign`'s pass-through was untested, and `CampaignConfig` needed the field

**What the plan said.** Task 1 Step 3: add `Campaign.consolidate_every: int = 10` "and set it in `init_campaign` from the config".

**What the code showed.** `init_campaign` takes one `CampaignConfig`, which had no such field, so the instruction was unexecutable as written. And once both dataclasses defaulted to `10`, the line `consolidate_every=config.consolidate_every` could be **deleted with all 1408 tests still passing** — nothing distinguished "the value was threaded" from "the default happened to be right".

**What I did.** Accepted the implementer's addition of `CampaignConfig.consolidate_every`, and required a round-trip test driving a **non-default** value. The implementer proved the gap by mutation: deleting the line made the new test fail `assert 10 == 3` while both original tests stayed green. Task 8 later removed the duplicated literal entirely (see D12).

---

## D7 — Task 3: the plan's RED test was green against unfixed code

**What the plan said.** Task 3 Step 2 expects `test_a_summary_reports_the_cluster_round_not_the_consolidation` to FAIL with `note == 'the consolidation'`.

**What the code showed.** It passes unfixed. `ai_rfc/server/core/revisions.py:103` writes the map with `yaml.safe_dump(document, sort_keys=True)`, so a consolidation's higher tag always sorts *after* the cluster round it follows, and "first match wins" is accidentally correct for the two-entry scenario.

**What I did.** A RED test that passes is normally a stop, because a wrong test hides a wrong fix. Here the implementer diagnosed *why* and substituted a scenario that genuinely exercises the defect — a cluster carrying **only** a consolidation entry, reachable because `record_revision` refuses a *second* `kind: cluster` entry but never requires a *first*. I accepted it after verifying `sort_keys=True` myself. The task reviewer then probed `revision_of` with the consolidation sorted first and confirmed the **landed filter, not sort order**, protects the two-entry case — so there is no latent defect. The originally-prescribed assertions were also non-discriminating; fix round 1 reversed the fixtures so they fail against unfiltered code, with mutation output pasted.

---

## D8 — Ruling R15: the git-argument guard belongs upstream

**What the plan said.** Nothing — `summary.revision_of` was to gain a `kind` filter and no more.

**What the tool showed.** A revision tag is a mapping key read by `_mapping`, which — unlike `load_revisions` — never validates it, and every caller hands it to git as a revision argument. Measured on git 2.55: **`git diff --numstat --output=<path> <tag>` actually wrote the file.** Arbitrary file write as the harness user, not a theoretical injection. `--` does not help: it separates revisions from pathspecs, and a leading-dash revision is still read as an option.

**What I did.** Ruled the guard upstream, in `revision_of`, because the same tag reaches **three** sinks — `summary.py`'s `diff` and, via `citation_delta`, `gate.py:169` `ls-tree` and `gate.py:181` `show`. Fixing only the call site would have left two open. `--end-of-options` was added on the `diff` call as a second line. A well-formed workspace cannot change behaviour, since `record_revision` revalidates the whole document against the same regex.

---

## D9 — Ruling R16: the citation rule is superset, and the plan said equality

**What the plan said.** Both the editorial skill and the consolidation template's closing paragraph: "the citation set after it must equal the set before it. The gate checks both."

**What the code and the spec showed.** Spec **D52**: a consolidation "keeps every citation; dropping one is `true` with a note" — superset. `ai_rfc/draft/gate.py:457-463`: for `kind == "consolidation"` it computes `dropped = previous_cited - cited` and reports **only** drops, with the message "a consolidation keeps every citation". Equality is enforced only on the branch that kind never reaches.

**What I did.** Corrected both texts. The wording was not merely imprecise but self-defeating: the same template's step 4 orders the agent to add references and a figure caption citing claims, both of which grow the cited set, so an agent obeying the closing paragraph would refuse what the step above asked. Verified end-to-end in the probe step: all four rendered arm prompts carry "keeps every citation" and neither equality phrasing.

---

## D10 — Ruling R16b: the slot check ran one stage too early

**What the plan said.** Nothing; the plan treated `render_loop`'s unfilled-slot check as sufficient.

**What the tool showed.** Task 6's review appended `{{low}} and {{unknown_slot}}` to a bundled skill body, called `arm_prompt("A", root)`, and got **no error with both slots verbatim in the returned prompt**. `render_loop` validates the *template* (`render.py:403`) while `arm_prompt` appends the skill bodies afterwards (`:479-481`), and nothing rescanned. On a profile opening on a fixed `preamble`, `render_loop` is never called, so **no** check ran at all.

**What I did.** Ruled that Task 4 close it, being the only task touching the function and the one widening the exposure with a second template and bundle. The fix round then moved the scan into `_render_template`, so `write_plugin_skill` and the GEPA `apply.py`/`codec.py` path inherit it — proven non-vacuous: with the scan stubbed, `write_plugin_skill` writes a `SKILL.md` containing a live `{{gate}}`. A second instance surfaced from the same work: substitution is **single-pass**, so a slot's own text naming a slot survived into the rendered opening where the pre-substitution check could not see it.

---

## D11 — Ruling R17: the bundle contradicted itself

**What the plan said.** `CONSOLIDATION_TEXTS` bundles `ai-rfc-rfc-style/SKILL.md` and `references/claim-citation.md`.

**What the tool showed.** Rendering `consolidation_prompt("A", root)` produced the superset rule **twice and the equality rule twice**: those two bundled files state equality, correctly for a *cluster* round (`gate.py:466`) but not for this one.

**What I did.** Extended Task 4's boundary to both files. This is not unrelated residue — Task 4 is what places those texts into a consolidation round, where their equality sentence becomes false; before it they were bundled only into loop prompts. The fix is a **carve-out scoped by round name**, not a replacement, so the loop prompt is unweakened. Confirmed by rendering both prompts, and the new needles were proven non-vacuous by rendering against the pre-fix texts.

---

## D12 — Ruling R10 as it actually landed, and what it did NOT achieve

**What the plan said.** Task 1: "whoever writes CLI-1 reconciles the two homes."

**What the code showed.** CLI-1 landed first (see D2), and by Task 8 the literal `10` lived in **three** places: `ai_rfc/config.py`, `CampaignConfig`, and `Campaign`.

**What I did.** `ai_rfc/config.py` gained `field_default(path)`; the CLI constant and `CampaignConfig` both derive from `sessions.consolidate_every`. Only `Campaign.consolidate_every` keeps a literal, and its reason is sharper than R10's own framing: `load_campaign` applies that default to campaigns frozen **before the field existed**, so deriving it would retroactively reinterpret them against later table drift.

**What R10 did NOT achieve, and CLI-2 must.** The flag and the field share a *schema default*, so the two numbers cannot drift — but **`campaign init` does not read an operator's configured value**. `sessions.consolidate_every: 3` in a `recon.yaml` is loaded (`config.py:593`), re-serialised (`:679`) and **read by nothing**; the campaign freezes 10 regardless. Now stated plainly in the protocol note, the verb table and the `--help` string.

---

## D13 — Critical 5 of my own plan review was a false alarm

**What I predicted.** Task 5 would break the GEPA optimize fixtures, because `codec._slot_reasons` computes `expected = Counter(SLOT_RE.findall(TEMPLATE.read_text()))` from the loop template, so adding two slots makes every candidate need them. I extended Task 5's boundary (R13) to cover the repair.

**What the tool showed.** The mechanism is real but **no fixture broke**: every optimize seed and candidate derives from `TEMPLATE.read_text()` at test time rather than storing a ten-step body. The reviewer checked the two deselected `@pytest.mark.slow` tests specifically, in case a stored body hid behind the marker — both build from `encode(...)`, and no `Bundle(` is constructed anywhere in `tests/`.

**What I did.** Recorded the boundary extension as unused. The 3.11 selection stayed at **222 passed, 2 skipped, 2 deselected** across five measurements. The guard is nonetheless live: dropping either new slot from a candidate yields `loop: missing slot`.

---

## D14 — Task 7: the plan's gate test could not produce the sequence it asserts

**What the plan said.** Task 7 Step 1's `test_a_consolidation_runs_after_every_k_clusters_and_at_the_end` is the row's gate, driving a scripted `fake_due`.

**What the tool showed.** It cannot produce the required sequence. `fake_due` matches on `at_end` alone and the first mid-sweep query happens **before any cluster round**, so a consolidation ran first; and `_stub_spawn` incremented on every spawn while `fake_artifacts` keyed completion off that counter, so a consolidation finished a cluster no session had worked on. Traced: `["consolidation","cluster","cluster","consolidation"]`, 4 sessions / 4 spawns.

**What I did.** Accepted a rewrite driving the **real** `consolidation_due` off a real `revisions.yaml` the spawn stub writes, with the stub skipping its counter on a `consolidation-` argv. The reviewer judged it the stronger gate and confirmed it cannot pass for an unrelated reason: `consolidate_every=2` against a default of 10 means the mid-sweep round could not fire at all if the field were not threaded. It now yields exactly `cluster, cluster, consolidation, cluster, consolidation`, 5 sessions, 3 cluster spawns — verified independently four times.

**Four further defects the plan would have shipped**, each found here and fixed with a test: the unconditional `continue` was a **retry loop** that re-ran a failed round every pass until the wall clock (D52 inverted); `budget_left`/`time_left` were read after the `row is None` return (`UnboundLocalError` on a complete window); the fall-through launched the cluster round from the **pre-consolidation budget** past an unre-applied guard (measured overrun: $1.00 cap, run ended at $1.20); and a consolidation's cost was not charged to `spent`, its session id filed under the next cluster.

**Two rulings against the implementer, both on traced evidence.** A forged cluster id is **not** fatal — `driver.py:104` has no `try` around `launch()` and `driver.py:85-89` refuses to resume a run dir lacking `status.json`, so one bad YAML scalar would have aborted the campaign and wedged the run. And `_run_consolidation` returns `tuple[bool, bool]`, not `bool`: it had discarded `spawn`'s `timed_out`, and `any_timeout` feeds `runner.py:320-321` where that flag sets `exit_code=None`, so a consolidation killed on the cap would have recorded no timeout.

**And one against a first fix.** The retry-suppression key was `(ordinal, base_cluster)`, which does not dedup: `consolidation.py:63` reassigns `base_cluster` to the newest cluster revision, so the key advances every time a cluster records — probed as `(1,'c1') → (1,'c2') → (1,'c3')`. Keyed on `due.ordinal` alone in round 2, with the sweep-end round deliberately exempt.

---

## D15 — Ruling R11 as it actually landed: membership, not a character filter

**What I originally ruled.** A `CLUSTER_ID_RE` identifier regex.

**What the tool showed.** Measured through the shipped `consolidation_due`, YAML implicit typing rewrites an agent's `cluster_id` before anything sees it: `01` → `'1'`, `yes` → `'True'`, empty → `'None'`, `[a, b]` → `"['a', 'b']"`, a block scalar → a string containing a **real newline**; `../../etc` and `/etc/passwd` pass intact. A character blacklist catches the newline and the traversal but passes `'1'`, `'True'`, `'None'` and `"['a', 'b']"` — none has a control character, none names a cluster.

**What I did.** Replaced my own ruling with **closed-set membership** against the run's timeline, which subsumes every row of that table in one check. It landed against the **whole timeline** (`gate._cluster_ordinals`), not the window, because pre-seeded baselines are supported and a seeded entry naming a cluster below the window's first ordinal would otherwise raise on a legitimate id.

**A fourth sink, and it is model-read.** `due.base_cluster` reaches the session prompt, a checkpoint path, **and the `report()` line**, whose grammar is one record per line — and the plan reported the id *before* validating it. `optimize/evaluator.py:475` passes `report=settings.log`, and `optimize/run.py:172-174` routes those lines into GEPA's feedback, which the **proposer LLM reads**. So validate-then-report closes a prompt-injection sink, not merely a line-grammar one. That reason is now a comment in the code.

---

## D16 — Task 8: a negative interval inverts the flag, and the new verb bypassed two invariants

**What the plan said.** Add `--consolidate-every N` and `run --task consolidation`.

**What the tool showed.** `consolidation_due` asks `since >= every`, so `--consolidate-every -1` is satisfied by the very first cluster and buys a **paid** editorial pass after every one. Measured: `every=-1` → `Due(ordinal=1, since=1)`; `0` and `10` → `None`. `config.py:436` already rejected a negative value in `recon.yaml`, so the YAML path was strict while the flag path was not.

Separately, `_run_consolidation` spawns with `append=True`, so the new verb appends a session to a **finished** run: `status.json` then describes only a prefix of `events.jsonl`, while `audit_run` reads both. The sweep enforces `runner.py:241` and `driver.py:85`; the verb had neither and bypassed both silently.

**What I did.** Negatives refused at parse time, `0` preserved. For the append: my first idea — refuse a run whose `status.json` says complete — was wrong, since every legitimate target has one. The landed guard is `--append-to-finished-run`, required **unconditionally**, plus an `appended.jsonl` marker carrying `events_lines_before` counted **before** the spawn. The re-reviewer supplied the strong rationale: `driver.py:85-93` already treats "run_dir without a status record" as an error state, so a conditional check would either silently append to an *in-flight* run or need a third branch.

The plan's own default test was also unusable: `CampaignConfig.consolidate_every` already carried `10`, so unfixed code froze 10 — and comparing two literals *while they agree* is precisely the state R10 forbids. Replaced with a seam test that monkeypatches the shared constant to 7.

---

## D17 — Task 9: writing the protocol note found five contradictions

Prose is where a contradiction shows up, and this was the row's first end-to-end description.

1. **The spec's SP7c Content cell is stale** — it lists `campaign init --task consolidation`; no such flag exists. `--task` is on the **`run`** parser and means something else. Ruling R3 pre-authorised exactly one spec cell, so this is **not mine to fix**; it goes to the user. (The plan's own File Structure was corrected on 2026-09-03 by `26ba0b97c`; the spec's roadmap row was not.)
2. **"Arm C never consolidates" is a scheduler property, not a freeze property** — `campaign init` renders and hashes `consolidation-C.md` alongside every other arm; only the guards stop it spending.
3. **The plan's `_run_consolidation` contract text drifted twice** — `tuple[int | None, bool]` in the Interfaces line, `bool` in the Self-review. Corrected in the plan to the landed `tuple[bool, bool]`.
4. **The single-source default is true of the flag only** (see D12).
5. **`ai_rfc/experiment/README.md` is the verb table an operator actually consults** — the top-level README points at it — and it was stale. The brief scoped only the top-level file; I extended the boundary.

A sixth, caught in review: the note **understated** the guard. The strongest "changes no claim" enforcement is `requirements_digest(consolidated) == requirements_digest(base)` (`gate.py:380-389`), refused at **write time** (`checkpoint.py:238`) and running unconditionally — a consolidation may change only `structures:`. The citation-superset rule runs only when the revision records `normative_change: false`, and nothing obliges it to. Two structural rules were unmentioned (`gate.py:356-365`). All now recorded.

---

## D18 — Out of row: pre-existing defects found but deliberately NOT fixed

Ruling R4 keeps unrelated residue out, and no SP7c task edits these files. All were verified, not inferred. **These are the row's most important hand-off.**

1. **`ai_rfc/draft/gate.py:224` joins an unvalidated `cluster_id` into a filesystem path** — `checkpoints_dir / entry.cluster_id`, so `../..` escapes the checkpoints directory. The sibling consolidation branch one line above at `:223` already sanitises with `Path(entry.checkpoint).name`. One branch guarded, one not.
2. `gate.py:96` sorts raw mapping keys before validating them, so a mixed-type key set raises `TypeError` before any of its own checks. One-line remedy: `sorted(revisions.items(), key=lambda kv: str(kv[0]))`.
3. `gate.py:75-88`'s docstring promises `GateError` for a malformed document and does not deliver it — `yaml.safe_load` at `:89` is uncaught.
4. **`REVISION_TAG` is applied with `.match` and ends in `$`**, so it accepts a trailing newline (`"draft-t-01\n"`). Shared by `gate.py:98`, `gate.py:273` and `server/core/draft.py:97`. Proven harmless at all three git sinks — git refuses to resolve such a ref and every sink errors — so it was correctly left alone; the right fix is `fullmatch`/`\Z` in `gate.py`.
5. `optimize/scoring.py:617` catches only `(GateError, OSError)` for `load_revisions`, so it carries both the `yaml.YAMLError` and `TypeError` holes that R14 closed locally.
6. `audit_run` does not read the new `appended.jsonl` marker. Nothing in `ai_rfc/` enumerates `run_dir`, so the marker cannot surprise an existing consumer.
7. `_render_template` has no guard against a **newline inside a `SLOT_TABLES` value**. The "no rendered line begins with table-controlled text" property is true of today's data, not enforced — one newline would put author-controlled text at column 0, which is the SP7b shape exactly.
