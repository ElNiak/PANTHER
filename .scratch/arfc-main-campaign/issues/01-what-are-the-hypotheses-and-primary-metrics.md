# 01 — What are the hypotheses, and which one primary metric does each carry?

Type: grilling (HITL)
Status: closed (grilling, 2026-09-21)
Claimed: chart-ai-rfc-main-campaign (session 40f5ddb1), 2026-09-21 15:20 CEST
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
un-saturating it) or yields to a metric that varied. Graduates the Not-yet-specified patch on
judged quality, one way or the other.

**Settled since charting, so these are inputs:**
- **The arms are A and B only** ([Does the main campaign include arm C](17-does-the-main-campaign-include-arm-c.md)),
  so each hypothesis is one A-against-B contrast.
- **MARK has no ground-truth dataset** (the Ground-Truth Yardstick map's rulings: MARK's code
  declares no spec). A recall or claim-accuracy hypothesis can hold only for aioquic, on that
  map's rebuilt w02-11 dataset and its **reachable recall**. MARK's figures are `None`.
- The statistical plan (research, closed) recommends one pooled, stratified exact test per
  hypothesis, estimation per target, and Bonferroni or a cost-first fixed sequence across
  hypotheses. With two arms there is no within-hypothesis multiplicity layer.

## Resolution (grilling, 2026-09-21)

Ruled by the user in three rounds, confirmed as a whole before recording. **The user chose
completion as the headline**, where the recommendation had been cost. **All four families are
confirmatory**, where the recommendation had been cost and completion only. Every other answer
followed the recommendation.

**Hypotheses** (arm A against arm B, all **two-sided**, all confirmatory):
- **H1, the headline, completion**: the completed fraction per run, meaning state-verified
  completed clusters over the task list's size (`metrics.py:326-343`).
- **H2, cost**: cost per completed cluster, meaning the run's cache-adjusted billed cost (faulted
  spend excluded) over its completed clusters, on the log scale. A run that completed nothing
  ranks worst (+infinity).
- **H3, process efficiency**: tokens to first completion per run. A run with no completion ranks
  worst.
- **H4, draft quality**: the blinded judge's score for each run's final draft, on both targets.
  The judge's prompt and rubric are frozen with the campaign.

**Inference:**
- One pooled, target-stratified, exact rank test per hypothesis; per-target results are
  estimation (the statistical plan).
- **Holm over H1–H4** (familywise error 0.05), with raw and adjusted p-values both reported. At
  k = 3, the pooled floor (0.005) still reaches Holm's strictest step (0.0125).
- **H1 must discriminate.** The task list has to un-saturate completion. If the validation pilot
  still shows saturation, **this ticket is reopened before the freeze**.

**Secondary** (estimated with intervals, not tested): cost per run, trajectory AUC, pass^k, the
v2 form metrics, and reachable recall on aioquic. **Descriptive**: hand edits, bypass attempts,
the error taxonomy, integrity rate, failure-cost share, gate exits, and faulted spend.

**Definitions** (protocol §6 items 2 and 10), as `experiment/metrics.py` computes them and frozen
at the pinned commit:
- the final `checked_fraction` is reported, and is 0.0 by design (D23);
- tokens-to-threshold is tokens to first completion;
- AUC is as coded;
- cost is the CLI's reported `total_cost_usd` per session, summed per run, with faulted sessions
  excluded and unpriced sessions reported apart. **It is notional under a subscription, which the
  freeze must check.**
