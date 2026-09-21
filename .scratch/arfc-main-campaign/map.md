# Map: ai_rfc Main Campaign, Ready to Launch

Label: `wayfinder:map`
Charted: 2026-09-21 (plan `~/.claude/plans/i-m-handing-you-one-iterative-fern.md`, approved)
Tracker: local markdown — tickets are `issues/NN-<slug>.md`; frontier = open, unblocked, unclaimed, lowest number first.
**Compute the frontier by excluding anything whose `Status:` is not exactly `open`**, never by grepping for one closed-spelling. Every `Blocked by:` entry is a ticket in this map, so "unblocked" means every listed ticket is closed.

`<ai_rfc>` = `panther/plugins/services/testers/ai_rfc` (the submodule, branch `main`)
`<protocol>` = `<ai_rfc>/docs/experiment-protocol.md`
`<pilot>` = `<ai_rfc>/docs/experiments/2026-08-31-pilot-aioquic.md`

This map lives in the **`iut-ai-rfc`** worktree (PANTHER branch
`feat/arfc-pipeline-and-runtime-anchors`), not in `lsp-to-claude` where the other eleven maps
live. Work it from a session rooted here.

## Destination

The arm comparison of `<protocol>` (arms A and B, plus arm C if
[Does the main campaign include arm C](issues/17-does-the-main-campaign-include-arm-c.md) keeps
it) is **ready to launch as a main campaign**: every item of
the protocol's §6 preregistration checklist is decided, the preregistration is written and
committed in the repository, code and prompts are pinned, and a $0 dry-run of the campaign
passes. The OSF submission and the launch itself are the next effort's first acts, not this
map's.

The consumer is a paper; no date bounds the effort.

## Notes

**Terms.** **Main campaign**: the preregistered set of runs made from one `campaign init` (what
earlier notes called "the main run"). **Run**: one arm × target × repeat. **Cell**: one arm ×
target. **Window**: a target's cluster-ordinal range; the task list may be sampled from it
rather than equal to it (see
[Which task list does each target use](issues/12-which-task-list-per-target.md)).

**Execution is carried.** Unlike a default wayfinder map, tickets here may land code and run $0
checks. **Every paid run asks the user first**, with the consent print, the command, the model
ids and the quota reading. Pin code with SP7d's `~/ai-rfc-experiments/code-pins/` clone method:
the editable install means live code moves under a run while anyone commits to `<ai_rfc>`.

**The owed-fixes row is a given, outside this map** (plan
`docs/superpowers/plans/2026-09-21-arfc-owed-fixes.md`). Before editing any `<ai_rfc>` file,
check that plan's file list and message its session. **Find the session's current name with
`ListAgents`**: it has answered as `iut-ai-rfc-0e` and as `plan-review-and-task-dispatch`. It
owns `experiment/{runner,audit,per_cluster}.py` and `driver/{spawn,stop,coverage,record}.py`.
**R91/R92 were reported to it, but its plan never mentions them** (grep at charting: no R91, R92,
`consolidations_recorded` or `recorded=True`); adoption is unconfirmed, see
[Has the owed-fixes row landed](issues/05-has-the-owed-fixes-row-landed.md). The ARM-B fix
`8358238` rides that row's push.

**Arm C is frozen out of v2 by spec D42**, found after charting: `<protocol>:157-159`,
`:191-195` and `:302-306` all say "a v2 campaign compares arms A and B", and arm C never
consolidates. The charting grilling assumed three arms, so
[Does the main campaign include arm C](issues/17-does-the-main-campaign-include-arm-c.md) comes
before the hypotheses.

**A sibling map owns the ground truth: "Ground-Truth Yardstick"**
(`.scratch/ground-truth-yardstick/map.md`, same worktree, charted by another session on
2026-09-21). Its destination is a ruled definition of a window's ground truth and of **reachable
recall** (primary there), the aioquic w02-11 dataset rebuilt to it, a $0 re-score, and a
scorer-change spec handed to ai_rfc. Two of its findings bear on this map:
- **8/35 is the window's ceiling, not a finding about the drafts.** The dataset is anchored at
  aioquic's 2025 tip and built from the final RFCs, while w02-11 ends in 2019 at draft-22. Its R93
  withdraws SP7d's "v2 recovers no more facts" reading.
- **The tip-source leak, wider than `clone/`.** The pristine's `clone/` working tree is checked
  out at the tip, so any arm's `Read` could open code from after the window (no run did). It is
  wider than that: `cluster_get` has no window check, and the pristine holds all 342 clusters'
  diffs, so every arm can read out-of-window clusters (confirmed at the site in
  [Diff the three rendered arm prompts](issues/02-diff-the-rendered-arm-prompts.md), entry S1).
  Arm C's unrestricted `git` also reaches the clone's whole history (its D13). A main campaign
  cannot freeze with the leak open; see
  [Freeze prompts, pin code, and dry-run](issues/13-freeze-pin-and-dry-run.md).

Any ground-truth measure this map adopts uses that map's definitions and never re-derives them.
Its glossary uses "window" as this map does, and plans to move into `<ai_rfc>/CONTEXT.md` once the
owed-fixes row lands; this map's terms go there too.

**Standing lessons** from the rows before this one:
- Dry-run a round's LAST gate on its input before paying; "could start" is not "could finish".
- Relaying is authoring: check at the site any claim taken from an agent or a reviewer.
- Measure the noise before believing a delta (the GEPA pilot's floor was 0.030 per example).
- Tests: run from the submodule root, `-n 4` (never `-n auto`), `--basetemp` under
  `/tmp/claude-501`, `SSLKEYLOGFILE=` set empty; an unaccepted Xcode licence fails ~60 tests.

**The protocol's §6 checklist is the destination.** Each item maps to a ticket:
hypotheses and primary metrics, trajectory aggregations, cache accounting and cost formula → 01;
task list and coverage → 12; exclusion rule → 08; enforcement per arm → 04 and 13; model and
harness → 09; prompt pair, diff and freeze → 02, 04 and 13; statistical plan → 10; parity
pre-run → 03 and 13; k and run matrix → 15; reporting commitments → 16.

## Decisions so far

<!-- the index: one line per closed ticket, enough to judge relevance, then zoom the link -->

- [What statistical plan fits k of 3–5 per cell over two targets?](issues/10-what-statistical-plan-fits.md):
  per-target rank tests cannot reach α = 0.05 at k = 3 (floor 0.10) and are usable only at k = 5.
  So test pooled and stratified by target, exactly; estimate per target; closed testing within a
  hypothesis and Bonferroni or a cost-first sequence across hypotheses; no bootstrap. k = 3 → 5
  cuts the pooled minimum detectable effect from 2.05 to 1.45 SD. Size k from the validation
  pilot's upper SD limit (research, not yet adopted).
- [Diff the three rendered arm prompts from a fresh `campaign init`](issues/02-diff-the-rendered-arm-prompts.md):
  the prompts are **not** identical modulo syntax. Sixteen differences between arms (D1–D16),
  among them: arm C is never told an anchor field name; arm B is never told the structure fields
  in the loop; the one "neutral" skill in consolidation, `ai-rfc-structures`, speaks arm A's tool
  names; and no arm but C sees the corpus schema. Two leaks are common to every arm (window-less
  cluster access, and the clone at the tip). `task.md` is unchanged since the pilot, and
  `campaign init`'s toolchain verification currently refuses. Listed, not ruled.
- [Audit the parity suite: which operations carry a cross-arm behavioural assertion?](issues/03-audit-the-parity-suite.md):
  25 passed at `571355c`. All 20 tools have an A-against-B twin: 13 full, 6 partial (claim
  upsert never sends an anchor; revision tag never refuses; three twins have no non-vacuity
  guard), and 1 none by design (status, D16). Probes: A and B *can* read the corpus schema, and
  anchors keep parity. No transport is tested, and arm C has no twin. Listed, not ruled; "Rule
  each arm asymmetry" now also waits on the arm C decision.

## Not yet specified

- **The class-3 companion measurement** (in scope, user ruling at charting). `<protocol>` §1
  allows a raw-shell arm only in a different harness (mini-swe-agent is its exemplar), run as a
  separate, harness-confounded measurement and never pooled with arms A–C. Unclear yet: which
  harness, how it is held to the same task list and gates, and how it is reported. Sharpens once
  the hypotheses and the task lists are settled.
- **Ground truth for MARK.** Ground truth exists only for aioquic w02-11 (41 facts,
  `<ai_rfc>/ai_rfc/experiment/groundtruth/aioquic-w02-11.yaml`). Whether MARK needs one depends
  on whether the hypotheses make a ground-truth measure primary or secondary. *How* it would be
  built is the sibling map's ticket "How is ground truth built for a target with no published
  spec?", not this map's. **The sibling map ruled on 2026-09-21** that a window's ground truth is
  anchored at the window's end (the last member commit of its last cluster; `509065a` for w02-11)
  and cites the spec version the code declares there. A target whose code declares no spec gets
  no dataset. **Until that ticket rules, preregister no recall figure for MARK.**
- **How the drafts' judged quality enters the paper**, if at all: SP7d's blinded judge exists,
  but no hypothesis names it yet.

## Out of scope

- **A third target.** The user ruled two targets, MARK and aioquic, as the protocol fixes them;
  the pilot's "denser normative surface" suggestion is not taken up here.
- **The OSF submission and the launch.** Past the finish line.
- **The ground-truth yardstick itself**: the definition of reachable recall, the w02-11 dataset,
  and the scorer spec. The sibling map "Ground-Truth Yardstick" owns it. Ground truth enters here
  only as a measure, if the hypotheses call for one.
- **Runtime anchors and `checked_fraction`.** Identically 0.0 in model-only runs by design (D23).
