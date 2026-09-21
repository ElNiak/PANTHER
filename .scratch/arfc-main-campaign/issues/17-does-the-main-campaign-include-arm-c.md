# 17 — Does the main campaign include arm C, frozen at its pre-v2 surface?

Type: grilling (HITL)
Status: closed (grilling, 2026-09-21)
Claimed: chart-ai-rfc-main-campaign (session 40f5ddb1), 2026-09-21 13:03 CEST
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

## Resolution (grilling, 2026-09-21)

Ruled by the user in two rounds, confirmed as a whole before recording.

**The evidence put to the user.**
- **For dropping arm C.** Spec D42 ("The raw arm C is frozen at today's surface",
  `docs/superpowers/specs/2026-09-02-arfc-draft-quality-design.md:50`) and the protocol's three v2
  entries. The prompt diff's D8, D9, D13 and D14: C has no structures, build or consolidation;
  its tags have no build gate and no rollback; it has unrestricted `git` and `sqlite3`. The parity
  audit's K2: no twin for any C path.
- **For keeping it.** Protocol §1 ("the B-versus-C contrast is deliberately kept"), and the
  pilot's 87 arm-C hand edits against 1 between A and B.
- **Cost.** 12 runs against 18 at k = 3.

**Rulings:**
- **The main campaign compares arms A and B only.** Each hypothesis has one contrast.
- **The departure from protocol §1 is stated in the preregistration**, citing D42 and the v2
  entries. The protocol is not edited now.
- **The 2026-08-31 pilot's arm-C runs are cited** as pre-v2, single-target, prompt-confounded
  history of the within-class affordance effect, and never pooled.
- **The class-3 companion measurement stays in the fog.** It asks a different question (no
  function-calling layer at all).

**What changes elsewhere** (map maintenance, no further ruling):
- The map's Destination now reads "arms A and B".
- In [Rule each arm asymmetry](04-rule-each-arm-asymmetry.md), the arm-C rows D8–D14 and K2 need
  no ruling, and D1's and D16's arm-C halves fall away.
- [What are the hypotheses](01-what-are-the-hypotheses-and-primary-metrics.md) has one A-against-B
  contrast per hypothesis.
- The landing ticket's run order and "Set k, the run matrix and the budget ceiling" use two arms
  per block, so 4k runs across the two targets.
