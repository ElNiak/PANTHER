# 10 — What statistical plan fits k of 3–5 per cell over two targets?

Type: research (AFK)
Status: closed (research, 2026-09-21)
Claimed: research subagent dispatched at charting
Blocked by: — (ON THE FRONTIER)
Parent: [ai_rfc Main Campaign, Ready to Launch](../map.md)

## Question

Protocol §6 item 9 asks for a statistical plan: "non-parametric tests, effect sizes,
multiplicity handling". §5 adds ">= k repeats; non-parametric tests plus effect sizes; pass^k"
and "raw counts with uncertainty, never rates alone" for rare, discrete gate exits.

The design is small: **3 arms × 2 targets × k repeats**, with k provisionally 3 (`<pilot>`) and
realistically 3–5 under the cost (the pilot's mean was $21.80 per run). Outcomes may be bounded
proportions (completed clusters over the window, possibly saturated), continuous costs with
heavy tails, and counts.

**Find, from the methodology literature and the protocol's evidence base** (`12-report.md`, the
related-work report the protocol is distilled from, where it can be found):
- Which tests are defensible at k = 3–5 per cell for a three-arm comparison, per target and
  pooled, and what they can and cannot detect (minimum detectable effect at these sizes).
- How to report pass^k and its uncertainty at small k.
- Effect-size measures suited to bounded and heavy-tailed outcomes (e.g. Cliff's delta, Vargha–
  Delaney A, bootstrap intervals), and when a Bayesian estimate is the better report.
- Multiplicity handling for three pairwise arm contrasts × a few hypotheses.
- How agent-benchmark papers of 2025–2026 with comparable repeat counts reported them.

**Output:** a short recommendation with citations, written to
`.scratch/arfc-main-campaign/research/10-statistical-plan/` (git-ignored). It feeds
[Set k, the run matrix and the budget ceiling](15-set-k-matrix-and-budget.md).

## Resolution (research, 2026-09-21)

Findings: `.scratch/arfc-main-campaign/research/10-statistical-plan/findings.md`, with the
enumeration and power script `floors_and_power.py` and its `output.txt` beside it. The directory
is git-ignored and lives only in this worktree. The findings were written by the dispatching
session from the research agent's hand-back text, because the agent's own `Write` was refused.

**The deciding fact.** Within one target, an exact rank test on k runs per arm cannot reach
α = 0.05 at k = 3 for any data: 20 arrangements give a two-sided floor of 0.10. At k = 4 the floor
is 0.029 (only complete separation rejects), and Holm's first step over three contrasts (0.0167)
is unreachable at k = 3 and at k = 4. Per-target tests become usable only at k = 5. The dispatching
session checked these floors, the Clopper–Pearson and Garwood bounds, and the cost projections by
hand.

**Recommended plan.**
- **Testing.** One confirmatory test per hypothesis, pooled over MARK and aioquic, stratified by
  target, computed exactly (floor 0.005 at k = 3). Per-target results are estimation only below
  k = 5. The run is the unit of analysis, and cost is analysed on the log scale as a ratio.
- **Multiplicity.** Closed testing within a hypothesis (the three-arm omnibus, then the pairs),
  and Bonferroni or a preregistered cost-first fixed sequence across hypotheses. With arms A and B
  only (see [Does the main campaign include arm C](17-does-the-main-campaign-include-arm-c.md))
  each hypothesis has a single contrast.
- **Reporting.** Estimation first: exact Hodges–Lehmann cost ratios, Cliff's δ as description,
  every run shown as a point. No bootstrap at five runs or fewer per cell. Boschloo's test for
  binary outcomes; Garwood intervals for counts. pass^k as a per-cell histogram of clusters by
  successes; k successes in k runs bound pass^k only at 0.025 or above.
- **For [Set k, the run matrix and the budget ceiling](15-set-k-matrix-and-budget.md).** Going
  from k = 3 to k = 5 cuts the pooled minimum detectable effect from 2.05 to 1.45 SD of log cost,
  for 67% more spend (~$392 → ~$654 at three arms). Size k from the validation pilot's
  **upper** SD limit, never from its point estimate or its effect sizes.

**Open, per the findings' §5.** MARK's cost variance is unknown. The Xu, Yang and τ-bench method
details came through WebFetch extraction, not raw text. Several statistics claims were seen only
through search summaries. The pooled Hodges–Lehmann interval is not implemented. Arm × target
interaction was not simulated. `12-report.md` (on disk as
`docs/research/2026-08-25-progressive-rfc-related-work.md`) holds no statistics references.

Adopting the plan is not ruled here: the preregistration adopts it, and k is set in
[Set k, the run matrix and the budget ceiling](15-set-k-matrix-and-budget.md).
