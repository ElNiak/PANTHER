# 17 — Does the main campaign include arm C, frozen at its pre-v2 surface?

Type: grilling (HITL)
Status: open
Claimed: —
Blocked by: — (ON THE FRONTIER)
Parent: [ai_rfc Main Campaign, Ready to Launch](../map.md)

## Question

Surfaced after charting by the research for
[What statistical plan fits](10-what-statistical-plan-fits.md). The map was charted as a
"three-arm comparison", and the charting grilling assumed arms A, B and C. **The protocol has
since said otherwise.** Spec **D42** froze arm C at its pre-v2 surface, and `<protocol>` says so
three times:

- `experiment-protocol.md:157-159` (SP7a): "Arm C stays frozen at the pre-v2, 16-tool surface
  (spec D42); the parity table's third column reads 'not available in arm C' for the two new
  rows, so **a v2 campaign compares arms A and B only**."
- `:191-195` (SP7b): arm C never sees the `structure-upsert` or `draft-render` verbs, though the
  raw `python -m ai_rfc draft render` stays reachable behind its unchanged `Bash(python -m
  ai_rfc*)` prefix. "What D42 freezes is the documented tool and verb set, not the substrate the
  prefix reaches."
- `:302-306` (SP7c): "**Arm C never consolidates.** D42 freezes its tool surface, so both the
  sweep and the one-off verb decline the round for C, and a v2 campaign compares arms A and B."

The 2026-08-31 pilot's "Arm C stays" (`<pilot>` "Decisions for the main run") predates D42. It
called arm C "the arm that produced the pilot's clearest differential signal" (87 hand edits, the
widest token spread), and the B-against-C contrast is what the protocol keeps to isolate
within-class affordance (§1).

**Decide:** is the main campaign a v2 campaign of arms A and B only, as D42 and the protocol's v2
entries say? Or does arm C return, and if so, on which surface? Options include C frozen at
pre-v2 (then its drafts are not comparable on the v2 measures: no consolidation, no structures,
and v2 build-gate differences), or C raised to v2 parity (which reverses D42). The answer reshapes
[What are the hypotheses](01-what-are-the-hypotheses-and-primary-metrics.md) (the number of
contrasts),
[Diff the three rendered arm prompts](02-diff-the-rendered-arm-prompts.md), the statistical plan
(with two arms the within-hypothesis multiplicity layer disappears), and the run count, and so
the cost, of every later ticket.
