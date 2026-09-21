# 14 — Run the validation pilot

Type: task (HITL: spend)
Status: open
Claimed: —
Blocked by: [What are the hypotheses](01-what-are-the-hypotheses-and-primary-metrics.md), [Which runs are excluded](08-which-runs-are-excluded.md), [Freeze prompts, pin code, and dry-run](13-freeze-pin-and-dry-run.md), [Land the fault, retry and exclusion rules](18-land-the-fault-retry-and-exclusion-rules.md)
Parent: [ai_rfc Main Campaign, Ready to Launch](../map.md)

## Question

The existing data cannot size the main campaign. The 2026-08-31 pilot's primary outcome had zero
variance, and its arm comparison is confounded by the arm-B prompt defect. This paid pilot
(in scope by user ruling at charting) measures **the variance of the chosen primary metrics on
the frozen artifacts**, from which
[Set k, the run matrix and the budget ceiling](15-set-k-matrix-and-budget.md) sizes k. It also
gives the first un-confounded look at the arms.

**Before launch, the user approves the spend** with: the consent print, the exact command, the
model ids, a fresh quota reading, the pinned code's commit, the run count and a cost estimate
from the pilot ($21.80 mean per run; SP7d arm-A runs $15.14 and $15.83). A launch is not a
decision this map makes alone.

**Decide with the user at launch:** the pilot's size (which cells, how many repeats) and its
budget cap (the pilot said raise it from $25; two of six runs came within $1). Apply the
exclusion and fault rules of
[Which runs are excluded](08-which-runs-are-excluded.md) exactly as the main campaign would.

**Output:** per primary metric, the per-cell mean and variance, and the run log with API
conditions, linked from the resolution comment. The pilot's results are **not** evidence for the
paper's hypotheses: they sized the campaign, and they are reported as such.
