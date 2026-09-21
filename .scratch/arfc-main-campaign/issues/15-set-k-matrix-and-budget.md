# 15 — Set k, the run matrix and the budget ceiling

Type: grilling (HITL)
Status: open
Claimed: —
Blocked by: [What statistical plan fits](10-what-statistical-plan-fits.md), [Run the validation pilot](14-run-the-validation-pilot.md)
Parent: [ai_rfc Main Campaign, Ready to Launch](../map.md)

## Question

Protocol §6 item 3: "k (repeats per cell) and the run matrix". The matrix is arms {A, B, C} ×
targets {MARK, aioquic} × k (§4). The pilot's provisional k = 3 was set before the metric
decision, and the pilot itself said k = 3 "adds nothing" on a zero-variance metric.

**With the validation pilot's measured variance and the statistical plan's minimum detectable
effects in hand, decide:**
- k per cell, and whether it differs by target.
- The per-run budget cap and the per-session timeout. The pilot's $25 cap and 7200 s timeout
  were set for 10-cluster single-session runs. **A full MARK run needs far more**: about $350 and
  15 h.
- **The total budget ceiling for the main campaign**, and what happens if it is reached mid-way.
  With arms A and B only, the matrix is 2 × 2 × k. With the windows ruled in
  [Which task list does each target use](12-which-task-list-per-target.md) (aioquic w02-31, MARK
  w01-69), the rough costs, **superseding the earlier $87 × k estimate made at 10 clusters**, are:
  - per run: about $57 and 1–2 h for aioquic, about $350 and 15 h for MARK;
  - per block (both arms, both targets): about $810 and 33 h;
  - **k = 3: about $2,400 and 100 h; k = 5: about $4,000 and 165 h**.

  These come before the judge, fault retries and replacements.

The user owns the budget. This ticket presents the options with their power and cost side by
side, and records the ruling.

**Sizing basis, ruled 2026-09-21:** four confirmatory hypotheses under **Holm**, whose strictest
step is 0.0125. Size k so that each primary metric (completed fraction, cost per completed
cluster, tokens to first completion, the judge's score) has adequate power at that step, from the
validation pilot's **upper** SD limits. The statistical plan's minimum-detectable-effect table at
α = 0.0167 is the nearest precomputed row.
