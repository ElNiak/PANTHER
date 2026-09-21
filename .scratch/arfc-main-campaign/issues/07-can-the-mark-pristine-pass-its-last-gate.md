# 07 — Can the rebuilt MARK pristine carry a v2 cluster through its last gate?

Type: task (AFK, $0)
Status: open
Claimed: —
Blocked by: — (ON THE FRONTIER)
Parent: [ai_rfc Main Campaign, Ready to Launch](../map.md)

## Question

MARK is one of the two targets (user ruling at charting). Its old draft repository **can never
pass the v2 build gate**: the 2026-09-02 MARK draft repo is a copy of i-d-template itself, from
before D45, with no root `Makefile`, so `idnits`' versioned sub-build has no `.targets.mk` rule
(SP7d ruling R90). No MARK revision, not even -37, passes `ai-rfc draft build`. The paid MARK
consolidation round of 2026-09-21 ran for $11.37 and could not tag for this reason. A $0
`draft build` beforehand would have caught it.

SP7d rebuilt a MARK pristine that passed its gate:
`~/ai-rfc-experiments/rebuild-sp7d/pristine/mark-w01-69`, under a separate root, because
`prepare` refuses the old evidence path. Its two forge captures are byte-identical. Whether a
*session's* work on it can clear the **last** gate (build, then `revision tag`, then the strict
citation gate) is unmeasured.

**Do, at $0:** copy the pristine with `copy_workspace` into a scratch directory. Run
`ai-rfc draft build` on the fresh draft. Then walk one cluster's gates by hand with the agent
verbs (claim, checkpoint, `revision record`, `revision tag`) far enough to see the tag either
created or refused. **Output:** MARK ready for a v2 campaign, or the list of what a fresh
bootstrap must change. Never edit the pristine itself.
