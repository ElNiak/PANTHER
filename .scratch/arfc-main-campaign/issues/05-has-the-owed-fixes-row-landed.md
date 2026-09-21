# 05 — Has the owed-fixes row landed on `origin/main`, and does it fix R91/R92?

Type: task (HITL checkpoint)
Status: open
Claimed: —
Blocked by: — (ON THE FRONTIER)
Parent: [ai_rfc Main Campaign, Ready to Launch](../map.md)

## Question

The owed-fixes row (plan `docs/superpowers/plans/2026-09-21-arfc-owed-fixes.md`, 55 items from
CLI-3's whole-branch review) is **a given, outside this map** (user ruling at charting). It is
mid-execution in `<ai_rfc>` and owns files that three tickets here need:
`experiment/{runner,audit,per_cluster}.py` and `driver/{spawn,stop,coverage,record}.py`. This
ticket is the checkpoint that turns "the row has landed" into something the frontier can compute.

**Closes when both hold:**
1. The row's session has sent its promised pre-push message (it said on 2026-09-21 that it will
   message before the push and the gitlink bump; find its current name with `ListAgents`).
2. `git -C <ai_rfc> log origin/main` shows the row's range, **`8358238` (the ARM-B fix)
   included**, and PANTHER's gitlink points into it.

**Then check R91/R92** (SP7d ledger `<ai_rfc>/.superpowers/sdd/2026-09-15-arfc-sp7d/progress.md`,
rulings R90–R92):
- **R91**: `consolidations_recorded` counts the `revisions.yaml` entry, which is written *before*
  the tag. A tag the build gate refuses therefore reports `recorded=True`.
- **R92**: the dangling entry then fails the strict citation gate on the final workspace. MARK's
  post-round copy went from completed 37/69 to 0/69, and completion is the protocol's primary
  outcome.

At charting, **the row's plan and deviation log never mention R91, R92, `consolidations_recorded`
or `recorded=True`**. The defects were reported to the row's session by `post-sp7d-cleanup-gepa`,
but adoption is unconfirmed. Grep the row's landed commits and ledger. **If R91/R92 are not
fixed, the user rules** whether this map takes them on (a new ticket that blocks
[Run the validation pilot](14-run-the-validation-pilot.md)) or waits for the row's follow-up. Any
fix must handle record-before-tag.
