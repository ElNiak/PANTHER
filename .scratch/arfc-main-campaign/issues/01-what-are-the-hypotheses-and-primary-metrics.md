# 01 — What are the hypotheses, and which one primary metric does each carry?

Type: grilling (HITL)
Status: open
Claimed: —
Blocked by: [Does the main campaign include arm C](17-does-the-main-campaign-include-arm-c.md)
Parent: [ai_rfc Main Campaign, Ready to Launch](../map.md)

## Question

The protocol requires "one primary metric per hypothesis, designated in the preregistration;
everything else is descriptive or multiplicity-corrected" (`<protocol>` §3), but it states no
hypotheses. This ticket names them and gives each exactly one primary metric. It is the root of
the map: the pilot's own report says the metric decision "should be made before k is chosen,
because it changes what k buys" (`<pilot>` "Decisions for the main run").

**What the protocol already fixes.** Primary outcome: state-verified completed clusters over the
window, with pass^k over repeats. Primary cost: cache-adjusted billed cost, per run and per
completed unit. Its expectation paragraph (§3, closing "Expectation-setting") predicts interface
effects on success **near zero** at current model strength, with the live effects in **cost,
consistency and the error taxonomy**. If those do not materialise, "the contribution is
instrument quality and domain transfer, not effect discovery".

**What the pilot measured (2026-08-31, aioquic w02-11, k = 2).**
- `completed_fraction` was **1.000 with zero variance** in all six runs. A ceiling that flat
  cannot discriminate arms.
- Metrics that did vary: `cost_per_completed_cluster`, `tokens_to_first_completion`, trajectory
  AUC, and the hand-edit count (arm C made 87).
- "Normative change" is not a stable property of a cluster: non-normative counts ran
  0, 1, 2, 2, 3, 1 across the runs, and B1 and A1 disagreed about `c0004`. Any metric that leans
  on it inherits that variance.
- `checked_fraction` is identically 0.0 in model-only runs (D23), so it cannot be primary.
- The arm comparison is confounded by the arm-B prompt defect (fixed as `8358238`), so no arm
  difference from the pilot may seed a hypothesis.

**What exists since the pilot (SP7d).** A blinded **judge** of draft quality, and a
**ground-truth** scorer over 41 anchored HTTP/3 facts for aioquic w02-11 only (scored over 35;
`claim_accuracy` and `recall`, both `None` when nothing was attempted). Every draft scored recall
8/35, but **that is the window's ceiling, not a finding about the drafts**. The sibling map
"Ground-Truth Yardstick" (`.scratch/ground-truth-yardstick/`) found the dataset anchored at
aioquic's 2025 tip and built from the final RFCs, while w02-11 ends in 2019. Its R93 withdraws
SP7d's "v2 recovers no more facts". Any ground-truth measure named here uses that map's
**reachable recall**, whose definition it owns.

**Also fixed here** (protocol §6 items 2 and 10): the trajectory aggregations (final
`checked_fraction`, tokens-to-threshold, trajectory AUC) and the cache-accounting method and cost
formula. The pilot measured cache reads and creation at 99.68% of 198.8 M tokens.

**Decide:** the hypothesis list; one primary metric for each; which measures are secondary or
descriptive; and whether completion stays primary under a harder task list (then
[Which task list does each target use](12-which-task-list-per-target.md) carries the burden of
un-saturating it) or yields to a metric that varied. Graduates the Not-yet-specified patches on
MARK ground truth and on judged quality, one way or the other.
