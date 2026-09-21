# 12 — Which task list does each target use, with its provenance-class coverage?

Type: grilling (HITL)
Status: closed (grilling, 2026-09-21)
Claimed: chart-ai-rfc-main-campaign (session 40f5ddb1), 2026-09-21 15:37 CEST
Blocked by: [What are the hypotheses](01-what-are-the-hypotheses-and-primary-metrics.md), [Can the rebuilt MARK pristine pass its last gate](07-can-the-mark-pristine-pass-its-last-gate.md)
Parent: [ai_rfc Main Campaign, Ready to Launch](../map.md)

## Question

Protocol §6 item 4: "task list per target, with provenance-class coverage stated".

**The protocol samples; it does not take a range.** §4 says tasks are drawn from each target's
cluster inventory "to cover the provenance classes the linkage literature shows are
recovery-sensitive: API-visible merges, forge-rescued squash clusters, and orphan-adjacent
history", and the list is fixed before any run and reused identically across arms. That is a
stratified design, not a contiguous ordinal window.

**The pilot's window was too easy** (`<pilot>` "Decisions for the main run"): aioquic ordinals
2–11 produced `completed_fraction` 1.000 in every run. Its options were to widen the window, pick
a denser target (out of scope here) or change the primary metric. Which of those this ticket
carries depends on
[What are the hypotheses](01-what-are-the-hypotheses-and-primary-metrics.md).

**Target facts.** aioquic: 342 clusters, 238 recoverable only through forge data (squash-heavy,
GitHub). MARK: 69 clusters, merge-commit history, GitLab. Ground truth exists only for aioquic
w02-11. Whether MARK is usable at all waits on
[Can the rebuilt MARK pristine pass its last gate](07-can-the-mark-pristine-pass-its-last-gate.md).

**Decide:** per target, the sampling frame and strata, the list size, and the list itself (fixed
and committed); whether the ground-truth window w02-11 must be included; and whether the task
runs as one contiguous sweep (clusters build on each other's draft) or as independent tasks. That
last choice changes what "a task" means for a progressive reconstruction.

**Inputs ruled since charting (2026-09-21):**
- **Completion is the headline hypothesis (H1)**, so this ticket carries the burden of making it
  discriminate: the lists must be ones on which completion falls **below 1, with variance**. The
  validation pilot checks this; if completion is still saturated there, the hypotheses ticket is
  reopened.
- Arms A and B only. MARK has no ground truth (only aioquic's w02-11 does), so including w02-11
  matters only for the secondary reachable-recall estimate.
- Per-cluster sessions, and MARK's rebuilt pristine passes every last gate.

## Resolution (grilling, 2026-09-21)

Ruled by the user in two rounds, confirmed as a whole before recording. **The user chose the full
MARK window**, where the recommendation had been w01-30. Every other answer followed the
recommendation.

**Facts found:**
- aioquic's 342 clusters are 235 forge-rescued squashes, 104 epochs and only 3 API-visible
  merges (ordinals 2–34).
- MARK's 69 clusters are 37 merges and 32 epochs, with no forge squashes (GitLab).
- **No target has shown completion below 1 for model reasons.** The pilot's w02-11 saturated.
  MARK's full-window run (`campaigns/mark-full-1`, A1) halted at cluster 38 after two failed
  attempts, the second costing $0.00, which is an infrastructure fault, not difficulty.
- MARK costs about $5.06 per cluster ($187.38 for 37 clusters, about 8 hours for 38), against
  about $1.90 per cluster for aioquic.

**Rulings:**
- **Task shape: one contiguous window per target**, run in ordinal order. A sampled list would
  leave later clusters working on an empty draft (`experiment/workspace.py:173-208`).
- **aioquic: w02-31**, 30 clusters (3 API-visible merges, 14 epochs, 13 forge squashes). w02-11 is
  its prefix, and it ends at `c0031-pr-48092046ff28`.
- **MARK: the full w01-69** (37 merges, 32 epochs). It ends at the clone head `b901f36`, so **no
  commit lies after the window**, and the tip leak does not reach MARK through the clone.
- **Secondary reachable recall** (aioquic only) is scored on each run's draft **at its c0011
  revision tag**, against the Ground-Truth Yardstick map's w02-11 dataset (anchored `509065a`).
  It covers the first 10 clusters, and says so.

**Consequences, decided elsewhere:**
- The validation pilot checks that completion is not saturated; if it is, the hypotheses ticket
  reopens.
- The freeze prepares a new aioquic pristine for w02-31, with the future-free cut at c0031's end.
- "Set k …" rules the budget. **Rough costs**:
  - per run: about $57 and 1–2 h for aioquic, about $350 and 15 h for MARK;
  - per block (both arms, both targets): about $810 and 33 h;
  - k = 3: about $2,400 and 100 h; k = 5: about $4,000 and 165 h.

  These come before the judge, retries and replacements. The per-run budget cap must allow a MARK
  run.
