# 12 — Which task list does each target use, with its provenance-class coverage?

Type: grilling (HITL)
Status: open
Claimed: —
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
